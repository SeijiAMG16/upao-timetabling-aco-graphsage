import requests
print("Verificando backend...")

try:
    response = requests.get("http://localhost:8000/api/professors")
    if response.status_code == 200:
        data = response.json()
        profesores = data.get("professors", [])
        print(f"✅ Backend OK - {len(profesores)} profesores")
        
        # Verificar nombres
        real_names = [p for p in profesores if p.get("nombre_completo", "None") not in ["None None", "None", ""]]
        print(f"✅ Profesores con nombres reales: {len(real_names)}")
        
        if real_names:
            print(f"   Ejemplo: {real_names[0]['nombre_completo']}")
        
        print("\n🎉 SISTEMA FUNCIONAL - PUEDES PROBAR:")
        print("   1. http://localhost:3000/projections - Sube Libro1.xlsx")
        print("   2. http://localhost:3000/professors-upload - Sube Horario_Docentes")
        
    else:
        print(f"❌ Backend error: {response.status_code}")
except Exception as e:
    print(f"❌ Error: {e}")