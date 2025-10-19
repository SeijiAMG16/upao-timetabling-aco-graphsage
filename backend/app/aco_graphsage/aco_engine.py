"""
Motor ACO (Ant Colony Optimization) con Heurística Neural

Implementa el algoritmo de Colonia de Hormigas con integración de GraphSAGE.
Usa Max-Min Ant System (MMAS) para estabilidad.

Probabilidad de selección: P(i,j) ∝ [τ(i,j)]^α · [Φ(G,i,j)]^β

donde:
- τ(i,j): feromona de la arista
- Φ(G,i,j): heurística neural (GraphSAGE)
- α, β: pesos de importancia
"""

import numpy as np
import random
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
from collections import defaultdict
import torch
from torch_geometric.data import HeteroData
from datetime import datetime, time as time_cls

from .config import ACO_PARAMS
from .constraints import (
    Assignment,
    TimeSlotInfo,
    ClassroomInfo,
    ProfessorRestrictionInfo,
    HardConstraintValidator,
    SoftConstraintEvaluator,
)
from .graphsage_model import ACOGraphSAGEModel


# ============================================================================
# ESTRUCTURAS DE DATOS
# ============================================================================

@dataclass
class Solution:
    """Representa una solución completa (horario)"""
    assignments: List[Assignment]
    total_cost: float
    soft_penalties: Dict[str, float]
    is_valid: bool
    construction_log: List[str]


@dataclass
class PheromoneMatrix:
    """Matriz de feromonas para asignaciones"""
    # Estructura: {section_id: {(prof, classroom, timeslot): pheromone}}
    matrix: Dict[int, Dict[Tuple[int, int, int], float]]
    tau_min: float
    tau_max: float
    
    def __init__(self, tau_min: float, tau_max: float, tau_init: float):
        self.matrix = defaultdict(dict)
        self.tau_min = tau_min
        self.tau_max = tau_max
        self.tau_init = tau_init
    
    def get(self, section_id: int, assignment_key: Tuple[int, int, int]) -> float:
        """Obtiene el valor de feromona"""
        return self.matrix[section_id].get(assignment_key, self.tau_init)
    
    def set(self, section_id: int, assignment_key: Tuple[int, int, int], value: float):
        """Establece el valor de feromona (con límites MMAS)"""
        value = max(self.tau_min, min(self.tau_max, value))
        self.matrix[section_id][assignment_key] = value
    
    def evaporate(self, rho: float):
        """Evapora todas las feromonas"""
        for section_id in self.matrix:
            for key in self.matrix[section_id]:
                current = self.matrix[section_id][key]
                new_value = (1 - rho) * current
                self.matrix[section_id][key] = max(self.tau_min, new_value)


# ============================================================================
# MOTOR ACO
# ============================================================================

