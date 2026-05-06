"""
Motor ACO (Ant Colony Optimization) con Heurística Neural

Implementa el algoritmo de Colonia de Hormigas con integración de GraphSAGE.
Usa Max-Min Ant System (MMAS) para estabilidad.

Probabilidad de selección: P(i,j) ∝ [τ(i,j)]^α · [Φ(G,i,j)]^β

donde:
- τ(i,j): feromona de la arista
- Φ(G,i,j): heurística neural (GraphSAGE)
- α, β: pesos de importancia
"""

import numpy as np
import random
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
from collections import defaultdict
import torch
from torch_geometric.data import HeteroData
from datetime import datetime, time as time_cls

from .config import ACO_PARAMS
from .constraints import (
    Assignment,
    TimeSlotInfo,
    ClassroomInfo,
    ProfessorRestrictionInfo,
    HardConstraintValidator,
    SoftConstraintEvaluator,
)
from .graphsage_model import ACOGraphSAGEModel


# ============================================================================
# ESTRUCTURAS DE DATOS
# ============================================================================

@dataclass
class Solution:
    """Representa una solución completa (horario)"""
    assignments: List[Assignment]
    total_cost: float
    soft_penalties: Dict[str, float]
    is_valid: bool
    construction_log: List[str]


@dataclass
class PheromoneMatrix:
    """Matriz de feromonas para asignaciones"""
    # Estructura: {section_id: {(prof, classroom, timeslot): pheromone}}
    matrix: Dict[int, Dict[Tuple[int, int, int], float]]
    tau_min: float
    tau_max: float
    
    def __init__(self, tau_min: float, tau_max: float, tau_init: float):
        self.matrix = defaultdict(dict)
        self.tau_min = tau_min
        self.tau_max = tau_max
        self.tau_init = tau_init
    
    def get(self, section_id: int, assignment_key: Tuple[int, int, int]) -> float:
        """Obtiene el valor de feromona"""
        return self.matrix[section_id].get(assignment_key, self.tau_init)
    
    def set(self, section_id: int, assignment_key: Tuple[int, int, int], value: float):
        """Establece el valor de feromona (con límites MMAS)"""
        value = max(self.tau_min, min(self.tau_max, value))
        self.matrix[section_id][assignment_key] = value
    
    def evaporate(self, rho: float):
        """Evapora todas las feromonas"""
        for section_id in self.matrix:
            for key in self.matrix[section_id]:
                current = self.matrix[section_id][key]
                new_value = (1 - rho) * current
                self.matrix[section_id][key] = max(self.tau_min, new_value)


# ============================================================================
# MOTOR ACO
# ============================================================================

