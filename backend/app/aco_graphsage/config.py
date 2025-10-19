"""
Configuración de Parámetros para ACO+GraphSAGE

Define los hiperparámetros del sistema basados en las especificaciones
confirmadas del proyecto UPAO y las mejores prácticas de la literatura.
"""

# ============================================================================
# PARÁMETROS ACO (Ant Colony Optimization)
# ============================================================================
ACO_PARAMS = {
    # Colonia
    "n_hormigas": 50,  # Número de hormigas por iteración
    "n_iteraciones": 100,  # Iteraciones del algoritmo
    "early_stopping_patience": 12,  # Iteraciones sin mejora antes de detener
    
    # Pesos de la función de probabilidad P(i,j) ∝ [τ]^α · [Φ]^β
    "alpha": 1.0,  # Influencia de la feromona
    "beta": 2.0,   # Influencia de la heurística neural (GraphSAGE)
    
    # Evaporación de feromona
    "rho": 0.1,  # Tasa de evaporación (0.1 = 10% por iteración)
    
    # Max-Min Ant System (MMAS)
    "q0": 0.9,  # Probabilidad de explotación (0.9 = 90% mejor opción, 10% exploración)
    "tau_min": 0.01,  # Límite inferior de feromona
    "tau_max": 10.0,  # Límite superior de feromona
    "tau_init": 1.0,  # Feromona inicial
    
    # Estrategia de actualización
    "elitist_weight": 0.5,  # Peso de la mejor solución global vs. mejor de iteración

    # Límites de espacio de búsqueda por sección
    "max_candidate_combinations": 600,
    "max_professors_per_section": 6,
    "max_classrooms_per_section": 12,
    "max_timeslots_per_section": 12,
    "shuffle_candidates": True,
}

# ============================================================================
# PARÁMETROS GRAPHSAGE (Red Neuronal GNN)
# ============================================================================
GRAPHSAGE_PARAMS = {
    # Arquitectura
    "hidden_dim": 128,  # Dimensión de las capas ocultas
    "n_layers": 3,  # Número de capas de agregación
    "dropout": 0.1,  # Dropout para regularización
    "aggregator_type": "mean",  # Tipo de agregación (mean, max, lstm)
    
    # Optimización
    "learning_rate": 0.001,  # Learning rate para Adam
    "weight_decay": 1e-5,  # Regularización L2
    
    # Features iniciales
    "node_feature_dim": 64,  # Dimensión de embeddings iniciales
    "edge_feature_dim": 32,  # Dimensión de features de aristas
}

# ============================================================================
# PESOS DE RESTRICCIONES (Función Objetivo)
# ============================================================================

# Restricciones DURAS (violación = solución inválida)
# Estas NO tienen peso porque simplemente invalidan la solución
HARD_CONSTRAINTS = [
    "solapamiento_profesor",  # Profesor en dos lugares simultáneamente
    "solapamiento_aula",  # Aula ocupada por dos secciones simultáneamente
    "conflicto_curriculo",  # Dos secciones del mismo ciclo solapadas
    "conflicto_liga",  # Secciones T/P/L de misma liga solapadas
    "disponibilidad_profesor",  # Profesor no disponible en ese horario
    "capacidad_aula",  # Aula con menos capacidad que alumnos proyectados
    "tipo_aula",  # Tipo de aula incorrecto (Lab vs. Teoría)
    "duracion_bloques",  # No se encuentran bloques consecutivos suficientes
]

# Restricciones BLANDAS (violación = penalización en función objetivo)
# Valores basados en prioridades confirmadas por el usuario
CONSTRAINT_WEIGHTS = {
    # PRIORIDAD ALTA: Experiencia del estudiante
    "huecos_estudiantes": 10.0,  # Minimizar espacios libres en horario de ciclo
    
    # PRIORIDAD MEDIA: Logística de movilidad
    "cambio_edificio": 5.0,  # Minimizar cambios de edificio por ciclo/día
    "compacidad_dia": 5.0,  # Preferir horarios compactos en el día
    
    # PRIORIDAD BAJA: Preferencias docentes
    "huecos_profesores": 2.0,  # Minimizar espacios libres en horario de profesor
    "distribucion_profesor": 2.0,  # Distribuir carga del profesor en la semana
    
    # PRIORIDAD MUY BAJA: Preferencias administrativas
    "preferencia_franja": 1.0,  # Penalizar franjas menos deseables (última del día)
    "equilibrio_aulas": 1.0,  # Balancear uso de aulas
    "alineacion_franja": 8.0,  # Favorecer que cada bloque respete su franja objetivo
}

# ============================================================================
# PARÁMETROS DE ENTRENAMIENTO (Reinforcement Learning)
# ============================================================================
TRAINING_PARAMS = {
    # REINFORCE Policy Gradient
    "n_episodes": 500,  # Número de episodios de entrenamiento
    "batch_size": 32,  # Tamaño de batch para actualización
    "gamma": 0.99,  # Factor de descuento para recompensas futuras
    
    # Baseline para reducir varianza
    "use_baseline": True,  # Usar baseline (valor promedio)
    "baseline_decay": 0.95,  # Decaimiento exponencial del baseline
    
    # Exploración
    "epsilon_start": 0.3,  # Exploración inicial
    "epsilon_end": 0.05,  # Exploración final
    "epsilon_decay": 0.995,  # Decaimiento de epsilon por episodio
    
    # Checkpointing
    "save_every": 50,  # Guardar modelo cada N episodios
    "eval_every": 10,  # Evaluar en validación cada N episodios
    
    # Early stopping
    "patience": 50,  # Episodios sin mejora antes de detener
    "min_improvement": 0.01,  # Mejora mínima requerida (1%)
}

# ============================================================================
# CONFIGURACIÓN DE BÚSQUEDA LOCAL
# ============================================================================
LOCAL_SEARCH_PARAMS = {
    "algorithm": "simulated_annealing",  # simulated_annealing | hill_climbing
    "max_iterations": 1000,  # Iteraciones máximas
    "initial_temperature": 100.0,  # Temperatura inicial (SA)
    "cooling_rate": 0.95,  # Tasa de enfriamiento (SA)
    "min_temperature": 0.01,  # Temperatura mínima (SA)
    "n_neighbors": 5,  # Vecinos a explorar por iteración
}

# ============================================================================
# CONFIGURACIÓN DE EVALUACIÓN
# ============================================================================
EVALUATION_PARAMS = {
    # Métricas a calcular
    "metrics": [
        "conflictos_profesor",
        "conflictos_aula",
        "conflictos_curriculo",
        "utilizacion_aulas",
        "huecos_estudiantes",
        "huecos_profesores",
        "cambios_edificio",
        "funcion_objetivo",
    ],
    
    # Formato de reportes
    "export_format": "json",  # json | excel | both
    "include_visualization": True,  # Generar gráficos
}

# ============================================================================
# CONFIGURACIÓN DE BLOQUES HORARIOS
# ============================================================================
TIMESLOT_CONFIG = {
    "duracion_bloque": 50,  # Minutos por bloque (time_slot)
    "dias_semana": [1, 2, 3, 4, 5, 6],  # Lun-Sab
    "periodo_academico": "2025-1",  # Periodo actual
}
