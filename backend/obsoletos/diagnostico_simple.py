"""
DIAGNÓSTICO SUPER SIMPLE
"""
import sys
sys.path.insert(0, r'c:\Users\amaya\Downloads\10mo Ciclo\TESIS\upao-timetabling-aco-graphsage\backend')

from app.database import SessionLocal
from app.models import CourseSection, Course, Classroom

db = SessionLocal()

print("="*80)
print("DIAGNÓSTICO CRÍTICO - SECCIONES 1800, 1810, 1811")
print("="*80)

for sec_id in [1800, 1810, 1811]:
    sec = db.query(CourseSection).filter_by(id=sec_id).first()
    if not sec:
        print(f"\n❌ Sección {sec_id} NO EXISTE")
        continue
    
    curso = sec.course
    
    print(f"\n{'='*80}")
    print(f"SECCIÓN {sec_id}: {sec.codigo_completo}")
    print(f"{'='*80}")
    print(f"  📚 Curso: {curso.codigo} - {curso.nombre}")
    print(f"  📋 Tipo: {sec.tipo}")
    print(f"  📊 Seccion: {sec.seccion}")
    print(f"  📊 Liga: {sec.league}")
    print(f"  👥 Estudiantes proyectados: {sec.alumnos_proyectados}")
    print(f"  👥 Estudiantes reales: {sec.alumnos_reales}")
    print(f"  🏢 Modalidad curso: {curso.modalidad}")
    print(f"  🧪 Requiere Lab: {'Sí' if curso.requiere_laboratorio else 'No'}")
    
    # Ver aulas disponibles
    max_cap = db.query(Classroom.capacidad).filter_by(active=True).order_by(Classroom.capacidad.desc()).first()
    aulas_ok = db.query(Classroom).filter(
        Classroom.active == True,
        Classroom.capacidad >= sec.alumnos_proyectados
    ).count()
    
    print(f"\n  🏫 Aula más grande: {max_cap[0] if max_cap else 0} estudiantes")
    print(f"  🏫 Aulas con capacidad suficiente: {aulas_ok}")
    
    if max_cap and sec.alumnos_proyectados > max_cap[0]:
        print(f"\n  ❌ PROBLEMA CRÍTICO: {sec.alumnos_proyectados} estudiantes > {max_cap[0]} capacidad máxima")
        print(f"     DIFERENCIA: {sec.alumnos_proyectados - max_cap[0]} estudiantes SIN AULA POSIBLE")

# Ver hermanos de liga
print(f"\n{'='*80}")
print("HERMANOS DE LIGA")
print(f"{'='*80}")

for sec_id in [1800, 1810, 1811]:
    sec = db.query(CourseSection).filter_by(id=sec_id).first()
    if sec and sec.league:
        hermanos = db.query(CourseSection).filter(
            CourseSection.league == sec.league,
            CourseSection.id != sec_id
        ).all()
        if hermanos:
            print(f"\nLiga {sec.league} (Sección {sec_id} - {sec.codigo_completo}):")
            for h in hermanos:
                print(f"  - Sección {h.id} ({h.codigo_completo}): {h.tipo}, Est: {h.alumnos_proyectados}")

db.close()
print(f"\n{'='*80}")
