#!/usr/bin/env python3
"""
Test de endpoints completos del sistema de Excel
"""
import requests
import json
import os

# Configuración
BACKEND_URL = "http://localhost:8000"
EXCEL_PROJECTIONS = "inputs/Libro1.xlsx"
EXCEL_PROFESSORS = "inputs/Horario_Docentes(2025-20).xlsx"

def test_professors_endpoint():
    """Test del endpoint de profesores"""
    print("🧪 Testeando endpoint de profesores...")
    
    try:
        response = requests.get(f"{BACKEND_URL}/api/professors")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Profesores obtenidos: {data['total']}")
            
            # Mostrar algunos profesores con nombres reales
            if data['professors']:
                print("\n📋 Primeros 3 profesores:")
                for i, prof in enumerate(data['professors'][:3]):
                    nombre = prof.get('nombre_completo', 'Sin nombre')
                    print(f"  {i+1}. {nombre}")
            
            return True
        else:
            print(f"❌ Error en endpoint: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return False

def test_projections_upload():
    """Test del endpoint de carga de proyecciones"""
    print("\n🧪 Testeando carga de proyecciones...")
    
    if not os.path.exists(EXCEL_PROJECTIONS):
        print(f"❌ Archivo no encontrado: {EXCEL_PROJECTIONS}")
        return False
    
    try:
        with open(EXCEL_PROJECTIONS, 'rb') as f:
            files = {'file': f}
            response = requests.post(f"{BACKEND_URL}/api/projections/upload", files=files)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Proyecciones procesadas: {len(data.get('projections', []))}")
            
            # Mostrar algunas proyecciones
            if data.get('projections'):
                print("\n📊 Primeras 3 proyecciones:")
                for i, proj in enumerate(data['projections'][:3]):
                    codigo = proj.get('codigo_curso', 'N/A')
                    nombre = proj.get('nombre_curso', 'N/A')
                    teoria = proj.get('horas_teoria', 0)
                    practica = proj.get('horas_practica', 0)
                    laboratorio = proj.get('horas_laboratorio', 0)
                    print(f"  {i+1}. {codigo}: {nombre} (T={teoria}, P={practica}, L={laboratorio})")
            
            return True
        else:
            print(f"❌ Error en upload: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error en upload: {e}")
        return False

def test_professors_upload():
    """Test del endpoint de carga de profesores"""
    print("\n🧪 Testeando carga de profesores...")
    
    if not os.path.exists(EXCEL_PROFESSORS):
        print(f"❌ Archivo no encontrado: {EXCEL_PROFESSORS}")
        return False
    
    try:
        with open(EXCEL_PROFESSORS, 'rb') as f:
            files = {'file': f}
            response = requests.post(f"{BACKEND_URL}/api/professors-upload/upload", files=files)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Procesamiento de profesores exitoso")
            
            # Mostrar resumen
            if 'summary' in data:
                summary = data['summary']
                print(f"📊 Asignaciones procesadas: {summary.get('asignaciones_procesadas', 0)}")
                print(f"📊 Restricciones procesadas: {summary.get('restricciones_procesadas', 0)}")
                print(f"📊 Profesores identificados: {summary.get('profesores_identificados', 0)}")
            
            return True
        else:
            print(f"❌ Error en upload: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error en upload: {e}")
        return False

def main():
    print("🚀 INICIANDO TESTS DE ENDPOINTS COMPLETOS")
    print("=" * 50)
    
    # Test 1: Endpoint de profesores
    test1 = test_professors_endpoint()
    
    # Test 2: Upload de proyecciones
    test2 = test_projections_upload()
    
    # Test 3: Upload de profesores
    test3 = test_professors_upload()
    
    # Resumen final
    print("\n" + "=" * 50)
    print("📊 RESUMEN DE TESTS:")
    print(f"  Profesores endpoint: {'✅' if test1 else '❌'}")
    print(f"  Proyecciones upload: {'✅' if test2 else '❌'}")
    print(f"  Profesores upload: {'✅' if test3 else '❌'}")
    
    if all([test1, test2, test3]):
        print("\n🎉 TODOS LOS TESTS EXITOSOS!")
        print("🎯 Sistema completamente funcional")
    else:
        print("\n⚠️ Algunos tests fallaron")
        print("🔧 Revisar logs para depuración")

if __name__ == "__main__":
    main()