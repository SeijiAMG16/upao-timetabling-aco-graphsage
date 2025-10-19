"""
Búsqueda Local para Refinamiento de Soluciones

Implementa algoritmos de búsqueda local para mejorar soluciones
generadas por ACO:
- Simulated Annealing (SA)
- Hill Climbing

Operadores de vecindario:
- Swap de aulas entre secciones
- Swap de franjas horarias
- Reubicación de secciones
"""

import random
import math
import copy
from typing import List, Tuple, Optional
import numpy as np

from .config import LOCAL_SEARCH_PARAMS
from .constraints import (
    Assignment,
    HardConstraintValidator,
    SoftConstraintEvaluator,
)
from .aco_engine import Solution


# ============================================================================
# OPERADORES DE VECINDARIO
# ============================================================================

class NeighborhoodOperators:
    """Operadores para generar soluciones vecinas"""
    
    def __init__(
        self,
        hard_validator: HardConstraintValidator,
        soft_evaluator: SoftConstraintEvaluator,
    ):
        self.hard_validator = hard_validator
        self.soft_evaluator = soft_evaluator
    
    def swap_classrooms(
        self,
        solution: Solution,
        idx1: int,
        idx2: int,
    ) -> Optional[Solution]:
        """
        Intercambia las aulas de dos asignaciones.
        
        Returns:
            Nueva solución si es válida, None si viola restricciones duras
        """
        new_assignments = copy.deepcopy(solution.assignments)
        
        # Intercambiar aulas
        temp = new_assignments[idx1].classroom_id
        new_assignments[idx1].classroom_id = new_assignments[idx2].classroom_id
        new_assignments[idx2].classroom_id = temp
        
        # Validar restricciones duras
        for idx in [idx1, idx2]:
            # Crear schedule sin la asignación actual
            other_assignments = [a for i, a in enumerate(new_assignments) if i != idx]
            is_valid, _ = self.hard_validator.validate_all(
                new_assignments[idx],
                other_assignments,
            )
            if not is_valid:
                return None
        
        # Calcular nuevo costo
        total_cost, penalties = self.soft_evaluator.calculate_total_penalty(new_assignments)
        
        return Solution(
            assignments=new_assignments,
            total_cost=total_cost,
            soft_penalties=penalties,
            is_valid=True,
            construction_log=[],
        )
    
    def swap_timeslots(
        self,
        solution: Solution,
        idx1: int,
        idx2: int,
    ) -> Optional[Solution]:
        """Intercambia las franjas horarias de dos asignaciones"""
        new_assignments = copy.deepcopy(solution.assignments)
        
        # Verificar que ambas asignaciones tengan la misma duración
        if len(new_assignments[idx1].timeslot_ids) != len(new_assignments[idx2].timeslot_ids):
            return None
        
        # Intercambiar franjas
        temp = new_assignments[idx1].timeslot_ids
        new_assignments[idx1].timeslot_ids = new_assignments[idx2].timeslot_ids
        new_assignments[idx2].timeslot_ids = temp
        
        # Validar
        for idx in [idx1, idx2]:
            other_assignments = [a for i, a in enumerate(new_assignments) if i != idx]
            is_valid, _ = self.hard_validator.validate_all(
                new_assignments[idx],
                other_assignments,
            )
            if not is_valid:
                return None
        
        total_cost, penalties = self.soft_evaluator.calculate_total_penalty(new_assignments)
        
        return Solution(
            assignments=new_assignments,
            total_cost=total_cost,
            soft_penalties=penalties,
            is_valid=True,
            construction_log=[],
        )
    
    def relocate_assignment(
        self,
        solution: Solution,
        idx: int,
        new_classroom_id: int,
        new_timeslot_ids: List[int],
    ) -> Optional[Solution]:
        """Reubica una asignación a un nuevo aula y/o franja"""
        new_assignments = copy.deepcopy(solution.assignments)
        
        new_assignments[idx].classroom_id = new_classroom_id
        new_assignments[idx].timeslot_ids = new_timeslot_ids
        
        # Validar
        other_assignments = [a for i, a in enumerate(new_assignments) if i != idx]
        is_valid, _ = self.hard_validator.validate_all(
            new_assignments[idx],
            other_assignments,
        )
        if not is_valid:
            return None
        
        total_cost, penalties = self.soft_evaluator.calculate_total_penalty(new_assignments)
        
        return Solution(
            assignments=new_assignments,
            total_cost=total_cost,
            soft_penalties=penalties,
            is_valid=True,
            construction_log=[],
        )