class ACOEngine:
    """Motor principal del algoritmo ACO con heurística neural"""
    
    def __init__(
        self,
        graph: HeteroData,
        model: ACOGraphSAGEModel,
        graph_builder,  # TimetableGraphBuilder instance
        hard_validator: HardConstraintValidator,
        soft_evaluator: SoftConstraintEvaluator,
        params: Dict = None,
    ):
        self.graph = graph
        self.model = model
        self.graph_builder = graph_builder
        self.hard_validator = hard_validator
        self.soft_evaluator = soft_evaluator
        
        # Parámetros (merge con defaults)
        self.params = {**ACO_PARAMS, **(params or {})}
        self.n_hormigas = self.params["n_hormigas"]
        self.n_iteraciones = self.params["n_iteraciones"]
        self.alpha = self.params["alpha"]
        self.beta = self.params["beta"]
        self.rho = self.params["rho"]
        self.q0 = self.params["q0"]

        # Debugging helpers
        debug_sections = self.params.get("debug_sections", []) or []
        if isinstance(debug_sections, (int, str)):
            debug_sections = [int(debug_sections)]
        self.debug_sections = {int(sec_id) for sec_id in debug_sections}
        self.debug_log_limit = int(self.params.get("debug_log_limit", 120))
        self._last_debug_logs: List[str] = []
        
        # Matriz de feromonas (MMAS)
        self.pheromones = PheromoneMatrix(
            tau_min=self.params["tau_min"],
            tau_max=self.params["tau_max"],
            tau_init=self.params["tau_init"],
        )
        
        # Estadísticas
        self.best_solution: Optional[Solution] = None
        self.iteration_best: List[float] = []
        self.iteration_avg: List[float] = []
        self.completed_iterations: int = 0
        
        # Cache de candidatos por sección
        self._candidate_cache: Dict[int, List[Tuple[int, int, int]]] = {}
        
        # OPTIMIZACIÓN: Cache de validaciones para evitar re-validar
        self._validation_cache: Dict[Tuple[int, int, int, int, frozenset], bool] = {}
        
        # OPTIMIZACIÓN: Contador de iteraciones sin mejora para early stopping
        self._iterations_without_improvement = 0
        self._max_iterations_without_improvement = self.params.get("early_stopping_patience", 12)

        # OPTIMIZACIÓN: Acceso O(1) a bloques consecutivos por día/orden
        self._timeslot_lookup = {
            (ts.dia_semana, ts.orden): ts_id
            for ts_id, ts in self.hard_validator.timeslots.items()
        }
    
    def optimize(self, max_iterations: int = None) -> Solution:
        """
        Ejecuta el algoritmo ACO completo.
        
        Args:
            max_iterations: Número máximo de iteraciones (override)
        
        Returns:
            Mejor solución encontrada
        """
        n_iters = max_iterations or self.n_iteraciones
        self.completed_iterations = 0
        
        print(f"\n{'='*80}")
        print(f"Iniciando ACO con {self.n_hormigas} hormigas, {n_iters} iteraciones")
        print(f"Alpha={self.alpha}, Beta={self.beta}, Rho={self.rho}, Q0={self.q0}")
        print(f"{'='*80}\n")
        
        for iteration in range(n_iters):
            iteration_index = iteration + 1
            # Construir soluciones con todas las hormigas
            solutions = []
            for ant_id in range(self.n_hormigas):
                solution = self._construct_solution(ant_id, iteration)
                if solution.is_valid:
                    solutions.append(solution)
            
            if not solutions:
                print(f"Iteración {iteration_index}/{n_iters}: ⚠️  No se encontraron soluciones válidas")
                self.completed_iterations = iteration_index
                continue
            
            # Encontrar mejor de esta iteración
            iteration_best_solution = min(solutions, key=lambda s: s.total_cost)
            avg_cost = sum(s.total_cost for s in solutions) / len(solutions)
            
            self.iteration_best.append(iteration_best_solution.total_cost)
            self.iteration_avg.append(avg_cost)
            
            # Actualizar mejor global
            if self.best_solution is None or iteration_best_solution.total_cost < self.best_solution.total_cost:
                self.best_solution = iteration_best_solution
                self._iterations_without_improvement = 0  # Reset contador
                print(f"Iteración {iteration_index}/{n_iters}: ✅ Nueva mejor solución: {self.best_solution.total_cost:.2f}")
            else:
                self._iterations_without_improvement += 1
                print(f"Iteración {iteration_index}/{n_iters}: Mejor={iteration_best_solution.total_cost:.2f}, "
                      f"Avg={avg_cost:.2f}, Global={self.best_solution.total_cost:.2f}")
            
            self.completed_iterations = iteration_index
            
            # OPTIMIZACIÓN: Early stopping si no hay mejoras
            if self._iterations_without_improvement >= self._max_iterations_without_improvement:
                print(f"\n⚠️  Early stopping: No hay mejoras en {self._max_iterations_without_improvement} iteraciones")
                break
            
            # Evaporar feromonas
            self.pheromones.evaporate(self.rho)
            
            # Actualizar feromonas (elitista: mejor iteración + mejor global)
            self._update_pheromones(iteration_best_solution, weight=1.0 - self.params["elitist_weight"])
            self._update_pheromones(self.best_solution, weight=self.params["elitist_weight"])
        
        print(f"\n{'='*80}")
        if self.best_solution is not None:
            print(f"✅ Optimización completada. Costo final: {self.best_solution.total_cost:.2f}")
        else:
            print(f"⚠️  Optimización completada SIN soluciones válidas encontradas")
        print(f"{'='*80}\n")
        
        return self.best_solution
    
    def _construct_solution(self, ant_id: int, iteration: int) -> Solution:
        """
        Construye una solución completa usando una hormiga.
        
        Proceso:
        1. Ordenar secciones por prioridad
        2. Para cada sección, seleccionar asignación usando feromona + heurística
        3. Validar restricciones duras en cada paso
        4. Calcular costo final con restricciones blandas
        """
        assignments = []
        construction_log = []
        
        # Obtener todas las secciones a asignar
        section_ids = list(self.graph_builder.section_id_to_idx.keys())

        # Agrupar por curso+liga para respetar secuencia pedagógica T -> P -> L
        type_order = {"T": 0, "P": 1, "L": 2, "V": 3}
        grouped_sections: Dict[Tuple[Optional[str], Optional[int]], List[int]] = defaultdict(list)
        for sec_id in section_ids:
            metadata = self.graph_builder.section_metadata.get(sec_id, {})
            course_code = metadata.get("course_code")
            league = metadata.get("league")
            key = (course_code, league)
            if course_code is None and league is None:
                key = ("__UNCLUSTERED__", sec_id)
            grouped_sections[key].append(sec_id)

        def group_sort_key(group_key: Tuple[Optional[str], Optional[int]]) -> Tuple[str, int]:
            course, league = group_key
            course_key = course or ""
            league_key = league if isinstance(league, int) else 0
            return (course_key, league_key)

        sorted_section_ids: List[int] = []
        
        # PRIORIDAD ESPECIAL: Grupos de cursos que necesitan asignarse primero
        # Configurable via parámetros
        priority_groups = self.params.get("priority_course_groups", [("CIEN769", 1)])
        
        # Separar grupos prioritarios del resto
        priority_section_groups = []
        regular_section_groups = []
        
        for group_key in sorted(grouped_sections.keys(), key=group_sort_key):
            course_code, league = group_key
            if (course_code, league) in priority_groups:
                priority_section_groups.append((group_key, grouped_sections[group_key]))
            else:
                regular_section_groups.append((group_key, grouped_sections[group_key]))
        
        # Procesar grupos prioritarios primero
        all_groups = priority_section_groups + regular_section_groups
        
        for group_key, sections in all_groups:

            def section_priority(sec_id: int) -> Tuple[int, int, int, int]:
                duration = self.graph_builder.section_durations.get(sec_id, 1)
                projected = self.graph_builder.section_projected_students.get(sec_id, 0)
                metadata = self.graph_builder.section_metadata.get(sec_id, {})
                session_type = (metadata.get("session_type") or "T").upper()
                priority = type_order.get(session_type, 99)
                return (priority, -duration, -projected, sec_id)

            sections.sort(key=section_priority)
            sorted_section_ids.extend(sections)
        
        # Construir asignaciones una por una
        for sec_id in sorted_section_ids:
            assignment = self._assign_section(sec_id, assignments, ant_id)
            
            if assignment is None:
                # No se pudo asignar esta sección
                construction_log.append(f"❌ No se pudo asignar sección {sec_id}")
                if self._last_debug_logs:
                    construction_log.extend(self._last_debug_logs)
                else:
                    construction_log.append(
                        "(sin detalles porque la sección no estaba en debug_sections)"
                    )
                preview = "\n      ".join(construction_log[-min(len(construction_log), 20):])
                print(
                    f"[Diagnóstico ACO] Iteración {iteration + 1}, hormiga {ant_id} detuvo la construcción en la sección {sec_id}.\n"
                    f"      Historial reciente:\n      {preview}"
                )
                # Marcar solución como inválida
                return Solution(
                    assignments=assignments,
                    total_cost=float('inf'),
                    soft_penalties={},
                    is_valid=False,
                    construction_log=construction_log,
                )
            
            assignments.append(assignment)
            construction_log.append(f"✅ Asignada sección {sec_id}")
            if self._last_debug_logs:
                construction_log.extend(self._last_debug_logs)
        
        # Calcular costo con restricciones blandas
        total_cost, penalties = self.soft_evaluator.calculate_total_penalty(assignments)
        
        return Solution(
            assignments=assignments,
            total_cost=total_cost,
            soft_penalties=penalties,
            is_valid=True,
            construction_log=construction_log,
        )
    
    def _assign_section(
        self,
        section_id: int,
        current_schedule: List[Assignment],
        ant_id: int,
    ) -> Optional[Assignment]:
        """
        Asigna una sección usando feromona + heurística neural.
        
        Returns:
            Assignment si se pudo asignar, None si no hay opciones válidas
        """
        self._last_debug_logs = []
        debug_enabled = section_id in self.debug_sections

        def debug(message: str):
            if debug_enabled and len(self._last_debug_logs) < self.debug_log_limit:
                self._last_debug_logs.append(message)

        # Obtener candidatos válidos (cachear para eficiencia)
        if section_id not in self._candidate_cache:
            candidates = self._get_candidate_assignments(section_id)
            
            # MANEJO ESPECIAL: Para cursos virtuales (NO_PRESENCIAL), si no hay candidatos 
            # del grafo (porque no tienen aristas section→classroom), generar candidatos especiales
            if not candidates:
                metadata_check = self.graph_builder.section_metadata.get(section_id, {})
                modalidad_check = metadata_check.get("modalidad", "").upper()
                if modalidad_check == "NO_PRESENCIAL":
                    # Generar candidatos sin aula (classroom_idx = -1)
                    candidates = self._generate_virtual_candidates(section_id)
            
            self._candidate_cache[section_id] = candidates
        else:
            candidates = self._candidate_cache[section_id]
        
        debug(f"🔍 Sección {section_id}: {len(candidates)} candidatos iniciales")

        if not candidates:
            debug("🚫 No se encontraron combinaciones profesor/aula/horario desde el grafo")
            return None
        
        # OPTIMIZACIÓN: Crear conjunto de recursos ocupados para validación rápida
        metadata = self.graph_builder.section_metadata.get(section_id, {})
        course_code = metadata.get("course_code") or f"SECTION-{section_id}"
        league_id = metadata.get("league") or 1
        ciclo = metadata.get("ciclo") or "SIN-CICLO"
        projected_students = self.graph_builder.section_projected_students.get(section_id, 0)
        session_type = (metadata.get("session_type") or "T").upper()
        modalidad = metadata.get("modalidad", "").upper()
        
        # MANEJO ESPECIAL: Cursos virtuales NO_PRESENCIAL no necesitan aula física
        is_virtual = modalidad == "NO_PRESENCIAL"
        if is_virtual:
            debug(f"🌐 Sección {section_id} es VIRTUAL (NO_PRESENCIAL) - no requiere aula física")

        # Enforzar T -> P -> L: si falta teoría/práctica previas, diferir esta asignación
        league_key = (course_code, league_id)
        if session_type in {"P", "L"}:
            predecessors = {"T"} if session_type == "P" else {"T", "P"}
            assigned_section_ids = {
                assignment.section_id
                for assignment in current_schedule
                if assignment.course_code == course_code and assignment.league_id == league_id
            }
            pending_predecessors = [
                sec
                for sec in self.hard_validator.sections_by_league.get(league_key, [])
                if (
                    self.hard_validator.section_session_types.get(sec, "").upper() in predecessors
                    and sec not in assigned_section_ids
                )
            ]
            if pending_predecessors:
                debug(
                    f"⏳ Pendiente asignar secciones {pending_predecessors} antes de programar {section_id}"
                )
                return None

        occupied_timeslots_by_prof: Dict[int, Set[int]] = {}
        occupied_timeslots_by_classroom: Dict[int, Set[int]] = {}
        curriculum_slots: Dict[Tuple[str, int], Tuple[str, int]] = {}
        league_slots: Dict[Tuple[str, int], Set[int]] = defaultdict(set)
        
        for existing in current_schedule:
            # Profesores ocupados
            if existing.professor_id not in occupied_timeslots_by_prof:
                occupied_timeslots_by_prof[existing.professor_id] = set()
            occupied_timeslots_by_prof[existing.professor_id].update(existing.timeslot_ids)
            
            # Aulas ocupadas (SOLO para cursos presenciales)
            if existing.classroom_id is not None:
                if existing.classroom_id not in occupied_timeslots_by_classroom:
                    occupied_timeslots_by_classroom[existing.classroom_id] = set()
                occupied_timeslots_by_classroom[existing.classroom_id].update(existing.timeslot_ids)

            for ts_id in existing.timeslot_ids:
                curriculum_slots[(existing.ciclo, ts_id)] = (existing.course_code, existing.league_id)
                league_slots[(existing.course_code, existing.league_id)].add(ts_id)
        
        # Filtrar candidatos que violan restricciones duras
        valid_candidates = []
        candidate_timeslots: Dict[Tuple[int, int, int], List[int]] = {}
        for prof_idx, classroom_idx, timeslot_idx in candidates:
            # OPTIMIZACIÓN: Validación rápida de conflictos básicos antes de construir Assignment
            professor_id = self.graph_builder.idx_to_professor_id[prof_idx]
            
            # Manejo especial para cursos virtuales (classroom_idx == -1)
            if classroom_idx == -1:
                classroom_id = None  # Sin aula física
                is_virtual_candidate = True
            else:
                classroom_id = self.graph_builder.idx_to_classroom_id[classroom_idx]
                is_virtual_candidate = False
            
            timeslot_start_id = self.graph_builder.idx_to_timeslot_id[timeslot_idx]
            
            # Obtener duración
            duracion = self.graph_builder.section_durations.get(section_id, 1)
            
            # Buscar bloques consecutivos necesarios
            start_ts = self.hard_validator.timeslots[timeslot_start_id]
            timeslot_sequence = self._get_consecutive_timeslots(
                start_ts.dia_semana,
                start_ts.orden,
                duracion,
            )
            
            if not timeslot_sequence or timeslot_sequence[0] != timeslot_start_id:
                debug(
                    f"✂️  Bloques insuficientes (duración {duracion}) para prof {professor_id}, aula {classroom_id}, inicio {timeslot_start_id}"
                )
                continue  # No hay bloques consecutivos suficientes
            
            # OPTIMIZACIÓN: Validación rápida de conflictos
            needed_slots_set = set(timeslot_sequence)

            # Validación rápida: capacidad del aula (SOLO para cursos presenciales)
            if not is_virtual_candidate:
                classroom_info = self.hard_validator.classrooms.get(classroom_id)
                if classroom_info and classroom_info.capacidad is not None and projected_students:
                    if projected_students > classroom_info.capacidad:
                        debug(
                            f"🚷 Capacidad insuficiente aula {classroom_id} ({projected_students}>{classroom_info.capacidad})"
                        )
                        continue

            # Validación rápida: conflictos curriculares (mismo ciclo)
            has_curriculum_conflict = False
            for ts_id in timeslot_sequence:
                existing_course_league = curriculum_slots.get((ciclo, ts_id))
                if existing_course_league is None:
                    continue

                existing_course, existing_league = existing_course_league

                # Si coincide el mismo curso, dejamos que coherencia de liga maneje el solape.
                if existing_course == course_code:
                    continue

                # Replicar la lógica del validador duro: solo bloquear si la liga coincide
                # (o si alguna liga es desconocida).
                if league_id is None or existing_league is None:
                    relevant_overlap = True
                else:
                    relevant_overlap = existing_league == league_id

                if not relevant_overlap:
                    continue

                has_curriculum_conflict = True
                debug(
                    f"🎓 Conflicto curricular en ciclo {ciclo} con curso {existing_course} liga {existing_league} en franja {ts_id}"
                )
                break
            if has_curriculum_conflict:
                continue

            # Validación rápida: coherencia de liga (misma liga no se solapa)
            league_key = (course_code, league_id)
            if league_slots.get(league_key) and league_slots[league_key] & needed_slots_set:
                debug(
                    f"🏷️  Cruce con liga {league_key} en franjas {sorted(league_slots[league_key] & needed_slots_set)}"
                )
                continue
            
            # Check profesor ocupado
            if professor_id in occupied_timeslots_by_prof:
                if occupied_timeslots_by_prof[professor_id] & needed_slots_set:
                    debug(
                        f"👨‍🏫 Profesor {professor_id} ocupado en franjas {sorted(occupied_timeslots_by_prof[professor_id] & needed_slots_set)}"
                    )
                    continue  # Profesor ya ocupado en estos horarios
            
            # Check aula ocupada (SOLO para cursos presenciales)
            if not is_virtual_candidate and classroom_id in occupied_timeslots_by_classroom:
                if occupied_timeslots_by_classroom[classroom_id] & needed_slots_set:
                    debug(
                        f"🏫 Aula {classroom_id} ocupada en franjas {sorted(occupied_timeslots_by_classroom[classroom_id] & needed_slots_set)}"
                    )
                    continue  # Aula ya ocupada
            
            # OPTIMIZACIÓN: Usar caché de validación completa
            schedule_fingerprint = frozenset((a.section_id, a.professor_id, a.classroom_id, tuple(a.timeslot_ids)) 
                                            for a in current_schedule[-5:])  # REDUCIDO: Solo últimas 5 para más velocidad
            cache_key = (section_id, professor_id, classroom_id, timeslot_start_id, schedule_fingerprint)
            
            if cache_key in self._validation_cache:
                if self._validation_cache[cache_key]:
                    candidate_key = (prof_idx, classroom_idx, timeslot_idx)
                    valid_candidates.append(candidate_key)
                    candidate_timeslots[candidate_key] = timeslot_sequence
                continue
            
            # Construir Assignment solo si pasó validaciones rápidas
            assignment = self._build_assignment_object(
                section_id,
                prof_idx,
                classroom_idx,
                timeslot_idx,
                precomputed_timeslots=timeslot_sequence,
            )
            
            # Validación completa
            is_valid, error = self.hard_validator.validate_all(assignment, current_schedule)
            
            # Guardar en caché
            self._validation_cache[cache_key] = is_valid
            
            if is_valid:
                candidate_key = (prof_idx, classroom_idx, timeslot_idx)
                valid_candidates.append(candidate_key)
                candidate_timeslots[candidate_key] = timeslot_sequence
                debug(
                    f"✅ Candidato válido con prof {professor_id}, aula {classroom_id}, franjas {timeslot_sequence}"
                )
            else:
                debug(
                    f"⛔️ Validación dura falló para prof {professor_id}, aula {classroom_id}, franjas {timeslot_sequence}: {error}"
                )
        
        if not valid_candidates:
            debug("🚫 Sin candidatos válidos tras validaciones duras")
            return None
        
        # Seleccionar usando feromona + heurística (regla de transición ACO)
        selected = self._select_assignment(section_id, valid_candidates, ant_id)
        
        # Construir Assignment final
        prof_id = self.graph_builder.idx_to_professor_id[selected[0]]
        classroom_id_str = "VIRTUAL (sin aula)" if selected[1] == -1 else str(self.graph_builder.idx_to_classroom_id[selected[1]])
        timeslot_id = self.graph_builder.idx_to_timeslot_id[selected[2]]
        
        debug(
            f"⭐ Sección {section_id} asignada con prof {prof_id}, "
            f"aula {classroom_id_str}, franja inicial {timeslot_id}"
        )
        return self._build_assignment_object(
            section_id,
            selected[0],
            selected[1],
            selected[2],
            precomputed_timeslots=candidate_timeslots.get(selected),
        )
    
    def _get_candidate_assignments(
        self,
        section_id: int,
    ) -> List[Tuple[int, int, int]]:
        """
        Obtiene las asignaciones candidatas para una sección.
        
        Basado en las aristas del grafo:
        - section -> professor
        - section -> classroom
        - section -> timeslot
        
        Returns:
            Lista de (prof_idx, classroom_idx, timeslot_idx)
        """
        sec_idx = self.graph_builder.section_id_to_idx[section_id]
        
        # Obtener profesores candidatos (desde aristas del grafo)
        if ('section', 'assigned_to', 'professor') in self.graph.edge_index_dict:
            section_to_prof_edges = self.graph[('section', 'assigned_to', 'professor')].edge_index
            prof_candidates = section_to_prof_edges[1][section_to_prof_edges[0] == sec_idx].tolist()
        else:
            prof_candidates = []
        
        # Obtener aulas candidatas
        if ('section', 'uses', 'classroom') in self.graph.edge_index_dict:
            section_to_classroom_edges = self.graph[('section', 'uses', 'classroom')].edge_index
            classroom_candidates = section_to_classroom_edges[1][section_to_classroom_edges[0] == sec_idx].tolist()
        else:
            classroom_candidates = []
        
        # Obtener franjas candidatas (bloques de inicio)
        if ('section', 'starts_at', 'timeslot') in self.graph.edge_index_dict:
            section_to_timeslot_edges = self.graph[('section', 'starts_at', 'timeslot')].edge_index
            timeslot_candidates = section_to_timeslot_edges[1][section_to_timeslot_edges[0] == sec_idx].tolist()
        else:
            timeslot_candidates = []
        
        # Producto cartesiano (limitado para eficiencia)
        candidates: List[Tuple[int, int, int]] = []

        # Opcional: mezclar candidatos para repartir carga entre hormigas
        if self.params.get("shuffle_candidates", True):
            random.shuffle(prof_candidates)
            random.shuffle(classroom_candidates)
            random.shuffle(timeslot_candidates)

        max_profs = min(
            len(prof_candidates),
            self.params.get("max_professors_per_section", len(prof_candidates)),
        )
        max_classrooms = min(
            len(classroom_candidates),
            self.params.get("max_classrooms_per_section", len(classroom_candidates)),
        )

        # Escalar la cuota de franjas según la duración para evitar que sesiones largas
        # exploren únicamente los primeros bloques y fallen por conflictos triviales.
        base_timeslot_limit = self.params.get("max_timeslots_per_section")
        if base_timeslot_limit is None or base_timeslot_limit <= 0:
            max_timeslots = len(timeslot_candidates)
        else:
            duration = max(1, self.graph_builder.section_durations.get(section_id, 1))
            scaled_limit = base_timeslot_limit * duration
            max_timeslots = min(len(timeslot_candidates), scaled_limit)

        if max_profs == 0 or max_classrooms == 0 or max_timeslots == 0:
            return candidates

        total_possible = max_profs * max_classrooms * max_timeslots
        requested_max = self.params.get("max_candidate_combinations", 1200)
        if requested_max is None or requested_max <= 0:
            max_candidates = total_possible
        else:
            max_candidates = max(1, min(requested_max, total_possible))

        per_prof_base = max_candidates // max_profs
        remainder = max_candidates % max_profs

        classroom_subset = classroom_candidates[:max_classrooms]
        timeslot_subset = timeslot_candidates[:max_timeslots]

        for idx, prof_idx in enumerate(prof_candidates[:max_profs]):
            quota = per_prof_base + (1 if idx < remainder else 0)
            if quota == 0:
                continue

            added = 0
            for classroom_idx in classroom_subset:
                for timeslot_idx in timeslot_subset:
                    candidates.append((prof_idx, classroom_idx, timeslot_idx))
                    added += 1
                    if len(candidates) >= max_candidates:
                        return candidates
                    if added >= quota:
                        break
                if len(candidates) >= max_candidates or added >= quota:
                    break

        return candidates
    
    def _generate_virtual_candidates(
        self,
        section_id: int,
    ) -> List[Tuple[int, int, int]]:
        """
        Genera candidatos para cursos virtuales (NO_PRESENCIAL).
        Estos cursos necesitan profesor y horario, pero NO aula física.
        
        Usamos -1 como índice especial de aula para indicar "sin aula".
        
        Returns:
            Lista de (prof_idx, -1, timeslot_idx)
        """
        sec_idx = self.graph_builder.section_id_to_idx[section_id]
        
        # Obtener profesores candidatos (desde aristas del grafo)
        if ('section', 'assigned_to', 'professor') in self.graph.edge_index_dict:
            section_to_prof_edges = self.graph[('section', 'assigned_to', 'professor')].edge_index
            prof_candidates = section_to_prof_edges[1][section_to_prof_edges[0] == sec_idx].tolist()
        else:
            prof_candidates = []
        
        # Obtener franjas candidatas
        if ('section', 'starts_at', 'timeslot') in self.graph.edge_index_dict:
            section_to_timeslot_edges = self.graph[('section', 'starts_at', 'timeslot')].edge_index
            timeslot_candidates = section_to_timeslot_edges[1][section_to_timeslot_edges[0] == sec_idx].tolist()
        else:
            timeslot_candidates = []
        
        # Producto cartesiano prof × timeslot (sin aula)
        candidates: List[Tuple[int, int, int]] = []
        
        if self.params.get("shuffle_candidates", True):
            random.shuffle(prof_candidates)
            random.shuffle(timeslot_candidates)
        
        max_profs = min(
            len(prof_candidates),
            self.params.get("max_professors_per_section", len(prof_candidates)),
        )
        
        base_timeslot_limit = self.params.get("max_timeslots_per_section")
        if base_timeslot_limit is None or base_timeslot_limit <= 0:
            max_timeslots = len(timeslot_candidates)
        else:
            duration = max(1, self.graph_builder.section_durations.get(section_id, 1))
            scaled_limit = base_timeslot_limit * duration
            max_timeslots = min(len(timeslot_candidates), scaled_limit)
        
        # Para cursos virtuales, usamos -1 como índice de "sin aula"
        VIRTUAL_CLASSROOM_IDX = -1
        
        for prof_idx in prof_candidates[:max_profs]:
            for timeslot_idx in timeslot_candidates[:max_timeslots]:
                candidates.append((prof_idx, VIRTUAL_CLASSROOM_IDX, timeslot_idx))
        
        return candidates
    
    def _get_virtual_candidates(
        self,
        section_id: int,
    ) -> List[Tuple[int, int, int]]:
        """
        Genera candidatos para cursos virtuales (NO_PRESENCIAL).
        Estos cursos necesitan profesor y horario, pero NO aula física.
        
        Usamos -1 como índice especial de aula para indicar "sin aula".
        
        Returns:
            Lista de (prof_idx, -1, timeslot_idx)
        """
        sec_idx = self.graph_builder.section_id_to_idx[section_id]
        
        # Obtener profesores candidatos (desde aristas del grafo)
        if ('section', 'assigned_to', 'professor') in self.graph.edge_index_dict:
            section_to_prof_edges = self.graph[('section', 'assigned_to', 'professor')].edge_index
            prof_candidates = section_to_prof_edges[1][section_to_prof_edges[0] == sec_idx].tolist()
        else:
            prof_candidates = []
        
        # Obtener franjas candidatas
        if ('section', 'starts_at', 'timeslot') in self.graph.edge_index_dict:
            section_to_timeslot_edges = self.graph[('section', 'starts_at', 'timeslot')].edge_index
            timeslot_candidates = section_to_timeslot_edges[1][section_to_timeslot_edges[0] == sec_idx].tolist()
        else:
            timeslot_candidates = []
        
        # Producto cartesiano prof × timeslot (sin aula)
        candidates: List[Tuple[int, int, int]] = []
        
        if self.params.get("shuffle_candidates", True):
            random.shuffle(prof_candidates)
            random.shuffle(timeslot_candidates)
        
        max_profs = min(
            len(prof_candidates),
            self.params.get("max_professors_per_section", len(prof_candidates)),
        )
        
        base_timeslot_limit = self.params.get("max_timeslots_per_section")
        if base_timeslot_limit is None or base_timeslot_limit <= 0:
            max_timeslots = len(timeslot_candidates)
        else:
            duration = max(1, self.graph_builder.section_durations.get(section_id, 1))
            scaled_limit = base_timeslot_limit * duration
            max_timeslots = min(len(timeslot_candidates), scaled_limit)
        
        # Para cursos virtuales, usamos -1 como índice de "sin aula"
        VIRTUAL_CLASSROOM_IDX = -1
        
        for prof_idx in prof_candidates[:max_profs]:
            for timeslot_idx in timeslot_candidates[:max_timeslots]:
                candidates.append((prof_idx, VIRTUAL_CLASSROOM_IDX, timeslot_idx))
        
        return candidates
    
    def _select_assignment(
        self,
        section_id: int,
        candidates: List[Tuple[int, int, int]],
        ant_id: int,
    ) -> Tuple[int, int, int]:
        """
        Selecciona una asignación usando la regla de transición ACO.
        
        Con probabilidad q0: elegir la mejor (explotación)
        Con probabilidad 1-q0: elegir probabilísticamente (exploración)
        """
        # Obtener valores de feromona
        pheromones = np.array([
            self.pheromones.get(section_id, candidate)
            for candidate in candidates
        ])
        
        # Obtener heurística neural
        sec_idx = self.graph_builder.section_id_to_idx[section_id]
        heuristics = self.model.get_heuristic_matrix(self.graph, sec_idx, candidates)
        
        # Calcular probabilidades: P ∝ τ^α · η^β
        values = (pheromones ** self.alpha) * (heuristics ** self.beta)
        
        # Evitar división por cero
        if values.sum() == 0:
            values = np.ones_like(values)
        
        probabilities = values / values.sum()
        
        # Regla de transición
        if random.random() < self.q0:
            # Explotación: elegir el mejor
            selected_idx = np.argmax(probabilities)
        else:
            # Exploración: muestreo probabilístico
            selected_idx = np.random.choice(len(candidates), p=probabilities)
        
        return candidates[selected_idx]

    def _get_consecutive_timeslots(self, day: int, start_order: int, duration: int) -> Optional[List[int]]:
        """Obtiene una secuencia de bloques consecutivos para una sección."""
        timeslot_ids = []
        for offset in range(duration):
            ts_id = self._timeslot_lookup.get((day, start_order + offset))
            if ts_id is None:
                return None
            timeslot_ids.append(ts_id)
        return timeslot_ids
    
    def _build_assignment_object(
        self,
        section_id: int,
        prof_idx: int,
        classroom_idx: int,
        timeslot_start_idx: int,
        precomputed_timeslots: Optional[List[int]] = None,
    ) -> Assignment:
        """
        Construye un objeto Assignment completo desde índices.
        
        Incluye la búsqueda de bloques consecutivos según duración.
        """
        # Mapear índices a IDs reales
        professor_id = self.graph_builder.idx_to_professor_id[prof_idx]
        
        # Manejo especial para cursos virtuales (classroom_idx == -1)
        if classroom_idx == -1:
            classroom_id = None  # Sin aula física para cursos virtuales
        else:
            classroom_id = self.graph_builder.idx_to_classroom_id[classroom_idx]
        
        timeslot_start_id = self.graph_builder.idx_to_timeslot_id[timeslot_start_idx]
        
        # Obtener duración
        duracion = self.graph_builder.section_durations.get(section_id, 1)
        
        # Buscar bloques consecutivos
        start_ts = self.hard_validator.timeslots[timeslot_start_id]
        if precomputed_timeslots is not None:
            timeslot_ids = list(precomputed_timeslots)
        else:
            timeslot_sequence = self._get_consecutive_timeslots(
                start_ts.dia_semana,
                start_ts.orden,
                duracion,
            )
            timeslot_ids = timeslot_sequence or [timeslot_start_id]
        
        # Obtener información adicional desde el graph builder
        metadata = self.graph_builder.section_metadata.get(section_id, {})
        course_code = metadata.get("course_code") or f"SECTION-{section_id}"
        session_type = (metadata.get("session_type") or "T").upper()
        league_id = metadata.get("league") or 1
        ciclo = metadata.get("ciclo") or "SIN-CICLO"
        alumnos_proyectados = self.graph_builder.section_projected_students.get(section_id, 0)
        original_section_id = metadata.get("original_section_id", section_id)
        split_group_index = metadata.get("split_group_index", 0)
        split_group_count = metadata.get("split_group_count", 1)
        block_id = metadata.get("block_id")
        franja_index = metadata.get("franja_index")
        
        return Assignment(
            section_id=section_id,
            professor_id=professor_id,
            classroom_id=classroom_id,
            timeslot_ids=timeslot_ids,
            course_code=course_code,
            session_type=session_type,
            league_id=league_id,
            ciclo=ciclo,
            alumnos_proyectados=alumnos_proyectados,
            original_section_id=original_section_id,
            split_group_index=split_group_index,
            split_group_count=split_group_count,
            block_id=block_id,
            franja_index=franja_index,
        )
    
    def _update_pheromones(self, solution: Solution, weight: float = 1.0):
        """
        Actualiza las feromonas basándose en una solución.
        
        Deposita más feromona en asignaciones de soluciones mejores.
        """
        if not solution.is_valid:
            return
        
        # Calcular cantidad de feromona a depositar (inverso del costo)
        delta_tau = weight / (1.0 + solution.total_cost)
        
        for assignment in solution.assignments:
            # Convertir a índices
            prof_idx = self.graph_builder.professor_id_to_idx[assignment.professor_id]
            
            # Manejo especial para cursos virtuales sin aula
            if assignment.classroom_id is None:
                classroom_idx = -1  # Usar -1 como índice especial
            else:
                classroom_idx = self.graph_builder.classroom_id_to_idx[assignment.classroom_id]
            
            timeslot_idx = self.graph_builder.timeslot_id_to_idx[assignment.timeslot_ids[0]]
            
            key = (prof_idx, classroom_idx, timeslot_idx)
            
            current = self.pheromones.get(assignment.section_id, key)
            new_value = current + delta_tau
            self.pheromones.set(assignment.section_id, key, new_value)


