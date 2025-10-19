import json

with open('horario_generado_20251018_195157.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

total = 315
asignadas = len(data['asignaciones'])
cobertura = asignadas / total * 100

print("="*80)
print("📊 ESTADÍSTICAS DEL HORARIO GENERADO")
print("="*80)
print(f"   Total secciones: {total}")
print(f"   Asignadas: {asignadas}")
print(f"   Cobertura: {cobertura:.1f}%")
print(f"   Profesores únicos: {len(set(a['profesor_id'] for a in data['asignaciones']))}")
print("="*80)
