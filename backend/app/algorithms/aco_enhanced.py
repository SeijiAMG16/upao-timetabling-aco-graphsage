"""
ACO Timetabling - Enhanced Version
Versión mejorada con parámetros ajustados para máxima exploración
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Reutilizar las clases del ACO optimizado
from aco_optimized import (Course, Professor, Classroom, TimeSlot, Assignment, 
                          Solution, OptimizedACOTimetabling)

class EnhancedACOTimetabling(OptimizedACOTimetabling):
    """ACO mejorado con parámetros ajustados para máxima cobertura"""
    
    def __init__(self, 
                 courses: Dict[str, Course],
                 professors: Dict[str, Professor], 
                 classrooms: Dict[str, Classroom],
                 time_slots: List[TimeSlot],
                 alpha: float = 0.8,     # Reducido (menos peso a feromonas)
                 beta: float = 1.2,      # Reducido (menos greedy)
                 rho: float = 0.4,       # Aumentado (más evaporación)
                 q: float = 100.0,
                 max_iterations: int = 30,  # Más iteraciones
                 num_ants: int = 15):       # Más hormigas
        
        # Llamar al constructor padre con parámetros mejorados
        super().__init__(courses, professors, classrooms, time_slots,
                        alpha, beta, rho, q, max_iterations, num_ants)
        
        logger.info("ACO Mejorado inicializado con parámetros de exploración")
        logger.info(f"Parámetros: α={alpha}, β={beta}, ρ={rho}, iter={max_iterations}, hormigas={num_ants}")
    
    def _construct_solution_enhanced(self) -> Solution:
        """Versión mejorada de construcción de solución con más randomización"""
        solution = Solution()
        
        # Tracking de ocupación por franja horaria
        occupied_slots = defaultdict(set)
        professor_load = defaultdict(int)
        
        # Ordenar tareas por dificultad (las más difíciles primero)
        task_indices = list(range(len(self.scheduling_tasks)))
        
        # Calcular "dificultad" de cada tarea
        task_difficulties = []
        for task_idx in task_indices:
            task = self.scheduling_tasks[task_idx]
            options_count = len(self.valid_options[task_idx])
            # Más difícil = menos opciones
            difficulty = 1.0 / max(1, options_count)
            task_difficulties.append((difficulty, task_idx))
        
        # Ordenar por dificultad (50% determinístico, 50% aleatorio)
        task_difficulties.sort(reverse=True)
        
        # Mezcla parcial: mantener las más difíciles al inicio, randomizar el resto
        difficult_tasks = [idx for _, idx in task_difficulties[:len(task_difficulties)//2]]
        easy_tasks = [idx for _, idx in task_difficulties[len(task_difficulties)//2:]]
        random.shuffle(easy_tasks)
        
        ordered_tasks = difficult_tasks + easy_tasks
        
        assignments_count = 0
        skipped_count = 0
        
        for task_idx in ordered_tasks:
            task = self.scheduling_tasks[task_idx]
            
            # Obtener opciones válidas
            options = self.valid_options[task_idx]
            if not options:
                skipped_count += 1
                continue
            
            # Filtrar opciones disponibles
            available_options = []
            probabilities = []
            
            for prof_id, classroom_id, time_slot in options:
                slot_key = (time_slot.dia, time_slot.franja)
                
                # Verificar conflictos
                if slot_key in occupied_slots:
                    if prof_id in occupied_slots[slot_key] or classroom_id in occupied_slots[slot_key]:
                        continue
                
                # Verificar carga del profesor (más flexible)
                max_load = self.professors[prof_id].carga_maxima
                if professor_load[prof_id] >= max_load:
                    continue
                
                # Calcular probabilidad ACO con más randomización
                pheromone = self.pheromones[task['course_id']][prof_id][classroom_id][(time_slot.dia, time_slot.franja)]
                heuristic = self._calculate_heuristic(task_idx, prof_id, classroom_id, time_slot)
                
                # Añadir factor de diversificación
                diversification = 1.0 + random.uniform(-0.3, 0.3)
                
                prob = (pheromone ** self.alpha) * (heuristic ** self.beta) * diversification
                
                available_options.append((prof_id, classroom_id, time_slot))
                probabilities.append(max(0.001, prob))  # Evitar probabilidades 0
            
            if not probabilities:
                # Intentar relajar restricciones para esta tarea
                relaxed_options = self._try_relaxed_assignment(task_idx, occupied_slots, professor_load)
                if relaxed_options:
                    available_options, probabilities = relaxed_options
                else:
                    skipped_count += 1
                    continue
            
            # Selección con más randomización
            probabilities = np.array(probabilities)
            probabilities = probabilities / probabilities.sum()
            
            # Añadir ruido para evitar convergencia prematura
            if assignments_count > 0 and assignments_count % 20 == 0:
                # Cada 20 asignaciones, usar selección más aleatoria
                probabilities = probabilities * 0.7 + 0.3 * np.ones_like(probabilities) / len(probabilities)
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
        
        logger.debug(f"Solución construida: {assignments_count} asignaciones, {skipped_count} saltadas")
        return solution
    
    def _try_relaxed_assignment(self, task_idx: int, occupied_slots, professor_load) -> Optional[Tuple[List, List]]:
        """Intenta asignación con restricciones relajadas"""
        
        task = self.scheduling_tasks[task_idx]
        options = self.valid_options[task_idx]
        
        # Relajar carga de profesores (permitir +2 sobre máximo)
        relaxed_options = []
        probabilities = []
        
        for prof_id, classroom_id, time_slot in options:
            slot_key = (time_slot.dia, time_slot.franja)
            
            # Solo verificar conflictos críticos (no carga)
            if slot_key in occupied_slots:
                if prof_id in occupied_slots[slot_key] or classroom_id in occupied_slots[slot_key]:
                    continue
            
            # Permitir sobrecarga moderada
            max_load = self.professors[prof_id].carga_maxima + 2
            if professor_load[prof_id] >= max_load:
                continue
            
            # Probabilidad reducida por relajación
            pheromone = self.pheromones[task['course_id']][prof_id][classroom_id][(time_slot.dia, time_slot.franja)]
            heuristic = self._calculate_heuristic(task_idx, prof_id, classroom_id, time_slot)
            
            # Penalizar por relajación
            relaxation_penalty = 0.5 if professor_load[prof_id] >= self.professors[prof_id].carga_maxima else 1.0
            
            prob = (pheromone ** self.alpha) * (heuristic ** self.beta) * relaxation_penalty
            
            relaxed_options.append((prof_id, classroom_id, time_slot))
            probabilities.append(max(0.001, prob))
        
        return (relaxed_options, probabilities) if relaxed_options else None
    
    def optimize(self) -> Solution:
        """Ejecuta optimización con logging mejorado"""
        start_time = time.time()
        logger.info(f"Iniciando ACO Mejorado: {self.max_iterations} iteraciones, {self.num_ants} hormigas")
        logger.info(f"Objetivo: Maximizar asignaciones (esperado: 297)")
        
        iteration_fitnesses = []
        best_assignments_count = 0
        
        for iteration in range(self.max_iterations):
            iteration_start = time.time()
            solutions = []
            
            # Construir soluciones con todas las hormigas
            for ant in range(self.num_ants):
                solution = self._construct_solution_enhanced()  # Usar versión mejorada
                solution.fitness = self._calculate_fitness_fast(solution)
                solutions.append(solution)
            
            # Actualizar mejor solución
            best_in_iteration = max(solutions, key=lambda x: x.fitness)
            
            # Tracking detallado
            assignments_in_iteration = len(best_in_iteration.assignments)
            if assignments_in_iteration > best_assignments_count:
                best_assignments_count = assignments_in_iteration
                logger.info(f"🎯 Nueva mejor cobertura: {assignments_in_iteration} asignaciones!")
            
            if best_in_iteration.fitness > self.best_fitness:
                self.best_fitness = best_in_iteration.fitness
                self.best_solution = deepcopy(best_in_iteration)
                logger.info(f"🏆 Nuevo mejor fitness: {self.best_fitness:.2f}")
            
            # Actualizar feromonas
            self._update_pheromones(solutions)
            
            # Tracking detallado
            fitnesses = [s.fitness for s in solutions]
            assignments_counts = [len(s.assignments) for s in solutions]
            
            avg_fitness = np.mean(fitnesses)
            avg_assignments = np.mean(assignments_counts)
            max_assignments = max(assignments_counts)
            min_assignments = min(assignments_counts)
            
            iteration_fitnesses.append(avg_fitness)
            
            iteration_time = time.time() - iteration_start
            
            logger.info(f"Iter {iteration + 1:2d}/{self.max_iterations}: "
                       f"Fitness={self.best_fitness:.1f} "
                       f"Asign={len(self.best_solution.assignments):3d} "
                       f"Rango=[{min_assignments}-{max_assignments}] "
                       f"Prom={avg_assignments:.1f} "
                       f"Tiempo={iteration_time:.1f}s")
            
            # Mostrar violaciones cada 10 iteraciones
            if iteration % 10 == 0 and self.best_solution:
                violations = self.best_solution.violations
                total_violations = sum(violations.values())
                logger.info(f"     Violaciones totales: {total_violations} {dict(violations)}")
            
            # Detección de estancamiento y diversificación
            if iteration > 5:
                recent_variance = np.var(iteration_fitnesses[-5:])
                if recent_variance < 0.1:  # Muy poca variación
                    logger.info(f"     ⚡ Diversificación: varianza baja ({recent_variance:.3f})")
                    self._diversify_pheromones()
        
        total_time = time.time() - start_time
        
        # Resumen final detallado
        logger.info(f"\n🏁 ACO MEJORADO COMPLETADO")
        logger.info(f"⏱️ Tiempo total: {total_time:.1f}s ({total_time/60:.1f} min)")
        logger.info(f"🎯 Mejor fitness: {self.best_fitness}")
        logger.info(f"📊 Asignaciones: {len(self.best_solution.assignments)}/297 ({len(self.best_solution.assignments)/297*100:.1f}%)")
        logger.info(f"🔧 Mejora vs anterior: +{len(self.best_solution.assignments) - 191} asignaciones")
        
        return self.best_solution
    
    def _diversify_pheromones(self):
        """Diversifica feromonas para evitar estancamiento"""
        
        logger.debug("Aplicando diversificación de feromonas")
        
        # Reducir feromonas dominantes y aumentar las bajas
        for course_id in self.pheromones:
            for prof_id in self.pheromones[course_id]:
                for classroom_id in self.pheromones[course_id][prof_id]:
                    for slot_key in self.pheromones[course_id][prof_id][classroom_id]:
                        current = self.pheromones[course_id][prof_id][classroom_id][slot_key]
                        
                        # Comprimir hacia la media
                        if current > 2.0:
                            self.pheromones[course_id][prof_id][classroom_id][slot_key] = current * 0.8
                        elif current < 0.5:
                            self.pheromones[course_id][prof_id][classroom_id][slot_key] = current * 1.2


def main():
    """Función principal para ejecutar ACO mejorado"""
    
    # Cargar datos
    with open('upao_data_for_aco.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Crear objetos del dominio
    courses = {}
    for course_data in data['courses']:
        courses[course_data['id']] = Course(**course_data)
    
    professors = {}
    for prof_data in data['professors']:
        availability_set = set()
        for slot in prof_data['disponibilidad']:
            availability_set.add(tuple(slot))
        prof_data['disponibilidad'] = availability_set
        professors[prof_data['id']] = Professor(**prof_data)
    
    classrooms = {}
    for classroom_data in data['classrooms']:
        classrooms[classroom_data['id']] = Classroom(**classroom_data)
    
    time_slots = []
    for slot_data in data['time_slots']:
        time_slots.append(TimeSlot(**slot_data))
    
    logger.info(f"Datos cargados: {len(courses)} cursos, {len(professors)} profesores, "
               f"{len(classrooms)} aulas, {len(time_slots)} franjas horarias")
    
    print("\n" + "="*70)
    print("🚀 ACO MEJORADO - OBJETIVO: 297 ASIGNACIONES")
    print("="*70)
    print("🎯 Mejoras implementadas:")
    print("   • Parámetros optimizados (α=0.8, β=1.2, ρ=0.4)")
    print("   • 30 iteraciones, 15 hormigas")
    print("   • Construcción por dificultad")
    print("   • Relajación de restricciones")
    print("   • Diversificación automática")
    print("   • Objetivo: 191 → 297 asignaciones")
    print("="*70)
    
    # Crear y ejecutar ACO mejorado
    aco = EnhancedACOTimetabling(
        courses=courses,
        professors=professors,
        classrooms=classrooms,
        time_slots=time_slots,
        alpha=0.8,      # Menos peso a feromonas
        beta=1.2,       # Menos greedy
        rho=0.4,        # Más evaporación
        max_iterations=30,  # Más iteraciones
        num_ants=15     # Más hormigas
    )
    
    # Ejecutar optimización
    best_solution = aco.optimize()
    
    # Guardar solución mejorada
    aco.save_solution("aco_enhanced_solution.json")
    
    # Comparar con versión anterior
    print(f"\n" + "="*70)
    print("📊 COMPARACIÓN DE RESULTADOS")
    print("="*70)
    print(f"ACO Original:    191/297 asignaciones (64.3%)")
    print(f"ACO Mejorado:    {len(best_solution.assignments)}/297 asignaciones ({len(best_solution.assignments)/297*100:.1f}%)")
    print(f"Mejora:          +{len(best_solution.assignments) - 191} asignaciones")
    print(f"Fitness:         {best_solution.fitness:.2f}")
    print(f"Violaciones:     {sum(best_solution.violations.values())}")
    print("="*70)


if __name__ == "__main__":
    main()