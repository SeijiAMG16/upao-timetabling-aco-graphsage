"""
Entrenador con Reinforcement Learning (REINFORCE)

Implementa el pipeline de entrenamiento para GraphSAGE usando
Policy Gradient (REINFORCE algorithm).

El modelo aprende a predecir mejores heurísticas maximizando la
recompensa (minimizando el costo de las soluciones generadas).
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch_geometric.data import HeteroData
from typing import List, Dict, Tuple, Optional
import numpy as np
from pathlib import Path
import json
import gc
from datetime import datetime

from .config import TRAINING_PARAMS, GRAPHSAGE_PARAMS
from .graphsage_model import ACOGraphSAGEModel, save_model
from .aco_engine import ACOEngine, Solution
from .evaluator import SolutionEvaluator
from .constraints import Assignment


# ============================================================================
# ENTRENADOR REINFORCE
# ============================================================================

class REINFORCETrainer:
    """Entrenador de GraphSAGE con algoritmo REINFORCE"""
    
    def __init__(
        self,
        model: ACOGraphSAGEModel,
        graph: HeteroData,
        aco_engine_factory,  # Función que crea ACOEngine
        evaluator: SolutionEvaluator,
        params: Dict = None,
        device: str = None,
    ):
        self.model = model
        self.graph = graph
        self.aco_engine_factory = aco_engine_factory
        self.evaluator = evaluator
        
        # Device
        self.device = device or 'cpu'
        self.model = self.model.to(self.device)
        print(f"Usando device: {self.device}")
        
        # Parámetros
        self.params = params or TRAINING_PARAMS
        self.n_episodes = self.params["n_episodes"]
        self.batch_size = self.params["batch_size"]
        self.gamma = self.params["gamma"]

        # Gestión de recursos CPU
        self.resource_mode = str(self.params.get("resource_mode", "balanced")).lower()
        requested_threads = int(self.params.get("torch_num_threads", 2))
        if requested_threads > 0:
            torch.set_num_threads(requested_threads)
        
        # Optimizador
        self.optimizer = optim.Adam(
            self.model.parameters(),
            lr=GRAPHSAGE_PARAMS["learning_rate"],
            weight_decay=GRAPHSAGE_PARAMS["weight_decay"],
        )
        
        # Baseline para reducir varianza
        self.use_baseline = self.params["use_baseline"]
        self.baseline_value = 0.0
        self.baseline_decay = self.params["baseline_decay"]
        
        # Exploración
        self.epsilon = self.params["epsilon_start"]
        self.epsilon_end = self.params["epsilon_end"]
        self.epsilon_decay = self.params["epsilon_decay"]
        
        # Estadísticas
        self.episode_rewards: List[float] = []
        self.episode_costs: List[float] = []
        self.episode_coverages: List[float] = []
        self.episode_hard_violations: List[int] = []
        self.episode_missing_sections: List[int] = []
        self.episode_training_objective: List[float] = []
        self.episode_strict_feasible: List[bool] = []
        self.best_solution: Optional[Solution] = None
        self.best_metrics: Optional[Dict] = None
        self.best_signature: Tuple[float, float, float] = (float('inf'), float('inf'), float('inf'))
        
        # Early stopping
        self.best_cost = float('inf')
        self.patience_counter = 0
        self.patience = self.params["patience"]
        self.min_improvement = self.params["min_improvement"]
    
    def train(self, save_dir: str = "models/checkpoints") -> ACOGraphSAGEModel:
        """
        Ejecuta el entrenamiento completo.
        
        Args:
            save_dir: Directorio donde guardar checkpoints
        
        Returns:
            Modelo entrenado
        """
        save_path = Path(save_dir)
        save_path.mkdir(parents=True, exist_ok=True)
        
        print(f"\n{'='*80}")
        print(f"Iniciando entrenamiento REINFORCE")
        print(f"Episodes: {self.n_episodes}, Batch size: {self.batch_size}")
        print(f"Epsilon: {self.epsilon} -> {self.epsilon_end} (decay={self.epsilon_decay})")
        print(f"Device: {self.device}")
        print(f"{'='*80}\n")
        
        for episode in range(self.n_episodes):
            # Generar solución usando ACO con modelo actual
            solution, log_probs, metrics = self._generate_solution_with_logging(episode)
            
            if solution is None:
                print(f"Episodio {episode+1}/{self.n_episodes}: ⚠️ No se generó solución válida")
                # Liberar memoria aunque no haya solución
                gc.collect()
                continue
            
            # Calcular recompensa curricular (hard + cobertura primero, blandas con bajo peso)
            reward = -metrics["training_objective"]
            self.episode_rewards.append(reward)
            self.episode_costs.append(solution.total_cost)
            self.episode_coverages.append(metrics["coverage"])
            self.episode_hard_violations.append(metrics["hard_violations"])
            self.episode_missing_sections.append(metrics["missing_sections"])
            self.episode_training_objective.append(metrics["training_objective"])
            self.episode_strict_feasible.append(metrics["strict_feasible"])
            
            # Actualizar mejor solución (orden lexicográfico: hard -> cobertura -> objetivo)
            candidate_signature = (
                float(metrics["hard_violations"]),
                float(metrics["missing_sections"]),
                float(metrics["training_objective"]),
            )
            if candidate_signature < self.best_signature:
                previous_objective = self.best_signature[2]
                if np.isfinite(previous_objective) and previous_objective != 0:
                    improvement = (previous_objective - metrics["training_objective"]) / previous_objective
                else:
                    improvement = 0.0

                self.best_signature = candidate_signature
                self.best_cost = metrics["training_objective"]
                self.best_solution = solution
                self.best_metrics = metrics
                self.patience_counter = 0
                
                print(
                    f"Episodio {episode+1}/{self.n_episodes}: ✅ Nuevo mejor | "
                    f"hard={metrics['hard_violations']} cov={metrics['coverage']*100:.1f}% "
                    f"obj={metrics['training_objective']:.2f} (mejora={improvement*100:.2f}%)"
                )
                
                # Guardar checkpoint
                checkpoint_path = save_path / f"best_model_episode_{episode+1}.pt"
                save_model(self.model, str(checkpoint_path))
            else:
                self.patience_counter += 1
                print(
                    f"Episodio {episode+1}/{self.n_episodes}: "
                    f"hard={metrics['hard_violations']} cov={metrics['coverage']*100:.1f}% "
                    f"obj={metrics['training_objective']:.2f}, best={self.best_cost:.2f}, "
                    f"eps={self.epsilon:.3f}"
                )
            
            # Actualizar modelo con REINFORCE
            if len(log_probs) > 0:
                self._update_policy(log_probs, reward)
            
            # Decay epsilon
            self.epsilon = max(self.epsilon_end, self.epsilon * self.epsilon_decay)
            
            # Evaluación periódica
            if (episode + 1) % self.params["eval_every"] == 0:
                self._evaluate_and_log(episode + 1)
            
            # Guardar checkpoint periódico
            if (episode + 1) % self.params["save_every"] == 0:
                checkpoint_path = save_path / f"model_episode_{episode+1}.pt"
                save_model(self.model, str(checkpoint_path))
            
            # Early stopping
            if self.patience_counter >= self.patience:
                print(f"\n⏹️ Early stopping: {self.patience} episodios sin mejora significativa")
                break

            # --- Liberar memoria al final de cada episodio ---
            del log_probs
            if solution is not None:
                del solution
            gc.collect()
        
        print(f"\n{'='*80}")
        print(f"✅ Entrenamiento completado")
        if self.best_metrics is not None:
            print(
                f"Mejor episodio -> hard={self.best_metrics['hard_violations']}, "
                f"cobertura={self.best_metrics['coverage']*100:.1f}%, "
                f"objetivo={self.best_metrics['training_objective']:.2f}"
            )
        else:
            print("Mejor episodio: N/A")
        print(f"{'='*80}\n")
        
        # Guardar modelo final
        final_path = save_path / "final_model.pt"
        save_model(self.model, str(final_path))
        
        # Guardar estadísticas
        self._save_training_stats(save_path)
        
        return self.model
    
    def _generate_solution_with_logging(self, episode: int) -> Tuple[Optional[Solution], List[torch.Tensor], Dict]:
        """
        Genera una solución usando ACO y registra log probabilities.
        
        Returns:
            (solution, log_probs)
        """
        # Crear motor ACO con modelo actual
        aco_engine = self.aco_engine_factory(self.model)
        aco_engine.collect_log_probs = True
        aco_engine.use_graphsage_heuristic = True
        aco_engine.params["collect_log_probs"] = True
        aco_engine.params["use_graphsage_heuristic"] = True
        aco_engine.params["allow_partial_solutions"] = True

        curriculum_ratio = self._episode_progress_ratio(episode)

        # Overrides de exploración para entrenamiento (mayor cobertura)
        resource_profile = self._get_resource_profile(curriculum_ratio)
        train_overrides = {
            "max_candidate_combinations": resource_profile["max_candidate_combinations"],
            "max_professors_per_section": resource_profile["max_professors_per_section"],
            "max_classrooms_per_section": resource_profile["max_classrooms_per_section"],
            "max_timeslots_per_section": resource_profile["max_timeslots_per_section"],
            "pedagogical_relaxation_attempts": resource_profile["pedagogical_relaxation_attempts"],
            "pedagogical_relaxation_rank_step": resource_profile["pedagogical_relaxation_rank_step"],
        }
        for key, value in train_overrides.items():
            if value is not None:
                aco_engine.params[key] = value

        # Sincronizar atributos cacheados del engine
        aco_engine.pedagogical_relaxation_attempts = int(
            aco_engine.params.get("pedagogical_relaxation_attempts", aco_engine.pedagogical_relaxation_attempts)
        )
        aco_engine.pedagogical_relaxation_rank_step = int(
            aco_engine.params.get("pedagogical_relaxation_rank_step", aco_engine.pedagogical_relaxation_rank_step)
        )

        coverage_target = self._interpolate_param(
            "coverage_target_start",
            "coverage_target_end",
            curriculum_ratio,
        )
        aco_engine.params["coverage_threshold"] = coverage_target
        
        # Modificar epsilon del ACO para exploración
        original_q0 = aco_engine.q0
        aco_engine.q0 = 1.0 - self.epsilon  # Mayor exploración al inicio
        aco_engine.params["q0"] = aco_engine.q0
        
        # Modo de entrenamiento
        self.model.train()
        
        # Generar solución (rollout progresivo: rápido al inicio, más fuerte al final)
        ants_start = float(resource_profile["train_aco_ants"])
        ants_end = float(resource_profile["train_aco_ants_end"])
        iter_start = float(resource_profile["train_aco_iterations"])
        iter_end = float(resource_profile["train_aco_iterations_end"])

        aco_engine.n_hormigas = max(1, int(round(ants_start + (ants_end - ants_start) * curriculum_ratio)))
        aco_engine.n_iteraciones = max(1, int(round(iter_start + (iter_end - iter_start) * curriculum_ratio)))
        
        solution = aco_engine.optimize()
        log_probs = list(getattr(aco_engine, "last_solution_log_probs", []))

        metrics = self._compute_episode_metrics(solution, aco_engine, curriculum_ratio)
        
        # Restaurar parámetros
        aco_engine.q0 = original_q0
        aco_engine.params["q0"] = original_q0
        
        return solution, log_probs, metrics

    def _get_resource_profile(self, curriculum_ratio: float) -> Dict[str, float]:
        """Devuelve parámetros de entrenamiento según perfil de recursos."""
        base_profile = {
            "train_aco_ants": int(self.params.get("train_aco_ants", 1)),
            "train_aco_ants_end": int(self.params.get("train_aco_ants_end", self.params.get("train_aco_ants", 1))),
            "train_aco_iterations": int(self.params.get("train_aco_iterations", 3)),
            "train_aco_iterations_end": int(self.params.get("train_aco_iterations_end", self.params.get("train_aco_iterations", 3))),
            "max_candidate_combinations": int(self.params.get("train_max_candidate_combinations", 1800)),
            "max_professors_per_section": int(self.params.get("train_max_professors_per_section", 8)),
            "max_classrooms_per_section": int(self.params.get("train_max_classrooms_per_section", 16)),
            "max_timeslots_per_section": int(self.params.get("train_max_timeslots_per_section", 16)),
            "pedagogical_relaxation_attempts": int(self.params.get("train_pedagogical_relaxation_attempts", 6)),
            "pedagogical_relaxation_rank_step": int(self.params.get("train_pedagogical_relaxation_rank_step", 50)),
        }

        if self.resource_mode == "aggressive":
            return base_profile

        if self.resource_mode == "safe_lite":
            # ✅ Perfil para laptops con RAM limitada (<8GB libre)
            # Candidatos muy reducidos: evita saturar RAM en run largos
            return {
                "train_aco_ants": 1,
                "train_aco_ants_end": 2,
                "train_aco_iterations": 1,
                "train_aco_iterations_end": 3,
                "max_candidate_combinations": 400,
                "max_professors_per_section": 5,
                "max_classrooms_per_section": 5,
                "max_timeslots_per_section": 8,
                "pedagogical_relaxation_attempts": 3,
                "pedagogical_relaxation_rank_step": 70,
            }

        if self.resource_mode == "lite":
            return {
                "train_aco_ants": min(base_profile["train_aco_ants"], 1),
                "train_aco_ants_end": min(base_profile["train_aco_ants_end"], 2),
                "train_aco_iterations": min(base_profile["train_aco_iterations"], 2),
                "train_aco_iterations_end": min(base_profile["train_aco_iterations_end"], 4),
                "max_candidate_combinations": min(base_profile["max_candidate_combinations"], 1200),
                "max_professors_per_section": min(base_profile["max_professors_per_section"], 8),
                "max_classrooms_per_section": min(base_profile["max_classrooms_per_section"], 12),
                "max_timeslots_per_section": min(base_profile["max_timeslots_per_section"], 12),
                "pedagogical_relaxation_attempts": min(base_profile["pedagogical_relaxation_attempts"], 4),
                "pedagogical_relaxation_rank_step": max(base_profile["pedagogical_relaxation_rank_step"], 60),
            }

        # balanced
        balanced = base_profile.copy()
        balanced["train_aco_ants_end"] = max(2, min(base_profile["train_aco_ants_end"], 3))
        balanced["train_aco_iterations_end"] = max(4, min(base_profile["train_aco_iterations_end"], 7))
        return balanced

    def _episode_progress_ratio(self, episode: int) -> float:
        if self.n_episodes <= 1:
            return 1.0
        return min(1.0, max(0.0, episode / float(self.n_episodes - 1)))

    def _interpolate_param(self, start_key: str, end_key: str, ratio: float) -> float:
        start_val = float(self.params[start_key])
        end_val = float(self.params[end_key])
        return start_val + (end_val - start_val) * ratio

    def _compute_episode_metrics(self, solution: Optional[Solution], aco_engine: ACOEngine, ratio: float) -> Dict:
        if solution is None:
            return {
                "hard_violations": int(10**6),
                "coverage": 0.0,
                "missing_sections": int(10**6),
                "training_objective": float(10**12),
                "strict_feasible": False,
            }

        total_sections = max(1, int(self.graph["section"].x.shape[0]))
        assigned_sections = int(len(solution.assignments))
        coverage = assigned_sections / total_sections
        missing_sections = max(0, total_sections - assigned_sections)

        hard_ok, hard_violations_detail = aco_engine.hard_validator.validate_schedule(solution.assignments)
        hard_violations = 0 if hard_ok else len(hard_violations_detail)

        missing_penalty = self._interpolate_param(
            "missing_section_penalty_start",
            "missing_section_penalty_end",
            ratio,
        )
        soft_cost_weight = float(self.params.get("soft_cost_weight", 0.05))
        hard_penalty = float(self.params.get("hard_violation_penalty", 1_000_000.0))

        objective = (
            soft_cost_weight * float(solution.total_cost)
            + missing_penalty * float(missing_sections)
            + hard_penalty * float(hard_violations)
        )

        strict_phase_start = float(self.params.get("strict_phase_start", 0.70))
        target_coverage_end = float(self.params.get("coverage_target_end", 0.95))
        strict_feasible = (hard_violations == 0) and (coverage >= target_coverage_end)

        if ratio >= strict_phase_start and not strict_feasible:
            objective += float(self.params.get("strict_infeasible_penalty", 5_000_000.0))

        return {
            "hard_violations": int(hard_violations),
            "coverage": float(coverage),
            "missing_sections": int(missing_sections),
            "training_objective": float(objective),
            "strict_feasible": bool(strict_feasible),
        }
    
    def _update_policy(self, log_probs: List[torch.Tensor], reward: float):
        """
        Actualiza la política usando REINFORCE.
        
        REINFORCE: ∇J(θ) = E[∑ log π(a|s) * (R - baseline)]
        """
        trainable_log_probs = [
            log_prob
            for log_prob in log_probs
            if log_prob is not None and getattr(log_prob, "requires_grad", False)
        ]

        if len(trainable_log_probs) == 0:
            return
        
        # Calcular retorno descontado
        discounted_reward = reward
        
        # Aplicar baseline para reducir varianza
        if self.use_baseline:
            advantage = discounted_reward - self.baseline_value
            # Actualizar baseline con decaimiento exponencial
            self.baseline_value = (
                self.baseline_decay * self.baseline_value +
                (1 - self.baseline_decay) * discounted_reward
            )
        else:
            advantage = discounted_reward
        
        # Calcular pérdida
        policy_loss = []
        for log_prob in trainable_log_probs:
            policy_loss.append(-log_prob * advantage)
        
        policy_loss = torch.stack(policy_loss).sum()
        
        # Backward pass
        self.optimizer.zero_grad()
        policy_loss.backward()
        
        # Clip gradientes para estabilidad
        torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
        
        self.optimizer.step()
    
    def _evaluate_and_log(self, episode: int):
        """Evalúa el modelo y registra métricas"""
        if self.best_solution is None:
            return
        
        metrics = self.evaluator.evaluate(self.best_solution)
        
        print(f"\n{'='*80}")
        print(f"EVALUACIÓN - Episodio {episode}")
        print(f"{'='*80}")
        print(f"Mejor costo: {self.best_cost:.2f}")
        conflictos = (
            metrics.get('conflictos_profesor', 0)
            + metrics.get('conflictos_aula', 0)
            + metrics.get('conflictos_curriculo', 0)
        )
        print(f"Conflictos totales: {conflictos}")
        print(f"Utilización aulas: {metrics.get('utilizacion_aulas', 0.0):.1f}%")
        print(f"Huecos estudiantes: {metrics.get('huecos_estudiantes', 0.0):.1f}")
        print(f"{'='*80}\n")
    
    def _save_training_stats(self, save_dir: Path):
        """Guarda estadísticas del entrenamiento"""
        stats = {
            'n_episodes': len(self.episode_costs),
            'episode_costs': self.episode_costs,
            'episode_rewards': self.episode_rewards,
            'episode_coverages': self.episode_coverages,
            'episode_hard_violations': self.episode_hard_violations,
            'episode_missing_sections': self.episode_missing_sections,
            'episode_training_objective': self.episode_training_objective,
            'episode_strict_feasible': self.episode_strict_feasible,
            'best_objective': self.best_cost if np.isfinite(self.best_cost) else None,
            'best_signature': list(self.best_signature),
            'best_metrics': self.best_metrics,
            'final_epsilon': self.epsilon,
            'training_params': self.params,
            'timestamp': datetime.now().isoformat(),
        }
        
        stats_path = save_dir / "training_stats.json"
        with open(stats_path, 'w') as f:
            json.dump(stats, f, indent=2)
        
        print(f"📊 Estadísticas guardadas en: {stats_path}")


# ============================================================================
# ENTRENADOR SUPERVISADO (ALTERNATIVA)
# ============================================================================

class SupervisedTrainer:
    """
    Entrenador supervisado usando horarios históricos.
    
    Alternativa a REINFORCE: aprende de soluciones conocidas.
    """
    
    def __init__(
        self,
        model: ACOGraphSAGEModel,
        graph: HeteroData,
        device: str = None,
    ):
        self.model = model
        self.graph = graph
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = self.model.to(self.device)
        
        self.optimizer = optim.Adam(
            self.model.parameters(),
            lr=GRAPHSAGE_PARAMS["learning_rate"],
        )
        
        self.criterion = nn.MSELoss()
    
    def train_from_historical_data(
        self,
        historical_solutions: List[Tuple[Assignment, float]],  # (assignment, quality_score)
        n_epochs: int = 100,
    ):
        """
        Entrena el modelo usando horarios históricos.
        
        Args:
            historical_solutions: Lista de (asignación, score de calidad)
            n_epochs: Número de épocas
        """
        print(f"\n{'='*80}")
        print(f"Entrenamiento supervisado con {len(historical_solutions)} ejemplos")
        print(f"{'='*80}\n")
        
        for epoch in range(n_epochs):
            total_loss = 0.0
            self.model.train()
            
            # Mezclar datos
            import random
            random.shuffle(historical_solutions)
            
            for assignment, target_score in historical_solutions:
                # Convertir a tensores
                sec_idx = torch.tensor([0], dtype=torch.long)  # Simplificado
                prof_idx = torch.tensor([0], dtype=torch.long)
                classroom_idx = torch.tensor([0], dtype=torch.long)
                timeslot_idx = torch.tensor([0], dtype=torch.long)
                
                # Forward
                predicted_score = self.model(
                    self.graph,
                    sec_idx,
                    prof_idx,
                    classroom_idx,
                    timeslot_idx,
                )
                
                target = torch.tensor([target_score], dtype=torch.float32)
                
                # Loss
                loss = self.criterion(predicted_score, target)
                
                # Backward
                self.optimizer.zero_grad()
                loss.backward()
                self.optimizer.step()
                
                total_loss += loss.item()
            
            avg_loss = total_loss / len(historical_solutions)
            
            if (epoch + 1) % 10 == 0:
                print(f"Época {epoch+1}/{n_epochs}: Loss={avg_loss:.4f}")
        
        print(f"\n✅ Entrenamiento supervisado completado\n")


# ============================================================================
# FACTORY
# ============================================================================

def create_trainer(
    model: ACOGraphSAGEModel,
    graph: HeteroData,
    aco_engine_factory,
    evaluator: SolutionEvaluator,
    mode: str = "reinforcement",
    params: Dict = None,
) -> REINFORCETrainer:
    """
    Crea un entrenador.
    
    Args:
        model: Modelo GraphSAGE
        graph: Grafo heterogéneo
        aco_engine_factory: Función que crea ACOEngine
        evaluator: Evaluador de métricas
        mode: 'reinforcement' o 'supervised'
        params: Parámetros de entrenamiento
    
    Returns:
        Instancia del entrenador
    """
    if mode == "reinforcement":
        return REINFORCETrainer(
            model=model,
            graph=graph,
            aco_engine_factory=aco_engine_factory,
            evaluator=evaluator,
            params=params,
        )
    elif mode == "supervised":
        return SupervisedTrainer(model=model, graph=graph)
    else:
        raise ValueError(f"Modo desconocido: {mode}")
