import json

with open('horario_generado_20251022_015751.json', 'r', encoding='utf-8') as f:
    horario = json.load(f)

# Buscar ISIA125
isia125 = [a for a in horario['asignaciones'] if a['course_code'] == 'ISIA125']

print("="*80)
print("ISIA125 (TESIS II) - Verificación en Horario Generado")
print("="*80)
print(f"\nTotal asignaciones: {len(isia125)}")

print("\nDetalle:")
for a in isia125:
    print(f"  Liga {a['league_id']} - Tipo {a['session_type']} - Profesor {a['professor_id']}")

print("\n" + "="*80)
print("ESPERADO (según BD):")
print("="*80)
print("  Liga 1 - Tipo T: Profesor 328 (Cieza)")
print("  Liga 1 - Tipo P: Profesor 328 (Cieza)")
print("  Liga 2 - Tipo T: Profesor 342 (Jaime Díaz)")
print("  Liga 2 - Tipo P: Profesor 342 (Jaime Díaz)")
print("  Liga 3 - Tipo T: Profesor 328 (Cieza)")
print("  Liga 3 - Tipo P: Profesor 328 (Cieza)")
print("  Liga 4 - Tipo T: Profesor 328 (Cieza)")
print("  Liga 4 - Tipo P: Profesor 328 (Cieza)")

print("\n" + "="*80)
print("RESULTADO:")
print("="*80)

# Verificar
expected = {
    (1, 'T'): 328,
    (1, 'P'): 328,
    (2, 'T'): 342,
    (2, 'P'): 342,
    (3, 'T'): 328,
    (3, 'P'): 328,
    (4, 'T'): 328,
    (4, 'P'): 328,
}

errors = []
for a in isia125:
    key = (a['league_id'], a['session_type'])
    if key in expected:
        if a['professor_id'] != expected[key]:
            errors.append(f"❌ Liga {a['league_id']} - Tipo {a['session_type']}: Esperado Prof {expected[key]}, obtenido Prof {a['professor_id']}")
        else:
            print(f"✅ Liga {a['league_id']} - Tipo {a['session_type']}: Correcto (Prof {a['professor_id']})")

if errors:
    print("\n⚠️ ERRORES encontrados:")
    for err in errors:
        print(f"  {err}")
else:
    print("\n✅ TODAS LAS ASIGNACIONES SON CORRECTAS")
