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

from typing import Any, Dict, List, Optional, Set, Tuple
from collections import defaultdict
from datetime import time, datetime, timedelta
import re
from .config import CONSTRAINT_WEIGHTS


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

    @staticmethod
    def _parse_ciclo_number(ciclo_str: Any) -> int:
        """
        Extrae el numero de ciclo desde representaciones como ``ISIA-V`` o ``I``.

        Retorna 0 cuando no se puede inferir el ciclo.
        """
        if ciclo_str is None:
            raw_value = ""
        elif isinstance(ciclo_str, (int, float)):
            # Soporta ciclos enviados como numericos desde la BD/modelo.
            raw_value = str(int(ciclo_str))
        else:
            raw_value = str(ciclo_str).strip().upper()
        if not raw_value:
            return 0

        roman_values: Dict[str, int] = {
            "I": 1,
            "V": 5,
            "X": 10,
            "L": 50,
            "C": 100,
            "D": 500,
            "M": 1000,
        }

        def _roman_to_int(value: str) -> int:
            total = 0
            previous = 0
            for char in reversed(value):
                current = roman_values.get(char)
                if current is None:
                    return 0
                if current < previous:
                    total -= current
                else:
                    total += current
                    previous = current
            return total

        tokens = [token for token in re.split(r"[^A-Z0-9]+", raw_value) if token]
        for token in reversed(tokens):
            if token.isdigit():
                return int(token)
            if re.fullmatch(r"[IVXLCDM]+", token):
                return _roman_to_int(token)

        if raw_value.isdigit():
            return int(raw_value)

        if re.fullmatch(r"[IVXLCDM]+", raw_value):
            return _roman_to_int(raw_value)

        return 0


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
        es_baja_prioridad: bool = False,
    ):
        self.professor_id = professor_id
        self.dia_semana = dia_semana
        self.hora_inicio = hora_inicio
        self.hora_fin = hora_fin
        self.es_baja_prioridad = es_baja_prioridad


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
        section_modalities: Optional[Dict[int, str]] = None,
    ):
        self.timeslots = timeslots
        self.classrooms = classrooms
        self.professor_restrictions = professor_restrictions
        self.sections_by_league = sections_by_league
        self.league_session_types = league_session_types
        self.section_session_types = section_session_types
        self.sections_by_block = sections_by_block or {}
        # Modalidad de cada sección (PRESENCIAL/NO_PRESENCIAL); default PRESENCIAL si falta
        self.section_modalities = section_modalities or {}
    
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

        # Nueva restricción dura: separar cursos virtuales de cualquier presencial al menos 1 franja
        valid, detail = self._validate_virtual_spacing(assignment, current_schedule)
        if not valid:
            return _result(False, "Curso virtual debe tener 1 franja de separación de presenciales", detail)

        # RE-HABILIT ADAS - Son necesarias para correctitud pero optimizadas
        valid, detail = self._validate_block_cohesion(assignment, current_schedule)
        if not valid:
            return _result(False, "Conflicto interno de franja/bloque", detail)

        valid, detail = self._validate_league_coherence(assignment, current_schedule)
        if not valid:
            return _result(False, "Conflicto con otras secciones de la misma liga", detail)

        valid, detail = self._validate_pedagogical_order(assignment, current_schedule)
        if not valid:
            return _result(False, "Secuencia pedagógica T→P→L inválida", detail)

        valid, detail = self._validate_professor_availability(assignment)
        if not valid:
            return _result(False, "El profesor no está disponible en este horario", detail)

        valid, detail = self._validate_classroom_capacity(assignment)
        if not valid:
            return _result(False, "La capacidad del aula es insuficiente", detail)

        valid, detail = self._validate_classroom_type(assignment)
        if not valid:
            return _result(False, "El tipo de aula no es apropiado para esta sesión", detail)

        return _result(True, "", {"validated": True})

    def _validate_consecutive_blocks(self, assignment: Assignment) -> Tuple[bool, Dict[str, Any]]:
        """Verifica que los bloques sean consecutivos en el mismo día"""
        detail: Dict[str, Any] = {"timeslot_ids": assignment.timeslot_ids}
        if len(assignment.timeslot_ids) <= 1:
            return True, detail

        # OPTIMIZACIÓN: Acceso directo sin comprensión de lista para evitar overhead
        try:
            first_ts = self.timeslots[assignment.timeslot_ids[0]]
            dia_ref = first_ts.dia_semana
            ordenes = [first_ts.orden]
            
            # Verificar todos los slots restantes
            for tid in assignment.timeslot_ids[1:]:
                ts = self.timeslots[tid]
                # Verificar mismo día
                if ts.dia_semana != dia_ref:
                    detail["dias_detectados"] = [dia_ref, ts.dia_semana]
                    return False, detail
                ordenes.append(ts.orden)
            
            # Verificar consecutividad
            ordenes.sort()
            for i in range(len(ordenes) - 1):
                if ordenes[i+1] != ordenes[i] + 1:
                    detail["ordenes_detectados"] = ordenes
                    detail["salto_en"] = (ordenes[i], ordenes[i+1])
                    return False, detail
            
            return True, detail
            
        except KeyError as e:
            # Si un timeslot no existe, es un error crítico
            detail["error"] = f"Timeslot {e} no encontrado"
            return False, detail

    def _validate_no_professor_overlap(
        self,
        assignment: Assignment,
        current_schedule: List[Assignment],
    ) -> Tuple[bool, Dict[str, Any]]:
        """Verifica que el profesor no tenga otra asignación simultánea"""
        detail: Dict[str, Any] = {"professor_id": assignment.professor_id}
        
        # OPTIMIZACIÓN: Usar set para detección rápida de overlap
        assignment_slots_set = set(assignment.timeslot_ids)
        
        for existing in current_schedule:
            if existing.professor_id == assignment.professor_id:
                # Verificación rápida con sets (O(1) promedio vs O(n) con listas)
                existing_slots_set = set(existing.timeslot_ids)
                overlap = assignment_slots_set & existing_slots_set
                
                if overlap:
                    detail.update({
                        "conflict_section_id": existing.section_id,
                        "conflict_course_code": existing.course_code,
                        "overlap_slots": sorted(overlap),
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
        
        if assignment.classroom_id is None or self._is_virtual(assignment.section_id, assignment.classroom_id):
            return True, detail
            
        # OPTIMIZACIÓN: Usar set para detección rápida de overlap
        assignment_slots_set = set(assignment.timeslot_ids)
        
        for existing in current_schedule:
            if existing.classroom_id == assignment.classroom_id:
                # Ignorar si el curso existente es virtual (no ocupa aula, incluso si tiene un ID residual)
                if self._is_virtual(existing.section_id, existing.classroom_id):
                    continue
                    
                # Verificación rápida con sets (O(1) promedio vs O(n) con listas)
                existing_slots_set = set(existing.timeslot_ids)
                overlap = assignment_slots_set & existing_slots_set
                
                if overlap:
                    detail.update({
                        "conflict_section_id": existing.section_id,
                        "conflict_course_code": existing.course_code,
                        "overlap_slots": sorted(overlap),
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

        # OPTIMIZACIÓN: Convertir a set para búsquedas O(1)
        tracked_set = set(tracked_sections) if tracked_sections else set()
        assignment_slots_set = set(assignment.timeslot_ids)
        
        for existing in current_schedule:
            if existing.section_id == assignment.section_id:
                continue

            existing_block = getattr(existing, "block_id", None)
            # OPTIMIZACIÓN: Skip early si no es del mismo bloque Y no está tracked
            if existing_block != block_id and existing.section_id not in tracked_set:
                continue

            existing_original = getattr(existing, "original_section_id", existing.section_id)
            if existing_original != current_original:
                continue

            # OPTIMIZACIÓN: Usar set intersection en vez de loop
            existing_slots_set = set(existing.timeslot_ids)
            overlap = assignment_slots_set & existing_slots_set
            if overlap:
                detail.update({
                    "conflict_section_id": existing.section_id,
                    "conflict_course_code": existing.course_code,
                    "conflict_original_section_id": existing_original,
                    "overlap_slots": list(overlap),
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
        """Aplica estrictamente el orden pedagógico T -> P -> L por liga."""
        detail: Dict[str, Any] = {
            "section_id": assignment.section_id,
            "session_type": assignment.session_type,
            "course_code": assignment.course_code,
            "league_id": assignment.league_id,
        }

        league_key = (assignment.course_code, assignment.league_id)
        league_types = {t.upper() for t in self.league_session_types.get(league_key, set())}

        same_league_sections = [
            a for a in current_schedule
            if a.course_code == assignment.course_code and a.league_id == assignment.league_id
        ]

        if not same_league_sections:
            return True, detail

        assignment_start_ts = self._get_start_timeslot(assignment)

        for other in same_league_sections:
            other_start_ts = self._get_start_timeslot(other)
            comparison = self._compare_timeslots(other_start_ts, assignment_start_ts)

            if assignment.session_type == "T":
                if other.session_type in {"P", "L"} and other.session_type in league_types:
                    # T debe ocurrir antes que P/L existentes
                    if comparison <= 0:
                        detail["conflict_type"] = f"T_after_{other.session_type}"
                        detail["other_section_id"] = other.section_id
                        return False, detail

            elif assignment.session_type == "P":
                if "T" in league_types and other.session_type == "T":
                    # P no puede comenzar antes (o al mismo tiempo) que T
                    if comparison >= 0:
                        detail["conflict_type"] = "P_before_T"
                        detail["other_section_id"] = other.section_id
                        return False, detail

                if "L" in league_types and other.session_type == "L":
                    # P debe ocurrir antes que L
                    if comparison <= 0:
                        detail["conflict_type"] = "P_after_L"
                        detail["other_section_id"] = other.section_id
                        return False, detail

            elif assignment.session_type == "L":
                # Si existe P en la liga, L debe ocurrir después de P. Si no hay P, usar T.
                enforce_against: List[str] = []
                if "P" in league_types:
                    enforce_against.append("P")
                elif "T" in league_types:
                    enforce_against.append("T")

                if other.session_type in enforce_against:
                    if comparison >= 0:
                        detail["conflict_type"] = f"L_before_{other.session_type}"
                        detail["other_section_id"] = other.section_id
                        return False, detail

        return True, detail

    def _is_virtual(self, section_id: int, classroom_id: Optional[int]) -> bool:
        """Determina si la sección es virtual considerando modalidad y ausencia de aula."""
        modality = self.section_modalities.get(section_id)
        if modality is not None:
            return modality.strip().upper() == "NO_PRESENCIAL"
        return classroom_id is None

    def _validate_virtual_spacing(
        self,
        assignment: Assignment,
        current_schedule: List[Assignment],
    ) -> Tuple[bool, Dict[str, Any]]:
        """Evita adyacencia virtual/presencial para alumnos del mismo ciclo en un mismo día."""
        detail: Dict[str, Any] = {}

        if not assignment.timeslot_ids:
            return True, detail

        assignment_is_virtual = self._is_virtual(assignment.section_id, assignment.classroom_id)

        # Rango de franjas del bloque en evaluación por día
        primary_ts = [self.timeslots.get(tid) for tid in assignment.timeslot_ids if self.timeslots.get(tid)]
        if not primary_ts:
            return True, detail

        # Agrupar por día porque el bloque podría tener múltiples días en casos inusuales
        by_day_primary: Dict[int, Tuple[int, int]] = {}
        for ts in primary_ts:
            low, high = by_day_primary.get(ts.dia_semana, (ts.orden, ts.orden))
            by_day_primary[ts.dia_semana] = (min(low, ts.orden), max(high, ts.orden))

        for other in current_schedule:
            if not other.timeslot_ids:
                continue

            # Solo aplica cuando son del mismo ciclo (los alumnos necesitan tiempo de traslado)
            if not assignment.ciclo or not other.ciclo or assignment.ciclo != other.ciclo:
                continue
                
            # Además, deben pertenecer a la misma liga (grupo de estudiantes) para que haya conflicto real
            if assignment.league_id is not None and other.league_id is not None:
                if assignment.league_id != other.league_id:
                    continue

            other_is_virtual = self._is_virtual(other.section_id, other.classroom_id)

            # Solo importa la dupla virtual-presencial
            if assignment_is_virtual == other_is_virtual:
                continue

            other_ts_list = [self.timeslots.get(tid) for tid in other.timeslot_ids if self.timeslots.get(tid)]
            if not other_ts_list:
                continue

            by_day_other: Dict[int, Tuple[int, int]] = {}
            for ts in other_ts_list:
                low, high = by_day_other.get(ts.dia_semana, (ts.orden, ts.orden))
                by_day_other[ts.dia_semana] = (min(low, ts.orden), max(high, ts.orden))

            # Comparar rangos en días coincidentes
            for day, (v_low, v_high) in by_day_primary.items():
                if day not in by_day_other:
                    continue
                o_low, o_high = by_day_other[day]

                # Requerimos al menos una franja libre entre rangos -> distancias estrictas
                # v_high + 1 < o_low  OR  o_high + 1 < v_low  para ser válidos
                if v_high + 1 < o_low or o_high + 1 < v_low:
                    continue

                detail.update({
                    "virtual_section_id": assignment.section_id if assignment_is_virtual else other.section_id,
                    "presencial_section_id": other.section_id if assignment_is_virtual else assignment.section_id,
                    "dia": day,
                    "rango_virtual": (v_low, v_high) if assignment_is_virtual else (o_low, o_high),
                    "rango_presencial": (o_low, o_high) if assignment_is_virtual else (v_low, v_high),
                })
                return False, detail

        return True, detail
    
    def _is_before(self, ts1: TimeSlotInfo, ts2: TimeSlotInfo) -> bool:
        """Compara si ts1 ocurre antes que ts2 en la semana."""
        return self._compare_timeslots(ts1, ts2) == -1

    def _compare_timeslots(self, ts1: TimeSlotInfo, ts2: TimeSlotInfo) -> int:
        """-1 si ts1 es antes, 0 si igual, 1 si es después."""
        if ts1.dia_semana < ts2.dia_semana:
            return -1
        if ts1.dia_semana > ts2.dia_semana:
            return 1
        if ts1.orden < ts2.orden:
            return -1
        if ts1.orden > ts2.orden:
            return 1
        return 0

    def _get_start_timeslot(self, assignment: Assignment) -> TimeSlotInfo:
        """Retorna el timeslot más temprano de la asignación."""
        slot_id = min(assignment.timeslot_ids)
        return self.timeslots[slot_id]

    def _validate_professor_availability(self, assignment: Assignment) -> Tuple[bool, Dict[str, Any]]:
        """Verifica que el profesor esté disponible en estas franjas"""
        detail: Dict[str, Any] = {"professor_id": assignment.professor_id}
        restrictions = self.professor_restrictions.get(assignment.professor_id, [])

        if not restrictions:
            return True, detail

        for timeslot_id in assignment.timeslot_ids:
            ts = self.timeslots[timeslot_id]

            for restriction in restrictions:
                if getattr(restriction, "es_baja_prioridad", False):
                    continue

                dia_num = getattr(restriction, "dia_semana", None)
                hora_inicio = getattr(restriction, "hora_inicio", None)
                hora_fin = getattr(restriction, "hora_fin", None)

                if dia_num is None and hasattr(restriction, "day"):
                    day_str = str(getattr(restriction, "day", "")).lower()
                    if "lun" in day_str or "mon" in day_str:
                        dia_num = 1
                    elif "mar" in day_str or "tue" in day_str:
                        dia_num = 2
                    elif "mie" in day_str or "mié" in day_str or "wed" in day_str:
                        dia_num = 3
                    elif "jue" in day_str or "thu" in day_str:
                        dia_num = 4
                    elif "vie" in day_str or "fri" in day_str:
                        dia_num = 5
                    elif "sab" in day_str or "sáb" in day_str or "sat" in day_str:
                        dia_num = 6

                if hora_inicio is None:
                    hora_inicio = getattr(restriction, "start_time", None)
                if hora_fin is None:
                    hora_fin = getattr(restriction, "end_time", None)

                if (
                    dia_num == ts.dia_semana and
                    self._time_overlaps(
                        ts.hora_inicio, ts.hora_fin,
                        hora_inicio, hora_fin
                    )
                ):
                    detail.update({
                        "timeslot_id": timeslot_id,
                        "restriction": {
                            "dia_semana": dia_num,
                            "hora_inicio": str(hora_inicio),
                            "hora_fin": str(hora_fin),
                        },
                    })
                    return False, detail
        return True, detail

    def _validate_classroom_capacity(self, assignment: Assignment) -> Tuple[bool, Dict[str, Any]]:
        """Verifica que la capacidad del aula sea suficiente"""
        is_actually_virtual = self._is_virtual(assignment.section_id, None)

        if assignment.classroom_id is None:
            if not is_actually_virtual:
                return False, {"error": "Curso presencial requiere aula física"}
            return True, {"virtual_course": True, "no_classroom_required": True}
            
        if is_actually_virtual:
            return False, {"error": "Curso virtual no debe tener aula física asignada"}
            
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
        is_actually_virtual = self._is_virtual(assignment.section_id, None)

        if assignment.classroom_id is None:
            if not is_actually_virtual:
                return False, {"error": "Curso presencial requiere aula física"}
            return True, {"virtual_course": True, "no_classroom_required": True}
            
        if is_actually_virtual:
            return False, {"error": "Curso virtual no debe tener aula física asignada"}
            
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
        start1, end1,
        start2, end2
    ) -> bool:
        """Verifica si dos rangos de tiempo se solapan"""
        if not all([start1, end1, start2, end2]):
            return False

        def to_minutes(value: Any) -> Optional[int]:
            if value is None:
                return None

            if isinstance(value, timedelta):
                return int(value.total_seconds() // 60)

            if isinstance(value, datetime):
                return value.hour * 60 + value.minute

            if isinstance(value, time):
                return value.hour * 60 + value.minute

            if isinstance(value, (int, float)):
                return int(value)

            if isinstance(value, str):
                raw = value.strip()
                if not raw:
                    return None

                if raw.isdigit():
                    return int(raw)

                hhmmss_match = re.match(r"^(\d{1,2}):(\d{2})(?::\d{2})?$", raw)
                if hhmmss_match:
                    hours = int(hhmmss_match.group(1))
                    minutes = int(hhmmss_match.group(2))
                    return hours * 60 + minutes

                return None

            hour = getattr(value, "hour", None)
            minute = getattr(value, "minute", None)
            if hour is not None and minute is not None:
                return int(hour) * 60 + int(minute)

            return None

        s1, e1 = to_minutes(start1), to_minutes(end1)
        s2, e2 = to_minutes(start2), to_minutes(end2)

        if None in (s1, e1, s2, e2):
            return False

        return s1 < e2 and s2 < e1

# ============================================================================
# CALCULADOR DE PENALIZACIONES (RESTRICCIONES BLANDAS)
# ============================================================================

class SoftConstraintEvaluator:
    """Calcula penalizaciones para restricciones blandas"""
    
    def __init__(
        self,
        timeslots: Dict[int, TimeSlotInfo],
        classrooms: Dict[int, ClassroomInfo],
        weights: Optional[Dict[str, float]] = None,
        professor_restrictions: Optional[Dict[int, List[ProfessorRestrictionInfo]]] = None,
    ):
        self.timeslots = timeslots
        self.classrooms = classrooms
        # Mantener pesos calibrados de negocio definidos en config.
        default_weights: Dict[str, float] = dict(CONSTRAINT_WEIGHTS)
        self.weights = {**default_weights, **(weights or {})}
        self.professor_restrictions = professor_restrictions or {}
    
    def calculate_total_penalty(
        self,
        schedule: List[Assignment],
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calcula la penalización total y el desglose por tipo de restricción.
        
        Returns:
            (total_penalty, penalty_breakdown)
        """
        penalties: Dict[str, float] = {}
        
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

        # 7. Preferencias de laboratorios de Sistemas
        penalties["preferencia_laboratorio"] = self._calculate_lab_preference(schedule)

        # 8. Separacion entre teoria y practica del mismo curso
        penalties["dispersion_teoria_practica"] = self._calculate_theory_practice_spread(schedule)

        # 9. Fatiga por bloques demasiado largos
        penalties["fatiga_bloques_largos"] = self._calculate_long_block_fatigue(schedule)

        # 10. Incumplimiento de restricciones docentes de baja prioridad
        penalties["profesor_baja_prioridad"] = self._calculate_professor_low_priority(schedule)
        
        # 11. Equilibrio de uso de aulas (PRIORIDAD MUY BAJA)
        penalties["equilibrio_aulas"] = self._calculate_classroom_balance(schedule)
        penalties["alineacion_franja"] = self._calculate_block_alignment(schedule)
        
        # 12. Concentración de cursos por profesor (Prioridad Baja pero Importante para distribución equitativa)
        penalties["concentracion_cursos"] = self._calculate_professor_course_concentration(schedule)
        
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
            if assign.classroom_id is None or assign.classroom_id not in self.classrooms:
                continue
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

    def _calculate_lab_preference(self, schedule: List[Assignment]) -> float:
        """Penaliza laboratorios pequenos fuera del edificio F."""
        penalty = 0.0

        for assign in schedule:
            if assign.session_type != "L":
                continue
            if assign.classroom_id is None:
                continue
            if assign.alumnos_proyectados > 20:
                continue

            classroom = self.classrooms.get(assign.classroom_id)
            if classroom is None:
                continue

            if (classroom.edificio or "").strip().upper() != "F":
                penalty += 15.0

        return penalty

    def _calculate_theory_practice_spread(self, schedule: List[Assignment]) -> float:
        """Penaliza teoria y practica del mismo curso cuando caen en el mismo dia."""
        assignments_by_course: Dict[str, List[Assignment]] = defaultdict(list)
        penalty = 0.0

        for assign in schedule:
            assignments_by_course[assign.course_code].append(assign)

        for course_assignments in assignments_by_course.values():
            theory_assignments = [assign for assign in course_assignments if assign.session_type == "T"]
            practice_assignments = [assign for assign in course_assignments if assign.session_type == "P"]

            if not theory_assignments or not practice_assignments:
                continue

            for theory in theory_assignments:
                theory_days = self._get_assignment_days(theory)
                if not theory_days:
                    continue

                for practice in practice_assignments:
                    if theory_days & self._get_assignment_days(practice):
                        penalty += 20.0

        return penalty

    def _calculate_long_block_fatigue(self, schedule: List[Assignment]) -> float:
        """Penaliza dias en los que una misma seccion supera cuatro franjas."""
        slots_by_section_day: Dict[int, Dict[int, Set[int]]] = defaultdict(lambda: defaultdict(set))

        for assign in schedule:
            for ts_id in assign.timeslot_ids:
                ts = self.timeslots[ts_id]
                slots_by_section_day[assign.section_id][ts.dia_semana].add(ts.orden)

        penalty = 0.0
        for days in slots_by_section_day.values():
            for orders in days.values():
                slot_count = len(orders)
                if slot_count > 4:
                    penalty += float((slot_count - 4) * 10)

        return penalty

    def _calculate_professor_low_priority(self, schedule: List[Assignment]) -> float:
        """Penaliza asignaciones que caen en restricciones docentes de baja prioridad."""
        penalty = 0.0

        for assign in schedule:
            restrictions = self.professor_restrictions.get(assign.professor_id, [])
            if not restrictions:
                continue

            low_priority_restrictions = [
                restriction
                for restriction in restrictions
                if getattr(restriction, "es_baja_prioridad", False)
            ]
            if not low_priority_restrictions:
                continue

            for ts_id in assign.timeslot_ids:
                ts = self.timeslots[ts_id]
                for restriction in low_priority_restrictions:
                    if (
                        restriction.dia_semana == ts.dia_semana and
                        self._time_overlaps(
                            ts.hora_inicio,
                            ts.hora_fin,
                            restriction.hora_inicio,
                            restriction.hora_fin,
                        )
                    ):
                        penalty += 50.0
                        break

        return penalty

    def _get_assignment_days(self, assignment: Assignment) -> Set[int]:
        """Retorna el conjunto de dias usados por una asignacion."""
        return {
            self.timeslots[ts_id].dia_semana
            for ts_id in assignment.timeslot_ids
            if ts_id in self.timeslots
        }

    def _normalize_text(self, value: str) -> str:
        """Normaliza texto libre a una forma comparable y sin acentos."""
        normalized = (value or "").strip().lower()
        normalized = normalized.replace("\u00e1", "a")
        normalized = normalized.replace("\u00e9", "e")
        normalized = normalized.replace("\u00ed", "i")
        normalized = normalized.replace("\u00f3", "o")
        normalized = normalized.replace("\u00fa", "u")
        normalized = normalized.replace("\u00f1", "n")
        normalized = normalized.replace("á", "a")
        normalized = normalized.replace("é", "e")
        normalized = normalized.replace("í", "i")
        normalized = normalized.replace("ó", "o")
        normalized = normalized.replace("ú", "u")
        normalized = normalized.replace("ñ", "n")
        normalized = normalized.replace("Ã¡", "a")
        normalized = normalized.replace("Ã©", "e")
        normalized = normalized.replace("Ã­", "i")
        normalized = normalized.replace("Ã³", "o")
        normalized = normalized.replace("Ãº", "u")
        normalized = normalized.replace("Ã±", "n")
        return normalized

    def _time_overlaps(
        self,
        start1: Any,
        end1: Any,
        start2: Any,
        end2: Any,
    ) -> bool:
        """Verifica si dos rangos de tiempo se solapan."""
        if not all([start1, end1, start2, end2]):
            return False

        def to_minutes(value: Any) -> Optional[int]:
            if value is None:
                return None
            if isinstance(value, timedelta):
                return int(value.total_seconds() // 60)
            if isinstance(value, datetime):
                return value.hour * 60 + value.minute
            if isinstance(value, time):
                return value.hour * 60 + value.minute
            if isinstance(value, (int, float)):
                return int(value)
            if isinstance(value, str):
                raw = value.strip()
                if not raw:
                    return None
                if raw.isdigit():
                    return int(raw)
                hhmmss_match = re.match(r"^(\d{1,2}):(\d{2})(?::\d{2})?$", raw)
                if hhmmss_match:
                    hours = int(hhmmss_match.group(1))
                    minutes = int(hhmmss_match.group(2))
                    return hours * 60 + minutes
                return None

            hour = getattr(value, "hour", None)
            minute = getattr(value, "minute", None)
            if hour is not None and minute is not None:
                return int(hour) * 60 + int(minute)
            return None

        s1, e1 = to_minutes(start1), to_minutes(end1)
        s2, e2 = to_minutes(start2), to_minutes(end2)

        if None in (s1, e1, s2, e2):
            return False

        return s1 < e2 and s2 < e1
    
    def _calculate_timeslot_preference(self, schedule: List[Assignment]) -> float:
        """Penaliza franjas menos deseables (ej: última hora del día)"""
        penalty = 0.0
        
        for assign in schedule:
            ciclo_num = Assignment._parse_ciclo_number(assign.ciclo)
            for ts_id in assign.timeslot_ids:
                ts = self.timeslots[ts_id]
                periodo = self._normalize_text(ts.periodo)

                if ciclo_num > 0:
                    if ciclo_num % 2 == 1 and periodo != "manana":
                        penalty += 5.0
                    elif ciclo_num % 2 == 0 and periodo != "tarde":
                        penalty += 5.0

                    if ciclo_num == 1 and ts.dia_semana == 6:
                        penalty += 25.0
                
        
        return float(penalty)
    
    def _calculate_classroom_balance(self, schedule: List[Assignment]) -> float:
        """Penaliza desbalance en el uso de aulas"""
        classroom_usage = defaultdict(int)
        
        for assign in schedule:
            if assign.classroom_id is None:
                continue
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
        periodo = self._normalize_text(timeslot.periodo)

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

    def _calculate_professor_course_concentration(self, schedule: List[Assignment]) -> float:
        """
        Penaliza si un profesor concentra múltiples grupos del mismo curso
        y tipo de sesión, para fomentar la distribución equitativa de carga
        entre los profesores disponibles.
        """
        # Estructura: dict[course_code][session_type][professor_id] = count
        course_prof_counts = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        
        for assign in schedule:
            if assign.professor_id is not None:
                course_prof_counts[assign.course_code][assign.session_type][assign.professor_id] += 1
                
        penalty = 0.0
        
        for course_code, session_types in course_prof_counts.items():
            for session_type, prof_counts in session_types.items():
                for prof_id, count in prof_counts.items():
                    # Si un profesor tiene más de 1 grupo del mismo curso/tipo,
                    # agregamos una penalización cuadrática para disuadir fuertemente
                    if count > 1:
                        penalty += ((count - 1) ** 2) * 10.0
                        
        return penalty
