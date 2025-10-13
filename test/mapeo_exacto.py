#!/usr/bin/env python3
"""
Mapeo EXACTO basado en el análisis del Excel
USANDO SOLO LOS NOMBRES QUE APARECEN EN LAS CELDAS
"""

# Mapeo extraído EXACTAMENTE del análisis anterior
MAPEO_EXCEL_EXACTO = {
    'A. Caballero': 'CABALLERO ALVARADO, ARMANDO',
    'C.Cuba': 'CAROLA LIZETH CUBA CASTILLO', 
    'C.Gay': 'Carlos Gaytan Toledo',
    'C. Guijon': 'Carlos Guijon Guerra',
    'C. Julca': 'Carlos Edwin Julca Castillo',
    'C.Mend': 'MENDOZA CORPUS CARLOS',
    'E.Cieza': 'CIEZA MOSTACERO SEGUNDO EDWIN',
    'E. Chav': 'Edilberto Chavez Fernandez',
    'E.SantaC': 'SANTA CRUZ, ELIAS',
    'Espinola': 'Espinola',  # Solo aparece "Espinola" sin apellido completo
    'E.Mir': 'Eddy Miranda Velasquez',
    'F.Inf': 'Freddy Infantes Quiroz',
    'F.Per': 'Fernando Perez Cueva',
    'F.Cas': 'Fernando Castillo Robles',
    'H.Aba': 'Heber Abanto Cabrera',
    'H. Mendoza': 'Henry Mendoza Puerta',
    'H.Sag': 'Hernan Sagastegui Chigne',
    'J. Baylon': 'BAYLÓN CARRANZA JORGE RAMÓN',
    'J.Cal': 'Jose Calderon Sedano',
    'J.Cast': 'Jose Castañeda Saldaña',
    'J.Dia': 'Jaime Diaz Sanchez',
    'J. Gutierrez': 'GUTIERREZ GUTIERREZ JORGE LUIS',
    'J.Hua': 'Jorge Huapaya Escobedo',
    'J.Jar': 'Jorge Jara Arenas',
    'J.Pim': 'Jorge Piminchumo Flores',
    'J.Vasquez': 'VASQUEZ PEREYRA, JOSE',
    'K.Mel': 'Karla Melendez Revilla',
    'L.Vla': 'Luis Vladimir Urrelo',
    'L.Llanos': 'Lenin Llanos Leon',
    'M. Llerena': 'LLERENA FERNANDEZ, MONICA',
    'Moises': 'PEREZ CHAVEZ MOISES',
    'STAFF': 'CONVOCATORIA',
    'S.Rodri': 'Silvia Rodriguez Aguirre',
    'Sheyli': 'VALVERDE VELA SHEYLI',
    'W.Cue': 'Walter Cueva Chavez',
    'W.Lazo': 'Walter Lazo',
    'W.Letur': 'Walter Leturia',
    'Z.Vidal': 'Zoraida Vidal Melgarejo'
}

def mostrar_mapeo_exacto():
    print("=== MAPEO EXACTO EXTRAÍDO DEL EXCEL ===")
    print(f"Total de profesores identificados: {len(MAPEO_EXCEL_EXACTO)}")
    print()
    
    for i, (hoja, nombre) in enumerate(MAPEO_EXCEL_EXACTO.items(), 1):
        print(f"{i:2d}. {hoja:15} -> {nombre}")
    
    print(f"\nTodos los nombres son EXACTAMENTE como aparecen en el Excel")
    return MAPEO_EXCEL_EXACTO

def crear_profesores_en_bd():
    """Crear todos estos profesores en la BD"""
    import pymysql
    
    print("\n=== CREANDO PROFESORES EN BD ===")
    
    conn = pymysql.connect(
        host='localhost',
        user='root',
        password='sistemas',
        database='upao_timetabling'
    )
    
    cursor = conn.cursor()
    
    # Verificar cuáles ya existen
    cursor.execute('SELECT nombre_completo FROM professors')
    existentes = [row[0] for row in cursor.fetchall()]
    print(f"Profesores ya existentes: {len(existentes)}")
    for nombre in existentes:
        print(f"  - {nombre}")
    
    # Crear los que no existen
    creados = 0
    for i, (hoja, nombre_completo) in enumerate(MAPEO_EXCEL_EXACTO.items()):
        if nombre_completo not in existentes:
            try:
                codigo = f"00000{1000 + i:04d}"  # Códigos únicos
                sql = """
                INSERT INTO professors 
                (codigo, nombre_completo, categoria, carga_maxima_horas, 
                 disponible_lunes, disponible_martes, disponible_miercoles,
                 disponible_jueves, disponible_viernes, disponible_sabado)
                VALUES (%s, %s, %s, %s, 1, 1, 1, 1, 1, 1)
                """
                
                cursor.execute(sql, (codigo, nombre_completo, 'DOCENTE', 40))
                print(f"✅ Creado: {nombre_completo}")
                creados += 1
                
            except Exception as e:
                print(f"❌ Error creando {nombre_completo}: {e}")
        else:
            print(f"⏭️ Ya existe: {nombre_completo}")
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"\n🎉 {creados} profesores nuevos creados")
    return creados

if __name__ == "__main__":
    mapeo = mostrar_mapeo_exacto()
    
    respuesta = input("\n¿Crear estos profesores en la BD? (s/n): ")
    if respuesta.lower() == 's':
        crear_profesores_en_bd()
    else:
        print("📋 Mapeo listo para usar en el código")