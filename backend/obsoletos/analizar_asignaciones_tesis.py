"""
Análisis de asignaciones de profesores para TESIS II (ISIA125)
"""

from app.database import get_db
from sqlalchemy import text

db = next(get_db())

print("=" * 100)
print("ANÁLISIS DE ASIGNACIONES: TESIS II (ISIA125)")
print("=" * 100)

# Consultar asignaciones en professor_course_assignments
query = text("""
    SELECT 
        pca.id,
        c.codigo as curso_codigo,
        c.nombre as curso_nombre,
        p.codigo as prof_codigo,
        p.nombre_completo as prof_nombre,
        pca.session_type as tipo,
        pca.league as liga_id
    FROM professor_course_assignments pca
    JOIN courses c ON pca.course_id = c.id
    JOIN professors p ON pca.professor_id = p.id
    WHERE c.codigo = 'ISIA125'
    ORDER BY pca.league, pca.session_type, p.codigo
""")

result = db.execute(query)
rows = list(result)

print(f"\n📊 Total de asignaciones en BD: {len(rows)}\n")

# Agrupar por liga
from collections import defaultdict
por_liga = defaultdict(list)

for r in rows:
    por_liga[r.liga_id].append(r)

# Mostrar por liga
for liga_id in sorted(por_liga.keys()):
    asignaciones = por_liga[liga_id]
    print(f"\n{'='*100}")
    print(f"🔹 LIGA {liga_id} - Total asignaciones: {len(asignaciones)}")
    print(f"{'='*100}")
    
    for a in asignaciones:
        print(f"  • Profesor: {a.prof_codigo:12} - {a.prof_nombre:40} | Tipo: {a.tipo:8}")

# Ahora consultar las secciones generadas
print(f"\n\n{'='*100}")
print("SECCIONES GENERADAS EN BD (course_sections)")
print(f"{'='*100}\n")

query_sections = text("""
    SELECT 
        cs.id,
        cs.seccion_codigo,
        c.codigo as curso_codigo,
        cs.tipo,
        cs.liga_id,
        cs.alumnos_proyectados
    FROM course_sections cs
    JOIN courses c ON cs.course_id = c.id
    WHERE c.codigo = 'ISIA125'
    ORDER BY cs.liga_id, cs.tipo, cs.seccion_codigo
""")

result_sections = db.execute(query_sections)
sections = list(result_sections)

print(f"📊 Total de secciones: {len(sections)}\n")

por_liga_sec = defaultdict(list)
for s in sections:
    por_liga_sec[s.liga_id].append(s)

for liga_id in sorted(por_liga_sec.keys()):
    secciones = por_liga_sec[liga_id]
    print(f"\n{'='*100}")
    print(f"🔹 LIGA {liga_id} - Total secciones: {len(secciones)}")
    print(f"{'='*100}")
    
    for s in secciones:
        print(f"  • Sección: {s.seccion_codigo:15} | Tipo: {s.tipo:8} | Alumnos: {s.alumnos_proyectados:3}")

# Ahora verificar qué pasó en el último horario generado
import glob
import json
from pathlib import Path

backend_dir = Path(__file__).parent
json_files = glob.glob(str(backend_dir / "horario_generado_*.json"))

if json_files:
    latest_json = max(json_files, key=lambda x: Path(x).stat().st_ctime)
    print(f"\n\n{'='*100}")
    print(f"ÚLTIMO HORARIO GENERADO: {Path(latest_json).name}")
    print(f"{'='*100}\n")
    
    with open(latest_json, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    asignaciones = data.get('asignaciones', data.get('assignments', []))
    
    # Filtrar TESIS II
    tesis_asignaciones = [a for a in asignaciones if a.get('codigo_curso') == 'ISIA125']
    
    print(f"📊 Total asignaciones de ISIA125 en horario: {len(tesis_asignaciones)}\n")
    
    # Agrupar por profesor
    por_profesor = defaultdict(list)
    for a in tesis_asignaciones:
        prof = a.get('profesor_codigo', 'DESCONOCIDO')
        por_profesor[prof].append(a)
    
    for prof in sorted(por_profesor.keys()):
        asigs = por_profesor[prof]
        print(f"\n{'='*100}")
        print(f"👨‍🏫 Profesor: {prof} - Total asignaciones: {len(asigs)}")
        print(f"{'='*100}")
        
        for a in asigs:
            seccion = a.get('seccion', 'N/A')
            tipo = a.get('tipo', 'N/A')
            liga = a.get('liga_id', 'N/A')
            print(f"  • Sección: {seccion:15} | Tipo: {tipo:8} | Liga: {liga}")

print("\n\n" + "=" * 100)
print("ANÁLISIS CRÍTICO")
print("=" * 100)
print("""
PROBLEMA IDENTIFICADO:
- El sistema está asignando profesores sin respetar las ligas correctamente
- Un profesor asignado a ligas 1, 3, 4 solo aparece en liga 3
- Otro profesor asignado solo a liga 2 aparece en múltiples secciones

CAUSA PROBABLE:
- El grafo no está filtrando candidatos por liga correctamente
- O la lógica de selección no considera la liga al elegir el profesor
""")
