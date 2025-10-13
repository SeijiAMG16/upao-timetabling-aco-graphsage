#!/usr/bin/env python3
"""
Verificar endpoints desde frontend
"""
import requests
import json

def test_professors_endpoint():
    print('=== VERIFICANDO ENDPOINT DE PROFESORES ===')
    
    try:
        response = requests.get('http://localhost:8000/api/professors')
        print(f'Status: {response.status_code}')
        
        if response.status_code == 200:
            data = response.json()
            total = data.get('total', len(data.get('professors', [])))
            print(f'Total profesores devueltos: {total}')
            
            if total > 0:
                professors = data.get('professors', [])
                print(f'Primeros 5 profesores:')
                for i, prof in enumerate(professors[:5]):
                    nombre = prof.get('nombre_completo', 'N/A')
                    codigo = prof.get('codigo', 'N/A')
                    categoria = prof.get('categoria', 'N/A')
                    print(f'  {i+1}. {codigo} - {nombre} ({categoria})')
                
                return True, total
            else:
                print('❌ No se devolvieron profesores')
                return False, 0
        else:
            print(f'Error: {response.text}')
            return False, 0
            
    except Exception as e:
        print(f'Error de conexión: {e}')
        return False, 0

def test_restrictions_endpoint():
    print('\n=== VERIFICANDO ENDPOINT DE RESTRICCIONES ===')
    
    # Verificar si existe endpoint de restricciones
    endpoints_to_try = [
        'http://localhost:8000/api/professors-restrictions',
        'http://localhost:8000/api/restrictions',
        'http://localhost:8000/api/professor-restrictions'
    ]
    
    for endpoint in endpoints_to_try:
        try:
            response = requests.get(endpoint)
            print(f'{endpoint} -> Status: {response.status_code}')
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    print(f'  Total restricciones: {len(data)}')
                    if len(data) > 0:
                        print(f'  Primera restricción: {data[0]}')
                elif isinstance(data, dict):
                    if 'restrictions' in data:
                        print(f'  Total restricciones: {len(data["restrictions"])}')
                    else:
                        print(f'  Estructura: {list(data.keys())}')
                return True
            elif response.status_code == 404:
                print(f'  Endpoint no existe')
            else:
                print(f'  Error: {response.text[:100]}')
                
        except Exception as e:
            print(f'  Error: {e}')
    
    return False

def check_backend_status():
    print('\n=== VERIFICANDO ESTADO DEL BACKEND ===')
    
    try:
        response = requests.get('http://localhost:8000/')
        print(f'Backend root status: {response.status_code}')
        
        # Verificar docs
        response = requests.get('http://localhost:8000/docs')
        print(f'Docs endpoint: {response.status_code}')
        
        return True
    except Exception as e:
        print(f'Backend no accesible: {e}')
        return False

if __name__ == "__main__":
    print("🔍 VERIFICACIÓN DE ENDPOINTS FRONTEND-BACKEND")
    print("="*60)
    
    # 1. Estado del backend
    backend_ok = check_backend_status()
    
    # 2. Endpoint de profesores
    prof_ok, prof_count = test_professors_endpoint()
    
    # 3. Endpoint de restricciones
    restr_ok = test_restrictions_endpoint()
    
    print("\n" + "="*60)
    print("📊 RESUMEN:")
    print(f"  Backend activo: {'✅' if backend_ok else '❌'}")
    print(f"  Profesores endpoint: {'✅' if prof_ok else '❌'} ({prof_count} profesores)")
    print(f"  Restricciones endpoint: {'✅' if restr_ok else '❌'}")
    
    if prof_ok and prof_count == 38:
        print("\n✅ Backend devuelve datos correctos")
        print("🔧 El problema está en el frontend - necesita refrescar cache")
    elif prof_count > 0 and prof_count != 38:
        print(f"\n⚠️ Backend devuelve {prof_count} profesores, esperados 38")
    else:
        print("\n❌ Backend no devuelve datos de profesores")