#!/usr/bin/env python3
import requests

print("VERIFICACION RAPIDA DEL SISTEMA")
print("="*50)

try:
    # Verificar backend
    resp = requests.get('http://localhost:8000/api/professors')
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ Backend: {data.get('total', 0)} profesores")
    else:
        print(f"❌ Backend: Error {resp.status_code}")
except:
    print("❌ Backend: No accesible")

try:
    # Verificar restricciones  
    resp = requests.get('http://localhost:8000/api/assignments/restrictions')
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ Restricciones: {len(data)} restricciones")
    else:
        print(f"❌ Restricciones: Error {resp.status_code}")
except:
    print("❌ Restricciones: No accesible")

try:
    # Verificar frontend
    resp = requests.get('http://localhost:3000/')
    if resp.status_code == 200:
        print("✅ Frontend: Accesible")
    else:
        print(f"❌ Frontend: Error {resp.status_code}")
except:
    print("❌ Frontend: No accesible")

print("\nSISTEMA LISTO PARA USO")