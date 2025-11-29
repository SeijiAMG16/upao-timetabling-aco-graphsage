from app.database import SessionLocal
from app.models import CourseSection, Course, ScheduleAssignment

db = SessionLocal()

section_ids = [1553, 1554, 1606, 1607, 1650, 1651, 1678, 1679, 1680, 1681]
secciones = db.query(CourseSection).filter(CourseSection.id.in_(section_ids)).all()

print(f"\n{'='*80}")
print(f"ANÁLISIS DE SECCIONES QUE FALLAN CONSISTENTEMENTE")
print(f"{'='*80}\n")

for s in secciones:
    c = db.query(Course).filter(Course.id == s.course_id).first()
    curso_code = c.codigo if c else "?"
    curso_name = c.nombre if c else "?"
    
    # Buscar asignación del profesor
    assignment = db.query(ScheduleAssignment).filter(ScheduleAssignment.course_section_id == s.id).first()
    prof_id = assignment.professor_id if assignment else "Sin asignar"
    
    print(f"ID={s.id:<5} NRC={s.nrc:<10} Curso={curso_code:<15} {curso_name[:40]:<42}")
    print(f"  Profesor: {prof_id:<5} Liga: {s.league:<2} Tipo: {s.tipo or 'N/A'}")
    print()

db.close()
