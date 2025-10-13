"""
📊 RESUMEN RÁPIDO DE EXPERIMENTO
Muestra estadísticas y algunas asignaciones de ejemplo
"""
import mysql.connector
import sys

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'sistemas',
    'database': 'upao_timetabling'
}

def main():
    # Obtener experiment_id
    if len(sys.argv) > 1:
        exp_id = int(sys.argv[1])
    else:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(id) FROM algorithm_executions")
        exp_id = cursor.fetchone()[0]
        cursor.close()
        conn.close()
    
    # Cargar asignaciones
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT 
            c.nombre as course_name,
            a.session_type,
            p.nombre_completo as professor_name,
            cl.codigo as classroom_name,
            cl.tipo as classroom_type,
            a.day,
            a.start_time,
            a.end_time
        FROM proposed_schedule_assignments a
        JOIN courses c ON a.course_id = c.id
        JOIN professors p ON a.professor_id = p.id
        JOIN classrooms cl ON a.classroom_id = cl.id
        WHERE a.algorithm_execution_id = %s
        ORDER BY c.nombre, 
            FIELD(a.day, 'LUNES', 'MARTES', 'MIÉRCOLES', 'JUEVES', 'VIERNES', 'SÁBADO'),
            a.start_time
    """, (exp_id,))
    
    asignaciones = cursor.fetchall()
    cursor.close()
    conn.close()
    
    print("="*120)
    print(f"📊 RESUMEN DEL EXPERIMENTO #{exp_id}")
    print("="*120)
    print(f"✅ Total asignaciones: {len(asignaciones)}")
    print(f"📚 Cursos: {len(set(a['course_name'] for a in asignaciones))}")
    print(f"👥 Profesores: {len(set(a['professor_name'] for a in asignaciones))}")
    print(f"🏫 Aulas: {len(set(a['classroom_name'] for a in asignaciones))}")
    
    print(f"\n{'Tipo':<6} {'Cantidad':<10}")
    print("-"*30)
    tipos = {}
    for a in asignaciones:
        tipo = a['session_type'][0]
        tipos[tipo] = tipos.get(tipo, 0) + 1
    
    print(f"{'T':<6} {tipos.get('T', 0):<10} (Teorías)")
    print(f"{'P':<6} {tipos.get('P', 0):<10} (Prácticas)")
    print(f"{'L':<6} {tipos.get('L', 0):<10} (Laboratorios)")
    
    # Mostrar 10 ejemplos
    print(f"\n📋 EJEMPLOS DE ASIGNACIONES (primeras 10):")
    print("="*120)
    print(f"{'Curso':<40} {'Tipo':<6} {'Día':<12} {'Hora':<12} {'Aula':<15}")
    print("-"*120)
    
    for i, asig in enumerate(asignaciones[:10]):
        curso = asig['course_name'][:38]
        tipo = asig['session_type']
        dia = asig['day']
        hora = f"{asig['start_time']}-{asig['end_time']}"
        aula = f"{asig['classroom_name']} ({asig['classroom_type']})"
        
        print(f"{curso:<40} {tipo:<6} {dia:<12} {hora:<12} {aula:<15}")
    
    print(f"\n... y {len(asignaciones) - 10} asignaciones más")
    print("="*120)
    print(f"\n💡 Para ver el horario completo, ejecuta:")
    print(f"   python visualizar_horario_generado.py {exp_id}")
    print("="*120)

if __name__ == '__main__':
    main()
