"""
ACO (Ant Colony Optimization) Algorithm for UPAO Timetabling
Implementación del algoritmo de colonias de hormigas para generación de horarios
"""

import numpy as np
import random
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, field
from copy import deepcopy
import json
import time
import logging

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
    
    def get_assignments_by_timeslot(self, dia: int, franja: int) -> List[Assignment]:
        return [a for a in self.assignments if a.time_slot.dia == dia and a.time_slot.franja == franja]

class ConstraintValidator:
    """Validador de restricciones para horarios"""
    
    def __init__(self):
        self.violations = {
            'professor_conflict': 0,
            'classroom_conflict': 0,
            'capacity_exceeded': 0,
            'lab_assignment_rule': 0,
            'cycle_time_preference': 0,
            'professor_overload': 0
        }
    
    def validate_solution(self, solution: Solution, courses: Dict[str, Course], 
                         professors: Dict[str, Professor], classrooms: Dict[str, Classroom]) -> Dict[str, int]:
        """Valida una solución completa y cuenta violaciones"""
        violations = {
            'professor_conflict': 0,
            'classroom_conflict': 0,
            'capacity_exceeded': 0,
            'lab_assignment_rule': 0,
            'cycle_time_preference': 0,
            'professor_overload': 0
        }
        
        # Agrupar asignaciones por franja horaria
        time_slots_assignments = {}
        for assignment in solution.assignments:
            key = (assignment.time_slot.dia, assignment.time_slot.franja)
            if key not in time_slots_assignments:
                time_slots_assignments[key] = []
            time_slots_assignments[key].append(assignment)
        
        # Validar conflictos por franja horaria
        for (dia, franja), assignments in time_slots_assignments.items():
            # Conflictos de profesores
            professors_in_slot = set()
            for assignment in assignments:
                if assignment.professor_id in professors_in_slot:
                    violations['professor_conflict'] += 1
                professors_in_slot.add(assignment.professor_id)
            
            # Conflictos de aulas
            classrooms_in_slot = set()
            for assignment in assignments:
                if assignment.classroom_id in classrooms_in_slot:
                    violations['classroom_conflict'] += 1
                classrooms_in_slot.add(assignment.classroom_id)
        
        # Validar capacidad de aulas
        for assignment in solution.assignments:
            classroom = classrooms[assignment.classroom_id]
            if assignment.students_count > classroom.capacidad:
                violations['capacity_exceeded'] += 1
        
        # Validar reglas de laboratorio
        for assignment in solution.assignments:
            if assignment.section_type == 'laboratorio':
                classroom = classrooms[assignment.classroom_id]
                if assignment.students_count <= 20 and classroom.edificio != 'F':
                    violations['lab_assignment_rule'] += 1
                elif assignment.students_count > 20 and classroom.edificio != 'G':
                    violations['lab_assignment_rule'] += 1
        
        # Validar preferencias de horario por ciclo
        for assignment in solution.assignments:
            course = courses[assignment.course_id]
            periodo = assignment.time_slot.periodo
            
            # Ciclos impares prefieren mañana, pares prefieren tarde/noche
            if course.ciclo % 2 == 1 and periodo != 'mañana':
                violations['cycle_time_preference'] += 1
            elif course.ciclo % 2 == 0 and periodo == 'mañana':
                violations['cycle_time_preference'] += 1
        
        # Validar carga de profesores
        professor_loads = {}
        for assignment in solution.assignments:
            prof_id = assignment.professor_id
            if prof_id not in professor_loads:
                professor_loads[prof_id] = 0
            professor_loads[prof_id] += 1
        
        for prof_id, load in professor_loads.items():
            professor = professors[prof_id]
            if load > professor.carga_maxima:
                violations['professor_overload'] += 1
        
        return violations

