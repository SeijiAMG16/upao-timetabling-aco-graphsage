import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal
from sqlalchemy import text

session = SessionLocal()

# Buscar código del curso HUMA900
result = session.execute(text("SELECT id, codigo, nombre FROM courses WHERE codigo = 'HUMA900'")).fetchone()

if result:
    course_id, code, name = result
    print(f"HUMA900 encontrado: ID={course_id}, Nombre={name}")
    
    # Buscar asignaciones de profesores
    assignments = session.execute(text(f"""
        SELECT professor_id, session_type, league
        FROM professor_course_assignments
        WHERE course_id = '{course_id}'
        ORDER BY league, session_type
    """)).fetchall()
    
    print(f"\nAsignaciones de HUMA900 ({len(assignments)}):")
    for prof_id, session_type, league in assignments:
        # Obtener nombre del profesor
        prof = session.execute(text(f"SELECT codigo, nombre FROM professors WHERE id = {prof_id}")).fetchone()
        prof_code, prof_name = prof if prof else ('?', '?')
        print(f"  Liga {league} - Tipo {session_type}: Profesor {prof_id} ({prof_code} - {prof_name})")
else:
    print("⚠️ HUMA900 NO encontrado en la base de datos")

session.close()
