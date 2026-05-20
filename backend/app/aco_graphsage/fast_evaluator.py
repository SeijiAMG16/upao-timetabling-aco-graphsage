"""
Validador Fast-Track para Movimientos en Tiempo Real (Human-in-the-Loop)
Permite evaluar rápidamente si un movimiento manual (Drag & Drop) es válido
y cuál es el impacto en la función de costo, sin recalcular todo el ACO.
"""

from typing import List, Dict, Any, Optional, Tuple
from copy import deepcopy

from .constraints import (
    Assignment, 
    HardConstraintValidator, 
    SoftConstraintEvaluator,
    TimeSlotInfo,
    ClassroomInfo,
    ProfessorRestrictionInfo
)

class MovementValidator:
    """
    Orquestador para validación rápida de movimientos manuales.
    Utiliza los validadores existentes pero enfocados en evaluación delta/local.
    """
    def __init__(
        self,
        timeslots: Dict[int, TimeSlotInfo],
        classrooms: Dict[int, ClassroomInfo],
        professor_restrictions: Dict[int, List[ProfessorRestrictionInfo]],
        sections_by_league: Dict[Tuple[str, int], List[int]],
        league_session_types: Dict[Tuple[str, int], set],
        section_session_types: Dict[int, str],
        weights: Optional[Dict[str, float]] = None,
        sections_by_block: Optional[Dict[str, List[int]]] = None,
        section_modalities: Optional[Dict[int, str]] = None,
    ):
        # Instanciar los validadores base
        self.hard_validator = HardConstraintValidator(
            timeslots=timeslots,
            classrooms=classrooms,
            professor_restrictions=professor_restrictions,
            sections_by_league=sections_by_league,
            league_session_types=league_session_types,
            section_session_types=section_session_types,
            sections_by_block=sections_by_block,
            section_modalities=section_modalities
        )
        
        self.soft_evaluator = SoftConstraintEvaluator(
            timeslots=timeslots,
            classrooms=classrooms,
            weights=weights,
            professor_restrictions=professor_restrictions
        )
        
    def evaluate_move(
        self,
        assignment_to_move: Assignment,
        new_timeslot_ids: List[int],
        new_classroom_id: Optional[int],
        current_schedule: List[Assignment],
    ) -> Dict[str, Any]:
        """
        Evalúa un movimiento propuesto aislando el bloque modificado.
        
        Retorna:
            dict con formato:
            {
                "valido": bool,
                "mensaje": str (si falla),
                "detalle": dict (si falla),
                "nuevo_costo": float,
                "delta_costo": float,
                "penalizaciones": dict
            }
        """
        # 1. Separar el resto del horario (quitando la asignación original)
        rest_of_schedule = [
            a for a in current_schedule 
            if a.section_id != assignment_to_move.section_id
        ]
        
        # 2. Crear el movimiento candidato
        candidate_assignment = deepcopy(assignment_to_move)
        candidate_assignment.timeslot_ids = new_timeslot_ids
        candidate_assignment.classroom_id = new_classroom_id
        
        # 3. Validar Restricciones Duras (O(N) contra el resto del horario)
        is_valid, message, detail = self.hard_validator.validate_all(
            assignment=candidate_assignment,
            current_schedule=rest_of_schedule,
            return_details=True
        )
        
        if not is_valid:
            return {
                "valido": False,
                "mensaje": message,
                "detalle": detail,
                "nuevo_costo": None,
                "delta_costo": None,
                "penalizaciones": None
            }
            
        # 4. Calcular Costos Blandos (Soft Constraints)
        # Costo actual (antes del movimiento)
        current_cost, _ = self.soft_evaluator.calculate_total_penalty(current_schedule)
        
        # Costo propuesto (después del movimiento)
        proposed_schedule = rest_of_schedule + [candidate_assignment]
        proposed_cost, proposed_penalties = self.soft_evaluator.calculate_total_penalty(proposed_schedule)
        
        delta = proposed_cost - current_cost
        
        return {
            "valido": True,
            "mensaje": "Movimiento válido",
            "detalle": None,
            "nuevo_costo": proposed_cost,
            "delta_costo": delta,
            "penalizaciones": proposed_penalties
        }
