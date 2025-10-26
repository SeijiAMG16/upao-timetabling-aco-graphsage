"""
DIAGNÓSTICO CRÍTICO DE SECCIONES PROBLEMÁTICAS
"""
import sys
sys.path.insert(0, r'c:\Users\amaya\Downloads\10mo Ciclo\TESIS\upao-timetabling-aco-graphsage\backend')

from app.database import SessionLocal
from app.models import Section, Course, Professor
from sqlalchemy import text

db = SessionLocal()

print("="*80)
print("DIAGNÓSTICO CRÍTICO - SECCIONES 1800, 1810, 1811")
print("="*80)

secciones_problema = [1800, 1810, 1811]

for sec_id in secciones_problema:
    sec = db.query(Section).filter_by(id=sec_id).first()
    if not sec:
        print(f"\n❌ Sección {sec_id} NO EXISTE en la BD")
        continue
    
    curso = db.query(Course).filter_by(id=sec.course_id).first()
    prof = db.query(Professor).filter_by(id=sec.professor_id).first() if sec.professor_id else None
    
    print(f"\n{'='*80}")
    print(f"SECCIÓN {sec_id}: {sec.codigo}")
    print(f"{'='*80}")
    print(f"  📚 Curso: {curso.codigo if curso else 'N/A'} - {curso.nombre if curso else 'N/A'}")
    print(f"  📋 Tipo: {sec.tipo}")
    print(f"  ⏱️  Horas/semana: {sec.horas_semana}")
    print(f"  👥 Estudiantes: {sec.num_estudiantes}")
    print(f"  👨‍🏫 Profesor: {prof.nombre if prof else 'SIN ASIGNAR'} (ID: {sec.professor_id})")
    print(f"  🏢 Modalidad: {curso.modalidad if curso else 'N/A'}")
    print(f"  🧪 Requiere Lab: {curso.requiere_laboratorio if curso else 'N/A'}")
    print(f"  📊 Liga ID: {sec.league_id}")
    
    # Buscar hermanos de liga
    if sec.league_id:
        hermanos = db.query(Section).filter(
            Section.league_id == sec.league_id,
            Section.id != sec_id
        ).all()
        if hermanos:
            print(f"\n  🔗 Hermanos de liga ({len(hermanos)}):")
            for h in hermanos:
                print(f"      - Sección {h.id} ({h.codigo}): {h.tipo}, Prof: {h.professor_id}")
    
    # Verificar si tiene profesor
    if not sec.professor_id:
        print(f"\n  ⚠️  PROBLEMA: SECCIÓN SIN PROFESOR ASIGNADO")
    
    # Verificar modalidad virtual
    if curso and curso.modalidad and curso.modalidad.upper() == 'NO_PRESENCIAL':
        print(f"  ✅ Curso VIRTUAL - No necesita aula física")
    
    # Verificar capacidad de aula necesaria
    if sec.num_estudiantes:
        print(f"\n  📏 Capacidad mínima de aula: {sec.num_estudiantes} estudiantes")
        
        # Buscar aulas disponibles
        query = text("""
            SELECT COUNT(*) as total, 
                   COUNT(CASE WHEN tipo = 'LAB' THEN 1 END) as labs,
                   COUNT(CASE WHEN tipo = 'NOLAB' THEN 1 END) as nolabs
            FROM classrooms 
            WHERE capacidad >= :capacidad AND active = 1
        """)
        result = db.execute(query, {"capacidad": sec.num_estudiantes}).first()
        print(f"  🏫 Aulas con capacidad suficiente: {result.total} ({result.labs} LAB + {result.nolabs} NOLAB)")
        
        if result.total == 0:
            print(f"  ❌ CRÍTICO: NO HAY AULAS CON CAPACIDAD SUFICIENTE!")

print("\n" + "="*80)
print("RESUMEN DE PROBLEMAS")
print("="*80)

# Verificar si hay conflictos de profesor
for sec_id in secciones_problema:
    sec = db.query(Section).filter_by(id=sec_id).first()
    if sec and sec.professor_id:
        # Contar cuántas secciones tiene este profesor
        count = db.query(Section).filter_by(professor_id=sec.professor_id).count()
        if count > 10:
            print(f"⚠️  Sección {sec_id}: Profesor {sec.professor_id} tiene {count} secciones asignadas")

# Verificar capacidades extremas
query = text("""
    SELECT s.id, s.codigo, s.num_estudiantes, c.nombre as curso,
           (SELECT MAX(capacidad) FROM classrooms WHERE active=1) as max_aula
    FROM course_sections s
    JOIN courses c ON s.course_id = c.id
    WHERE s.id IN (1800, 1810, 1811)
    AND s.num_estudiantes > (SELECT MAX(capacidad) FROM classrooms WHERE active=1)
""")
over_capacity = db.execute(query).fetchall()
if over_capacity:
    print(f"\n❌ PROBLEMA CRÍTICO: Secciones con más estudiantes que la mayor aula:")
    for row in over_capacity:
        print(f"   - Sección {row.id} ({row.codigo}): {row.num_estudiantes} estudiantes vs {row.max_aula} capacidad máxima")

db.close()
print("\n" + "="*80)
