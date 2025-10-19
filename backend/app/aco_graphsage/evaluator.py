"""
Evaluador de Métricas para Soluciones de Horarios

Calcula y registra métricas de calidad de las soluciones generadas.
Guarda resultados en la tabla algorithm_executions.
"""

from typing import Dict, List, Tuple
from datetime import datetime
from collections import defaultdict
import json

from .aco_engine import Solution
from .constraints import Assignment, TimeSlotInfo, ClassroomInfo


# ============================================================================
# CALCULADOR DE MÉTRICAS
# ============================================================================

class SolutionEvaluator:
    """Evalúa la calidad de una solución generada"""
    
    def __init__(
        self,
        timeslots: Dict[int, TimeSlotInfo],
        classrooms: Dict[int, ClassroomInfo],
    ):
        self.timeslots = timeslots
        self.classrooms = classrooms
    
    def evaluate(self, solution: Solution) -> Dict:
        """
        Calcula todas las métricas para una solución.
        
        Returns:
            Diccionario con todas las métricas
        """
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'is_valid': solution.is_valid,
            'n_assignments': len(solution.assignments),
            'total_cost': solution.total_cost,
        }
        
        if not solution.is_valid:
            return metrics
        
        # Métricas de conflictos (siempre 0 si es válida, pero contamos por si acaso)
        metrics['conflictos_profesor'] = self._count_professor_conflicts(solution.assignments)
        metrics['conflictos_aula'] = self._count_classroom_conflicts(solution.assignments)
        metrics['conflictos_curriculo'] = self._count_curriculum_conflicts(solution.assignments)
        
        # Métricas de utilización
        metrics['utilizacion_aulas'] = self._calculate_classroom_utilization(solution.assignments)
        metrics['utilizacion_profesores'] = self._calculate_professor_utilization(solution.assignments)
        
        # Métricas de calidad (restricciones blandas)
        metrics['huecos_estudiantes'] = solution.soft_penalties.get('huecos_estudiantes', 0)
        metrics['huecos_profesores'] = solution.soft_penalties.get('huecos_profesores', 0)
        metrics['cambios_edificio'] = solution.soft_penalties.get('cambio_edificio', 0)
        metrics['compacidad_dia'] = solution.soft_penalties.get('compacidad_dia', 0)
        
        # Métricas de distribución
        metrics['distribucion_por_dia'] = self._calculate_day_distribution(solution.assignments)
        metrics['distribucion_por_periodo'] = self._calculate_period_distribution(solution.assignments)
        
        # Métricas de aulas
        metrics['uso_por_edificio'] = self._calculate_building_usage(solution.assignments)
        metrics['aulas_subutilizadas'] = self._count_underutilized_classrooms(solution.assignments)
        
        # Función objetivo desagregada
        metrics['soft_penalties_breakdown'] = solution.soft_penalties
        
        return metrics
    
    def _count_professor_conflicts(self, assignments: List[Assignment]) -> int:
        """Cuenta conflictos de solapamiento de profesores"""
        conflicts = 0
        by_professor = defaultdict(list)
        
        for assign in assignments:
            by_professor[assign.professor_id].append(assign)
        
        for prof_id, prof_assigns in by_professor.items():
            for i, a1 in enumerate(prof_assigns):
                for a2 in prof_assigns[i+1:]:
                    if set(a1.timeslot_ids) & set(a2.timeslot_ids):
                        conflicts += 1
        
        return conflicts
    
    def _count_classroom_conflicts(self, assignments: List[Assignment]) -> int:
        """Cuenta conflictos de solapamiento de aulas"""
        conflicts = 0
        by_classroom = defaultdict(list)
        
        for assign in assignments:
            by_classroom[assign.classroom_id].append(assign)
        
        for classroom_id, classroom_assigns in by_classroom.items():
            for i, a1 in enumerate(classroom_assigns):
                for a2 in classroom_assigns[i+1:]:
                    if set(a1.timeslot_ids) & set(a2.timeslot_ids):
                        conflicts += 1
        
        return conflicts
    
    def _count_curriculum_conflicts(self, assignments: List[Assignment]) -> int:
        """Cuenta conflictos curriculares (mismo ciclo)"""
        conflicts = 0
        by_curriculum = defaultdict(list)
        
        for assign in assignments:
            by_curriculum[assign.ciclo].append(assign)
        
        for ciclo, ciclo_assigns in by_curriculum.items():
            for i, a1 in enumerate(ciclo_assigns):
                for a2 in ciclo_assigns[i+1:]:
                    # Solo contar si son cursos diferentes o ligas diferentes
                    if (a1.course_code != a2.course_code or 
                        a1.league_id != a2.league_id):
                        if set(a1.timeslot_ids) & set(a2.timeslot_ids):
                            conflicts += 1
        
        return conflicts
    
    def _calculate_classroom_utilization(self, assignments: List[Assignment]) -> float:
        """
        Calcula el porcentaje de utilización de aulas.
        
        Utilización = horas ocupadas / horas disponibles
        """
        total_slots = len(self.timeslots) * len(self.classrooms)
        
        occupied_slots = 0
        for assign in assignments:
            occupied_slots += len(assign.timeslot_ids)
        
        return (occupied_slots / total_slots * 100) if total_slots > 0 else 0.0
    
    def _calculate_professor_utilization(self, assignments: List[Assignment]) -> float:
        """Calcula utilización promedio de profesores"""
        by_professor = defaultdict(set)
        
        for assign in assignments:
            by_professor[assign.professor_id].update(assign.timeslot_ids)
        
        if not by_professor:
            return 0.0
        
        total_hours = sum(len(slots) for slots in by_professor.values())
        avg_hours = total_hours / len(by_professor)
        
        # Asumir semana de 40 horas = ~48 bloques de 50 min
        max_hours = 48
        
        return (avg_hours / max_hours * 100)
    
    def _calculate_day_distribution(self, assignments: List[Assignment]) -> Dict[int, int]:
        """Cuenta asignaciones por día de la semana"""
        by_day = defaultdict(int)
        
        for assign in assignments:
            for ts_id in assign.timeslot_ids:
                ts = self.timeslots[ts_id]
                by_day[ts.dia_semana] += 1
        
        return dict(by_day)
    
    def _calculate_period_distribution(self, assignments: List[Assignment]) -> Dict[str, int]:
        """Cuenta asignaciones por periodo (mañana/tarde/noche)"""
        by_period = defaultdict(int)
        
        for assign in assignments:
            for ts_id in assign.timeslot_ids:
                ts = self.timeslots[ts_id]
                by_period[ts.periodo] += 1
        
        return dict(by_period)
    
    def _calculate_building_usage(self, assignments: List[Assignment]) -> Dict[str, int]:
        """Cuenta uso por edificio"""
        by_building = defaultdict(int)
        
        for assign in assignments:
            classroom = self.classrooms[assign.classroom_id]
            by_building[classroom.edificio] += len(assign.timeslot_ids)
        
        return dict(by_building)
    
    def _count_underutilized_classrooms(self, assignments: List[Assignment]) -> int:
        """Cuenta aulas con baja utilización (<20%)"""
        by_classroom = defaultdict(int)
        
        for assign in assignments:
            by_classroom[assign.classroom_id] += len(assign.timeslot_ids)
        
        total_slots = len(self.timeslots)
        threshold = total_slots * 0.2
        
        underutilized = sum(
            1 for usage in by_classroom.values()
            if usage < threshold
        )
        
        return underutilized
    
    def generate_report(self, metrics: Dict) -> str:
        """Genera un reporte legible de las métricas"""
        lines = [
            "=" * 80,
            "REPORTE DE EVALUACIÓN DE HORARIO",
            "=" * 80,
            "",
            f"Timestamp: {metrics['timestamp']}",
            f"Solución válida: {'✅ Sí' if metrics['is_valid'] else '❌ No'}",
            f"Número de asignaciones: {metrics['n_assignments']}",
            f"Costo total: {metrics['total_cost']:.2f}",
            "",
            "CONFLICTOS (deben ser 0):",
            f"  - Profesores: {metrics['conflictos_profesor']}",
            f"  - Aulas: {metrics['conflictos_aula']}",
            f"  - Currículo: {metrics['conflictos_curriculo']}",
            "",
            "UTILIZACIÓN:",
            f"  - Aulas: {metrics['utilizacion_aulas']:.1f}%",
            f"  - Profesores: {metrics['utilizacion_profesores']:.1f}%",
            "",
            "CALIDAD (restricciones blandas):",
            f"  - Huecos estudiantes: {metrics['huecos_estudiantes']:.1f}",
            f"  - Huecos profesores: {metrics['huecos_profesores']:.1f}",
            f"  - Cambios de edificio: {metrics['cambios_edificio']:.1f}",
            f"  - Compacidad del día: {metrics['compacidad_dia']:.1f}",
            "",
            "DISTRIBUCIÓN POR DÍA:",
        ]
        
        for dia, count in sorted(metrics['distribucion_por_dia'].items()):
            dia_names = {1: "Lun", 2: "Mar", 3: "Mié", 4: "Jue", 5: "Vie", 6: "Sáb"}
            lines.append(f"  - {dia_names.get(dia, dia)}: {count} bloques")
        
        lines.extend([
            "",
            "DISTRIBUCIÓN POR PERIODO:",
        ])
        
        for periodo, count in sorted(metrics['distribucion_por_periodo'].items()):
            lines.append(f"  - {periodo.capitalize()}: {count} bloques")
        
        lines.extend([
            "",
            "USO POR EDIFICIO:",
        ])
        
        for edificio, count in sorted(metrics['uso_por_edificio'].items()):
            lines.append(f"  - Edificio {edificio}: {count} bloques")
        
        lines.extend([
            "",
            f"Aulas subutilizadas (<20%): {metrics['aulas_subutilizadas']}",
            "",
            "=" * 80,
        ])
        
        return "\n".join(lines)


