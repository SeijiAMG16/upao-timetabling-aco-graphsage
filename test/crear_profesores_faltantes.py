#!/usr/bin/env python3
"""
Crear profesores faltantes en la BD
"""
import requests
import json

# Profesores que necesitamos crear
NUEVOS_PROFESORES = [
    {
        'codigo': '000000039',  # Siguiente código disponible
        'nombre_completo': 'Jose Baylon',
        'categoria': 'DOCENTE',
        'carga_maxima_horas': 40
    },
    {
        'codigo': '000000040',
        'nombre_completo': 'Jose Gutierrez', 
        'categoria': 'DOCENTE',
        'carga_maxima_horas': 40
    },
    {
        'codigo': '000000041',
        'nombre_completo': 'Jose Vasquez',
        'categoria': 'DOCENTE', 
        'carga_maxima_horas': 40
    },
    {
        'codigo': '000000042',
        'nombre_completo': 'Karen Melendez',  # Asumiendo K.Mel
        'categoria': 'DOCENTE',
        'carga_maxima_horas': 40
    },
    {
        'codigo': '000000043',
        'nombre_completo': 'Luis Llanos',
        'categoria': 'DOCENTE',
        'carga_maxima_horas': 40
    },
    {
        'codigo': '000000044', 
        'nombre_completo': 'Moises',
        'categoria': 'DOCENTE',
        'carga_maxima_horas': 40
    },
    {
        'codigo': '000000045',
        'nombre_completo': 'STAFF GENERAL',
        'categoria': 'DOCENTE',
        'carga_maxima_horas': 40
    },
    {
        'codigo': '000000046',
        'nombre_completo': 'Carlos Guijon',
        'categoria': 'DOCENTE',
        'carga_maxima_horas': 40
    }
]

def crear_profesores_faltantes():
    print("=== CREANDO PROFESORES FALTANTES ===")
    
    # Primero verificar cuántos hay actualmente
    response = requests.get('http://localhost:8000/api/professors')
    if response.status_code == 200:
        current_count = response.json()['total']
        print(f"Profesores actuales: {current_count}")
    
    # Crear cada profesor via API (simulado, ya que no tenemos endpoint de creación)
    # Lo haremos directo en BD con Python
    
    import pymysql
    
    try:
        conn = pymysql.connect(
            host='localhost',
            user='root', 
            password='sistemas',
            database='upao_timetabling'
        )
        cursor = conn.cursor()
        
        creados = 0
        for prof in NUEVOS_PROFESORES:
            try:
                sql = """
                INSERT INTO professors 
                (codigo, nombre_completo, categoria, carga_maxima_horas, 
                 disponible_lunes, disponible_martes, disponible_miercoles,
                 disponible_jueves, disponible_viernes, disponible_sabado)
                VALUES (%s, %s, %s, %s, 1, 1, 1, 1, 1, 1)
                """
                
                cursor.execute(sql, (
                    prof['codigo'],
                    prof['nombre_completo'], 
                    prof['categoria'],
                    prof['carga_maxima_horas']
                ))
                
                print(f"✅ Creado: {prof['nombre_completo']}")
                creados += 1
                
            except Exception as e:
                print(f"❌ Error creando {prof['nombre_completo']}: {e}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"\n🎉 {creados} profesores creados exitosamente")
        
        # Verificar total después
        response = requests.get('http://localhost:8000/api/professors')
        if response.status_code == 200:
            new_count = response.json()['total']
            print(f"Profesores después: {new_count}")
            print(f"Incremento: +{new_count - current_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return False

if __name__ == "__main__":
    crear_profesores_faltantes()