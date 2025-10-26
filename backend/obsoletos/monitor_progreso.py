"""
Script para monitorear el progreso de la ejecución ACO
"""
import sys
import time
from datetime import datetime

print("="*80)
print("MONITOR DE PROGRESO - ACO")
print("="*80)
print(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("\nEsperando salida del proceso ACO...")
print("Este proceso tomará aproximadamente 5-7 minutos para 10 iteraciones.")
print("\nProgreso esperado:")
print("  - Preparación del grafo: ~30 segundos")
print("  - Por iteración: ~30-40 segundos")
print("  - Total estimado: 5-7 minutos")
print("="*80)
