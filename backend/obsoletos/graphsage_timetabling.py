"""
GRAPHSAGE PARA TIMETABLING

Genera embeddings de cursos, profesores y aulas usando GraphSAGE
para inicializar inteligentemente las feromonas del ACO.

Características consideradas:
- Cursos: Ciclo, modalidad, requiere_lab, num_alumnos, tipo_sesiones
- Profesores: Experiencia (cursos impartidos), disponibilidad
- Aulas: Tipo, capacidad, equipamiento

El grafo:
- Nodos: Cursos, Profesores, Aulas
- Aristas: Curso-Curso (mismo ciclo), Profesor-Curso (impartió),
           Aula-Curso (compatible), etc.
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import List, Dict, Tuple
import networkx as nx
from collections import defaultdict


class GraphSAGELayer(nn.Module):
    """Capa GraphSAGE con agregación MEAN"""
    
    def __init__(self, in_features: int, out_features: int):
        super(GraphSAGELayer, self).__init__()
        self.linear = nn.Linear(in_features * 2, out_features)
    
    def forward(self, x: torch.Tensor, adj_list: Dict) -> torch.Tensor:
        """
        Args:
            x: Features de nodos [N, in_features]
            adj_list: {node_id: [neighbor_ids]}
        
        Returns:
            Embeddings actualizados [N, out_features]
        """
        num_nodes = x.size(0)
        aggregated = []
        
        for node_id in range(num_nodes):
            # Feature del nodo
            node_feat = x[node_id]
            
            # Agregar features de vecinos (MEAN aggregator)
            neighbors = adj_list.get(node_id, [])
            if neighbors:
                neighbor_feats = x[neighbors]
                neighbor_agg = torch.mean(neighbor_feats, dim=0)
            else:
                neighbor_agg = torch.zeros_like(node_feat)
            
            # Concatenar node + aggregated neighbors
            combined = torch.cat([node_feat, neighbor_agg])
            aggregated.append(combined)
        
        aggregated = torch.stack(aggregated)
        
        # Transformación lineal + activación
        out = self.linear(aggregated)
        out = F.relu(out)
        
        return out


class GraphSAGETimetabling(nn.Module):
    """Modelo GraphSAGE para timetabling"""
    
    def __init__(
        self,
        input_dim: int,
        hidden_dim: int = 64,
        output_dim: int = 32,
        num_layers: int = 2
    ):
        super(GraphSAGETimetabling, self).__init__()
        
        self.layers = nn.ModuleList()
        
        # Primera capa
        self.layers.append(GraphSAGELayer(input_dim, hidden_dim))
        
        # Capas intermedias
        for _ in range(num_layers - 2):
            self.layers.append(GraphSAGELayer(hidden_dim, hidden_dim))
        
        # Última capa
        if num_layers > 1:
            self.layers.append(GraphSAGELayer(hidden_dim, output_dim))
    
    def forward(self, x: torch.Tensor, adj_list: Dict) -> torch.Tensor:
        """Forward pass a través de todas las capas"""
        for layer in self.layers:
            x = layer(x, adj_list)
        return x


class GraphSAGEGenerator:
    """Genera embeddings para el sistema de timetabling"""
    
    def __init__(
        self,
        cursos: List[Dict],
        profesores: List[Dict],
        aulas: List[Dict],
        historico_asignaciones: List[Dict] = None
    ):
        self.cursos = cursos
        self.profesores = profesores
        self.aulas = aulas
        self.historico = historico_asignaciones or []
        
        # Construir grafo
        self.G = nx.Graph()
        self.node_to_idx = {}
        self.idx_to_node = {}
        self.node_types = {}
        
        self.construir_grafo()
        
        print("=" * 80)
        print("GRAPHSAGE PARA TIMETABLING")
        print("=" * 80)
        print(f"  📚 Cursos: {len(self.cursos)}")
        print(f"  👥 Profesores: {len(self.profesores)}")
        print(f"  🏫 Aulas: {len(self.aulas)}")
        print(f"  🔗 Nodos totales: {self.G.number_of_nodes()}")
        print(f"  ➡️  Aristas totales: {self.G.number_of_edges()}")
    
    def construir_grafo(self):
        """Construye el grafo de relaciones"""
        idx = 0
        
        # 1. AÑADIR NODOS DE CURSOS
        for curso in self.cursos:
            node_id = f"C_{curso['id']}"
            self.G.add_node(node_id, tipo='curso', data=curso)
            self.node_to_idx[node_id] = idx
            self.idx_to_node[idx] = node_id
            self.node_types[node_id] = 'curso'
            idx += 1
        
        # 2. AÑADIR NODOS DE PROFESORES
        for profesor in self.profesores:
            node_id = f"P_{profesor['id']}"
            self.G.add_node(node_id, tipo='profesor', data=profesor)
            self.node_to_idx[node_id] = idx
            self.idx_to_node[idx] = node_id
            self.node_types[node_id] = 'profesor'
            idx += 1
        
        # 3. AÑADIR NODOS DE AULAS
        for aula in self.aulas:
            node_id = f"A_{aula['id']}"
            self.G.add_node(node_id, tipo='aula', data=aula)
            self.node_to_idx[node_id] = idx
            self.idx_to_node[idx] = node_id
            self.node_types[node_id] = 'aula'
            idx += 1
        
        # 4. CREAR ARISTAS: CURSO-CURSO (mismo ciclo)
        cursos_por_ciclo = defaultdict(list)
        for curso in self.cursos:
            ciclo = curso.get('ciclo', 'unknown')
            cursos_por_ciclo[ciclo].append(f"C_{curso['id']}")
        
        for ciclo, cursos_ids in cursos_por_ciclo.items():
            for i, c1 in enumerate(cursos_ids):
                for c2 in cursos_ids[i+1:]:
                    self.G.add_edge(c1, c2, tipo='mismo_ciclo')
        
        # 5. CREAR ARISTAS: PROFESOR-CURSO (del histórico)
        if self.historico:
            for asig in self.historico:
                curso_node = f"C_{asig['course_id']}"
                prof_node = f"P_{asig['professor_id']}"
                if self.G.has_node(curso_node) and self.G.has_node(prof_node):
                    # Si ya existe, incrementar peso
                    if self.G.has_edge(curso_node, prof_node):
                        self.G[curso_node][prof_node]['peso'] += 1
                    else:
                        self.G.add_edge(curso_node, prof_node, tipo='imparte', peso=1)
        
        # 6. CREAR ARISTAS: AULA-CURSO (compatibilidad)
        for curso in self.cursos:
            curso_node = f"C_{curso['id']}"
            for aula in self.aulas:
                aula_node = f"A_{aula['id']}"
                
                # Compatible si:
                # - Curso requiere lab Y aula es lab
                # - Curso NO requiere lab Y aula NO es lab
                curso_requiere_lab = curso.get('requiere_lab', False)
                aula_es_lab = aula['tipo'] == 'LAB'
                
                if (curso_requiere_lab and aula_es_lab) or (not curso_requiere_lab and not aula_es_lab):
                    # También considerar capacidad
                    capacidad_ok = aula['capacidad'] >= curso.get('alumnos', 0)
                    if capacidad_ok:
                        self.G.add_edge(curso_node, aula_node, tipo='compatible')
    
    def extraer_features(self) -> torch.Tensor:
        """Extrae features de cada nodo para el modelo"""
        num_nodes = len(self.node_to_idx)
        feature_dim = 10  # Dimensión de features manuales
        
        features = torch.zeros(num_nodes, feature_dim)
        
        for node_id, idx in self.node_to_idx.items():
            tipo = self.node_types[node_id]
            data = self.G.nodes[node_id]['data']
            
            if tipo == 'curso':
                # Features de curso: [ciclo(norm), modalidad(bin), requiere_lab(bin), 
                #                     alumnos(norm), num_teorias, num_practicas, num_labs,
                #                     grado_nodo(norm), 0, 0]
                ciclo = data.get('ciclo', 1)
                modalidad = 1.0 if data.get('modalidad') == 'NPR' else 0.0
                requiere_lab = 1.0 if data.get('requiere_lab', False) else 0.0
                alumnos = data.get('alumnos', 0) / 100.0  # Normalizar
                
                # Contar secciones por tipo (necesitaríamos más info)
                grado = self.G.degree(node_id) / 50.0  # Normalizar
                
                features[idx] = torch.tensor([
                    ciclo / 10.0, modalidad, requiere_lab, alumnos,
                    0, 0, 0,  # Placeholders para num_teorias, practicas, labs
                    grado, 0, 0
                ])
            
            elif tipo == 'profesor':
                # Features de profesor: [experiencia(norm), num_cursos_impartidos(norm),
                #                        grado_nodo(norm), 0, ..., 0]
                grado = self.G.degree(node_id) / 20.0
                
                features[idx] = torch.tensor([
                    0.5,  # Experiencia (placeholder)
                    grado, grado,
                    0, 0, 0, 0, 0, 0, 0
                ])
            
            elif tipo == 'aula':
                # Features de aula: [tipo(bin), capacidad(norm), equipamiento(bin),
                #                    grado_nodo(norm), 0, ..., 0]
                tipo_lab = 1.0 if data['tipo'] == 'LAB' else 0.0
                capacidad = data['capacidad'] / 50.0  # Normalizar
                grado = self.G.degree(node_id) / 30.0
                
                features[idx] = torch.tensor([
                    tipo_lab, capacidad, 0,  # equipamiento placeholder
                    grado, 0, 0, 0, 0, 0, 0
                ])
        
        return features
    
    def construir_adj_list(self) -> Dict:
        """Construye lista de adyacencia para GraphSAGE"""
        adj_list = defaultdict(list)
        
        for edge in self.G.edges():
            node1, node2 = edge
            idx1 = self.node_to_idx[node1]
            idx2 = self.node_to_idx[node2]
            
            adj_list[idx1].append(idx2)
            adj_list[idx2].append(idx1)
        
        return adj_list
    
    def entrenar(self, epochs: int = 100, lr: float = 0.01) -> Dict:
        """
        Entrena el modelo GraphSAGE
        
        Returns:
            Embeddings: {node_id: embedding_vector}
        """
        print("\n" + "=" * 80)
        print("ENTRENANDO GRAPHSAGE")
        print("=" * 80)
        
        # Preparar datos
        features = self.extraer_features()
        adj_list = self.construir_adj_list()
        
        # Crear modelo
        input_dim = features.size(1)
        model = GraphSAGETimetabling(input_dim, hidden_dim=64, output_dim=32, num_layers=2)
        
        # Optimizador
        optimizer = torch.optim.Adam(model.parameters(), lr=lr)
        
        # Entrenamiento no supervisado (reconstrucción de vecinos)
        for epoch in range(epochs):
            model.train()
            optimizer.zero_grad()
            
            # Forward pass
            embeddings = model(features, adj_list)
            
            # Loss: Predicción de aristas (link prediction)
            loss = self.compute_link_prediction_loss(embeddings, adj_list)
            
            loss.backward()
            optimizer.step()
            
            if (epoch + 1) % 20 == 0:
                print(f"  Epoch {epoch + 1:3d}: Loss = {loss.item():.4f}")
        
        print("\n✅ Entrenamiento completado")
        
        # Extraer embeddings finales
        model.eval()
        with torch.no_grad():
            final_embeddings = model(features, adj_list)
        
        # Convertir a diccionario
        embeddings_dict = {}
        for node_id, idx in self.node_to_idx.items():
            embeddings_dict[node_id] = final_embeddings[idx].numpy()
        
        return embeddings_dict
    
    def compute_link_prediction_loss(self, embeddings: torch.Tensor, adj_list: Dict) -> torch.Tensor:
        """Loss para link prediction (pares conectados vs no conectados)"""
        num_nodes = embeddings.size(0)
        
        # Muestrear aristas positivas
        pos_pairs = []
        for node in adj_list:
            if adj_list[node]:
                neighbor = np.random.choice(adj_list[node])
                pos_pairs.append((node, neighbor))
        
        if not pos_pairs:
            return torch.tensor(0.0, requires_grad=True)
        
        pos_pairs = pos_pairs[:min(100, len(pos_pairs))]  # Limitar para eficiencia
        
        # Muestrear aristas negativas
        neg_pairs = []
        for _ in range(len(pos_pairs)):
            n1 = np.random.randint(0, num_nodes)
            n2 = np.random.randint(0, num_nodes)
            if n2 not in adj_list.get(n1, []):
                neg_pairs.append((n1, n2))
        
        # Calcular scores
        pos_scores = []
        for n1, n2 in pos_pairs:
            score = torch.dot(embeddings[n1], embeddings[n2])
            pos_scores.append(torch.sigmoid(score))
        
        neg_scores = []
        for n1, n2 in neg_pairs:
            score = torch.dot(embeddings[n1], embeddings[n2])
            neg_scores.append(torch.sigmoid(score))
        
        # Loss: Maximizar pos, minimizar neg
        pos_loss = -torch.log(torch.stack(pos_scores) + 1e-10).mean()
        neg_loss = -torch.log(1 - torch.stack(neg_scores) + 1e-10).mean()
        
        return pos_loss + neg_loss


if __name__ == '__main__':
    print("Este módulo debe ser importado desde el ejecutor principal")
