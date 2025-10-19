"""
Constructor de Grafo Heterogéneo para ACO+GraphSAGE

Construye un grafo que representa el problema de asignación de horarios:
- Nodos: CourseSection, Professor, Classroom, TimeSlot, Curriculum
- Aristas: Relaciones de asignación potencial y restricciones

El grafo se usa para:
1. GraphSAGE aprende embeddings de nodos
2. ACO navega por las aristas para construir soluciones
"""

from typing import Dict, List, Tuple, Set, Optional
from dataclasses import dataclass
import torch
import torch_geometric
from torch_geometric.data import HeteroData
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import text
from math import ceil
import unicodedata

from app.models import (
    Course, CourseSection, Professor, Classroom, TimeSlot,
    ProfessorRestriction
)


# ============================================================================
# ESTRUCTURAS DE DATOS
# ============================================================================

@dataclass
class GraphNode:
    """Representación de un nodo en el grafo"""
    id: int
    type: str  # 'section', 'professor', 'classroom', 'timeslot', 'curriculum'
    features: np.ndarray


@dataclass
class GraphEdge:
    """Representación de una arista en el grafo"""
    source: int
    target: int
    edge_type: str
    weight: float = 1.0


@dataclass
class SectionInstance:
    """Sección extendida para permitir divisiones automáticas por capacidad."""
    id: int
    original: CourseSection
    alumnos_proyectados: int
    group_index: int = 0
    group_count: int = 1
    max_capacity: int = 0

    def __getattr__(self, item):
        return getattr(self.original, item)

    @property
    def original_id(self) -> int:
        return self.original.id

    @property
    def is_split(self) -> bool:
        return self.group_count > 1

# ============================================================================
# CONSTRUCTOR DEL GRAFO
# ============================================================================

