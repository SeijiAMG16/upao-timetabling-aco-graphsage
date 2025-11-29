from app.database import SessionLocal
from app.models import ProfessorRestriction, Professor

db = SessionLocal()

print(f"\n{'='*80}")
print(f"RESTRICCIONES DE PROFESORES CON SECCIONES FALLIDAS")
print(f"{'='*80}\n")

for prof_id in [330, 333, 336]:
    prof = db.query(Professor).filter(Professor.id == prof_id).first()
    print(f"\n=== Profesor {prof_id}: {prof.nombre_completo if prof else 'No encontrado'} ===")
    
    restrictions = db.query(ProfessorRestriction).filter(ProfessorRestriction.professor_id == prof_id).all()
    if restrictions:
        for r in restrictions:
            print(f"  Día {r.day}: {r.start_time} - {r.end_time}")
    else:
        print("  ✓ Sin restricciones (disponible todos los días)")

db.close()
