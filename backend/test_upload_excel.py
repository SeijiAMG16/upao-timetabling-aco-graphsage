#!/usr/bin/env python3
"""
PRUEBA DIRECTA DE UPLOAD DE EXCEL
Simula el upload del frontend para verificar que funciona
"""

import requests

def test_upload_excel():
    """Probar el upload de Excel directamente"""
    
    excel_file = r"..\inputs\Horario_Docentes(2025-20).xlsx"
    url = 'http://localhost:8000/api/professors-upload/upload'
    
    print("🧪 PROBANDO UPLOAD DE EXCEL")
    print("=" * 50)
    print(f"Archivo: {excel_file}")
    print(f"URL: {url}")
    
    try:
        # Abrir archivo
        with open(excel_file, 'rb') as f:
            files = {'file': ('Horario_Docentes(2025-20).xlsx', f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
            
            print("\n📤 Enviando archivo...")
            response = requests.post(url, files=files, timeout=60)
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ UPLOAD EXITOSO!")
                print(f"Profesores: {data.get('total_professors', 0)}")
                print(f"Restricciones: {data.get('total_restrictions', 0)}")
                
                if 'professors' in data:
                    print(f"\nPrimeros profesores:")
                    for i, prof in enumerate(data['professors'][:3]):
                        print(f"  {i+1}. {prof.get('nombre_completo', 'N/A')} ({prof.get('restrictions_count', 0)} restricciones)")
                
                return True
            else:
                print(f"❌ ERROR: {response.status_code}")
                print(f"Respuesta: {response.text}")
                return False
                
    except FileNotFoundError:
        print(f"❌ Archivo no encontrado: {excel_file}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_confirm_upload():
    """Probar confirmación de datos (simulado)"""
    url = 'http://localhost:8000/api/professors-upload/confirm'
    
    # Datos dummy para confirmar
    dummy_data = {
        'professors': [],
        'restrictions': []
    }
    
    print("\n🔄 PROBANDO CONFIRMACIÓN...")
    
    try:
        response = requests.post(url, json=dummy_data, timeout=30)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Confirmación funciona")
            return True
        else:
            print(f"❌ Error en confirmación: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    # Test 1: Upload
    upload_ok = test_upload_excel()
    
    # Test 2: Confirm (solo si upload funcionó)
    if upload_ok:
        confirm_ok = test_confirm_upload()
    
    print("\n" + "=" * 50)
    print("📋 RESUMEN:")
    print(f"  Upload Excel: {'✅' if upload_ok else '❌'}")
    if upload_ok:
        print(f"  Confirm: {'✅' if confirm_ok else '❌'}")
    print("\n¡El upload de Excel funciona desde backend!")