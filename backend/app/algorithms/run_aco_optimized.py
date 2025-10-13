"""
Data Adapter for UPAO Projections to ACO Algorithm Format
Convierte los datos del Excel procesado al formato esperado por el algoritmo ACO
"""

import json
import logging
from typing import Dict, List, Set, Tuple

logger = logging.getLogger(__name__)

class DataAdapter:
    """Adaptador de datos para convertir proyecciones UPAO a formato ACO"""
    
    def __init__(self):
        self.time_periods = {
            'mañana': list(range(1, 7)),    # 07:00-12:30
            'tarde': list(range(7, 13)),    # 12:30-18:00 
            'noche': list(range(13, 17))    # 18:00-21:30
        }
        
    def _get_period_for_slot(self, franja: int) -> str:
        """Determina el periodo del día para una franja horaria"""
        if franja in self.time_periods['mañana']:
            return 'mañana'
        elif franja in self.time_periods['tarde']:
            return 'tarde'
        else:
            return 'noche'
    
    def convert_projections_to_aco_format(self, projections_file: str) -> Dict:
        """Convierte proyecciones UPAO al formato esperado por ACO"""
        
        # Cargar datos originales
        with open(projections_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        projections = data['projections']
        logger.info(f"Procesando {len(projections)} proyecciones de cursos")
        
        # Convertir cursos
        courses = []
        for proj in projections:
            course = {
                'id': proj['codigo_completo'],
                'nombre': proj['nombre_asignatura'],
                'ciclo': proj['ciclo_numerico'],
                'modalidad': proj['modalidad'],
                'grupos_teoria': proj['grupos_teoria'],
                'grupos_practica': proj['grupos_practica'],
                'grupos_laboratorio': proj['grupos_laboratorio'],
                'alumnos_teoria': proj['alumnos_teoria'] // max(1, proj['grupos_teoria']),
                'alumnos_practica': proj['alumnos_practica'] // max(1, proj['grupos_practica']) if proj['grupos_practica'] > 0 else 0,
                'alumnos_laboratorio': proj['alumnos_laboratorio'] // max(1, proj['grupos_laboratorio']) if proj['grupos_laboratorio'] > 0 else 0,
                'requiere_laboratorio': proj['requiere_laboratorio'],
                'requiere_practica': proj['requiere_practica']
            }
            courses.append(course)
        
        # Generar profesores (simulados basados en necesidades de cursos)
        professors = self._generate_professors(projections)
        
        # Generar aulas UPAO
        classrooms = self._generate_upao_classrooms()
        
        # Generar franjas horarias
        time_slots = self._generate_time_slots()
        
        converted_data = {
            'courses': courses,
            'professors': professors,
            'classrooms': classrooms,
            'time_slots': time_slots,
            'metadata': {
                'converted_from': projections_file,
                'total_courses': len(courses),
                'total_professors': len(professors),
                'total_classrooms': len(classrooms),
                'total_time_slots': len(time_slots)
            }
        }
        
        logger.info(f"Conversión completada: {len(courses)} cursos, {len(professors)} profesores, "
                   f"{len(classrooms)} aulas, {len(time_slots)} franjas horarias")
        
        return converted_data
    
    def _generate_professors(self, projections: List[Dict]) -> List[Dict]:
        """Genera profesores basados en las necesidades de los cursos"""
        professors = []
        
        # Calcular necesidades totales
        total_theory_groups = sum(p['grupos_teoria'] for p in projections)
        total_practice_groups = sum(p['grupos_practica'] for p in projections)
        total_lab_groups = sum(p['grupos_laboratorio'] for p in projections)
        
        # Generar profesores con disponibilidad completa
        prof_count = max(50, (total_theory_groups + total_practice_groups + total_lab_groups) // 4)
        
        for i in range(prof_count):
            # Disponibilidad completa (todos los días y franjas)
            availability = []
            for dia in range(1, 7):  # Lunes a Sábado
                for franja in range(1, 17):  # 16 franjas por día
                    availability.append([dia, franja])
            
            professor = {
                'id': f'PROF_{i+1:03d}',
                'nombre': f'Profesor {i+1}',
                'disponibilidad': availability,
                'carga_maxima': 20,
                'carga_actual': 0
            }
            professors.append(professor)
        
        logger.info(f"Generados {prof_count} profesores con disponibilidad completa")
        return professors
    
    def _generate_upao_classrooms(self) -> List[Dict]:
        """Genera aulas según la infraestructura UPAO"""
        classrooms = []
        
        # Piso F - Laboratorios pequeños (≤20 estudiantes)
        for i in range(1, 13):  # F101-F112
            classroom = {
                'id': f'F{100+i}',
                'tipo': 'laboratorio',
                'capacidad': 20,
                'edificio': 'F',
                'disponible': True
            }
            classrooms.append(classroom)
        
        # Pisos G - Aulas teóricas grandes (>20 estudiantes)
        for piso in range(1, 4):  # G101-G112, G201-G212, G301-G312
            for aula in range(1, 10):
                classroom = {
                    'id': f'G{piso}{aula:02d}',
                    'tipo': 'teorica',
                    'capacidad': 40,
                    'edificio': 'G',
                    'disponible': True
                }
                classrooms.append(classroom)
        
        # Pisos G - Algunos laboratorios grandes (>20 estudiantes)
        for i in range(1, 10):  # G401-G409
            classroom = {
                'id': f'G4{i:02d}',
                'tipo': 'laboratorio',
                'capacidad': 30,
                'edificio': 'G',
                'disponible': True
            }
            classrooms.append(classroom)
        
        logger.info(f"Generadas {len(classrooms)} aulas UPAO (F: laboratorios ≤20, G: teóricas y labs >20)")
        return classrooms
    
    def _generate_time_slots(self) -> List[Dict]:
        """Genera franjas horarias UPAO (16 franjas × 6 días)"""
        time_slots = []
        
        for dia in range(1, 7):  # Lunes a Sábado
            for franja in range(1, 17):  # 16 franjas por día
                periodo = self._get_period_for_slot(franja)
                
                slot = {
                    'dia': dia,
                    'franja': franja,
                    'periodo': periodo
                }
                time_slots.append(slot)
        
        logger.info(f"Generadas {len(time_slots)} franjas horarias (16×6 días)")
        return time_slots


def main():
    """Convierte los datos y ejecuta el algoritmo ACO optimizado"""
    
    # Convertir datos
    adapter = DataAdapter()
    converted_data = adapter.convert_projections_to_aco_format('upao_projections_processed.json')
    
    # Guardar datos convertidos
    with open('upao_data_for_aco.json', 'w', encoding='utf-8') as f:
        json.dump(converted_data, f, indent=2, ensure_ascii=False)
    
    logger.info("Datos convertidos guardados en 'upao_data_for_aco.json'")
    
    # Ahora ejecutar el ACO optimizado con datos convertidos
    from aco_optimized import OptimizedACOTimetabling, Course, Professor, Classroom, TimeSlot
    
    # Crear objetos del dominio
    courses = {}
    for course_data in converted_data['courses']:
        courses[course_data['id']] = Course(**course_data)
    
    professors = {}
    for prof_data in converted_data['professors']:
        # Convertir disponibilidad de lista a set
        availability_set = set()
        for slot in prof_data['disponibilidad']:
            availability_set.add(tuple(slot))
        prof_data['disponibilidad'] = availability_set
        professors[prof_data['id']] = Professor(**prof_data)
    
    classrooms = {}
    for classroom_data in converted_data['classrooms']:
        classrooms[classroom_data['id']] = Classroom(**classroom_data)
    
    time_slots = []
    for slot_data in converted_data['time_slots']:
        time_slots.append(TimeSlot(**slot_data))
    
    logger.info(f"Datos cargados: {len(courses)} cursos, {len(professors)} profesores, "
               f"{len(classrooms)} aulas, {len(time_slots)} franjas horarias")
    
    # Crear y ejecutar algoritmo ACO optimizado
    aco = OptimizedACOTimetabling(
        courses=courses,
        professors=professors,
        classrooms=classrooms,
        time_slots=time_slots,
        max_iterations=15,  # Aún más reducido para primera prueba
        num_ants=8,         # Reducido para velocidad
        alpha=1.0,
        beta=2.0,
        rho=0.15
    )
    
    # Ejecutar optimización
    best_solution = aco.optimize()
    
    # Guardar solución
    aco.save_solution("aco_optimized_final_solution.json")
    
    # Imprimir resumen final
    print("\n" + "="*60)
    print("RESUMEN FINAL ACO OPTIMIZADO")
    print("="*60)
    print(f"Tareas totales: {len(aco.scheduling_tasks)}")
    print(f"Asignaciones exitosas: {len(best_solution.assignments)}")
    print(f"Tasa de éxito: {len(best_solution.assignments)/len(aco.scheduling_tasks)*100:.1f}%")
    print(f"Fitness final: {best_solution.fitness:.2f}")
    print(f"\nViolaciones:")
    for violation, count in best_solution.violations.items():
        print(f"  {violation}: {count}")
    print("="*60)


if __name__ == "__main__":
    # Configurar logging
    logging.basicConfig(level=logging.INFO)
    main()