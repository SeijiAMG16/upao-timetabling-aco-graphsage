import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

print("=" * 100)
print("SECCIONES ACTIVAS DE ISIA126 (TALLER INTEGRADOR II)")
print("=" * 100)

result = db.execute(text("""
    SELECT cs.id, c.codigo, cs.tipo, cs.league, cs.alumnos_proyectados
    FROM course_sections cs
    JOIN courses c ON cs.course_id = c.id
    WHERE c.codigo = 'ISIA126' AND cs.activa = 1 AND cs.alumnos_proyectados > 0
    ORDER BY cs.id
"""))

for row in result:
    print(f"  ID {row[0]:4d} | {row[1]} | Tipo: {row[2]:12s} | Liga {row[3]} | {row[4]} alumnos")

print("\n" + "=" * 100)
print("ASIGNACIONES DE PROFESORES PARA ISIA126")
print("=" * 100)

result2 = db.execute(text("""
    SELECT 
        p.id,
        p.nombre_completo,
        pca.session_type,
        pca.league
    FROM professor_course_assignments pca
    JOIN professors p ON pca.professor_id = p.id
    JOIN courses c ON pca.course_id = c.id
    WHERE c.codigo = 'ISIA126'
    ORDER BY pca.session_type, pca.league
"""))

for row in result2:
    print(f"  {row[1]:40s} | Tipo: {row[2]} | Liga {row[3]}")

# Ahora verificar cuántas secciones virtuales se generarían
from app.aco_graphsage.graph_builder import TimetableGraphBuilder

builder = TimetableGraphBuilder(db)

# Simular construcción del grafo para ver las secciones generadas
sections = builder._load_sections()

print("\n" + "=" * 100)
print("SECCIONES GENERADAS (REALES + VIRTUALES) PARA ISIA126")
print("=" * 100)

isia126_sections = [s for s in sections if s.course.codigo == 'ISIA126']
print(f"\nTotal secciones reales: {len(isia126_sections)}")

# Ahora generar instancias
classrooms = builder._load_classrooms()
instances = builder._generate_section_instances(sections, classrooms)

isia126_instances = [inst for inst in instances if inst.course.codigo == 'ISIA126']
print(f"Total instancias (reales + virtuales): {len(isia126_instances)}")

print("\nDetalle de instancias:")
for inst in isia126_instances:
    virtual_marker = " (VIRTUAL)" if inst.id < 0 else ""
    print(f"  ID {inst.id:4d} | {inst.course.codigo} | Tipo: {inst.tipo:12s} | Liga {inst.league} | {inst.num_students} alumnos{virtual_marker}")

db.close()