# ============================================================================
# UTILIDADES
# ============================================================================

def create_aco_engine(
    graph: HeteroData,
    model: ACOGraphSAGEModel,
    graph_builder,
    db_session,
    params: Dict = None,
) -> ACOEngine:
    """
    Factory function para crear un ACOEngine configurado.
    
    Args:
        graph: Grafo heterogéneo
        model: Modelo GraphSAGE entrenado
        graph_builder: Instancia de TimetableGraphBuilder
        db_session: Sesión de base de datos para cargar restricciones
        params: Parámetros ACO (opcional)
    
    Returns:
        ACOEngine configurado y listo para optimizar
    """
    from app.models import TimeSlot, Classroom, ProfessorRestriction

    def _parse_time(value) -> Optional[time_cls]:
        if value is None:
            return None
        if isinstance(value, time_cls):
            return value
        if isinstance(value, str):
            try:
                return datetime.strptime(value, "%H:%M").time()
            except ValueError:
                return None
        if hasattr(value, "total_seconds"):
            total_seconds = int(value.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes = (remainder // 60) % 60
            hours = hours % 24
            return time_cls(hour=hours, minute=minutes)
        if hasattr(value, "hour") and hasattr(value, "minute"):
            return time_cls(hour=int(value.hour) % 24, minute=int(value.minute) % 60)
        return None
    
    # Cargar información de BD
    timeslots_db = db_session.query(TimeSlot).all()
    classrooms_db = db_session.query(Classroom).all()
    restrictions_db = db_session.query(ProfessorRestriction).all()
    
    # Convertir a estructuras de constraints.py
    timeslots = {
        ts.id: TimeSlotInfo(
            id=ts.id,
            dia_semana=ts.dia_semana,
            hora_inicio=_parse_time(ts.hora_inicio),
            hora_fin=_parse_time(ts.hora_fin),
            orden=ts.orden,
            periodo=ts.periodo,
        )
        for ts in timeslots_db
    }
    
    classrooms = {
        c.id: ClassroomInfo(
            id=c.id,
            codigo=c.codigo,
            capacidad=c.capacidad,
            tipo=graph_builder._normalize_classroom_type(c.tipo),
            edificio=c.edificio,
            tiene_computadoras=c.tiene_computadoras,
        )
        for c in classrooms_db
    }
    
    professor_restrictions = defaultdict(list)
    for r in restrictions_db:
        day_num = graph_builder._normalize_day_of_week(r.day)
        if day_num == 0:
            continue
        start_time = _parse_time(r.start_time)
        end_time = _parse_time(r.end_time)
        if start_time is None or end_time is None:
            continue
        professor_restrictions[r.professor_id].append(
            ProfessorRestrictionInfo(
                professor_id=r.professor_id,
                dia_semana=day_num,
                hora_inicio=start_time,
                hora_fin=end_time,
            )
        )
    
    # Crear validadores
    hard_validator = HardConstraintValidator(
        timeslots=timeslots,
        classrooms=classrooms,
        professor_restrictions=dict(professor_restrictions),
        sections_by_league=graph_builder.sections_by_league,
        league_session_types=graph_builder.league_session_types,
        section_session_types=graph_builder.section_session_types,
        sections_by_block=graph_builder.sections_by_block,
    )
    
    soft_evaluator = SoftConstraintEvaluator(
        timeslots=timeslots,
        classrooms=classrooms,
    )
    
    # Crear engine
    engine = ACOEngine(
        graph=graph,
        model=model,
        graph_builder=graph_builder,
        hard_validator=hard_validator,
        soft_evaluator=soft_evaluator,
        params=params,
    )
    
    return engine
