#!/usr/bin/env python3
"""
Test completo del procesamiento de profesores
"""
import requests
import json

def test_professors_upload():
    print('=== TESTEANDO UPLOAD DE PROFESORES ===')
    
    with open('inputs/Horario_Docentes(2025-20).xlsx', 'rb') as f:
        response = requests.post('http://localhost:8000/api/professors-upload/upload', files={'file': f})

    if response.status_code == 200:
        data = response.json()
        print('✅ Upload exitoso')
        
        if 'summary' in data:
            summary = data['summary']
            print(f'Asignaciones: {summary.get("asignaciones_procesadas", 0)}')
            print(f'Restricciones: {summary.get("restricciones_procesadas", 0)}')
            print(f'Profesores identificados: {summary.get("profesores_identificados", 0)}')
        else:
            print('Respuesta:', data)
        
        return True
    else:
        print(f'❌ Error: {response.status_code}')
        print('Response:', response.text)
        return False

def count_professors_in_db():
    print('\n=== PROFESORES EN BD ===')
    
    response = requests.get('http://localhost:8000/api/professors')
    if response.status_code == 200:
        data = response.json()
        total = data.get('total', 0)
        professors = data.get('professors', [])
        
        print(f'Total profesores en BD: {total}')
        
        # Contar con nombres reales
        real_names = [p for p in professors if p.get('nombre_completo') and 'None' not in p.get('nombre_completo', '')]
        print(f'Con nombres reales: {len(real_names)}')
        
        return total
    else:
        print(f'Error: {response.status_code}')
        return 0

def analyze_excel_structure():
    print('\n=== ANALIZANDO ESTRUCTURA DEL EXCEL ===')
    
    # Ejecutar script de análisis
    import sys
    sys.path.append('backend')
    
    try:
        from extraer_por_colores_v4 import Extractor
        
        extractor = Extractor('inputs/Horario_Docentes(2025-20).xlsx')
        
        print(f'Total hojas en Excel: {len(extractor.hoja_names)}')
        print('Hojas encontradas:')
        for i, hoja in enumerate(extractor.hoja_names):
            print(f'  {i+1}. {hoja}')
        
        return len(extractor.hoja_names)
    except Exception as e:
        print(f'Error analizando Excel: {e}')
        return 0

if __name__ == "__main__":
    # Test 1: Upload
    upload_ok = test_professors_upload()
    
    # Test 2: Count in DB
    db_count = count_professors_in_db()
    
    # Test 3: Excel structure
    excel_sheets = analyze_excel_structure()
    
    print('\n' + '='*50)
    print('RESUMEN:')
    print(f'Upload funcionó: {"✅" if upload_ok else "❌"}')
    print(f'Profesores en BD: {db_count}')
    print(f'Hojas en Excel: {excel_sheets}')
    
    if excel_sheets > db_count:
        print('⚠️ Puede que no se estén procesando todas las hojas')
    else:
        print('✅ Números consistentes')