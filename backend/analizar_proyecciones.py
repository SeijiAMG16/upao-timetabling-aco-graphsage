"""
Analiza Libro1.xlsx para entender la estructura de proyecciones
"""
import pandas as pd

# Leer proyecciones
df = pd.read_excel('../inputs/Libro1.xlsx')

print("=" * 80)
print("ANÁLISIS DE PROYECCIONES (Libro1.xlsx)")
print("=" * 80)

# Columnas relevantes
print("\n📋 COLUMNAS DISPONIBLES:")
for col in df.columns:
    print(f"  • {col}")

# Renombrar para facilitar acceso
df_renamed = df.rename(columns={
    'ASIGNATURA': 'curso',
    'PRESENCIAL (PRS)/ NO PRESENCIAL (NPR)': 'modalidad',
    'N° Grupos Teoría': 'grupos_teoria',
    'N° Grupos Práctica': 'grupos_practica',
    'N° Grupos Laboratorio': 'grupos_laboratorio',
    'N° alumnos para Teoría': 'alumnos_teoria',
    'N° alumnos para Práctica': 'alumnos_practica',
    'N° alumnos para Laboratorio': 'alumnos_laboratorio'
})

# Limpiar datos
df_clean = df_renamed[df_renamed['curso'].notna()].copy()

print("\n" + "=" * 80)
print("📊 CURSOS POR MODALIDAD:")
print("=" * 80)
print(df_clean['modalidad'].value_counts())

print("\n" + "=" * 80)
print("🎓 EJEMPLOS DE PROYECCIONES (primeros 15 cursos):")
print("=" * 80)

for idx, row in df_clean.head(15).iterrows():
    curso = row['curso']
    modalidad = row['modalidad']
    gt = int(row['grupos_teoria']) if pd.notna(row['grupos_teoria']) else 0
    gp = int(row['grupos_practica']) if pd.notna(row['grupos_practica']) else 0
    gl = int(row['grupos_laboratorio']) if pd.notna(row['grupos_laboratorio']) else 0
    
    print(f"\n📚 {curso[:50]}")
    print(f"   Modalidad: {modalidad}")
    print(f"   Grupos T: {gt}, P: {gp}, L: {gl}")
    
    if gt > 0:
        print(f"   💡 LIGAS A GENERAR: {gt}")
        print(f"   📌 Estructura por liga:")
        if gt > 0 and gp > 0:
            practicas_por_liga = gp // gt if gt > 0 else 0
            print(f"      • Cada liga tiene: 1 T + {practicas_por_liga} P", end="")
        if gt > 0 and gl > 0:
            labs_por_liga = gl // gt if gt > 0 else 0
            print(f" + {labs_por_liga} L" if gp > 0 else f"      • Cada liga tiene: 1 T + {labs_por_liga} L")
        print()

print("\n" + "=" * 80)
print("📊 ESTADÍSTICAS DE LIGAS:")
print("=" * 80)

ligas_stats = {}
for idx, row in df_clean.iterrows():
    gt = int(row['grupos_teoria']) if pd.notna(row['grupos_teoria']) else 0
    if gt > 0:
        if gt not in ligas_stats:
            ligas_stats[gt] = 0
        ligas_stats[gt] += 1

for num_ligas, count in sorted(ligas_stats.items()):
    print(f"  • {num_ligas} liga(s): {count} cursos")

print("\n" + "=" * 80)
print("🔍 CURSOS NPR (NO PRESENCIALES):")
print("=" * 80)

cursos_npr = df_clean[df_clean['modalidad'] == 'NPR']
print(f"\nTotal: {len(cursos_npr)} cursos\n")
for idx, row in cursos_npr.iterrows():
    curso = row['curso']
    gt = int(row['grupos_teoria']) if pd.notna(row['grupos_teoria']) else 0
    print(f"  • {curso[:50]} (Teorías: {gt})")

print("\n" + "=" * 80)
print("🧪 CURSOS ESPECIALES (TESIS/PROYECTOS):")
print("=" * 80)

cursos_especiales = ['PROYECTO', 'TESIS']
for keyword in cursos_especiales:
    matching = df_clean[df_clean['curso'].str.contains(keyword, case=False, na=False)]
    if len(matching) > 0:
        print(f"\n🔬 Cursos con '{keyword}':")
        for idx, row in matching.iterrows():
            print(f"  • {row['curso']}")
            print(f"    Modalidad: {row['modalidad']}, T:{int(row['grupos_teoria']) if pd.notna(row['grupos_teoria']) else 0}, P:{int(row['grupos_practica']) if pd.notna(row['grupos_practica']) else 0}, L:{int(row['grupos_laboratorio']) if pd.notna(row['grupos_laboratorio']) else 0}")
