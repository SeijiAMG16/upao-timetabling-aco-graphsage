"""
Investigar las secciones que consistentemente NO se pueden asignar
"""
from app.database import SessionLocal
from app.models import CourseSection, ProfessorCourseAssignment

sections_problem = [-12, 1778, 1794, 1795, 1812, 1813, 1815, 1820, 1821, 1818, 1819]

session = SessionLocal()
try:
    for sid in sections_problem:
        sec = session.query(CourseSection).filter_by(id=sid).first()
        
        if sec is None:
            print(f"\nSección {sid}: VIRTUAL (no existe en DB)")
            continue
        
        # Buscar profesores asignados
        assignments = session.query(ProfessorCourseAssignment).filter_by(
            course_id=sec.course_id,
            session_type=sec.tipo,
            league=sec.league
        ).all()
        
        prof_list = [a.professor.apellidos for a in assignments] if assignments else ["NINGUNO"]
        
        print(f"\nSección {sid}:")
        print(f"  Curso: {sec.course.codigo} - {sec.course.nombre}")
        print(f"  Tipo: {sec.tipo}, Liga: {sec.league}")
        print(f"  Alumnos proyectados: {sec.alumnos_proyectados}")
        print(f"  Profesores asignados: {', '.join(prof_list)}")
        
finally:
    session.close()