# ============================================================================
# SIMULATED ANNEALING
# ============================================================================

class SimulatedAnnealing:
    """Algoritmo de Simulated Annealing para refinamiento"""
    
    def __init__(
        self,
        hard_validator: HardConstraintValidator,
        soft_evaluator: SoftConstraintEvaluator,
        params: dict = None,
    ):
        self.operators = NeighborhoodOperators(hard_validator, soft_evaluator)
        
        # Parámetros
        params = params or LOCAL_SEARCH_PARAMS
        self.max_iterations = params["max_iterations"]
        self.initial_temperature = params["initial_temperature"]
        self.cooling_rate = params["cooling_rate"]
        self.min_temperature = params["min_temperature"]
        self.n_neighbors = params["n_neighbors"]
    
    def optimize(self, initial_solution: Solution) -> Solution:
        """
        Ejecuta Simulated Annealing desde una solución inicial.
        
        Args:
            initial_solution: Solución inicial (de ACO)
        
        Returns:
            Solución mejorada
        """
        current_solution = initial_solution
        best_solution = initial_solution
        
        temperature = self.initial_temperature
        iteration = 0
        
        print(f"\n{'='*80}")
        print(f"Iniciando Simulated Annealing")
        print(f"T_inicial={self.initial_temperature}, cooling={self.cooling_rate}")
        print(f"Costo inicial: {current_solution.total_cost:.2f}")
        print(f"{'='*80}\n")
        
        improvements = 0
        
        while temperature > self.min_temperature and iteration < self.max_iterations:
            # Generar vecinos
            neighbor = self._generate_neighbor(current_solution)
            
            if neighbor is None:
                iteration += 1
                continue
            
            # Calcular diferencia de costo
            delta = neighbor.total_cost - current_solution.total_cost
            
            # Decidir si aceptar
            if delta < 0:
                # Mejor solución: aceptar siempre
                current_solution = neighbor
                improvements += 1
                
                if neighbor.total_cost < best_solution.total_cost:
                    best_solution = neighbor
                    print(f"Iter {iteration}: ✅ Nueva mejor: {best_solution.total_cost:.2f} (T={temperature:.2f})")
            
            else:
                # Peor solución: aceptar con probabilidad e^(-delta/T)
                acceptance_prob = math.exp(-delta / temperature)
                if random.random() < acceptance_prob:
                    current_solution = neighbor
            
            # Enfriar
            temperature *= self.cooling_rate
            iteration += 1
            
            # Log periódico
            if iteration % 100 == 0:
                print(f"Iter {iteration}: Current={current_solution.total_cost:.2f}, "
                      f"Best={best_solution.total_cost:.2f}, T={temperature:.2f}")
        
        print(f"\n{'='*80}")
        print(f"✅ SA completado: {iteration} iteraciones, {improvements} mejoras")
        print(f"Costo inicial: {initial_solution.total_cost:.2f}")
        print(f"Costo final: {best_solution.total_cost:.2f}")
        print(f"Mejora: {initial_solution.total_cost - best_solution.total_cost:.2f} "
              f"({(1 - best_solution.total_cost/initial_solution.total_cost)*100:.1f}%)")
        print(f"{'='*80}\n")
        
        return best_solution
    
    def _generate_neighbor(self, solution: Solution) -> Optional[Solution]:
        """Genera una solución vecina usando operadores aleatorios"""
        n_assignments = len(solution.assignments)
        if n_assignments < 2:
            return None
        
        # Elegir operador aleatorio
        operator = random.choice(['swap_classrooms', 'swap_timeslots'])
        
        # Intentar varias veces
        for _ in range(self.n_neighbors):
            idx1 = random.randint(0, n_assignments - 1)
            idx2 = random.randint(0, n_assignments - 1)
            
            if idx1 == idx2:
                continue
            
            if operator == 'swap_classrooms':
                neighbor = self.operators.swap_classrooms(solution, idx1, idx2)
            elif operator == 'swap_timeslots':
                neighbor = self.operators.swap_timeslots(solution, idx1, idx2)
            else:
                neighbor = None
            
            if neighbor is not None:
                return neighbor
        
        return None


