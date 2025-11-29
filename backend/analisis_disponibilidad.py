from app.database import SessionLocal
from app.models import CourseSection, Course, ScheduleAssignment, TimeSlot, ProfessorRestriction
from datetime import time

db = SessionLocal()

print(f"\n{'='*80}")
print(f"ANÁLISIS PROFUNDO DE SECCIONES FALLIDAS")
print(f"{'='*80}\n")

section_ids = [1553, 1554, 1606, 1607, 1650, 1651, 1678, 1679, 1680, 1681]
secciones = db.query(CourseSection).filter(CourseSection.id.in_(section_ids)).all()

# Agrupar por profesor
prof_sections = {}
for s in secciones:
    assignment = db.query(ScheduleAssignment).filter(ScheduleAssignment.course_section_id == s.id).first()
    prof_id = assignment.professor_id if assignment else None
    if prof_id:
        if prof_id not in prof_sections:
            prof_sections[prof_id] = []
        prof_sections[prof_id].append(s)

# Analizar cada profesor
for prof_id, sections in prof_sections.items():
    restrictions = db.query(ProfessorRestriction).filter(ProfessorRestriction.professor_id == prof_id).all()
    
    print(f"\n{'='*70}")
    print(f"Profesor {prof_id} - {len(sections)} secciones sin asignar")
    print(f"{'='*70}")
    
    # Mostrar restricciones
    print("\nRestricciones:")
    dias_bloqueados = {}
    for r in restrictions:
        if r.day not in dias_bloqueados:
            dias_bloqueados[r.day] = []
        dias_bloqueados[r.day].append((r.start_time, r.end_time))
        print(f"  {r.day}: {r.start_time} - {r.end_time}")
    
    # Calcular ventanas disponibles
    dias_semana = ['LUNES', 'MARTES', 'MIÉRCOLES', 'JUEVES', 'VIERNES', 'SÁBADO']
    print("\nVentanas potencialmente disponibles:")
    for dia in dias_semana:
        if dia not in dias_bloqueados:
            print(f"  ✓ {dia}: TODO EL DÍA (07:00-22:30)")
        else:
            # Solo indicar que hay restricciones
            print(f"  ✗ {dia}: PARCIAL O BLOQUEADO")
    
    # Mostrar secciones
    print(f"\nSecciones que requieren asignación ({len(sections)}):")
    for s in sections:
        c = db.query(Course).filter(Course.id == s.course_id).first()
        print(f"  - ID {s.id}: {c.codigo if c else '?'} (Liga {s.league}, Tipo: {s.tipo or 'N/A'})")

# Contar franjas totales disponibles vs bloqueadas
print(f"\n{'='*80}")
print(f"RESUMEN GENERAL")
print(f"{'='*80}\n")

all_timeslots = db.query(TimeSlot).all()
print(f"Total de franjas horarias en BD: {len(all_timeslots)}")

for prof_id in prof_sections.keys():
    restrictions = db.query(ProfessorRestriction).filter(ProfessorRestriction.professor_id == prof_id).all()
    
    # Contar días con restricciones
    dias_bloqueados_count = len(set(r.day for r in restrictions))
    dias_disponibles = 6 - dias_bloqueados_count
    
    print(f"\nProfesor {prof_id}:")
    print(f"  Días con restricciones: {dias_bloqueados_count}/6")
    print(f"  Días completamente libres: {dias_disponibles}/6")
    print(f"  Secciones sin asignar: {len(prof_sections[prof_id])}")

db.close()
