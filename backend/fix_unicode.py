#!/usr/bin/env python3
"""Script para reemplazar caracteres Unicode problemáticos con ASCII"""

import sys
from pathlib import Path

# Mapa de reemplazos
REPLACEMENTS = {
    '→': '->',
    '←': '<-',
    '✓': '[OK]',
    '✅': '[OK]',
    '❌': '[X]',
    '🔍': '[BUSCAR]',
    '🚫': '[BLOQUEADO]',
    '🌐': '[VIRTUAL]',
    '⏳': '[PENDIENTE]',
    '✂️': '[BLOQUES]',
    '✂': '[BLOQUES]',
    '🚷': '[CAPACIDAD]',
    '🎓': '[CURRICULA]',
    '🏷️': '[LIGA]',
    '🏷': '[LIGA]',
    '👨‍🏫': '[PROFESOR]',
    '🏫': '[AULA]',
    '⚠️': '[WARN]',
    '⚠': '[WARN]',
    '⛔': '[PROHIBIDO]',
    '💪': '[FUERZA]',
    '📊': '[GRAFICO]',
    '📈': '[METRICA]',
    '📉': '[COSTO]',
    '🎯': '[TARGET]',
    '✨': '[NUEVO]',
    # Caracteres corruptos
    'Ô£ô': '[OK]',
    'ÔåÆ': '->',
}

def fix_file(filepath: Path):
    """Reemplaza caracteres Unicode en un archivo"""
    print(f"Procesando: {filepath}")
    
    # Leer archivo
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"  ERROR leyendo: {e}")
        return False
    
    # Aplicar reemplazos
    original_content = content
    for old, new in REPLACEMENTS.items():
        if old in content:
            count = content.count(old)
            content = content.replace(old, new)
            print(f"  Reemplazado '{old}' -> '{new}' ({count} veces)")
    
    # Guardar si hubo cambios
    if content != original_content:
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  [OK] Archivo actualizado")
            return True
        except Exception as e:
            print(f"  ERROR guardando: {e}")
            return False
    else:
        print(f"  Sin cambios necesarios")
        return False

def main():
    """Procesa todos los archivos Python en el proyecto"""
    backend_dir = Path(__file__).parent
    
    # Archivos a procesar
    files_to_fix = [
        backend_dir / 'app' / 'aco_graphsage' / 'aco_engine.py',
        backend_dir / 'ejecutar_aco_completo.py',
        backend_dir / 'app' / 'aco_graphsage' / 'constraints.py',
        backend_dir / 'app' / 'aco_graphsage' / 'graph_builder.py',
        backend_dir / 'app' / 'aco_graphsage' / 'soft_constraints.py',
    ]
    
    total_fixed = 0
    for filepath in files_to_fix:
        if filepath.exists():
            if fix_file(filepath):
                total_fixed += 1
        else:
            print(f"SKIP: {filepath} (no existe)")
    
    print(f"\n{'='*60}")
    print(f"RESUMEN: {total_fixed} archivos actualizados")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
