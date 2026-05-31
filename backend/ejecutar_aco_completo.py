"""
Script para ejecutar ACO+GraphSAGE con la BD completa
y generar métricas de progreso
"""

print("[DEBUG] Script iniciado - imports comenzando...")

import argparse
import sys
import time
from pathlib import Path
from datetime import timedelta, time as datetime_time

print("[DEBUG] Imports básicos completados")

sys.path.append(str(Path(__file__).parent))

print("[DEBUG] Importando módulos de la aplicación...")
from app.database import SessionLocal
from app.models import AlgorithmExecution
print("[DEBUG] - SessionLocal y AlgorithmExecution importados")

# Check if PyTorch is available
TORCH_AVAILABLE = False
try:
    import torch
    TORCH_AVAILABLE = True
    print("[DEBUG] - Torch disponible")
except ImportError:
    print("[DEBUG] - Torch NO disponible, usando ACO básico")

if TORCH_AVAILABLE:
    from app.aco_graphsage.graph_builder import TimetableGraphBuilder
    print("[DEBUG] - TimetableGraphBuilder importado")
    from app.aco_graphsage.graphsage_model import ACOGraphSAGEModel
    print("[DEBUG] - ACOGraphSAGEModel importado")
    from app.aco_graphsage.aco_engine import ACOEngine
    print("[DEBUG] - ACOEngine importado")
    from app.aco_graphsage.constraints import HardConstraintValidator, SoftConstraintEvaluator
    print("[DEBUG] - Constraints importados")
    print("[DEBUG] [OK] Todos los imports completados!")
else:
    # Imports para ACO básico sin PyTorch
    print("[DEBUG] Usando modo ACO básico sin GraphSAGE")
    print("[DEBUG] [OK] Imports básicos completados!")


def run_basic_aco():
    """
    Ejecuta una versión básica que usa las asignaciones existentes en la BD.
    Esta función se usa cuando PyTorch no está disponible.
    """
    import json
    from datetime import datetime
    
    print("\n" + "="*80)
    print("MODO BÁSICO - Usando asignaciones existentes de la BD")
    print("="*80)
    
    db = SessionLocal()
    try:
        # Importar modelos
        from app.models import ScheduleAssignment, CourseSection, Course, Professor, Classroom, TimeSlot
        
        # Obtener asignaciones existentes (compatibilidad con esquemas antiguos/nuevos)
        query = db.query(ScheduleAssignment)
        if hasattr(ScheduleAssignment, "active"):
            query = query.filter(ScheduleAssignment.active == True)
        elif hasattr(ScheduleAssignment, "estado"):
            query = query.filter(ScheduleAssignment.estado != "cancelado")
        assignments = query.all()
        
        print(f"\n[OK] Se encontraron {len(assignments)} asignaciones activas en la BD")
        
        if len(assignments) == 0:
            print("\n[WARN] No hay asignaciones en la base de datos.")
            print("   Por favor, cree asignaciones manualmente o ejecute el algoritmo localmente.")
            return
        
        # Crear estructura de horario para exportar
        horario_data = []
        
        for a in assignments:
            section_id = getattr(a, "section_id", None) or getattr(a, "course_section_id", None)
            section = db.query(CourseSection).filter(CourseSection.id == section_id).first() if section_id else None
            if not section:
                continue
                
            course_id = getattr(a, "course_id", None) or getattr(section, "course_id", None)
            course = db.query(Course).filter(Course.id == course_id).first() if course_id else None
            professor = db.query(Professor).filter(Professor.id == a.professor_id).first() if getattr(a, "professor_id", None) else None
            classroom = db.query(Classroom).filter(Classroom.id == a.classroom_id).first() if getattr(a, "classroom_id", None) else None
            timeslot = db.query(TimeSlot).filter(TimeSlot.id == a.time_slot_id).first() if getattr(a, "time_slot_id", None) else None
            
            horario_data.append({
                "section_id": section_id,
                "nrc": getattr(section, "nrc", None),
                "course_code": course.codigo if course else "N/A",
                "course_name": course.nombre if course else "N/A",
                "session_type": getattr(section, "tipo", "N/A"),
                "section": getattr(section, "seccion", "N/A"),
                "professor_id": getattr(a, "professor_id", None),
                "professor_name": professor.nombre_completo if professor else "Sin asignar",
                "classroom_id": getattr(a, "classroom_id", None),
                "classroom_code": classroom.codigo if classroom else "Sin asignar",
                "timeslot_id": getattr(a, "time_slot_id", None),
                "day": timeslot.dia_semana if timeslot else "N/A",
                "start_time": str(timeslot.hora_inicio) if timeslot else "N/A",
                "end_time": str(timeslot.hora_fin) if timeslot else "N/A",
            })
        
        # Guardar JSON
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"horario_generado_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(horario_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n[FILE] Horario exportado a: {output_file}")
        print(f"   Total de asignaciones: {len(horario_data)}")
        
        # Estadísticas
        with_professor = sum(1 for h in horario_data if h['professor_id'])
        with_classroom = sum(1 for h in horario_data if h['classroom_id'])
        with_timeslot = sum(1 for h in horario_data if h['timeslot_id'])
        
        print(f"\n   Con profesor asignado: {with_professor}")
        print(f"   Con aula asignada: {with_classroom}")
        print(f"   Con horario asignado: {with_timeslot}")
        
        print("\n" + "="*80)
        print("[OK] EXPORTACIÓN COMPLETADA")
        print("="*80)
        
    finally:
        db.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ejecuta el motor ACO+GraphSAGE sobre la BD completa.",
        epilog="Ejemplo: python ejecutar_aco_completo.py --hormigas 40 --iteraciones 150 --max-timeslots 24 --debug 1554,1598",
    )
    parser.add_argument("--hormigas", type=int, default=10, help="Número de hormigas por iteración.")
    parser.add_argument("--iteraciones", type=int, default=4, help="Número máximo de iteraciones ACO.")
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
    parser.add_argument("--verbose", action="store_true", help="Muestra logs detallados de construcción de soluciones.")
    parser.add_argument("--model-path", type=str, default="", help="Ruta de un modelo preentrenado (.pt) a cargar.")
    return parser.parse_args()


