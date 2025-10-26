import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from app.aco_graphsage.graph_builder import TimetableGraphBuilder
import logging

# Desactivar logs de SQLAlchemy
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

db = SessionLocal()
builder = TimetableGraphBuilder(db)

# Construir grafo para generar todas las instancias
sections = builder._load_sections()
classrooms = builder._load_classrooms()
instances = builder._generate_section_instances(sections, classrooms)

print("=" * 100)
print("INSTANCIAS VIRTUALES (ID < 0)")
print("=" * 100)

virtual_instances = [inst for inst in instances if inst.id < 0]
print(f"\nTotal instancias virtuales: {len(virtual_instances)}")

# Ordenar por ID para encontrar -12
virtual_instances.sort(key=lambda x: x.id)

print("\nPrimeras 20 instancias virtuales:")
for inst in virtual_instances[:20]:
    print(f"  ID {inst.id:4d} | {inst.course.codigo:8s} | {inst.tipo:12s} | Liga {inst.league} | {inst.num_students:3d} alumnos | (de sección real {inst.original_section_id})")

print("\nBuscando específicamente ID -12:")
inst_12 = next((inst for inst in virtual_instances if inst.id == -12), None)

if inst_12:
    print(f"\n{'=' * 100}")
    print(f"ENCONTRADA: Sección Virtual -12")
    print(f"{'=' * 100}")
    print(f"  Curso: {inst_12.course.codigo} - {inst_12.course.nombre}")
    print(f"  Tipo: {inst_12.tipo}")
    print(f"  Liga: {inst_12.league}")
    print(f"  Alumnos: {inst_12.num_students}")
    print(f"  Sección real original: {inst_12.original_section_id}")
    print(f"  Grupo: {inst_12.group_index + 1}/{inst_12.group_count}")
    print(f"  Capacidad máxima aula: {inst_12.max_capacity}")
    
    # Buscar candidatos para esta sección
    builder._load_professor_assignments()
    candidatos = builder._candidate_professors_for_section(inst_12.original)
    
    print(f"\n  Candidatos de profesores: {len(candidatos)}")
    if candidatos:
        print(f"    -> Profesores: {candidatos}")
    else:
        print(f"    -> *** SIN CANDIDATOS *** (por eso ACO falla)")
        
        # Investigar por qué no hay candidatos
        session_type = builder._normalize_session_type(inst_12.tipo)
        course_id = inst_12.course_id
        league = inst_12.league
        
        print(f"\n  Buscando en prof_assign_by_league para:")
        print(f"    course_id={course_id}, session_type='{session_type}', league={league}")
        
        key_league = (course_id, session_type, league)
        if key_league in builder.prof_assign_by_league:
            print(f"    -> Encontrado en prof_assign_by_league: {builder.prof_assign_by_league[key_league]}")
        else:
            print(f"    -> NO encontrado en prof_assign_by_league")
        
        print(f"\n  Buscando en prof_assign_by_type para:")
        print(f"    course_id={course_id}, session_type='{session_type}'")
        
        key_type = (course_id, session_type)
        if key_type in builder.prof_assign_by_type:
            print(f"    -> Encontrado en prof_assign_by_type: {builder.prof_assign_by_type[key_type]}")
        else:
            print(f"    -> NO encontrado en prof_assign_by_type")
            
        print(f"\n  Buscando en prof_assign_by_course para:")
        print(f"    course_id={course_id}")
        
        if course_id in builder.prof_assign_by_course:
            print(f"    -> Encontrado en prof_assign_by_course: {builder.prof_assign_by_course[course_id]}")
        else:
            print(f"    -> NO encontrado en prof_assign_by_course")
else:
    print("\n*** Sección virtual -12 NO encontrada ***")
    print(f"Total de instancias: {len(instances)}")
    print(f"IDs virtuales van desde {virtual_instances[0].id if virtual_instances else 'N/A'} hasta {virtual_instances[-1].id if virtual_instances else 'N/A'}")

db.close()
