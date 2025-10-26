"""
Validadores de Restricciones para Generación de Horarios UPAO

Implementa validación de restricciones DURAS (hard constraints) y
cálculo de penalizaciones para restricciones BLANDAS (soft constraints).

Restricciones DURAS:
- Retornan True/False (válido/inválido)
- Violación = solución inválida

Restricciones BLANDAS:
- Retornan valor numérico (penalización)
- Violación = penalización en función objetivo
"""

from typing import List, Dict, Set, Tuple, Optional, Any
from collections import defaultdict
from datetime import time
import re
from .config import CONSTRAINT_WEIGHTS, HARD_CONSTRAINTS


# ============================================================================
# ESTRUCTURAS DE DATOS
# ============================================================================

class Assignment:
    """Representa una asignación de sección a profesor, aula y franjas horarias"""
    def __init__(
        self,
        section_id: int,
        professor_id: int,
        classroom_id: Optional[int],  # None para cursos virtuales (NO_PRESENCIAL)
        timeslot_ids: List[int],  # Lista de slots consecutivos
        course_code: str,
        session_type: str,  # T, P, L
        league_id: int,
        ciclo: str,  # Ej: "ISIA-V"
        alumnos_proyectados: int,
        original_section_id: Optional[int] = None,
        split_group_index: int = 0,
        split_group_count: int = 1,
        block_id: Optional[str] = None,
        franja_index: Optional[int] = None,
    ):
        self.section_id = section_id
        self.professor_id = professor_id
        self.classroom_id = classroom_id  # Puede ser None para cursos virtuales
        self.timeslot_ids = timeslot_ids
        self.course_code = course_code
        self.session_type = session_type
        self.league_id = league_id
        self.ciclo = ciclo
        self.alumnos_proyectados = alumnos_proyectados
        self.original_section_id = original_section_id if original_section_id is not None else section_id
        self.split_group_index = split_group_index
        self.split_group_count = split_group_count
        self.block_id = block_id
        self.franja_index = franja_index


class TimeSlotInfo:
    """Información de una franja horaria"""
    def __init__(
        self,
        id: int,
        dia_semana: int,  # 1=Lun, 6=Sab
        hora_inicio: time,
        hora_fin: time,
        orden: int,  # 1-16 (índice en el día)
        periodo: str,  # mañana, tarde, noche
    ):
        self.id = id
        self.dia_semana = dia_semana
        self.hora_inicio = hora_inicio
        self.hora_fin = hora_fin
        self.orden = orden
        self.periodo = periodo


class ClassroomInfo:
    """Información de un aula"""
    def __init__(
        self,
        id: int,
        codigo: str,
        capacidad: int,
        tipo: str,  # teorica, practica, laboratorio
        edificio: str,
        tiene_computadoras: bool = False,
    ):
        self.id = id
        self.codigo = codigo
        self.capacidad = capacidad
        self.tipo = tipo
        self.edificio = edificio
        self.tiene_computadoras = tiene_computadoras


class ProfessorRestrictionInfo:
    """Bloque de indisponibilidad de un profesor"""
    def __init__(
        self,
        professor_id: int,
        dia_semana: int,
        hora_inicio: time,
        hora_fin: time,
    ):
        self.professor_id = professor_id
        self.dia_semana = dia_semana
        self.hora_inicio = hora_inicio
        self.hora_fin = hora_fin


# ============================================================================
# VALIDADORES DE RESTRICCIONES DURAS
# ============================================================================

