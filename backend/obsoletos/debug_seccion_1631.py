"""Script para diagnosticar por qué no se puede asignar la sección 1631"""

from app.database import SessionLocal
from app.models import CourseSection, Course, Classroom, Professor
from app.aco_graphsage.graph_builder import TimetableGraphBuilder
from sqlalchemy import text

def main():
    db = SessionLocal()
    
    try:
        print("="*80)
        print("DIAGNÓSTICO SECCIÓN 1631 - CIEN769 LABORATORIO")
        print("="*80)
        
        # 1. Información básica de la sección
        section = db.query(CourseSection).filter_by(id=1631).first()
        course = section.course
        
        print(f"\n1. INFORMACIÓN DE LA SECCIÓN")
        print("-"*80)
        print(f"  ID: {section.id}")
        print(f"  Curso: {course.codigo} - {course.nombre}")
        print(f"  Tipo: {section.tipo}")
        print(f"  Ciclo: {course.ciclo}")
        print(f"  Liga: {section.league}")
        print(f"  Alumnos proyectados: {section.alumnos_proyectados}")
        
        # 2. Verificar profesores disponibles
        print(f"\n2. PROFESORES DISPONIBLES PARA {course.codigo}")
        print("-"*80)
        
        query = text("""
            SELECT p.id, p.codigo, p.nombre_completo, pca.session_type, pca.league
            FROM professors p
            JOIN professor_course_assignments pca ON p.id = pca.professor_id
            WHERE pca.course_id = :course_id
            ORDER BY pca.session_type, pca.league, p.id
        """)
        
        professors = db.execute(query, {"course_id": course.id}).fetchall()
        print(f"  Total asignaciones: {len(professors)}")
        
        lab_profs = [p for p in professors if p.session_type == 'laboratorio' and p.league == 1]
        print(f"  Profesores para LABORATORIO Liga 1: {len(lab_profs)}")
        for prof in lab_profs:
            print(f"    - ID {prof.id}: {prof.nombre_completo} ({prof.codigo})")
        
        # 3. Verificar aulas disponibles
        print(f"\n3. AULAS DE LABORATORIO DISPONIBLES")
        print("-"*80)
        
        labs = db.query(Classroom).filter(
            Classroom.tipo == 'laboratorio',
            Classroom.active == True
        ).all()
        
        print(f"  Total aulas de laboratorio: {len(labs)}")
        print(f"  Alumnos a acomodar: {section.alumnos_proyectados}")
        print("")
        
        suitable_labs = [lab for lab in labs if lab.capacidad >= section.alumnos_proyectados]
        print(f"  Aulas con capacidad suficiente (>={section.alumnos_proyectados}): {len(suitable_labs)}")
        for lab in suitable_labs:
            print(f"    - {lab.codigo}: Cap {lab.capacidad}, Edificio {lab.edificio}")
        
        if not suitable_labs:
            print(f"\n  ⚠️  PROBLEMA: No hay aulas de laboratorio con capacidad >= {section.alumnos_proyectados}")
            print(f"  Aulas de laboratorio ordenadas por capacidad:")
            for lab in sorted(labs, key=lambda x: x.capacidad, reverse=True):
                print(f"    - {lab.codigo}: Cap {lab.capacidad}")
        
        # 4. Verificar otras secciones del mismo curso
        print(f"\n4. OTRAS SECCIONES DE {course.codigo}")
        print("-"*80)
        
        other_sections = db.query(CourseSection).filter(
            CourseSection.course_id == course.id,
            CourseSection.activa == True
        ).order_by(CourseSection.tipo, CourseSection.league).all()
        
        for sec in other_sections:
            marker = ">>> ESTA <<<" if sec.id == 1631 else ""
            print(f"  Sección {sec.id}: {sec.tipo.upper()}, Liga {sec.league}, "
                  f"{sec.alumnos_proyectados} alumnos {marker}")
        
        # 5. Verificar en el grafo
        print(f"\n5. VERIFICACIÓN EN EL GRAFO")
        print("-"*80)
        
        graph_builder = TimetableGraphBuilder(db)
        graph_builder.build_graph()
        
        if 1631 in graph_builder.section_metadata:
            metadata = graph_builder.section_metadata[1631]
            print(f"  Sección encontrada en el grafo:")
            print(f"    - course_code: {metadata.get('course_code')}")
            print(f"    - session_type: {metadata.get('session_type')}")
            print(f"    - league: {metadata.get('league')}")
            print(f"    - ciclo: {metadata.get('ciclo')}")
            
            # Verificar combinaciones disponibles
            prof_edges = graph_builder.graph['section', 'assigned_to', 'professor'].edge_index
            classroom_edges = graph_builder.graph['section', 'uses', 'classroom'].edge_index
            timeslot_edges = graph_builder.graph['section', 'starts_at', 'timeslot'].edge_index
            
            # Encontrar índice de la sección
            section_idx = list(graph_builder.section_metadata.keys()).index(1631)
            
            # Contar conexiones
            prof_connections = (prof_edges[0] == section_idx).sum().item()
            classroom_connections = (classroom_edges[0] == section_idx).sum().item()
            timeslot_connections = (timeslot_edges[0] == section_idx).sum().item()
            
            print(f"\n  Conexiones en el grafo:")
            print(f"    - Profesores conectados: {prof_connections}")
            print(f"    - Aulas conectadas: {classroom_connections}")
            print(f"    - Franjas horarias conectadas: {timeslot_connections}")
            
            if prof_connections == 0:
                print(f"\n  ❌ PROBLEMA: No hay profesores conectados en el grafo")
            if classroom_connections == 0:
                print(f"\n  ❌ PROBLEMA: No hay aulas conectadas en el grafo")
            if timeslot_connections == 0:
                print(f"\n  ❌ PROBLEMA: No hay franjas horarias conectadas en el grafo")
        else:
            print(f"  ❌ PROBLEMA: Sección 1631 NO encontrada en el grafo")
        
        # 6. Resumen del diagnóstico
        print(f"\n{'='*80}")
        print("6. RESUMEN Y DIAGNÓSTICO")
        print("="*80)
        
        issues = []
        
        if len(lab_profs) == 0:
            issues.append("❌ No hay profesores asignados para LABORATORIO Liga 1")
        
        if len(suitable_labs) == 0:
            issues.append(f"❌ No hay aulas de laboratorio con capacidad >= {section.alumnos_proyectados}")
        
        if 1631 not in graph_builder.section_metadata:
            issues.append("❌ La sección no está en el grafo")
        elif prof_connections == 0 or classroom_connections == 0 or timeslot_connections == 0:
            issues.append("❌ La sección no tiene conexiones suficientes en el grafo")
        
        if issues:
            print("\nPROBLEMAS IDENTIFICADOS:")
            for issue in issues:
                print(f"  {issue}")
        else:
            print("\n✅ No se identificaron problemas obvios. El problema puede ser:")
            print("   - Conflictos con otras secciones ya asignadas")
            print("   - Restricciones de horario de profesores")
            print("   - Orden de asignación en el algoritmo ACO")
        
    finally:
        db.close()

if __name__ == "__main__":
    main()
