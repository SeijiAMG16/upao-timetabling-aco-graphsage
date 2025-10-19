"""
ACO+GraphSAGE Pipeline para Generación Automática de Horarios Académicos UPAO

Este módulo implementa el framework híbrido basado en:
- Ant Colony Optimization (ACO) con Max-Min Ant System (MMAS)
- GraphSAGE como heurística aprendida Φ(G,i,j)
- Reinforcement Learning (REINFORCE) para entrenamiento offline

Arquitectura:
1. graph_builder: Construcción de grafo heterogéneo
2. graphsage_model: Red neuronal GNN para heurística
3. aco_engine: Motor ACO con integración neural
4. constraints: Validadores de restricciones duras/blandas
5. local_search: Refinamiento de soluciones
6. trainer: Pipeline de entrenamiento RL
7. evaluator: Métricas de calidad
8. pipeline: Orquestador principal
9. config: Parámetros del sistema

Referencias:
- DeepACO: https://arxiv.org/abs/2309.14032
- Neural Combinatorial Optimization
"""

from .config import (
    ACO_PARAMS,
    GRAPHSAGE_PARAMS,
    CONSTRAINT_WEIGHTS,
    TRAINING_PARAMS,
    LOCAL_SEARCH_PARAMS,
)
from .pipeline import (
    TimetablePipeline,
    generate_timetable,
    train_model_from_scratch,
)
from .graph_builder import TimetableGraphBuilder
from .graphsage_model import (
    ACOGraphSAGEModel,
    create_model_from_graph,
    save_model,
    load_model,
)
from .aco_engine import ACOEngine, Solution, create_aco_engine
from .evaluator import SolutionEvaluator
from .local_search import create_local_search

__version__ = "1.0.0"
__all__ = [
    # Configuración
    "ACO_PARAMS",
    "GRAPHSAGE_PARAMS",
    "CONSTRAINT_WEIGHTS",
    "TRAINING_PARAMS",
    "LOCAL_SEARCH_PARAMS",
    # Pipeline principal
    "TimetablePipeline",
    "generate_timetable",
    "train_model_from_scratch",
    # Componentes
    "TimetableGraphBuilder",
    "ACOGraphSAGEModel",
    "create_model_from_graph",
    "save_model",
    "load_model",
    "ACOEngine",
    "Solution",
    "create_aco_engine",
    "SolutionEvaluator",
    "create_local_search",
]
