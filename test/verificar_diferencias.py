#!/usr/bin/env python3
"""
Verificar diferencias entre mapeo y profesores procesados
"""

MAPEO_ESPERADO = {
    'A. Caballero': 'CABALLERO ALVARADO, ARMANDO',
    'C.Cuba': 'CAROLA LIZETH CUBA CASTILLO', 
    'C.Gay': 'Carlos Gaytan Toledo',
    'C. Guijon': 'Carlos Guijon Guerra',
    'C. Julca': 'Carlos Edwin Julca Castillo',
    'C.Mend': 'MENDOZA CORPUS CARLOS',
    'E.Cieza': 'CIEZA MOSTACERO SEGUNDO EDWIN',
    'E. Chav': 'Edilberto Chavez Fernandez',
    'E.SantaC': 'SANTA CRUZ, ELIAS',
    'Espinola': 'Espinola',
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

PROCESADOS = [
    'CABALLERO ALVARADO, ARMANDO',
    'CAROLA LIZETH CUBA CASTILLO',
    'Carlos Gaytan Toledo',
    'MENDOZA CORPUS CARLOS',
    'CIEZA MOSTACERO SEGUNDO EDWIN',
    'SANTA CRUZ, ELIAS',
    'Espinola',
    'Eddy Miranda Velasquez',
    'Freddy Infantes Quiroz',
    'Fernando Perez Cueva',
    'Fernando Castillo Robles',
    'Heber Abanto Cabrera',
    'Henry Mendoza Puerta',
    'Hernan Sagastegui Chigne',
    'BAYLÓN CARRANZA JORGE RAMÓN',
    'Jose Calderon Sedano',
    'Jose Castañeda Saldaña',
    'Jaime Diaz Sanchez',
    'GUTIERREZ GUTIERREZ JORGE LUIS',
    'Jorge Huapaya Escobedo',
    'Jorge Jara Arenas',
    'Jorge Piminchumo Flores',
    'Luis Vladimir Urrelo',
    'Lenin Llanos Leon',
    'LLERENA FERNANDEZ, MONICA',
    'PEREZ CHAVEZ MOISES',
    'VALVERDE VELA SHEYLI',
    'Walter Cueva Chavez',
    'Walter Lazo',
    'Walter Leturia',
    'Zoraida Vidal Melgarejo'
]

def verificar_diferencias():
    print("=== VERIFICANDO DIFERENCIAS ===")
    
    esperados = list(MAPEO_ESPERADO.values())
    
    print(f"Profesores esperados: {len(esperados)}")
    print(f"Profesores procesados: {len(PROCESADOS)}")
    
    no_procesados = []
    for nombre in esperados:
        if nombre not in PROCESADOS:
            no_procesados.append(nombre)
    
    print(f"\nProfesores NO procesados ({len(no_procesados)}):")
    for nombre in no_procesados:
        # Buscar la hoja correspondiente
        hoja = None
        for h, n in MAPEO_ESPERADO.items():
            if n == nombre:
                hoja = h
                break
        print(f"  - {nombre} (hoja: {hoja})")
    
    # Buscar cuáles hojas podrían tener problemas
    hojas_problematicas = []
    for hoja, nombre in MAPEO_ESPERADO.items():
        if nombre not in PROCESADOS:
            hojas_problematicas.append(hoja)
    
    print(f"\nHojas que podrían tener problemas ({len(hojas_problematicas)}):")
    for hoja in hojas_problematicas:
        print(f"  - {hoja}")

if __name__ == "__main__":
    verificar_diferencias()