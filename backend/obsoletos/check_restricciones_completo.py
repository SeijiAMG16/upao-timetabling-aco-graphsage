"""
Verificar restricciones de profesores y timeslots en BD
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal
from sqlalchemy import text
import json

session = SessionLocal()

print("="*80)
print("VERIFICACIÓN COMPLETA DE RESTRICCIONES Y TIMESLOTS")
print("="*80)

# 1. Verificar tabla de restricciones de profesores
print("\n1. TABLA: professor_restrictions")
print("-"*80)

result = session.execute(text("""
    SELECT COUNT(*) as total
    FROM information_schema.tables 
    WHERE table_schema = DATABASE() 
    AND table_name = 'professor_restrictions'
""")).fetchone()

if result[0] > 0:
    print("✅ Tabla existe")
    
    total = session.execute(text('SELECT COUNT(*) FROM professor_restrictions')).fetchone()[0]
    print(f"\nTotal restricciones: {total}")
    
    # Ver algunos ejemplos
    data = session.execute(text("""
        SELECT pr.*, p.codigo, p.nombre_completo
        FROM professor_restrictions pr
        JOIN professors p ON pr.professor_id = p.id
        LIMIT 20
    """)).fetchall()
    
    print("\nPrimeros 20 registros:")
    for row in data:
        print(f"  Prof {row.codigo} ({row.nombre_completo}): Day={row.day}, {row.start_time}-{row.end_time}")
    
else:
    print("❌ Tabla NO existe")

# 2. Verificar tabla de timeslots
print("\n\n2. TABLA: time_slots")
print("-"*80)

result = session.execute(text("""
    SELECT COUNT(*) as total
    FROM information_schema.tables 
    WHERE table_schema = DATABASE() 
    AND table_name = 'time_slots'
""")).fetchone()

if result[0] > 0:
    print("✅ Tabla existe")
    
    total = session.execute(text('SELECT COUNT(*) FROM time_slots')).fetchone()[0]
    print(f"\nTotal timeslots: {total}")
    
    # Ver estructura
    columns = session.execute(text("""
        SHOW COLUMNS FROM time_slots
    """)).fetchall()
    
    print("\nColumnas:")
    for col in columns:
        print(f"  - {col[0]}: {col[1]}")
    
    # Ver datos agrupados
    data = session.execute(text("""
        SELECT dia_semana, COUNT(*) as bloques, 
               MIN(hora_inicio) as primera, 
               MAX(hora_fin) as ultima
        FROM time_slots
        GROUP BY dia_semana
        ORDER BY dia_semana
    """)).fetchall()
    
    print("\nTimeslots por día:")
    dias = {1: 'Lunes', 2: 'Martes', 3: 'Miércoles', 4: 'Jueves', 5: 'Viernes', 6: 'Sábado'}
    for row in data:
        dia_nombre = dias.get(row.dia_semana, f'Día {row.dia_semana}')
        print(f"  {dia_nombre}: {row.bloques} bloques ({row.primera} - {row.ultima})")
else:
    print("❌ Tabla NO existe")

# 3. Verificar Cieza (328)
print("\n\n3. RESTRICCIONES DEL PROFESOR CIEZA (ID 328)")
print("-"*80)

restricciones = session.execute(text("""
    SELECT *
    FROM professor_restrictions
    WHERE professor_id = 328
    ORDER BY day, start_time
""")).fetchall()

if restricciones:
    print(f"Total restricciones: {len(restricciones)}")
    for r in restricciones:
        dias = {1: 'Lun', 2: 'Mar', 3: 'Mié', 4: 'Jue', 5: 'Vie', 6: 'Sáb'}
        dia_nombre = dias.get(r.day, f'Día {r.day}')
        print(f"  {dia_nombre} {r.start_time} - {r.end_time}")
else:
    print("❌ NO tiene restricciones configuradas")

# 4. Verificar si el horario generado respeta las restricciones
print("\n\n4. VERIFICAR HORARIO GENERADO")
print("-"*80)

try:
    with open('horario_generado_20251022_015751.json', 'r') as f:
        horario = json.load(f)
    
    asignaciones_cieza = [a for a in horario['asignaciones'] if a['professor_id'] == 328]
    print(f"\nAsignaciones de Cieza: {len(asignaciones_cieza)}")
    
    if asignaciones_cieza:
        print("\nDetalle de asignaciones:")
        for asig in asignaciones_cieza:
            print(f"\n  Curso: {asig['course_code']} - Liga {asig['league_id']}")
            print(f"  Timeslots: {asig['timeslot_ids']}")
            
            # Obtener info de los timeslots
            for ts_id in asig['timeslot_ids']:
                ts_info = session.execute(text(f"""
                    SELECT dia_semana, hora_inicio, hora_fin
                    FROM time_slots
                    WHERE id = {ts_id}
                """)).fetchone()
                
                if ts_info:
                    dias = {1: 'Lun', 2: 'Mar', 3: 'Mié', 4: 'Jue', 5: 'Vie', 6: 'Sáb'}
                    dia_nombre = dias.get(ts_info.dia_semana, f'Día {ts_info.dia_semana}')
                    print(f"    - TS {ts_id}: {dia_nombre} {ts_info.hora_inicio} - {ts_info.hora_fin}")
                    
                    # Verificar si hay restricción en este horario
                    conflicto = session.execute(text(f"""
                        SELECT *
                        FROM professor_restrictions
                        WHERE professor_id = 328
                        AND day = {ts_info.dia_semana}
                        AND (
                            (start_time <= '{ts_info.hora_inicio}' AND end_time > '{ts_info.hora_inicio}')
                            OR
                            (start_time < '{ts_info.hora_fin}' AND end_time >= '{ts_info.hora_fin}')
                            OR
                            (start_time >= '{ts_info.hora_inicio}' AND end_time <= '{ts_info.hora_fin}')
                        )
                    """)).fetchone()
                    
                    if conflicto:
                        print(f"      ❌ CONFLICTO: Profesor tiene restricción {conflicto.start_time}-{conflicto.end_time}")
                    else:
                        print(f"      ✅ OK: No hay conflicto")

except FileNotFoundError:
    print("❌ No se encontró el archivo de horario generado")

session.close()
