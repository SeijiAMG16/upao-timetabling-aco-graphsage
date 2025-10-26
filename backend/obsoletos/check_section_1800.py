import sys
sys.path.insert(0, r'c:\Users\amaya\Downloads\10mo Ciclo\TESIS\upao-timetabling-aco-graphsage\backend')

from app.config.db import SessionLocal
from app.models import Section, Course

db = SessionLocal()
sec = db.query(Section).filter_by(id=1800).first()
if sec:
    curso = db.query(Course).filter_by(id=sec.course_id).first()
    print(f"Sección 1800:")
    print(f"  Código: {sec.codigo}")
    print(f"  Tipo: {sec.tipo}")
    print(f"  Horas semana: {sec.horas_semana}")
    print(f"  Curso: {curso.codigo if curso else 'N/A'} - {curso.nombre if curso else 'N/A'}")
    print(f"  Modalidad: {curso.modalidad if curso else 'N/A'}")
    print(f"  Requiere lab: {curso.requiere_laboratorio if curso else 'N/A'}")
else:
    print("No se encontró la sección 1800")

db.close()
