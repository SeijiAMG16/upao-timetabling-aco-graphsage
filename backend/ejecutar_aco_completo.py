"""
Script para ejecutar ACO+GraphSAGE con la BD completa
y generar métricas de progreso
"""

import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from app.database import SessionLocal
from app.aco_graphsage.graph_builder import TimetableGraphBuilder
from app.aco_graphsage.graphsage_model import ACOGraphSAGEModel
from app.aco_graphsage.aco_engine import ACOEngine
from app.aco_graphsage.constraints import HardConstraintValidator, SoftConstraintEvaluator
import torch


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ejecuta el motor ACO+GraphSAGE sobre la BD completa.",
        epilog="Ejemplo: python ejecutar_aco_completo.py --hormigas 40 --iteraciones 150 --max-timeslots 24 --debug 1554,1598",
    )
    parser.add_argument("--hormigas", type=int, default=10, help="Número de hormigas por iteración.")
    parser.add_argument("--iteraciones", type=int, default=50, help="Número máximo de iteraciones ACO.")
    parser.add_argument("--alpha", type=float, default=1.0, help="Peso de feromona.")
    parser.add_argument("--beta", type=float, default=2.3, help="Peso de heurística neural.")
    parser.add_argument("--rho", type=float, default=0.2, help="Tasa de evaporación de feromona.")
    parser.add_argument("--q0", type=float, default=0.88, help="Probabilidad de explotación directa.")
    parser.add_argument("--patiencia", type=int, default=6, help="Iteraciones sin mejora antes de early stopping.")
    parser.add_argument("--max-candidatos", type=int, default=600, help="Número máximo de combinaciones candidato por sección.")
    parser.add_argument("--max-profesores", type=int, default=6, help="Profesores máximos a considerar por sección.")
    parser.add_argument("--max-aulas", type=int, default=12, help="Aulas máximas a considerar por sección.")
    parser.add_argument("--max-timeslots", type=int, default=12, help="Franjas de inicio máximas por sección (antes de escalar por duración).")
    parser.add_argument("--debug", type=str, default="", help="Lista separada por comas de IDs de sección a depurar.")
    parser.add_argument("--log-limit", type=int, default=200, help="Máximo de líneas de log por sección depurada.")
    parser.add_argument("--sin-early", action="store_true", help="Desactiva el early stopping por falta de mejoras.")
    return parser.parse_args()


