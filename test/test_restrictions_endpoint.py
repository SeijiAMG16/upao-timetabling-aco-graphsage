#!/usr/bin/env python3
"""
Verificar endpoint de restricciones correcto
"""
import requests
import json

def test_restrictions_correct_endpoint():
    print('=== VERIFICANDO ENDPOINT DE RESTRICCIONES CORRECTO ===')
    
    try:
        # El endpoint correcto está en assignments con prefijo /api/assignments
        response = requests.get('http://localhost:8000/api/assignments/restrictions')
        print(f'Status: {response.status_code}')
        
        if response.status_code == 200:
            data = response.json()
            print(f'Total restricciones devueltas: {len(data)}')
            
            if len(data) > 0:
                print(f'Primeras 3 restricciones:')
                for i, restr in enumerate(data[:3]):
                    print(f'  {i+1}. Profesor: {restr.get("professor_name", "N/A")}, Día: {restr.get("day", "N/A")}, Horario: {restr.get("start_time", "N/A")}-{restr.get("end_time", "N/A")}')
                
                return True, len(data)
            else:
                print('❌ No se devolvieron restricciones')
                return False, 0
        else:
            print(f'Error: {response.text}')
            return False, 0
            
    except Exception as e:
        print(f'Error de conexión: {e}')
        return False, 0

if __name__ == "__main__":
    print("🔍 VERIFICACIÓN ENDPOINT RESTRICCIONES")
    print("="*50)
    
    restr_ok, restr_count = test_restrictions_correct_endpoint()
    
    print(f"\n📊 RESULTADO:")
    print(f"  Restricciones endpoint: {'✅' if restr_ok else '❌'} ({restr_count} restricciones)")
    
    if restr_count == 44:
        print("\n✅ Backend devuelve restricciones correctas")
    elif restr_count > 0:
        print(f"\n⚠️ Backend devuelve {restr_count} restricciones")
    else:
        print("\n❌ Backend no devuelve restricciones")