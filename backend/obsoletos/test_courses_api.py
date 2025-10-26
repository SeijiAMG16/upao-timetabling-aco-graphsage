#!/usr/bin/env python3
import requests

try:
    response = requests.get('http://localhost:8000/api/projections/courses')
    if response.status_code == 200:
        data = response.json()
        courses = data.get('courses', [])
        print(f"✅ API devuelve {len(courses)} cursos")
        
        # Mostrar primeros cursos con grupos
        with_groups = [c for c in courses if c.get('grupos_teoria', 0) > 0 or c.get('grupos_practica', 0) > 0 or c.get('grupos_laboratorio', 0) > 0]
        print(f"✅ Cursos con grupos: {len(with_groups)}")
        
        print("\nPrimeros 5 cursos con grupos:")
        for i, curso in enumerate(with_groups[:5]):
            print(f"  {i+1}. {curso['codigo']} - T:{curso.get('grupos_teoria', 0)} P:{curso.get('grupos_practica', 0)} L:{curso.get('grupos_laboratorio', 0)}")
    else:
        print(f"❌ Error: {response.status_code}")
        
except Exception as e:
    print(f"❌ Error: {e}")