def main():
    args = parse_args()
    db = SessionLocal()
    
    try:
        print("="*80)
        print("EJECUCIÓN COMPLETA ACO+GraphSAGE")
        print("="*80)
        
        # 1. Construir grafo
        print("\n1. Construyendo grafo...")
        builder = TimetableGraphBuilder(db)
        graph = builder.build_graph()
        
        print(f"\nGrafo construido:")
        print(f"  Secciones: {graph['section'].x.shape[0]}")
        print(f"  Profesores: {graph['professor'].x.shape[0]}")
        print(f"  Aulas: {graph['classroom'].x.shape[0]}")
        print(f"  Franjas: {graph['timeslot'].x.shape[0]}")
        print(f"  Currículos: {graph['curriculum'].x.shape[0]}")
        print(f"\nAristas:")
        print(f"  section->professor: {graph['section', 'assigned_to', 'professor'].edge_index.shape[1]}")
        print(f"  section->classroom: {graph['section', 'uses', 'classroom'].edge_index.shape[1]}")
        print(f"  section->timeslot: {graph['section', 'starts_at', 'timeslot'].edge_index.shape[1]}")
        
        # 2. Crear modelo GNN
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
        
        print(f"  Modelo creado con hidden_dim={hidden_dim}")
        
        # 3. Crear validador
        print("\n3. Creando validador de restricciones...")
        
        # Cargar datos necesarios para el validador
        from app.models import TimeSlot, Classroom, ProfessorRestriction
        from app.aco_graphsage.constraints import TimeSlotInfo, ClassroomInfo, ProfessorRestrictionInfo
        
        # Convertir TimeSlots a diccionario
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
        
        # Convertir Classrooms a diccionario
        classrooms_dict = {}
        for cr in db.query(Classroom).all():
            classrooms_dict[cr.id] = ClassroomInfo(
                id=cr.id,
                codigo=cr.codigo,
                edificio=cr.edificio,
                capacidad=cr.capacidad,
                tipo=builder._normalize_classroom_type(cr.tipo),
                tiene_computadoras=cr.tiene_computadoras,
            )
        
        # Mapeo de restricciones de profesores
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
            league_session_types=builder.league_session_types,
            section_session_types=builder.section_session_types,
            sections_by_block=builder.sections_by_block,
        )
        
        # 4. Crear evaluador de restricciones suaves
        print("\n4. Creando evaluador de restricciones suaves...")
        
        soft_evaluator = SoftConstraintEvaluator(
            timeslots=timeslots_dict,
            classrooms=classrooms_dict,
        )
        
        # 5. Crear motor ACO
        print("\n5. Configurando ACO...")

        debug_sections = []
        if args.debug:
            debug_sections = [int(value) for value in args.debug.split(",") if value.strip().isdigit()]

        early_patience = float("inf") if args.sin_early else max(0, args.patiencia)

        run_params = {
            "n_hormigas": args.hormigas,
            "n_iteraciones": args.iteraciones,
            "alpha": args.alpha,
            "beta": args.beta,
            "rho": args.rho,
            "q0": args.q0,
            "early_stopping_patience": early_patience,
            "max_candidate_combinations": max(1, args.max_candidatos) if args.max_candidatos else None,
            "max_professors_per_section": max(1, args.max_profesores) if args.max_profesores else None,
            "max_classrooms_per_section": max(1, args.max_aulas) if args.max_aulas else None,
            "max_timeslots_per_section": max(1, args.max_timeslots) if args.max_timeslots else None,
            "debug_sections": debug_sections,
            "debug_log_limit": max(20, args.log_limit),
        }
        aco = ACOEngine(
            graph=graph,
            model=model,
            graph_builder=builder,
            hard_validator=validator,
            soft_evaluator=soft_evaluator,
            params=run_params,
        )
        
        print(f"  Hormigas: {aco.n_hormigas}")
        print(f"  Iteraciones máximas: {aco.n_iteraciones}")
        if args.sin_early:
            print("  Early stopping: No")
        else:
            print(f"  Early stopping: Sí (sin mejora en {run_params['early_stopping_patience']} iteraciones)")
        print(f"  Validación con caché: Activada")
        print(f"  Alpha (feromona): {aco.alpha}")
        print(f"  Beta (heurística): {aco.beta}")
        print(f"  Rho (evaporación): {aco.rho}")
        print(f"  Q0 (exploración vs explotación): {aco.q0}")
        if run_params["max_candidate_combinations"]:
            print(f"  Candidatos máx. por sección: {run_params['max_candidate_combinations']}")
        else:
            print("  Candidatos máx. por sección: sin límite adicional")
        if debug_sections:
            print(f"  Secciones en modo depuración: {debug_sections}")
        
        # 6. Ejecutar optimización
        print("\n" + "="*80)
        print("INICIANDO OPTIMIZACIÓN")
        print("="*80)
        
        best_solution = aco.optimize()
        
        # 6. Analizar resultados
        print("\n" + "="*80)
        print("RESULTADOS")
        print("="*80)
        
        if best_solution:
            print(f"\n✓ Mejor solución encontrada:")
            print(f"  Secciones asignadas: {len(best_solution.assignments)}/{graph['section'].x.shape[0]}")
            print(f"  Costo soft: {best_solution.total_cost:.2f}")
            print(f"  Solución válida: {best_solution.is_valid}")
            
            if not best_solution.is_valid:
                print(f"\n⚠ Solución con violaciones de restricciones duras")
                print(f"\nLog de construcción:")
                for log_entry in best_solution.construction_log[-10:]:  # Últimas 10 entradas
                    print(f"  {log_entry}")
            
            # Guardar resultados en archivo JSON
            import json
            from datetime import datetime
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"horario_generado_{timestamp}.json"
            
            # Convertir assignments a formato serializable
            horario_data = {
                "metadata": {
                    "timestamp": timestamp,
                    "total_secciones": len(best_solution.assignments),
                    "costo_total": best_solution.total_cost,
                    "es_valida": best_solution.is_valid,
                    "penalizaciones": best_solution.soft_penalties
                },
                "asignaciones": []
            }
            
            sorted_assignments = sorted(
                best_solution.assignments,
                key=lambda a: (
                    a.professor_id,
                    min(a.timeslot_ids) if a.timeslot_ids else 0,
                    a.section_id,
                ),
            )
            for assignment in sorted_assignments:
                horario_data["asignaciones"].append({
                    "section_id": assignment.section_id,
                    "course_code": assignment.course_code,
                    "session_type": assignment.session_type,
                    "league_id": assignment.league_id,
                    "ciclo": assignment.ciclo,
                    "professor_id": assignment.professor_id,
                    "classroom_id": assignment.classroom_id,
                    "timeslot_ids": assignment.timeslot_ids,
                    "alumnos_proyectados": assignment.alumnos_proyectados
                })
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(horario_data, f, indent=2, ensure_ascii=False)
            
            print(f"\n💾 Horario guardado en: {output_file}")
            
            # También guardar en CSV para Excel
            import csv
            csv_file = f"horario_generado_{timestamp}.csv"
            
            with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'Section ID', 'Codigo Curso', 'Tipo Sesion', 'Liga', 'Ciclo',
                    'Profesor ID', 'Aula ID', 'Franjas Horarias', 'Alumnos Proyectados'
                ])
                
                for assignment in sorted_assignments:
                    writer.writerow([
                        assignment.section_id,
                        assignment.course_code,
                        assignment.session_type,
                        assignment.league_id,
                        assignment.ciclo,
                        assignment.professor_id,
                        assignment.classroom_id,
                        ','.join(map(str, assignment.timeslot_ids)),
                        assignment.alumnos_proyectados
                    ])
            
            print(f"📊 Horario guardado en CSV: {csv_file}")
        else:
            print("\n❌ No se encontró ninguna solución")
        
        print(f"\n📊 Métricas de ejecución:")
        print(f"  Mejor solución ACO: {best_solution is not None}")
        print(f"  Iteraciones completadas: {aco.completed_iterations}")
        
        # 7. Análisis de candidatos
        print("\n" + "="*80)
        print("ANÁLISIS DE CANDIDATOS")
        print("="*80)
        
        if hasattr(builder, 'section_candidate_stats'):
            print("\nEstadísticas de candidatos por sección:")
            
            # Encontrar secciones problemáticas
            problematic = []
            for section_id, stats in builder.section_candidate_stats.items():
                total = stats.get('professors', 0) * stats.get('classrooms', 0) * stats.get('timeslots', 0)
                if total < 100:  # Menos de 100 combinaciones posibles
                    problematic.append((section_id, stats, total))
            
            if problematic:
                print(f"\n⚠ {len(problematic)} secciones con pocos candidatos:")
                # Ordenar por total de candidatos
                problematic.sort(key=lambda x: x[2])
                for section_id, stats, total in problematic[:10]:  # Top 10
                    metadata = builder.section_metadata.get(section_id, {})
                    print(f"\n  Sección {section_id}:")
                    print(f"    Curso: {metadata.get('course_code', 'N/A')}")
                    print(f"    Tipo: {metadata.get('session_type', 'N/A')}")
                    print(f"    Liga: {metadata.get('league', 'N/A')}")
                    print(f"    Profesores: {stats.get('professors', 0)}")
                    print(f"    Aulas: {stats.get('classrooms', 0)}")
                    print(f"    Franjas: {stats.get('timeslots', 0)}")
                    print(f"    Total candidatos: {total}")
            else:
                print("\n✓ Todas las secciones tienen suficientes candidatos")
        
    finally:
        db.close()

if __name__ == "__main__":
    main()
