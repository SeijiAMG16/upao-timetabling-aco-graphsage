"""Script para probar la asignación de la sección 1631 con prioridad"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import random
import numpy as np
import torch
from app.database import SessionLocal
from app.aco_graphsage.pipeline import TimetablePipeline
from app.aco_graphsage.aco_engine import create_aco_engine

# Fijar semillas para reproducibilidad
torch.manual_seed(42)
np.random.seed(42)
random.seed(42)

def main():
    session = SessionLocal()
    try:
        print("="*80)
        print("PRUEBA DE ASIGNACION - SECCION 1631 CON PRIORIDAD")
        print("="*80)
        
        # Preparar pipeline
        print("\nPreparando pipeline...")
        pipeline = TimetablePipeline(session)
        pipeline.prepare()
        pipeline.model.eval()

        # Configurar ACO con pocas iteraciones para prueba rápida
        params = {
            "n_hormigas": 3,
            "n_iteraciones": 1,
            "alpha": 1.0,
            "beta": 3.0,
            "rho": 0.1,
            "q0": 0.9,
            "shuffle_candidates": False,
            "max_timeslots_per_section": 48,
            "max_candidate_combinations": 1200,
            "max_professors_per_section": 50,
            "max_classrooms_per_section": 50,
            "debug_sections": [1631],  # Debug solo sección 1631
        }

        print("\nCreando motor ACO...")
        engine = create_aco_engine(
            graph=pipeline.graph,
            model=pipeline.model,
            graph_builder=pipeline.graph_builder,
            db_session=session,
            params=params,
        )

        print("\nEjecutando construcción de solución...")
        print("-"*80)
        solution = engine._construct_solution(0, 0)

        print("\n" + "="*80)
        print("RESULTADOS")
        print("="*80)
        print(f"Solución válida: {solution.is_valid}")
        print(f"Total asignaciones: {len(solution.assignments)}")
        
        # Buscar específicamente la sección 1631
        seccion_1631 = None
        for assignment in solution.assignments:
            if assignment.section_id == 1631:
                seccion_1631 = assignment
                break
        
        if seccion_1631:
            print(f"\n✅ SECCION 1631 ASIGNADA!")
            print(f"  Profesor: {seccion_1631.professor_id}")
            print(f"  Aula: {seccion_1631.classroom_id}")
            print(f"  Franjas horarias: {seccion_1631.timeslot_ids}")
            
            # Obtener detalles del aula
            from app.models import Classroom
            aula = session.query(Classroom).filter_by(id=seccion_1631.classroom_id).first()
            if aula:
                print(f"  Aula nombre: {aula.codigo}")
                print(f"  Capacidad: {aula.capacidad}")
                print(f"  Tipo: {aula.tipo}")
        else:
            print(f"\n❌ SECCION 1631 NO FUE ASIGNADA")
            print("\nRevisando logs de construcción...")
            if hasattr(solution, 'construction_log'):
                for log in solution.construction_log:
                    if '1631' in str(log):
                        print(f"  {log}")
        
        # Mostrar primeras asignaciones para ver el orden
        print(f"\n" + "="*80)
        print("PRIMERAS 10 ASIGNACIONES (verificar orden de prioridad)")
        print("="*80)
        for i, assignment in enumerate(solution.assignments[:10]):
            marker = " <-- SECCION 1631" if assignment.section_id == 1631 else ""
            print(f"{i+1}. Sección {assignment.section_id}: "
                  f"Prof {assignment.professor_id}, "
                  f"Aula {assignment.classroom_id}{marker}")
        
    finally:
        session.close()

if __name__ == "__main__":
    main()
