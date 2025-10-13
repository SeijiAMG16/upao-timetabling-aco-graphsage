#!/usr/bin/env python3
"""
Crear mapeo manual de hojas a profesores
"""

# Mapeo manual basado en análisis de nombres
MAPEO_HOJAS_PROFESORES = {
    'A. Caballero': 'CABALLERO ALVARADO, ARMANDO',
    'C.Cuba': 'CAROLA LIZETH CUBA CASTILLO', 
    'C.Gay': 'Carlos Gaytan Toledo',
    'C. Julca': 'Carlos Edwin Julca Castillo',
    'C.Mend': 'MENDOZA CORPUS CARLOS',  # Asumiendo Mendoza
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
    'J.Cal': 'Jose Calderon Sedano',
    'J.Cast': 'Jose Castañeda Saldaña',
    'J.Dia': 'Jaime Diaz Sanchez',
    'J.Hua': 'Jorge Huapaya Escobedo',
    'J.Jar': 'Jorge Jara Arenas',
    'J.Pim': 'Jorge Piminchumo Flores',
    'L.Vla': 'Luis Vladimir Urrelo',
    'M. Llerena': 'LLERENA FERNANDEZ, MONICA',
    'S.Rodri': 'Silvia Rodriguez Aguirre',
    'Sheyli': 'VALVERDE VELA SHEYLI',
    'W.Cue': 'Walter Cueva Chavez',
    'W.Lazo': 'Walter Lazo',
    'W.Letur': 'Walter Leturia',
    'Z.Vidal': 'Zoraida Vidal Melgarejo',
}

# Los que no están en BD y necesitamos crear
PROFESORES_FALTANTES = [
    'J. Baylon',      # No encontrado en BD
    'J. Gutierrez',   # No encontrado en BD
    'J.Vasquez',      # No encontrado en BD
    'K.Mel',          # No encontrado en BD
    'L.Llanos',       # No encontrado en BD
    'Moises',         # No encontrado en BD
    'STAFF',          # Genérico
    'C. Guijon',      # No encontrado en BD
]

def mostrar_mapeo():
    print("MAPEO DE HOJAS A PROFESORES EN BD:")
    print("="*60)
    
    for hoja, profesor in MAPEO_HOJAS_PROFESORES.items():
        print(f"{hoja:15} -> {profesor}")
    
    print(f"\nPROFESORES ENCONTRADOS: {len(MAPEO_HOJAS_PROFESORES)}")
    
    print(f"\nPROFESORES FALTANTES EN BD:")
    print("="*40)
    for prof in PROFESORES_FALTANTES:
        print(f"  - {prof}")
    
    print(f"\nRESUMEN:")
    print(f"  Hojas totales: 38")
    print(f"  Con mapeo a BD: {len(MAPEO_HOJAS_PROFESORES)}")
    print(f"  Faltantes en BD: {len(PROFESORES_FALTANTES)}")
    print(f"  Total: {len(MAPEO_HOJAS_PROFESORES) + len(PROFESORES_FALTANTES)}")

if __name__ == "__main__":
    mostrar_mapeo()