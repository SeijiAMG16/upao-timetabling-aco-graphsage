"""
Módulo de inferencia para GraphSAGE
Provee funciones para cargar y usar embeddings en el algoritmo ACO
"""

import numpy as np
import json
from pathlib import Path
from typing import Dict, Tuple, Optional

class GraphSAGEInference:
    """Clase para cargar y usar embeddings de GraphSAGE en ACO"""
    
    def __init__(self, embeddings_path='models/embeddings_latest.npy',
                 mapping_path='models/node_mapping_latest.json'):
        """
        Inicializa el módulo de inferencia
        
        Args:
            embeddings_path: Ruta al archivo .npy con embeddings
            mapping_path: Ruta al archivo .json con mapeo de nodos
        """
        self.embeddings = self._load_embeddings(embeddings_path)
        self.node_mapping = self._load_mapping(mapping_path)
        print(f"✅ Embeddings cargados: {self.embeddings.shape}")
        print(f"✅ Nodos mapeados: {len(self.node_mapping)}")
    
    def _load_embeddings(self, path: str) -> np.ndarray:
        """Carga embeddings desde archivo .npy"""
        full_path = Path(__file__).parent / path
        return np.load(full_path)
    
    def _load_mapping(self, path: str) -> Dict:
        """Carga mapeo de nodos desde JSON"""
        full_path = Path(__file__).parent / path
        with open(full_path, 'r') as f:
            return json.load(f)
    
    def get_embedding(self, entity_type: str, entity_id: int) -> Optional[np.ndarray]:
        """
        Obtiene el embedding de una entidad específica
        
        Args:
            entity_type: Tipo de entidad ('course', 'professor', 'classroom', 'slot')
            entity_id: ID de la entidad
            
        Returns:
            Array numpy con el embedding (64 dimensiones) o None si no existe
        """
        key = f"{entity_type}_{entity_id}"
        
        if key not in self.node_mapping:
            return None
        
        node_idx = self.node_mapping[key]
        return self.embeddings[node_idx]
    
    def get_slot_embedding(self, day: str, start_time: str) -> Optional[np.ndarray]:
        """
        Obtiene embedding de un slot temporal específico
        
        Args:
            day: Día de la semana ('lunes', 'martes', etc.)
            start_time: Hora de inicio ('07:00', '08:00', etc.)
            
        Returns:
            Embedding del slot o None si no existe
        """
        key = f"slot_{day}_{start_time}"
        
        if key not in self.node_mapping:
            return None
        
        node_idx = self.node_mapping[key]
        return self.embeddings[node_idx]
    
    def cosine_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """
        Calcula similaridad coseno entre dos embeddings
        
        Args:
            emb1: Primer embedding
            emb2: Segundo embedding
            
        Returns:
            Valor entre -1 y 1 (1 = muy similar, -1 = muy diferente)
        """
        if emb1 is None or emb2 is None:
            return 0.0
        
        dot_product = np.dot(emb1, emb2)
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def calculate_assignment_score(self, course_id: int, professor_id: int,
                                   classroom_id: int, day: str, start_time: str,
                                   weights: Tuple[float, float, float] = (0.4, 0.3, 0.3)) -> float:
        """
        Calcula un score de compatibilidad para una asignación completa
        basado en embeddings de GraphSAGE
        
        Args:
            course_id: ID del curso
            professor_id: ID del profesor
            classroom_id: ID del aula
            day: Día de la semana
            start_time: Hora de inicio
            weights: Pesos para (curso-slot, curso-aula, curso-profesor)
            
        Returns:
            Score entre 0 y 1 (1 = muy compatible, 0 = incompatible)
        """
        # Obtener embeddings
        emb_course = self.get_embedding('course', course_id)
        emb_professor = self.get_embedding('professor', professor_id)
        emb_classroom = self.get_embedding('classroom', classroom_id)
        emb_slot = self.get_slot_embedding(day, start_time)
        
        # Si falta algún embedding, retornar score neutral
        if any(e is None for e in [emb_course, emb_professor, emb_classroom, emb_slot]):
            return 0.5
        
        # Calcular similaridades
        sim_course_slot = self.cosine_similarity(emb_course, emb_slot)
        sim_course_classroom = self.cosine_similarity(emb_course, emb_classroom)
        sim_course_professor = self.cosine_similarity(emb_course, emb_professor)
        
        # Normalizar a rango [0, 1]
        sim_course_slot = (sim_course_slot + 1) / 2
        sim_course_classroom = (sim_course_classroom + 1) / 2
        sim_course_professor = (sim_course_professor + 1) / 2
        
        # Combinar con pesos
        w1, w2, w3 = weights
        score = (w1 * sim_course_slot + 
                w2 * sim_course_classroom + 
                w3 * sim_course_professor)
        
        return max(0.0, min(1.0, score))  # Clamp entre 0 y 1
    
    def get_top_k_similar_slots(self, course_id: int, available_slots: list, k: int = 5) -> list:
        """
        Obtiene los K slots más compatibles con un curso según embeddings
        
        Args:
            course_id: ID del curso
            available_slots: Lista de slots disponibles [(day, start_time), ...]
            k: Número de slots a retornar
            
        Returns:
            Lista de tuplas (day, start_time, similarity_score) ordenadas por score
        """
        emb_course = self.get_embedding('course', course_id)
        
        if emb_course is None:
            return available_slots[:k]  # Si no hay embedding, retornar primeros k
        
        scores = []
        for day, start_time in available_slots:
            emb_slot = self.get_slot_embedding(day, start_time)
            if emb_slot is not None:
                sim = self.cosine_similarity(emb_course, emb_slot)
                sim_normalized = (sim + 1) / 2  # Normalizar a [0, 1]
                scores.append((day, start_time, sim_normalized))
        
        # Ordenar por score descendente
        scores.sort(key=lambda x: x[2], reverse=True)
        
        return scores[:k]
    
    def explain_assignment(self, course_id: int, professor_id: int,
                          classroom_id: int, day: str, start_time: str) -> dict:
        """
        Genera una explicación detallada de por qué una asignación es compatible
        
        Returns:
            Dict con scores individuales y explicación
        """
        emb_course = self.get_embedding('course', course_id)
        emb_professor = self.get_embedding('professor', professor_id)
        emb_classroom = self.get_embedding('classroom', classroom_id)
        emb_slot = self.get_slot_embedding(day, start_time)
        
        if any(e is None for e in [emb_course, emb_professor, emb_classroom, emb_slot]):
            return {
                'error': 'Embeddings no encontrados',
                'available': {
                    'course': emb_course is not None,
                    'professor': emb_professor is not None,
                    'classroom': emb_classroom is not None,
                    'slot': emb_slot is not None
                }
            }
        
        # Calcular todas las similaridades
        sim_course_slot = self.cosine_similarity(emb_course, emb_slot)
        sim_course_classroom = self.cosine_similarity(emb_course, emb_classroom)
        sim_course_professor = self.cosine_similarity(emb_course, emb_professor)
        sim_slot_classroom = self.cosine_similarity(emb_slot, emb_classroom)
        sim_slot_professor = self.cosine_similarity(emb_slot, emb_professor)
        sim_classroom_professor = self.cosine_similarity(emb_classroom, emb_professor)
        
        # Normalizar
        def normalize(s):
            return (s + 1) / 2
        
        overall_score = self.calculate_assignment_score(
            course_id, professor_id, classroom_id, day, start_time
        )
        
        return {
            'overall_score': overall_score,
            'pairwise_similarities': {
                'course_slot': normalize(sim_course_slot),
                'course_classroom': normalize(sim_course_classroom),
                'course_professor': normalize(sim_course_professor),
                'slot_classroom': normalize(sim_slot_classroom),
                'slot_professor': normalize(sim_slot_professor),
                'classroom_professor': normalize(sim_classroom_professor)
            },
            'interpretation': self._interpret_score(overall_score)
        }
    
    def _interpret_score(self, score: float) -> str:
        """Interpreta un score de compatibilidad"""
        if score >= 0.8:
            return "Excelente compatibilidad ✅"
        elif score >= 0.6:
            return "Buena compatibilidad ✓"
        elif score >= 0.4:
            return "Compatibilidad aceptable ~"
        elif score >= 0.2:
            return "Baja compatibilidad ⚠️"
        else:
            return "Incompatibilidad detectada ❌"


