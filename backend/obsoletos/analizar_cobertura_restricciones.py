"""
Mostrar qué profesores TIENEN restricciones y cuáles NO
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal
from sqlalchemy import text
import json

session = SessionLocal()

print("="*80)
print("ANÁLISIS DE COBERTURA DE RESTRICCIONES")
print("="*80)

# 1. Cargar horario generado
with open('horario_generado_20251022_015751.json', 'r') as f:
    horario = json.load(f)

# 2. Obtener todos los profesores usados en el horario
profesores_en_horario = set()
for asig in horario['asignaciones']:
    profesores_en_horario.add(asig['professor_id'])

print(f"\nProfesores utilizados en el horario: {len(profesores_en_horario)}")

# 3. Ver cuáles tienen restricciones
restricciones_raw = session.execute(text("""
    SELECT DISTINCT professor_id, p.codigo, p.nombre_completo
    FROM professor_restrictions pr
    JOIN professors p ON pr.professor_id = p.id
    ORDER BY p.codigo
""")).fetchall()

profs_con_restricciones = {r.professor_id for r in restricciones_raw}

print(f"Profesores CON restricciones en BD: {len(profs_con_restricciones)}")

# 4. Ver cuáles NO tienen restricciones
profs_sin_restricciones = profesores_en_horario - profs_con_restricciones

print(f"\n{'='*80}")
print(f"PROFESORES SIN RESTRICCIONES CONFIGURADAS: {len(profs_sin_restricciones)}")
print(f"{'='*80}")

if profs_sin_restricciones:
    # Obtener detalles
    prof_ids_str = ','.join(str(pid) for pid in profs_sin_restricciones)
    detalles = session.execute(text(f"""
        SELECT id, codigo, nombre_completo
        FROM professors
        WHERE id IN ({prof_ids_str})
        ORDER BY codigo
    """)).fetchall()
    
    for prof in detalles:
        # Contar asignaciones
        asigs_count = sum(1 for a in horario['asignaciones'] if a['professor_id'] == prof.id)
        print(f"\n  {prof.codigo} - {prof.nombre_completo}")
        print(f"    Asignaciones en horario: {asigs_count}")
        
        # Mostrar algunas asignaciones
        asigs = [a for a in horario['asignaciones'] if a['professor_id'] == prof.id]
        for asig in asigs[:3]:  # Mostrar max 3
            print(f"    - {asig['course_code']} Liga {asig['league_id']}: Timeslots {asig['timeslot_ids']}")
        if len(asigs) > 3:
            print(f"    ... y {len(asigs) - 3} más")

# 5. Mostrar profesores con restricciones
print(f"\n{'='*80}")
print(f"PROFESORES CON RESTRICCIONES CONFIGURADAS: {len(profs_con_restricciones)}")
print(f"{'='*80}")

for r in restricciones_raw:
    if r.professor_id in profesores_en_horario:
        asigs_count = sum(1 for a in horario['asignaciones'] if a['professor_id'] == r.professor_id)
        print(f"\n  {r.codigo} - {r.nombre_completo}")
        print(f"    Asignaciones: {asigs_count}")
        
        # Ver restricciones
        restricciones = session.execute(text(f"""
            SELECT day, start_time, end_time
            FROM professor_restrictions
            WHERE professor_id = {r.professor_id}
            ORDER BY day, start_time
        """)).fetchall()
        
        print(f"    Restricciones ({len(restricciones)} registros):")
        for rest in restricciones[:3]:  # Max 3
            print(f"      {rest.day}: {rest.start_time} - {rest.end_time}")
        if len(restricciones) > 3:
            print(f"      ... y {len(restricciones) - 3} más")

session.close()