def main():
    print("[DEBUG] main() iniciada")
    start_time_exec = time.time()
    
    # Si PyTorch no está disponible, usar generador básico
    if not TORCH_AVAILABLE:
        print("="*80)
        print("    [WARN] PyTorch no está instalado")
        print("    La generación de horarios con ACO+GraphSAGE no está disponible")
        print("    Por favor, use la funcionalidad básica del sistema")
        print("="*80)
        # Salir con código 0 para indicar que no es un error fatal
        # pero mostrar mensaje informativo
        return run_basic_aco()
    
    args = parse_args()
    print(f"[DEBUG] Argumentos parseados: hormigas={args.hormigas}, iteraciones={args.iteraciones}")
    
    print("[DEBUG] Creando sesión de base de datos...")
    db = SessionLocal()
    print("[DEBUG] [OK] Sesión de BD creada")
    
    try:
        print("="*80)
        print("EJECUCIÓN COMPLETA ACO+GraphSAGE")
        print("="*80)
        
        # 1. Construir grafo
        print("\n1. Construyendo grafo...")
        print("   [DEBUG] Inicializando TimetableGraphBuilder...")
        builder = TimetableGraphBuilder(db)
        print("   [DEBUG] Llamando a build_graph()...")
        graph = builder.build_graph()
        print("   [DEBUG] [OK] Grafo construido exitosamente!")
        
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
        print("   [DEBUG] Calculando dimensiones de características...")
        hidden_dim = 64
        device = torch.device('cpu')
        
        node_features_dict = {
            'section': graph['section'].x.shape[1],
            'professor': graph['professor'].x.shape[1],
            'classroom': graph['classroom'].x.shape[1],
            'timeslot': graph['timeslot'].x.shape[1],
            'curriculum': graph['curriculum'].x.shape[1],
        }
        
        print("   [DEBUG] Inicializando ACOGraphSAGEModel...")
        model = ACOGraphSAGEModel(
            node_features_dict=node_features_dict,
            hidden_dim=hidden_dim,
            metadata=graph.metadata()
        ).to(device)
        if args.model_path:
            try:
                checkpoint = torch.load(args.model_path, map_location=device)
                state_dict = checkpoint.get("model_state_dict", checkpoint)
                model.load_state_dict(state_dict)
                print(f"   [DEBUG] [OK] Pesos del modelo precargados exitosamente desde {args.model_path}")
            except Exception as e:
                print(f"   [ERROR] No se pudo cargar el modelo desde {args.model_path}: {e}")
                print("   [DEBUG] Continuando con pesos inicializados al azar.")
        
        print(f"  Modelo creado con hidden_dim={hidden_dim}")
        print("   [DEBUG] Modelo GNN listo!")
        
        # 3. Crear validador
        print("\n3. Creando validador de restricciones...")
        
        # Cargar datos necesarios para el validador
        from app.models import TimeSlot, Classroom, ProfessorRestriction
        from app.aco_graphsage.constraints import TimeSlotInfo, ClassroomInfo, ProfessorRestrictionInfo
        
        # Convertir TimeSlots a diccionario
        timeslots_dict = {}
        for ts in db.query(TimeSlot).all():
            # Convertir hora_inicio y hora_fin a datetime.time
            # Puede venir como timedelta (desde BD) o como string (desde modelo)
            if isinstance(ts.hora_inicio, timedelta):
                total_seconds = int(ts.hora_inicio.total_seconds())
                hora_inicio = datetime_time(hour=total_seconds // 3600, minute=(total_seconds % 3600) // 60)
            elif isinstance(ts.hora_inicio, str):
                # Parse "HH:MM" string
                parts = ts.hora_inicio.split(':')
                hora_inicio = datetime_time(hour=int(parts[0]), minute=int(parts[1]))
            else:
                hora_inicio = ts.hora_inicio
            
            if isinstance(ts.hora_fin, timedelta):
                total_seconds = int(ts.hora_fin.total_seconds())
                hora_fin = datetime_time(hour=total_seconds // 3600, minute=(total_seconds % 3600) // 60)
            elif isinstance(ts.hora_fin, str):
                # Parse "HH:MM" string
                parts = ts.hora_fin.split(':')
                hora_fin = datetime_time(hour=int(parts[0]), minute=int(parts[1]))
            else:
                hora_fin = ts.hora_fin
            
            timeslots_dict[ts.id] = TimeSlotInfo(
                id=ts.id,
                dia_semana=ts.dia_semana,
                hora_inicio=hora_inicio,
                hora_fin=hora_fin,
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
        # IMPORTANTE: La BD usa ENUM con TODO EN MAYÚSCULAS
        day_map = {
            "LUNES": 1, "Lunes": 1, "lunes": 1,
            "MARTES": 2, "Martes": 2, "martes": 2,
            "MIÉRCOLES": 3, "MIERCOLES": 3, "Miércoles": 3, "Miercoles": 3, "miércoles": 3, "miercoles": 3,
            "JUEVES": 4, "Jueves": 4, "jueves": 4,
            "VIERNES": 5, "Viernes": 5, "viernes": 5,
            "SÁBADO": 6, "SABADO": 6, "Sábado": 6, "Sabado": 6, "sábado": 6, "sabado": 6,
            "DOMINGO": 7, "Domingo": 7, "domingo": 7,
        }
        professor_restrictions = {}
        for r in db.query(ProfessorRestriction).all():
            if r.professor_id not in professor_restrictions:
                professor_restrictions[r.professor_id] = []
            dia_num = day_map.get(r.day, 0)
            if dia_num == 0:
                print(f"  [WARN] WARNING: Día no reconocido '{r.day}' para profesor ID={r.professor_id}")
            
            # Convertir timedelta a time si es necesario
            if isinstance(r.start_time, timedelta):
                total_seconds = int(r.start_time.total_seconds())
                hora_inicio = datetime_time(hour=total_seconds // 3600, minute=(total_seconds % 3600) // 60)
            else:
                hora_inicio = r.start_time
            
            if isinstance(r.end_time, timedelta):
                total_seconds = int(r.end_time.total_seconds())
                hora_fin = datetime_time(hour=total_seconds // 3600, minute=(total_seconds % 3600) // 60)
            else:
                hora_fin = r.end_time
            
            professor_restrictions[r.professor_id].append(
                ProfessorRestrictionInfo(
                    professor_id=r.professor_id,
                    dia_semana=dia_num,
                    hora_inicio=hora_inicio,
                    hora_fin=hora_fin,
                )
            )
        
        # Log de restricciones cargadas
        total_restricciones = sum(len(rest) for rest in professor_restrictions.values())
        print(f"  >> Cargadas {total_restricciones} restricciones para {len(professor_restrictions)} profesores")
        
        # Debug: verificar tipos de datos
        if timeslots_dict and professor_restrictions:
            sample_ts = next(iter(timeslots_dict.values()))
            print(f"  DEBUG: TimeSlot hora_inicio type = {type(sample_ts.hora_inicio)}, value = {sample_ts.hora_inicio}")
            if professor_restrictions:
                sample_prof_id = next(iter(professor_restrictions.keys()))
                sample_restriction = professor_restrictions[sample_prof_id][0]
                print(f"  DEBUG: Restriction hora_inicio type = {type(sample_restriction.hora_inicio)}, value = {sample_restriction.hora_inicio}")
        
        validator = HardConstraintValidator(
            timeslots=timeslots_dict,
            classrooms=classrooms_dict,
            professor_restrictions=dict(professor_restrictions),
            sections_by_league=builder.sections_by_league,
            league_session_types=builder.league_session_types,
            section_session_types=builder.section_session_types,
            sections_by_block=builder.sections_by_block,
            section_modalities=builder.section_modalities,
        )
        
        # 4. Crear evaluador de restricciones suaves
        print("\n4. Creando evaluador de restricciones suaves...")
        
        soft_evaluator = SoftConstraintEvaluator(
            timeslots=timeslots_dict,
            classrooms=classrooms_dict,
            professor_restrictions=dict(professor_restrictions),
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
            "verbose": args.verbose,  # Nuevo parámetro
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
            print(f"\n[OK] Mejor solución encontrada:")
            print(f"  Secciones asignadas: {len(best_solution.assignments)}/{graph['section'].x.shape[0]}")
            print(f"  Costo soft: {best_solution.total_cost:.2f}")
            print(f"  Solución válida: {best_solution.is_valid}")
            
            if not best_solution.is_valid:
                print(f"\n[WARN] Solución con violaciones de restricciones duras")
                print(f"\nLog de construcción:")
                for log_entry in best_solution.construction_log[-10:]:  # Últimas 10 entradas
                    print(f"  {log_entry}")
            
            # Guardar resultados en archivo JSON
            import json
            from datetime import datetime
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"horario_generado_{timestamp}.json"
            execution_time_seconds = time.time() - start_time_exec
            print(f"\n[TIEMPO] Duración de ejecución: {execution_time_seconds:.2f} segundos")
            
            # Convertir assignments a formato serializable
            horario_data = {
                "metadata": {
                    "timestamp": timestamp,
                    "total_secciones": len(best_solution.assignments),
                    "costo_total": best_solution.total_cost,
                    "es_valida": best_solution.is_valid,
                    "penalizaciones": best_solution.soft_penalties,
                    "duracion_segundos": execution_time_seconds
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
            
            print(f"\n[GUARDADO] Horario guardado en: {output_file}")

            # Guardar en base de datos
            try:
                print("\n[BD] Registrando ejecución en la base de datos...")
                execution = AlgorithmExecution(
                    algoritmo="ACO+GraphSAGE (Script)",
                    semestre="2025-II",  # Semestre objetivo
                    parametros=json.dumps({
                        "n_hormigas": args.hormigas,
                        "n_iteraciones": args.iteraciones,
                        "version": "v2_reparacion_greedy",
                        "metrics": horario_data["metadata"]
                    }),
                    estado="completed",
                    tiempo_ejecucion=execution_time_seconds,
                    funcion_objetivo=best_solution.total_cost,
                    restricciones_violadas=0 if best_solution.is_valid else (len(builder.section_id_to_idx) - len(best_solution.assignments)),
                    conflictos_profesor=best_solution.soft_penalties.get("concentracion_cursos", 0), # Usamos concentración como indicador clave
                    conflictos_aula=best_solution.soft_penalties.get("cambio_edificio", 0),
                    log_ejecucion=f"Archivo generado: {output_file} | Cobertura: {len(best_solution.assignments)}/{len(builder.section_id_to_idx)}",
                    terminado_en=datetime.now()
                )
                db.add(execution)
                db.commit()
                print(f"[BD] [OK] Ejecución registrada con ID: {execution.id}")
            except Exception as e:
                print(f"[BD] [ERR] Error al registrar en BD: {e}")
            
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
            
            print(f"[GRAFICO] Horario guardado en CSV: {csv_file}")
            
            # Convertir automáticamente a Excel formateado
            print("\n[EXCEL] Convirtiendo a formato Excel...")
            try:
                from convertir_csv_a_excel import convertir_csv_a_excel
                excel_file = convertir_csv_a_excel(csv_file)
                print(f"[EXCEL] [OK] Archivo Excel creado: {excel_file}")
            except Exception as e:
                print(f"[EXCEL] [ERR] Error al convertir a Excel: {e}")
        else:
            print("\n[X] No se encontró ninguna solución")
        
        print(f"\n[GRAFICO] Métricas de ejecución:")
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
                c_count = max(1, stats.get('classrooms', 0))
                total = stats.get('professors', 0) * c_count * stats.get('timeslots', 0)
                if total < 100:  # Menos de 100 combinaciones posibles
                    problematic.append((section_id, stats, total))
            
            if problematic:
                print(f"\n[WARN] {len(problematic)} secciones con pocos candidatos:")
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
                print("\n[OK] Todas las secciones tienen suficientes candidatos")
        
    finally:
        db.close()

if __name__ == "__main__":
    main()