# ============================================================================
# PERSISTENCIA EN BASE DE DATOS
# ============================================================================

def save_execution_to_db(
    db_session,
    metrics: Dict,
    parameters: Dict,
    execution_time: float,
    status: str = "completed",
):
    """
    Guarda los resultados de una ejecución en la tabla algorithm_executions.
    
    Args:
        db_session: Sesión de SQLAlchemy
        metrics: Diccionario de métricas
        parameters: Parámetros usados en la ejecución
        execution_time: Tiempo de ejecución en segundos
        status: Estado de la ejecución
    """
    from app.models import AlgorithmExecution
    
    execution = AlgorithmExecution(
        algoritmo="ACO+GraphSAGE",
        parametros=json.dumps(parameters, indent=2),
        estado=status,
        tiempo_ejecucion=execution_time,
        funcion_objetivo=metrics.get('total_cost', 0.0),
        conflictos_profesor=metrics.get('conflictos_profesor', 0),
        conflictos_aula=metrics.get('conflictos_aula', 0),
        conflictos_curriculo=metrics.get('conflictos_curriculo', 0),
        utilizacion_aulas=metrics.get('utilizacion_aulas', 0.0),
        huecos_estudiantes=metrics.get('huecos_estudiantes', 0.0),
        huecos_profesores=metrics.get('huecos_profesores', 0.0),
        log_ejecucion=json.dumps(metrics, indent=2),
    )
    
    db_session.add(execution)
    db_session.commit()
    
    return execution.id


