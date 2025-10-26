"""
Mostrar qué profesores NO tienen restricciones de horario
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal
from sqlalchemy import text
import json

session = SessionLocal()

# Cargar horario
with open('horario_generado_20251022_015751.json', 'r') as f:
    horario = json.load(f)

# Profesores usados en el horario
profesores_en_horario = set(a['professor_id'] for a in horario['asignaciones'])

# Profesores con restricciones
profs_con_restricciones = set()
result = session.execute(text("SELECT DISTINCT professor_id FROM professor_restrictions"))
for row in result:
    profs_con_restricciones.add(row[0])

# Profesores SIN restricciones
profs_sin_restricciones = profesores_en_horario - profs_con_restricciones

print("="*80)
print(f"PROFESORES SIN RESTRICCIONES DE HORARIO ({len(profs_sin_restricciones)} de {len(profesores_en_horario)})")
print("="*80)

if profs_sin_restricciones:
    prof_ids_str = ','.join(str(pid) for pid in profs_sin_restricciones)
    detalles = session.execute(text(f"""
        SELECT id, codigo, nombre_completo
        FROM professors
        WHERE id IN ({prof_ids_str})
        ORDER BY codigo
    """)).fetchall()
    
    print("\nEstos profesores pueden ser asignados a CUALQUIER horario:")
    print("(Lunes-Sábado, 7:00-21:35, sin restricciones)\n")
    
    for prof in detalles:
        asigs_count = sum(1 for a in horario['asignaciones'] if a['professor_id'] == prof.id)
        print(f"{prof.codigo:15} {prof.nombre_completo[:50]:50} ({asigs_count} asignaciones)")

print("\n" + "="*80)
print("OPCIONES:")
print("="*80)
print("""
1. Si está OK que estos profesores trabajen cualquier horario:
   ✅ No hacer nada - el sistema funciona correctamente

2. Si necesitas agregar restricciones para estos profesores:
   📋 Proporcióname un archivo Excel/CSV con:
      - Columna: codigo_profesor
      - Columna: dia (Lunes, Martes, etc.)
      - Columna: hora_inicio (ej: 18:00)
      - Columna: hora_fin (ej: 22:00)
   
   Y las cargo automáticamente a la BD

3. Si quieres una restricción general (ej: "todos solo Lun-Vie"):
   📝 Dime qué restricción aplicar y la agrego para todos
""")

session.close()
