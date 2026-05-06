"""
ACO (Ant Colony Optimization) Algorithm for UPAO Timetabling - OPTIMIZED VERSION
Versión optimizada para reducir tiempo de ejecución de 3 horas a minutos
"""

import numpy as np
import random
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, field
from copy import deepcopy
import json
import time
import logging
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Course:
    """Representación de un curso"""
    id: str
    nombre: str
    ciclo: int
    modalidad: str
    grupos_teoria: int
    grupos_practica: int
    grupos_laboratorio: int
    alumnos_teoria: int
    alumnos_practica: int
    alumnos_laboratorio: int
    requiere_laboratorio: bool = False
    requiere_practica: bool = False

@dataclass
class Professor:
    """Representación de un profesor"""
    id: str
    nombre: str
    disponibilidad: Set[Tuple[int, int]]  # (dia, franja) disponibles
    carga_maxima: int = 20
    carga_actual: int = 0

@dataclass
class Classroom:
    """Representación de un aula"""
    id: str
    tipo: str  # 'teorica', 'laboratorio'
    capacidad: int
    edificio: str  # 'F', 'G'
    disponible: bool = True

@dataclass
class TimeSlot:
    """Representación de una franja horaria"""
    dia: int  # 1-6 (Lunes-Sábado)
    franja: int  # 1-16
    periodo: str  # 'mañana', 'tarde', 'noche'

@dataclass
class Assignment:
    """Asignación de curso-profesor-aula-horario"""
    course_id: str
    section_type: str  # 'teoria', 'practica', 'laboratorio'
    section_number: int  # 1, 2, 3...
    professor_id: str
    classroom_id: str
    time_slot: TimeSlot
    students_count: int

@dataclass
class Solution:
    """Representación de una solución completa"""
    assignments: List[Assignment] = field(default_factory=list)
    fitness: float = 0.0
    violations: Dict[str, int] = field(default_factory=dict)
    
    def add_assignment(self, assignment: Assignment):
        self.assignments.append(assignment)

