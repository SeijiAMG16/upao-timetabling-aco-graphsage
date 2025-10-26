"""
DIAGNÓSTICO CRÍTICO RÁPIDO - SQL DIRECTO
"""
import sys
sys.path.insert(0, r'c:\Users\amaya\Downloads\10mo Ciclo\TESIS\upao-timetabling-aco-graphsage\backend')

from app.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

print("="*80)
print("DIAGNÓSTICO CRÍTICO - SECCIONES 1800, 1810, 1811")
print("="*80)

query = text("""
    SELECT 
        s.id,
        s.codigo,
        s.tipo,
        s.horas_semana,
        s.num_estudiantes,
        s.professor_id,
        s.league_id,
        c.codigo as curso_codigo,
        c.nombre as curso_nombre,
        c.modalidad,
        c.requiere_laboratorio,
        p.nombre as profesor_nombre,
        (SELECT MAX(capacidad) FROM classrooms WHERE active=1) as max_aula_capacidad,
        (SELECT COUNT(*) FROM classrooms WHERE active=1 AND capacidad >= s.num_estudiantes) as aulas_suficientes
    FROM course_sections s
    JOIN courses c ON s.course_id = c.id
    LEFT JOIN professors p ON s.professor_id = p.id
    WHERE s.id IN (1800, 1810, 1811)
    ORDER BY s.id
""")

result = db.execute(query).fetchall()

for row in result:
    print(f"\n{'='*80}")
    print(f"SECCIÓN {row.id}: {row.codigo}")
    print(f"{'='*80}")
    print(f"  📚 Curso: {row.curso_codigo} - {row.curso_nombre}")
    print(f"  📋 Tipo: {row.tipo}")
    print(f"  ⏱️  Horas/semana: {row.horas_semana}")
    print(f"  👥 Estudiantes: {row.num_estudiantes}")
    print(f"  👨‍🏫 Profesor: {row.profesor_nombre if row.profesor_nombre else 'SIN ASIGNAR'} (ID: {row.professor_id})")
    print(f"  🏢 Modalidad: {row.modalidad}")
    print(f"  🧪 Requiere Lab: {'Sí' if row.requiere_laboratorio else 'No'}")
    print(f"  📊 Liga ID: {row.league_id}")
    print(f"\n  🏫 Aula más grande: {row.max_aula_capacidad} estudiantes")
    print(f"  🏫 Aulas con capacidad suficiente: {row.aulas_suficientes}")
    
    if row.num_estudiantes > row.max_aula_capacidad:
        print(f"\n  ❌ PROBLEMA CRÍTICO: {row.num_estudiantes} estudiantes > {row.max_aula_capacidad} capacidad máxima")
        print(f"     ¡NO HAY NINGUNA AULA CON CAPACIDAD SUFICIENTE!")
    
    if not row.professor_id:
        print(f"\n  ⚠️  PROBLEMA: SECCIÓN SIN PROFESOR ASIGNADO")

# Buscar hermanos de liga
print(f"\n{'='*80}")
print("HERMANOS DE LIGA")
print(f"{'='*80}")

for row in result:
    if row.league_id:
        query_hermanos = text("""
            SELECT id, codigo, tipo, professor_id, num_estudiantes
            FROM course_sections
            WHERE league_id = :league_id AND id != :sec_id
            ORDER BY id
        """)
        hermanos = db.execute(query_hermanos, {"league_id": row.league_id, "sec_id": row.id}).fetchall()
        if hermanos:
            print(f"\nLiga {row.league_id} (Sección {row.id}):")
            for h in hermanos:
                print(f"  - Sección {h.id} ({h.codigo}): {h.tipo}, Prof: {h.professor_id}, Est: {h.num_estudiantes}")

# Ver todas las secciones que exceden capacidad
print(f"\n{'='*80}")
print("RESUMEN DE PROBLEMAS CRÍTICOS")
print(f"{'='*80}")

query_over = text("""
    SELECT s.id, s.codigo, s.num_estudiantes,
           (SELECT MAX(capacidad) FROM classrooms WHERE active=1) as max_cap
    FROM course_sections s
    WHERE s.num_estudiantes > (SELECT MAX(capacidad) FROM classrooms WHERE active=1)
    AND s.id IN (1800, 1810, 1811)
""")
over_capacity = db.execute(query_over).fetchall()

if over_capacity:
    print("\n❌ Secciones con MÁS estudiantes que la mayor aula:")
    for row in over_capacity:
        print(f"   - Sección {row.id} ({row.codigo}): {row.num_estudiantes} estudiantes vs {row.max_cap} capacidad máxima")
        print(f"     DIFERENCIA: {row.num_estudiantes - row.max_cap} estudiantes SIN AULA")
else:
    print("\n✅ TODAS las secciones problemáticas tienen aulas con capacidad suficiente")

db.close()
print(f"\n{'='*80}")
