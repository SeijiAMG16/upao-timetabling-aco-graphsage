#!/usr/bin/env python3
"""
Probar extractor mejorado
"""
import requests

def test_extractor_mejorado():
    print('=== PROBANDO EXTRACTOR MEJORADO ===')
    
    with open('inputs/Horario_Docentes(2025-20).xlsx', 'rb') as f:
        response = requests.post('http://localhost:8000/api/professors-upload/upload', files={'file': f})

    if response.status_code == 200:
        data = response.json()
        print('✅ Upload exitoso')
        
        stats = data.get('stats', {})
        print(f'📊 ESTADÍSTICAS:')
        print(f'   Hojas procesadas: {stats.get("hojas_procesadas", 0)}')
        print(f'   Profesores identificados: {stats.get("profesores_identificados", 0)}')
        print(f'   Cursos identificados: {stats.get("cursos_identificados", 0)}')
        print(f'   Asignaciones creadas: {stats.get("asignaciones_creadas", 0)}')
        print(f'   Restricciones encontradas: {stats.get("restricciones_encontradas", 0)}')
        
        total_profesores = data.get('total_professors', 0)
        print(f'📋 Total profesores procesados: {total_profesores}')
        
        if total_profesores > 0:
            print(f'📝 Algunos profesores procesados:')
            for i, prof in enumerate(data['professors'][:5]):
                nombre = prof.get('nombre_completo', 'N/A')
                restrictions = prof.get('restrictions_count', 0)
                print(f'   {i+1}. {nombre} ({restrictions} restricciones)')
                
        return stats.get("hojas_procesadas", 0)
    else:
        print(f'❌ Error: {response.status_code}')
        print('Response:', response.text)
        return 0

if __name__ == "__main__":
    hojas_procesadas = test_extractor_mejorado()
    
    print(f'\n📈 RESULTADO:')
    print(f'   Hojas esperadas: 38')
    print(f'   Hojas procesadas: {hojas_procesadas}')
    
    if hojas_procesadas >= 35:  # Permitir margen de error
        print('🎉 ¡ÉXITO! Se están procesando casi todas las hojas')
    elif hojas_procesadas >= 25:
        print('✅ MEJORA SIGNIFICATIVA en el procesamiento')
    else:
        print('⚠️ Aún hay problemas en el procesamiento')