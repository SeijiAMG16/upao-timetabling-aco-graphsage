"""
Script para ejecutar ACO completo y generar horario optimizado

Este script ejecuta el algoritmo de Colonia de Hormigas con GraphSAGE
para generar un horario completo optimizado.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import random
import numpy as np
import torch
import json
from datetime import datetime
from app.database import SessionLocal
from app.aco_graphsage.pipeline import TimetablePipeline
from app.aco_graphsage.aco_engine import create_aco_engine

# Fijar semillas para reproducibilidad
SEED = 42
torch.manual_seed(SEED)
np.random.seed(SEED)
random.seed(SEED)

def main():
    session = SessionLocal()
    try:
        print("="*80)
        print("GENERACION DE HORARIO COMPLETO - ACO + GRAPHSAGE")
        print("="*80)
        print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Semilla aleatoria: {SEED}")
        
        # Preparar pipeline
        print("\n1. Preparando pipeline...")
        print("-"*80)
        pipeline = TimetablePipeline(session)
        pipeline.prepare()
        pipeline.model.eval()

        # Configuración ACO optimizada
        print("\n2. Configurando parametros ACO...")
        print("-"*80)
        params = {
            # Parámetros básicos ACO - OPTIMIZADOS URGENTEMENTE
            "n_hormigas": 3,            # REDUCIDO de 15 a 3 para velocidad
            "n_iteraciones": 2,         # REDUCIDO de 5 a 2 para velocidad
            "alpha": 1.0,               # Peso de feromona
            "beta": 3.5,                # Peso de heurística neural (más peso)
            "rho": 0.12,                # Evaporación de feromona ligeramente mayor
            
            # GRUPOS PRIORITARIOS - Cursos con restricciones severas
            # Estos grupos se asignan PRIMERO para asegurar disponibilidad de recursos
            "priority_course_groups": [
                # Cursos con alta demanda de estudiantes (necesitan aulas grandes)
                ("CIEN768", 3),   # Física I Liga 3: 58 estudiantes - PRACTICA
                ("CIEN754", 1),   # Cálculo II Liga 1: 53 estudiantes - PRACTICA  
                ("HUMA900", 2),   # Metodología Liga 2: 40 estudiantes - PRACTICA
                ("CIEN755", 1),   # Cálculo III Liga 1: 35 estudiantes - PRACTICA
                ("CIEN755", 2),   # Cálculo III Liga 2: 34 estudiantes - PRACTICA
                
                # Laboratorios que necesitan aulas especializadas
                ("CIEN769", 1),   # Física II Liga 1: 28 est - LABORATORIO (incluye 1629, 1630, 1631)
                ("ICSI509", 2),   # POO Liga 2: 17 est - LABORATORIOS (1608-1610)
                ("ICSI509", 3),   # POO Liga 3: 17 est - LABORATORIOS (1611-1613)
                ("ICSI506", 1),   # Algoritmia Liga 1: 16 est - LABORATORIOS (1550-1552)
                ("ICSI506", 2),   # Algoritmia Liga 2: 16 est - LABORATORIOS (1553-1554)
            ],
            
            # Parámetros MMAS
            "tau_max": 1.0,
            "tau_min": 0.01,
            "q0": 0.9,                  # Probabilidad de explotación vs exploración
            
            # Límites de candidatos (optimización)
            "shuffle_candidates": True,
            "max_timeslots_per_section": 96,  # AUMENTADO: Permitir todos los timeslots (96 total)
            "max_candidate_combinations": 3000,  # AUMENTADO: Más combinaciones para explorar
            "max_professors_per_section": 50,
            "max_classrooms_per_section": 50,
            
            # Early stopping
            "early_stopping_patience": 8,  # REDUCIDO: Detener más rápido si no mejora
            
            # Prioridades especiales
            "priority_course_groups": [("CIEN769", 1)],  # Grupos que se asignan primero
            
            # Debug (opcional, deshabilitar para producción)
            "debug_sections": [],  # Sin debug para ejecución rápida
        }
        
        print(f"  Hormigas: {params['n_hormigas']}")
        print(f"  Iteraciones máximas: {params['n_iteraciones']}")
        print(f"  Alpha (feromona): {params['alpha']}")
        print(f"  Beta (heurística): {params['beta']}")
        print(f"  Rho (evaporación): {params['rho']}")
        print(f"  Q0 (explotación): {params['q0']}")
        print(f"  Grupos prioritarios: {params['priority_course_groups']}")

        print("\n3. Creando motor ACO...")
        print("-"*80)
        engine = create_aco_engine(
            graph=pipeline.graph,
            model=pipeline.model,
            graph_builder=pipeline.graph_builder,
            db_session=session,
            params=params,
        )

        print("\n4. Ejecutando optimización ACO...")
        print("="*80)
        best_solution = engine.optimize()

        print("\n" + "="*80)
        print("5. RESULTADOS FINALES")
        print("="*80)
        
        if best_solution is None or not best_solution.is_valid:
            print("❌ No se pudo generar una solución válida")
            return
        
        print(f"✅ Solución válida encontrada")
        print(f"   Total de asignaciones: {len(best_solution.assignments)}")
        print(f"   Costo total: {best_solution.total_cost:.2f}")
        print(f"   Iteraciones completadas: {engine.completed_iterations}")
        
        # Mostrar penalizaciones por categoría
        print(f"\n📊 Penalizaciones por categoría:")
        for category, penalty in sorted(best_solution.soft_penalties.items()):
            print(f"   {category}: {penalty:.2f}")
        
        # Verificar asignación de sección 1631
        section_1631 = None
        for assignment in best_solution.assignments:
            if assignment.section_id == 1631:
                section_1631 = assignment
                break
        
        if section_1631:
            print(f"\n✅ VERIFICACIÓN: Sección 1631 (CIEN769 LAB) asignada")
            from app.models import Classroom, Professor
            aula = session.query(Classroom).filter_by(id=section_1631.classroom_id).first()
            profesor = session.query(Professor).filter_by(id=section_1631.professor_id).first()
            print(f"   Profesor: {profesor.nombre_completo if profesor else 'N/A'}")
            print(f"   Aula: {aula.codigo if aula else 'N/A'} (capacidad {aula.capacidad if aula else 'N/A'})")
            print(f"   Franjas horarias: {section_1631.timeslot_ids}")
        else:
            print(f"\n⚠️  ADVERTENCIA: Sección 1631 NO fue asignada")
        
        # Guardar resultados
        print(f"\n6. Guardando resultados...")
        print("-"*80)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"horario_generado_{timestamp}.json"
        
        # Convertir a formato serializable
        result_data = {
            "metadata": {
                "fecha_generacion": datetime.now().isoformat(),
                "algoritmo": "ACO + GraphSAGE",
                "semilla": SEED,
                "iteraciones_completadas": engine.completed_iterations,
                "parametros": params,
            },
            "solucion": {
                "valida": best_solution.is_valid,
                "costo_total": best_solution.total_cost,
                "penalizaciones": best_solution.soft_penalties,
                "num_asignaciones": len(best_solution.assignments),
            },
            "asignaciones": []
        }
        
        for assignment in best_solution.assignments:
            result_data["asignaciones"].append({
                "section_id": assignment.section_id,
                "course_code": assignment.course_code,
                "session_type": assignment.session_type,
                "league_id": assignment.league_id,
                "ciclo": assignment.ciclo,
                "professor_id": assignment.professor_id,
                "classroom_id": assignment.classroom_id,
                "timeslot_ids": assignment.timeslot_ids,
                "alumnos_proyectados": assignment.alumnos_proyectados,
            })
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Resultados guardados en: {output_file}")
        
        # Estadísticas adicionales
        print(f"\n7. Estadísticas adicionales")
        print("-"*80)
        
        # Curvas de convergencia
        if engine.iteration_best:
            print(f"   Mejor costo inicial: {engine.iteration_best[0]:.2f}")
            print(f"   Mejor costo final: {engine.iteration_best[-1]:.2f}")
            print(f"   Mejora total: {((engine.iteration_best[0] - engine.iteration_best[-1]) / engine.iteration_best[0] * 100):.1f}%")
        
        # Distribución por edificio
        edificio_count = {}
        for assignment in best_solution.assignments:
            from app.models import Classroom
            aula = session.query(Classroom).filter_by(id=assignment.classroom_id).first()
            if aula:
                edificio = aula.edificio
                edificio_count[edificio] = edificio_count.get(edificio, 0) + 1
        
        print(f"\n   Distribución de asignaciones por edificio:")
        for edificio, count in sorted(edificio_count.items()):
            print(f"     Edificio {edificio}: {count} asignaciones")
        
        print(f"\n{'='*80}")
        print(f"✅ GENERACIÓN DE HORARIO COMPLETADA EXITOSAMENTE")
        print(f"{'='*80}\n")
        
    except Exception as e:
        print(f"\n❌ ERROR durante la ejecución:")
        print(f"   {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    main()
