import json

with open('horario_generado_20251022_015751.json', 'r', encoding='utf-8') as f:
    horario = json.load(f)

print(f"Total asignaciones: {len(horario['asignaciones'])}")

# Buscar HUMA900
huma900 = []
for asig in horario['asignaciones']:
    if asig.get('curso_codigo') == 'HUMA900':
        huma900.append(asig)

print(f"\nHUMA900: {len(huma900)} asignaciones encontradas")

for h in huma900:
    print(f"\n  Liga {h['liga']} - Tipo {h['tipo']} - Prof {h['profesor_id']}")
    print(f"    Aula: {h['aula_id']} - Timeslots: {h['timeslots']}")