class ACOEngine:
    """Motor principal del algoritmo ACO con heurística neural"""
    
    def __init__(
        self,
        graph: HeteroData,
        model: ACOGraphSAGEModel,
        graph_builder,  # TimetableGraphBuilder instance
        hard_validator: HardConstraintValidator,
        soft_evaluator: SoftConstraintEvaluator,
        params: Dict = None,
    ):
        self.graph = graph
        self.model = model
        self.graph_builder = graph_builder
        self.hard_validator = hard_validator
        self.soft_evaluator = soft_evaluator
        
        # Parámetros (merge con defaults)
        self.params = {**ACO_PARAMS, **(params or {})}
        self.n_hormigas = self.params["n_hormigas"]
        self.n_iteraciones = self.params["n_iteraciones"]
        self.alpha = self.params["alpha"]
        self.beta = self.params["beta"]
        self.rho = self.params["rho"]
        self.q0 = self.params["q0"]
        self.use_graphsage_heuristic = bool(self.params.get("use_graphsage_heuristic", True))
        self.collect_log_probs = bool(self.params.get("collect_log_probs", False))
        self.enforce_league_coherence = self.params.get("enforce_league_coherence", False)

        # Debugging helpers
        debug_sections = self.params.get("debug_sections", []) or []
        if isinstance(debug_sections, (int, str)):
            debug_sections = [int(debug_sections)]
        self.debug_sections = {int(sec_id) for sec_id in debug_sections}
        self.debug_log_limit = int(self.params.get("debug_log_limit", 120))
        self.verbose = self.params.get("verbose", False)  # Modo verbose
        self._last_debug_logs: List[str] = []

        # Relajación automática de corte pedagógico (para ciclos superiores)
        self.pedagogical_relaxation_min_cycle = int(self.params.get("pedagogical_relaxation_min_cycle", 4))
        self.pedagogical_relaxation_attempts = int(self.params.get("pedagogical_relaxation_attempts", 0))
        self.pedagogical_relaxation_rank_step = int(self.params.get("pedagogical_relaxation_rank_step", 0))
        
        # Matriz de feromonas (MMAS)
        self.pheromones = PheromoneMatrix(
            tau_min=self.params["tau_min"],
            tau_max=self.params["tau_max"],
            tau_init=self.params["tau_init"],
        )
        
        # Estadísticas
        self.best_solution: Optional[Solution] = None
        self.iteration_best: List[float] = []
        self.iteration_avg: List[float] = []
        self.completed_iterations: int = 0
        self.last_solution_log_probs: List[torch.Tensor] = []
        self._solution_log_probs_map: Dict[int, List[torch.Tensor]] = {}
        self._current_solution_log_probs: List[torch.Tensor] = []
        self._last_selection_log_prob: Optional[torch.Tensor] = None
        
        # Cache de candidatos por sección
        self._candidate_cache: Dict[int, List[Tuple[int, int, int]]] = {}
        
        # OPTIMIZACIÓN: Cache de validaciones para evitar re-validar
        self._validation_cache: Dict[Tuple[int, int, int, int, frozenset], bool] = {}
        
        # OPTIMIZACIÓN: Contador de iteraciones sin mejora para early stopping
        self._iterations_without_improvement = 0
        self._max_iterations_without_improvement = self.params.get("early_stopping_patience", 12)

        # OPTIMIZACIÓN: Acceso O(1) a bloques consecutivos por día/orden
        self._timeslot_lookup = {
            (ts.dia_semana, ts.orden): ts_id
            for ts_id, ts in self.hard_validator.timeslots.items()
        }
        
        # MEJORA: Identificar secciones críticas (profesores con alta restricción)
        self.critical_sections: Set[int] = set()
        self._identify_critical_sections()
    
    def _identify_critical_sections(self):
        """
        Identifica secciones críticas que requieren priorización especial.
        
        Criterios:
        - Profesor tiene 4+ días restringidos (de 6 días laborables)
        - Sección es tipo laboratorio (requiere 4 bloques consecutivos)
        """
        # Contar días restringidos por profesor
        prof_restricted_days: Dict[int, Set[Any]] = defaultdict(set)
        
        for prof_id, restrictions in self.hard_validator.professor_restrictions.items():
            for restriction in restrictions:
                start_time = getattr(restriction, "hora_inicio", None)
                end_time = getattr(restriction, "hora_fin", None)
                day_value = getattr(restriction, "dia_semana", None)

                if start_time is None:
                    start_time = getattr(restriction, "start_time", None)
                if end_time is None:
                    end_time = getattr(restriction, "end_time", None)
                if day_value is None:
                    day_value = getattr(restriction, "day", None)

                # Contar día como "restringido" si tiene bloqueo significativo (>= 6 horas)
                if start_time and end_time:
                    try:
                        from datetime import datetime, time as dt_time

                        def _to_time(value):
                            if value is None:
                                return None
                            if isinstance(value, dt_time):
                                return value
                            if isinstance(value, str):
                                text = value.strip()
                                for fmt in ("%H:%M", "%H:%M:%S"):
                                    try:
                                        return datetime.strptime(text, fmt).time()
                                    except ValueError:
                                        continue
                            if hasattr(value, "hour") and hasattr(value, "minute"):
                                return dt_time(hour=int(value.hour) % 24, minute=int(value.minute) % 60)
                            return None

                        st_time = _to_time(start_time)
                        et_time = _to_time(end_time)
                        if st_time is None or et_time is None:
                            continue

                        st = datetime.combine(datetime.min.date(), st_time)
                        et = datetime.combine(datetime.min.date(), et_time)
                        if et < st:
                            et = et.replace(day=et.day + 1)

                        duracion_horas = (et - st).total_seconds() / 3600
                        if duracion_horas >= 6.0:
                            prof_restricted_days[prof_id].add(day_value)
                    except (ValueError, TypeError):
                        pass
        
        # Identificar secciones de profesores altamente restringidos
        for sec_id in self.graph_builder.section_id_to_idx.keys():
            metadata = self.graph_builder.section_metadata.get(sec_id, {})
            session_type = (metadata.get("session_type") or "T").upper()
            
            # Buscar profesor asignado a esta sección
            assigned_prof = None
            sec_idx = self.graph_builder.section_id_to_idx[sec_id]
            
            if ('section', 'assigned_to', 'professor') in self.graph.edge_index_dict:
                edges = self.graph[('section', 'assigned_to', 'professor')].edge_index
                prof_indices = edges[1][edges[0] == sec_idx].tolist()
                if prof_indices:
                    assigned_prof = self.graph_builder.idx_to_professor_id.get(prof_indices[0])
            
            if assigned_prof is None:
                continue
            
            # Criterio: laboratorio + profesor con 3+ días restringidos
            restricted_days = len(prof_restricted_days.get(assigned_prof, set()))
            if session_type == "L" and restricted_days >= 2:  # BAJADO de 3 a 2 para ser más agresivo
                self.critical_sections.add(sec_id)
                if self.verbose:
                    print(f"[CRITICO] Sección {sec_id} marcada como crítica (prof {assigned_prof} con {restricted_days} días restringidos)")
        
        print(f"\n[INFO] Identificadas {len(self.critical_sections)} secciones críticas que requieren priorización especial")
        if self.critical_sections:
            print(f"        IDs críticos: {sorted(list(self.critical_sections)[:20])}{'...' if len(self.critical_sections) > 20 else ''}\n")
    
    def optimize(self, max_iterations: int = None) -> Solution:
        """
        Ejecuta el algoritmo ACO completo.
        
        Args:
            max_iterations: Número máximo de iteraciones (override)
        
        Returns:
            Mejor solución encontrada
        """
        n_iters = max_iterations or self.n_iteraciones
        self.completed_iterations = 0
        self.last_solution_log_probs = []
        self._solution_log_probs_map = {}
        
        print(f"\n{'='*80}")
        print(f"Iniciando ACO con {self.n_hormigas} hormigas, {n_iters} iteraciones")
        print(f"Alpha={self.alpha}, Beta={self.beta}, Rho={self.rho}, Q0={self.q0}")
        print(f"{'='*80}\n")

        allow_partial_solutions = bool(self.params.get("allow_partial_solutions", True))
        
        for iteration in range(n_iters):
            iteration_index = iteration + 1
            # Construir soluciones con todas las hormigas
            solutions = []
            for ant_id in range(self.n_hormigas):
                solution = self._construct_solution(ant_id, iteration)
                if solution.is_valid or allow_partial_solutions:
                    solutions.append(solution)
            
            if not solutions:
                print(f"Iteración {iteration_index}/{n_iters}: [WARN]  No se encontraron soluciones válidas")
                self.completed_iterations = iteration_index
                continue
            
            # Encontrar mejor de esta iteración
            iteration_best_solution = min(solutions, key=lambda s: s.total_cost)
            avg_cost = sum(s.total_cost for s in solutions) / len(solutions)
            
            self.iteration_best.append(iteration_best_solution.total_cost)
            self.iteration_avg.append(avg_cost)
            
            # Actualizar mejor global
            if self.best_solution is None or iteration_best_solution.total_cost < self.best_solution.total_cost:
                self.best_solution = iteration_best_solution
                self.last_solution_log_probs = list(
                    self._solution_log_probs_map.get(id(iteration_best_solution), [])
                )
                self._iterations_without_improvement = 0  # Reset contador
                print(f"Iteración {iteration_index}/{n_iters}: [OK] Nueva mejor solución: {self.best_solution.total_cost:.2f}")
            else:
                self._iterations_without_improvement += 1
                print(f"Iteración {iteration_index}/{n_iters}: Mejor={iteration_best_solution.total_cost:.2f}, "
                      f"Avg={avg_cost:.2f}, Global={self.best_solution.total_cost:.2f}")
            
            self.completed_iterations = iteration_index
            
            # OPTIMIZACIÓN: Early stopping si no hay mejoras
            if self._iterations_without_improvement >= self._max_iterations_without_improvement:
                print(f"\n[WARN]  Early stopping: No hay mejoras en {self._max_iterations_without_improvement} iteraciones")
                break
            
            # Evaporar feromonas
            self.pheromones.evaporate(self.rho)
            
            # Actualizar feromonas (elitista: mejor iteración + mejor global)
            self._update_pheromones(iteration_best_solution, weight=1.0 - self.params["elitist_weight"])
            self._update_pheromones(self.best_solution, weight=self.params["elitist_weight"])
        
        print(f"\n{'='*80}")
        if self.best_solution is not None:
            print(f"[OK] Optimización completada. Costo final: {self.best_solution.total_cost:.2f}")
            
            # REPARACIÓN GREEDY
            total_sections = len(self.graph_builder.section_id_to_idx)
            if len(self.best_solution.assignments) < total_sections:
                print(f"[REPARACIÓN] Cobertura parcial ({len(self.best_solution.assignments)}/{total_sections}). Iniciando reparación greedy...")
                self.best_solution = self._greedy_repair(self.best_solution)
        else:
            print(f"[WARN] Optimización completada SIN soluciones válidas encontradas")
        print(f"{'='*80}\n")
        
        return self.best_solution
    
    def _construct_solution(self, ant_id: int, iteration: int) -> Solution:
        """
        Construye una solución completa usando una hormiga.
        
        Proceso:
        1. Ordenar secciones por prioridad
        2. Para cada sección, seleccionar asignación usando feromona + heurística
        3. Validar restricciones duras en cada paso
        4. Calcular costo final con restricciones blandas
        """
        assignments = []
        construction_log = []
        self._current_solution_log_probs = []
        
        # Obtener todas las secciones a asignar
        section_ids = list(self.graph_builder.section_id_to_idx.keys())

        # Agrupar por curso+liga para respetar secuencia pedagógica T -> P -> L
        type_order = {"T": 0, "P": 1, "L": 2, "V": 3}
        grouped_sections: Dict[Tuple[Optional[str], Optional[int]], List[int]] = defaultdict(list)
        for sec_id in section_ids:
            metadata = self.graph_builder.section_metadata.get(sec_id, {})
            course_code = metadata.get("course_code")
            league = metadata.get("league")
            key = (course_code, league)
            if course_code is None and league is None:
                key = ("__UNCLUSTERED__", sec_id)
            grouped_sections[key].append(sec_id)

        def group_sort_key(group_key: Tuple[Optional[str], Optional[int]]) -> Tuple[str, int]:
            course, league = group_key
            course_key = course or ""
            league_key = league if isinstance(league, int) else 0
            return (course_key, league_key)

        sorted_section_ids: List[int] = []
        
        # PRIORIDAD MÁXIMA: Secciones críticas (profesores altamente restringidos)
        critical_groups = []
        priority_groups_param = self.params.get("priority_course_groups", [("CIEN769", 1)])
        priority_section_groups = []
        regular_section_groups = []
        
        for group_key in sorted(grouped_sections.keys(), key=group_sort_key):
            course_code, league = group_key
            sections_in_group = grouped_sections[group_key]
            
            # Verificar si alguna sección del grupo es crítica
            has_critical = any(sec_id in self.critical_sections for sec_id in sections_in_group)
            
            if has_critical:
                critical_groups.append((group_key, sections_in_group))
            elif (course_code, league) in priority_groups_param:
                priority_section_groups.append((group_key, sections_in_group))
            else:
                regular_section_groups.append((group_key, grouped_sections[group_key]))
        
        # Procesar en orden: CRÍTICOS -> PRIORITARIOS -> REGULARES
        all_groups = critical_groups + priority_section_groups + regular_section_groups
        
        for group_key, sections in all_groups:

            def section_priority(sec_id: int) -> Tuple[int, int, int, int]:
                duration = self.graph_builder.section_durations.get(sec_id, 1)
                projected = self.graph_builder.section_projected_students.get(sec_id, 0)
                metadata = self.graph_builder.section_metadata.get(sec_id, {})
                session_type = (metadata.get("session_type") or "T").upper()
                priority = type_order.get(session_type, 99)
                return (priority, -duration, -projected, sec_id)

            sections.sort(key=section_priority)
            sorted_section_ids.extend(sections)
        
        # Construir asignaciones una por una
        failed_sections = []  # Trackear secciones que no se pudieron asignar
        
        for sec_id in sorted_section_ids:
            assignment = self._assign_section(sec_id, assignments, ant_id)
            
            if assignment is None:
                # No se pudo asignar esta sección - CONTINUAR en vez de abortar
                failed_sections.append(sec_id)
                construction_log.append(f"[X] No se pudo asignar sección {sec_id}")
                if self._last_debug_logs:
                    construction_log.extend(self._last_debug_logs)
                else:
                    construction_log.append(
                        "(sin detalles porque la sección no estaba en debug_sections)"
                    )
                # **CONTINUAR** procesando otras secciones en vez de abortar
                continue
            
            assignments.append(assignment)
            # Log detallado en modo verbose
            if self.verbose:
                prof_id = assignment.professor_id
                aula_id = assignment.classroom_id
                franjas = ','.join(map(str, assignment.timeslot_ids[:4]))  # Primeras 4 franjas
                if len(assignment.timeslot_ids) > 4:
                    franjas += f'...(+{len(assignment.timeslot_ids)-4})'
                construction_log.append(
                    f"[OK] Sec={sec_id:4d} -> Prof={prof_id:3d}, Aula={aula_id:2d}, Slots=[{franjas}]"
                )
            else:
                construction_log.append(f"[OK] Asignada sección {sec_id}")
            if self._last_debug_logs:
                construction_log.extend(self._last_debug_logs)
        
        # Determinar si la solución es válida basado en cobertura
        coverage = len(assignments) / len(sorted_section_ids) if sorted_section_ids else 0.0
        coverage_threshold = float(self.params.get("coverage_threshold", 0.90))
        is_valid = coverage >= coverage_threshold
        
        # Modo verbose: imprimir TODOS los logs de construcción
        if self.verbose:
            print(f"\n{'='*80}")
            print(f"[CONSTRUCCIÓN] Hormiga {ant_id}, Iteración {iteration + 1}")
            print(f"{'='*80}")
            for log_line in construction_log:
                print(f"  {log_line}")
            print(f"{'='*80}")
            print(f"Resultado: {len(assignments)}/{len(sorted_section_ids)} secciones asignadas ({coverage*100:.1f}%)")
            print(f"{'='*80}\n")
        
        if failed_sections:
            preview = "\n      ".join(construction_log[-min(len(construction_log), 20):])
            print(
                f"[Diagnóstico ACO] Iteración {iteration + 1}, hormiga {ant_id}: "
                f"asignó {len(assignments)}/{len(sorted_section_ids)} secciones ({coverage*100:.1f}%).\n"
                f"      Secciones no asignadas: {failed_sections[:10]}"
                f"{'...' if len(failed_sections) > 10 else ''}\n"
                f"      Historial reciente:\n      {preview}"
            )
        
        # Calcular costo con restricciones blandas
        total_cost, penalties = self.soft_evaluator.calculate_total_penalty(assignments)
        
        # PENALIZAR soluciones parciales severamente (pero no infinito)
        if not is_valid:
            total_cost += 1000.0 * len(failed_sections)  # Penalización por secciones faltantes
        
        solution = Solution(
            assignments=assignments,
            total_cost=total_cost,
            soft_penalties=penalties,
            is_valid=is_valid,
            construction_log=construction_log,
        )
        self._solution_log_probs_map[id(solution)] = list(self._current_solution_log_probs)
        return solution
    
    def _assign_section(
        self,
        section_id: int,
        current_schedule: List[Assignment],
        ant_id: int,
    ) -> Optional[Assignment]:
        """
        Asigna una sección usando feromona + heurística neural.
        
        Returns:
            Assignment si se pudo asignar, None si no hay opciones válidas
        """
        self._last_debug_logs = []
        debug_enabled = section_id in self.debug_sections
        is_critical = section_id in self.critical_sections

        def debug(message: str):
            if debug_enabled and len(self._last_debug_logs) < self.debug_log_limit:
                self._last_debug_logs.append(message)
        
        # MEJORA: Secciones críticas obtienen más candidatos para mayor exploración
        candidates = self._get_candidate_assignments(section_id, is_critical=is_critical)
        if is_critical:
            debug(f"[CRITICO] Sección {section_id}: {len(candidates)} candidatos (modo crítico con exploración ampliada)")
        else:
            debug(f"[BUSCAR] Sección {section_id}: {len(candidates)} candidatos iniciales")

        if not candidates:
            debug("[BLOQUEADO] No se encontraron combinaciones profesor/aula/horario desde el grafo")
            return None
        
        # OPTIMIZACIÓN: Crear conjunto de recursos ocupados para validación rápida
        metadata = self.graph_builder.section_metadata.get(section_id, {})
        course_code = metadata.get("course_code") or f"SECTION-{section_id}"
        league_id = metadata.get("league") or 1
        ciclo_value_raw = metadata.get("ciclo")
        ciclo = ciclo_value_raw or "SIN-CICLO"
        try:
            ciclo_numeric = int(str(ciclo_value_raw))
        except (TypeError, ValueError):
            ciclo_numeric = None
        projected_students = self.graph_builder.section_projected_students.get(section_id, 0)
        session_type = (metadata.get("session_type") or "T").upper()
        modalidad = metadata.get("modalidad", "").upper()
        
        # MANEJO ESPECIAL: Cursos virtuales NO_PRESENCIAL no necesitan aula física
        is_virtual = modalidad == "NO_PRESENCIAL"
        if is_virtual:
            debug(f"[VIRTUAL] Sección {section_id} es VIRTUAL (NO_PRESENCIAL) - no requiere aula física")

        # Enforzar T -> P -> L: si falta teoría/práctica previas, diferir esta asignación
        league_key = (course_code, league_id)
        if session_type in {"P", "L"}:
            predecessors = {"T"} if session_type == "P" else {"T", "P"}
            assigned_section_ids = {
                assignment.section_id
                for assignment in current_schedule
                if assignment.course_code == course_code and assignment.league_id == league_id
            }
            pending_predecessors = [
                sec
                for sec in self.hard_validator.sections_by_league.get(league_key, [])
                if (
                    self.hard_validator.section_session_types.get(sec, "").upper() in predecessors
                    and sec not in assigned_section_ids
                )
            ]
            if pending_predecessors:
                debug(
                    f"[PENDIENTE] Pendiente asignar secciones {pending_predecessors} antes de programar {section_id}"
                )
                return None

        pedagogical_cutoff = self._compute_pedagogical_cutoff(
            course_code,
            league_id,
            session_type,
            current_schedule,
        )

        if pedagogical_cutoff is not None and not self._has_candidate_after_rank(candidates, pedagogical_cutoff):
            expanded_candidates = self._get_candidate_assignments(
                section_id,
                min_start_rank=pedagogical_cutoff,
                is_critical=is_critical,
            )
            if expanded_candidates:
                debug(
                    f"[PEDAGOGICO] Expandimos candidatos posteriores a {pedagogical_cutoff} "
                    f"(de {len(candidates)} a {len(expanded_candidates)})"
                )
                candidates = expanded_candidates
            else:
                debug(
                    f"[PEDAGOGICO] Sin franjas disponibles después del requisito mínimo "
                    f"{pedagogical_cutoff}"
                )

        occupied_timeslots_by_prof: Dict[int, Set[int]] = {}
        occupied_timeslots_by_classroom: Dict[int, Set[int]] = {}
        curriculum_slots: Dict[Tuple[str, int], Tuple[str, int]] = {}
        league_slots: Dict[Tuple[str, int], Set[int]] = defaultdict(set)
        
        for existing in current_schedule:
            # Profesores ocupados
            if existing.professor_id not in occupied_timeslots_by_prof:
                occupied_timeslots_by_prof[existing.professor_id] = set()
            occupied_timeslots_by_prof[existing.professor_id].update(existing.timeslot_ids)
            
            # Aulas ocupadas (SOLO para cursos presenciales)
            if existing.classroom_id is not None:
                if existing.classroom_id not in occupied_timeslots_by_classroom:
                    occupied_timeslots_by_classroom[existing.classroom_id] = set()
                occupied_timeslots_by_classroom[existing.classroom_id].update(existing.timeslot_ids)

            for ts_id in existing.timeslot_ids:
                curriculum_slots[(existing.ciclo, ts_id)] = (existing.course_code, existing.league_id)
                if self.enforce_league_coherence:
                    league_slots[(existing.course_code, existing.league_id)].add(ts_id)
        
        # Filtrar candidatos que violan restricciones duras
        valid_candidates = []
        candidate_timeslots: Dict[Tuple[int, int, int], List[int]] = {}
        for prof_idx, classroom_idx, timeslot_idx in candidates:
            # OPTIMIZACIÓN: Validación rápida de conflictos básicos antes de construir Assignment
            professor_id = self.graph_builder.idx_to_professor_id[prof_idx]
            
            # Manejo especial para cursos virtuales (classroom_idx == -1)
            if classroom_idx == -1:
                classroom_id = None  # Sin aula física
                is_virtual_candidate = True
            else:
                classroom_id = self.graph_builder.idx_to_classroom_id[classroom_idx]
                # Filtrar candidatos que violan restricciones duras, con relajación pedagógica opcional
                def _evaluate_candidates(ped_limit: Optional[int]):
                    valid: List[Tuple[int, int, int]] = []
                    timeslot_map: Dict[Tuple[int, int, int], List[int]] = {}
                    blocked_by_pedagogical = False

                    for prof_idx, classroom_idx, timeslot_idx in candidates:
                        professor_id = self.graph_builder.idx_to_professor_id[prof_idx]

                        if classroom_idx == -1:
                            classroom_id = None
                            is_virtual_candidate = True
                        else:
                            classroom_id = self.graph_builder.idx_to_classroom_id[classroom_idx]
                            is_virtual_candidate = False

                        timeslot_start_id = self.graph_builder.idx_to_timeslot_id[timeslot_idx]
                        duracion = self.graph_builder.section_durations.get(section_id, 1)
                        start_ts = self.hard_validator.timeslots[timeslot_start_id]
                        timeslot_sequence = self._get_consecutive_timeslots(
                            start_ts.dia_semana,
                            start_ts.orden,
                            duracion,
                        )

                        if not timeslot_sequence or timeslot_sequence[0] != timeslot_start_id:
                            debug(
                                f"[BLOQUES]  Bloques insuficientes (duración {duracion}) para prof {professor_id}, aula {classroom_id}, inicio {timeslot_start_id}"
                            )
                            continue

                        if ped_limit is not None:
                            candidate_rank = self.hard_validator._timeslot_rank(start_ts)
                            if candidate_rank <= ped_limit:
                                blocked_by_pedagogical = True
                                debug(
                                    f"[PEDAGOGICO] Franjas {timeslot_sequence} ocurren antes del requisito mínimo {ped_limit}"
                                )
                                continue

                        needed_slots_set = set(timeslot_sequence)

                        if not is_virtual_candidate:
                            classroom_info = self.hard_validator.classrooms.get(classroom_id)
                            if classroom_info and classroom_info.capacidad is not None and projected_students:
                                if projected_students > classroom_info.capacidad:
                                    debug(
                                        f"[CAPACIDAD] Capacidad insuficiente aula {classroom_id} ({projected_students}>{classroom_info.capacidad})"
                                    )
                                    continue

                        has_curriculum_conflict = False
                        for ts_id in timeslot_sequence:
                            existing_course_league = curriculum_slots.get((ciclo, ts_id))
                            if existing_course_league is None:
                                continue

                            existing_course, existing_league = existing_course_league

                            if existing_course == course_code:
                                continue

                            if league_id is None or existing_league is None:
                                relevant_overlap = True
                            else:
                                relevant_overlap = existing_league == league_id

                            if not relevant_overlap:
                                continue

                            has_curriculum_conflict = True
                            debug(
                                f"[CURRICULA] Conflicto curricular en ciclo {ciclo} con curso {existing_course} liga {existing_league} en franja {ts_id}"
                            )
                            break
                        if has_curriculum_conflict:
                            continue

                        league_key = (course_code, league_id)
                        # MEJORA: Para secciones críticas, PERMITIR solapamiento de liga si es necesario
                        if self.enforce_league_coherence and not is_critical:
                            overlap = league_slots.get(league_key, set()) & needed_slots_set
                            if overlap:
                                debug(
                                    f"[LIGA]  Cruce con liga {league_key} en franjas {sorted(overlap)}"
                                )
                                continue
                        elif is_critical and self.enforce_league_coherence:
                            # Para críticos: advertir pero NO bloquear
                            overlap = league_slots.get(league_key, set()) & needed_slots_set
                            if overlap:
                                debug(
                                    f"[LIGA] (PERMITIDO para crítico) Cruce con liga {league_key} en franjas {sorted(overlap)}"
                                )

                        if professor_id in occupied_timeslots_by_prof:
                            if occupied_timeslots_by_prof[professor_id] & needed_slots_set:
                                debug(
                                    f"[PROFESOR_OCUPADO] Profesor {professor_id} ocupado en franjas {sorted(occupied_timeslots_by_prof[professor_id] & needed_slots_set)}"
                                )
                                continue

                        prof_restrictions = self.hard_validator.professor_restrictions.get(professor_id, [])
                        if prof_restrictions:
                            violates_restriction = False
                            for ts_id in timeslot_sequence:
                                ts = self.hard_validator.timeslots[ts_id]
                                for restriction in prof_restrictions:
                                    if (restriction.dia_semana == ts.dia_semana and 
                                        self.hard_validator._time_overlaps(
                                            ts.hora_inicio, ts.hora_fin,
                                            restriction.hora_inicio, restriction.hora_fin
                                        )):
                                        debug(
                                            f"[RESTRICCION_PROF] Profesor {professor_id} NO disponible {restriction.dia_semana} "
                                            f"{restriction.hora_inicio}-{restriction.hora_fin} (franja {ts_id})"
                                        )
                                        violates_restriction = True
                                        break
                                if violates_restriction:
                                    break
                            if violates_restriction:
                                continue

                        if not is_virtual_candidate and classroom_id in occupied_timeslots_by_classroom:
                            if occupied_timeslots_by_classroom[classroom_id] & needed_slots_set:
                                debug(
                                    f"[AULA] Aula {classroom_id} ocupada en franjas {sorted(occupied_timeslots_by_classroom[classroom_id] & needed_slots_set)}"
                                )
                                continue

                        schedule_fingerprint = frozenset((a.section_id, a.professor_id, a.classroom_id, tuple(a.timeslot_ids)) 
                                                        for a in current_schedule[-5:])
                        cache_key = (section_id, professor_id, classroom_id, timeslot_start_id, schedule_fingerprint)

                        if cache_key in self._validation_cache:
                            if self._validation_cache[cache_key]:
                                candidate_key = (prof_idx, classroom_idx, timeslot_idx)
                                valid.append(candidate_key)
                                timeslot_map[candidate_key] = timeslot_sequence
                            continue

                        assignment = self._build_assignment_object(
                            section_id,
                            prof_idx,
                            classroom_idx,
                            timeslot_idx,
                            precomputed_timeslots=timeslot_sequence,
                        )

                        is_valid, error = self.hard_validator.validate_all(assignment, current_schedule)
                        self._validation_cache[cache_key] = is_valid

                        if is_valid:
                            candidate_key = (prof_idx, classroom_idx, timeslot_idx)
                            valid.append(candidate_key)
                            timeslot_map[candidate_key] = timeslot_sequence
                        else:
                            debug(
                                f"[X] Validación dura falló para prof {professor_id}, aula {classroom_id}, franjas {timeslot_sequence}: {error}"
                            )

                    return valid, timeslot_map, blocked_by_pedagogical

                ped_limit = pedagogical_cutoff
                candidate_timeslots: Dict[Tuple[int, int, int], List[int]] = {}
                last_blocked_by_pedagogical = False
                
                # MEJORA: Secciones críticas obtienen más intentos de relajación y step más agresivo
                if is_critical:
                    relaxation_attempts = 8  # REDUCIDO para performance
                    rank_step = 40  # AUMENTADO para menos pasos
                    # Para críticos, habilitar relajación desde ciclo 1 (no solo ciclo 4+)
                    min_cycle_for_relaxation = 1
                else:
                    relaxation_attempts = self.pedagogical_relaxation_attempts
                    rank_step = self.pedagogical_relaxation_rank_step
                    min_cycle_for_relaxation = self.pedagogical_relaxation_min_cycle
                
                relaxation_enabled = (
                    ped_limit is not None
                    and ciclo_numeric is not None
                    and ciclo_numeric >= min_cycle_for_relaxation
                    and relaxation_attempts > 0
                )
                attempts_left = relaxation_attempts if relaxation_enabled else 0
                current_rank_step = rank_step

                while True:
                    valid_candidates, candidate_timeslots, last_blocked_by_pedagogical = _evaluate_candidates(ped_limit)
                    if valid_candidates:
                        break

                    should_attempt_relaxation = (
                        relaxation_enabled
                        and ped_limit is not None
                        and attempts_left > 0
                    )

                    if not should_attempt_relaxation:
                        break

                    if not last_blocked_by_pedagogical:
                        debug(
                            "[PEDAGOGICO] No quedan combinaciones válidas posteriores; relajamos requisito aunque otras restricciones también bloqueen"
                        )

                    attempts_left -= 1
                    prev_limit = ped_limit
                    if ped_limit is None or current_rank_step <= 0:
                        ped_limit = None
                    else:
                        ped_limit -= current_rank_step
                        if ped_limit < 0:
                            ped_limit = None

                    if ped_limit is None:
                        debug("[PEDAGOGICO] Sin franjas posteriores compatibles; se desactiva el requisito pedagógico para esta sección")
                    else:
                        debug(
                            f"[PEDAGOGICO] Relajamos rank mínimo de {prev_limit} a {ped_limit} para sección {section_id}"
                        )

                if not valid_candidates:
                    if last_blocked_by_pedagogical and pedagogical_cutoff is not None:
                        debug("[PEDAGOGICO] Incluso tras relajar no se encontraron franjas válidas")
                    debug("[BLOQUEADO] Sin candidatos válidos tras validaciones duras")
                    return None

                # Seleccionar usando feromona + heurística (regla de transición ACO)
                selected = self._select_assignment(section_id, valid_candidates, ant_id)
                if self.collect_log_probs and self._last_selection_log_prob is not None:
                    self._current_solution_log_probs.append(self._last_selection_log_prob)
                prof_id = self.graph_builder.idx_to_professor_id[selected[0]]
                classroom_id_str = "VIRTUAL (sin aula)" if selected[1] == -1 else str(self.graph_builder.idx_to_classroom_id[selected[1]])
                timeslot_id = self.graph_builder.idx_to_timeslot_id[selected[2]]

                debug(
                    f"⭐ Sección {section_id} asignada con prof {prof_id}, "
                    f"aula {classroom_id_str}, franja inicial {timeslot_id}"
                )
                return self._build_assignment_object(
                    section_id,
                    selected[0],
                    selected[1],
                    selected[2],
                    precomputed_timeslots=candidate_timeslots.get(selected),
                )

    def _compute_pedagogical_cutoff(
        self,
        course_code: str,
        league_id: int,
        session_type: str,
        current_schedule: List[Assignment],
    ) -> Optional[int]:
        """Obtiene el rank mínimo permitido según sesiones predecesoras ya asignadas."""
        session_type = (session_type or "T").upper()
        if session_type == "T":
            return None

        if session_type == "P":
            required = {"T"}
        else:  # L
            required = {"P"}
            # Si no existe práctica asignada, usar teoría como fallback
            has_practica = any(
                a.course_code == course_code and a.league_id == league_id and a.session_type == "P"
                for a in current_schedule
            )
            if not has_practica:
                required.add("T")

        latest_rank: Optional[int] = None
        for assignment in current_schedule:
            if assignment.course_code != course_code or assignment.league_id != league_id:
                continue
            if assignment.session_type not in required:
                continue

            rank = self.hard_validator._assignment_start_rank(assignment)
            if rank is None:
                continue

            if latest_rank is None or rank > latest_rank:
                latest_rank = rank

        return latest_rank
    
    def _get_candidate_assignments(
        self,
        section_id: int,
        min_start_rank: Optional[int] = None,
        is_critical: bool = False,
    ) -> List[Tuple[int, int, int]]:
        """
        Obtiene las asignaciones candidatas para una sección.
        
        Basado en las aristas del grafo:
        - section -> professor
        - section -> classroom
        - section -> timeslot
        
        Args:
            section_id: ID de la sección
            min_start_rank: Rank mínimo pedagógico (si aplica)
            is_critical: Si True, amplía límites de exploración para secciones críticas
        
        Returns:
            Lista de (prof_idx, classroom_idx, timeslot_idx)
        """
        if min_start_rank is None and not is_critical:
            cached = self._candidate_cache.get(section_id)
            if cached is not None:
                return cached

        sec_idx = self.graph_builder.section_id_to_idx[section_id]
        
        # Obtener profesores candidatos (desde aristas del grafo)
        if ('section', 'assigned_to', 'professor') in self.graph.edge_index_dict:
            section_to_prof_edges = self.graph[('section', 'assigned_to', 'professor')].edge_index
            prof_candidates = section_to_prof_edges[1][section_to_prof_edges[0] == sec_idx].tolist()
        else:
            prof_candidates = []
        
        # Obtener aulas candidatas
        if ('section', 'uses', 'classroom') in self.graph.edge_index_dict:
            section_to_classroom_edges = self.graph[('section', 'uses', 'classroom')].edge_index
            classroom_candidates = section_to_classroom_edges[1][section_to_classroom_edges[0] == sec_idx].tolist()
        else:
            classroom_candidates = []
        
        # Obtener franjas candidatas (bloques de inicio)
        if ('section', 'starts_at', 'timeslot') in self.graph.edge_index_dict:
            section_to_timeslot_edges = self.graph[('section', 'starts_at', 'timeslot')].edge_index
            timeslot_candidates = section_to_timeslot_edges[1][section_to_timeslot_edges[0] == sec_idx].tolist()
        else:
            timeslot_candidates = []
        
        shuffle_enabled = self.params.get("shuffle_candidates", True)
        if shuffle_enabled:
            random.shuffle(prof_candidates)
            random.shuffle(classroom_candidates)

        ordered_timeslots = self._order_timeslot_candidates(
            timeslot_candidates,
            min_start_rank,
            shuffle_enabled,
        )

        # Producto cartesiano (limitado para eficiencia)
        candidates: List[Tuple[int, int, int]] = []

        max_profs = min(
            len(prof_candidates),
            self.params.get("max_professors_per_section", len(prof_candidates)),
        )
        max_classrooms = min(
            len(classroom_candidates),
            self.params.get("max_classrooms_per_section", len(classroom_candidates)),
        )

        # MEJORA: Secciones críticas obtienen más slots de tiempo para explorar
        base_timeslot_limit = self.params.get("max_timeslots_per_section")
        if is_critical:
            # Críticos: explorar hasta 18 franjas (1.5x normal de 12) - REDUCIDO para performance
            max_timeslots = min(len(ordered_timeslots), 18)
        elif min_start_rank is not None:
            max_timeslots = len(ordered_timeslots)
        elif base_timeslot_limit is None or base_timeslot_limit <= 0:
            max_timeslots = len(ordered_timeslots)
        else:
            duration = max(1, self.graph_builder.section_durations.get(section_id, 1))
            scaled_limit = base_timeslot_limit * duration
            max_timeslots = min(len(ordered_timeslots), scaled_limit)

        if max_profs == 0 or max_classrooms == 0 or max_timeslots == 0:
            return candidates

        total_possible = max_profs * max_classrooms * max_timeslots
        # MEJORA: Secciones críticas obtienen 1.5x combinaciones (900 vs 600) - REDUCIDO para performance
        base_max_combinations = self.params.get("max_candidate_combinations", 600)
        requested_max = int(base_max_combinations * 1.5) if is_critical else base_max_combinations
        if requested_max is None or requested_max <= 0:
            max_candidates = total_possible
        else:
            max_candidates = max(1, min(requested_max, total_possible))

        per_prof_base = max_candidates // max_profs
        remainder = max_candidates % max_profs

        classroom_subset = classroom_candidates[:max_classrooms]
        timeslot_subset = ordered_timeslots[:max_timeslots]

        for idx, prof_idx in enumerate(prof_candidates[:max_profs]):
            quota = per_prof_base + (1 if idx < remainder else 0)
            if quota == 0:
                continue

            added = 0
            for classroom_idx in classroom_subset:
                for timeslot_idx in timeslot_subset:
                    candidates.append((prof_idx, classroom_idx, timeslot_idx))
                    added += 1
                    if len(candidates) >= max_candidates:
                        return candidates
                    if added >= quota:
                        break
                if len(candidates) >= max_candidates or added >= quota:
                    break

        if not candidates:
            metadata_check = self.graph_builder.section_metadata.get(section_id, {})
            modalidad_check = metadata_check.get("modalidad", "").upper()
            if modalidad_check == "NO_PRESENCIAL":
                candidates = self._generate_virtual_candidates(
                    section_id,
                    min_start_rank=min_start_rank,
                )

        # No cachear secciones críticas para que siempre usen límites ampliados
        if min_start_rank is None and not is_critical:
            self._candidate_cache[section_id] = candidates

        return candidates
    
    def _generate_virtual_candidates(
        self,
        section_id: int,
        min_start_rank: Optional[int] = None,
    ) -> List[Tuple[int, int, int]]:
        """
        Genera candidatos para cursos virtuales (NO_PRESENCIAL).
        Estos cursos necesitan profesor y horario, pero NO aula física.
        
        Usamos -1 como índice especial de aula para indicar "sin aula".
        
        Returns:
            Lista de (prof_idx, -1, timeslot_idx)
        """
        sec_idx = self.graph_builder.section_id_to_idx[section_id]
        
        # Obtener profesores candidatos (desde aristas del grafo)
        if ('section', 'assigned_to', 'professor') in self.graph.edge_index_dict:
            section_to_prof_edges = self.graph[('section', 'assigned_to', 'professor')].edge_index
            prof_candidates = section_to_prof_edges[1][section_to_prof_edges[0] == sec_idx].tolist()
        else:
            prof_candidates = []
        
        # Obtener franjas candidatas
        if ('section', 'starts_at', 'timeslot') in self.graph.edge_index_dict:
            section_to_timeslot_edges = self.graph[('section', 'starts_at', 'timeslot')].edge_index
            timeslot_candidates = section_to_timeslot_edges[1][section_to_timeslot_edges[0] == sec_idx].tolist()
        else:
            timeslot_candidates = []
        
        shuffle_enabled = self.params.get("shuffle_candidates", True)
        if shuffle_enabled:
            random.shuffle(prof_candidates)
        ordered_timeslots = self._order_timeslot_candidates(
            timeslot_candidates,
            min_start_rank,
            shuffle_enabled,
        )
        
        # Producto cartesiano prof × timeslot (sin aula)
        candidates: List[Tuple[int, int, int]] = []
        
        max_profs = min(
            len(prof_candidates),
            self.params.get("max_professors_per_section", len(prof_candidates)),
        )
        
        base_timeslot_limit = self.params.get("max_timeslots_per_section")
        if min_start_rank is not None:
            max_timeslots = len(ordered_timeslots)
        elif base_timeslot_limit is None or base_timeslot_limit <= 0:
            max_timeslots = len(ordered_timeslots)
        else:
            duration = max(1, self.graph_builder.section_durations.get(section_id, 1))
            scaled_limit = base_timeslot_limit * duration
            max_timeslots = min(len(ordered_timeslots), scaled_limit)
        
        # Para cursos virtuales, usamos -1 como índice de "sin aula"
        VIRTUAL_CLASSROOM_IDX = -1
        ordered_subset = ordered_timeslots[:max_timeslots]
        for prof_idx in prof_candidates[:max_profs]:
            for timeslot_idx in ordered_subset:
                candidates.append((prof_idx, VIRTUAL_CLASSROOM_IDX, timeslot_idx))
        
        return candidates
    
    def _has_candidate_after_rank(
        self,
        candidates: List[Tuple[int, int, int]],
        min_rank: int,
    ) -> bool:
        """Detecta si algún candidato comienza después del rank indicado."""
        for _, _, timeslot_idx in candidates:
            candidate_rank = self._timeslot_rank_from_idx(timeslot_idx)
            if candidate_rank is not None and candidate_rank > min_rank:
                return True
        return False

    def _order_timeslot_candidates(
        self,
        timeslot_candidates: List[int],
        min_start_rank: Optional[int],
        shuffle_enabled: bool,
    ) -> List[int]:
        """Prioriza franjas posteriores al rank pedagógico requerido."""
        if not timeslot_candidates:
            return []

        if min_start_rank is None:
            ordered = list(timeslot_candidates)
            if shuffle_enabled:
                random.shuffle(ordered)
            return ordered

        later: List[int] = []
        earlier_or_unknown: List[int] = []
        for ts_idx in timeslot_candidates:
            rank = self._timeslot_rank_from_idx(ts_idx)
            if rank is None or rank <= min_start_rank:
                earlier_or_unknown.append(ts_idx)
            else:
                later.append(ts_idx)

        if shuffle_enabled:
            random.shuffle(later)
            random.shuffle(earlier_or_unknown)

        return later + earlier_or_unknown

    def _timeslot_rank_from_idx(self, timeslot_idx: int) -> Optional[int]:
        """Mapea un índice de grafo a su rank lineal día/orden."""
        timeslot_id = self.graph_builder.idx_to_timeslot_id.get(timeslot_idx)
        if timeslot_id is None:
            return None
        timeslot = self.hard_validator.timeslots.get(timeslot_id)
        if timeslot is None:
            return None
        return self.hard_validator._timeslot_rank(timeslot)
    
    def _get_virtual_candidates(
        self,
        section_id: int,
    ) -> List[Tuple[int, int, int]]:
        """
        Genera candidatos para cursos virtuales (NO_PRESENCIAL).
        Estos cursos necesitan profesor y horario, pero NO aula física.
        
        Usamos -1 como índice especial de aula para indicar "sin aula".
        
        Returns:
            Lista de (prof_idx, -1, timeslot_idx)
        """
        sec_idx = self.graph_builder.section_id_to_idx[section_id]
        
        # Obtener profesores candidatos (desde aristas del grafo)
        if ('section', 'assigned_to', 'professor') in self.graph.edge_index_dict:
            section_to_prof_edges = self.graph[('section', 'assigned_to', 'professor')].edge_index
            prof_candidates = section_to_prof_edges[1][section_to_prof_edges[0] == sec_idx].tolist()
        else:
            prof_candidates = []
        
        # Obtener franjas candidatas
        if ('section', 'starts_at', 'timeslot') in self.graph.edge_index_dict:
            section_to_timeslot_edges = self.graph[('section', 'starts_at', 'timeslot')].edge_index
            timeslot_candidates = section_to_timeslot_edges[1][section_to_timeslot_edges[0] == sec_idx].tolist()
        else:
            timeslot_candidates = []
        
        # Producto cartesiano prof × timeslot (sin aula)
        candidates: List[Tuple[int, int, int]] = []
        
        if self.params.get("shuffle_candidates", True):
            random.shuffle(prof_candidates)
            random.shuffle(timeslot_candidates)
        
        max_profs = min(
            len(prof_candidates),
            self.params.get("max_professors_per_section", len(prof_candidates)),
        )
        
        base_timeslot_limit = self.params.get("max_timeslots_per_section")
        if base_timeslot_limit is None or base_timeslot_limit <= 0:
            max_timeslots = len(timeslot_candidates)
        else:
            duration = max(1, self.graph_builder.section_durations.get(section_id, 1))
            scaled_limit = base_timeslot_limit * duration
            max_timeslots = min(len(timeslot_candidates), scaled_limit)
        
        # Para cursos virtuales, usamos -1 como índice de "sin aula"
        VIRTUAL_CLASSROOM_IDX = -1
        
        for prof_idx in prof_candidates[:max_profs]:
            for timeslot_idx in timeslot_candidates[:max_timeslots]:
                candidates.append((prof_idx, VIRTUAL_CLASSROOM_IDX, timeslot_idx))
        
        return candidates
    
    def _select_assignment(
        self,
        section_id: int,
        candidates: List[Tuple[int, int, int]],
        ant_id: int,
    ) -> Tuple[int, int, int]:
        """
        Selecciona una asignación usando la regla de transición ACO.
        
        Con probabilidad q0: elegir la mejor (explotación)
        Con probabilidad 1-q0: elegir probabilísticamente (exploración)
        """
        self._last_selection_log_prob = None

        # Obtener valores de feromona
        pheromones = np.array([
            self.pheromones.get(section_id, candidate)
            for candidate in candidates
        ], dtype=np.float32)

        sec_idx = self.graph_builder.section_id_to_idx[section_id]

        fallback_heuristics = np.array([
            1.0 / (1.0 + timeslot_idx * 0.01)
            for _, _, timeslot_idx in candidates
        ], dtype=np.float32)

        heuristics_np, heuristics_tensor = self._compute_candidate_heuristics(
            section_idx=sec_idx,
            candidates=candidates,
            fallback_heuristics=fallback_heuristics,
            requires_grad=self.collect_log_probs,
        )

        if self.collect_log_probs and heuristics_tensor is not None:
            device = heuristics_tensor.device
            pheromone_tensor = torch.tensor(pheromones, dtype=torch.float32, device=device)
            values = (pheromone_tensor ** self.alpha) * (heuristics_tensor ** self.beta)
            values = torch.clamp(values, min=1e-12)

            prob_sum = values.sum()
            if not torch.isfinite(prob_sum) or prob_sum.item() <= 0.0:
                probabilities = torch.ones_like(values) / max(1, values.numel())
            else:
                probabilities = values / prob_sum

            if random.random() < self.q0:
                selected_idx = int(torch.argmax(probabilities).item())
            else:
                selected_idx = int(torch.multinomial(probabilities, num_samples=1).item())

            self._last_selection_log_prob = torch.log(torch.clamp(probabilities[selected_idx], min=1e-12))
        else:
            values = (pheromones ** self.alpha) * (heuristics_np ** self.beta)

            if values.sum() == 0:
                values = np.ones_like(values)

            probabilities = values / values.sum()

            if random.random() < self.q0:
                selected_idx = np.argmax(probabilities)
            else:
                selected_idx = np.random.choice(len(candidates), p=probabilities)

        return candidates[selected_idx]

    def _compute_candidate_heuristics(
        self,
        section_idx: int,
        candidates: List[Tuple[int, int, int]],
        fallback_heuristics: np.ndarray,
        requires_grad: bool,
    ) -> Tuple[np.ndarray, Optional[torch.Tensor]]:
        """Calcula heurísticas por candidato usando GraphSAGE con fallback seguro."""
        if not self.use_graphsage_heuristic:
            return fallback_heuristics, None

        valid_positions = [index for index, (_, classroom_idx, _) in enumerate(candidates) if classroom_idx >= 0]
        if not valid_positions:
            return fallback_heuristics, None

        valid_candidates = [candidates[index] for index in valid_positions]

        if not requires_grad:
            try:
                self.model.eval()
                neural_values = self.model.get_heuristic_matrix(
                    self.graph,
                    section_idx,
                    valid_candidates,
                )
                merged = fallback_heuristics.copy()
                for local_pos, global_pos in enumerate(valid_positions):
                    merged[global_pos] = max(float(neural_values[local_pos]), 1e-8)
                return merged, None
            except Exception:
                return fallback_heuristics, None

        try:
            self.model.train()
            device = next(self.model.parameters()).device

            n_candidates = len(valid_candidates)
            section_batch = torch.full((n_candidates,), section_idx, dtype=torch.long, device=device)
            professor_batch = torch.tensor([candidate[0] for candidate in valid_candidates], dtype=torch.long, device=device)
            classroom_batch = torch.tensor([candidate[1] for candidate in valid_candidates], dtype=torch.long, device=device)
            timeslot_batch = torch.tensor([candidate[2] for candidate in valid_candidates], dtype=torch.long, device=device)

            scores = self.model.forward(
                self.graph,
                section_batch,
                professor_batch,
                classroom_batch,
                timeslot_batch,
            )
            neural_probs = torch.softmax(scores, dim=0)

            fallback_tensor = torch.tensor(
                np.clip(fallback_heuristics, 1e-8, None),
                dtype=torch.float32,
                device=device,
            )
            full_tensor = fallback_tensor.clone()
            valid_positions_tensor = torch.tensor(valid_positions, dtype=torch.long, device=device)
            full_tensor[valid_positions_tensor] = neural_probs

            return full_tensor.detach().cpu().numpy(), full_tensor
        except Exception:
            return fallback_heuristics, None

    def _get_consecutive_timeslots(self, day: int, start_order: int, duration: int) -> Optional[List[int]]:
        """Obtiene una secuencia de bloques consecutivos para una sección."""
        timeslot_ids = []
        for offset in range(duration):
            ts_id = self._timeslot_lookup.get((day, start_order + offset))
            if ts_id is None:
                return None
            timeslot_ids.append(ts_id)
        return timeslot_ids
    
    def _build_assignment_object(
        self,
        section_id: int,
        prof_idx: int,
        classroom_idx: int,
        timeslot_start_idx: int,
        precomputed_timeslots: Optional[List[int]] = None,
    ) -> Assignment:
        """
        Construye un objeto Assignment completo desde índices.
        
        Incluye la búsqueda de bloques consecutivos según duración.
        """
        # Mapear índices a IDs reales
        professor_id = self.graph_builder.idx_to_professor_id[prof_idx]
        
        # Manejo especial para cursos virtuales (classroom_idx == -1)
        if classroom_idx == -1:
            classroom_id = None  # Sin aula física para cursos virtuales
        else:
            classroom_id = self.graph_builder.idx_to_classroom_id[classroom_idx]
        
        timeslot_start_id = self.graph_builder.idx_to_timeslot_id[timeslot_start_idx]
        
        # Obtener duración
        duracion = self.graph_builder.section_durations.get(section_id, 1)
        
        # Buscar bloques consecutivos
        start_ts = self.hard_validator.timeslots[timeslot_start_id]
        if precomputed_timeslots is not None:
            timeslot_ids = list(precomputed_timeslots)
        else:
            timeslot_sequence = self._get_consecutive_timeslots(
                start_ts.dia_semana,
                start_ts.orden,
                duracion,
            )
            timeslot_ids = timeslot_sequence or [timeslot_start_id]
        
        # Obtener información adicional desde el graph builder
        metadata = self.graph_builder.section_metadata.get(section_id, {})
        course_code = metadata.get("course_code") or f"SECTION-{section_id}"
        session_type = (metadata.get("session_type") or "T").upper()
        league_id = metadata.get("league") or 1
        ciclo = metadata.get("ciclo") or "SIN-CICLO"
        alumnos_proyectados = self.graph_builder.section_projected_students.get(section_id, 0)
        original_section_id = metadata.get("original_section_id", section_id)
        split_group_index = metadata.get("split_group_index", 0)
        split_group_count = metadata.get("split_group_count", 1)
        block_id = metadata.get("block_id")
        franja_index = metadata.get("franja_index")
        
        return Assignment(
            section_id=section_id,
            professor_id=professor_id,
            classroom_id=classroom_id,
            timeslot_ids=timeslot_ids,
            course_code=course_code,
            session_type=session_type,
            league_id=league_id,
            ciclo=ciclo,
            alumnos_proyectados=alumnos_proyectados,
            original_section_id=original_section_id,
            split_group_index=split_group_index,
            split_group_count=split_group_count,
            block_id=block_id,
            franja_index=franja_index,
        )
    
    def _update_pheromones(self, solution: Solution, weight: float = 1.0):
        """
        Actualiza las feromonas basándose en una solución.
        
        Deposita más feromona en asignaciones de soluciones mejores.
        """
        if not solution.is_valid:
            return
        
        # Calcular cantidad de feromona a depositar (inverso del costo)
        delta_tau = weight / (1.0 + solution.total_cost)
        
        for assignment in solution.assignments:
            # Convertir a índices
            prof_idx = self.graph_builder.professor_id_to_idx[assignment.professor_id]
            
            # Manejo especial para cursos virtuales sin aula
            if assignment.classroom_id is None:
                classroom_idx = -1  # Usar -1 como índice especial
            else:
                classroom_idx = self.graph_builder.classroom_id_to_idx[assignment.classroom_id]
            
            timeslot_idx = self.graph_builder.timeslot_id_to_idx[assignment.timeslot_ids[0]]
            
            key = (prof_idx, classroom_idx, timeslot_idx)
            
            current = self.pheromones.get(assignment.section_id, key)
            new_value = current + delta_tau
            self.pheromones.set(assignment.section_id, key, new_value)

    def _greedy_repair(self, partial_solution: Solution) -> Solution:
        """
        Fase de reparación greedy para asegurar asignación del 100%.
        Toma una solución parcial y fuerza la asignación de las secciones faltantes.
        """
        assignments = list(partial_solution.assignments)
        assigned_section_ids = {a.section_id for a in assignments}
        all_section_ids = list(self.graph_builder.section_id_to_idx.keys())
        missing_sections = [sec_id for sec_id in all_section_ids if sec_id not in assigned_section_ids]
        
        if not missing_sections:
            return partial_solution
            
        construction_log = list(partial_solution.construction_log)
        construction_log.append(f"\n[GREEDY REPAIR] Iniciando reparación para {len(missing_sections)} secciones.")
        
        repaired_count = 0
        for sec_id in missing_sections:
            candidates = self._get_candidate_assignments(sec_id, is_critical=True)
            # Mezclar candidatos para exploración
            import random
            candidates_list = list(candidates)
            random.shuffle(candidates_list)
            
            assigned = False
            for prof_idx, classroom_idx, timeslot_idx in candidates_list:
                assignment = self._build_assignment_object(
                    sec_id, prof_idx, classroom_idx, timeslot_idx
                )
                
                is_valid, _ = self.hard_validator.validate_all(assignment, assignments)
                if is_valid:
                    assignments.append(assignment)
                    repaired_count += 1
                    assigned = True
                    construction_log.append(f"[GREEDY] Reparada sección {sec_id}")
                    break
                    
            if not assigned:
                construction_log.append(f"[GREEDY ERROR] No se pudo reparar sección {sec_id} sin violar restricciones duras.")
                
        total_cost, penalties = self.soft_evaluator.calculate_total_penalty(assignments)
        
        coverage = len(assignments) / len(all_section_ids) if all_section_ids else 0.0
        coverage_threshold = float(self.params.get("coverage_threshold", 0.90))
        is_valid_final = coverage >= coverage_threshold
        
        if not is_valid_final:
             total_cost += 1000.0 * (len(all_section_ids) - len(assignments))
             
        construction_log.append(f"[GREEDY REPAIR] Finalizado. Reparadas: {repaired_count}/{len(missing_sections)}.")
        
        return Solution(
            assignments=assignments,
            total_cost=total_cost,
            soft_penalties=penalties,
            is_valid=is_valid_final,
            construction_log=construction_log,
        )


