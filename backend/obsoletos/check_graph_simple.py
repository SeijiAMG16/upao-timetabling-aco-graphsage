"""Script simple para verificar conexiones en el grafo"""
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')

from app.database import SessionLocal
from app.models import CourseSection, Classroom
from app.aco_graphsage.graph_builder import TimetableGraphBuilder

def main():
    db = SessionLocal()
    
    try:
        print("="*80)
        print("ANALISIS GRAFO - SECCION 1631")
        print("="*80)
        
        # Construir grafo
        print("\nConstruyendo grafo...")
        graph_builder = TimetableGraphBuilder(db)
        graph = graph_builder.build_graph()
        
        # Verificar sección 1631
        section_ids = list(graph_builder.section_metadata.keys())
        if 1631 not in section_ids:
            print("ERROR: Seccion 1631 no esta en el grafo!")
            return
        
        section_idx = graph_builder.section_id_to_idx.get(1631)
        if section_idx is None:
            print("ERROR: No se puede encontrar el indice de la seccion 1631!")
            return
            
        metadata = graph_builder.section_metadata[1631]
        
        print(f"\nSeccion 1631 (indice {section_idx}):")
        print(f"  Curso: {metadata.get('course_code')}")
        print(f"  Tipo: {metadata.get('session_type')}")
        print(f"  Alumnos: {graph_builder.section_projected_students.get(1631)}")
        
        # Verificar conexiones a aulas
        classroom_edges = graph['section', 'uses', 'classroom'].edge_index
        section_connections = classroom_edges[1][classroom_edges[0] == section_idx]
        
        print(f"\nAulas conectadas: {len(section_connections)}")
        
        # Buscar aulas específicas
        g_labs = db.query(Classroom).filter(
            Classroom.codigo.in_(['G601', 'G701', 'G801'])
        ).all()
        
        classroom_ids = list(graph_builder.idx_to_classroom_id.values())
        
        print("\nVerificando aulas G-LAB:")
        for aula in g_labs:
            if aula.id in classroom_ids:
                aula_idx = classroom_ids.index(aula.id)
                is_connected = aula_idx in section_connections
                status = "CONECTADA" if is_connected else "NO CONECTADA"
                print(f"  {aula.codigo} (ID={aula.id}): {status}")
                print(f"    tipo={aula.tipo}, capacidad={aula.capacidad}")
            else:
                print(f"  {aula.codigo}: NO ESTA EN EL GRAFO")
        
        # Mostrar todas las aulas LAB conectadas
        print("\nTodas las aulas LAB conectadas a seccion 1631:")
        count = 0
        for classroom_idx in section_connections[:20]:  # Primeras 20
            classroom_id = classroom_ids[classroom_idx.item()]
            classroom = db.query(Classroom).filter_by(id=classroom_id).first()
            if classroom and classroom.tipo == 'LAB':
                print(f"  {classroom.codigo}: tipo={classroom.tipo}, cap={classroom.capacidad}")
                count += 1
        
        print(f"\nTotal aulas LAB conectadas: {count}")
        
    finally:
        db.close()

if __name__ == "__main__":
    main()
