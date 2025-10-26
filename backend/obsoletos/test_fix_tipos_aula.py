"""
Test rápido: ¿Ahora pueden asignarse las secciones problemáticas?
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')

import random
import numpy as np
import torch
from app.database import SessionLocal
from app.aco_graphsage.pipeline import TimetablePipeline
from app.aco_graphsage.aco_engine import create_aco_engine

# Fijar semillas
SEED = 42
torch.manual_seed(SEED)
np.random.seed(SEED)
random.seed(SEED)

session = SessionLocal()

try:
    print("="*80)
    print("TEST: ¿Se pueden asignar secciones problemáticas ahora?")
    print("="*80)
    
    pipeline = TimetablePipeline(session)
    pipeline.prepare()
    pipeline.model.eval()
    
    # Configuración ACO mínima - solo 3 hormigas, 1 iteración
    params = {
        "n_hormigas": 5,
        "n_iteraciones": 3,
        "alpha": 1.0,
        "beta": 3.5,
        "rho": 0.1,
        
        # Priorizar ICSI506 Liga 1 (secciones 1550-1552 problematicas)
        "priority_course_groups": [
            ("ICSI506", 1),
            ("ICSI506", 2),
            ("ICSI509", 2),
            ("CIEN769", 1),
        ],
        
        "tau_max": 1.0,
        "tau_min": 0.01,
        "q0": 0.9,
        
        "shuffle_candidates": True,
        "max_timeslots_per_section": 48,
        "max_candidate_combinations": 1000,
        
        "early_stopping_patience": 5,
        
        # DEBUG: Ver estas secciones específicamente
        "debug_sections": [1550, 1551, 1552, 1553, 1554, 1608, 1631],
    }
    
    print("\nCreando motor ACO...")
    engine = create_aco_engine(
        graph=pipeline.graph,
        model=pipeline.model,
        graph_builder=pipeline.graph_builder,
        db_session=session,
        params=params,
    )
    
    print("\nEjecutando optimización...")
    best_solution = engine.optimize()
    
    if best_solution:
        print(f"\n{'='*80}")
        print("ÉXITO: Se encontró una solución!")
        print(f"{'='*80}")
        print(f"Secciones asignadas: {len(best_solution.assignments)}")
        print(f"Costo total: {best_solution.total_cost:.2f}")
        
        # Verificar si las secciones problemáticas están asignadas
        asignadas = {a.section_id for a in best_solution.assignments}
        criticas = [1550, 1551, 1552, 1553, 1554, 1608, 1631]
        
        print("\nSecciones críticas:")
        for sec_id in criticas:
            if sec_id in asignadas:
                print(f"  ✓ Sección {sec_id}: ASIGNADA")
            else:
                print(f"  ✗ Sección {sec_id}: NO ASIGNADA")
    else:
        print(f"\n{'='*80}")
        print("FALLO: No se pudo generar solución completa")
        print(f"{'='*80}")

finally:
    session.close()
