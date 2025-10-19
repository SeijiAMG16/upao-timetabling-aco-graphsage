"""
Asignar cursos sin profesor al placeholder PROF_032
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:sistemas@localhost:3306/upao_timetabling")
engine = create_engine(DATABASE_URL, echo=False)
Session = sessionmaker(bind=engine)
session = Session()

print("=" * 80)
print("ASIGNACIÓN DE CURSOS PENDIENTES A PROF_032")
print("=" * 80)
print()

# 1. Obtener ID de PROF_032
result = session.execute(text("""
    SELECT id FROM professors WHERE codigo = 'PROF_032'
"""))
prof_row = result.fetchone()
if not prof_row:
    print("❌ ERROR: Profesor PROF_032 no encontrado")
    session.close()
    exit(1)

prof_id = prof_row.id
print(f"✅ Profesor PROF_032 encontrado (ID: {prof_id})")
print()

# 2. Obtener cursos sin asignación
result = session.execute(text("""
    SELECT DISTINCT c.id, c.codigo, c.nombre
    FROM course_sections cs
    INNER JOIN courses c ON cs.course_id = c.id
    LEFT JOIN professor_course_assignments pca ON cs.course_id = pca.course_id
    WHERE cs.activa = 1 
        AND cs.alumnos_proyectados > 0
        AND pca.id IS NULL
    ORDER BY c.codigo
"""))

cursos_pendientes = result.fetchall()
print(f"📋 Cursos a asignar: {len(cursos_pendientes)}")
print()

# 3. Asignar cada curso para todos los tipos de sesión
for curso in cursos_pendientes:
    print(f"   Asignando: {curso.codigo} - {curso.nombre[:50]}")
    
    # Insertar asignación para T, P, L (todos los tipos)
    for session_type in ['T', 'P', 'L']:
        session.execute(text("""
            INSERT INTO professor_course_assignments 
                (professor_id, course_id, session_type, league, created_at)
            VALUES 
                (:prof_id, :course_id, :session_type, 1, NOW())
        """), {
            "prof_id": prof_id,
            "course_id": curso.id,
            "session_type": session_type,
        })

session.commit()
print()
print("=" * 80)
print("✅ ASIGNACIONES COMPLETADAS")
print("=" * 80)
print(f"Total: {len(cursos_pendientes)} cursos asignados a PROF_032")
print()

# Verificar resultado
result = session.execute(text("""
    SELECT COUNT(*) as total
    FROM course_sections cs
    LEFT JOIN professor_course_assignments pca ON cs.course_id = pca.course_id
    WHERE cs.activa = 1 
        AND cs.alumnos_proyectados > 0
        AND pca.id IS NULL
"""))
sin_asignar = result.fetchone().total
print(f"Secciones sin asignar restantes: {sin_asignar}")

session.close()
