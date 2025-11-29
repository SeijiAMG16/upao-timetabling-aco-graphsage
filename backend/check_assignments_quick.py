from app.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
result = db.execute(text('SELECT COUNT(*) FROM professor_course_assignments'))
count = result.fetchone()[0]
print(f'Total asignaciones en BD: {count}')
if count == 0:
    print('⚠️ TABLA VACÍA')
    print('Ejecutar: python sincronizar_asignaciones.py')
db.close()
