import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.models import CourseSection, Course

engine = create_engine('mysql+pymysql://root:sistemas@localhost:3306/upao_timetabling', echo=False)
Session = sessionmaker(bind=engine)
session = Session()

# Buscar sección 1815 y su curso
seccion = session.query(CourseSection).filter_by(id=1815).first()
if seccion:
    curso = session.query(Course).filter_by(id=seccion.course_id).first()
    print(f"Sección 1815:")
    print(f"  Curso: {curso.codigo} - {curso.nombre}")
    print(f"  Modalidad: '{curso.modalidad}'")
    print(f"  Tipo sección: {seccion.tipo}")
    print(f"  Liga: {seccion.league}")
    print(f"  Estudiantes proyectados: {seccion.alumnos_proyectados}")
else:
    print("No se encontró sección 1815")

# Buscar todas las secciones NO_PRESENCIAL
print("\n" + "="*80)
print("CURSOS CON MODALIDAD NO_PRESENCIAL:")
print("="*80)
cursos_virtuales = session.query(Course).filter(
    (Course.modalidad == 'NO_PRESENCIAL') | (Course.modalidad == 'no_presencial')
).all()

print(f"Total cursos virtuales: {len(cursos_virtuales)}")
for curso in cursos_virtuales[:10]:  # Primeros 10
    secciones = session.query(CourseSection).filter_by(course_id=curso.id).count()
    print(f"  {curso.codigo} - {curso.nombre}: {secciones} secciones")

# Contar secciones de cursos virtuales
total_secciones_virtuales = 0
for curso in cursos_virtuales:
    secciones = session.query(CourseSection).filter_by(course_id=curso.id).all()
    total_secciones_virtuales += len(secciones)

print(f"\nTotal secciones virtuales: {total_secciones_virtuales}")

session.close()
