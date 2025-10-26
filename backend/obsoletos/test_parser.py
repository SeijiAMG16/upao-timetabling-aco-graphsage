"""
Script para verificar que el parser del Excel funcione correctamente
"""
from app.excel.projection_parser import parse_libro1_projections

# Ruta al archivo Excel
excel_path = '../inputs/Libro1.xlsx'

print("=" * 80)
print("PROBANDO PARSER DE EXCEL")
print("=" * 80)

result = parse_libro1_projections(excel_path)

print("\n" + "=" * 80)
print(f"SUCCESS: {result['success']}")
print(f"TOTAL CURSOS: {result['total']}")

if result.get('error'):
    print(f"ERROR: {result['error']}")
else:
    print("\nPRIMEROS 5 CURSOS:")
    for i, course in enumerate(result['courses'][:5], 1):
        print(f"\n{i}. {course['codigo']} - {course['nombre']}")
        print(f"   Ciclo: {course['ciclo']} | Créditos: {course['creditos']}")
        print(f"   Alumnos - T:{course['alumnos_teoria']} P:{course['alumnos_practica']} L:{course['alumnos_laboratorio']}")
        print(f"   Requiere - Práctica:{course['requiere_practica']} Lab:{course['requiere_laboratorio']}")

print("\n" + "=" * 80)
