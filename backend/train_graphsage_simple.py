"""
Script simplificado para entrenar GraphSAGE y generar embeddings
para el sistema de horarios UPAO

Este script:
1. Carga datos directamente de la BD
2. Construye un grafo heterogéneo simple  
3. Entrena GraphSAGE
4. Guarda embeddings para uso en ACO
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import SAGEConv
from torch_geometric.data import Data
import numpy as np
import mysql.connector
import json
from pathlib import Path
from datetime import datetime

# ============================================================================
# MODELO GRAPHSAGE
# ============================================================================

class SimpleGraphSAGE(nn.Module):
    """Modelo GraphSAGE simplificado para embeddings académicos"""
    
    def __init__(self, input_dim, hidden_dim=128, embedding_dim=64):
        super().__init__()
        self.conv1 = SAGEConv(input_dim, hidden_dim)
        self.conv2 = SAGEConv(hidden_dim, embedding_dim)
        self.dropout = 0.3
    
    def forward(self, x, edge_index):
        x = self.conv1(x, edge_index)
        x = F.relu(x)
        x = F.dropout(x, p=self.dropout, training=self.training)
        x = self.conv2(x, edge_index)
        return F.normalize(x, p=2, dim=1)  # L2 normalization

# ============================================================================
# CONSTRUCCIÓN DEL GRAFO
# ============================================================================

def build_simple_graph(courses, professors, classrooms, time_slots):
    """
    Construye grafo heterogéneo simplificado:
    - Nodos: cursos, profesores, aulas, slots
    - Edges: curso-profesor (dicta), curso-aula (compatible), curso-slot (asignado)
    """
    
    nodes = []
    node_mapping = {}
    node_idx = 0
    
    # ========== NODOS DE CURSOS ==========
    print("Creando nodos de cursos...")
    for course in courses:
        features = [
            course.get('ciclo', 5) / 10.0,  # Normalizado
            course.get('total_alumnos', 50) / 100.0,
            1.0 if course.get('requiere_laboratorio') else 0.0,
            1.0 if course.get('requiere_practica') else 0.0,
            course.get('creditos', 3) / 6.0,
            0, 0, 0  # Padding para igualar dimensiones
        ]
        nodes.append(features)
        node_mapping[f"course_{course['id']}"] = node_idx
        node_idx += 1
    
    # ========== NODOS DE PROFESORES ==========
    print("Creando nodos de profesores...")
    for prof in professors:
        features = [
            1.0,  # Tipo: profesor
            prof.get('carga_horaria', 20) / 40.0,
            0, 0, 0, 0, 0, 0  # Padding
        ]
        nodes.append(features)
        node_mapping[f"professor_{prof['id']}"] = node_idx
        node_idx += 1
    
    # ========== NODOS DE AULAS ==========
    print("Creando nodos de aulas...")
    for aula in classrooms:
        tipo_val = 1.0 if aula['tipo'] == 'laboratorio' else 0.5
        features = [
            tipo_val,
            aula['capacidad'] / 100.0,
            1.0 if aula['edificio'] == 'F' else 0.0,
            1.0 if aula['edificio'] == 'G' else 0.0,
            0, 0, 0, 0  # Padding
        ]
        nodes.append(features)
        node_mapping[f"classroom_{aula['id']}"] = node_idx
        node_idx += 1
    
    # ========== NODOS DE SLOTS ==========
    print("Creando nodos de slots...")
    for slot in time_slots:
        # Parsear día y hora
        day_map = {
            'lunes': 0, 'martes': 1, 'miércoles': 2, 'miercoles': 2,
            'jueves': 3, 'viernes': 4, 'sábado': 5, 'sabado': 5
        }
        day_str = slot.get('day', 'lunes').lower() if isinstance(slot.get('day'), str) else 'lunes'
        day_num = day_map.get(day_str, 0)
        
        features = [
            day_num / 6.0,  # Día normalizado
            0.5,  # Hora (simplificado)
            0, 0, 0, 0, 0, 0  # Padding
        ]
        nodes.append(features)
        slot_key = f"slot_{slot.get('day', 'lunes')}_{slot.get('start_time', '07:00')}"
        node_mapping[slot_key] = node_idx
        node_idx += 1
    
    # ========== CREAR EDGES ==========
    print("Creando edges...")
    edges = []
    
    # Edges: curso -> profesor (basado en asignaciones existentes en BD)
    conn = mysql.connector.connect(
        host='localhost', user='root',
        password='sistemas', database='upao_timetabling'
    )
    cursor = conn.cursor(dictionary=True)
    
    # Obtener asignaciones curso-profesor
    cursor.execute("""
        SELECT DISTINCT course_id, professor_id 
        FROM proposed_schedule_assignments 
        WHERE course_id IS NOT NULL AND professor_id IS NOT NULL
    """)
    for row in cursor.fetchall():
        course_key = f"course_{row['course_id']}"
        prof_key = f"professor_{row['professor_id']}"
        if course_key in node_mapping and prof_key in node_mapping:
            edges.append([node_mapping[course_key], node_mapping[prof_key]])
            edges.append([node_mapping[prof_key], node_mapping[course_key]])  # Bidireccional
    
    # Edges: curso -> aula (compatibilidad por tipo)
    for course in courses:
        course_key = f"course_{course['id']}"
        if course_key not in node_mapping:
            continue
        
        # Si requiere lab, conectar solo con labs
        if course.get('requiere_laboratorio'):
            for aula in classrooms:
                if aula['tipo'] == 'laboratorio':
                    aula_key = f"classroom_{aula['id']}"
                    if aula_key in node_mapping:
                        edges.append([node_mapping[course_key], node_mapping[aula_key]])
        else:
            # Conectar con todas las aulas compatibles por capacidad
            for aula in classrooms:
                if aula['capacidad'] >= course.get('total_alumnos', 0):
                    aula_key = f"classroom_{aula['id']}"
                    if aula_key in node_mapping:
                        edges.append([node_mapping[course_key], node_mapping[aula_key]])
    
    conn.close()
    
    print(f"Grafo creado: {len(nodes)} nodos, {len(edges)} edges")
    
    # Convertir a tensores
    x = torch.tensor(nodes, dtype=torch.float)
    edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous()
    
    return Data(x=x, edge_index=edge_index), node_mapping

# ============================================================================
# ENTRENAMIENTO
# ============================================================================

def train_graphsage(model, data, epochs=50, lr=0.01):
    """Entrenar modelo GraphSAGE con loss contrastiva simple"""
    
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    model.train()
    
    best_loss = float('inf')
    best_embeddings = None
    
    print(f"\nEntrenando por {epochs} epochs...")
    for epoch in range(epochs):
        optimizer.zero_grad()
        
        # Forward pass
        embeddings = model(data.x, data.edge_index)
        
        # Loss contrastiva simple: minimizar distancia entre nodos conectados
        src, dst = data.edge_index
        pos_loss = ((embeddings[src] - embeddings[dst]) ** 2).sum(dim=1).mean()
        
        # Penalty por embeddings muy grandes
        reg_loss = (embeddings ** 2).sum(dim=1).mean()
        
        loss = pos_loss + 0.001 * reg_loss
        
        # Backward
        loss.backward()
        optimizer.step()
        
        if loss.item() < best_loss:
            best_loss = loss.item()
            best_embeddings = embeddings.detach().clone()
        
        if (epoch + 1) % 10 == 0:
            print(f"Epoch {epoch+1}/{epochs} - Loss: {loss.item():.4f}")
    
    return model, best_embeddings

# ============================================================================
# GUARDAR RESULTADOS
# ============================================================================

def save_embeddings(embeddings, node_mapping, output_dir='models'):
    """Guardar embeddings y mapping para uso en ACO"""
    
    Path(output_dir).mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Guardar embeddings
    embeddings_np = embeddings.numpy()
    np.save(f"{output_dir}/embeddings_{timestamp}.npy", embeddings_np)
    np.save(f"{output_dir}/embeddings_latest.npy", embeddings_np)
    
    # Guardar mapping
    with open(f"{output_dir}/node_mapping_{timestamp}.json", 'w') as f:
        json.dump(node_mapping, f, indent=2)
    with open(f"{output_dir}/node_mapping_latest.json", 'w') as f:
        json.dump(node_mapping, f, indent=2)
    
    print(f"\n✅ Embeddings guardados en {output_dir}/")
    print(f"   - embeddings_latest.npy ({embeddings_np.shape})")
    print(f"   - node_mapping_latest.json ({len(node_mapping)} nodos)")

# ============================================================================
# MAIN
# ============================================================================

def main():
    print("="*70)
    print("GRAPHSAGE SIMPLE - UPAO TIMETABLING")
    print("="*70)
    
    # 1. Cargar datos
    print("\n[1/4] Cargando datos de BD...")
    conn = mysql.connector.connect(
        host='localhost', user='root',
        password='sistemas', database='upao_timetabling'
    )
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM courses WHERE modalidad = 'PRS'")
    courses = cursor.fetchall()
    
    cursor.execute("SELECT * FROM professors")
    professors = cursor.fetchall()
    
    cursor.execute("SELECT * FROM classrooms WHERE disponible = TRUE")
    classrooms = cursor.fetchall()
    
    cursor.execute("SELECT DISTINCT day, start_time FROM proposed_schedule_assignments")
    time_slots = cursor.fetchall()
    
    conn.close()
    
    print(f"   Cursos: {len(courses)}")
    print(f"   Profesores: {len(professors)}")
    print(f"   Aulas: {len(classrooms)}")
    print(f"   Slots: {len(time_slots)}")
    
    # 2. Construir grafo
    print("\n[2/4] Construyendo grafo...")
    data, node_mapping = build_simple_graph(courses, professors, classrooms, time_slots)
    print(f"   Nodos: {data.num_nodes}")
    print(f"   Edges: {data.num_edges}")
    print(f"   Features: {data.x.shape[1]}")
    
    # 3. Entrenar modelo
    print("\n[3/4] Entrenando GraphSAGE...")
    input_dim = data.x.shape[1]
    model = SimpleGraphSAGE(input_dim=input_dim, hidden_dim=128, embedding_dim=64)
    model, embeddings = train_graphsage(model, data, epochs=100, lr=0.01)  # 🆕 100 épocas
    
    # 4. Guardar resultados
    print("\n[4/4] Guardando embeddings...")
    save_embeddings(embeddings, node_mapping)
    
    print("\n" + "="*70)
    print("✅ ENTRENAMIENTO COMPLETADO")
    print("="*70)
    print("\nLos embeddings están listos para usar en ACO.")
    print("Para integrarlos en el algoritmo ACO:")
    print("  1. Cargar embeddings con: np.load('models/embeddings_latest.npy')")
    print("  2. Cargar mapping con: json.load('models/node_mapping_latest.json')")
    print("  3. Calcular similarity: cosine_similarity(emb_curso, emb_slot)")
    print("="*70)
    
    return model, embeddings, node_mapping

if __name__ == "__main__":
    model, embeddings, node_mapping = main()