# ============================================================================
# HILL CLIMBING
# ============================================================================

class HillClimbing:
    """Algoritmo de Hill Climbing simple"""
    
    def __init__(
        self,
        hard_validator: HardConstraintValidator,
        soft_evaluator: SoftConstraintEvaluator,
        params: dict = None,
    ):
        self.operators = NeighborhoodOperators(hard_validator, soft_evaluator)
        
        params = params or LOCAL_SEARCH_PARAMS
        self.max_iterations = params["max_iterations"]
        self.n_neighbors = params["n_neighbors"]
    
    def optimize(self, initial_solution: Solution) -> Solution:
        """Ejecuta Hill Climbing"""
        current_solution = initial_solution
        iteration = 0
        improvements = 0
        
        print(f"\n{'='*80}")
        print(f"Iniciando Hill Climbing")
        print(f"Costo inicial: {current_solution.total_cost:.2f}")
        print(f"{'='*80}\n")
        
        no_improvement_count = 0
        max_no_improvement = 50
        
        while iteration < self.max_iterations and no_improvement_count < max_no_improvement:
            # Generar vecinos
            neighbors = self._generate_neighbors(current_solution)
            
            if not neighbors:
                break
            
            # Encontrar mejor vecino
            best_neighbor = min(neighbors, key=lambda s: s.total_cost)
            
            # Si es mejor, moverse
            if best_neighbor.total_cost < current_solution.total_cost:
                current_solution = best_neighbor
                improvements += 1
                no_improvement_count = 0
                print(f"Iter {iteration}: ✅ Mejora: {current_solution.total_cost:.2f}")
            else:
                no_improvement_count += 1
            
            iteration += 1
        
        print(f"\n{'='*80}")
        print(f"✅ Hill Climbing completado: {iteration} iteraciones, {improvements} mejoras")
        print(f"Costo inicial: {initial_solution.total_cost:.2f}")
        print(f"Costo final: {current_solution.total_cost:.2f}")
        print(f"{'='*80}\n")
        
        return current_solution
    
    def _generate_neighbors(self, solution: Solution) -> List[Solution]:
        """Genera todos los vecinos posibles (limitado)"""
        neighbors = []
        n_assignments = len(solution.assignments)
        
        # Limitar número de vecinos a explorar
        max_pairs = min(self.n_neighbors, n_assignments * (n_assignments - 1) // 2)
        
        pairs = []
        for i in range(n_assignments):
            for j in range(i + 1, n_assignments):
                pairs.append((i, j))
        
        random.shuffle(pairs)
        pairs = pairs[:max_pairs]
        
        for idx1, idx2 in pairs:
            # Probar swap de aulas
            neighbor = self.operators.swap_classrooms(solution, idx1, idx2)
            if neighbor:
                neighbors.append(neighbor)
            
            # Probar swap de franjas
            neighbor = self.operators.swap_timeslots(solution, idx1, idx2)
            if neighbor:
                neighbors.append(neighbor)
        
        return neighbors


# ============================================================================
# FACTORY
# ============================================================================

def create_local_search(
    algorithm: str,
    hard_validator: HardConstraintValidator,
    soft_evaluator: SoftConstraintEvaluator,
    params: dict = None,
):
    """
    Crea un algoritmo de búsqueda local.
    
    Args:
        algorithm: 'simulated_annealing' o 'hill_climbing'
        hard_validator: Validador de restricciones duras
        soft_evaluator: Evaluador de restricciones blandas
        params: Parámetros del algoritmo
    
    Returns:
        Instancia del algoritmo seleccionado
    """
    if algorithm == 'simulated_annealing':
        return SimulatedAnnealing(hard_validator, soft_evaluator, params)
    elif algorithm == 'hill_climbing':
        return HillClimbing(hard_validator, soft_evaluator, params)
    else:
        raise ValueError(f"Algoritmo desconocido: {algorithm}")
