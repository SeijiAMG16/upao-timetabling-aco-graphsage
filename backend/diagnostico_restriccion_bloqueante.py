"""
Diagnóstico: ¿QUÉ RESTRICCIÓN está bloqueando las secciones 1810 y 1811?
"""
import sys
sys.path.insert(0, 'c:\\Users\\amaya\\Downloads\\10mo Ciclo\\TESIS\\upao-timetabling-aco-graphsage\\backend')

from app.database import SessionLocal
from app.models import CourseSection, Classroom, TimeSlot, ProfessorCourseAssignment
from app.aco_graphsage.graph_builder import TimetableGraphBuilder
from sqlalchemy.orm import joinedload

def main():
    print("="*80)
    print("DIAGNÓSTICO: ¿Qué restricción bloquea secciones 1810 y 1811?")
    print("="*80)
    
    db = SessionLocal()
    
    # Construir grafo
    builder = TimetableGraphBuilder(db)
    graph, metadata = builder.build_graph()
    
    sections_metadata = metadata['sections']
    classrooms = db.query(Classroom).filter_by(active=True).all()
    timeslots = db.query(TimeSlot).all()
    
    # Analizar sección 1810
    print("\n🔍 SECCIÓN 1810:")
    section_1810 = db.query(CourseSection).options(
        joinedload(CourseSection.course)
    ).filter_by(id=1810).first()
    
    print(f"  ID: {section_1810.id}")
    print(f"  Código: {section_1810.codigo_completo}")
    print(f"  Tipo: {section_1810.tipo}")
    print(f"  Estudiantes: {section_1810.alumnos_proyectados}")
    print(f"  League: {section_1810.league}")
    print(f"  Modalidad: {section_1810.course.modalidad if section_1810.course else 'N/A'}")
    
    # Encontrar en metadata
    meta_1810 = sections_metadata.get(1810)
    print(f"\n  Metadata:")
    print(f"    course_code: {meta_1810['course_code']}")
    print(f"    session_type: {meta_1810['session_type']}")
    print(f"    league: {meta_1810['league']}")
    print(f"    required_hours: {meta_1810['required_hours']}")
    print(f"    modalidad: {meta_1810.get('modalidad', 'N/A')}")
    
    # Verificar profesor asignado
    prof_assign = db.query(ProfessorCourseAssignment).filter_by(
        course_section_id=1810
    ).first()
    
    if prof_assign:
        print(f"\n  Profesor asignado: ID={prof_assign.professor_id}")
    else:
        print(f"\n  ⚠️  NO HAY PROFESOR ASIGNADO")
    
    # Buscar en el grafo
    section_idx = None
    for idx, sec_id in enumerate(metadata['section_ids']):
        if sec_id == 1810:
            section_idx = idx
            break
    
    if section_idx is None:
        print(f"\n  ❌ ERROR: Sección 1810 NO está en el grafo!")
        print(f"  Section IDs en el grafo: {metadata['section_ids'][:20]}...")
    else:
        print(f"\n  ✅ Sección 1810 está en índice {section_idx} del grafo")
        
        # Verificar aristas section→classroom
        edge_index_classroom = graph['section', 'uses', 'classroom'].edge_index
        compatible_classrooms_indices = edge_index_classroom[1][edge_index_classroom[0] == section_idx]
        
        print(f"\n  Aulas compatibles (según grafo): {len(compatible_classrooms_indices)}")
        
        if len(compatible_classrooms_indices) == 0:
            print(f"  ❌ PROBLEMA: NO hay aristas section→classroom para sección 1810")
            print(f"  Esto significa que el grafo no encontró NINGÚN aula compatible")
            print(f"\n  Verificando manualmente compatibilidad:")
            
            def normalize_type(tipo):
                if tipo == 'LAB':
                    return 'laboratorio'
                elif tipo == 'NOLAB':
                    return 'teorica'
                return tipo.lower()
            
            section_tipo = section_1810.tipo.lower() if section_1810.tipo else ''
            compatible_count = 0
            
            for classroom in classrooms:
                tipo_norm = normalize_type(classroom.tipo)
                
                type_compatible = (
                    (section_tipo == 'teorica' and tipo_norm in ['teorica', 'practica']) or
                    (section_tipo == 'practica' and tipo_norm in ['teorica', 'practica']) or
                    (section_tipo == 'laboratorio' and tipo_norm == 'laboratorio')
                )
                
                capacity_ok = classroom.capacidad >= section_1810.alumnos_proyectados
                
                if type_compatible and capacity_ok:
                    compatible_count += 1
                    if compatible_count <= 3:
                        print(f"    - {classroom.codigo}: tipo={classroom.tipo}→{tipo_norm}, cap={classroom.capacidad}")
            
            print(f"\n  Total aulas compatibles (manual): {compatible_count}")
            print(f"  ⚠️  DISCREPANCIA: Grafo dice 0, manual dice {compatible_count}")
            print(f"  🔍 CAUSA PROBABLE: Problema en graph_builder.py al crear aristas")
        
    # Hacer lo mismo para sección 1811
    print("\n" + "="*80)
    print("🔍 SECCIÓN 1811:")
    section_1811 = db.query(CourseSection).options(
        joinedload(CourseSection.course)
    ).filter_by(id=1811).first()
    
    print(f"  ID: {section_1811.id}")
    print(f"  Código: {section_1811.codigo_completo}")
    print(f"  Tipo: {section_1811.tipo}")
    print(f"  Estudiantes: {section_1811.alumnos_proyectados}")
    print(f"  League: {section_1811.league}")
    print(f"  Modalidad: {section_1811.course.modalidad if section_1811.course else 'N/A'}")
    
    meta_1811 = sections_metadata.get(1811)
    print(f"\n  Metadata:")
    print(f"    course_code: {meta_1811['course_code']}")
    print(f"    session_type: {meta_1811['session_type']}")
    print(f"    league: {meta_1811['league']}")
    print(f"    required_hours: {meta_1811['required_hours']}")
    print(f"    modalidad: {meta_1811.get('modalidad', 'N/A')}")
    
    prof_assign_1811 = db.query(ProfessorCourseAssignment).filter_by(
        course_section_id=1811
    ).first()
    
    if prof_assign_1811:
        print(f"\n  Profesor asignado: ID={prof_assign_1811.professor_id}")
    else:
        print(f"\n  ⚠️  NO HAY PROFESOR ASIGNADO")
    
    # Buscar en el grafo
    section_idx_1811 = None
    for idx, sec_id in enumerate(metadata['section_ids']):
        if sec_id == 1811:
            section_idx_1811 = idx
            break
    
    if section_idx_1811 is None:
        print(f"\n  ❌ ERROR: Sección 1811 NO está en el grafo!")
    else:
        print(f"\n  ✅ Sección 1811 está en índice {section_idx_1811} del grafo")
        
        edge_index_classroom = graph['section', 'uses', 'classroom'].edge_index
        compatible_classrooms_indices = edge_index_classroom[1][edge_index_classroom[0] == section_idx_1811]
        
        print(f"\n  Aulas compatibles (según grafo): {len(compatible_classrooms_indices)}")
        
        if len(compatible_classrooms_indices) == 0:
            print(f"  ❌ PROBLEMA: NO hay aristas section→classroom para sección 1811")
    
    print("\n" + "="*80)
    print("💡 CONCLUSIÓN:")
    print("="*80)
    if (section_idx is not None and len(edge_index_classroom[1][edge_index_classroom[0] == section_idx]) == 0) or \
       (section_idx_1811 is not None and len(edge_index_classroom[1][edge_index_classroom[0] == section_idx_1811]) == 0):
        print("""
El problema NO es una restricción de validación durante la construcción,
sino que el GRAFO no tiene aristas section→classroom para estas secciones.

Esto significa que graph_builder.py está FILTRANDO incorrectamente estas secciones
al momento de crear las aristas, probablemente por:
  1. Tipo de aula no compatible
  2. Capacidad insuficiente  
  3. Algún otro filtro erróneo

ACCIÓN REQUERIDA:
Revisar graph_builder.py línea ~650-750 donde se crean las aristas section→classroom
y verificar por qué estas secciones NO tienen aristas.
        """)
    else:
        print("""
Las secciones SÍ tienen aristas en el grafo.
El problema debe estar en la validación de restricciones durante la construcción.
        """)
    
    db.close()

if __name__ == '__main__':
    main()
