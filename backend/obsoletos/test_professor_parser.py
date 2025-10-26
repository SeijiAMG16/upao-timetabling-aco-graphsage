"""
Script de prueba para el parser de profesores
"""
from app.excel.professor_schedule_parser import parse_professor_schedules

result = parse_professor_schedules('../inputs/Horario_Docentes(2025-20).xlsx')

print('\n' + '='*80)
print('RESUMEN DE EXTRACCIÓN')
print('='*80)
print(f'✅ Profesores extraídos: {result["total_professors"]}')
print(f'✅ Restricciones extraídas: {result["total_restrictions"]}')

if result['professors']:
    print('\n' + '='*80)
    print('PRIMEROS 3 PROFESORES')
    print('='*80)
    for i, prof in enumerate(result['professors'][:3], 1):
        print(f"\n{i}. {prof['nombre_completo']} ({prof['codigo']})")
        print(f"   Email: {prof['email']}")
        print(f"   Categoría: {prof['categoria']}")
        print(f"   Restricciones: {prof['restrictions_count']}")

if result['restrictions']:
    print('\n' + '='*80)
    print('PRIMERAS 5 RESTRICCIONES')
    print('='*80)
    for i, rest in enumerate(result['restrictions'][:5], 1):
        print(f"\n{i}. {rest['professor_name']}")
        print(f"   Día: {rest['day']} | {rest['start_time']} - {rest['end_time']}")
        print(f"   Razón: {rest['reason']}")
