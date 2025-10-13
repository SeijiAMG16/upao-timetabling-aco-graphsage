"""Validación específica del Experimento 12"""
from reglas_pedagogicas_v2 import ReglaspedagogicasV2
from proyecciones_loader import ProyeccionesLoader
import mysql.connector

# Conectar
conn = mysql.connector.connect(
    host='localhost',
    user='root',
    password='sistemas',
    database='upao_timetabling'
)
cursor = conn.cursor(dictionary=True)

# Obtener sesiones experimento 12
cursor.execute("""
    SELECT 
        c.nombre as course_name,
        psa.session_type,
        psa.day as dia,
        psa.start_time as hora_inicio
    FROM proposed_schedule_assignments psa
    JOIN courses c ON psa.course_id = c.id
    WHERE psa.algorithm_execution_id = 12
    ORDER BY c.nombre, psa.day, psa.start_time
""")

sesiones = cursor.fetchall()
cursor.close()
conn.close()

print(f"Total sesiones: {len(sesiones)}")

# Agrupar por curso
cursos = {}
for sesion in sesiones:
    cn = sesion['course_name']
    if cn not in cursos:
        cursos[cn] = []
    cursos[cn].append(sesion)

print(f"Total cursos: {len(cursos)}\n")
print("="*80)
print("VALIDACION T->P->L - EXPERIMENTO 12")
print("="*80)

cursos_validos = 0
cursos_invalidos = 0
total_violaciones = 0

for cn, scs in sorted(cursos.items()):
    ok, nviol, det = ReglaspedagogicasV2.validar_orden_TPL(scs)
    
    if not ok:
        cursos_invalidos += 1
        total_violaciones += nviol
        print(f"\n[FAIL] {cn}")
        print(f"  T:{det['teorias']} P:{det['practicas']} L:{det['laboratorios']}")
        for v in det['violaciones']:
            print(f"  - {v['mensaje']}")
    else:
        cursos_validos += 1

pct = (cursos_validos / len(cursos) * 100) if len(cursos) > 0 else 0

print("\n" + "="*80)
print("RESULTADO FINAL:")
print(f"  Cursos validos: {cursos_validos}/{len(cursos)} ({pct:.1f}%)")
print(f"  Cursos invalidos: {cursos_invalidos}")
print(f"  Total violaciones: {total_violaciones}")
print("="*80)

# Validar contra proyecciones
print("\n" + "="*80)
print("VALIDACION CONTRA PROYECCIONES")
print("="*80)

loader = ProyeccionesLoader()

proyecciones_invalidas = 0
for cn, scs in sorted(cursos.items()):
    conteo = {'T': 0, 'P': 0, 'L': 0}
    for s in scs:
        tipo_raw = str(s['session_type']).upper()
        tipo = tipo_raw[0] if tipo_raw else ''
        if tipo in conteo:
            conteo[tipo] += 1
    
    proyeccion = loader.obtener_proyeccion(cn)
    
    if not proyeccion:
        proyecciones_invalidas += 1
        print(f"\n[ERROR] {cn}: No encontrado en proyecciones")
        print(f"  Generado: T:{conteo['T']} P:{conteo['P']} L:{conteo['L']}")
        continue
    
    dif_t = conteo['T'] - proyeccion['teoria']
    dif_p = conteo['P'] - proyeccion['practica']
    dif_l = conteo['L'] - proyeccion['laboratorio']
    
    if dif_t != 0 or dif_p != 0 or dif_l != 0:
        proyecciones_invalidas += 1
        print(f"\n[FAIL] {cn}")
        print(f"  Esperado: T:{proyeccion['teoria']} P:{proyeccion['practica']} L:{proyeccion['laboratorio']}")
        print(f"  Generado: T:{conteo['T']} P:{conteo['P']} L:{conteo['L']}")
        print(f"  Diferencias: T:{dif_t:+d} P:{dif_p:+d} L:{dif_l:+d}")

pct_proy = ((len(cursos) - proyecciones_invalidas) / len(cursos) * 100) if len(cursos) > 0 else 0

print("\n" + "="*80)
print("RESULTADO PROYECCIONES:")
print(f"  Cursos que cumplen: {len(cursos) - proyecciones_invalidas}/{len(cursos)} ({pct_proy:.1f}%)")
print(f"  Cursos que NO cumplen: {proyecciones_invalidas}")
print("="*80)
