"""
GraphSAGE Integration Setup for UPAO Timetabling
Fase 2: Implementación de GraphSAGE para optimización híbrida ACO+GraphSAGE
"""

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import SAGEConv, global_mean_pool
from torch_geometric.data import Data, DataLoader
import json
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from sklearn.preprocessing import StandardScaler, LabelEncoder
import networkx as nx

logger = logging.getLogger(__name__)

@dataclass
class GraphNode:
    """Representación de un nodo en el grafo académico"""
    id: str
    type: str  # 'course', 'professor', 'classroom', 'timeslot'
    features: np.ndarray
    metadata: Dict

@dataclass 
class GraphEdge:
    """Representación de una arista en el grafo académico"""
    source: str
    target: str
    edge_type: str  # 'compatibility', 'constraint', 'preference'
    weight: float
    metadata: Dict

class AcademicGraphBuilder:
    """Constructor del grafo académico UPAO"""
    
    def __init__(self):
        self.nodes = {}
        self.edges = []
        self.node_encoder = LabelEncoder()
        self.scaler = StandardScaler()
        
    def build_upao_academic_graph(self, courses: Dict, professors: Dict, 
                                 classrooms: Dict, time_slots: List) -> Data:
        """Construye el grafo académico completo de UPAO"""
        
        logger.info("Construyendo grafo académico UPAO...")
        
        # 1. Crear nodos para cada entidad
        self._create_course_nodes(courses)
        self._create_professor_nodes(professors)
        self._create_classroom_nodes(classrooms)
        self._create_timeslot_nodes(time_slots)
        
        # 2. Crear aristas basadas en compatibilidad y restricciones
        self._create_compatibility_edges(courses, professors, classrooms, time_slots)
        self._create_constraint_edges(courses, classrooms)
        self._create_preference_edges(courses, time_slots)
        
        # 3. Convertir a formato PyTorch Geometric
        graph_data = self._convert_to_pytorch_geometric()
        
        logger.info(f"Grafo construido: {len(self.nodes)} nodos, {len(self.edges)} aristas")
        return graph_data
    
    def _create_course_nodes(self, courses: Dict):
        """Crea nodos para cursos con features relevantes"""
        
        for course_id, course in courses.items():
            features = np.array([
                course.ciclo,  # Ciclo académico (1-10)
                course.grupos_teoria,
                course.grupos_practica,
                course.grupos_laboratorio,
                course.alumnos_teoria,
                course.alumnos_practica,
                course.alumnos_laboratorio,
                1.0 if course.requiere_laboratorio else 0.0,
                1.0 if course.requiere_practica else 0.0,
                1.0 if course.modalidad == 'PRS' else 0.0,  # Presencial vs no presencial
                # Complejidad basada en número de grupos y estudiantes
                (course.grupos_teoria + course.grupos_practica + course.grupos_laboratorio) * 
                (course.alumnos_teoria + course.alumnos_practica + course.alumnos_laboratorio) / 1000.0
            ])
            
            self.nodes[course_id] = GraphNode(
                id=course_id,
                type='course',
                features=features,
                metadata={
                    'nombre': course.nombre,
                    'ciclo': course.ciclo,
                    'modalidad': course.modalidad
                }
            )
    
    def _create_professor_nodes(self, professors: Dict):
        """Crea nodos para profesores con features de disponibilidad y carga"""
        
        for prof_id, prof in professors.items():
            # Calcular métricas de disponibilidad
            total_slots = 16 * 6  # 16 franjas × 6 días
            available_slots = len(prof.disponibilidad)
            availability_ratio = available_slots / total_slots
            
            # Distribución de disponibilidad por periodo
            morning_slots = sum(1 for (day, slot) in prof.disponibilidad if 1 <= slot <= 6)
            afternoon_slots = sum(1 for (day, slot) in prof.disponibilidad if 7 <= slot <= 12)
            evening_slots = sum(1 for (day, slot) in prof.disponibilidad if 13 <= slot <= 16)
            
            features = np.array([
                availability_ratio,
                morning_slots / max(1, available_slots),
                afternoon_slots / max(1, available_slots), 
                evening_slots / max(1, available_slots),
                prof.carga_maxima,
                prof.carga_actual,
                prof.carga_actual / max(1, prof.carga_maxima),  # Utilización actual
                # Flexibilidad (diversidad de días disponibles)
                len(set(day for (day, slot) in prof.disponibilidad)) / 6.0
            ])
            
            self.nodes[prof_id] = GraphNode(
                id=prof_id,
                type='professor',
                features=features,
                metadata={
                    'nombre': prof.nombre,
                    'disponibilidad_count': available_slots,
                    'carga_maxima': prof.carga_maxima
                }
            )
    
    def _create_classroom_nodes(self, classrooms: Dict):
        """Crea nodos para aulas con features de capacidad y tipo"""
        
        for classroom_id, classroom in classrooms.items():
            # Normalizar capacidad (asumiendo rango 15-50)
            normalized_capacity = (classroom.capacidad - 15) / 35.0
            
            features = np.array([
                normalized_capacity,
                1.0 if classroom.tipo == 'laboratorio' else 0.0,
                1.0 if classroom.tipo == 'teorica' else 0.0,
                1.0 if classroom.edificio == 'F' else 0.0,
                1.0 if classroom.edificio == 'G' else 0.0,
                classroom.capacidad,
                # Indicador de aula premium (alta capacidad)
                1.0 if classroom.capacidad > 35 else 0.0,
                # Indicador de aula especializada
                1.0 if classroom.tipo == 'laboratorio' and classroom.edificio == 'F' else 0.0
            ])
            
            self.nodes[classroom_id] = GraphNode(
                id=classroom_id,
                type='classroom',
                features=features,
                metadata={
                    'tipo': classroom.tipo,
                    'capacidad': classroom.capacidad,
                    'edificio': classroom.edificio
                }
            )
    
    def _create_timeslot_nodes(self, time_slots: List):
        """Crea nodos para franjas horarias con features temporales"""
        
        for slot in time_slots:
            slot_id = f"D{slot.dia}_F{slot.franja}"
            
            # Features temporales
            day_normalized = (slot.dia - 1) / 5.0  # Lunes=0, Sábado=1
            slot_normalized = (slot.franja - 1) / 15.0  # Primera=0, Última=1
            
            features = np.array([
                day_normalized,
                slot_normalized,
                1.0 if slot.periodo == 'mañana' else 0.0,
                1.0 if slot.periodo == 'tarde' else 0.0,
                1.0 if slot.periodo == 'noche' else 0.0,
                # Desirabilidad del horario (mañana y tarde más deseables)
                1.0 if slot.periodo in ['mañana', 'tarde'] else 0.5,
                # Indicador de día de semana vs sábado
                1.0 if slot.dia <= 5 else 0.0,
                # Horario premium (mañana entre semana)
                1.0 if slot.periodo == 'mañana' and slot.dia <= 5 else 0.0
            ])
            
            self.nodes[slot_id] = GraphNode(
                id=slot_id,
                type='timeslot',
                features=features,
                metadata={
                    'dia': slot.dia,
                    'franja': slot.franja,
                    'periodo': slot.periodo
                }
            )
    
    def _create_compatibility_edges(self, courses, professors, classrooms, time_slots):
        """Crea aristas de compatibilidad entre entidades"""
        
        # Course-Professor compatibility (basado en disponibilidad y carga)
        for course_id in courses:
            for prof_id, prof in professors.items():
                # Compatibilidad basada en carga disponible
                load_compatibility = max(0.0, (prof.carga_maxima - prof.carga_actual) / prof.carga_maxima)
                
                if load_compatibility > 0:
                    self.edges.append(GraphEdge(
                        source=course_id,
                        target=prof_id,
                        edge_type='compatibility',
                        weight=load_compatibility,
                        metadata={'type': 'course_professor'}
                    ))
        
        # Course-Classroom compatibility (basado en tipo y capacidad)
        for course_id, course in courses.items():
            for classroom_id, classroom in classrooms.items():
                compatibility = 0.0
                
                # Compatibilidad de tipo para laboratorios
                if course.requiere_laboratorio and classroom.tipo == 'laboratorio':
                    # Verificar regla F/G
                    if course.alumnos_laboratorio <= 20 and classroom.edificio == 'F':
                        compatibility = 1.0
                    elif course.alumnos_laboratorio > 20 and classroom.edificio == 'G':
                        compatibility = 1.0
                    else:
                        compatibility = 0.3  # Penalización por violación F/G
                
                # Compatibilidad de capacidad
                max_students = max(course.alumnos_teoria, course.alumnos_practica, course.alumnos_laboratorio)
                if max_students <= classroom.capacidad:
                    capacity_score = 1.0 - abs(max_students - classroom.capacidad) / classroom.capacidad
                    compatibility = max(compatibility, capacity_score)
                
                if compatibility > 0:
                    self.edges.append(GraphEdge(
                        source=course_id,
                        target=classroom_id,
                        edge_type='compatibility',
                        weight=compatibility,
                        metadata={'type': 'course_classroom'}
                    ))
    
    def _create_constraint_edges(self, courses, classrooms):
        """Crea aristas de restricciones duras"""
        
        # Restricciones de laboratorio F/G
        for course_id, course in courses.items():
            if course.requiere_laboratorio:
                for classroom_id, classroom in classrooms.items():
                    if classroom.tipo == 'laboratorio':
                        # Arista de restricción si viola regla F/G
                        violates_fg_rule = (
                            (course.alumnos_laboratorio <= 20 and classroom.edificio != 'F') or
                            (course.alumnos_laboratorio > 20 and classroom.edificio != 'G')
                        )
                        
                        if violates_fg_rule:
                            self.edges.append(GraphEdge(
                                source=course_id,
                                target=classroom_id,
                                edge_type='constraint',
                                weight=-1.0,  # Peso negativo indica restricción
                                metadata={'type': 'fg_lab_rule', 'violation': True}
                            ))
    
    def _create_preference_edges(self, courses, time_slots):
        """Crea aristas de preferencias suaves"""
        
        # Preferencias de horario por ciclo
        for course_id, course in courses.items():
            preferred_period = 'mañana' if course.ciclo % 2 == 1 else 'tarde'
            
            for slot in time_slots:
                slot_id = f"D{slot.dia}_F{slot.franja}"
                
                # Peso de preferencia
                if slot.periodo == preferred_period:
                    preference_weight = 1.0
                elif slot.periodo == 'noche':
                    preference_weight = 0.3  # Menos preferible para todos
                else:
                    preference_weight = 0.7  # Moderadamente preferible
                
                self.edges.append(GraphEdge(
                    source=course_id,
                    target=slot_id,
                    edge_type='preference',
                    weight=preference_weight,
                    metadata={'type': 'cycle_time_preference', 'preferred': preferred_period}
                ))
    
    def _convert_to_pytorch_geometric(self) -> Data:
        """Convierte el grafo a formato PyTorch Geometric"""
        
        # Crear mapeo de IDs a índices
        node_ids = list(self.nodes.keys())
        id_to_idx = {node_id: idx for idx, node_id in enumerate(node_ids)}
        
        # Preparar features de nodos
        node_features = []
        node_types = []
        
        for node_id in node_ids:
            node = self.nodes[node_id]
            node_features.append(node.features)
            node_types.append(node.type)
        
        # Normalizar features
        node_features = np.array(node_features)
        node_features = self.scaler.fit_transform(node_features)
        
        # Preparar aristas
        edge_indices = []
        edge_weights = []
        edge_types = []
        
        for edge in self.edges:
            if edge.source in id_to_idx and edge.target in id_to_idx:
                edge_indices.append([id_to_idx[edge.source], id_to_idx[edge.target]])
                edge_weights.append(edge.weight)
                edge_types.append(edge.edge_type)
        
        # Convertir a tensores
        x = torch.tensor(node_features, dtype=torch.float)
        edge_index = torch.tensor(edge_indices, dtype=torch.long).t().contiguous()
        edge_attr = torch.tensor(edge_weights, dtype=torch.float)
        
        return Data(
            x=x,
            edge_index=edge_index,
            edge_attr=edge_attr,
            node_ids=node_ids,
            node_types=node_types,
            edge_types=edge_types
        )