# ============================================================================
# FUNCIÓN HELPER PARA USO EN ACO
# ============================================================================

# Instancia global (se carga una sola vez)
_inference_instance = None

def get_graphsage_inference():
    """Obtiene instancia singleton de GraphSAGEInference"""
    global _inference_instance
    if _inference_instance is None:
        _inference_instance = GraphSAGEInference()
    return _inference_instance


def calcular_heuristica_graphsage(course_id: int, professor_id: int,
                                  classroom_id: int, day: str, start_time: str,
                                  penalty_factor: float = 1.0) -> float:
    """
    Función de heurística mejorada con GraphSAGE para usar en ACO
    
    Esta función reemplaza la heurística simple del ACO baseline.
    
    Args:
        course_id: ID del curso
        professor_id: ID del profesor
        classroom_id: ID del aula
        day: Día de la semana
        start_time: Hora de inicio
        penalty_factor: Factor de penalización por restricciones (0.0-1.0)
            - 1.0 = sin restricciones violadas
            - 0.1 = restricción dura violada
            - 0.5 = restricción suave violada
    
    Returns:
        Valor heurístico entre 0.01 y 1.0
    """
    inference = get_graphsage_inference()
    
    # Obtener score base de GraphSAGE
    base_score = inference.calculate_assignment_score(
        course_id, professor_id, classroom_id, day, start_time
    )
    
    # Aplicar penalizaciones por restricciones
    final_score = base_score * penalty_factor
    
    # Garantizar mínimo valor positivo (para que ACO no descarte completamente)
    return max(0.01, min(1.0, final_score))


