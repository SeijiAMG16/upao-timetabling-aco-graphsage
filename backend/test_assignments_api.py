"""
Script para probar los nuevos endpoints de asignaciones
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_endpoints():
    print("="*80)
    print("PROBANDO ENDPOINTS DE ASIGNACIONES")
    print("="*80)
    
    # 1. Obtener profesores
    print("\n[1] Obteniendo lista de profesores...")
    response = requests.get(f"{BASE_URL}/api/assignments/professors")
    if response.status_code == 200:
        professors = response.json()
        print(f"  [OK] {len(professors)} profesores encontrados")
        print(f"  Ejemplo: {professors[0]['nombre_completo']}")
    else:
        print(f"  [ERROR] {response.status_code}")
    
    # 2. Obtener cursos con asignaciones
    print("\n[2] Obteniendo cursos con asignaciones...")
    response = requests.get(f"{BASE_URL}/api/assignments/courses-with-assignments")
    if response.status_code == 200:
        courses = response.json()
        print(f"  [OK] {len(courses)} cursos encontrados")
        
        # Contar cursos con y sin asignaciones
        with_assignments = sum(1 for c in courses if len(c['assigned_professors']) > 0)
        without = len(courses) - with_assignments
        print(f"  Cursos con asignaciones: {with_assignments}")
        print(f"  Cursos sin asignaciones: {without}")
        
        # Mostrar ejemplo
        if with_assignments > 0:
            example = next(c for c in courses if len(c['assigned_professors']) > 0)
            print(f"\n  Ejemplo: {example['codigo']} - {example['nombre']}")
            for assign in example['assigned_professors']:
                print(f"    - {assign['session_type']}: {assign['professor_name']}")
    else:
        print(f"  [ERROR] {response.status_code}")
    
    # 3. Obtener restricciones
    print("\n[3] Obteniendo restricciones...")
    response = requests.get(f"{BASE_URL}/api/assignments/restrictions")
    if response.status_code == 200:
        restrictions = response.json()
        print(f"  [OK] {len(restrictions)} restricciones encontradas")
        
        # Agrupar por profesor
        by_professor = {}
        for r in restrictions:
            name = r['professor_name']
            by_professor[name] = by_professor.get(name, 0) + 1
        
        print(f"  Profesores con restricciones: {len(by_professor)}")
        for prof, count in sorted(by_professor.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"    - {prof[:30]:30} {count} bloques")
    else:
        print(f"  [ERROR] {response.status_code}")
    
    # 4. Obtener bloques horarios
    print("\n[4] Obteniendo bloques horarios...")
    response = requests.get(f"{BASE_URL}/api/assignments/time-blocks")
    if response.status_code == 200:
        blocks = response.json()
        print(f"  [OK] {len(blocks)} bloques horarios")
        print(f"  Ejemplo: {blocks[0]['label']}")
    else:
        print(f"  [ERROR] {response.status_code}")
    
    # 5. Obtener asignaciones profesor-curso
    print("\n[5] Obteniendo todas las asignaciones...")
    response = requests.get(f"{BASE_URL}/api/assignments/professor-courses")
    if response.status_code == 200:
        assignments = response.json()
        print(f"  [OK] {len(assignments)} asignaciones encontradas")
        
        # Agrupar por tipo de sesión
        by_type = {'T': 0, 'P': 0, 'L': 0}
        for a in assignments:
            by_type[a['session_type']] = by_type.get(a['session_type'], 0) + 1
        
        print(f"  Por tipo de sesión:")
        print(f"    - Teoría: {by_type.get('T', 0)}")
        print(f"    - Práctica: {by_type.get('P', 0)}")
        print(f"    - Laboratorio: {by_type.get('L', 0)}")
        
        # Mostrar ejemplos
        if assignments:
            print(f"\n  Ejemplos:")
            for assign in assignments[:3]:
                print(f"    - {assign['course_code']} ({assign['session_type']}): {assign['professor_name'][:30]}")
    else:
        print(f"  [ERROR] {response.status_code}")
    
    print("\n" + "="*80)
    print("PRUEBAS COMPLETADAS")
    print("="*80)
    print("\nPuedes acceder a:")
    print(f"  - Documentación API: {BASE_URL}/docs")
    print(f"  - Frontend (una vez iniciado): http://localhost:3000")

if __name__ == "__main__":
    try:
        test_endpoints()
    except requests.exceptions.ConnectionError:
        print("[ERROR] No se pudo conectar al servidor")
        print("Asegúrate de que el servidor FastAPI esté corriendo:")
        print("  cd backend")
        print("  python -m uvicorn app.main:app --reload --port 8000")
    except Exception as e:
        print(f"[ERROR] {e}")