# ============================================================================
# UTILIDADES
# ============================================================================

def create_aco_engine(
    graph: HeteroData,
    model: ACOGraphSAGEModel,
    graph_builder,
    db_session,
    params: Dict = None,
) -> ACOEngine:
    """
    Factory function para crear un ACOEngine configurado.
    
    Args:
        graph: Grafo heterogéneo
        model: Modelo GraphSAGE entrenado
        graph_builder: Instancia de TimetableGraphBuilder
        db_session: Sesión de base de datos para cargar restricciones
        params: Parámetros ACO (opcional)
    
    Returns:
        ACOEngine configurado y listo para optimizar
    """
    from app.models import TimeSlot, Classroom, ProfessorRestriction

    def _parse_time(value) -> Optional[time_cls]:
        if value is None:
            return None
        if isinstance(value, time_cls):
            return value
        if isinstance(value, str):
            try:
                return datetime.strptime(value, "%H:%M").time()
            except ValueError:
                return None
        if hasattr(value, "total_seconds"):
            total_seconds = int(value.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes = (remainder // 60) % 60
            hours = hours % 24
            return time_cls(hour=hours, minute=minutes)
        if hasattr(value, "hour") and hasattr(value, "minute"):
            return time_cls(hour=int(value.hour) % 24, minute=int(value.minute) % 60)
        return None
    
    # Cargar información de BD
    timeslots_db = db_session.query(TimeSlot).all()
    classrooms_db = db_session.query(Classroom).all()
    restrictions_db = db_session.query(ProfessorRestriction).all()
    
    # Convertir a estructuras de constraints.py
    timeslots = {
        ts.id: TimeSlotInfo(
            id=ts.id,
            dia_semana=ts.dia_semana,
            hora_inicio=_parse_time(ts.hora_inicio),
            hora_fin=_parse_time(ts.hora_fin),
            orden=ts.orden,
            periodo=ts.periodo,
        )
        for ts in timeslots_db
    }
    
    classrooms = {
        c.id: ClassroomInfo(
            id=c.id,
            codigo=c.codigo,
            capacidad=c.capacidad,
            tipo=graph_builder._normalize_classroom_type(c.tipo),
            edificio=c.edificio,
            tiene_computadoras=c.tiene_computadoras,
        )
        for c in classrooms_db
    }
    
    professor_restrictions = defaultdict(list)
    for r in restrictions_db:
        day_num = graph_builder._normalize_day_of_week(r.day)
        if day_num == 0:
            continue
        start_time = _parse_time(r.start_time)
        end_time = _parse_time(r.end_time)
        if start_time is None or end_time is None:
            continue
        professor_restrictions[r.professor_id].append(
            ProfessorRestrictionInfo(
                professor_id=r.professor_id,
                dia_semana=day_num,
                hora_inicio=start_time,
                hora_fin=end_time,
                es_baja_prioridad=bool(getattr(r, "es_baja_prioridad", False)),
            )
        )
    
    # Crear validadores
    hard_validator = HardConstraintValidator(
        timeslots=timeslots,
        classrooms=classrooms,
        professor_restrictions=dict(professor_restrictions),
        sections_by_league=graph_builder.sections_by_league,
        league_session_types=graph_builder.league_session_types,
        section_session_types=graph_builder.section_session_types,
        sections_by_block=graph_builder.sections_by_block,
        section_modalities=graph_builder.section_modalities,
    )
    
    soft_evaluator = SoftConstraintEvaluator(
        timeslots=timeslots,
        classrooms=classrooms,
        professor_restrictions=dict(professor_restrictions),
    )
    
    # Crear engine
    engine = ACOEngine(
        graph=graph,
        model=model,
        graph_builder=graph_builder,
        hard_validator=hard_validator,
        soft_evaluator=soft_evaluator,
        params=params,
    )
    
    return engine