def save_solution_to_db(
    db_session,
    solution: Solution,
    execution_id: int,
    algorithm_name: str = "ACO+GraphSAGE",
):
    """
    Guarda una solución en la tabla schedule_assignments.
    
    Args:
        db_session: Sesión de SQLAlchemy
        solution: Solución a guardar
        execution_id: ID de la ejecución en algorithm_executions
        algorithm_name: Nombre del algoritmo
    """
    from app.models import ScheduleAssignment
    
    # Limpiar asignaciones anteriores de esta ejecución (si existen)
    db_session.query(ScheduleAssignment).filter(
        ScheduleAssignment.algorithm_execution_id == execution_id
    ).delete()
    
    # Insertar nuevas asignaciones
    for assignment in solution.assignments:
        for timeslot_id in assignment.timeslot_ids:
            schedule_entry = ScheduleAssignment(
                section_id=assignment.original_section_id,
                professor_id=assignment.professor_id,
                classroom_id=assignment.classroom_id,
                timeslot_id=timeslot_id,
                generado_por_algoritmo=True,
                confianza_asignacion=1.0 - (solution.total_cost / 1000.0),  # Heurística
                algorithm_execution_id=execution_id,
            )
            db_session.add(schedule_entry)
    
    db_session.commit()
    
    print(f"✅ Guardadas {len(solution.assignments)} asignaciones en schedule_assignments")


# ============================================================================
# COMPARADOR DE SOLUCIONES
# ============================================================================

def compare_solutions(
    solution1: Solution,
    solution2: Solution,
    evaluator: SolutionEvaluator,
) -> Dict:
    """
    Compara dos soluciones y genera un reporte de diferencias.
    
    Returns:
        Diccionario con comparación
    """
    metrics1 = evaluator.evaluate(solution1)
    metrics2 = evaluator.evaluate(solution2)
    
    comparison = {
        'solution1': metrics1,
        'solution2': metrics2,
        'differences': {},
    }
    
    # Comparar métricas clave
    key_metrics = [
        'total_cost',
        'conflictos_profesor',
        'conflictos_aula',
        'utilizacion_aulas',
        'huecos_estudiantes',
    ]
    
    for metric in key_metrics:
        val1 = metrics1.get(metric, 0)
        val2 = metrics2.get(metric, 0)
        diff = val2 - val1
        improvement = -diff if metric == 'total_cost' or 'conflictos' in metric or 'huecos' in metric else diff
        
        comparison['differences'][metric] = {
            'value1': val1,
            'value2': val2,
            'difference': diff,
            'improvement': improvement,
            'improvement_pct': (improvement / val1 * 100) if val1 != 0 else 0,
        }
    
    return comparison
