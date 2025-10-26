"""
Analiza Horario_Docentes para entender la estructura de ligas
"""
import pandas as pd
import re

# Leer horario de docentes
df = pd.read_excel('../inputs/Horario_Docentes(2025-20).xlsx', header=None)

print("=" * 80)
print("ANÁLISIS DE LIGAS EN HORARIO DE DOCENTES")
print("=" * 80)

# Buscar ejemplos de ligas (T1, T2, P1, P2, L1, L2, etc.)
patron_liga = r'(\w+.*?)\((T|P|L)(\d+)\)'

ligas_encontradas = {}

for col in df.columns:
    for idx, valor in df[col].items():
        if pd.notna(valor):
            valor_str = str(valor)
            matches = re.findall(patron_liga, valor_str)
            
            for curso, tipo, liga_num in matches:
                curso = curso.strip()
                key = f"{curso}_{tipo}"
                
                if key not in ligas_encontradas:
                    ligas_encontradas[key] = set()
                
                ligas_encontradas[key].add(int(liga_num))

# Mostrar resultados
print("\n📚 CURSOS CON MÚLTIPLES LIGAS:")
print("=" * 80)

cursos_con_ligas = {}
for key, ligas in sorted(ligas_encontradas.items()):
    curso, tipo = key.rsplit('_', 1)
    
    if curso not in cursos_con_ligas:
        cursos_con_ligas[curso] = {'T': set(), 'P': set(), 'L': set()}
    
    cursos_con_ligas[curso][tipo] = ligas

# Mostrar cursos con estructura completa
for curso, tipos in sorted(cursos_con_ligas.items())[:15]:  # Primeros 15
    max_teorias = max(tipos['T']) if tipos['T'] else 0
    max_practicas = max(tipos['P']) if tipos['P'] else 0
    max_labs = max(tipos['L']) if tipos['L'] else 0
    
    print(f"\n🎓 {curso[:50]}")
    print(f"   Teorías: {sorted(tipos['T']) if tipos['T'] else '❌'}")
    print(f"   Prácticas: {sorted(tipos['P']) if tipos['P'] else '❌'}")
    print(f"   Laboratorios: {sorted(tipos['L']) if tipos['L'] else '❌'}")
    
    if max_teorias > 0:
        print(f"   💡 LIGAS IDENTIFICADAS: {max_teorias}")

print("\n" + "=" * 80)
print("📊 ESTADÍSTICAS:")
print("=" * 80)

# Contar cursos por número de ligas
ligas_por_curso = {}
for curso, tipos in cursos_con_ligas.items():
    num_ligas = max(tipos['T']) if tipos['T'] else 0
    if num_ligas > 0:
        if num_ligas not in ligas_por_curso:
            ligas_por_curso[num_ligas] = []
        ligas_por_curso[num_ligas].append(curso)

for num, cursos in sorted(ligas_por_curso.items()):
    print(f"  • {num} liga(s): {len(cursos)} cursos")

print("\n" + "=" * 80)
print("🔍 EJEMPLOS DE ASIGNACIONES DEL HORARIO:")
print("=" * 80)

# Mostrar algunos ejemplos reales
ejemplos = []
for col in df.columns[3:9]:  # Columnas de días
    for idx, valor in df[col].items():
        if pd.notna(valor):
            valor_str = str(valor)
            if '(T1)' in valor_str or '(P1)' in valor_str or '(L1)' in valor_str:
                ejemplos.append(valor_str[:100])
                if len(ejemplos) >= 10:
                    break
        if len(ejemplos) >= 10:
            break

for i, ejemplo in enumerate(ejemplos[:10], 1):
    print(f"{i}. {ejemplo}")
