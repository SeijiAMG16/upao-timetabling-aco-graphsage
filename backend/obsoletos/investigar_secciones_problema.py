"""
Investigar secciones problemáticas que bloquean la generación
"""
from app.database import get_db
from sqlalchemy import text

db = next(get_db())

print("=" * 100)
print("INVESTIGACION: Secciones que fallan en ACO")
print("=" * 100)

# Secciones problemáticas identificadas
problem_sections = [1713, 1778]

print("\n[SECCIONES PROBLEMATICAS]")
result = db.execute(text("""
    SELECT 
        cs.id,
        cs.seccion,
        c.codigo,
        c.nombre,
        cs.tipo,
        cs.league,
        cs.alumnos_proyectados,
        c.id as course_id
    FROM course_sections cs
    JOIN courses c ON cs.course_id = c.id
    WHERE cs.id IN (1713, 1778)
    ORDER BY cs.id
"""))

sections_info = list(result)
for s in sections_info:
    print(f"\nID: {s.id} | Seccion: {s.seccion}")
    print(f"  Curso: {s.codigo} - {s.nombre}")
    print(f"  Tipo: {s.tipo} | Liga: {s.league}")
    print(f"  Alumnos proyectados: {s.alumnos_proyectados}")
    print(f"  Course ID: {s.course_id}")

# Verificar asignaciones de profesores para estos cursos
print("\n" + "=" * 100)
print("ASIGNACIONES DE PROFESORES")
print("=" * 100)

for s in sections_info:
    print(f"\n[CURSO: {s.codigo} - {s.nombre}]")
    
    # Buscar asignaciones
    result_assign = db.execute(text(f"""
        SELECT 
            pca.session_type,
            pca.league,
            p.codigo as prof_codigo,
            p.nombre_completo
        FROM professor_course_assignments pca
        JOIN professors p ON pca.professor_id = p.id
        WHERE pca.course_id = {s.course_id}
        ORDER BY pca.league, pca.session_type
    """))
    
    assignments = list(result_assign)
    if assignments:
        print(f"  Total asignaciones: {len(assignments)}")
        for a in assignments:
            print(f"    {a.session_type} | Liga {a.league} | {a.prof_codigo} - {a.nombre_completo}")
    else:
        print(f"  [ERROR] NO HAY ASIGNACIONES PARA ESTE CURSO!")

# Verificar el mapeo de tipo
print("\n" + "=" * 100)
print("ANALISIS DE TIPO DE SESION")
print("=" * 100)

for s in sections_info:
    print(f"\nSeccion {s.id}:")
    print(f"  Tipo en BD: '{s.tipo}'")
    print(f"  Normalizado esperado: 'L' (laboratorio)")
    
    # Verificar si existe asignación con tipo 'L'
    has_L = any(a.session_type == 'L' for a in db.execute(text(f"""
        SELECT session_type FROM professor_course_assignments 
        WHERE course_id = {s.course_id} AND league = {s.league}
    """)))
    
    print(f"  ¿Tiene asignaciones con tipo 'L'? {has_L}")

print("\n" + "=" * 100)
print("DIAGNOSTICO")
print("=" * 100)
print("""
PROBLEMA POTENCIAL:
1. Las secciones tienen tipo "laboratorio" en BD
2. Se normaliza a 'L' en graph_builder._map_section_type()
3. Pero las asignaciones en professor_course_assignments pueden tener tipo diferente
4. Si no coinciden, NO encuentra candidatos

SOLUCION:
- Verificar que las asignaciones usen el mismo tipo normalizado
- O ajustar la lógica de búsqueda para ser más flexible con tipos
""")
