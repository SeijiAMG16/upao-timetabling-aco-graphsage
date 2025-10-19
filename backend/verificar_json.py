import json

with open('horario_generado_20251018_191408.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Keys del JSON: {list(data.keys())}")
print(f"Total de asignaciones: {len(data.get('assignments', []))}")

if 'assignments' in data and len(data['assignments']) > 0:
    print(f"\nPrimera asignación:")
    first = data['assignments'][0]
    for key, value in first.items():
        print(f"  {key}: {value}")
