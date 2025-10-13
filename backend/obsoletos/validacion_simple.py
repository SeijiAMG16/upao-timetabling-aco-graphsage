"""Script simplificado para validar primer experimento"""
import mysql.connector
import json
from reglas_pedagogicas_v2 import ReglaspedagogicasV2
from proyecciones_loader import ProyeccionesLoader

def conectar_bd():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='sistemas',
        database='upao_timetabling'
    )

# Obtener sesiones del primer experimento
conn = conectar_bd()
cursor = conn.cursor(dictionary=True)

cursor.execute("""
    SELECT 
        c.nombre as course_name,
        psa.session_type,
        psa.day as dia,
        psa.start_time as hora_inicio,
        psa.end_time as hora_fin
    FROM proposed_schedule_assignments psa
    JOIN courses c ON psa.course_id = c.id
    WHERE psa.algorithm_execution_id = 1
    ORDER BY c.nombre, psa.day, psa.start_time
""")

sesiones = cursor.fetchall()
cursor.close()
conn.close()

print(f"Total sesiones encontradas: {len(sesiones)}")

# Agrupar por curso
cursos = {}
for sesion in sesiones:
    course_name = sesion['course_name']
    if course_name not in cursos:
        cursos[course_name] = []
    cursos[course_name].append(sesion)

print(f"Total cursos: {len(cursos)}")

# Validar T->P->L por curso
print("\n" + "="*80)
print("VALIDACION T->P->L POR CURSO")
print("="*80)

cursos_validos = 0
cursos_invalidos = 0

for course_name, sesiones_curso in sorted(cursos.items())[:10]:  # Primeros 10
    es_valido, num_viol, detalle = ReglaspedagogicasV2.validar_orden_TPL(sesiones_curso)
    
    estado = "[OK]" if es_valido else "[FAIL]"
    print(f"\n{estado} {course_name}")
    print(f"  T:{detalle['teorias']} P:{detalle['practicas']} L:{detalle['laboratorios']}")
    
    if not es_valido:
        cursos_invalidos += 1
        for v in detalle['violaciones']:
            print(f"  - {v['tipo']}: {v['mensaje']}")
    else:
        cursos_validos += 1

print(f"\n\nRESUMEN: {cursos_validos} validos, {cursos_invalidos} invalidos de primeros 10")