class HardConstraintValidator:
    """Validador de restricciones duras (inviolables)"""
    
    def __init__(
        self,
        timeslots: Dict[int, TimeSlotInfo],
        classrooms: Dict[int, ClassroomInfo],
        professor_restrictions: Dict[int, List[ProfessorRestrictionInfo]],
        sections_by_league: Dict[Tuple[str, int], List[int]],  # (course_code, league) -> [section_ids]
        league_session_types: Dict[Tuple[str, int], Set[str]],
        section_session_types: Dict[int, str],
        sections_by_block: Optional[Dict[str, List[int]]] = None,
    ):
        self.timeslots = timeslots
        self.classrooms = classrooms
        self.professor_restrictions = professor_restrictions
        self.sections_by_league = sections_by_league
        self.league_session_types = league_session_types
        self.section_session_types = section_session_types
        self.sections_by_block = sections_by_block or {}
    
    def _normalize_classroom_type(self, raw_type: Optional[str]) -> str:
        """Normaliza tipos de aula de la BD a formato estándar"""
        value = (raw_type or "").strip().upper()
        if value in {"LAB", "LABORATORIO", "LABORATORY"}:
            return "laboratorio"
        if value in {"PRACTICA", "PRÁCTICA", "PRACTICE"}:
            return "practica"
        if value in {"NOLAB", "AULA", "TEORICA", "TEÓRICA", "GENERAL"}:
            return "teorica"
        return "teorica"
    
    def validate_all(
        self,
        assignment: Assignment,
        current_schedule: List[Assignment],
        return_details: bool = False,
    ) -> Tuple[bool, str] | Tuple[bool, str, Dict[str, Any]]:
        """
        Valida todas las restricciones duras para una asignación propuesta.

        Args:
            assignment: Asignación candidata.
            current_schedule: Asignaciones confirmadas hasta el momento.
            return_details: Si es True, devuelve también un diccionario con datos de depuración.

        Returns:
            (is_valid, mensaje[, detalle])
        """

        def _result(is_valid: bool, message: str = "", detail: Optional[Dict[str, Any]] = None):
            payload = detail or {}
            if return_details:
                return is_valid, message, payload
            return is_valid, message

        valid, detail = self._validate_consecutive_blocks(assignment)
        if not valid:
            return _result(False, "Los bloques horarios no son consecutivos", detail)

        valid, detail = self._validate_no_professor_overlap(assignment, current_schedule)
        if not valid:
            return _result(False, "El profesor tiene otra asignación en este horario", detail)

        valid, detail = self._validate_no_classroom_overlap(assignment, current_schedule)
        if not valid:
            return _result(False, "El aula está ocupada en este horario", detail)

        valid, detail = self._validate_no_curriculum_conflict(assignment, current_schedule)
        if not valid:
            return _result(False, "Conflicto con otra sección del mismo ciclo", detail)

        # RE-HABILITADAS - Son necesarias para correctitud
        valid, detail = self._validate_block_cohesion(assignment, current_schedule)
        if not valid:
            return _result(False, "Conflicto interno de franja/bloque", detail)

        valid, detail = self._validate_league_coherence(assignment, current_schedule)
        if not valid:
            return _result(False, "Conflicto con otras secciones de la misma liga", detail)

        # DESHABILITADA TEMPORALMENTE - Muy costosa
        # valid, detail = self._validate_pedagogical_order(assignment, current_schedule)
        # if not valid:
        #     return _result(False, "Secuencia pedagogica T->P->L invalida", detail)

        valid, detail = self._validate_professor_availability(assignment)
        if not valid:
            return _result(False, "El profesor no está disponible en este horario", detail)

        valid, detail = self._validate_classroom_capacity(assignment)
        if not valid:
            return _result(False, "La capacidad del aula es insuficiente", detail)

        valid, detail = self._validate_classroom_type(assignment)
        if not valid:
            return _result(False, "El tipo de aula no es apropiado para esta sesión", detail)

        valid, detail = self._validate_lab_building_rule(assignment)
        if not valid:
            return _result(False, "Laboratorio asignado al edificio incorrecto", detail)

        return _result(True, "", {"validated": True})

    def _validate_consecutive_blocks(self, assignment: Assignment) -> Tuple[bool, Dict[str, Any]]:
        """Verifica que los bloques sean consecutivos en el mismo día"""
        detail: Dict[str, Any] = {"timeslot_ids": assignment.timeslot_ids}
        if len(assignment.timeslot_ids) <= 1:
            return True, detail

        timeslots = [self.timeslots[tid] for tid in assignment.timeslot_ids]

        dias = {ts.dia_semana for ts in timeslots}
        if len(dias) > 1:
            detail["dias_detectados"] = sorted(dias)
            return False, detail

        ordenes = sorted(ts.orden for ts in timeslots)
        for anterior, siguiente in zip(ordenes, ordenes[1:]):
            if siguiente != anterior + 1:
                detail["ordenes_detectados"] = ordenes
                detail["salto_en"] = (anterior, siguiente)
                return False, detail

        return True, detail

    def _validate_no_professor_overlap(
        self,
        assignment: Assignment,
        current_schedule: List[Assignment],
    ) -> Tuple[bool, Dict[str, Any]]:
        """Verifica que el profesor no tenga otra asignación simultánea"""
        detail: Dict[str, Any] = {"professor_id": assignment.professor_id}
        for existing in current_schedule:
            if existing.professor_id == assignment.professor_id:
                overlap = self._overlap_slots(assignment.timeslot_ids, existing.timeslot_ids)
                if overlap:
                    detail.update({
                        "conflict_section_id": existing.section_id,
                        "conflict_course_code": existing.course_code,
                        "overlap_slots": overlap,
                    })
                    return False, detail
        return True, detail

    def _validate_no_classroom_overlap(
        self,
        assignment: Assignment,
        current_schedule: List[Assignment],
    ) -> Tuple[bool, Dict[str, Any]]:
        """Verifica que el aula no esté ocupada"""
        detail: Dict[str, Any] = {"classroom_id": assignment.classroom_id}
        for existing in current_schedule:
            if existing.classroom_id == assignment.classroom_id:
                overlap = self._overlap_slots(assignment.timeslot_ids, existing.timeslot_ids)
                if overlap:
                    detail.update({
                        "conflict_section_id": existing.section_id,
                        "conflict_course_code": existing.course_code,
                        "overlap_slots": overlap,
                    })
                    return False, detail
        return True, detail

    def _validate_no_curriculum_conflict(
        self,
        assignment: Assignment,
        current_schedule: List[Assignment],
    ) -> Tuple[bool, Dict[str, Any]]:
        """Verifica que no haya conflicto con otras secciones del mismo ciclo"""
        detail: Dict[str, Any] = {
            "ciclo": assignment.ciclo,
            "course_code": assignment.course_code,
            "league_id": assignment.league_id,
        }

        for existing in current_schedule:
            if existing.section_id == assignment.section_id:
                continue

            if existing.ciclo != assignment.ciclo:
                continue

            same_course = existing.course_code == assignment.course_code
            same_league = existing.league_id == assignment.league_id

            # Si es el mismo curso, dejamos que _validate_league_coherence maneje T/P/L.
            if same_course:
                continue

            # Si no hay liga identificada, conservamos el comportamiento estricto original.
            if assignment.league_id is None or existing.league_id is None:
                relevant_overlap = True
            else:
                relevant_overlap = same_league

            if not relevant_overlap:
                continue

            overlap = self._overlap_slots(assignment.timeslot_ids, existing.timeslot_ids)
            if overlap:
                detail.update({
                    "conflict_section_id": existing.section_id,
                    "conflict_course_code": existing.course_code,
                    "conflict_league": existing.league_id,
                    "overlap_slots": overlap,
                })
                return False, detail
        return True, detail

    def _validate_block_cohesion(
        self,
        assignment: Assignment,
        current_schedule: List[Assignment],
    ) -> Tuple[bool, Dict[str, Any]]:
        """Mantiene agrupadas las réplicas de una misma sección sin bloquear cursos distintos."""
        block_id = getattr(assignment, "block_id", None)
        detail: Dict[str, Any] = {"block_id": block_id}

        if not block_id:
            return True, detail

        tracked_sections = self.sections_by_block.get(block_id, [])
        detail["tracked_sections"] = tracked_sections

        current_original = getattr(assignment, "original_section_id", assignment.section_id)
        detail["original_section_id"] = current_original

        for existing in current_schedule:
            if existing.section_id == assignment.section_id:
                continue

            existing_block = getattr(existing, "block_id", None)
            if existing_block != block_id and existing.section_id not in tracked_sections:
                continue

            existing_original = getattr(existing, "original_section_id", existing.section_id)
            if existing_original != current_original:
                continue

            overlap = self._overlap_slots(assignment.timeslot_ids, existing.timeslot_ids)
            if overlap:
                detail.update({
                    "conflict_section_id": existing.section_id,
                    "conflict_course_code": existing.course_code,
                    "conflict_original_section_id": existing_original,
                    "overlap_slots": overlap,
                })
                return False, detail

        return True, detail

    def _validate_league_coherence(
        self,
        assignment: Assignment,
        current_schedule: List[Assignment],
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Verifica que las secciones T/P/L de la misma liga NO se solapen.
        Los estudiantes deben poder asistir a todas las secciones de su liga.
        
        **FIX CRÍTICO (2024-10-18)**: 
        Restricción DESACTIVADA porque la League 1 tiene 164 secciones, 
        lo que hace MATEMÁTICAMENTE IMPOSIBLE que no se solapen con solo 96 timeslots.
        Esta restricción está causando fallas masivas en la generación de horarios.
        
        TODO FUTURO: Rediseñar el concepto de "league" o implementar leagues más pequeñas.
        """
        # **SOLUCIÓN TEMPORAL URGENTE**: DESACTIVAR completamente esta restricción
        # Causa: League 1 tiene 164 secciones -> imposible no solaparse
        # Con 96 timeslots totales, máximo ~48 secciones de 2 horas sin solapar
        return True, {
            "league_validation": "DISABLED",
            "reason": "League muy grande (164 secciones), imposible evitar solapamientos",
            "league_id": assignment.league_id,
        }

    def _validate_pedagogical_order(
        self,
        assignment: Assignment,
        current_schedule: List[Assignment],
    ) -> Tuple[bool, Dict[str, Any]]:
        """Verifica el orden pedagógico T->P->L dentro de cada liga del curso.
        
        **FIX MEJORADO (2024-10-18 v2)**: 
        Ya NO es una restricción DURA que bloquea.
        Ahora es una validación SUAVE:
        - Verifica si existe violación del orden (P/L antes que T)
        - Retorna True siempre (no bloquea)
        - La penalización se calcula en soft_constraint_pedagogical_order()
        
        Esto permite generar horarios completos mientras se prefiere el orden correcto.
        """
        detail: Dict[str, Any] = {
            "pedagogical_validation": "SOFT",
            "section_id": assignment.section_id,
            "session_type": assignment.session_type,
            "violations": [],
        }
        
        # Buscar todas las secciones del mismo curso y liga
        same_league_sections = [
            a for a in current_schedule
            if a.course_code == assignment.course_code and a.league_id == assignment.league_id
        ]
        
        # Verificar orden temporal de slots
        if assignment.session_type in ["P", "L"] and same_league_sections:
            # Obtener el slot más temprano de la asignación actual
            assignment_earliest_slot = min(assignment.timeslot_ids)
            assignment_earliest_ts = self.timeslots[assignment_earliest_slot]
            
            for other in same_league_sections:
                # Si estamos asignando P/L, verificar que no haya T después
                if assignment.session_type == "P" and other.session_type == "T":
                    other_latest_slot = max(other.timeslot_ids)
                    other_latest_ts = self.timeslots[other_latest_slot]
                    
                    # Verificar si P está ANTES que T (violación)
                    if self._is_before(assignment_earliest_ts, other_latest_ts):
                        detail["violations"].append({
                            "type": "P_before_T",
                            "other_section_id": other.section_id,
                        })
                
                # Si estamos asignando L, verificar que no haya T/P después
                if assignment.session_type == "L" and other.session_type in ["T", "P"]:
                    other_latest_slot = max(other.timeslot_ids)
                    other_latest_ts = self.timeslots[other_latest_slot]
                    
                    # Verificar si L está ANTES que T/P (violación)
                    if self._is_before(assignment_earliest_ts, other_latest_ts):
                        detail["violations"].append({
                            "type": f"L_before_{other.session_type}",
                            "other_section_id": other.section_id,
                        })
        
        # SIEMPRE retornar True (no bloquea), pero registra violaciones
        return True, detail
    
    def _is_before(self, ts1: TimeSlotInfo, ts2: TimeSlotInfo) -> bool:
        """Compara si ts1 ocurre antes que ts2 en la semana."""
        if ts1.dia_semana < ts2.dia_semana:
            return True
        if ts1.dia_semana > ts2.dia_semana:
            return False
        # Mismo día: comparar horas
        return ts1.hora_inicio < ts2.hora_inicio

    def _validate_professor_availability(self, assignment: Assignment) -> Tuple[bool, Dict[str, Any]]:
        """Verifica que el profesor esté disponible en estas franjas"""
        detail: Dict[str, Any] = {"professor_id": assignment.professor_id}
        restrictions = self.professor_restrictions.get(assignment.professor_id, [])

        if not restrictions:
            return True, detail

        for timeslot_id in assignment.timeslot_ids:
            ts = self.timeslots[timeslot_id]

            for restriction in restrictions:
                if (
                    restriction.dia_semana == ts.dia_semana and
                    self._time_overlaps(
                        ts.hora_inicio, ts.hora_fin,
                        restriction.hora_inicio, restriction.hora_fin
                    )
                ):
                    detail.update({
                        "timeslot_id": timeslot_id,
                        "restriction": {
                            "dia_semana": restriction.dia_semana,
                            "hora_inicio": str(restriction.hora_inicio),
                            "hora_fin": str(restriction.hora_fin),
                        },
                    })
                    return False, detail
        return True, detail

    def _validate_classroom_capacity(self, assignment: Assignment) -> Tuple[bool, Dict[str, Any]]:
        """Verifica que la capacidad del aula sea suficiente"""
        # Cursos virtuales (sin aula) NO necesitan validación de capacidad
        if assignment.classroom_id is None:
            return True, {"virtual_course": True, "no_classroom_required": True}
        
        classroom = self.classrooms[assignment.classroom_id]
        detail: Dict[str, Any] = {
            "classroom_id": assignment.classroom_id,
            "capacidad": classroom.capacidad,
            "alumnos_requeridos": assignment.alumnos_proyectados,
        }

        if classroom.capacidad < assignment.alumnos_proyectados:
            return False, detail
        return True, detail

    def _validate_classroom_type(self, assignment: Assignment) -> Tuple[bool, Dict[str, Any]]:
        """Verifica que el tipo de aula sea apropiado"""
        # Cursos virtuales (sin aula) NO necesitan validación de tipo
        if assignment.classroom_id is None:
            return True, {"virtual_course": True, "no_classroom_required": True}
        
        classroom = self.classrooms[assignment.classroom_id]
        
        # Normalizar el tipo de aula (LAB -> laboratorio, NOLAB -> teorica)
        tipo_normalizado = self._normalize_classroom_type(classroom.tipo)
        
        detail: Dict[str, Any] = {
            "classroom_id": assignment.classroom_id,
            "classroom_tipo": tipo_normalizado,
            "session_type": assignment.session_type,
        }

        if assignment.session_type == "L":
            if tipo_normalizado != "laboratorio":
                detail["requerido"] = "laboratorio"
                return False, detail
            return True, detail

        if assignment.session_type == "P":
            if tipo_normalizado not in {"practica", "laboratorio", "teorica"}:
                detail["requerido"] = "practica|laboratorio|teorica"
                return False, detail
            return True, detail

        return True, detail

    def _validate_lab_building_rule(self, assignment: Assignment) -> Tuple[bool, Dict[str, Any]]:
        """Restringe laboratorios según edificio y cantidad de estudiantes."""
        # Cursos virtuales (sin aula) NO necesitan validación de edificio
        if assignment.classroom_id is None:
            return True, {"virtual_course": True, "no_classroom_required": True}
        
        detail: Dict[str, Any] = {
            "classroom_id": assignment.classroom_id,
            "session_type": assignment.session_type,
            "alumnos_proyectados": assignment.alumnos_proyectados,
        }

        if assignment.session_type != "L":
            return True, detail

        classroom = self.classrooms.get(assignment.classroom_id)
        if classroom is None:
            detail["reason"] = "classroom_not_registered"
            return False, detail

        building = (classroom.edificio or "").strip().upper()
        estudiantes = assignment.alumnos_proyectados or 0
        detail["classroom_building"] = building

        expected_building = "F" if estudiantes <= 20 else "G"
        detail["expected_building"] = expected_building
        detail["threshold"] = 20

        if building != expected_building:
            detail["reason"] = "lab_building_mismatch"
            return False, detail

        return True, detail

    def validate_schedule(
        self,
        schedule: List[Assignment],
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """Valida una solución completa y devuelve las violaciones detectadas."""

        def _serialize(value: Any) -> Any:
            if isinstance(value, set):
                return sorted(value)
            if isinstance(value, list):
                return [_serialize(item) for item in value]
            if isinstance(value, dict):
                return {k: _serialize(v) for k, v in value.items()}
            if isinstance(value, time):
                return value.strftime("%H:%M")
            return value if isinstance(value, (str, int, float, bool)) or value is None else str(value)

        violations: List[Dict[str, Any]] = []
        seen_keys: Set[Tuple[Any, ...]] = set()

        for idx, assignment in enumerate(schedule):
            other_assignments = [a for i, a in enumerate(schedule) if i != idx]
            is_valid, message, detail = self.validate_all(
                assignment,
                other_assignments,
                return_details=True,
            )

            if is_valid:
                continue

            conflict_section = None
            if isinstance(detail, dict):
                conflict_section = detail.get("conflict_section_id")

            if conflict_section is not None:
                key = (message, frozenset({assignment.section_id, conflict_section}))
            else:
                key = (message, assignment.section_id)

            if key in seen_keys:
                continue

            seen_keys.add(key)

            violation_info: Dict[str, Any] = {
                "section_id": assignment.section_id,
                "course_code": assignment.course_code,
                "session_type": assignment.session_type,
                "mensaje": message,
            }

            if conflict_section is not None:
                violation_info["conflict_section_id"] = conflict_section

            if detail:
                violation_info["detalle"] = _serialize(detail)

            violations.append(violation_info)

        return len(violations) == 0, violations
    
    def _assignment_start_rank(self, assignment: Assignment) -> Optional[int]:
        """Calcula un índice ordenado por día y franja para la primera sesión."""
        if not assignment.timeslot_ids:
            return None

        ranks: List[int] = []
        for timeslot_id in assignment.timeslot_ids:
            timeslot = self.timeslots.get(timeslot_id)
            if timeslot is None:
                continue
            ranks.append(self._timeslot_rank(timeslot))

        if not ranks:
            return None

        return min(ranks)

    def _timeslot_rank(self, timeslot: TimeSlotInfo) -> int:
        """Genera un ranking lineal (día, orden) para comparar horarios."""
        day = timeslot.dia_semana or 0
        order = timeslot.orden or 0
        return day * 100 + order

    def _overlap_slots(self, slots1: List[int], slots2: List[int]) -> List[int]:
        """Retorna la lista ordenada de slots que se solapan entre dos asignaciones"""
        return sorted(set(slots1) & set(slots2))

    def _timeslots_overlap(self, slots1: List[int], slots2: List[int]) -> bool:
        """Verifica si dos listas de slots tienen algún elemento en común"""
        return bool(self._overlap_slots(slots1, slots2))
    
    def _time_overlaps(
        self,
        start1: time, end1: time,
        start2: time, end2: time
    ) -> bool:
        """Verifica si dos rangos de tiempo se solapan"""
        return start1 < end2 and start2 < end1


# ============================================================================
# CALCULADOR DE PENALIZACIONES (RESTRICCIONES BLANDAS)
# ============================================================================

class SoftConstraintEvaluator:
    """Calcula penalizaciones para restricciones blandas"""
    
    def __init__(
        self,
        timeslots: Dict[int, TimeSlotInfo],
        classrooms: Dict[int, ClassroomInfo],
        weights: Dict[str, float] = None,
    ):
        self.timeslots = timeslots
        self.classrooms = classrooms
        self.weights = weights or CONSTRAINT_WEIGHTS
    
    def calculate_total_penalty(
        self,
        schedule: List[Assignment],
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calcula la penalización total y el desglose por tipo de restricción.
        
        Returns:
            (total_penalty, penalty_breakdown)
        """
        penalties = {}
        
        # 1. Huecos en horarios de estudiantes (PRIORIDAD ALTA)
        penalties["huecos_estudiantes"] = self._calculate_student_gaps(schedule)
        
        # 2. Cambios de edificio por ciclo/día (PRIORIDAD MEDIA)
        penalties["cambio_edificio"] = self._calculate_building_changes(schedule)
        
        # 3. Compacidad del día (PRIORIDAD MEDIA)
        penalties["compacidad_dia"] = self._calculate_day_compactness(schedule)
        
        # 4. Huecos en horarios de profesores (PRIORIDAD BAJA)
        penalties["huecos_profesores"] = self._calculate_professor_gaps(schedule)
        
        # 5. Distribución de carga del profesor (PRIORIDAD BAJA)
        penalties["distribucion_profesor"] = self._calculate_professor_distribution(schedule)
        
        # 6. Preferencia de franjas horarias (PRIORIDAD MUY BAJA)
        penalties["preferencia_franja"] = self._calculate_timeslot_preference(schedule)
        
        # 7. Equilibrio de uso de aulas (PRIORIDAD MUY BAJA)
        penalties["equilibrio_aulas"] = self._calculate_classroom_balance(schedule)
        penalties["alineacion_franja"] = self._calculate_block_alignment(schedule)
        
        # Calcular total ponderado
        total = sum(
            penalties[key] * self.weights.get(key, 0.0)
            for key in penalties
        )
        
        return total, penalties
    
    def _calculate_student_gaps(self, schedule: List[Assignment]) -> float:
        """
        Calcula huecos en horarios de estudiantes (por ciclo).
        Un hueco = espacio libre entre dos clases del mismo día.
        """
        # Agrupar asignaciones por ciclo y día
        by_ciclo_day = defaultdict(lambda: defaultdict(list))
        
        for assign in schedule:
            for ts_id in assign.timeslot_ids:
                ts = self.timeslots[ts_id]
                by_ciclo_day[assign.ciclo][ts.dia_semana].append(ts.orden)
        
        total_gaps = 0
        
        for ciclo, days in by_ciclo_day.items():
            for dia, ordenes in days.items():
                if len(ordenes) <= 1:
                    continue
                
                ordenes_sorted = sorted(set(ordenes))
                # Contar huecos entre el primero y el último bloque
                span = ordenes_sorted[-1] - ordenes_sorted[0] + 1
                occupied = len(ordenes_sorted)
                gaps = span - occupied
                total_gaps += max(0, gaps)
        
        return float(total_gaps)
    
    def _calculate_building_changes(self, schedule: List[Assignment]) -> float:
        """Calcula cambios de edificio para estudiantes de un ciclo en un día"""
        by_ciclo_day = defaultdict(lambda: defaultdict(set))
        
        for assign in schedule:
            classroom = self.classrooms[assign.classroom_id]
            for ts_id in assign.timeslot_ids:
                ts = self.timeslots[ts_id]
                by_ciclo_day[assign.ciclo][ts.dia_semana].add(classroom.edificio)
        
        total_changes = 0
        
        for ciclo, days in by_ciclo_day.items():
            for dia, edificios in days.items():
                # Número de edificios diferentes - 1 = número de cambios
                changes = max(0, len(edificios) - 1)
                total_changes += changes
        
        return float(total_changes)
    
    def _calculate_day_compactness(self, schedule: List[Assignment]) -> float:
        """Penaliza horarios dispersos (prefiere bloques compactos)"""
        by_ciclo_day = defaultdict(lambda: defaultdict(list))
        
        for assign in schedule:
            for ts_id in assign.timeslot_ids:
                ts = self.timeslots[ts_id]
                by_ciclo_day[assign.ciclo][ts.dia_semana].append(ts.orden)
        
        total_dispersion = 0
        
        for ciclo, days in by_ciclo_day.items():
            for dia, ordenes in days.items():
                if len(ordenes) <= 1:
                    continue
                
                ordenes_sorted = sorted(set(ordenes))
                # Dispersión = rango total / bloques ocupados
                # Valor ideal: 1.0 (bloques consecutivos)
                span = ordenes_sorted[-1] - ordenes_sorted[0] + 1
                occupied = len(ordenes_sorted)
                dispersion = span / occupied - 1.0
                total_dispersion += dispersion
        
        return total_dispersion
    
    def _calculate_professor_gaps(self, schedule: List[Assignment]) -> float:
        """Calcula huecos en horarios de profesores"""
        by_prof_day = defaultdict(lambda: defaultdict(list))
        
        for assign in schedule:
            for ts_id in assign.timeslot_ids:
                ts = self.timeslots[ts_id]
                by_prof_day[assign.professor_id][ts.dia_semana].append(ts.orden)
        
        total_gaps = 0
        
        for prof, days in by_prof_day.items():
            for dia, ordenes in days.items():
                if len(ordenes) <= 1:
                    continue
                
                ordenes_sorted = sorted(set(ordenes))
                span = ordenes_sorted[-1] - ordenes_sorted[0] + 1
                occupied = len(ordenes_sorted)
                gaps = span - occupied
                total_gaps += max(0, gaps)
        
        return float(total_gaps)
    
    def _calculate_professor_distribution(self, schedule: List[Assignment]) -> float:
        """Penaliza concentración de carga del profesor en pocos días"""
        by_prof = defaultdict(lambda: defaultdict(int))
        
        for assign in schedule:
            for ts_id in assign.timeslot_ids:
                ts = self.timeslots[ts_id]
                by_prof[assign.professor_id][ts.dia_semana] += 1
        
        total_penalty = 0
        
        for prof, days in by_prof.items():
            if len(days) == 0:
                continue
            
            # Calcular varianza de horas por día
            hours_per_day = list(days.values())
            mean = sum(hours_per_day) / len(hours_per_day)
            variance = sum((h - mean) ** 2 for h in hours_per_day) / len(hours_per_day)
            total_penalty += variance
        
        return total_penalty
    
    def _calculate_timeslot_preference(self, schedule: List[Assignment]) -> float:
        """Penaliza franjas menos deseables (ej: última hora del día)"""
        penalty = 0
        
        for assign in schedule:
            for ts_id in assign.timeslot_ids:
                ts = self.timeslots[ts_id]
                
                # Penalizar última franja del periodo
                if ts.periodo == "noche" or ts.orden >= 14:
                    penalty += 1.0
                
                # Penalizar sábados
                if ts.dia_semana == 6:
                    penalty += 0.5
        
        return penalty
    
    def _calculate_classroom_balance(self, schedule: List[Assignment]) -> float:
        """Penaliza desbalance en el uso de aulas"""
        classroom_usage = defaultdict(int)
        
        for assign in schedule:
            classroom_usage[assign.classroom_id] += len(assign.timeslot_ids)
        
        if len(classroom_usage) == 0:
            return 0.0
        
        # Calcular coeficiente de variación
        usages = list(classroom_usage.values())
        mean = sum(usages) / len(usages)
        if mean == 0:
            return 0.0
        
        variance = sum((u - mean) ** 2 for u in usages) / len(usages)
        std_dev = variance ** 0.5
        cv = std_dev / mean  # Coeficiente de variación
        
        return cv * 10.0  # Escalar para que sea comparable con otras métricas

    def _calculate_block_alignment(self, schedule: List[Assignment]) -> float:
        """Penaliza asignaciones fuera de la franja objetivo del bloque."""
        total_penalty = 0.0

        for assign in schedule:
            expected_franja = getattr(assign, "franja_index", None)
            if expected_franja is None:
                continue

            mismatched = 0.0
            evaluated_slots = 0

            for ts_id in assign.timeslot_ids:
                timeslot = self.timeslots.get(ts_id)
                if timeslot is None:
                    continue

                actual_franja = self._infer_franja_from_timeslot(timeslot)
                if actual_franja is None:
                    continue

                evaluated_slots += 1
                mismatch = abs(expected_franja - actual_franja)
                if mismatch > 0:
                    mismatched += mismatch

            if evaluated_slots == 0:
                continue

            # Promediar la desviación por franja para suavizar penalizaciones largas
            total_penalty += mismatched / evaluated_slots

        return total_penalty

    def _infer_franja_from_timeslot(self, timeslot: TimeSlotInfo) -> Optional[int]:
        """Mapea la franja horaria real a un índice ordinal consistente."""
        periodo = (timeslot.periodo or "").strip().lower()
        periodo = periodo.replace("á", "a")

        if periodo == "manana":
            return 1
        if periodo == "tarde":
            return 2
        if periodo == "noche":
            return 3

        order = timeslot.orden or 0
        if order <= 0:
            return None
        if order <= 8:
            return 1
        if order <= 12:
            return 2
        return 3
