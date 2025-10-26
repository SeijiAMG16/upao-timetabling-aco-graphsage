"""
DEBUG: Verificar la lógica de _load_professor_assignments
"""
from app.aco_graphsage.graph_builder import TimetableGraphBuilder
from app.database import get_db

db = next(get_db())
builder = TimetableGraphBuilder(db)

# Cargar asignaciones
builder._load_professor_assignments()

print("=" * 100)
print("DEBUG: _load_professor_assignments")
print("=" * 100)

# Verificar para ISIA109 y ISIA116
from sqlalchemy import text
result = db.execute(text("""
    SELECT id, codigo 
    FROM courses 
    WHERE codigo IN ('ISIA109', 'ISIA116')
"""))

courses = {r.codigo: r.id for r in result}

print(f"\nCursos encontrados:")
for codigo, course_id in courses.items():
    print(f"  {codigo}: ID = {course_id}")

# Verificar qué hay en assign_by_league
print("\n" + "=" * 100)
print("assign_by_league (filtrado por ISIA109 y ISIA116):")
print("=" * 100)

for key, profs in builder.prof_assign_by_league.items():
    course_id, session_type, league = key
    if course_id in courses.values():
        curso_codigo = [k for k, v in courses.items() if v == course_id][0]
        print(f"  ({curso_codigo}, {session_type}, Liga {league}): {len(profs)} profesores -> {profs}")

# Verificar qué hay en assign_by_type
print("\n" + "=" * 100)
print("assign_by_type (filtrado por ISIA109 y ISIA116):")
print("=" * 100)

for key, profs in builder.prof_assign_by_type.items():
    course_id, session_type = key
    if course_id in courses.values():
        curso_codigo = [k for k, v in courses.items() if v == course_id][0]
        print(f"  ({curso_codigo}, {session_type}): {len(profs)} profesores -> {profs}")

# Simular la búsqueda de candidatos para sección 1713
print("\n" + "=" * 100)
print("SIMULACION: _candidate_professors_for_section para sección 1713")
print("=" * 100)

# Mock de la sección 1713
class MockSection:
    def __init__(self):
        self.course_id = courses['ISIA109']  # 654
        self.tipo = 'laboratorio'
        self.league = 1

mock_section = MockSection()

# Llamar a la función
candidatos = builder._candidate_professors_for_section(mock_section)

print(f"\nSeccion 1713 (ISIA109, tipo='laboratorio', liga=1):")
print(f"  course_id: {mock_section.course_id}")
print(f"  Tipo normalizado: 'L'")
print(f"  Liga: {mock_section.league}")
print(f"  Candidatos encontrados: {len(candidatos)} -> {candidatos}")

if not candidatos:
    print("\n  [ERROR] ¡NO SE ENCONTRARON CANDIDATOS!")
    print("  Verificando por qué...")
    
    # Verificar key_league
    key_league = (mock_section.course_id, 'L', mock_section.league)
    print(f"\n  key_league buscada: {key_league}")
    print(f"  ¿Existe en prof_assign_by_league? {key_league in builder.prof_assign_by_league}")
    
    # Verificar key_type
    key_type = (mock_section.course_id, 'L')
    print(f"\n  key_type buscada: {key_type}")
    print(f"  ¿Existe en prof_assign_by_type? {key_type in builder.prof_assign_by_type}")
    
    # Verificar course_id
    print(f"\n  course_id: {mock_section.course_id}")
    print(f"  ¿Existe en prof_assign_by_course? {mock_section.course_id in builder.prof_assign_by_course}")
    
    if mock_section.course_id in builder.prof_assign_by_course:
        print(f"    Profesores: {builder.prof_assign_by_course[mock_section.course_id]}")

# Hacer lo mismo para sección 1778
print("\n" + "=" * 100)
print("SIMULACION: _candidate_professors_for_section para sección 1778")
print("=" * 100)

class MockSection2:
    def __init__(self):
        self.course_id = courses['ISIA116']  # 667
        self.tipo = 'laboratorio'
        self.league = 2

mock_section2 = MockSection2()
candidatos2 = builder._candidate_professors_for_section(mock_section2)

print(f"\nSeccion 1778 (ISIA116, tipo='laboratorio', liga=2):")
print(f"  course_id: {mock_section2.course_id}")
print(f"  Tipo normalizado: 'L'")
print(f"  Liga: {mock_section2.league}")
print(f"  Candidatos encontrados: {len(candidatos2)} -> {candidatos2}")

if not candidatos2:
    print("\n  [ERROR] ¡NO SE ENCONTRARON CANDIDATOS!")
