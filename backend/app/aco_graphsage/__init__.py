"""
ACO+GraphSAGE Pipeline para Generación Automática de Horarios Académicos UPAO

Este módulo implementa el framework híbrido basado en:
- Ant Colony Optimization (ACO) con Max-Min Ant System (MMAS)
- GraphSAGE como heurística aprendida Φ(G,i,j)
- Reinforcement Learning (REINFORCE) para entrenamiento offline

NOTA: PyTorch/torch_geometric son opcionales. Si no están instalados,
el módulo proporcionará stubs que lanzan errores informativos.

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

import warnings

# Config siempre disponible (no requiere torch)
from .config import (
    ACO_PARAMS,
    GRAPHSAGE_PARAMS,
    CONSTRAINT_WEIGHTS,
    TRAINING_PARAMS,
    LOCAL_SEARCH_PARAMS,
)

# Verificar si PyTorch está disponible
TORCH_AVAILABLE = False
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    warnings.warn(
        "PyTorch no está instalado. Las funciones de GraphSAGE no estarán disponibles. "
        "El sistema funcionará solo con ACO básico."
    )


# Stubs para cuando torch no está disponible
class _TorchNotAvailableError(Exception):
    """Error cuando se intenta usar funcionalidad que requiere PyTorch"""
    def __init__(self):
        super().__init__(
            "Esta funcionalidad requiere PyTorch, que no está instalado. "
            "Instale torch y torch_geometric para usar GraphSAGE."
        )


class _StubClass:
    """Stub class que lanza error al instanciar"""
    def __init__(self, *args, **kwargs):
        raise _TorchNotAvailableError()


def _stub_function(*args, **kwargs):
    """Stub function que lanza error al llamar"""
    raise _TorchNotAvailableError()


# Importar componentes reales o usar stubs
if TORCH_AVAILABLE:
    try:
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
    except ImportError as e:
        warnings.warn(f"Error importando componentes ACO+GraphSAGE: {e}")
        TORCH_AVAILABLE = False

if not TORCH_AVAILABLE:
    # Usar stubs
    TimetablePipeline = _StubClass
    generate_timetable = _stub_function
    train_model_from_scratch = _stub_function
    TimetableGraphBuilder = _StubClass
    ACOGraphSAGEModel = _StubClass
    create_model_from_graph = _stub_function
    save_model = _stub_function
    load_model = _stub_function
    ACOEngine = _StubClass
    Solution = _StubClass
    create_aco_engine = _stub_function
    SolutionEvaluator = _StubClass
    create_local_search = _stub_function


__version__ = "1.0.0"
__all__ = [
    # Flag de disponibilidad
    "TORCH_AVAILABLE",
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
