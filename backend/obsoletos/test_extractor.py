import sys
sys.path.append('.')

# Probar el extractor V4
print("Probando extraer_por_colores_v4...")

# Cambiar el path temporalmente
import extraer_por_colores_v4
original_path = extraer_por_colores_v4.EXCEL_PATH
extraer_por_colores_v4.EXCEL_PATH = '../inputs/Horario_Docentes(2025-20).xlsx'

try:
    asignaciones, restricciones, stats = extraer_por_colores_v4.extraer_asignaciones_v4()
    print(f"\n✅ Extracción completada:")
    print(f"   Asignaciones: {len(asignaciones)}")
    print(f"   Restricciones: {len(restricciones)}")
    print(f"   Stats: {stats}")
    
    if asignaciones:
        print(f"\nPrimera asignación:")
        print(f"   {asignaciones[0]}")
    
    if restricciones:
        print(f"\nPrimera restricción:")
        print(f"   {restricciones[0]}")
        
finally:
    # Restaurar path
    extraer_por_colores_v4.EXCEL_PATH = original_path