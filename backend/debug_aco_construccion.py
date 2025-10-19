"""
Script para diagnosticar por qué el ACO no encuentra soluciones válidas
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.aco_graphsage.graph_builder import TimetableGraphBuilder
from app.models import TimeSlot, Classroom, ProfessorRestriction
from app.aco_graphsage.constraints import (
    TimeSlotInfo, 
    ClassroomInfo, 
    ProfessorRestrictionInfo,
    HardConstraintValidator,
    Assignment
)

def main():
    db = SessionLocal()
    
    try:
        print("="*80)
        print("DIAGNÓSTICO DE CONSTRUCCIÓN ACO")
        print("="*80)
        
        # 1. Construir grafo
        print("\n1. Construyendo grafo...")
        builder = TimetableGraphBuilder(db)
        graph = builder.build_graph()
        
        # 2. Preparar validador
        print("\n2. Preparando validador...")
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
        
        # 3. Simular construcción de solución
        print("\n3. Simulando construcción de solución...")
        
        # Obtener todas las secciones
        section_ids = list(builder.section_id_to_idx.keys())
        
        # Ordenar por duración y alumnos (como hace el ACO)
        section_priorities = []
        for sec_id in section_ids:
            duration = builder.section_durations.get(sec_id, 1)
            projected = builder.section_projected_students.get(sec_id, 0)
            section_priorities.append((sec_id, duration, projected))
        
        section_priorities.sort(key=lambda item: (-item[1], -item[2], item[0]))
        
        print(f"\nOrden de asignación (primeras 10 secciones):")
        for i, (sec_id, dur, proj) in enumerate(section_priorities[:10]):
            metadata = builder.section_metadata.get(sec_id, {})
            print(f"  {i+1}. Sección {sec_id}: {metadata.get('course_code')} - "
                  f"Duración={dur}, Alumnos={proj}")
        
        # 4. Intentar asignar las primeras 3 secciones
        print("\n4. Intentando asignar primeras 3 secciones...")
        current_schedule = []
        
        for i, (sec_id, dur, proj) in enumerate(section_priorities[:3]):
            metadata = builder.section_metadata.get(sec_id, {})
            print(f"\n{'='*70}")
            print(f"Sección {sec_id}: {metadata.get('course_code')} {metadata.get('session_type')} Liga {metadata.get('league')}")
            print(f"Duración: {dur} bloques, Alumnos proyectados: {proj}")
            print(f"{'='*70}")
            
            # Obtener candidatos desde el grafo
            sec_idx = builder.section_id_to_idx[sec_id]
            
            # Profesores
            if ('section', 'assigned_to', 'professor') in graph.edge_index_dict:
                edges = graph[('section', 'assigned_to', 'professor')].edge_index
                prof_indices = edges[1][edges[0] == sec_idx].tolist()
            else:
                prof_indices = []
            
            # Aulas
            if ('section', 'uses', 'classroom') in graph.edge_index_dict:
                edges = graph[('section', 'uses', 'classroom')].edge_index
                classroom_indices = edges[1][edges[0] == sec_idx].tolist()
            else:
                classroom_indices = []
            
            # Franjas
            if ('section', 'starts_at', 'timeslot') in graph.edge_index_dict:
                edges = graph[('section', 'starts_at', 'timeslot')].edge_index
                timeslot_indices = edges[1][edges[0] == sec_idx].tolist()
            else:
                timeslot_indices = []
            
            print(f"\nCandidatos disponibles:")
            print(f"  Profesores: {len(prof_indices)}")
            print(f"  Aulas: {len(classroom_indices)}")
            print(f"  Franjas horarias: {len(timeslot_indices)}")
            print(f"  Total combinaciones: {len(prof_indices) * len(classroom_indices) * len(timeslot_indices)}")
            
            # Intentar encontrar una asignación válida
            valid_found = False
            total_tried = 0
            reasons = {}
            
            # Limitar búsqueda para no saturar
            max_to_try = 1000
            
            for prof_idx in prof_indices[:5]:  # Solo primeros 5 profesores
                for classroom_idx in classroom_indices[:10]:  # Solo primeras 10 aulas
                    for timeslot_idx in timeslot_indices[:20]:  # Solo primeras 20 franjas
                        if total_tried >= max_to_try:
                            break
                        
                        total_tried += 1
                        
                        # Construir Assignment
                        professor_id = builder.idx_to_professor_id[prof_idx]
                        classroom_id = builder.idx_to_classroom_id[classroom_idx]
                        timeslot_start_id = builder.idx_to_timeslot_id[timeslot_idx]
                        
                        # Buscar bloques consecutivos
                        start_ts = timeslots_dict[timeslot_start_id]
                        timeslot_ids = [timeslot_start_id]
                        
                        for j in range(1, dur):
                            next_orden = start_ts.orden + j
                            next_ts = None
                            for ts_id, ts in timeslots_dict.items():
                                if ts.dia_semana == start_ts.dia_semana and ts.orden == next_orden:
                                    next_ts = ts_id
                                    break
                            
                            if next_ts is not None:
                                timeslot_ids.append(next_ts)
                            else:
                                break
                        
                        if len(timeslot_ids) < dur:
                            reasons["Bloques consecutivos insuficientes"] = reasons.get("Bloques consecutivos insuficientes", 0) + 1
                            continue
                        
                        assignment = Assignment(
                            section_id=sec_id,
                            professor_id=professor_id,
                            classroom_id=classroom_id,
                            timeslot_ids=timeslot_ids,
                            course_code=metadata.get("course_code", f"SECTION-{sec_id}"),
                            session_type=metadata.get("session_type", "T").upper(),
                            league_id=metadata.get("league", 1),
                            ciclo=metadata.get("ciclo", "SIN-CICLO"),
                            alumnos_proyectados=proj,
                        )
                        
                        # Validar
                        is_valid, error = validator.validate_all(assignment, current_schedule)
                        
                        if is_valid:
                            valid_found = True
                            current_schedule.append(assignment)
                            print(f"\nASIGNACION VALIDA ENCONTRADA:")
                            print(f"   Profesor ID: {professor_id}")
                            print(f"   Aula ID: {classroom_id}")
                            print(f"   Franjas: {timeslot_ids}")
                            print(f"   Intentos necesarios: {total_tried}")
                            break
                        else:
                            reasons[error] = reasons.get(error, 0) + 1
                    
                    if valid_found:
                        break
                
                if valid_found:
                    break
            
            if not valid_found:
                print(f"\nNO SE ENCONTRO ASIGNACION VALIDA")
                print(f"   Combinaciones probadas: {total_tried}")
                print(f"\n   Razones de rechazo:")
                sorted_reasons = sorted(reasons.items(), key=lambda x: -x[1])
                for reason, count in sorted_reasons[:5]:
                    print(f"     - {reason}: {count} veces")
                
                print("\nCONSTRUCCION DETENIDA - No se puede continuar sin asignar esta seccion")
                break
        
        print(f"\n{'='*80}")
        print(f"RESUMEN:")
        print(f"  Secciones asignadas: {len(current_schedule)}/3")
        print(f"  Exito: {'SI' if len(current_schedule) == 3 else 'NO'}")
        print(f"{'='*80}")
        
    finally:
        db.close()

if __name__ == "__main__":
    main()
