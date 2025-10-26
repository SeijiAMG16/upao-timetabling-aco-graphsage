"""
Script simple: identificar sección -12
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from app.database import SessionLocal
from app.models import CourseSection, Course

# Buscar secciones que podrían generar -12 al dividirse
session = SessionLocal()
try:
    print("\nBUSCANDO SECCIONES QUE SE DIVIDEN (y generan IDs negativos):\n")
    
    # Obtener capacidad máxima de aulas
    from app.models import Classroom
    max_capacity = session.query(Classroom).filter(Classroom.active == True).order_by(Classroom.capacidad.desc()).first()
    print(f"Capacidad maxima de aula: {max_capacity.capacidad if max_capacity else 'N/A'}")
    
    # Buscar secciones con muchos estudiantes
    sections = session.query(CourseSection).filter(
        CourseSection.activa == True,
        CourseSection.alumnos_proyectados > 50  # Más de 50 estudiantes
    ).order_by(CourseSection.alumnos_proyectados.desc()).all()
    
    print(f"\nSecciones con >50 estudiantes (candidatas a dividirse):\n")
    count = 0
    for sec in sections[:15]:  # Top 15
        print(f"ID {sec.id}: {sec.course.codigo}-{sec.tipo}-Liga{sec.league} - {sec.alumnos_proyectados} estudiantes")
        count += 1
        if count >= 12:  # Si hay 12 que se dividen, la #12 sería -12
            print(f"  ^^^ Esta podría generar la sección virtual -12")
    
finally:
    session.close()
