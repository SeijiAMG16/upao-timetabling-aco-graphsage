"""
Verificar TODAS las restricciones de profesores contra el horario generado
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal
from sqlalchemy import text
import json
from collections import defaultdict

session = SessionLocal()

print("="*80)
print("ANÁLISIS DETALLADO DE VIOLACIONES DE RESTRICCIONES")
print("="*80)

# 1. Cargar horario generado
with open('horario_generado_20251022_015751.json', 'r') as f:
    horario = json.load(f)

print(f"\nTotal asignaciones en horario: {len(horario['asignaciones'])}")

# 2. Cargar restricciones de profesores
restricciones_raw = session.execute(text("""
    SELECT pr.*, p.codigo, p.nombre_completo
    FROM professor_restrictions pr
    JOIN professors p ON pr.professor_id = p.id
""")).fetchall()

print(f"Total restricciones en BD: {len(restricciones_raw)}")

# Normalizar días
dia_map = {
    'LUNES': 1, 'LUN': 1,
    'MARTES': 2, 'MAR': 2,
    'MIÉRCOLES': 3, 'MIERCOLES': 3, 'MIE': 3,
    'JUEVES': 4, 'JUE': 4,
    'VIERNES': 5, 'VIE': 5,
    'SÁBADO': 6, 'SABADO': 6, 'SAB': 6
}

# Agrupar restricciones por profesor
restricciones_por_prof = defaultdict(list)
for r in restricciones_raw:
    dia_num = dia_map.get(r.day.upper().strip(), 0)
    if dia_num > 0:
        restricciones_por_prof[r.professor_id].append({
            'dia': dia_num,
            'inicio': r.start_time,
            'fin': r.end_time,
            'codigo': r.codigo,
            'nombre': r.nombre_completo
        })

print(f"\nProfesores con restricciones: {len(restricciones_por_prof)}")

# 3. Verificar cada asignación contra las restricciones
violaciones = []
total_verificadas = 0

for asig in horario['asignaciones']:
    prof_id = asig['professor_id']
    
    if prof_id not in restricciones_por_prof:
        continue
    
    restricciones = restricciones_por_prof[prof_id]
    
    for ts_id in asig['timeslot_ids']:
        total_verificadas += 1
        
        # Obtener info del timeslot
        ts_info = session.execute(text(f"""
            SELECT dia_semana, hora_inicio, hora_fin
            FROM time_slots
            WHERE id = {ts_id}
        """)).fetchone()
        
        if not ts_info:
            continue
        
        # Convertir horas a formato comparable
        def time_to_minutes(t):
            if isinstance(t, str):
                h, m = t.split(':')
                return int(h) * 60 + int(m)
            else:  # timedelta
                return int(t.total_seconds() / 60)
        
        ts_dia = ts_info.dia_semana
        ts_inicio = time_to_minutes(ts_info.hora_inicio)
        ts_fin = time_to_minutes(ts_info.hora_fin)
        
        # Verificar contra restricciones
        for rest in restricciones:
            if rest['dia'] != ts_dia:
                continue
            
            rest_inicio = time_to_minutes(rest['inicio'])
            rest_fin = time_to_minutes(rest['fin'])
            
            # Hay solapamiento?
            if ts_inicio < rest_fin and rest_inicio < ts_fin:
                violaciones.append({
                    'profesor_id': prof_id,
                    'profesor_codigo': rest['codigo'],
                    'profesor_nombre': rest['nombre'],
                    'curso': asig['course_code'],
                    'liga': asig['league_id'],
                    'timeslot_id': ts_id,
                    'dia': ts_dia,
                    'ts_inicio': ts_info.hora_inicio,
                    'ts_fin': ts_info.hora_fin,
                    'restriccion_inicio': rest['inicio'],
                    'restriccion_fin': rest['fin']
                })

print(f"\n{'='*80}")
print(f"RESULTADOS")
print(f"{'='*80}")
print(f"\nAsignaciones verificadas: {total_verificadas}")
print(f"Profesores con restricciones: {len(restricciones_por_prof)}")
print(f"\n❌ VIOLACIONES ENCONTRADAS: {len(violaciones)}")

if violaciones:
    print(f"\n{'='*80}")
    print("DETALLE DE VIOLACIONES")
    print(f"{'='*80}")
    
    dias_nombres = {1: 'Lunes', 2: 'Martes', 3: 'Miércoles', 4: 'Jueves', 5: 'Viernes', 6: 'Sábado'}
    
    # Agrupar por profesor
    por_profesor = defaultdict(list)
    for v in violaciones:
        por_profesor[v['profesor_id']].append(v)
    
    for prof_id, viol_list in sorted(por_profesor.items()):
        v = viol_list[0]
        print(f"\n{v['profesor_codigo']} - {v['profesor_nombre']}")
        print(f"  Total violaciones: {len(viol_list)}")
        
        for v in viol_list[:5]:  # Mostrar primeras 5
            dia_nombre = dias_nombres.get(v['dia'], f'Día {v["dia"]}')
            print(f"  - {v['curso']} (Liga {v['liga']}) - {dia_nombre}")
            print(f"    Asignado: {v['ts_inicio']} - {v['ts_fin']}")
            print(f"    Restricción: {v['restriccion_inicio']} - {v['restriccion_fin']}")
        
        if len(viol_list) > 5:
            print(f"  ... y {len(viol_list) - 5} más")
else:
    print("\n✅ No se encontraron violaciones de restricciones de profesores")

session.close()
