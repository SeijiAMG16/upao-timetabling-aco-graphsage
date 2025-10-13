"""
Diagnóstico de violaciones T→P→L del Experimento 31
"""
import json
from collections import defaultdict
from datetime import datetime

# Cargar resultados del experimento 31
with open('experimento_proy_31.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print("="*80)
print("DIAGNÓSTICO VALIDACIÓN T→P→L - EXPERIMENTO 31")
print("="*80)
print(f"\n📊 Métricas generales:")
print(f"   • Cursos válidos: {data['metricas']['cursos_validos_tpl']}/61")
print(f"   • Violaciones totales: {data['metricas']['total_violaciones_tpl']}")
print(f"\n🔍 Analizando estructura temporal de un curso...\n")

# Cargar asignaciones de la BD
import mysql.connector

conn = mysql.connector.connect(
    host='localhost',
    user='root',
    password='sistemas',
    database='upao_timetabling'
)
cursor = conn.cursor(dictionary=True)

# Obtener todas las asignaciones del experimento 31
cursor.execute("""
    SELECT 
        c.nombre as curso,
        psa.session_type,
        psa.day,
        psa.start_time,
        psa.end_time,
        cr.nombre as aula
    FROM proposed_schedule_assignments psa
    JOIN courses c ON psa.course_id = c.id
    LEFT JOIN classrooms cr ON psa.classroom_id = cr.id
    WHERE psa.execution_id = 31
    ORDER BY c.nombre, psa.day, psa.start_time
""")

asignaciones = cursor.fetchall()
conn.close()

# Agrupar por curso
cursos = defaultdict(list)
for asig in asignaciones:
    cursos[asig['curso']].append(asig)

# Analizar un ejemplo con violaciones
print("🔎 EJEMPLO DE CURSO CON VIOLACIONES:")
print("="*80)

# Buscar un curso con todas las secciones (T, P, L)
curso_ejemplo = None
for nombre, secciones in cursos.items():
    tipos = set(s['session_type'][0] for s in secciones)
    if 'T' in tipos and 'P' in tipos and 'L' in tipos:
        curso_ejemplo = nombre
        break

if curso_ejemplo:
    print(f"\n📚 Curso: {curso_ejemplo}")
    print(f"   Secciones: {len(cursos[curso_ejemplo])}")
    
    # Convertir horarios a timestamps para ordenar
    dias_num = {'LUNES': 1, 'MARTES': 2, 'MIÉRCOLES': 3, 'JUEVES': 4, 'VIERNES': 5, 'SÁBADO': 6}
    
    secciones_ordenadas = []
    for sec in cursos[curso_ejemplo]:
        dia_num = dias_num.get(sec['day'], 0)
        hora = sec['start_time']
        if isinstance(hora, str):
            hora_obj = datetime.strptime(hora, '%H:%M:%S').time()
        else:
            hora_obj = (datetime.min + hora).time()
        
        timestamp = (dia_num, hora_obj)
        secciones_ordenadas.append((timestamp, sec))
    
    # Ordenar por timestamp
    secciones_ordenadas.sort(key=lambda x: x[0])
    
    print("\n   Orden temporal de secciones:")
    print("   " + "-"*76)
    print(f"   {'Tipo':<6} {'Día':<12} {'Horario':<15} {'Aula':<10}")
    print("   " + "-"*76)
    
    for timestamp, sec in secciones_ordenadas:
        tipo = sec['session_type']
        dia = sec['day']
        horario = f"{sec['start_time']}-{sec['end_time']}"
        aula = sec['aula'] or 'N/A'
        print(f"   {tipo:<6} {dia:<12} {horario:<15} {aula:<10}")
    
    # Encontrar violaciones
    print("\n   ❌ VIOLACIONES DETECTADAS:")
    teorias = [(ts, s) for ts, s in secciones_ordenadas if s['session_type'][0] == 'T']
    practicas = [(ts, s) for ts, s in secciones_ordenadas if s['session_type'][0] == 'P']
    laboratorios = [(ts, s) for ts, s in secciones_ordenadas if s['session_type'][0] == 'L']
    
    if teorias:
        max_teoria_ts = max(t[0] for t in teorias)
        
        # Buscar prácticas antes de última teoría
        for ts, prac in practicas:
            if ts <= max_teoria_ts:
                print(f"      • {prac['session_type']} en {prac['day']} {prac['start_time']} ANTES que última teoría")
        
        # Buscar labs antes de última teoría
        for ts, lab in laboratorios:
            if ts <= max_teoria_ts:
                print(f"      • {lab['session_type']} en {lab['day']} {lab['start_time']} ANTES que última teoría")
    
    if practicas:
        max_practica_ts = max(p[0] for p in practicas)
        
        # Buscar labs antes de última práctica
        for ts, lab in laboratorios:
            if ts <= max_practica_ts:
                print(f"      • {lab['session_type']} en {lab['day']} {lab['start_time']} ANTES que última práctica")

print("\n" + "="*80)
print("💡 PROBLEMA IDENTIFICADO:")
print("="*80)
print("""
La validación T→P→L requiere que:
1. TODAS las teorías estén ANTES que CUALQUIER práctica/lab
2. TODAS las prácticas estén ANTES que CUALQUIER lab

Actualmente:
- Ordenamos secciones T→P→L (✓)
- Priorizamos slots tempranos para T, tardíos para L (✓)

PERO FALTA:
- Las teorías se asignan a slots tempranos DENTRO DE LOS DISPONIBLES
- Si slots tempranos (Lunes 7am) ya están ocupados por otras teorías,
  la siguiente teoría toma Martes 7am o Lunes 9am
- Mientras tanto, labs pueden tomar slots tardíos en Lunes (5pm, 7pm)
- Resultado: Lab el Lunes 7pm ANTES que Teoría el Martes 9am → VIOLACIÓN

SOLUCIÓN NECESARIA:
- Agrupar secciones POR CURSO
- Para cada curso, asignar TODAS sus teorías primero
- Luego TODAS sus prácticas
- Finalmente TODOS sus laboratorios
- Esto garantiza orden temporal dentro del mismo curso
""")
print("="*80)
