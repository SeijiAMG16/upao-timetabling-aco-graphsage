"""
Debug: Ver qué contienen las secciones generadas
"""

import sys
sys.path.append('.')

from proyecciones_loader import ProyeccionesLoader
import mysql.connector

def conectar_bd():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='sistemas',
        database='upao_timetabling'
    )

def main():
    # Cargar proyecciones
    loader = ProyeccionesLoader('../inputs/Libro1.xlsx')
    proyecciones = loader.proyecciones
    
    print(f"Proyecciones cargadas: {len(proyecciones)}")
    
    # Cargar cursos de BD
    conn = conectar_bd()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT id, nombre, ciclo, alumnos_teoria, alumnos_practica, alumnos_laboratorio
        FROM courses
    """)
    cursos_bd = cursor.fetchall()
    
    print(f"Cursos en BD: {len(cursos_bd)}")
    
    # Normalizar y crear dict
    import re
    cursos = {}
    for c in cursos_bd:
        nombre_norm = re.sub(r'\s+', ' ', c['nombre'].strip().upper())
        cursos[nombre_norm] = {
            'id': c['id'],
            'nombre': c['nombre'],
            'alumnos_teoria': c['alumnos_teoria'],
            'alumnos_practica': c['alumnos_practica'],
            'alumnos_laboratorio': c['alumnos_laboratorio']
        }
    
    # Generar secciones
    secciones = []
    sin_proyeccion = []
    
    for nombre_norm, info_curso in cursos.items():
        proyeccion = proyecciones.get(nombre_norm)
        
        if not proyeccion:
            sin_proyeccion.append(nombre_norm)
            continue
        
        # Generar teorías
        for i in range(proyeccion['teoria']):
            secciones.append({
                'course_id': info_curso['id'],
                'course_name': info_curso['nombre'],
                'session_type': f'T{i+1}',
                'alumnos': info_curso['alumnos_teoria'],
                'tipo_aula': 'NOLAB'
            })
        
        # Generar prácticas
        for i in range(proyeccion['practica']):
            secciones.append({
                'course_id': info_curso['id'],
                'course_name': info_curso['nombre'],
                'session_type': f'P{i+1}',
                'alumnos': info_curso['alumnos_practica'],
                'tipo_aula': 'NOLAB'
            })
        
        # Generar laboratorios
        for i in range(proyeccion['laboratorio']):
            secciones.append({
                'course_id': info_curso['id'],
                'course_name': info_curso['nombre'],
                'session_type': f'L{i+1}',
                'alumnos': info_curso['alumnos_laboratorio'],
                'tipo_aula': 'LAB'
            })
    
    print(f"\nSecciones generadas: {len(secciones)}")
    print(f"Teorías: {sum(1 for s in secciones if s['session_type'][0] == 'T')}")
    print(f"Prácticas: {sum(1 for s in secciones if s['session_type'][0] == 'P')}")
    print(f"Laboratorios: {sum(1 for s in secciones if s['session_type'][0] == 'L')}")
    
    print(f"\nCursos sin proyección: {len(sin_proyeccion)}")
    for c in sin_proyeccion:
        print(f"  • {c}")
    
    # Ver primeras 10 secciones
    print(f"\nPrimeras 10 secciones:")
    for i, s in enumerate(secciones[:10]):
        print(f"  {i+1}. {s['course_name']} - {s['session_type']} - {s['alumnos']} alumnos - Aula: {s['tipo_aula']}")
    
    # Verificar si alguna tiene alumnos None o 0
    sin_alumnos = [s for s in secciones if s['alumnos'] is None or s['alumnos'] == 0]
    print(f"\nSecciones sin alumnos definidos: {len(sin_alumnos)}")
    if sin_alumnos:
        for s in sin_alumnos[:5]:
            print(f"  • {s['course_name']} - {s['session_type']}")
    
    conn.close()

if __name__ == '__main__':
    main()