# ============================================================================
# EJEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("GRAPHSAGE INFERENCE - DEMO")
    print("="*70)
    
    # Cargar embeddings
    inference = GraphSAGEInference()
    
    # Ejemplo 1: Obtener embedding de un curso
    print("\n[Ejemplo 1] Obtener embedding de curso ID=1")
    emb = inference.get_embedding('course', 1)
    if emb is not None:
        print(f"  Shape: {emb.shape}")
        print(f"  Primeros 5 valores: {emb[:5]}")
    
    # Ejemplo 2: Calcular similaridad entre curso y slot
    print("\n[Ejemplo 2] Similaridad curso-slot")
    emb_course = inference.get_embedding('course', 1)
    emb_slot = inference.get_slot_embedding('lunes', '07:00')
    if emb_course is not None and emb_slot is not None:
        sim = inference.cosine_similarity(emb_course, emb_slot)
        print(f"  Similaridad: {sim:.4f}")
        print(f"  Normalizada [0-1]: {(sim + 1) / 2:.4f}")
    
    # Ejemplo 3: Score de asignación completa
    print("\n[Ejemplo 3] Score de asignación completa")
    score = inference.calculate_assignment_score(
        course_id=1,
        professor_id=2,
        classroom_id=3,
        day='lunes',
        start_time='07:00'
    )
    print(f"  Score: {score:.4f}")
    print(f"  Interpretación: {inference._interpret_score(score)}")
    
    # Ejemplo 4: Top-k slots más compatibles
    print("\n[Ejemplo 4] Top 3 slots más compatibles para curso ID=1")
    available_slots = [
        ('lunes', '07:00'),
        ('martes', '08:00'),
        ('miercoles', '09:00'),
        ('jueves', '10:00'),
        ('viernes', '11:00')
    ]
    top_slots = inference.get_top_k_similar_slots(1, available_slots, k=3)
    for i, (day, time, score) in enumerate(top_slots, 1):
        print(f"  {i}. {day} {time} - Score: {score:.4f}")
    
    # Ejemplo 5: Explicación detallada
    print("\n[Ejemplo 5] Explicación detallada de asignación")
    explanation = inference.explain_assignment(
        course_id=1, professor_id=2, classroom_id=3,
        day='lunes', start_time='07:00'
    )
    if 'error' not in explanation:
        print(f"  Score general: {explanation['overall_score']:.4f}")
        print(f"  {explanation['interpretation']}")
        print("\n  Similaridades por pares:")
        for pair, sim in explanation['pairwise_similarities'].items():
            print(f"    - {pair}: {sim:.4f}")
    
    # Ejemplo 6: Usar en ACO
    print("\n[Ejemplo 6] Heurística para ACO")
    heuristica = calcular_heuristica_graphsage(
        course_id=1, professor_id=2, classroom_id=3,
        day='lunes', start_time='07:00',
        penalty_factor=1.0  # Sin penalizaciones
    )
    print(f"  Heurística ACO: {heuristica:.4f}")
    
    heuristica_penalizada = calcular_heuristica_graphsage(
        course_id=1, professor_id=2, classroom_id=3,
        day='lunes', start_time='07:00',
        penalty_factor=0.5  # Con penalización suave
    )
    print(f"  Heurística penalizada (50%): {heuristica_penalizada:.4f}")
    
    print("\n" + "="*70)
    print("✅ Demo completada. Listo para integrar en ACO!")
    print("="*70)