class OptimizedACOTimetabling:
    """Algoritmo ACO optimizado para generación de horarios"""
    
    def __init__(self, 
                 courses: Dict[str, Course],
                 professors: Dict[str, Professor], 
                 classrooms: Dict[str, Classroom],
                 time_slots: List[TimeSlot],
                 alpha: float = 1.0,
                 beta: float = 2.0,
                 rho: float = 0.15,
                 q: float = 100.0,
                 max_iterations: int = 4,  # Reducido de 20
                 num_ants: int = 10):       # Reducido de 20
        
        self.courses = courses
        self.professors = professors
        self.classrooms = classrooms
        self.time_slots = time_slots
        
        # Parámetros ACO optimizados
        self.alpha = alpha
        self.beta = beta
        self.rho = rho
        self.q = q
        self.max_iterations = max_iterations
        self.num_ants = num_ants
        
        # Generar tareas de programación
        self.scheduling_tasks = self._generate_scheduling_tasks()
        logger.info(f"Generadas {len(self.scheduling_tasks)} tareas de programación")
        
        # Pre-filtrar opciones válidas para cada tarea (OPTIMIZACIÓN CLAVE)
        self.valid_options = self._precompute_valid_options()
        logger.info("Pre-computadas opciones válidas para cada tarea")
        
        # Inicializar feromonas de forma más eficiente
        self.pheromones = self._initialize_pheromones()
        
        # Para tracking de mejores soluciones
        self.best_solution = None
        self.best_fitness = float('-inf')
        self.fitness_history = []
        
        logger.info("ACO Optimizado inicializado correctamente")
    
    def _generate_scheduling_tasks(self) -> List[Dict]:
        """Genera todas las tareas de programación"""
        tasks = []
        
        for course_id, course in self.courses.items():
            # Grupos de teoría
            for i in range(1, course.grupos_teoria + 1):
                tasks.append({
                    'course_id': course_id,
                    'section_type': 'teoria',
                    'section_number': i,
                    'students_count': course.alumnos_teoria
                })
            
            # Grupos de práctica
            for i in range(1, course.grupos_practica + 1):
                tasks.append({
                    'course_id': course_id,
                    'section_type': 'practica',
                    'section_number': i,
                    'students_count': course.alumnos_practica
                })
            
            # Grupos de laboratorio
            for i in range(1, course.grupos_laboratorio + 1):
                tasks.append({
                    'course_id': course_id,
                    'section_type': 'laboratorio',
                    'section_number': i,
                    'students_count': course.alumnos_laboratorio
                })
        
        return tasks
    
    def _precompute_valid_options(self) -> Dict:
        """Pre-computa opciones válidas para cada tarea - OPTIMIZACIÓN CLAVE"""
        valid_options = {}
        
        for i, task in enumerate(self.scheduling_tasks):
            options = []
            course = self.courses[task['course_id']]
            students = task['students_count']
            section_type = task['section_type']
            
            # Filtrar aulas válidas primero
            valid_classrooms = []
            for classroom_id, classroom in self.classrooms.items():
                # Verificar capacidad
                if students > classroom.capacidad:
                    continue
                
                # Verificar tipo de aula
                if section_type == 'laboratorio':
                    if classroom.tipo != 'laboratorio':
                        continue
                    # Regla F/G para laboratorios
                    if students <= 20 and classroom.edificio != 'F':
                        continue
                    if students > 20 and classroom.edificio != 'G':
                        continue
                else:
                    # Teoría y práctica pueden usar aulas teóricas o laboratorios
                    pass
                
                valid_classrooms.append(classroom_id)
            
            # Filtrar franjas horarias por preferencia de ciclo
            preferred_periods = ['mañana'] if course.ciclo % 2 == 1 else ['tarde', 'noche']
            valid_time_slots = [ts for ts in self.time_slots if ts.periodo in preferred_periods]
            
            # Si no hay franjas preferidas, usar todas
            if not valid_time_slots:
                valid_time_slots = self.time_slots
            
            # Generar combinaciones válidas
            for prof_id in self.professors:
                for classroom_id in valid_classrooms:
                    for time_slot in valid_time_slots:
                        # Verificar disponibilidad del profesor
                        if (time_slot.dia, time_slot.franja) not in self.professors[prof_id].disponibilidad:
                            continue
                        
                        options.append((prof_id, classroom_id, time_slot))
            
            valid_options[i] = options
            
        return valid_options
    
    def _initialize_pheromones(self) -> Dict:
        """Inicializa matriz de feromonas de forma más eficiente"""
        pheromones = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(float))))
        
        initial_pheromone = 1.0
        
        # Solo inicializar feromonas para combinaciones válidas
        for task_idx, options in self.valid_options.items():
            task = self.scheduling_tasks[task_idx]
            course_id = task['course_id']
            
            for prof_id, classroom_id, time_slot in options:
                key = (time_slot.dia, time_slot.franja)
                pheromones[course_id][prof_id][classroom_id][key] = initial_pheromone
        
        return pheromones
    
    def _calculate_heuristic(self, task_idx: int, prof_id: str, classroom_id: str, time_slot: TimeSlot) -> float:
        """Calcula heurística de forma optimizada"""
        task = self.scheduling_tasks[task_idx]
        course = self.courses[task['course_id']]
        classroom = self.classrooms[classroom_id]
        
        heuristic = 1.0
        
        # Penalizar sobrecarga (ya pre-filtrado pero ajustamos)
        if task['students_count'] > classroom.capacidad * 0.9:
            heuristic *= 0.8
        
        # Bonificar concordancia de periodo con ciclo (ya pre-filtrado pero ajustamos)
        if course.ciclo % 2 == 1 and time_slot.periodo == 'mañana':
            heuristic *= 1.2
        elif course.ciclo % 2 == 0 and time_slot.periodo in ['tarde', 'noche']:
            heuristic *= 1.2
        
        return heuristic
    
    def _construct_solution(self) -> Solution:
        """Construye una solución usando una hormiga - VERSIÓN OPTIMIZADA"""
        solution = Solution()
        
        # Tracking de ocupación por franja horaria
        occupied_slots = defaultdict(set)  # {(dia, franja): {prof_ids, classroom_ids}}
        professor_load = defaultdict(int)
        
        # Mezclar tareas aleatoriamente
        task_indices = list(range(len(self.scheduling_tasks)))
        random.shuffle(task_indices)
        
        assignments_count = 0
        skipped_count = 0
        
        for task_idx in task_indices:
            task = self.scheduling_tasks[task_idx]
            
            # Obtener opciones válidas pre-computadas
            options = self.valid_options[task_idx]
            if not options:
                skipped_count += 1
                continue
            
            # Filtrar opciones que no tengan conflictos
            available_options = []
            probabilities = []
            
            for prof_id, classroom_id, time_slot in options:
                slot_key = (time_slot.dia, time_slot.franja)
                
                # Verificar conflictos
                if slot_key in occupied_slots:
                    if prof_id in occupied_slots[slot_key] or classroom_id in occupied_slots[slot_key]:
                        continue
                
                # Verificar carga del profesor
                if professor_load[prof_id] >= self.professors[prof_id].carga_maxima:
                    continue
                
                # Calcular probabilidad ACO
                pheromone = self.pheromones[task['course_id']][prof_id][classroom_id][(time_slot.dia, time_slot.franja)]
                heuristic = self._calculate_heuristic(task_idx, prof_id, classroom_id, time_slot)
                
                prob = (pheromone ** self.alpha) * (heuristic ** self.beta)
                
                available_options.append((prof_id, classroom_id, time_slot))
                probabilities.append(prob)
            
            if not probabilities:
                skipped_count += 1
                continue
            
            # Selección por ruleta
            probabilities = np.array(probabilities)
            probabilities = probabilities / probabilities.sum()
            
            selected_idx = np.random.choice(len(available_options), p=probabilities)
            prof_id, classroom_id, time_slot = available_options[selected_idx]
            
            # Crear asignación
            assignment = Assignment(
                course_id=task['course_id'],
                section_type=task['section_type'],
                section_number=task['section_number'],
                professor_id=prof_id,
                classroom_id=classroom_id,
                time_slot=time_slot,
                students_count=task['students_count']
            )
            
            solution.add_assignment(assignment)
            assignments_count += 1
            
            # Actualizar ocupación
            slot_key = (time_slot.dia, time_slot.franja)
            if slot_key not in occupied_slots:
                occupied_slots[slot_key] = set()
            occupied_slots[slot_key].add(prof_id)
            occupied_slots[slot_key].add(classroom_id)
            
            # Actualizar carga del profesor
            professor_load[prof_id] += 1
        
        return solution
    
    def _calculate_fitness_fast(self, solution: Solution) -> float:
        """Calcula fitness de forma optimizada"""
        violations = {
            'professor_conflict': 0,
            'classroom_conflict': 0,
            'capacity_exceeded': 0,
            'lab_assignment_rule': 0,
            'cycle_time_preference': 0,
            'professor_overload': 0
        }
        
        # Usar defaultdict para conteo más eficiente
        slot_professors = defaultdict(set)
        slot_classrooms = defaultdict(set)
        professor_loads = defaultdict(int)
        
        for assignment in solution.assignments:
            slot_key = (assignment.time_slot.dia, assignment.time_slot.franja)
            
            # Conflictos de profesores
            if assignment.professor_id in slot_professors[slot_key]:
                violations['professor_conflict'] += 1
            slot_professors[slot_key].add(assignment.professor_id)
            
            # Conflictos de aulas
            if assignment.classroom_id in slot_classrooms[slot_key]:
                violations['classroom_conflict'] += 1
            slot_classrooms[slot_key].add(assignment.classroom_id)
            
            # Carga de profesores
            professor_loads[assignment.professor_id] += 1
            
            # Verificaciones rápidas
            classroom = self.classrooms[assignment.classroom_id]
            course = self.courses[assignment.course_id]
            
            # Capacidad excedida
            if assignment.students_count > classroom.capacidad:
                violations['capacity_exceeded'] += 1
            
            # Regla de laboratorio F/G
            if assignment.section_type == 'laboratorio':
                if assignment.students_count <= 20 and classroom.edificio != 'F':
                    violations['lab_assignment_rule'] += 1
                elif assignment.students_count > 20 and classroom.edificio != 'G':
                    violations['lab_assignment_rule'] += 1
            
            # Preferencia de horario por ciclo
            if course.ciclo % 2 == 1 and assignment.time_slot.periodo != 'mañana':
                violations['cycle_time_preference'] += 1
            elif course.ciclo % 2 == 0 and assignment.time_slot.periodo == 'mañana':
                violations['cycle_time_preference'] += 1
        
        # Sobrecarga de profesores
        for prof_id, load in professor_loads.items():
            if load > self.professors[prof_id].carga_maxima:
                violations['professor_overload'] += 1
        
        solution.violations = violations
        
        # Cálculo de fitness optimizado
        penalty = (violations['professor_conflict'] * 100 + 
                  violations['classroom_conflict'] * 100 + 
                  violations['capacity_exceeded'] * 50 + 
                  violations['lab_assignment_rule'] * 30 + 
                  violations['cycle_time_preference'] * 5 +  # Reducido peso
                  violations['professor_overload'] * 20)
        
        base_fitness = len(solution.assignments)
        fitness = base_fitness - penalty
        
        return fitness
    
    def _update_pheromones(self, solutions: List[Solution]):
        """Actualiza feromonas de forma optimizada"""
        # Evaporación global más eficiente
        for course_id in self.pheromones:
            for prof_id in self.pheromones[course_id]:
                for classroom_id in self.pheromones[course_id][prof_id]:
                    for slot_key in self.pheromones[course_id][prof_id][classroom_id]:
                        self.pheromones[course_id][prof_id][classroom_id][slot_key] *= (1 - self.rho)
        
        # Reforzar solo las mejores soluciones
        sorted_solutions = sorted(solutions, key=lambda x: x.fitness, reverse=True)
        top_solutions = sorted_solutions[:max(1, len(solutions) // 3)]  # Top 1/3
        
        for solution in top_solutions:
            delta_pheromone = self.q / (1 + abs(solution.fitness - self.best_fitness))
            
            for assignment in solution.assignments:
                slot_key = (assignment.time_slot.dia, assignment.time_slot.franja)
                self.pheromones[assignment.course_id][assignment.professor_id][assignment.classroom_id][slot_key] += delta_pheromone
    
    def optimize(self) -> Solution:
        """Ejecuta el algoritmo ACO optimizado"""
        start_time = time.time()
        logger.info(f"Iniciando ACO optimizado: {self.max_iterations} iteraciones, {self.num_ants} hormigas")
        logger.info(f"Tareas totales: {len(self.scheduling_tasks)}")
        
        for iteration in range(self.max_iterations):
            iteration_start = time.time()
            solutions = []
            
            # Construir soluciones con todas las hormigas
            for ant in range(self.num_ants):
                solution = self._construct_solution()
                solution.fitness = self._calculate_fitness_fast(solution)
                solutions.append(solution)
            
            # Actualizar mejor solución
            best_in_iteration = max(solutions, key=lambda x: x.fitness)
            if best_in_iteration.fitness > self.best_fitness:
                self.best_fitness = best_in_iteration.fitness
                self.best_solution = deepcopy(best_in_iteration)
                logger.info(f"Nueva mejor solución encontrada! Fitness: {self.best_fitness:.2f}")
            
            # Actualizar feromonas
            self._update_pheromones(solutions)
            
            # Tracking
            avg_fitness = np.mean([s.fitness for s in solutions])
            self.fitness_history.append(avg_fitness)
            
            iteration_time = time.time() - iteration_start
            
            logger.info(f"Iteración {iteration + 1}/{self.max_iterations}: "
                       f"Mejor={self.best_fitness:.2f}, "
                       f"Promedio={avg_fitness:.2f}, "
                       f"Asignaciones={len(best_in_iteration.assignments)}, "
                       f"Tiempo={iteration_time:.2f}s")
            
            # Mostrar violaciones de la mejor solución
            if iteration % 5 == 0:
                violations = self.best_solution.violations
                logger.info(f"Violaciones actuales: {violations}")
        
        total_time = time.time() - start_time
        logger.info(f"ACO completado en {total_time:.2f} segundos")
        logger.info(f"Mejor fitness final: {self.best_fitness}")
        logger.info(f"Asignaciones exitosas: {len(self.best_solution.assignments)}/{len(self.scheduling_tasks)}")
        
        return self.best_solution
    
    def save_solution(self, filename: str = "aco_optimized_solution.json"):
        """Guarda la mejor solución encontrada"""
        if not self.best_solution:
            logger.warning("No hay solución para guardar")
            return
        
        solution_data = {
            'metadata': {
                'total_tasks': len(self.scheduling_tasks),
                'successful_assignments': len(self.best_solution.assignments),
                'success_rate': len(self.best_solution.assignments) / len(self.scheduling_tasks) * 100,
                'final_fitness': self.best_solution.fitness,
                'violations': self.best_solution.violations,
                'parameters': {
                    'max_iterations': self.max_iterations,
                    'num_ants': self.num_ants,
                    'alpha': self.alpha,
                    'beta': self.beta,
                    'rho': self.rho
                }
            },
            'assignments': []
        }
        
        for assignment in self.best_solution.assignments:
            course_name = self.courses[assignment.course_id].nombre
            prof_name = self.professors[assignment.professor_id].nombre
            classroom_name = assignment.classroom_id
            
            solution_data['assignments'].append({
                'course_id': assignment.course_id,
                'course_name': course_name,
                'section_type': assignment.section_type,
                'section_number': assignment.section_number,
                'professor_id': assignment.professor_id,
                'professor_name': prof_name,
                'classroom_id': assignment.classroom_id,
                'classroom_name': classroom_name,
                'day': assignment.time_slot.dia,
                'time_slot': assignment.time_slot.franja,
                'period': assignment.time_slot.periodo,
                'students_count': assignment.students_count
            })
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(solution_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Solución guardada en {filename}")


def main():
    """Función principal para ejecutar el ACO optimizado"""
    
    # Cargar datos procesados
    try:
        with open('upao_projections_processed.json', 'r', encoding='utf-8') as f:
            processed_data = json.load(f)
        logger.info("Datos procesados cargados exitosamente")
    except FileNotFoundError:
        logger.error("Archivo de datos procesados no encontrado")
        return
    
    # Crear objetos del dominio
    courses = {}
    for course_data in processed_data['courses']:
        courses[course_data['id']] = Course(**course_data)
    
    professors = {}
    for prof_data in processed_data['professors']:
        # Convertir disponibilidad de lista a set
        availability_set = set()
        for slot in prof_data['disponibilidad']:
            availability_set.add(tuple(slot))
        prof_data['disponibilidad'] = availability_set
        professors[prof_data['id']] = Professor(**prof_data)
    
    classrooms = {}
    for classroom_data in processed_data['classrooms']:
        classrooms[classroom_data['id']] = Classroom(**classroom_data)
    
    time_slots = []
    for slot_data in processed_data['time_slots']:
        time_slots.append(TimeSlot(**slot_data))
    
    logger.info(f"Datos cargados: {len(courses)} cursos, {len(professors)} profesores, "
               f"{len(classrooms)} aulas, {len(time_slots)} franjas horarias")
    
    # Crear y ejecutar algoritmo ACO optimizado
    aco = OptimizedACOTimetabling(
        courses=courses,
        professors=professors,
        classrooms=classrooms,
        time_slots=time_slots,
        max_iterations=4,  # Reducido significativamente
        num_ants=10,        # Reducido significativamente
        alpha=1.0,
        beta=2.0,
        rho=0.15
    )
    
    # Ejecutar optimización
    best_solution = aco.optimize()
    
    # Guardar solución
    aco.save_solution("aco_optimized_best_solution.json")
    
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
    main()