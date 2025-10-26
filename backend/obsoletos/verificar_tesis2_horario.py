"""
Verificar que TESIS II en el horario generado respeta las asignaciones por liga
"""
import json
import glob

# Encontrar el archivo más reciente
files = sorted(glob.glob("horario_generado_*.json"), key=lambda x: x, reverse=True)
if not files:
    print("No se encontró archivo de horario generado")
    exit(1)

latest_file = files[0]
print(f"Verificando archivo: {latest_file}\n")

with open(latest_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Detectar la clave correcta
if 'assignments' in data:
    assignments_key = 'assignments'
elif 'asignaciones' in data:
    assignments_key = 'asignaciones'
elif 'schedule' in data:
    assignments_key = 'schedule'
else:
    print(f"Claves disponibles en JSON: {list(data.keys())}")
    print("No se encontró la clave de asignaciones")
    exit(1)

print(f"Usando clave: '{assignments_key}' con {len(data[assignments_key])} asignaciones\n")

print("="*80)
print("VERIFICACIÓN: TESIS II (HUMA900) - Asignaciones por Liga")
print("="*80)
print("\nESPERADO:")
print("  Liga 1: Profesor 307 (Cieza)")  
print("  Liga 2: Profesor 321 (Jaime Díaz)")
print("  Liga 3: Profesor 307 (Cieza)")
print("  Liga 4: Profesor 307 (Cieza)")

# Buscar TESIS II
tesis_assignments = [a for a in data[assignments_key] if a['course_code'] == 'HUMA900']

if not tesis_assignments:
    print("\n⚠️ TESIS II (HUMA900) NO encontrada en el horario generado")
    print(f"\nTotal de asignaciones: {len(data[assignments_key])}")
    
    # Mostrar algunos cursos HUMA
    huma_courses = [a for a in data[assignments_key] if 'HUMA' in a['course_code']]
    print(f"Cursos HUMA encontrados: {len(huma_courses)}")
    for a in sorted(set([a['course_code'] for a in huma_courses])):
        print(f"  - {a}")
else:
    print("\n\nREAL (generado):")
    for assignment in sorted(tesis_assignments, key=lambda x: (x['league_id'], x['session_type'])):
        liga = assignment['league_id']
        tipo = assignment['session_type']
        prof = assignment['professor_id']
        aula = assignment['classroom_id']
        timeslots = assignment['timeslot_ids']
        alumnos = assignment['alumnos_proyectados']
        
        print(f"  Liga {liga} - Tipo {tipo}: Profesor {prof} - Aula {aula} - Timeslots {timeslots} - {alumnos} alumnos")
    
    # Verificar corrección
    print("\n" + "="*80)
    print("RESULTADO:")
    print("="*80)
    
    ligas = {}
    for a in tesis_assignments:
        if a['league_id'] not in ligas:
            ligas[a['league_id']] = set()
        ligas[a['league_id']].add(a['professor_id'])
    
    errores = []
    if 1 in ligas and 307 not in ligas[1]:
        errores.append(f"❌ Liga 1: Esperado Prof 307, obtenido {ligas[1]}")
    elif 1 in ligas:
        print("✅ Liga 1: Profesor 307 (Cieza) - CORRECTO")
    
    if 2 in ligas and 321 not in ligas[2]:
        errores.append(f"❌ Liga 2: Esperado Prof 321, obtenido {ligas[2]}")
    elif 2 in ligas:
        print("✅ Liga 2: Profesor 321 (Jaime Díaz) - CORRECTO")
    
    if 3 in ligas and 307 not in ligas[3]:
        errores.append(f"❌ Liga 3: Esperado Prof 307, obtenido {ligas[3]}")
    elif 3 in ligas:
        print("✅ Liga 3: Profesor 307 (Cieza) - CORRECTO")
    
    if 4 in ligas and 307 not in ligas[4]:
        errores.append(f"❌ Liga 4: Esperado Prof 307, obtenido {ligas[4]}")
    elif 4 in ligas:
        print("✅ Liga 4: Profesor 307 (Cieza) - CORRECTO")
    
    if errores:
        print("\n⚠️ ERRORES encontrados:")
        for e in errores:
            print(f"  {e}")
    else:
        print("\n🎉 TODAS LAS ASIGNACIONES POR LIGA SON CORRECTAS")

print(f"\nTotal de secciones asignadas en el horario: {len(data[assignments_key])}/315")
