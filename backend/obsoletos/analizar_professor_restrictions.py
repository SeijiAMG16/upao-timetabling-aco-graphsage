"""
Verificar TODAS las restricciones en professor_restrictions
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal
from sqlalchemy import text

session = SessionLocal()

print("="*80)
print("ANÁLISIS COMPLETO DE professor_restrictions")
print("="*80)

# 1. Total de registros
total = session.execute(text("SELECT COUNT(*) FROM professor_restrictions")).fetchone()[0]
print(f"\nTotal registros en professor_restrictions: {total}")

# 2. Profesores únicos
profesores_unicos = session.execute(text("""
    SELECT COUNT(DISTINCT professor_id) FROM professor_restrictions
""")).fetchone()[0]
print(f"Profesores únicos con restricciones: {profesores_unicos}")

# 3. Total de profesores en la tabla professors
total_profesores = session.execute(text("SELECT COUNT(*) FROM professors")).fetchone()[0]
print(f"Total profesores en BD: {total_profesores}")

# 4. Ver estructura de las restricciones
print("\n" + "="*80)
print("MUESTRA DE RESTRICCIONES (primeras 20)")
print("="*80)

restricciones = session.execute(text("""
    SELECT pr.id, pr.professor_id, p.codigo, p.nombre_completo, 
           pr.day, pr.start_time, pr.end_time
    FROM professor_restrictions pr
    JOIN professors p ON pr.professor_id = p.id
    ORDER BY pr.professor_id, pr.day, pr.start_time
    LIMIT 20
""")).fetchall()

for r in restricciones:
    print(f"ID {r.id:4} | Prof {r.professor_id:3} ({r.codigo:15}) | {r.day:15} {r.start_time} - {r.end_time}")

# 5. Ver distribución por profesor
print("\n" + "="*80)
print("DISTRIBUCIÓN DE RESTRICCIONES POR PROFESOR")
print("="*80)

dist = session.execute(text("""
    SELECT p.id, p.codigo, p.nombre_completo, COUNT(*) as num_restricciones
    FROM professor_restrictions pr
    JOIN professors p ON pr.professor_id = p.id
    GROUP BY p.id, p.codigo, p.nombre_completo
    ORDER BY num_restricciones DESC, p.codigo
""")).fetchall()

print(f"\nTotal profesores: {len(dist)}\n")

for prof in dist:
    print(f"{prof.codigo:15} {prof.nombre_completo[:40]:40} | {prof.num_restricciones:2} restricciones")

# 6. Verificar si hay profesores SIN restricciones que estén siendo usados
print("\n" + "="*80)
print("PROFESORES SIN RESTRICCIONES")
print("="*80)

sin_restricciones = session.execute(text("""
    SELECT p.id, p.codigo, p.nombre_completo
    FROM professors p
    WHERE NOT EXISTS (
        SELECT 1 FROM professor_restrictions pr 
        WHERE pr.professor_id = p.id
    )
    ORDER BY p.codigo
""")).fetchall()

print(f"\nTotal profesores SIN restricciones: {len(sin_restricciones)}\n")

if sin_restricciones:
    # Verificar cuáles están siendo usados
    import json
    with open('horario_generado_20251022_015751.json', 'r') as f:
        horario = json.load(f)
    
    profesores_en_horario = set(a['professor_id'] for a in horario['asignaciones'])
    
    print("Profesores SIN restricciones que ESTÁN en el horario generado:")
    count = 0
    for prof in sin_restricciones:
        if prof.id in profesores_en_horario:
            asigs = sum(1 for a in horario['asignaciones'] if a['professor_id'] == prof.id)
            print(f"  {prof.codigo:15} {prof.nombre_completo[:40]:40} ({asigs} asignaciones)")
            count += 1
    
    if count == 0:
        print("  ✅ NINGUNO - Todos los profesores en el horario tienen restricciones")
    else:
        print(f"\n  ⚠️ {count} profesores sin restricciones están siendo usados")

session.close()
