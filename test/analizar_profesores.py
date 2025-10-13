#!/usr/bin/env python3
"""
Comparar profesores en BD vs hojas del Excel
"""
import requests

def analizar_profesores():
    # Obtener profesores de BD
    response = requests.get('http://localhost:8000/api/professors')
    data = response.json()

    print('PROFESORES EN BD:')
    profesores_bd = []
    for i, prof in enumerate(data['professors'], 1):
        nombre = prof.get('nombre_completo', 'N/A')
        profesores_bd.append(nombre)
        print(f'{i:2d}. {nombre}')

    # Hojas del Excel
    hojas = [
        'A. Caballero', 'C.Cuba', 'C.Gay', 'C. Guijon', 'C. Julca', 'C.Mend',
        'E.Cieza', 'E. Chav', 'E.SantaC', 'Espinola', 'E.Mir', 'F.Inf',
        'F.Per', 'F.Cas', 'H.Aba', 'H. Mendoza', 'H.Sag', 'J. Baylon',
        'J.Cal', 'J.Cast', 'J.Dia', 'J. Gutierrez', 'J.Hua', 'J.Jar',
        'J.Pim', 'J.Vasquez', 'K.Mel', 'L.Vla', 'L.Llanos', 'M. Llerena',
        'Moises', 'STAFF', 'S.Rodri', 'Sheyli', 'W.Cue', 'W.Lazo', 'W.Letur', 'Z.Vidal'
    ]

    print(f'\nTotal profesores en BD: {len(profesores_bd)}')
    print(f'Total hojas de profesores: {len(hojas)}')
    
    print(f'\nHOJAS DEL EXCEL:')
    for i, hoja in enumerate(hojas, 1):
        print(f'{i:2d}. {hoja}')
    
    # Intentar hacer matching manual
    print(f'\nMATCHING BÁSICO:')
    matches = 0
    no_matches = []
    
    for hoja in hojas:
        match_found = False
        hoja_clean = hoja.replace('.', '').replace(' ', '').lower()
        
        for prof_bd in profesores_bd:
            prof_clean = prof_bd.replace(' ', '').replace(',', '').lower()
            
            # Buscar si alguna parte del nombre de la hoja está en el profesor
            if any(part in prof_clean for part in hoja_clean.split() if len(part) > 2):
                print(f'  ✅ {hoja} -> {prof_bd}')
                matches += 1
                match_found = True
                break
        
        if not match_found:
            no_matches.append(hoja)
    
    print(f'\nRESUMEN:')
    print(f'  Matches encontrados: {matches}')
    print(f'  Sin match: {len(no_matches)}')
    
    if no_matches:
        print(f'  Hojas sin match:')
        for hoja in no_matches:
            print(f'    - {hoja}')

if __name__ == "__main__":
    analizar_profesores()