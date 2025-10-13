#!/usr/bin/env python3
"""
Debug del flujo de proyecciones
"""
import requests
import json

def test_projections_upload():
    print('=== TESTEANDO ENDPOINT DE PROYECCIONES ===')
    
    with open('inputs/Libro1.xlsx', 'rb') as f:
        response = requests.post('http://localhost:8000/api/projections/upload', files={'file': f})

    if response.status_code == 200:
        data = response.json()
        print(f'Cursos procesados: {len(data.get("courses", []))}')
        
        # Mostrar primeros 3 con detalles
        for i, course in enumerate(data['courses'][:3]):
            print(f'{i+1}. {course["codigo"]}: {course["nombre"]}')
            print(f'   T={course["grupos_teoria"]}, P={course["grupos_practica"]}, L={course["grupos_laboratorio"]}')
            print(f'   Modalidad: {course["modalidad"]}')
            print(f'   Exists: {course.get("exists", False)}')
            print()
        
        return data['courses']
    else:
        print(f'Error: {response.status_code} - {response.text}')
        return None

def check_current_courses_in_db():
    print('=== CURSOS ACTUALES EN BD ===')
    
    response = requests.get('http://localhost:8000/api/courses')
    if response.status_code == 200:
        courses = response.json()
        print(f'Total cursos en BD: {len(courses)}')
        
        # Mostrar algunos con grupos
        for i, course in enumerate(courses[:5]):
            codigo = course.get('codigo', 'N/A')
            nombre = course.get('nombre', 'N/A')
            t = course.get('grupos_teoria', 0)
            p = course.get('grupos_practica', 0)
            l = course.get('grupos_laboratorio', 0)
            print(f'{i+1}. {codigo}: {nombre}')
            print(f'   T={t}, P={p}, L={l}')
        
        return courses
    else:
        print(f'Error: {response.status_code}')
        return None

if __name__ == "__main__":
    # Test 1: Upload endpoint
    upload_data = test_projections_upload()
    
    print('\n' + '='*50)
    
    # Test 2: Current DB state
    db_data = check_current_courses_in_db()
    
    print('\n' + '='*50)
    print('ANÁLISIS:')
    
    if upload_data and db_data:
        upload_with_groups = [c for c in upload_data if c['grupos_teoria'] > 0 or c['grupos_practica'] > 0 or c['grupos_laboratorio'] > 0]
        db_with_groups = [c for c in db_data if c.get('grupos_teoria', 0) > 0 or c.get('grupos_practica', 0) > 0 or c.get('grupos_laboratorio', 0) > 0]
        
        print(f'Cursos con grupos en upload: {len(upload_with_groups)}')
        print(f'Cursos con grupos en BD: {len(db_with_groups)}')
        
        if len(upload_with_groups) > len(db_with_groups):
            print('❌ Los datos de grupos no se están guardando en BD')
        else:
            print('✅ Los datos parecen consistentes')