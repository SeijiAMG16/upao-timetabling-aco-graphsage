#!/usr/bin/env python3
"""
Analizar por qué las hormigas exitosas fallan en 1814 a pesar de tener recursos.
"""

from app.database import SessionLocal
from app.models import CourseSection, Classroom, Course

def main():
    session = SessionLocal()
    
    print("=" * 80)
    print("ANÁLISIS DEL PATRÓN DE FALLO")
    print("=" * 80)
    print()
    
    # Secciones en la cadena exitosa
    secuencia = [1810, 1811, 1812, 1813, 1814]
    
    print("SECUENCIA DE SECCIONES:")
    print()
    
    for sec_id in secuencia:
        sec = session.query(CourseSection).filter_by(id=sec_id).first()
        curso = sec.course
        
        print(f"Sección {sec_id}: {sec.codigo_completo}")
        print(f"  Tipo: {sec.tipo}")
        print(f"  Estudiantes: {sec.alumnos_proyectados}")
        print(f"  League: {sec.league}")
        print(f"  Modalidad: {curso.modalidad}")
        print(f"  Curso código: {curso.codigo}")
        print()
    
    print("=" * 80)
    print("ANÁLISIS DE LEAGUES")
    print("=" * 80)
    print()
    
    # Verificar si hay conflictos de league
    leagues = {}
    for sec_id in secuencia:
        sec = session.query(CourseSection).filter_by(id=sec_id).first()
        league = sec.league
        if league not in leagues:
            leagues[league] = []
        leagues[league].append(f"{sec_id} ({sec.codigo_completo})")
    
    for league, secciones in leagues.items():
        print(f"League {league}:")
        for s in secciones:
            print(f"  - {s}")
        print()
    
    print("=" * 80)
    print("ANÁLISIS DE MODALIDADES")
    print("=" * 80)
    print()
    
    # Contar por modalidad
    modalidades = {}
    for sec_id in secuencia:
        sec = session.query(CourseSection).filter_by(id=sec_id).first()
        curso = sec.course
        mod = curso.modalidad
        if mod not in modalidades:
            modalidades[mod] = []
        modalidades[mod].append(f"{sec_id} ({sec.codigo_completo})")
    
    for mod, secciones in modalidades.items():
        print(f"Modalidad {mod}: {len(secciones)} secciones")
        for s in secciones:
            print(f"  - {s}")
        print()
    
    print("=" * 80)
    print("HIPÓTESIS DEL PROBLEMA")
    print("=" * 80)
    print()
    
    # Las hormigas exitosas asignan: 1810 (PRACTICA) → 1811 (LAB) → 1812 (PRACTICA) → 1813 (LAB)
    # Luego fallan en: 1814 (PRACTICA)
    
    print("OBSERVACIONES:")
    print("1. Todas las secciones 1810-1814 están en la misma league (1)")
    print("2. Todas son NO_PRESENCIAL (virtuales)")
    print("3. Pattern: P1 → L1 → P1 → L1 → P1")
    print("4. Cursos: ISIA127 → ISIA127 → ISIA128 → ISIA128 → ISIA129")
    print()
    print("POSIBLES CAUSAS:")
    print("a) Restricción de cohesión de bloques (secciones de la misma league)")
    print("b) Profesor compartido entre secciones consume todos los slots")
    print("c) Restricción de secuencia pedagógica (PRACTICA debe ir antes/después de LAB)")
    print("d) Recursos agotados (aulas NOLAB/LAB) después de asignar 1810-1813")
    print()
    
    # Verificar profesores
    print("=" * 80)
    print("ANÁLISIS DE PROFESORES")
    print("=" * 80)
    print()
    
    for sec_id in secuencia:
        sec = session.query(CourseSection).filter_by(id=sec_id).first()
        # Intentar obtener profesor asignado
        print(f"Sección {sec_id} ({sec.codigo_completo}):")
        print(f"  NRC: {sec.nrc}")
        # El profesor puede estar en otra tabla, por ahora solo mostramos NRC
        print()
    
    session.close()

if __name__ == "__main__":
    main()
