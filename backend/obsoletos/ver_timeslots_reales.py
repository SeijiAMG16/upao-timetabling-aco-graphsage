"""
Verificar los timeslots reales en la base de datos
"""
from app.database import SessionLocal
from app.models import TimeSlot

session = SessionLocal()

print("\n" + "="*70)
print("TIMESLOTS REALES EN LA BASE DE DATOS")
print("="*70)

slots = session.query(TimeSlot).order_by(
    TimeSlot.dia_semana, 
    TimeSlot.hora_inicio
).all()

print(f"\nTotal timeslots: {len(slots)}")
print("\nPrimeros 20 timeslots:")
print("-"*70)

for s in slots[:20]:
    dia_name = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"][s.dia_semana - 1] if 1 <= s.dia_semana <= 6 else str(s.dia_semana)
    print(f"ID: {s.id:3d} | {dia_name:10s} | {str(s.hora_inicio)[:5]} - {str(s.hora_fin)[:5]}")

session.close()
