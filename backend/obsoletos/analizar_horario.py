import json

# Leer horario
with open('horario_generado_20251022_015751.json', 'r', encoding='utf-8') as f:
    horario = json.load(f)

print(f"Total asignaciones: {len(horario['asignaciones'])}")
print(f"\n{'='*80}")
print("PROFESORES ÚNICOS EN EL HORARIO:")
print('='*80)

# Obtener todos los professor_ids únicos
prof_ids = set()
for asig in horario['asignaciones']:
    prof_ids.add(asig['professor_id'])

print(f"\nTotal profesores diferentes: {len(prof_ids)}")
print(f"IDs: {sorted(prof_ids)}")

# Verificar si hay profesor 368, 307, 321, 328, 342
target_profs = [368, 307, 321, 328, 342]
print(f"\n{'='*80}")
print("VERIFICACIÓN DE PROFESORES ESPECÍFICOS:")
print('='*80)

for pid in target_profs:
    asigs = [a for a in horario['asignaciones'] if a['professor_id'] == pid]
    print(f"\nProfesor {pid}: {len(asigs)} asignaciones")
    if len(asigs) > 0:
        # Mostrar primeras 3
        for i, a in enumerate(asigs[:3]):
            print(f"  {i+1}. Curso {a['course_code']} - Liga {a['league_id']} - Tipo {a['session_type']}")

# Buscar cursos con "TESIS" en el nombre
print(f"\n{'='*80}")
print("CURSOS CON 'TESIS' o 'ISIA125' EN EL HORARIO:")
print('='*80)

cursos_unicos = {}
for asig in horario['asignaciones']:
    curso = asig['course_code']
    if curso not in cursos_unicos:
        cursos_unicos[curso] = 0
    cursos_unicos[curso] += 1

tesis_courses = {k: v for k, v in cursos_unicos.items() if 'TESIS' in k.upper() or 'ISIA125' in k or 'HUMA900' in k}

if tesis_courses:
    for curso, count in tesis_courses.items():
        print(f"  {curso}: {count} asignaciones")
        # Mostrar detalles
        asigs_curso = [a for a in horario['asignaciones'] if a['course_code'] == curso]
        for a in asigs_curso:
            print(f"    Liga {a['league_id']} - Tipo {a['session_type']} - Prof {a['professor_id']}")
else:
    print("  ⚠️ NO se encontraron cursos con 'TESIS', 'ISIA125' o 'HUMA900'")

print(f"\n{'='*80}")
print("PRIMEROS 10 CURSOS ÚNICOS:")
print('='*80)
for i, (curso, count) in enumerate(list(cursos_unicos.items())[:10]):
    print(f"  {curso}: {count} asignaciones")