class GraphSAGEConflictPredictor(nn.Module):
    """Modelo GraphSAGE para predicción de conflictos en asignaciones"""
    
    def __init__(self, input_dim: int, hidden_dim: int = 64, num_layers: int = 3):
        super(GraphSAGEConflictPredictor, self).__init__()
        
        self.num_layers = num_layers
        
        # Capas GraphSAGE
        self.convs = nn.ModuleList()
        self.convs.append(SAGEConv(input_dim, hidden_dim))
        
        for _ in range(num_layers - 2):
            self.convs.append(SAGEConv(hidden_dim, hidden_dim))
        
        self.convs.append(SAGEConv(hidden_dim, hidden_dim))
        
        # Predictor de conflictos (binary classification)
        self.conflict_predictor = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )
        
        # Predictor de calidad de asignación (regression)
        self.quality_predictor = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2), 
            nn.Linear(hidden_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 1)
        )
    
    def forward(self, data):
        x, edge_index = data.x, data.edge_index
        
        # Propagación GraphSAGE
        for i, conv in enumerate(self.convs):
            x = conv(x, edge_index)
            if i < len(self.convs) - 1:
                x = F.relu(x)
                x = F.dropout(x, training=self.training)
        
        # Embeddings finales de nodos
        node_embeddings = x
        
        return node_embeddings
    
    def predict_assignment_quality(self, node_embeddings, source_idx, target_idx):
        """Predice la calidad de una asignación específica"""
        
        # Concatenar embeddings de nodos relacionados
        source_emb = node_embeddings[source_idx]
        target_emb = node_embeddings[target_idx]
        combined = torch.cat([source_emb, target_emb], dim=-1)
        
        # Predicciones
        conflict_prob = self.conflict_predictor(combined)
        quality_score = self.quality_predictor(combined)
        
        return conflict_prob, quality_score


