"""
Mapear secciones virtuales (IDs negativos) a sus secciones reales originales
"""
from app.database import SessionLocal
from app.aco_graphsage.pipeline import TimetablePipeline

session = SessionLocal()
try:
    print("="*80)
    print("MAPEO DE SECCIONES VIRTUALES A SECCIONES REALES")
    print("="*80)
    
    # Construir el grafo (esto genera las secciones virtuales)
    pipeline = TimetablePipeline(session)
    pipeline.prepare()
    
    # Acceder al graph_builder
    gb = pipeline.graph_builder
    
    print(f"\nTotal de secciones en el grafo: {len(gb.section_id_to_idx)}")
    print(f"Mapeo virtual_to_real tiene: {len(gb.virtual_to_real_section)} entradas")
    
    # Buscar las secciones negativas específicas
    virtual_sections = [-12, -11, -10, -9, -8, -7, -6, -5, -4, -3, -2, -1]
    
    print(f"\n{'='*80}")
    print("SECCIONES VIRTUALES (IDs negativos):")
    print(f"{'='*80}\n")
    
    for vid in virtual_sections:
        if vid in gb.virtual_to_real_section:
            real_id = gb.virtual_to_real_section[vid]
            
            # Obtener metadata
            metadata = gb.section_metadata.get(vid, {})
            course_code = metadata.get('course_code', 'N/A')
            session_type = metadata.get('session_type', 'N/A')
            league = metadata.get('league', 'N/A')
            students = gb.section_projected_students.get(vid, 0)
            duration = gb.section_durations.get(vid, 0)
            split_index = metadata.get('split_group_index', 0)
            split_count = metadata.get('split_group_count', 1)
            
            print(f"Sección Virtual {vid}:")
            print(f"  → Originada de sección real: {real_id}")
            print(f"  → Curso: {course_code}")
            print(f"  → Tipo: {session_type}, Liga: {league}")
            print(f"  → Estudiantes: {students}")
            print(f"  → Duración: {duration} bloques")
            print(f"  → Subgrupo {split_index + 1}/{split_count}")
            
            # Verificar si tiene candidatos
            candidate_stats = gb.section_candidate_stats.get(vid, {})
            profs = candidate_stats.get('professors', 0)
            classrooms = candidate_stats.get('classrooms', 0)
            timeslots = candidate_stats.get('timeslots', 0)
            
            print(f"  → Candidatos: {profs} profesores, {classrooms} aulas, {timeslots} timeslots")
            
            if profs == 0:
                print(f"  ⚠️ SIN PROFESORES CANDIDATOS - Esta sección NO se puede asignar")
            
            print()
        else:
            print(f"Sección Virtual {vid}: NO encontrada en virtual_to_real_section\n")
    
    print(f"\n{'='*80}")
    print("GRUPOS DE SECCIONES (secciones reales divididas):")
    print(f"{'='*80}\n")
    
    for real_id, virtual_ids in gb.section_virtual_groups.items():
        if len(virtual_ids) > 1:  # Solo mostrar las que se dividieron
            print(f"Sección Real {real_id} se dividió en {len(virtual_ids)} subgrupos:")
            for vid in virtual_ids:
                students = gb.section_projected_students.get(vid, 0)
                print(f"  - ID {vid}: {students} estudiantes")
            print()

finally:
    session.close()
