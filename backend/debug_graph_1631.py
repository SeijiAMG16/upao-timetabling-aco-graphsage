"""Verificar por qué G601, G701, G801 no están disponibles para sección 1631"""

from app.database import SessionLocal
from app.models import CourseSection, Classroom
from app.aco_graphsage.pipeline import TimetablePipeline
import torch

def main():
    db = SessionLocal()
    
    try:
        print("="*80)
        print("VERIFICACIÓN GRAFO - SECCIÓN 1631 y AULAS G-LAB")
        print("="*80)
        
        # 1. Información de la sección
        section = db.query(CourseSection).filter_by(id=1631).first()
        print(f"\nSección 1631: {section.course.codigo} {section.tipo}")
        print(f"Alumnos proyectados: {section.alumnos_proyectados}")
        
        # 2. Aulas G LAB
        g_labs = db.query(Classroom).filter(
            Classroom.codigo.in_(['G601', 'G701', 'G801']),
            Classroom.active == True
        ).all()
        
        print(f"\n{'='*80}")
        print("AULAS G-LAB:")
        for aula in g_labs:
            print(f"  {aula.codigo}: tipo={aula.tipo}, capacidad={aula.capacidad}, ID={aula.id}")
        
        # 3. Construir pipeline y verificar grafo
        print(f"\n{'='*80}")
        print("CONSTRUYENDO GRAFO...")
        pipeline = TimetablePipeline(db)
        pipeline.prepare()
        
        graph_builder = pipeline.graph_builder
        
        # Encontrar índice de la sección 1631
        section_ids = list(graph_builder.section_metadata.keys())
        if 1631 not in section_ids:
            print(f"\n❌ ERROR: Sección 1631 NO está en el grafo!")
            return
        
        section_idx = section_ids.index(1631)
        print(f"\nSección 1631 tiene índice {section_idx} en el grafo")
        
        # 4. Verificar conexiones a aulas
        classroom_edges = graph_builder.graph['section', 'uses', 'classroom'].edge_index
        classroom_ids = list(graph_builder.classroom_to_idx.keys())
        
        # Encontrar conexiones de la sección 1631
        section_classroom_connections = classroom_edges[1][classroom_edges[0] == section_idx]
        
        print(f"\n{'='*80}")
        print(f"AULAS CONECTADAS A SECCIÓN 1631: {len(section_classroom_connections)} aulas")
        
        # Buscar las aulas G-LAB específicas
        g_lab_ids = [aula.id for aula in g_labs]
        
        connected_classrooms = []
        for classroom_idx in section_classroom_connections:
            classroom_id = classroom_ids[classroom_idx.item()]
            classroom = db.query(Classroom).filter_by(id=classroom_id).first()
            connected_classrooms.append(classroom)
            
            if classroom_id in g_lab_ids:
                print(f"  ✅ {classroom.codigo} (ID={classroom.id}) ESTÁ CONECTADA")
        
        # Verificar si las G-LAB están conectadas
        print(f"\n{'='*80}")
        print("VERIFICACIÓN ESPECÍFICA G-LAB:")
        for aula in g_labs:
            if aula.id in [c.id for c in connected_classrooms]:
                print(f"  ✅ {aula.codigo} (ID={aula.id}) - CONECTADA AL GRAFO")
            else:
                print(f"  ❌ {aula.codigo} (ID={aula.id}) - NO CONECTADA")
                
                # Verificar por qué no está conectada
                # Posibles razones:
                # 1. Tipo de aula no coincide
                metadata = graph_builder.section_metadata[1631]
                print(f"      Metadatos sección: session_type={metadata.get('session_type')}")
                print(f"      Tipo aula requerido: LAB (para laboratorio)")
                print(f"      Tipo aula real: {aula.tipo}")
                
                # 2. Capacidad insuficiente
                if aula.capacidad < section.alumnos_proyectados:
                    print(f"      ❌ Capacidad insuficiente: {aula.capacidad} < {section.alumnos_proyectados}")
                else:
                    print(f"      ✅ Capacidad suficiente: {aula.capacidad} >= {section.alumnos_proyectados}")
        
        # 5. Mostrar algunas aulas conectadas
        print(f"\n{'='*80}")
        print("EJEMPLO DE AULAS CONECTADAS (primeras 10):")
        for i, classroom in enumerate(connected_classrooms[:10]):
            print(f"  {classroom.codigo}: tipo={classroom.tipo}, capacidad={classroom.capacidad}")
        
        # 6. Verificar construcción de aristas
        print(f"\n{'='*80}")
        print("VERIFICANDO LÓGICA DE CONEXIÓN EN GRAPH_BUILDER:")
        print(f"  Session type de 1631: {graph_builder.section_metadata[1631].get('session_type')}")
        print(f"  Alumnos proyectados: {graph_builder.section_projected_students.get(1631)}")
        
        # Simular la lógica del graph_builder
        session_type = (section.tipo or "").upper()
        required_classroom_type = "LAB" if session_type == "LABORATORIO" else "NOLAB"
        print(f"  Tipo requerido calculado: {required_classroom_type}")
        
        for aula in g_labs:
            match = aula.tipo == required_classroom_type
            capacity_ok = aula.capacidad >= section.alumnos_proyectados
            print(f"  {aula.codigo}: tipo_match={match}, capacity_ok={capacity_ok}")
        
    finally:
        db.close()

if __name__ == "__main__":
    main()
