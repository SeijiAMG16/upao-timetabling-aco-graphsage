"""
Script para probar la velocidad del ACO optimizado
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.aco_graphsage.graph_builder import TimetableGraphBuilder
from app.aco_graphsage.graphsage_model import ACOGraphSAGEModel
from app.aco_graphsage.aco_engine import ACOEngine
from app.models import TimeSlot, Classroom, ProfessorRestriction
from app.aco_graphsage.constraints import (
    TimeSlotInfo, 
    ClassroomInfo, 
    ProfessorRestrictionInfo,
    HardConstraintValidator,
    SoftConstraintEvaluator
)
import torch
import time

def main():
    db = SessionLocal()
    
    try:
        print("="*80)
        print("TEST DE VELOCIDAD ACO OPTIMIZADO")
        print("="*80)
        
        start_time = time.time()
        
        # 1. Construir grafo
        print("\n1. Construyendo grafo...")
        builder = TimetableGraphBuilder(db)
        graph = builder.build_graph()
        
        graph_time = time.time() - start_time
        print(f"   Tiempo: {graph_time:.2f}s")
        
        # 2. Crear modelo
        print("\n2. Creando modelo GNN...")
        hidden_dim = 64
        device = torch.device('cpu')
        
        node_features_dict = {
            'section': graph['section'].x.shape[1],
            'professor': graph['professor'].x.shape[1],
            'classroom': graph['classroom'].x.shape[1],
            'timeslot': graph['timeslot'].x.shape[1],
            'curriculum': graph['curriculum'].x.shape[1],
        }
        
        model = ACOGraphSAGEModel(
            node_features_dict=node_features_dict,
            hidden_dim=hidden_dim,
            metadata=graph.metadata()
        ).to(device)
        
        model_time = time.time() - start_time - graph_time
        print(f"   Tiempo: {model_time:.2f}s")
        
        # 3. Preparar validadores
        print("\n3. Preparando validadores...")
        timeslots_dict = {}
        for ts in db.query(TimeSlot).all():
            timeslots_dict[ts.id] = TimeSlotInfo(
                id=ts.id,
                dia_semana=ts.dia_semana,
                hora_inicio=ts.hora_inicio,
                hora_fin=ts.hora_fin,
                periodo=ts.periodo,
                orden=ts.orden,
            )
        
        classrooms_dict = {}
        for cr in db.query(Classroom).all():
            classrooms_dict[cr.id] = ClassroomInfo(
                id=cr.id,
                codigo=cr.codigo,
                edificio=cr.edificio,
                capacidad=cr.capacidad,
                tipo=cr.tipo,
                tiene_computadoras=cr.tiene_computadoras,
            )
        
        day_map = {"Lunes": 1, "Martes": 2, "Miércoles": 3, "Miercoles": 3, "Jueves": 4, "Viernes": 5, "Sábado": 6, "Sabado": 6}
        professor_restrictions = {}
        for r in db.query(ProfessorRestriction).all():
            if r.professor_id not in professor_restrictions:
                professor_restrictions[r.professor_id] = []
            professor_restrictions[r.professor_id].append(
                ProfessorRestrictionInfo(
                    professor_id=r.professor_id,
                    dia_semana=day_map.get(r.day, 0),
                    hora_inicio=r.start_time,
                    hora_fin=r.end_time,
                )
            )
        
        validator = HardConstraintValidator(
            timeslots=timeslots_dict,
            classrooms=classrooms_dict,
            professor_restrictions=dict(professor_restrictions),
            sections_by_league=builder.sections_by_league,
        )
        
        soft_evaluator = SoftConstraintEvaluator(
            timeslots=timeslots_dict,
            classrooms=classrooms_dict,
        )
        
        validator_time = time.time() - start_time - graph_time - model_time
        print(f"   Tiempo: {validator_time:.2f}s")
        
        # 4. Ejecutar ACO con configuración rápida
        print("\n4. Ejecutando ACO (configuración rápida)...")
        quick_params = {
            "n_hormigas": 6,
            "n_iteraciones": 10,
            "alpha": 1.0,
            "beta": 2.3,
            "rho": 0.2,
            "q0": 0.88,
            "early_stopping_patience": 4,
            "max_candidate_combinations": 600,
            "max_professors_per_section": 6,
            "max_classrooms_per_section": 12,
            "max_timeslots_per_section": 12,
        }
        print(f"   Configuración: {quick_params['n_hormigas']} hormigas × {quick_params['n_iteraciones']} iteraciones")
        
        aco = ACOEngine(
            graph=graph,
            model=model,
            graph_builder=builder,
            hard_validator=validator,
            soft_evaluator=soft_evaluator,
            params=quick_params,
        )
        
        aco_start = time.time()
        best_solution = aco.optimize()
        aco_time = time.time() - aco_start
        
        total_time = time.time() - start_time
        
        print("\n" + "="*80)
        print("RESULTADOS DEL TEST DE VELOCIDAD")
        print("="*80)
        
        print(f"\nTiempos de ejecución:")
        print(f"  1. Construcción del grafo: {graph_time:.2f}s")
        print(f"  2. Creación del modelo: {model_time:.2f}s")
        print(f"  3. Preparación validadores: {validator_time:.2f}s")
        print(f"  4. Optimización ACO: {aco_time:.2f}s")
        print(f"  ─────────────────────────────")
        print(f"  TIEMPO TOTAL: {total_time:.2f}s ({total_time/60:.2f} minutos)")
        
        if best_solution:
            print(f"\nResultado:")
            print(f"  ✓ Secciones asignadas: {len(best_solution.assignments)}/300")
            print(f"  ✓ Costo: {best_solution.total_cost:.2f}")
            print(f"  ✓ Válida: {best_solution.is_valid}")
            print(f"  ✓ Iteraciones ejecutadas: {aco.completed_iterations}")
        else:
            print(f"\n  ✗ No se encontró solución")
        
        # Estimación para configuración completa
        estimated_full = (
            aco_time
            * (15 / max(1, quick_params["n_hormigas"]))
            * (100 / max(1, quick_params["n_iteraciones"]))
        )
        print(f"\nEstimación para configuración completa (15 hormigas × 100 iter):")
        print(f"  Tiempo estimado: {estimated_full:.2f}s ({estimated_full/60:.2f} minutos)")
        
        if estimated_full > 3600:
            print(f"  ⚠️  ADVERTENCIA: Tiempo estimado > 1 hora")
        elif estimated_full > 1800:
            print(f"  ⚠️  Tiempo estimado alto (> 30 minutos)")
        else:
            print(f"  ✓ Tiempo estimado aceptable")
        
    finally:
        db.close()

if __name__ == "__main__":
    main()
