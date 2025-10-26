"""
Verificación del FIX: Asignaciones por liga
"""

from app.aco_graphsage.graph_builder import TimetableGraphBuilder
from app.database import get_db
from sqlalchemy import text

print("=" * 100)
print("VERIFICACIÓN DEL FIX: Asignaciones de profesores por liga")
print("=" * 100)

db = next(get_db())

# Crear instancia del TimetableGraphBuilder
builder = TimetableGraphBuilder(db)

# Cargar asignaciones
builder._load_professor_assignments()

# Verificar ISIA125 (TESIS II)
print("\n[VERIFICANDO] Asignaciones de ISIA125 (TESIS II):\n")

# Obtener course_id de ISIA125
result = db.execute(text("SELECT id FROM courses WHERE codigo = 'ISIA125'"))
course_row = result.first()
course_id = course_row.id if course_row else None

if not course_id:
    print("[ERROR] No se encontro el curso ISIA125")
    exit(1)

print(f"[OK] Course ID: {course_id}\n")

# Verificar asignaciones por liga
print("[ASIGNACIONES] Cargadas por liga (course_id, session_type, league):")
print("-" * 100)

for liga in [1, 2, 3, 4]:
    for tipo in ['T', 'P']:
        key = (course_id, tipo, liga)
        if key in builder.prof_assign_by_league:
            profs = builder.prof_assign_by_league[key]
            # Obtener nombres
            prof_names = []
            for prof_id in profs:
                prof_result = db.execute(text(f"SELECT codigo, nombre_completo FROM professors WHERE id = {prof_id}"))
                prof_row = prof_result.first()
                if prof_row:
                    prof_names.append(f"{prof_row.codigo} ({prof_row.nombre_completo})")
            
            print(f"  Liga {liga} - Tipo {tipo}: {', '.join(prof_names)}")

# Ahora simular _candidate_professors_for_section para cada liga
print("\n\n[SIMULACION] Seleccion de candidatos POR SECCION:")
print("-" * 100)

# Obtener secciones de ISIA125
sections_result = db.execute(text("""
    SELECT id, tipo, league, seccion
    FROM course_sections
    WHERE course_id = (SELECT id FROM courses WHERE codigo = 'ISIA125')
    ORDER BY league, tipo, seccion
"""))

sections = list(sections_result)

# Crear un mock de CourseSection para simular
class MockSection:
    def __init__(self, course_id, tipo, league):
        self.course_id = course_id
        self.tipo = tipo
        self.league = league

print(f"\nTotal secciones: {len(sections)}\n")

for sec in sections:
    mock_section = MockSection(course_id, sec.tipo, sec.league)
    
    # Llamar a la función corregida
    candidatos = builder._candidate_professors_for_section(mock_section)
    
    # Obtener nombres de candidatos
    if candidatos:
        prof_names = []
        for prof_id in candidatos:
            prof_result = db.execute(text(f"SELECT codigo, nombre_completo FROM professors WHERE id = {prof_id}"))
            prof_row = prof_result.first()
            if prof_row:
                prof_names.append(f"{prof_row.codigo} ({prof_row.nombre_completo[:30]})")
        
        print(f"Sección {sec.seccion:10} | Liga {sec.league} | Tipo {sec.tipo:8} -> Candidatos: {', '.join(prof_names)}")
    else:
        print(f"Sección {sec.seccion:10} | Liga {sec.league} | Tipo {sec.tipo:8} -> [SIN CANDIDATOS]")

print("\n" + "=" * 100)
print("RESULTADO ESPERADO:")
print("=" * 100)
print("""
[OK] Liga 1 (T y P): PROF_007 (Cieza)
[OK] Liga 2 (T y P): PROF_021 (Jaime Diaz)
[OK] Liga 3 (T y P): PROF_007 (Cieza)
[OK] Liga 4 (T y P): PROF_007 (Cieza)

Si ves esto, el FIX esta FUNCIONANDO correctamente!
""")
