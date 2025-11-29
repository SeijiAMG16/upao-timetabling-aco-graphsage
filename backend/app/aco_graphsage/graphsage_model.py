"""
Modelo GraphSAGE para Heurística Neural ACO

Implementa una red neuronal de grafos que aprende a predecir la "calidad"
de asignar una sección a un profesor, aula y franja horaria específicos.

Esta heurística Φ(G, i, j) reemplaza la heurística manual η en ACO tradicional.

Arquitectura:
1. Embeddings iniciales por tipo de nodo
2. Capas SAGEConv para agregación de vecindario
3. MLP final para predecir score de asignación

Entrenamiento:
- Reinforcement Learning (REINFORCE policy gradient)
- Recompensa: -costo_total (minimizar conflictos y penalizaciones)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import SAGEConv, HeteroConv, Linear
from torch_geometric.data import HeteroData
from typing import Dict, List, Tuple, Optional
import numpy as np

from .config import GRAPHSAGE_PARAMS


# ============================================================================
# MODELO GRAPHSAGE HETEROGÉNEO
# ============================================================================

class HeteroGraphSAGE(nn.Module):
    """
    GraphSAGE para grafo heterogéneo del problema de horarios.
    
    Toma un grafo con múltiples tipos de nodos y aristas, y aprende
    embeddings que capturan la estructura y restricciones del problema.
    
    """
    
    def __init__(
        self,
        hidden_dim: int = 128,
        n_layers: int = 3,
        dropout: float = 0.1,
        aggregator: str = "mean",
        metadata: Optional[Tuple] = None,
    ):
        super().__init__()
        
        self.hidden_dim = hidden_dim
        self.n_layers = n_layers
        self.dropout = dropout
        self.aggregator = aggregator
        
        # Construir capas heterogéneas directamente
        self.convs = nn.ModuleList()
        
        if metadata is not None:
            node_types, edge_types = metadata
            
            # Crear HeteroConv para cada capa
            for _ in range(n_layers):
                conv_dict = {}
                for edge_type in edge_types:
                    # Cada tipo de arista tiene su propio SAGEConv
                    conv_dict[edge_type] = SAGEConv(
                        in_channels=hidden_dim,
                        out_channels=hidden_dim,
                        aggr=aggregator,
                        normalize=True,
                    )
                # HeteroConv agrega mensajes de diferentes tipos de aristas
                self.convs.append(HeteroConv(conv_dict, aggr="sum"))
            
            # Batch normalization por tipo de nodo
            self.batch_norms = nn.ModuleDict()
            for node_type in node_types:
                self.batch_norms[node_type] = nn.ModuleList([
                    nn.BatchNorm1d(hidden_dim) for _ in range(n_layers)
                ])
        else:
            # Fallback para cuando no hay metadata (no debería pasar en producción)
            for _ in range(n_layers):
                self.convs.append(
                    SAGEConv(
                        in_channels=hidden_dim,
                        out_channels=hidden_dim,
                        aggr=aggregator,
                        normalize=True,
                    )
                )
            self.batch_norms = nn.ModuleList([
                nn.BatchNorm1d(hidden_dim) for _ in range(n_layers)
            ])
    
    def forward(
        self,
        x_dict: Dict[str, torch.Tensor],
        edge_index_dict: Dict[Tuple[str, str, str], torch.Tensor],
    ) -> Dict[str, torch.Tensor]:
        """
        Forward pass del modelo.
        
        Args:
            x_dict: Diccionario {node_type: features}
            edge_index_dict: Diccionario {edge_type: edge_index}
        
        Returns:
            Diccionario {node_type: embeddings}
        """
        # Aplicar capas HeteroConv
        for i, conv in enumerate(self.convs):
            # Convolución heterogénea
            x_dict = conv(x_dict, edge_index_dict)
            
            # Batch norm y activación por tipo de nodo
            for node_type in x_dict:
                if x_dict[node_type].size(0) > 0:
                    # Aplicar batch norm específico del tipo de nodo
                    if isinstance(self.batch_norms, nn.ModuleDict):
                        x_dict[node_type] = self.batch_norms[node_type][i](x_dict[node_type])
                    else:
                        # Fallback para estructura antigua
                        x_dict[node_type] = self.batch_norms[i](x_dict[node_type])
                    
                    x_dict[node_type] = F.relu(x_dict[node_type])
                    x_dict[node_type] = F.dropout(
                        x_dict[node_type],
                        p=self.dropout,
                        training=self.training
                    )
        
        return x_dict


# ============================================================================
# PREDICTOR DE ASIGNACIONES
# ============================================================================

class AssignmentScorer(nn.Module):
    """
    Predice el score (heurística Φ) de una asignación potencial.
    
    Toma embeddings de: section, professor, classroom, timeslot
    Y produce un score escalar que indica qué tan buena es esa asignación.
    """
    
    def __init__(
        self,
        hidden_dim: int = 128,
        mlp_layers: int = 3,
        dropout: float = 0.1,
    ):
        super().__init__()
        
        self.hidden_dim = hidden_dim
        
        # MLP para combinar embeddings
        # Input: concatenación de 4 embeddings (section + professor + classroom + timeslot)
        input_dim = hidden_dim * 4
        
        layers = []
        current_dim = input_dim
        
        for i in range(mlp_layers - 1):
            next_dim = hidden_dim // (2 ** i)
            next_dim = max(next_dim, 32)  # Mínimo 32
            
            layers.extend([
                nn.Linear(current_dim, next_dim),
                nn.BatchNorm1d(next_dim),
                nn.ReLU(),
                nn.Dropout(dropout),
            ])
            current_dim = next_dim
        
        # Capa final: output escalar
        layers.append(nn.Linear(current_dim, 1))
        
        self.mlp = nn.Sequential(*layers)
    
    def forward(
        self,
        section_emb: torch.Tensor,
        professor_emb: torch.Tensor,
        classroom_emb: torch.Tensor,
        timeslot_emb: torch.Tensor,
    ) -> torch.Tensor:
        """
        Predice el score de una asignación.
        
        Args:
            section_emb: (batch_size, hidden_dim)
            professor_emb: (batch_size, hidden_dim)
            classroom_emb: (batch_size, hidden_dim)
            timeslot_emb: (batch_size, hidden_dim)
        
        Returns:
            scores: (batch_size, 1) - mayor = mejor asignación
        """
        # Concatenar embeddings
        combined = torch.cat([
            section_emb,
            professor_emb,
            classroom_emb,
            timeslot_emb,
        ], dim=-1)
        
        # Pasar por MLP
        scores = self.mlp(combined)
        
        return scores


# ============================================================================
# MODELO COMPLETO ACO+GRAPHSAGE
# ============================================================================

class ACOGraphSAGEModel(nn.Module):
    """
    Modelo completo que combina GraphSAGE y AssignmentScorer.
    
    Este es el modelo que se entrena con REINFORCE y se usa
    como heurística neural en el algoritmo ACO.
    """
    
    def __init__(
        self,
        node_features_dict: Dict[str, int],  # {node_type: n_features}
        hidden_dim: int = None,
        n_layers: int = None,
        dropout: float = None,
        metadata: Optional[Tuple] = None,
    ):
        super().__init__()
        
        # Usar parámetros de config si no se especifican
        hidden_dim = hidden_dim or GRAPHSAGE_PARAMS["hidden_dim"]
        n_layers = n_layers or GRAPHSAGE_PARAMS["n_layers"]
        dropout = dropout or GRAPHSAGE_PARAMS["dropout"]
        
        self.hidden_dim = hidden_dim
        
        # Proyecciones lineales para features iniciales
        self.input_projections = nn.ModuleDict({
            node_type: nn.Linear(n_features, hidden_dim)
            for node_type, n_features in node_features_dict.items()
        })
        
        # GraphSAGE para aprender embeddings
        self.gnn = HeteroGraphSAGE(
            hidden_dim=hidden_dim,
            n_layers=n_layers,
            dropout=dropout,
            metadata=metadata,
        )
        
        # Scorer para predecir calidad de asignaciones
        self.scorer = AssignmentScorer(
            hidden_dim=hidden_dim,
            mlp_layers=3,
            dropout=dropout,
        )
    
    def forward(
        self,
        graph: HeteroData,
        section_idx: torch.Tensor,
        professor_idx: torch.Tensor,
        classroom_idx: torch.Tensor,
        timeslot_idx: torch.Tensor,
    ) -> torch.Tensor:
        """
        Predice el score de asignaciones propuestas.
        
        Args:
            graph: Grafo heterogéneo con x_dict y edge_index_dict
            section_idx: (batch_size,) índices de secciones
            professor_idx: (batch_size,) índices de profesores
            classroom_idx: (batch_size,) índices de aulas
            timeslot_idx: (batch_size,) índices de franjas
        
        Returns:
            scores: (batch_size,) scores de asignación
        """
        # 1. Proyectar features iniciales
        x_dict = {}
        for node_type, features in graph.x_dict.items():
            x_dict[node_type] = self.input_projections[node_type](features)
        
        # 2. Aplicar GraphSAGE
        embeddings = self.gnn(x_dict, graph.edge_index_dict)
        
        # 3. Extraer embeddings específicos
        section_emb = embeddings['section'][section_idx]
        professor_emb = embeddings['professor'][professor_idx]
        classroom_emb = embeddings['classroom'][classroom_idx]
        timeslot_emb = embeddings['timeslot'][timeslot_idx]
        
        # 4. Calcular scores
        scores = self.scorer(
            section_emb,
            professor_emb,
            classroom_emb,
            timeslot_emb,
        )
        
        return scores.squeeze(-1)  # (batch_size,)
    
    def get_heuristic_matrix(
        self,
        graph: HeteroData,
        section_idx: int,
        candidate_assignments: List[Tuple[int, int, int]],  # (prof, classroom, timeslot)
    ) -> np.ndarray:
        """
        Calcula la matriz de heurística para una sección específica.
        
        Esta función se usa durante la construcción de soluciones en ACO.
        
        Args:
            graph: Grafo heterogéneo
            section_idx: Índice de la sección a asignar
            candidate_assignments: Lista de asignaciones candidatas
        
        Returns:
            heuristic_values: (n_candidates,) valores de heurística
        """
        if len(candidate_assignments) == 0:
            return np.array([])
        
        self.eval()
        
        with torch.no_grad():
            # Preparar batch
            n_candidates = len(candidate_assignments)
            section_batch = torch.full((n_candidates,), section_idx, dtype=torch.long)
            professor_batch = torch.tensor([c[0] for c in candidate_assignments], dtype=torch.long)
            classroom_batch = torch.tensor([c[1] for c in candidate_assignments], dtype=torch.long)
            timeslot_batch = torch.tensor([c[2] for c in candidate_assignments], dtype=torch.long)
            
            # Mover a device si es necesario
            device = next(self.parameters()).device
            section_batch = section_batch.to(device)
            professor_batch = professor_batch.to(device)
            classroom_batch = classroom_batch.to(device)
            timeslot_batch = timeslot_batch.to(device)
            
            # Forward pass
            scores = self.forward(
                graph,
                section_batch,
                professor_batch,
                classroom_batch,
                timeslot_batch,
            )
            
            # Aplicar softmax para obtener probabilidades
            heuristic_values = F.softmax(scores, dim=0)
            
            return heuristic_values.cpu().numpy()


# ============================================================================
# UTILIDADES DE CONSTRUCCIÓN
# ============================================================================

def create_model_from_graph(
    graph: HeteroData,
    hidden_dim: int = None,
    n_layers: int = None,
    dropout: float = None,
) -> ACOGraphSAGEModel:
    """
    Crea un modelo ACOGraphSAGE a partir de un grafo.
    
    Extrae automáticamente las dimensiones de features y metadata.
    """
    # Extraer dimensiones de features
    node_features_dict = {
        node_type: features.size(1)
        for node_type, features in graph.x_dict.items()
    }
    
    # Extraer metadata (tipos de nodos y aristas)
    metadata = graph.metadata()
    
    # Crear modelo
    model = ACOGraphSAGEModel(
        node_features_dict=node_features_dict,
        hidden_dim=hidden_dim,
        n_layers=n_layers,
        dropout=dropout,
        metadata=metadata,
    )
    
    return model


def save_model(model: ACOGraphSAGEModel, filepath: str):
    """Guarda el modelo en disco"""
    torch.save({
        'model_state_dict': model.state_dict(),
        'hidden_dim': model.hidden_dim,
        'config': GRAPHSAGE_PARAMS,
    }, filepath)
    print(f"Modelo guardado en: {filepath}")


def load_model(
    filepath: str,
    node_features_dict: Dict[str, int],
    metadata: Tuple,
) -> ACOGraphSAGEModel:
    """Carga un modelo desde disco"""
    checkpoint = torch.load(filepath)
    
    model = ACOGraphSAGEModel(
        node_features_dict=node_features_dict,
        hidden_dim=checkpoint['hidden_dim'],
        metadata=metadata,
    )
    
    model.load_state_dict(checkpoint['model_state_dict'])
    print(f"Modelo cargado desde: {filepath}")
    
    return model
