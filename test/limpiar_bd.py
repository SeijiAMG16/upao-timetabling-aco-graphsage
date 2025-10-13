#!/usr/bin/env python3
"""
Limpiar BD de datos incorrectos
"""
import pymysql

def limpiar_bd():
    print('=== LIMPIANDO BD DE DATOS INCORRECTOS ===')

    conn = pymysql.connect(
        host='localhost',
        user='root',
        password='sistemas',
        database='upao_timetabling'
    )

    cursor = conn.cursor()

    # 1. Eliminar restricciones de profesores
    cursor.execute('DELETE FROM professor_restrictions WHERE reason = "Extraido de Excel"')
    restricciones_eliminadas = cursor.rowcount
    print(f'✅ Restricciones eliminadas: {restricciones_eliminadas}')

    # 2. Eliminar asignaciones de horarios 
    cursor.execute('DELETE FROM schedule_assignments WHERE created_at > "2025-10-09"')
    asignaciones_eliminadas = cursor.rowcount
    print(f'✅ Asignaciones eliminadas: {asignaciones_eliminadas}')
    
    # 2.5. Eliminar historial de profesores (foreign key)
    cursor.execute('DELETE FROM professor_course_history WHERE professor_id >= 39')
    historial_eliminado = cursor.rowcount
    print(f'✅ Historial de profesores eliminado: {historial_eliminado}')

    # 3. Eliminar profesores creados hoy (los inventados)
    cursor.execute('DELETE FROM professors WHERE codigo >= "000000039"')
    profesores_eliminados = cursor.rowcount
    print(f'✅ Profesores inventados eliminados: {profesores_eliminados}')

    conn.commit()

    # Verificar estado actual
    cursor.execute('SELECT COUNT(*) FROM professors')
    total_profesores = cursor.fetchone()[0]
    print(f'📊 Profesores restantes: {total_profesores}')

    cursor.execute('SELECT COUNT(*) FROM professor_restrictions')
    total_restricciones = cursor.fetchone()[0]
    print(f'📊 Restricciones restantes: {total_restricciones}')
    
    # Mostrar profesores actuales
    cursor.execute('SELECT id, nombre_completo FROM professors ORDER BY id')
    profesores = cursor.fetchall()
    print('\n📋 PROFESORES ACTUALES EN BD:')
    for prof_id, nombre in profesores:
        print(f'  {prof_id}: {nombre}')

    cursor.close()
    conn.close()

    print('\n🧹 BD limpiada correctamente')
    return total_profesores

if __name__ == "__main__":
    limpiar_bd()