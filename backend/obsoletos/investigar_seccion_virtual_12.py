import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from app.models import CourseSection, Professor, Course
from sqlalchemy import func, text

db = SessionLocal()

# Las secciones virtuales son < 0 y se generan para cubrir horas fragmentadas
# Necesitamos ver cuál es el curso que genera la sección -12

print("=" * 100)
print("INVESTIGANDO SECCIONES VIRTUALES")
print("=" * 100)

# Obtener secciones con IDs negativos (no existen en BD, se generan en memoria)
# Pero podemos buscar el patrón: se generan en _generate_section_instances

# Busquemos cursos con horas muy específicas que generen múltiples instancias
query = text("""
    SELECT 
        cs.id,
        c.codigo,
        c.nombre,
        cs.tipo,
        cs.league,
        cs.alumnos_proyectados,
        csh.duration_blocks
    FROM course_sections cs
    JOIN courses c ON cs.course_id = c.id
    LEFT JOIN course_session_hours csh ON cs.course_id = csh.course_id AND cs.tipo = csh.session_type
    WHERE cs.activa = 1 AND cs.alumnos_proyectados > 0
    ORDER BY cs.id DESC
    LIMIT 20
""")

result = db.execute(query)
print("\nUltimas 20 secciones activas:")
for row in result:
    print(f"  ID {row[0]:4d} | {row[1]:8s} | {row[2]:40s} | {row[3]:12s} | Liga {row[4]} | {row[5]:3d} alumnos | {row[6]} bloques")

# Las secciones virtuales se generan cuando:
# duration_blocks > num_blocks_per_session (típicamente 2)
# Por ejemplo: un curso de 4 bloques genera 2 secciones virtuales de 2 bloques cada una

print("\n" + "=" * 100)
print("CURSOS QUE GENERAN SECCIONES VIRTUALES (duration_blocks > 2):")
print("=" * 100)

query2 = text("""
    SELECT 
        c.id,
        c.codigo,
        c.nombre,
        csh.session_type,
        csh.duration_blocks,
        COUNT(cs.id) as num_secciones
    FROM courses c
    JOIN course_session_hours csh ON c.id = csh.course_id
    LEFT JOIN course_sections cs ON c.id = cs.course_id 
        AND cs.tipo = csh.session_type 
        AND cs.activa = 1 
        AND cs.alumnos_proyectados > 0
    WHERE csh.duration_blocks > 2
    GROUP BY c.id, csh.session_type
    ORDER BY csh.duration_blocks DESC, num_secciones DESC
""")

result2 = db.execute(query2)
for row in result2:
    course_id, codigo, nombre, tipo, bloques, num_secciones = row
    num_virtuales = (bloques // 2) - 1  # -1 porque la primera NO es virtual
    print(f"\n{codigo} - {nombre}")
    print(f"  Tipo: {tipo} | Bloques: {bloques} | Secciones reales: {num_secciones}")
    print(f"  -> Genera {num_virtuales} secciones virtuales por cada sección real")
    
    # Buscar profesores asignados
    query_prof = text("""
        SELECT p.id, p.nombre_completo, pca.session_type, pca.league
        FROM professor_course_assignments pca
        JOIN professors p ON pca.professor_id = p.id
        WHERE pca.course_id = :course_id AND pca.session_type = :tipo
        ORDER BY pca.league
    """)
    prof_result = db.execute(query_prof, {"course_id": course_id, "tipo": tipo})
    profs = list(prof_result)
    
    if profs:
        print(f"  Profesores asignados:")
        for p_id, p_nombre, p_tipo, p_liga in profs:
            print(f"    - {p_nombre} ({p_tipo}, Liga {p_liga})")
    else:
        print(f"  *** SIN PROFESORES ASIGNADOS PARA TIPO '{tipo}' ***")

db.close()
