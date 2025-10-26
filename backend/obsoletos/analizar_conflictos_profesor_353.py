"""
Análisis profundo de conflictos del profesor 353 (PLACEHOLDER)
y estrategia de resolución
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models import CourseSection, Course, Professor, Classroom, TimeSlot
from collections import defaultdict

def main():
    db = SessionLocal()
    
    try:
        print("="*80)
        print("ANÁLISIS DE CONFLICTOS - PROFESOR 353 (PLACEHOLDER)")
        print("="*80)
        
        # 1. Identificar todas las secciones asignadas al profesor 353
        print("\n1. SECCIONES ASIGNADAS AL PROFESOR 353:")
        print("-" * 80)
        
        sections_353 = (
            db.query(CourseSection)
            .join(Course)
            .filter(CourseSection.activa == True)
            .all()
        )
        
        # Filtrar las que tienen candidatos que incluyen profesor 353
        sections_with_353 = []
        for section in sections_353:
            # Buscar profesores del curso
            professors = db.query(Professor).join(Professor.courses).filter(Course.id == section.course_id).all()
            prof_ids = [p.id for p in professors]
            if 353 in prof_ids:
                sections_with_353.append(section)
        
        print(f"Total de secciones con profesor 353 disponible: {len(sections_with_353)}")
        
        # Agrupar por curso y liga
        by_course_league = defaultdict(list)
        for section in sections_with_353:
            key = (section.course.codigo, section.course.nombre, section.league, section.course.ciclo)
            by_course_league[key].append(section)
        
        print(f"\nAgrupación por curso/liga:")
        for (codigo, nombre, league, ciclo), secs in sorted(by_course_league.items()):
            print(f"\n  {codigo} - {nombre[:50]}")
            print(f"    Ciclo: {ciclo}, Liga: {league}")
            print(f"    Secciones ({len(secs)}):")
            for sec in secs:
                print(f"      - ID {sec.id}: {sec.tipo}, {sec.alumnos_proyectados} alumnos")
        
        # 2. Analizar secciones problemáticas específicas
        print("\n" + "="*80)
        print("2. ANÁLISIS DE SECCIONES PROBLEMÁTICAS")
        print("="*80)
        
        problematic_ids = [1572, 1573, 1576, 1593, 1595, 1602]
        print(f"\nAnalizando secciones: {problematic_ids}")
        
        for sec_id in problematic_ids:
            section = db.query(CourseSection).filter(CourseSection.id == sec_id).first()
            if not section:
                continue
                
            course = section.course
            print(f"\n--- Sección {sec_id} ---")
            print(f"  Curso: {course.codigo} - {course.nombre}")
            print(f"  Ciclo: {course.ciclo}, Liga: {section.league}, Tipo: {section.tipo}")
            print(f"  Alumnos proyectados: {section.alumnos_proyectados}")
            
            # Profesores disponibles
            professors = db.query(Professor).join(Professor.courses).filter(Course.id == course.id).all()
            print(f"  Profesores disponibles ({len(professors)}):")
            for prof in professors:
                print(f"    - ID {prof.id}: {prof.nombre_completo} ({prof.codigo})")
        
        # 3. Estrategia de resolución
        print("\n" + "="*80)
        print("3. ESTRATEGIA DE RESOLUCIÓN")
        print("="*80)
        
        print("\nOPCIÓN A: ASIGNAR PROFESORES REALES")
        print("-" * 40)
        print("Identificar qué secciones pueden tener profesores reales:")
        
        for (codigo, nombre, league, ciclo), secs in sorted(by_course_league.items()):
            if not secs:
                continue
            
            # Buscar profesores del curso
            course_id = secs[0].course_id
            professors = db.query(Professor).join(Professor.courses).filter(Course.id == course_id).all()
            real_profs = [p for p in professors if p.id != 353]
            
            if real_profs:
                print(f"\n  {codigo} (Liga {league}, Ciclo {ciclo}):")
                print(f"    Profesores reales disponibles: {len(real_profs)}")
                for prof in real_profs:
                    print(f"      - {prof.nombre_completo}")
                print(f"    Secciones que necesitan asignación: {len(secs)}")
                if len(real_profs) >= len(secs):
                    print(f"    ✓ SUFICIENTES profesores para todas las secciones")
                else:
                    print(f"    ⚠ FALTAN {len(secs) - len(real_profs)} profesores")
        
        print("\n\nOPCIÓN B: REORDENAR CONSTRUCCIÓN DE SOLUCIÓN")
        print("-" * 40)
        print("Construir en orden estratégico para evitar deadlocks:")
        print("  1. Ordenar secciones por restricciones (menos candidatos primero)")
        print("  2. Para secciones de misma liga, construir secuencialmente")
        print("  3. Reservar recursos por liga antes de asignar")
        
        # 4. Calcular estadísticas de disponibilidad
        print("\n" + "="*80)
        print("4. ESTADÍSTICAS DE DISPONIBILIDAD")
        print("="*80)
        
        all_classrooms = db.query(Classroom).filter(Classroom.active == True).all()
        all_timeslots = db.query(TimeSlot).all()
        
        print(f"\nRecursos totales:")
        print(f"  Profesores: {len(db.query(Professor).all())}")
        print(f"  Profesores reales (sin placeholder): {len(db.query(Professor).filter(Professor.id != 353).all())}")
        print(f"  Aulas activas: {len(all_classrooms)}")
        print(f"    - Laboratorios: {len([c for c in all_classrooms if c.tipo == 'laboratorio'])}")
        print(f"    - Aulas normales: {len([c for c in all_classrooms if c.tipo != 'laboratorio'])}")
        print(f"  Franjas horarias: {len(all_timeslots)}")
        
        print("\n" + "="*80)
        print("RECOMENDACIONES:")
        print("="*80)
        print("""
1. INMEDIATO: Verificar si existen profesores reales asignados a CIEN754
   - Si existen, actualizar la BD para vincularlos correctamente
   - Si no existen, crear profesores placeholder por liga

2. CORTO PLAZO: Implementar orden de construcción por disponibilidad
   - Ordenar por: n_profesores * n_aulas * n_timeslots (ascendente)
   - Construir secciones más restringidas primero

3. MEDIANO PLAZO: Implementar reserva de recursos por liga
   - Antes de asignar, reservar timeslots para toda la liga
   - Garantizar no-solapamiento entre secciones de misma liga
        """)
        
    finally:
        db.close()

if __name__ == "__main__":
    main()
