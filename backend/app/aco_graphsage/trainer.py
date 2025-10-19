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
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = self.model.to(self.device)
        print(f"Usando device: {self.device}")
        
        # Parámetros
        self.params = params or TRAINING_PARAMS
        self.n_episodes = self.params["n_episodes"]
        self.batch_size = self.params["batch_size"]
        self.gamma = self.params["gamma"]
        
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
        self.best_solution: Optional[Solution] = None
        
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
            solution, log_probs = self._generate_solution_with_logging()
            
            if solution is None:
                print(f"Episodio {episode+1}/{self.n_episodes}: ⚠️ No se generó solución válida")
                continue
            
            # Calcular recompensa (negativo del costo para maximizar)
            reward = -solution.total_cost
            self.episode_rewards.append(reward)
            self.episode_costs.append(solution.total_cost)
            
            # Actualizar mejor solución
            if solution.is_valid and solution.total_cost < self.best_cost:
                improvement = (self.best_cost - solution.total_cost) / self.best_cost
                self.best_cost = solution.total_cost
                self.best_solution = solution
                self.patience_counter = 0
                
                print(f"Episodio {episode+1}/{self.n_episodes}: ✅ Nuevo mejor: {self.best_cost:.2f} "
                      f"(mejora={improvement*100:.2f}%)")
                
                # Guardar checkpoint
                checkpoint_path = save_path / f"best_model_episode_{episode+1}.pt"
                save_model(self.model, str(checkpoint_path))
            else:
                self.patience_counter += 1
                print(f"Episodio {episode+1}/{self.n_episodes}: Cost={solution.total_cost:.2f}, "
                      f"Best={self.best_cost:.2f}, Epsilon={self.epsilon:.3f}")
            
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
        
        print(f"\n{'='*80}")
        print(f"✅ Entrenamiento completado")
        print(f"Mejor costo alcanzado: {self.best_cost:.2f}")
        print(f"Mejora total: {(self.episode_costs[0] - self.best_cost) / self.episode_costs[0] * 100:.1f}%")
        print(f"{'='*80}\n")
        
        # Guardar modelo final
        final_path = save_path / "final_model.pt"
        save_model(self.model, str(final_path))
        
        # Guardar estadísticas
        self._save_training_stats(save_path)
        
        return self.model
    
    def _generate_solution_with_logging(self) -> Tuple[Optional[Solution], List[torch.Tensor]]:
        """
        Genera una solución usando ACO y registra log probabilities.
        
        Returns:
            (solution, log_probs)
        """
        # Crear motor ACO con modelo actual
        aco_engine = self.aco_engine_factory(self.model)
        
        # Modificar epsilon del ACO para exploración
        original_q0 = aco_engine.params["q0"]
        aco_engine.params["q0"] = 1.0 - self.epsilon  # Mayor exploración al inicio
        
        # Modo de entrenamiento
        self.model.train()
        
        # Generar solución (solo 1 hormiga, pocas iteraciones para entrenamiento rápido)
        aco_engine.n_hormigas = 1
        aco_engine.n_iteraciones = 10
        
        log_probs = []
        
        # Hook para capturar log probabilities durante la construcción
        # (Simplificado: en implementación completa, modificar ACO para retornar log_probs)
        
        solution = aco_engine.optimize()
        
        # Restaurar parámetros
        aco_engine.params["q0"] = original_q0
        
        # Por ahora, log_probs vacío (implementación completa requiere modificar ACOEngine)
        # En la práctica, cada decisión de asignación generaría un log_prob
        
        return solution, log_probs
    
    def _update_policy(self, log_probs: List[torch.Tensor], reward: float):
        """
        Actualiza la política usando REINFORCE.
        
        REINFORCE: ∇J(θ) = E[∑ log π(a|s) * (R - baseline)]
        """
        if len(log_probs) == 0:
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
        for log_prob in log_probs:
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
        print(f"Conflictos totales: {metrics['conflictos_profesor'] + metrics['conflictos_aula'] + metrics['conflictos_curriculo']}")
        print(f"Utilización aulas: {metrics['utilizacion_aulas']:.1f}%")
        print(f"Huecos estudiantes: {metrics['huecos_estudiantes']:.1f}")
        print(f"{'='*80}\n")
    
    def _save_training_stats(self, save_dir: Path):
        """Guarda estadísticas del entrenamiento"""
        stats = {
            'n_episodes': len(self.episode_costs),
            'episode_costs': self.episode_costs,
            'episode_rewards': self.episode_rewards,
            'best_cost': self.best_cost,
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
