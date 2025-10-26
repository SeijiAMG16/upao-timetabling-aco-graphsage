import json
import pprint

with open('horario_generado_20251022_015751.json', 'r', encoding='utf-8') as f:
    horario = json.load(f)

print("Claves del horario:")
print(horario.keys())

print("\n" + "="*80)
print("PRIMERA ASIGNACIÓN (ejemplo):")
print("="*80)
pprint.pprint(horario['asignaciones'][0])