class ACOTimetabling:
    """Algoritmo ACO para generación de horarios"""
    
    def __init__(self, 
                 courses: Dict[str, Course],
                 professors: Dict[str, Professor], 
                 classrooms: Dict[str, Classroom],
                 time_slots: List[TimeSlot],
                 alpha: float = 1.0,    # Importancia de feromonas
                 beta: float = 2.0,     # Importancia de heurística
                 rho: float = 0.1,      # Tasa de evaporación
                 q: float = 100.0,      # Constante de actualización
                 max_iterations: int = 100,
                 num_ants: int = 20):
        
        self.courses = courses
        self.professors = professors
        self.classrooms = classrooms
        self.time_slots = time_slots
        
        # Parámetros ACO
        self.alpha = alpha
        self.beta = beta
        self.rho = rho
        self.q = q
        self.max_iterations = max_iterations
        self.num_ants = num_ants
        
        # Inicializar feromonas
        self.pheromones = {}
        self.init_pheromones()
        
        # Validador de restricciones
        self.validator = ConstraintValidator()
        
        # Mejores soluciones
        self.best_solution = None
        self.best_fitness = float('-inf')
        
        # Generar tareas de programación
        self.scheduling_tasks = self._generate_scheduling_tasks()
        
    def init_pheromones(self):
        """Inicializar matriz de feromonas"""
        initial_pheromone = 1.0
        
        for course_id in self.courses:
            self.pheromones[course_id] = {}
            for prof_id in self.professors:
                self.pheromones[course_id][prof_id] = {}
                for classroom_id in self.classrooms:
                    self.pheromones[course_id][prof_id][classroom_id] = {}
                    for time_slot in self.time_slots:
                        key = (time_slot.dia, time_slot.franja)
                        self.pheromones[course_id][prof_id][classroom_id][key] = initial_pheromone
    
    def _generate_scheduling_tasks(self) -> List[Dict]:
        """Genera lista de tareas de programación a partir de los cursos"""
        tasks = []
        
        for course_id, course in self.courses.items():
            # Tareas de teoría
            for i in range(course.grupos_teoria):
                tasks.append({
                    'course_id': course_id,
                    'section_type': 'teoria',
                    'section_number': i + 1,
                    'students_count': course.alumnos_teoria // course.grupos_teoria if course.grupos_teoria > 0 else 0
                })
            
            # Tareas de práctica
            for i in range(course.grupos_practica):
                tasks.append({
                    'course_id': course_id,
                    'section_type': 'practica',
                    'section_number': i + 1,
                    'students_count': course.alumnos_practica // course.grupos_practica if course.grupos_practica > 0 else 0
                })
            
            # Tareas de laboratorio
            for i in range(course.grupos_laboratorio):
                tasks.append({
                    'course_id': course_id,
                    'section_type': 'laboratorio',
                    'section_number': i + 1,
                    'students_count': course.alumnos_laboratorio // course.grupos_laboratorio if course.grupos_laboratorio > 0 else 0
                })
        
        return tasks
    
    def calculate_heuristic(self, task: Dict, prof_id: str, classroom_id: str, time_slot: TimeSlot) -> float:
        """Calcula valor heurístico para una asignación"""
        heuristic = 1.0
        
        course = self.courses[task['course_id']]
        professor = self.professors[prof_id]
        classroom = self.classrooms[classroom_id]
        
        # Verificar disponibilidad del profesor
        if (time_slot.dia, time_slot.franja) not in professor.disponibilidad:
            return 0.0
        
        # Verificar tipo de aula compatible
        if task['section_type'] == 'laboratorio' and classroom.tipo != 'laboratorio':
            return 0.0
        
        if task['section_type'] in ['teoria', 'practica'] and classroom.tipo == 'laboratorio':
            heuristic *= 0.5  # Penalizar usar lab para teoría/práctica
        
        # Verificar capacidad
        if task['students_count'] > classroom.capacidad:
            return 0.0
        
        # Preferencia de horario por ciclo
        if course.ciclo % 2 == 1 and time_slot.periodo == 'mañana':
            heuristic *= 1.5  # Bonus para ciclos impares en mañana
        elif course.ciclo % 2 == 0 and time_slot.periodo in ['tarde', 'noche']:
            heuristic *= 1.5  # Bonus para ciclos pares en tarde/noche
        
        # Regla de laboratorios F/G
        if task['section_type'] == 'laboratorio':
            if task['students_count'] <= 20 and classroom.edificio == 'F':
                heuristic *= 2.0
            elif task['students_count'] > 20 and classroom.edificio == 'G':
                heuristic *= 2.0
            else:
                heuristic *= 0.1  # Penalizar violaciones de regla F/G
        
        return heuristic
    
    def select_assignment(self, task: Dict, forbidden_assignments: Set) -> Optional[Assignment]:
        """Selecciona una asignación usando probabilidades ACO"""
        probabilities = []
        valid_options = []
        
        for prof_id in self.professors:
            for classroom_id in self.classrooms:
                for time_slot in self.time_slots:
                    # Verificar si la asignación está prohibida (por conflictos)
                    assignment_key = (prof_id, classroom_id, time_slot.dia, time_slot.franja)
                    if assignment_key in forbidden_assignments:
                        continue
                    
                    # Calcular heurística
                    heuristic = self.calculate_heuristic(task, prof_id, classroom_id, time_slot)
                    if heuristic == 0.0:
                        continue
                    
                    # Obtener feromona
                    pheromone = self.pheromones[task['course_id']][prof_id][classroom_id][(time_slot.dia, time_slot.franja)]
                    
                    # Calcular probabilidad
                    prob = (pheromone ** self.alpha) * (heuristic ** self.beta)
                    
                    probabilities.append(prob)
                    valid_options.append((prof_id, classroom_id, time_slot))
        
        if not probabilities:
            return None
        
        # Selección por ruleta
        probabilities = np.array(probabilities)
        probabilities = probabilities / probabilities.sum()
        
        selected_idx = np.random.choice(len(valid_options), p=probabilities)
        prof_id, classroom_id, time_slot = valid_options[selected_idx]
        
        return Assignment(
            course_id=task['course_id'],
            section_type=task['section_type'],
            section_number=task['section_number'],
            professor_id=prof_id,
            classroom_id=classroom_id,
            time_slot=time_slot,
            students_count=task['students_count']
        )
    
    def construct_solution(self) -> Solution:
        """Construye una solución usando una hormiga"""
        solution = Solution()
        forbidden_assignments = set()
        
        # Mezclar tareas aleatoriamente
        tasks = self.scheduling_tasks.copy()
        random.shuffle(tasks)
        
        for task in tasks:
            assignment = self.select_assignment(task, forbidden_assignments)
            
            if assignment:
                solution.add_assignment(assignment)
                
                # Agregar a asignaciones prohibidas para evitar conflictos
                forbidden_key = (assignment.professor_id, assignment.classroom_id, 
                               assignment.time_slot.dia, assignment.time_slot.franja)
                forbidden_assignments.add(forbidden_key)
        
        return solution
    
    def calculate_fitness(self, solution: Solution) -> float:
        """Calcula fitness de una solución"""
        violations = self.validator.validate_solution(solution, self.courses, self.professors, self.classrooms)
        solution.violations = violations
        
        # Penalizar violaciones
        penalty = 0
        penalty += violations['professor_conflict'] * 100
        penalty += violations['classroom_conflict'] * 100  
        penalty += violations['capacity_exceeded'] * 50
        penalty += violations['lab_assignment_rule'] * 30
        penalty += violations['cycle_time_preference'] * 10
        penalty += violations['professor_overload'] * 20
        
        # Fitness base (número de asignaciones exitosas)
        base_fitness = len(solution.assignments)
        
        # Fitness final
        fitness = base_fitness - penalty
        
        return fitness
    
    def update_pheromones(self, solutions: List[Solution]):
        """Actualiza feromonas basado en las soluciones"""
        # Evaporación
        for course_id in self.pheromones:
            for prof_id in self.pheromones[course_id]:
                for classroom_id in self.pheromones[course_id][prof_id]:
                    for time_key in self.pheromones[course_id][prof_id][classroom_id]:
                        self.pheromones[course_id][prof_id][classroom_id][time_key] *= (1 - self.rho)
        
        # Depósito de feromonas
        for solution in solutions:
            if solution.fitness > 0:  # Solo depositar en soluciones válidas
                for assignment in solution.assignments:
                    time_key = (assignment.time_slot.dia, assignment.time_slot.franja)
                    delta_pheromone = self.q / (1 + abs(solution.fitness))
                    
                    self.pheromones[assignment.course_id][assignment.professor_id][assignment.classroom_id][time_key] += delta_pheromone
    
    def optimize(self) -> Solution:
        """Ejecuta el algoritmo ACO"""
        logger.info(f"Starting ACO optimization with {self.num_ants} ants for {self.max_iterations} iterations")
        logger.info(f"Total scheduling tasks: {len(self.scheduling_tasks)}")
        
        start_time = time.time()
        
        for iteration in range(self.max_iterations):
            # Generar soluciones con hormigas
            solutions = []
            for ant in range(self.num_ants):
                solution = self.construct_solution()
                solution.fitness = self.calculate_fitness(solution)
                solutions.append(solution)
            
            # Encontrar mejor solución de esta iteración
            best_iteration_solution = max(solutions, key=lambda s: s.fitness)
            
            # Actualizar mejor solución global
            if best_iteration_solution.fitness > self.best_fitness:
                self.best_fitness = best_iteration_solution.fitness
                self.best_solution = deepcopy(best_iteration_solution)
                logger.info(f"Iteration {iteration + 1}: New best fitness = {self.best_fitness}")
                logger.info(f"  Assignments: {len(self.best_solution.assignments)}")
                logger.info(f"  Violations: {self.best_solution.violations}")
            
            # Actualizar feromonas
            self.update_pheromones(solutions)
            
            if (iteration + 1) % 10 == 0:
                logger.info(f"Iteration {iteration + 1}/{self.max_iterations}, Best fitness: {self.best_fitness}")
        
        execution_time = time.time() - start_time
        logger.info(f"ACO optimization completed in {execution_time:.2f} seconds")
        logger.info(f"Final best fitness: {self.best_fitness}")
        
        return self.best_solution