def setup_graphsage_environment():
    """Configura el entorno para GraphSAGE"""
    
    logger.info("Configurando entorno GraphSAGE...")
    
    # Verificar dependencias
    try:
        import torch_geometric
        logger.info(f"PyTorch Geometric versión: {torch_geometric.__version__}")
    except ImportError:
        logger.error("PyTorch Geometric no está instalado. Ejecutar: pip install torch-geometric")
        return False
    
    try:
        import networkx
        logger.info(f"NetworkX versión: {networkx.__version__}")
    except ImportError:
        logger.error("NetworkX no está instalado. Ejecutar: pip install networkx")
        return False
    
    # Verificar GPU si está disponible
    if torch.cuda.is_available():
        logger.info(f"GPU disponible: {torch.cuda.get_device_name(0)}")
    else:
        logger.info("Usando CPU para entrenamiento")
    
    return True


def main():
    """Función principal para configurar GraphSAGE"""
    
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "="*60)
    print("🚀 FASE 2: CONFIGURACIÓN GRAPHSAGE")
    print("="*60)
    
    # Verificar entorno
    if not setup_graphsage_environment():
        print("❌ Error en configuración de dependencias")
        return
    
    print("✅ Entorno GraphSAGE configurado correctamente")
    
    # Cargar datos de la Fase 1
    try:
        with open('upao_data_for_aco.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✅ Datos ACO cargados: {data['metadata']['total_courses']} cursos")
    except FileNotFoundError:
        print("❌ Datos de ACO no encontrados. Ejecutar primero run_aco_optimized.py")
        return
    
    print("\n📋 PRÓXIMOS PASOS GRAPHSAGE:")
    print("1. 🔧 Instalar dependencias: pip install torch-geometric networkx scikit-learn")
    print("2. 🏗️ Construir grafo académico UPAO")
    print("3. 🧠 Entrenar modelo GraphSAGE")
    print("4. 🔄 Integrar con ACO (algoritmo híbrido)")
    print("5. 📊 Comparar resultados ACO vs ACO+GraphSAGE")
    
    print("\n🎯 OBJETIVOS FASE 2:")
    print("• Mejorar tasa de éxito: 64.3% → 85%+")
    print("• Reducir asignaciones no realizadas: 106 → <50")
    print("• Mantener 0 violaciones de restricciones")
    print("• Implementar predicción inteligente de conflictos")
    
    print("\n" + "="*60)
    print("💡 Ejecutar: pip install torch-geometric para continuar")
    print("="*60)


if __name__ == "__main__":
    main()