class TimetableGraphBuilder:
    """Construye el grafo heterogéneo del problema de horarios"""
    
    def __init__(
        self,
        db: Session,
        periodo_academico: str = "2025-1"
    ):
        self.db = db
        self.periodo_academico = periodo_academico
        
        # Mapeo de IDs de BD a índices en el grafo
        self.section_id_to_idx: Dict[int, int] = {}
        self.professor_id_to_idx: Dict[int, int] = {}
        self.classroom_id_to_idx: Dict[int, int] = {}
        self.timeslot_id_to_idx: Dict[int, int] = {}
        self.curriculum_id_to_idx: Dict[str, int] = {}  # ciclo -> idx
        
        # Mapeo inverso
        self.idx_to_section_id: Dict[int, int] = {}
        self.idx_to_professor_id: Dict[int, int] = {}
        self.idx_to_classroom_id: Dict[int, int] = {}
        self.idx_to_timeslot_id: Dict[int, int] = {}
        self.idx_to_curriculum_id: Dict[int, str] = {}
        
        # Información adicional
        self.section_durations: Dict[int, int] = {}  # section_id -> n_bloques
        self.section_projected_students: Dict[int, int] = {}
        self.section_metadata: Dict[int, Dict[str, object]] = {}
        self.section_candidate_stats: Dict[int, Dict[str, int]] = {}
        self.sections_by_league: Dict[Tuple[str, int], List[int]] = {}
        self.league_session_types: Dict[Tuple[str, int], Set[str]] = {}
        self.section_session_types: Dict[int, str] = {}
        self.sections_by_block: Dict[str, List[int]] = {}
        self.prof_assign_by_league: Dict[Tuple[int, str, int], List[int]] = {}
        self.prof_assign_by_type: Dict[Tuple[int, str], List[int]] = {}
        self.prof_assign_by_course: Dict[int, List[int]] = {}
        self.course_session_durations: Dict[Tuple[int, str], int] = {}
        self.virtual_to_real_section: Dict[int, int] = {}
        self.section_virtual_groups: Dict[int, List[int]] = {}
        self.section_instances: List[SectionInstance] = []

        self._load_course_session_hours()
        
    def build_graph(self) -> HeteroData:
        """
        Construye el grafo heterogéneo completo.
        
        Returns:
            HeteroData: Grafo de PyTorch Geometric con nodos y aristas tipados
        """
        graph = HeteroData()
        
        print("Construyendo grafo heterogéneo...")
        
        # 1. Cargar datos de la BD
        sections = self._load_sections()
        professors = self._load_professors()
        self._load_professor_assignments()
        classrooms = self._load_classrooms()
        timeslots = self._load_timeslots()
        curricula = self._extract_curricula(sections)
        section_instances = self._generate_section_instances(sections, classrooms)
        self.section_instances = section_instances

        # 2. Crear nodos con features
        print(
            f"Creando nodos: {len(section_instances)} secciones, {len(professors)} profesores, "
            f"{len(classrooms)} aulas, {len(timeslots)} franjas, {len(curricula)} currículos"
        )

        graph['section'].x = self._create_section_features(section_instances)
        graph['professor'].x = self._create_professor_features(professors)
        graph['classroom'].x = self._create_classroom_features(classrooms)
        graph['timeslot'].x = self._create_timeslot_features(timeslots)
        graph['curriculum'].x = self._create_curriculum_features(curricula)

        # 3. Crear aristas de asignación potencial
        print("Creando aristas de asignación potencial...")
        self._add_assignment_edges(graph, section_instances, professors, classrooms, timeslots)

        # 4. Crear aristas de conflicto curricular
        print("Creando aristas de conflicto curricular...")
        self._add_curriculum_edges(graph, section_instances)

        # 5. Crear aristas de coherencia de liga
        print("Creando aristas de coherencia de liga...")
        self._add_league_edges(graph, section_instances)
        
        # 6. Crear aristas de restricciones de profesor
        print("Creando aristas de restricciones de profesor...")
        self._add_professor_restriction_edges(graph, professors)
        
        print(f"Grafo construido: {graph}")
        
        return graph

    
    # ========================================================================
    # CARGA DE DATOS
    # ========================================================================
    
    def _load_sections(self) -> List[CourseSection]:
        """Carga todas las secciones activas CON estudiantes proyectados > 0"""
        sections = (
            self.db.query(CourseSection)
            .filter(CourseSection.activa == True)
            .filter(CourseSection.alumnos_proyectados > 0)  # FILTRAR secciones sin estudiantes
            .all()
        )
        print(f"  → Secciones cargadas: {len(sections)} (filtradas las que tienen 0 estudiantes)")
        return sections
    
    def _load_professors(self) -> List[Professor]:
        """Carga todos los profesores activos"""
        professors = (
            self.db.query(Professor)
            .all()
        )
        
        for idx, prof in enumerate(professors):
            self.professor_id_to_idx[prof.id] = idx
            self.idx_to_professor_id[idx] = prof.id
        
        return professors
    
    def _load_classrooms(self) -> List[Classroom]:
        """Carga todas las aulas activas"""
        classrooms = (
            self.db.query(Classroom)
            .filter(Classroom.active == True)
            .all()
        )
        
        for idx, classroom in enumerate(classrooms):
            self.classroom_id_to_idx[classroom.id] = idx
            self.idx_to_classroom_id[idx] = classroom.id
        
        return classrooms
    
    def _load_timeslots(self) -> List[TimeSlot]:
        """Carga todas las franjas horarias"""
        timeslots = (
            self.db.query(TimeSlot)
            .order_by(TimeSlot.dia_semana, TimeSlot.orden)
            .all()
        )
        
        for idx, ts in enumerate(timeslots):
            self.timeslot_id_to_idx[ts.id] = idx
            self.idx_to_timeslot_id[idx] = ts.id
        
        return timeslots
    
    def _extract_curricula(self, sections: List[CourseSection]) -> List[str]:
        """Extrae los currículos únicos (ciclos) de las secciones"""
        curricula = set()
        
        for section in sections:
            course = section.course
            if course.ciclo:
                curricula.add(course.ciclo)
        
        curricula_list = sorted(list(curricula))
        
        for idx, ciclo in enumerate(curricula_list):
            self.curriculum_id_to_idx[ciclo] = idx
            self.idx_to_curriculum_id[idx] = ciclo
        
        return curricula_list

    def _generate_section_instances(
        self,
        sections: List[CourseSection],
        classrooms: List[Classroom],
    ) -> List[SectionInstance]:
        """Genera instancias de sección dividiendo automáticamente si excede la capacidad."""
        # Resetear estructuras dependientes de secciones
        self.section_id_to_idx.clear()
        self.idx_to_section_id.clear()
        self.section_durations.clear()
        self.section_projected_students.clear()
        self.section_metadata.clear()
        self.section_candidate_stats.clear()
        self.sections_by_league.clear()
        self.league_session_types.clear()
        self.section_session_types.clear()
        self.sections_by_block.clear()
        self.virtual_to_real_section.clear()
        self.section_virtual_groups.clear()

        instances: List[SectionInstance] = []
        normalized_classrooms = [
            (classroom, self._normalize_classroom_type(classroom.tipo))
            for classroom in classrooms
        ]
        next_virtual_id = -1

        for section in sections:
            session_type = self._normalize_session_type(section.tipo)
            projected_students = section.alumnos_proyectados or 0

            compatible_classrooms = [
                classroom
                for classroom, normalized_type in normalized_classrooms
                if not (session_type == 'L' and normalized_type != 'laboratorio')
            ]

            max_capacity = max(
                (classroom.capacidad or 0) for classroom in compatible_classrooms
            ) if compatible_classrooms else 0

            if max_capacity > 0 and projected_students > max_capacity:
                group_count = max(1, ceil(projected_students / max_capacity))
            else:
                group_count = 1

            remaining_students = projected_students

            if group_count > 1:
                print(
                    f"⚠️  Sección {section.id} (curso {section.course.codigo if section.course else 'sin-curso'}) "
                    f"dividida en {group_count} subgrupos de hasta {max_capacity} estudiantes"
                )

            for group_index in range(group_count):
                if group_index == 0:
                    instance_id = section.id
                else:
                    instance_id = next_virtual_id
                    next_virtual_id -= 1

                if max_capacity > 0:
                    students_for_instance = min(max_capacity, remaining_students)
                else:
                    students_for_instance = remaining_students if group_index == 0 else 0

                instance = SectionInstance(
                    id=instance_id,
                    original=section,
                    alumnos_proyectados=students_for_instance,
                    group_index=group_index,
                    group_count=group_count,
                    max_capacity=max_capacity,
                )

                remaining_students = max(0, remaining_students - students_for_instance)

                instances.append(instance)
                idx = len(instances) - 1

                self.section_id_to_idx[instance.id] = idx
                self.idx_to_section_id[idx] = instance.id
                self.virtual_to_real_section[instance.id] = section.id
                self.section_virtual_groups.setdefault(section.id, []).append(instance.id)

                duration = self._get_section_duration(section)
                self.section_durations[instance.id] = duration
                self.section_projected_students[instance.id] = instance.alumnos_proyectados
                self.section_session_types[instance.id] = session_type

                course = section.course
                ciclo = course.ciclo if course else None
                course_code = course.codigo if course else None
                league_id = section.league or 1

                block_id, block_index = self._compute_block_info(ciclo, league_id)

                # Obtener modalidad del curso para manejar cursos virtuales (NO_PRESENCIAL)
                course_obj = self.db.query(Course).filter_by(id=section.course_id).first()
                course_modalidad = course_obj.modalidad if course_obj else None

                self.section_metadata[instance.id] = {
                    "course_code": course_code,
                    "session_type": session_type,
                    "league": league_id,
                    "ciclo": ciclo,
                    "modalidad": course_modalidad,  # Agregar modalidad (NO_PRESENCIAL, PRESENCIAL)
                    "original_section_id": section.id,
                    "split_group_index": group_index,
                    "split_group_count": group_count,
                    "total_projected": projected_students,
                    "max_classroom_capacity": max_capacity,
                    "duration_blocks": duration,
                    "block_id": block_id,
                    "franja_index": block_index,
                }

                self.section_candidate_stats[instance.id] = {
                    "professors": 0,
                    "classrooms": 0,
                    "timeslots": 0,
                }

                if course_code:
                    league_key = (course_code, league_id)
                    self.sections_by_league.setdefault(league_key, []).append(instance.id)
                    self.league_session_types.setdefault(league_key, set()).add(session_type)

                if block_id:
                    self.sections_by_block.setdefault(block_id, []).append(instance.id)

        return instances

    def _compute_block_info(self, ciclo: Optional[str], league_id: Optional[int]) -> Tuple[Optional[str], Optional[int]]:
        """Calcula la franja (bloque) sugerida para una sección según ciclo y liga."""
        if not ciclo or league_id is None:
            return None, None

        franja_index = 1 if league_id % 2 == 1 else 2
        block_id = f"Bloque_{ciclo}_Franja{franja_index}"
        return block_id, franja_index
    
    def _get_section_duration(self, section: CourseSection) -> int:
        """
        Calcula la duración en bloques de 50 minutos para una sección.
        
        La duración depende del tipo de sesión y está almacenada en el curso.
        """
        course = section.course
        session_type = self._normalize_session_type(section.tipo)

        if course:
            key = (course.id, session_type)
            if key in self.course_session_durations:
                return self.course_session_durations[key]

        if session_type == 'T':
            return 2
        if session_type == 'P':
            return 2
        if session_type == 'L':
            return 3
        return 1
    
    # ========================================================================
    # CREACIÓN DE FEATURES
    # ========================================================================
    
    def _create_section_features(self, sections: List[CourseSection]) -> torch.Tensor:
        """
        Crea features para nodos de sección.
        
        Features:
        - One-hot del tipo (T/P/L)
        - Alumnos proyectados (normalizado)
        - League ID (normalizado)
        - Duración en bloques
        - One-hot del ciclo (primeros bits del hash)
        """
        features = []
        
        max_alumnos = max((s.alumnos_proyectados or 0) for s in sections) or 1
        max_league = max((s.league or 0) for s in sections) or 1
        
        for section in sections:
            feat = []
            
            # One-hot tipo (3 dims)
            tipo = self._normalize_session_type(section.tipo)
            feat.extend([1.0 if tipo == 'T' else 0.0,
                        1.0 if tipo == 'P' else 0.0,
                        1.0 if tipo == 'L' else 0.0])
            
            # Alumnos proyectados (normalizado)
            alumnos = (section.alumnos_proyectados or 0) / max_alumnos
            feat.append(alumnos)
            
            # League (normalizado)
            league = (section.league or 0) / max_league
            feat.append(league)
            
            # Duración
            duracion = self.section_durations.get(section.id, 1) / 3.0  # Normalizado
            feat.append(duracion)
            
            # Ciclo (hash simple)
            ciclo = section.course.ciclo or ""
            ciclo_hash = hash(ciclo) % 100 / 100.0
            feat.append(ciclo_hash)
            
            features.append(feat)
        
        return torch.tensor(features, dtype=torch.float32)
    
    def _create_professor_features(self, professors: List[Professor]) -> torch.Tensor:
        """
        Crea features para nodos de profesor.
        
        Features:
        - Número de restricciones (normalizado)
        - Número de cursos asignados (normalizado)
        - Embedding aleatorio (para inicialización)
        """
        features = []
        
        for prof in professors:
            feat = []
            
            # Contar restricciones
            n_restrictions = len(prof.restrictions)
            feat.append(n_restrictions / 20.0)  # Normalizado (max ~20)
            
            # Contar cursos asignados
            n_courses = len(prof.courses)
            feat.append(n_courses / 10.0)  # Normalizado (max ~10)
            
            # Embedding aleatorio (será aprendido)
            feat.extend(np.random.randn(5).tolist())
            
            features.append(feat)
        
        return torch.tensor(features, dtype=torch.float32)
    
    def _create_classroom_features(self, classrooms: List[Classroom]) -> torch.Tensor:
        """
        Crea features para nodos de aula.
        
        Features:
        - Capacidad (normalizada)
        - One-hot del tipo (teorica/practica/laboratorio)
        - Tiene computadoras (binario)
        - Número de computadoras (normalizado)
        - Edificio (hash)
        - Piso (normalizado)
        """
        features = []
        
        max_capacidad = max(c.capacidad for c in classrooms) or 1
        max_computadoras = max((c.numero_computadoras or 0) for c in classrooms) or 1
        
        for classroom in classrooms:
            feat = []
            
            # Capacidad
            feat.append(classroom.capacidad / max_capacidad)
            
            # One-hot tipo (NORMALIZADO: LAB -> laboratorio, NOLAB -> teorica)
            tipo_normalizado = self._normalize_classroom_type(classroom.tipo)
            feat.extend([
                1.0 if tipo_normalizado == 'teorica' else 0.0,
                1.0 if tipo_normalizado == 'practica' else 0.0,
                1.0 if tipo_normalizado == 'laboratorio' else 0.0,
            ])
            
            # Computadoras
            feat.append(1.0 if classroom.tiene_computadoras else 0.0)
            feat.append((classroom.numero_computadoras or 0) / max_computadoras)
            
            # Edificio (hash)
            edificio_hash = hash(classroom.edificio or "") % 100 / 100.0
            feat.append(edificio_hash)
            
            # Piso (convertir de string a int, normalizado)
            try:
                piso_num = int(classroom.piso or "1") / 10.0
            except (ValueError, AttributeError):
                piso_num = 0.1
            feat.append(piso_num)
            
            features.append(feat)
        
        return torch.tensor(features, dtype=torch.float32)
    
    def _create_timeslot_features(self, timeslots: List[TimeSlot]) -> torch.Tensor:
        """
        Crea features para nodos de franja horaria.
        
        Features:
        - Día de la semana (one-hot 6 dims)
        - Hora de inicio (normalizada)
        - Orden en el día (normalizado)
        - Periodo (one-hot: mañana/tarde/noche)
        """
        features = []
        
        for ts in timeslots:
            feat = []
            
            # Día de la semana (one-hot)
            for dia in range(1, 7):
                feat.append(1.0 if ts.dia_semana == dia else 0.0)
            
            # Hora de inicio (normalizada 7:00-20:00 -> 0-1)
            # Parsear string "HH:MM"
            if isinstance(ts.hora_inicio, str):
                hora_parts = ts.hora_inicio.split(":")
                hora_inicio = int(hora_parts[0]) + int(hora_parts[1]) / 60.0
            else:
                # Si es time object
                hora_inicio = ts.hora_inicio.hour + ts.hora_inicio.minute / 60.0
            feat.append((hora_inicio - 7.0) / 13.0)
            
            # Orden en el día
            feat.append(ts.orden / 16.0)
            
            # Periodo (one-hot)
            feat.extend([
                1.0 if ts.periodo == 'mañana' else 0.0,
                1.0 if ts.periodo == 'tarde' else 0.0,
                1.0 if ts.periodo == 'noche' else 0.0,
            ])
            
            features.append(feat)
        
        return torch.tensor(features, dtype=torch.float32)
    
    def _create_curriculum_features(self, curricula: List[str]) -> torch.Tensor:
        """
        Crea features para nodos de currículo.
        
        Features:
        - Embedding basado en el nombre del ciclo
        - Número de secciones en este currículo
        """
        features = []
        
        for ciclo in curricula:
            feat = []
            
            # Hash del ciclo
            ciclo_hash = hash(ciclo) % 1000 / 1000.0
            feat.append(ciclo_hash)
            
            # Número de secciones (aproximado)
            # Contar secciones que pertenecen a este ciclo
            n_sections = sum(
                1 for section_ids in self.sections_by_league.values()
                for _ in section_ids
            ) / len(curricula)  # Aproximación
            feat.append(n_sections / 100.0)
            
            # Embedding aleatorio
            feat.extend(np.random.randn(5).tolist())
            
            features.append(feat)
        
        return torch.tensor(features, dtype=torch.float32)
    
    # ========================================================================
    # CREACIÓN DE ARISTAS
    # ========================================================================
    
    def _add_assignment_edges(
        self,
        graph: HeteroData,
        sections: List[CourseSection],
        professors: List[Professor],
        classrooms: List[Classroom],
        timeslots: List[TimeSlot],
    ):
        """
        Crea aristas que representan asignaciones potenciales.
        
        Tipos de aristas:
        - section -> professor: puede ser asignado a
        - section -> classroom: puede usar
        - section -> timeslot: puede ocupar (inicio de bloque)
        """
        # Section -> Professor
        # Usar la relación many-to-many profesor-curso
        # Cada sección se conecta con todos los profesores que enseñan su curso
        section_to_prof = []
        
        for section in sections:
            sec_idx = self.section_id_to_idx[section.id]
            candidate_professors = self._candidate_professors_for_section(section)
            stats = self.section_candidate_stats.setdefault(section.id, {
                "professors": 0,
                "classrooms": 0,
                "timeslots": 0,
            })
            stats["professors"] = len(candidate_professors)
            for professor_id in candidate_professors:
                if professor_id in self.professor_id_to_idx:
                    prof_idx = self.professor_id_to_idx[professor_id]
                    section_to_prof.append([sec_idx, prof_idx])
        
        if section_to_prof:
            graph['section', 'assigned_to', 'professor'].edge_index = (
                torch.tensor(section_to_prof, dtype=torch.long).t().contiguous()
            )
        
        # Section -> Classroom (todas las combinaciones válidas)
        section_to_classroom = []
        for section in sections:
            sec_idx = self.section_id_to_idx[section.id]
            # Obtener la letra del tipo (LABORATORIO -> L, TEORIA -> T, PRACTICA -> P)
            tipo_section_key = (section.tipo or "")[0].upper() if section.tipo else ""
            stats = self.section_candidate_stats.setdefault(section.id, {
                "professors": 0,
                "classrooms": 0,
                "timeslots": 0,
            })
            classroom_count = 0
            
            for classroom in classrooms:
                # Normalizar tipo de aula
                tipo_aula_normalizado = self._normalize_classroom_type(classroom.tipo)
                
                # **FIX CRÍTICO**: Filtro de compatibilidad de tipo
                # - Si la sección es LABORATORIO (L), SOLO usar aulas tipo laboratorio
                # - Si la sección es TEORÍA (T), usar aulas tipo teorica o practica
                # - Si la sección es PRÁCTICA (P), usar aulas tipo teorica o practica
                if tipo_section_key == 'L' and tipo_aula_normalizado != 'laboratorio':
                    continue
                if tipo_section_key in ['T', 'P'] and tipo_aula_normalizado == 'laboratorio':
                    # Teoría y práctica NO usan laboratorios
                    continue
                
                # Filtrar por capacidad
                if classroom.capacidad < (section.alumnos_proyectados or 0):
                    continue
                
                classroom_idx = self.classroom_id_to_idx[classroom.id]
                section_to_classroom.append([sec_idx, classroom_idx])
                classroom_count += 1

            stats["classrooms"] = classroom_count
        
        if section_to_classroom:
            graph['section', 'uses', 'classroom'].edge_index = (
                torch.tensor(section_to_classroom, dtype=torch.long).t().contiguous()
            )
        
        # Section -> TimeSlot (bloques de inicio válidos)
        section_to_timeslot = []
        for section in sections:
            sec_idx = self.section_id_to_idx[section.id]
            duracion = self.section_durations[section.id]
            stats = self.section_candidate_stats.setdefault(section.id, {
                "professors": 0,
                "classrooms": 0,
                "timeslots": 0,
            })
            timeslot_count = 0
            
            for ts in timeslots:
                # Verificar que hay suficientes bloques consecutivos disponibles
                if self._has_consecutive_blocks(ts, duracion, timeslots):
                    ts_idx = self.timeslot_id_to_idx[ts.id]
                    section_to_timeslot.append([sec_idx, ts_idx])
                    timeslot_count += 1

            stats["timeslots"] = timeslot_count
        
        if section_to_timeslot:
            graph['section', 'starts_at', 'timeslot'].edge_index = (
                torch.tensor(section_to_timeslot, dtype=torch.long).t().contiguous()
            )
    
    def _add_curriculum_edges(self, graph: HeteroData, sections: List[CourseSection]):
        """
        Crea aristas de pertenencia a currículo.
        Section -> Curriculum: indica que la sección pertenece a ese ciclo.
        """
        section_to_curriculum = []
        
        for section in sections:
            ciclo = section.course.ciclo
            if ciclo and ciclo in self.curriculum_id_to_idx:
                sec_idx = self.section_id_to_idx[section.id]
                curr_idx = self.curriculum_id_to_idx[ciclo]
                section_to_curriculum.append([sec_idx, curr_idx])
        
        if section_to_curriculum:
            graph['section', 'belongs_to', 'curriculum'].edge_index = (
                torch.tensor(section_to_curriculum, dtype=torch.long).t().contiguous()
            )
    
    def _add_league_edges(self, graph: HeteroData, sections: List[CourseSection]):
        """
        Crea aristas entre secciones de la misma liga.
        Section <-> Section: indica coherencia de liga (no deben solaparse).
        """
        league_edges = []
        
        for (course_code, league_id), section_ids in self.sections_by_league.items():
            # Crear aristas entre todas las secciones de la misma liga
            for i, sec_id_1 in enumerate(section_ids):
                for sec_id_2 in section_ids[i+1:]:
                    idx_1 = self.section_id_to_idx[sec_id_1]
                    idx_2 = self.section_id_to_idx[sec_id_2]
                    league_edges.append([idx_1, idx_2])
                    league_edges.append([idx_2, idx_1])  # Bidireccional
        
        if league_edges:
            graph['section', 'same_league', 'section'].edge_index = (
                torch.tensor(league_edges, dtype=torch.long).t().contiguous()
            )
    
    def _add_professor_restriction_edges(
        self,
        graph: HeteroData,
        professors: List[Professor]
    ):
        """
        Crea aristas de restricción de profesor a franjas horarias.
        Professor -> TimeSlot: indica que el profesor NO está disponible.
        """
        prof_to_timeslot_restricted = []

        # Cachear franjas por día para evitar consultas repetidas
        timeslots_by_day: Dict[int, List[TimeSlot]] = {}
        for ts in self.db.query(TimeSlot).all():
            timeslots_by_day.setdefault(ts.dia_semana, []).append(ts)

        for prof in professors:
            prof_idx = self.professor_id_to_idx[prof.id]

            for restriction in prof.restrictions:
                restriction_day_num = self._normalize_day_of_week(restriction.day)
                if restriction_day_num == 0:
                    continue

                restriction_start = self._time_to_minutes(restriction.start_time)
                restriction_end = self._time_to_minutes(restriction.end_time)
                if restriction_start is None or restriction_end is None:
                    continue

                for ts in timeslots_by_day.get(restriction_day_num, []):
                    slot_start = self._time_to_minutes(ts.hora_inicio)
                    slot_end = self._time_to_minutes(ts.hora_fin)
                    if slot_start is None or slot_end is None:
                        continue
                    if self._ranges_overlap(slot_start, slot_end, restriction_start, restriction_end):
                        ts_idx = self.timeslot_id_to_idx.get(ts.id)
                        if ts_idx is not None:
                            prof_to_timeslot_restricted.append([prof_idx, ts_idx])
        
        if prof_to_timeslot_restricted:
            graph['professor', 'unavailable_at', 'timeslot'].edge_index = (
                torch.tensor(prof_to_timeslot_restricted, dtype=torch.long).t().contiguous()
            )
    
    # ========================================================================
    # UTILIDADES
    # ========================================================================
    
    def _has_consecutive_blocks(
        self,
        start_ts: TimeSlot,
        duracion: int,
        all_timeslots: List[TimeSlot]
    ) -> bool:
        """Verifica si existen bloques consecutivos desde start_ts"""
        if duracion <= 1:
            return True
        
        # Buscar bloques en el mismo día con orden consecutivo
        same_day_slots = [
            ts for ts in all_timeslots
            if ts.dia_semana == start_ts.dia_semana
        ]
        same_day_slots_sorted = sorted(same_day_slots, key=lambda ts: ts.orden)
        
        try:
            start_idx = same_day_slots_sorted.index(start_ts)
        except ValueError:
            return False
        
        # Verificar que hay suficientes slots consecutivos
        for i in range(duracion):
            if start_idx + i >= len(same_day_slots_sorted):
                return False
            expected_orden = start_ts.orden + i
            if same_day_slots_sorted[start_idx + i].orden != expected_orden:
                return False
        
        return True
    
    # ========================================================================
    # ASIGNACIONES DE PROFESORES
    # ========================================================================

    def _load_professor_assignments(self) -> None:
        """Carga asignaciones explicitas de profesores por curso, tipo y liga."""
        assign_by_league: Dict[Tuple[int, str, int], List[int]] = {}
        assign_by_type: Dict[Tuple[int, str], List[int]] = {}
        assign_by_course: Dict[int, List[int]] = {}

        result = self.db.execute(
            text(
                "SELECT course_id, professor_id, session_type, league "
                "FROM professor_course_assignments"
            )
        )

        for row in result:
            course_id = row.course_id
            professor_id = row.professor_id
            session_type = (row.session_type or "").upper()
            league = row.league or 1

            key_league = (course_id, session_type, league)
            key_type = (course_id, session_type)

            assign_by_league.setdefault(key_league, []).append(professor_id)
            assign_by_type.setdefault(key_type, []).append(professor_id)
            assign_by_course.setdefault(course_id, []).append(professor_id)

        self.prof_assign_by_league = assign_by_league
        self.prof_assign_by_type = assign_by_type
        self.prof_assign_by_course = assign_by_course

    def _candidate_professors_for_section(self, section: CourseSection) -> List[int]:
        """Obtiene profesores candidatos priorizando las asignaciones manuales."""
        course_id = section.course_id
        session_type = self._map_section_type(section)
        league = section.league or 1

        manual_candidates: Set[int] = set()

        if (course_id, session_type, league) in self.prof_assign_by_league:
            manual_candidates.update(
                self.prof_assign_by_league[(course_id, session_type, league)]
            )

        if (course_id, session_type) in self.prof_assign_by_type:
            manual_candidates.update(
                self.prof_assign_by_type[(course_id, session_type)]
            )

        if course_id in self.prof_assign_by_course:
            manual_candidates.update(self.prof_assign_by_course[course_id])

        if manual_candidates:
            return sorted(manual_candidates)

        # **FIX CRÍTICO (2024-10-18 v3)**: 
        # ELIMINADO el fallback a course.professors
        # Ahora SOLO se permiten profesores explícitamente asignados en professor_course_assignments
        # Esto garantiza 100% de respeto al mapeo manual
        # Si una sección no tiene asignaciones, NO tendrá candidatos y NO podrá ser asignada
        # (mejor que asignar un profesor incorrecto)
        
        return []  # Sin asignaciones manuales = sin candidatos

    def _map_section_type(self, section: CourseSection) -> str:
        return self._normalize_session_type(section.tipo)

    # ====================================================================
    # Normalización de datos provenientes de la BD
    # ====================================================================

    def _normalize_session_type(self, raw_type: Optional[str]) -> str:
        value = (raw_type or "").strip().lower()
        if value in {"t", "teoria", "teoría", "theory"}:
            return "T"
        if value in {"p", "practica", "práctica", "practice"}:
            return "P"
        if value in {"l", "lab", "laboratorio", "laboratory"}:
            return "L"
        if value in {"v", "virtual"}:
            return "V"
        return "T"

    def _normalize_classroom_type(self, raw_type: Optional[str]) -> str:
        value = (raw_type or "").strip().lower()
        if value in {"lab", "laboratorio", "laboratory"}:
            return "laboratorio"
        if value in {"practica", "práctica", "practice"}:
            return "practica"
        if value in {"nolab", "aula", "teorica", "teórica", "general"}:
            return "teorica"
        return "teorica"

    def _load_course_session_hours(self) -> None:
        try:
            result = self.db.execute(
                text(
                    "SELECT course_id, session_type, duration_minutes, duration_blocks "
                    "FROM course_session_hours"
                )
            )
        except Exception as exc:
            print(f"⚠️  No se pudieron cargar course_session_hours: {exc}")
            return

        for row in result:
            session_type = (row.session_type or "").strip().upper()
            if not session_type:
                continue
            minutes = row.duration_minutes
            blocks = getattr(row, "duration_blocks", None)
            if blocks is None or int(blocks or 0) <= 0:
                if minutes is None:
                    continue
                blocks = self._calculate_blocks_from_minutes(minutes)
            try:
                blocks_int = max(1, int(blocks))
            except (TypeError, ValueError):
                if minutes is None:
                    continue
                blocks_int = self._calculate_blocks_from_minutes(minutes)
            self.course_session_durations[(row.course_id, session_type)] = blocks_int

    def _calculate_blocks_from_minutes(self, minutes: Optional[int]) -> int:
        """Convierte una duración en minutos al número de bloques de 50m con descansos."""
        try:
            minutes_value = float(minutes)
        except (TypeError, ValueError):
            return 1

        if minutes_value <= 0:
            return 1

        # Cada bloque dura 50 minutos con descansos de 5 minutos entre bloques consecutivos.
        blocks = ceil((minutes_value + 5) / 55)
        return max(1, int(blocks))

    def _normalize_day_of_week(self, raw_day: Optional[str]) -> int:
        if not raw_day:
            return 0

        normalized = self._normalize_string(raw_day)
        mapping = {
            "monday": 1, "lunes": 1, "lun": 1,
            "tuesday": 2, "martes": 2, "mar": 2,
            "wednesday": 3, "miercoles": 3, "miércoles": 3, "mie": 3,
            "thursday": 4, "jueves": 4, "jue": 4,
        "friday": 5, "viernes": 5, "vie": 5,
        "saturday": 6, "sabado": 6, "sábado": 6, "sab": 6,
        }
        return mapping.get(normalized, 0)

    def _normalize_string(self, value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value)
        normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
        return normalized.lower().strip()

    def _time_to_minutes(self, value) -> Optional[int]:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            try:
                hours, minutes = value.split(":")
                return int(hours) * 60 + int(minutes)
            except ValueError:
                return None
        if hasattr(value, "hour") and hasattr(value, "minute"):
            return int(value.hour) * 60 + int(value.minute)
        if hasattr(value, "total_seconds"):
            return int(value.total_seconds() // 60)
        return None

    def _ranges_overlap(self, start_a: int, end_a: int, start_b: int, end_b: int) -> bool:
        return start_a < end_b and start_b < end_a