def load_data_from_json(json_path: str) -> Tuple[Dict[str, Course], Dict[str, Professor], Dict[str, Classroom], List[TimeSlot]]:
    """Carga datos desde JSON procesado"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Cargar cursos
    courses = {}
    for proj in data['projections']:
        course = Course(
            id=proj['codigo_completo'],
            nombre=proj['nombre_asignatura'],
            ciclo=proj['ciclo_numerico'],
            modalidad=proj['modalidad'],
            grupos_teoria=proj['grupos_teoria'],
            grupos_practica=proj['grupos_practica'],
            grupos_laboratorio=proj['grupos_laboratorio'],
            alumnos_teoria=proj['alumnos_teoria'],
            alumnos_practica=proj['alumnos_practica'],
            alumnos_laboratorio=proj['alumnos_laboratorio'],
            requiere_laboratorio=proj['requiere_laboratorio'],
            requiere_practica=proj['requiere_practica']
        )
        courses[course.id] = course
    
    # Generar profesores de ejemplo (en producción vendrían de BD)
    professors = {}
    for i in range(50):  # 50 profesores de ejemplo
        prof_id = f"PROF_{i+1:03d}"
        
        # Generar disponibilidad aleatoria
        disponibilidad = set()
        for dia in range(1, 7):  # Lunes a Sábado
            for franja in range(1, 17):  # 16 franjas
                if random.random() > 0.3:  # 70% probabilidad de estar disponible
                    disponibilidad.add((dia, franja))
        
        professor = Professor(
            id=prof_id,
            nombre=f"Profesor {i+1}",
            disponibilidad=disponibilidad,
            carga_maxima=random.randint(15, 25)
        )
        professors[prof_id] = professor
    
    # Cargar aulas
    classrooms = {}
    for aula_data in data['classrooms']:
        classroom = Classroom(
            id=aula_data['codigo'],
            tipo=aula_data['tipo'],
            capacidad=aula_data['capacidad'],
            edificio=aula_data['edificio']
        )
        classrooms[classroom.id] = classroom
    
    # Cargar franjas horarias
    time_slots = []
    for slot_data in data['time_slots']:
        time_slot = TimeSlot(
            dia=slot_data['dia_semana'],
            franja=slot_data['orden'],
            periodo=slot_data['periodo']
        )
        time_slots.append(time_slot)
    
    return courses, professors, classrooms, time_slots

def main():
    """Función principal para probar ACO"""
    # Cargar datos
    json_path = "upao_projections_processed.json"
    courses, professors, classrooms, time_slots = load_data_from_json(json_path)
    
    logger.info(f"Loaded {len(courses)} courses, {len(professors)} professors, {len(classrooms)} classrooms")
    
    # Crear y ejecutar algoritmo ACO
    aco = ACOTimetabling(
        courses=courses,
        professors=professors,
        classrooms=classrooms,
        time_slots=time_slots,
        alpha=1.0,
        beta=2.0,
        rho=0.1,
        max_iterations=50,
        num_ants=15
    )
    
    # Optimizar
    best_solution = aco.optimize()
    
    if best_solution:
        logger.info("=== BEST SOLUTION FOUND ===")
        logger.info(f"Fitness: {best_solution.fitness}")
        logger.info(f"Total assignments: {len(best_solution.assignments)}")
        logger.info(f"Violations: {best_solution.violations}")
        
        # Guardar solución
        solution_data = {
            'fitness': best_solution.fitness,
            'violations': best_solution.violations,
            'assignments': [
                {
                    'course_id': a.course_id,
                    'section_type': a.section_type,
                    'section_number': a.section_number,
                    'professor_id': a.professor_id,
                    'classroom_id': a.classroom_id,
                    'day': a.time_slot.dia,
                    'time_slot': a.time_slot.franja,
                    'period': a.time_slot.periodo,
                    'students_count': a.students_count
                }
                for a in best_solution.assignments
            ]
        }
        
        with open('aco_best_solution.json', 'w', encoding='utf-8') as f:
            json.dump(solution_data, f, indent=2, ensure_ascii=False)
        
        logger.info("Solution saved to aco_best_solution.json")
    else:
        logger.error("No solution found!")

if __name__ == "__main__":
    main()