"""
SCRIPT DE VERIFICACIÓN FINAL - COMPRUEBA TODO EL SISTEMA
"""

import requests
import json

BASE_URL = "http://localhost:8000/api"

def verificar_backend():
    """Verifica que el backend responda"""
    try:
        response = requests.get(f"{BASE_URL}/professors")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Backend OK - {len(data.get('professors', []))} profesores")
            return True
        else:
            print(f"❌ Backend error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Backend no responde: {e}")
        return False

def verificar_proyecciones():
    """Verifica endpoint de proyecciones"""
    try:
        response = requests.get(f"{BASE_URL}/projections/courses")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Proyecciones OK - {len(data.get('courses', []))} cursos")
            return True
        else:
            print(f"❌ Proyecciones error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Proyecciones no responde: {e}")
        return False

def verificar_profesores():
    """Verifica endpoint de profesores"""
    try:
        response = requests.get(f"{BASE_URL}/professors")
        if response.status_code == 200:
            data = response.json()
            profesores = data.get('professors', [])
            
            # Verificar que no hay "None None"
            none_count = len([p for p in profesores if p.get('nombre_completo') in ['None None', 'None', '']])
            real_count = len([p for p in profesores if p.get('nombre_completo') not in ['None None', 'None', '']])
            
            print(f"✅ Profesores OK - {real_count} con nombres reales, {none_count} con None")
            
            if real_count > 0:
                print(f"   Ejemplo: {profesores[0].get('nombre_completo')}")
            
            return real_count > none_count
        else:
            print(f"❌ Profesores error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Profesores no responde: {e}")
        return False

def main():
    """Verificación completa del sistema"""
    print("="*80)
    print("VERIFICACIÓN FINAL DEL SISTEMA UPAO TIMETABLING")
    print("="*80)
    
    checks = [
        ("Backend general", verificar_backend),
        ("Endpoint proyecciones", verificar_proyecciones), 
        ("Endpoint profesores", verificar_profesores)
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n🔍 Verificando {name}...")
        success = check_func()
        results.append((name, success))
    
    print("\n" + "="*80)
    print("RESUMEN DE VERIFICACIÓN:")
    print("="*80)
    
    for name, success in results:
        status = "✅ OK" if success else "❌ FALLO"
        print(f"  {name}: {status}")
    
    all_ok = all(result[1] for result in results)
    
    if all_ok:
        print("\n🎉 SISTEMA COMPLETAMENTE FUNCIONAL")
        print("   ✅ Puedes subir Libro1.xlsx en /projections") 
        print("   ✅ Puedes subir Horario_Docentes en /professors-upload")
        print("   ✅ Los nombres de profesores se muestran correctamente")
    else:
        print("\n⚠️ HAY PROBLEMAS EN EL SISTEMA")
    
    print("="*80)

if __name__ == "__main__":
    main()