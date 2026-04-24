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
    "use_graphsage_heuristic": True,  # Activar heurística neural GraphSAGE en selección ACO
    "allow_partial_solutions": True,  # Permitir seleccionar la mejor solución parcial si no hay cobertura completa
    
    # Estrategia de actualización
    "elitist_weight": 0.5,  # Peso de la mejor solución global vs. mejor de iteración

    # Límites de espacio de búsqueda por sección
    "max_candidate_combinations": 600,
    "max_professors_per_section": 6,
    "max_classrooms_per_section": 12,
    "max_timeslots_per_section": 12,
    "shuffle_candidates": True,
    "enforce_league_coherence": False,  # Evitar solapes dentro de la misma liga (desactivado por defecto)
    # Relajación pedagógica automática (para prácticas/laboratorios de ciclos altos)
    "pedagogical_relaxation_min_cycle": 4,
    "pedagogical_relaxation_attempts": 3,  # REDUCIDO de 6 a 3 para secciones normales
    # Cada 60 unidades equivale aproximadamente a 2/3 de día (rank = día*100 + orden)
    "pedagogical_relaxation_rank_step": 80,  # AUMENTADO de 60 a 80 para ser menos agresivo en regulares
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
    # Perfil de recursos: safe_lite | lite | balanced | aggressive
    # safe_lite: para laptops con <8GB RAM libre (recomendado para entrenamiento local)
    # lite:      para laptops con 8-12GB RAM libre
    # balanced:  para máquinas con >12GB RAM (puede saturar laptops)
    # aggressive: máximo rendimiento, solo en servidores
    "resource_mode": "safe_lite",
    "torch_num_threads": 2,

    # REINFORCE Policy Gradient
    "n_episodes": 150,   # Reducido: con early_stopping=30 suele converger antes
    "batch_size": 16,    # Reducido para menos uso de memoria en el backward pass
    "gamma": 0.99,

    # Baseline para reducir varianza
    "use_baseline": True,
    "baseline_decay": 0.95,

    # Exploración
    "epsilon_start": 0.35,   # Ligeramente más exploración al inicio
    "epsilon_end": 0.05,
    "epsilon_decay": 0.990,  # Decaimiento más rápido (converge antes)

    # Tamaño del rollout ACO por episodio de entrenamiento
    # safe_lite/lite usan sus propios valores en _get_resource_profile()
    "train_aco_ants": 1,
    "train_aco_iterations": 2,
    "train_aco_ants_end": 3,
    "train_aco_iterations_end": 6,

    # Candidatos base (balanced/aggressive)
    # safe_lite y lite los reducen en _get_resource_profile()
    "train_max_candidate_combinations": 1800,
    "train_max_professors_per_section": 10,
    "train_max_classrooms_per_section": 16,
    "train_max_timeslots_per_section": 16,
    "train_pedagogical_relaxation_attempts": 6,
    "train_pedagogical_relaxation_rank_step": 50,

    # Currículo de factibilidad (penalización creciente)
    "coverage_target_start": 0.80,  # Empezar más alto → presionar cobertura desde ep.1
    "coverage_target_end": 0.95,
    "strict_phase_start": 0.80,     # Exigir factibilidad desde el 80% del entrenamiento
    "missing_section_penalty_start": 500.0,   # Penalizar secciones faltantes más fuerte
    "missing_section_penalty_end": 4000.0,
    "hard_violation_penalty": 1_000_000.0,
    "strict_infeasible_penalty": 2_000_000.0,

    # Priorizar cobertura (tesis: 95% asignación)
    "soft_cost_weight": 0.02,  # Reducido: blandas importan menos que cobertura

    # Checkpointing frecuente para poder resumir
    "save_every": 25,
    "eval_every": 10,

    # Early stopping más agresivo en local
    "patience": 30,
    "min_improvement": 0.005,
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
