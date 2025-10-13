"""
Analyzer for ACO Timetabling Solution
Analiza la solución generada por el algoritmo ACO y genera reportes detallados
"""

import json
import logging
from collections import defaultdict, Counter
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

class TimetablingSolutionAnalyzer:
    """Analizador de soluciones de horarios generados por ACO"""
    
    def __init__(self, solution_file: str):
        with open(solution_file, 'r', encoding='utf-8') as f:
            self.solution_data = json.load(f)
        
        self.assignments = self.solution_data['assignments']
        self.metadata = self.solution_data['metadata']
        
        logger.info(f"Cargada solución con {len(self.assignments)} asignaciones")
    
    def generate_comprehensive_report(self) -> Dict:
        """Genera un reporte comprensivo de la solución"""
        
        report = {
            'executive_summary': self._get_executive_summary(),
            'resource_utilization': self._analyze_resource_utilization(),
            'schedule_distribution': self._analyze_schedule_distribution(),
            'constraint_analysis': self._analyze_constraints(),
            'course_coverage': self._analyze_course_coverage(),
            'recommendations': self._generate_recommendations()
        }
        
        return report
    
    def _get_executive_summary(self) -> Dict:
        """Resumen ejecutivo de la solución"""
        total_tasks = self.metadata['total_tasks']
        successful = self.metadata['successful_assignments']
        success_rate = self.metadata['success_rate']
        
        return {
            'total_scheduling_tasks': total_tasks,
            'successful_assignments': successful,
            'success_rate_percentage': round(success_rate, 1),
            'unassigned_tasks': total_tasks - successful,
            'final_fitness': self.metadata['final_fitness'],
            'constraint_violations': self.metadata['violations'],
            'algorithm_parameters': self.metadata['parameters'],
            'quality_assessment': 'EXCELENTE' if success_rate > 60 and sum(self.metadata['violations'].values()) == 0 else 'BUENO' if success_rate > 40 else 'NECESITA MEJORAS'
        }
    
    def _analyze_resource_utilization(self) -> Dict:
        """Analiza la utilización de recursos (profesores, aulas, franjas)"""
        
        # Utilización de profesores
        professor_usage = Counter(a['professor_id'] for a in self.assignments)
        professor_stats = {
            'total_professors_used': len(professor_usage),
            'average_load_per_professor': round(sum(professor_usage.values()) / len(professor_usage), 2),
            'max_load_per_professor': max(professor_usage.values()),
            'min_load_per_professor': min(professor_usage.values()),
            'professors_by_load': dict(Counter(professor_usage.values()))
        }
        
        # Utilización de aulas
        classroom_usage = Counter(a['classroom_id'] for a in self.assignments)
        classroom_stats = {
            'total_classrooms_used': len(classroom_usage),
            'average_usage_per_classroom': round(sum(classroom_usage.values()) / len(classroom_usage), 2),
            'max_usage_per_classroom': max(classroom_usage.values()),
            'min_usage_per_classroom': min(classroom_usage.values()),
            'classrooms_by_usage': dict(Counter(classroom_usage.values()))
        }
        
        # Utilización de franjas horarias
        time_slot_usage = Counter((a['day'], a['time_slot']) for a in self.assignments)
        time_stats = {
            'total_time_slots_used': len(time_slot_usage),
            'average_assignments_per_slot': round(sum(time_slot_usage.values()) / len(time_slot_usage), 2),
            'max_assignments_per_slot': max(time_slot_usage.values()),
            'busiest_time_slots': [k for k, v in time_slot_usage.most_common(5)]
        }
        
        return {
            'professors': professor_stats,
            'classrooms': classroom_stats,
            'time_slots': time_stats
        }
    
    def _analyze_schedule_distribution(self) -> Dict:
        """Analiza la distribución de horarios"""
        
        # Distribución por día
        day_names = {1: 'Lunes', 2: 'Martes', 3: 'Miércoles', 4: 'Jueves', 5: 'Viernes', 6: 'Sábado'}
        by_day = Counter(day_names[a['day']] for a in self.assignments)
        
        # Distribución por periodo
        by_period = Counter(a['period'] for a in self.assignments)
        
        # Distribución por tipo de sección
        by_section_type = Counter(a['section_type'] for a in self.assignments)
        
        # Distribución por ciclo
        cycle_distribution = defaultdict(list)
        for assignment in self.assignments:
            course_id = assignment['course_id']
            # Extraer ciclo del course_id o usar lógica específica
            cycle_distribution['general'].append(assignment)
        
        return {
            'by_day': dict(by_day),
            'by_period': dict(by_period),
            'by_section_type': dict(by_section_type),
            'busiest_day': by_day.most_common(1)[0] if by_day else None,
            'preferred_period': by_period.most_common(1)[0] if by_period else None,
            'section_type_balance': dict(by_section_type)
        }
    
    def _analyze_constraints(self) -> Dict:
        """Analiza el cumplimiento de restricciones"""
        
        violations = self.metadata['violations']
        
        constraint_analysis = {
            'hard_constraints': {
                'professor_conflicts': violations['professor_conflict'],
                'classroom_conflicts': violations['classroom_conflict'],
                'capacity_violations': violations['capacity_exceeded'],
                'lab_assignment_violations': violations['lab_assignment_rule'],
                'professor_overload': violations['professor_overload']
            },
            'soft_constraints': {
                'cycle_time_preferences': violations['cycle_time_preference']
            },
            'total_violations': sum(violations.values()),
            'constraint_satisfaction_rate': 100.0 if sum(violations.values()) == 0 else 0.0
        }
        
        # Análisis específico por restricción
        constraint_analysis['detailed_analysis'] = {
            'all_hard_constraints_satisfied': sum(constraint_analysis['hard_constraints'].values()) == 0,
            'all_soft_constraints_satisfied': sum(constraint_analysis['soft_constraints'].values()) == 0,
            'critical_issues': [k for k, v in violations.items() if v > 0],
            'compliance_level': 'PERFECTO' if sum(violations.values()) == 0 else 'CRÍTICO' if sum(constraint_analysis['hard_constraints'].values()) > 0 else 'BUENO'
        }
        
        return constraint_analysis
    
    def _analyze_course_coverage(self) -> Dict:
        """Analiza la cobertura de cursos"""
        
        # Agrupar asignaciones por curso
        by_course = defaultdict(list)
        for assignment in self.assignments:
            by_course[assignment['course_id']].append(assignment)
        
        course_stats = {}
        for course_id, assignments in by_course.items():
            # Contar por tipo de sección
            section_counts = Counter(a['section_type'] for a in assignments)
            
            course_stats[course_id] = {
                'total_assignments': len(assignments),
                'theory_groups': section_counts.get('teoria', 0),
                'practice_groups': section_counts.get('practica', 0),
                'lab_groups': section_counts.get('laboratorio', 0),
                'is_complete': len(assignments) > 0  # Lógica básica, se puede refinar
            }
        
        return {
            'total_courses_with_assignments': len(by_course),
            'course_statistics': course_stats,
            'coverage_summary': {
                'courses_with_theory': sum(1 for stats in course_stats.values() if stats['theory_groups'] > 0),
                'courses_with_practice': sum(1 for stats in course_stats.values() if stats['practice_groups'] > 0),
                'courses_with_labs': sum(1 for stats in course_stats.values() if stats['lab_groups'] > 0),
                'fully_covered_courses': sum(1 for stats in course_stats.values() if stats['is_complete'])
            }
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Genera recomendaciones basadas en el análisis"""
        
        recommendations = []
        
        # Basado en tasa de éxito
        success_rate = self.metadata['success_rate']
        if success_rate < 70:
            recommendations.append(f"📈 Mejorar tasa de éxito: actual {success_rate:.1f}%. Considerar agregar más recursos (aulas/profesores) o ajustar parámetros del algoritmo.")
        
        # Basado en violaciones
        violations = self.metadata['violations']
        if sum(violations.values()) == 0:
            recommendations.append("✅ ¡Excelente! No hay violaciones de restricciones. La solución cumple perfectamente con todas las reglas UPAO.")
        else:
            for constraint, count in violations.items():
                if count > 0:
                    recommendations.append(f"⚠️ Resolver {count} violaciones de {constraint}")
        
        # Basado en utilización de recursos
        # (Aquí se pueden agregar análisis más específicos)
        
        # Recomendaciones de mejora
        recommendations.append("🔄 Considerar ejecutar el algoritmo con más iteraciones para potencial mejora.")
        recommendations.append("📊 Implementar GraphSAGE para optimización híbrida en la siguiente fase.")
        recommendations.append("🖥️ Desarrollar interfaz visual para edición manual de conflictos restantes.")
        
        return recommendations
    
    def save_report(self, filename: str = "timetabling_analysis_report.json"):
        """Guarda el reporte de análisis"""
        
        report = self.generate_comprehensive_report()
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Reporte de análisis guardado en {filename}")
        return report
    
    def print_executive_summary(self):
        """Imprime un resumen ejecutivo en consola"""
        
        report = self.generate_comprehensive_report()
        summary = report['executive_summary']
        
        print("\n" + "="*80)
        print("🎯 REPORTE EJECUTIVO - SOLUCIÓN DE HORARIOS UPAO")
        print("="*80)
        
        print(f"📋 Tareas totales de programación: {summary['total_scheduling_tasks']}")
        print(f"✅ Asignaciones exitosas: {summary['successful_assignments']}")
        print(f"📊 Tasa de éxito: {summary['success_rate_percentage']}%")
        print(f"❌ Tareas no asignadas: {summary['unassigned_tasks']}")
        print(f"🎯 Fitness final: {summary['final_fitness']}")
        print(f"🏆 Calidad general: {summary['quality_assessment']}")
        
        print(f"\n🔍 VIOLACIONES DE RESTRICCIONES:")
        violations = summary['constraint_violations']
        if sum(violations.values()) == 0:
            print("   ✅ ¡PERFECTO! No hay violaciones de ningún tipo")
        else:
            for constraint, count in violations.items():
                status = "✅" if count == 0 else "❌"
                print(f"   {status} {constraint}: {count}")
        
        print(f"\n⚙️ PARÁMETROS DEL ALGORITMO:")
        params = summary['algorithm_parameters']
        for param, value in params.items():
            print(f"   • {param}: {value}")
        
        print(f"\n💡 RECOMENDACIONES PRINCIPALES:")
        recommendations = report['recommendations'][:3]  # Top 3
        for i, rec in enumerate(recommendations, 1):
            print(f"   {i}. {rec}")
        
        print("="*80)


def main():
    """Función principal para analizar la solución ACO"""
    
    logging.basicConfig(level=logging.INFO)
    
    # Analizar la solución generada
    analyzer = TimetablingSolutionAnalyzer('aco_optimized_final_solution.json')
    
    # Generar y mostrar resumen ejecutivo
    analyzer.print_executive_summary()
    
    # Guardar reporte completo
    report = analyzer.save_report('upao_timetabling_final_report.json')
    
    print(f"\n📄 Reporte completo guardado en: upao_timetabling_final_report.json")
    print(f"📊 Análisis detallado incluye: utilización de recursos, distribución de horarios, cobertura de cursos")


if __name__ == "__main__":
    main()