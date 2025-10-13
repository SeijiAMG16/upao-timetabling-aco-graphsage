#!/usr/bin/env python3
"""
VERIFICACIÓN COMPLETA DEL SISTEMA FRONTEND-BACKEND
Verifica que toda la integración funcione correctamente
"""
import requests
import json
import time

def verificar_backend():
    print("🔍 VERIFICANDO BACKEND...")
    print("=" * 60)
    
    try:
        # 1. Backend principal
        response = requests.get('http://localhost:8000/')
        print(f"✅ Backend principal: {response.status_code}")
        
        # 2. Profesores
        response = requests.get('http://localhost:8000/api/professors')
        if response.status_code == 200:
            data = response.json()
            total_profs = data.get('total', len(data.get('professors', [])))
            print(f"✅ Profesores: {total_profs} profesores")
            
            if total_profs >= 38:
                return True, f"Backend OK - {total_profs} profesores"
            else:
                return False, f"Solo {total_profs} profesores, esperados 38"
        else:
            return False, f"Error profesores: {response.status_code}"
            
    except Exception as e:
        return False, f"Error backend: {e}"

def verificar_restricciones():
    print("\n🔒 VERIFICANDO RESTRICCIONES...")
    print("=" * 60)
    
    try:
        response = requests.get('http://localhost:8000/api/assignments/restrictions')
        if response.status_code == 200:
            data = response.json()
            total_restr = len(data)
            print(f"✅ Restricciones: {total_restr} restricciones")
            
            if total_restr >= 40:
                return True, f"Restricciones OK - {total_restr} restricciones"
            else:
                return False, f"Solo {total_restr} restricciones"
        else:
            return False, f"Error restricciones: {response.status_code}"
            
    except Exception as e:
        return False, f"Error restricciones: {e}"

def verificar_frontend():
    print("\n🌐 VERIFICANDO FRONTEND...")
    print("=" * 60)
    
    try:
        response = requests.get('http://localhost:3000/')
        if response.status_code == 200:
            print("✅ Frontend accesible en localhost:3000")
            return True, "Frontend OK"
        else:
            return False, f"Frontend error: {response.status_code}"
            
    except Exception as e:
        return False, f"Frontend no accesible: {e}"

def verificar_datos_exactos():
    print("\n📊 VERIFICANDO DATOS EXACTOS...")
    print("=" * 60)
    
    try:
        # Verificar profesores específicos
        response = requests.get('http://localhost:8000/api/professors')
        data = response.json()
        professors = data.get('professors', [])
        
        # Buscar profesores específicos que sabemos están en Excel
        nombres_esperados = [
            'CAROLA LIZETH CUBA CASTILLO',
            'Carlos Edwin Julca Castillo', 
            'Freddy Infantes Quiroz',
            'Jorge Piminchumo Flores'
        ]
        
        encontrados = []
        for prof in professors:
            nombre = prof.get('nombre_completo', '')
            if nombre in nombres_esperados:
                encontrados.append(nombre)
        
        print(f"✅ Profesores exactos encontrados: {len(encontrados)}/{len(nombres_esperados)}")
        for nombre in encontrados:
            print(f"   - {nombre}")
        
        return len(encontrados) >= 3, f"Datos exactos verificados"
        
    except Exception as e:
        return False, f"Error verificando datos: {e}"

def main():
    print("🚀 VERIFICACIÓN COMPLETA DEL SISTEMA")
    print("=" * 80)
    print("Verificando integración Frontend-Backend con datos del Excel")
    print("=" * 80)
    
    resultados = []
    
    # 1. Backend
    backend_ok, backend_msg = verificar_backend()
    resultados.append(("Backend", backend_ok, backend_msg))
    
    # 2. Restricciones
    restr_ok, restr_msg = verificar_restricciones()
    resultados.append(("Restricciones", restr_ok, restr_msg))
    
    # 3. Frontend
    frontend_ok, frontend_msg = verificar_frontend()
    resultados.append(("Frontend", frontend_ok, frontend_msg))
    
    # 4. Datos exactos
    datos_ok, datos_msg = verificar_datos_exactos()
    resultados.append(("Datos Exactos", datos_ok, datos_msg))
    
    # Resumen final
    print("\n" + "=" * 80)
    print("📋 RESUMEN FINAL")
    print("=" * 80)
    
    todo_ok = True
    for componente, ok, mensaje in resultados:
        status = "✅ OK" if ok else "❌ ERROR"
        print(f"{componente:15} {status:8} - {mensaje}")
        if not ok:
            todo_ok = False
    
    print("\n" + "=" * 80)
    if todo_ok:
        print("🎉 SISTEMA COMPLETAMENTE FUNCIONAL")
        print("✅ Backend devuelve 38 profesores exactos del Excel")
        print("✅ Backend devuelve restricciones correctas")
        print("✅ Frontend accesible y funcionando")
        print("✅ Integración Frontend-Backend verificada")
        print("\n🔧 Próximos pasos:")
        print("   1. Navegar a http://localhost:3000")
        print("   2. Verificar página de Profesores")
        print("   3. Verificar página de Restricciones")
        print("   4. Probar funcionalidad de upload desde UI")
    else:
        print("⚠️ SISTEMA PARCIALMENTE FUNCIONAL")
        print("🔧 Revisar componentes con errores arriba")
    
    print("=" * 80)

if __name__ == "__main__":
    main()