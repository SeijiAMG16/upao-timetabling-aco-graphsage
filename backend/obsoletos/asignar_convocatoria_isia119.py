"""
Asignar profesor "convocatoria" (PROF_032, ID: 353) a ISIA119
Para cubrir las teorías T1 y T2 que no fueron asignadas
"""
from app.database import SessionLocal
from app.models import Course, Professor
from sqlalchemy import text

db = SessionLocal()

print("="*80)
print("ASIGNANDO PROFESOR CONVOCATORIA A ISIA119")
print("="*80)

# Verificar que el profesor existe
profesor = db.query(Professor).filter(Professor.id == 353).first()
if not profesor:
    print("❌ ERROR: Profesor ID 353 no encontrado")
    db.close()
    exit(1)

print(f"\n✅ Profesor encontrado: {profesor.codigo} - {profesor.nombre_completo}")

# Verificar que el curso existe
curso = db.query(Course).filter(Course.codigo == 'ISIA119').first()
if not curso:
    print("❌ ERROR: Curso ISIA119 no encontrado")
    db.close()
    exit(1)

print(f"✅ Curso encontrado: {curso.codigo} - {curso.nombre}")
print(f"   Course ID: {curso.id}")

# Verificar si ya existe alguna asignación
existing = db.execute(
    text("""
    SELECT COUNT(*) as count
    FROM professor_course_assignments
    WHERE course_id = :course_id AND professor_id = :professor_id
    """),
    {'course_id': curso.id, 'professor_id': 353}
).fetchone()

if existing[0] > 0:
    print(f"\n⚠️ Ya existen {existing[0]} asignaciones para este profesor en este curso")
    print("   Eliminando asignaciones existentes...")
    db.execute(
        text("""
        DELETE FROM professor_course_assignments
        WHERE course_id = :course_id AND professor_id = :professor_id
        """),
        {'course_id': curso.id, 'professor_id': 353}
    )
    db.commit()
    print("   ✅ Asignaciones anteriores eliminadas")

# Insertar asignaciones para teoría en ambas ligas
print("\n📝 Insertando nuevas asignaciones...")

# Liga 1 - Teoría
db.execute(
    text("""
    INSERT INTO professor_course_assignments 
    (course_id, professor_id, session_type, league, created_at)
    VALUES 
    (:course_id, :professor_id, 'T', 1, NOW())
    """),
    {'course_id': curso.id, 'professor_id': 353}
)
print("   ✅ Asignado: Teoría Liga 1")

# Liga 2 - Teoría
db.execute(
    text("""
    INSERT INTO professor_course_assignments 
    (course_id, professor_id, session_type, league, created_at)
    VALUES 
    (:course_id, :professor_id, 'T', 2, NOW())
    """),
    {'course_id': curso.id, 'professor_id': 353}
)
print("   ✅ Asignado: Teoría Liga 2")

# También asignar laboratorios (ya que el curso requiere laboratorio)
# Liga 1 - Laboratorio
db.execute(
    text("""
    INSERT INTO professor_course_assignments 
    (course_id, professor_id, session_type, league, created_at)
    VALUES 
    (:course_id, :professor_id, 'L', 1, NOW())
    """),
    {'course_id': curso.id, 'professor_id': 353}
)
print("   ✅ Asignado: Laboratorio Liga 1")

# Liga 2 - Laboratorio
db.execute(
    text("""
    INSERT INTO professor_course_assignments 
    (course_id, professor_id, session_type, league, created_at)
    VALUES 
    (:course_id, :professor_id, 'L', 2, NOW())
    """),
    {'course_id': curso.id, 'professor_id': 353}
)
print("   ✅ Asignado: Laboratorio Liga 2")

db.commit()

print("\n" + "="*80)
print("✅ ASIGNACIONES COMPLETADAS")
print("="*80)
print(f"""
Profesor: {profesor.codigo} - {profesor.nombre_completo}
Curso: {curso.codigo} - {curso.nombre}

Asignaciones creadas:
  • Teoría Liga 1
  • Teoría Liga 2
  • Laboratorio Liga 1
  • Laboratorio Liga 2

Ahora puedes regenerar el horario y las secciones de ISIA119 deberían ser asignadas.
""")

db.close()
