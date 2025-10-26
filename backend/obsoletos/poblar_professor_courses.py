"""
Script para poblar la tabla professor_courses con asignaciones realistas
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Course, Professor, professor_course_table
from sqlalchemy import text

def main():
    db = SessionLocal()
    
    try:
        print("="*80)
        print("POBLANDO TABLA PROFESSOR_COURSES")
        print("="*80)
        
        # 1. Verificar estado actual
        result = db.execute(text("SELECT COUNT(*) as count FROM professor_courses")).fetchone()
        print(f"\nRegistros actuales en professor_courses: {result[0]}")
        
        # 2. Obtener todos los cursos y profesores
        all_courses = db.query(Course).filter(Course.active == True).all()
        all_professors = db.query(Professor).filter(Professor.id != 353).all()  # Excluir placeholder
        
        print(f"\nCursos activos: {len(all_courses)}")
        print(f"Profesores disponibles (sin placeholder): {len(all_professors)}")
        
        if not all_professors:
            print("\n❌ ERROR: No hay profesores disponibles (todos son placeholder)")
            print("Necesitas crear profesores reales primero.")
            return
        
        # 3. Estrategia de asignación:
        # - Cada curso se asigna a 2-4 profesores aleatorios
        # - Cursos del mismo ciclo comparten algunos profesores
        
        print("\n" + "="*80)
        print("ASIGNANDO PROFESORES A CURSOS")
        print("="*80)
        
        import random
        random.seed(42)  # Para reproducibilidad
        
        assignments = []
        existing_assignments = set()
        
        # Obtener asignaciones existentes
        existing = db.execute(text("SELECT professor_id, course_id FROM professor_courses")).fetchall()
        existing_assignments = {(row[0], row[1]) for row in existing}
        
        print(f"\nAsignaciones existentes: {len(existing_assignments)}")
        
        # Agrupar cursos por ciclo
        courses_by_cycle = {}
        for course in all_courses:
            ciclo = course.ciclo or "NONE"
            if ciclo not in courses_by_cycle:
                courses_by_cycle[ciclo] = []
            courses_by_cycle[ciclo].append(course)
        
        total_new = 0
        
        for ciclo, courses in sorted(courses_by_cycle.items()):
            print(f"\n--- Ciclo {ciclo} ({len(courses)} cursos) ---")
            
            # Seleccionar un pool de profesores para este ciclo
            n_profs_for_cycle = min(len(all_professors), max(5, len(courses)))
            cycle_professors = random.sample(all_professors, n_profs_for_cycle)
            
            for course in courses:
                # Asignar 2-3 profesores por curso
                n_profs = random.randint(2, 3)
                course_professors = random.sample(cycle_professors, min(n_profs, len(cycle_professors)))
                
                new_for_course = 0
                for prof in course_professors:
                    if (prof.id, course.id) not in existing_assignments:
                        assignments.append({
                            'professor_id': prof.id,
                            'course_id': course.id
                        })
                        existing_assignments.add((prof.id, course.id))
                        new_for_course += 1
                
                if new_for_course > 0:
                    print(f"  {course.codigo} ({course.nombre[:40]}): +{new_for_course} profesores")
                    total_new += new_for_course
        
        if not assignments:
            print("\n✓ No hay nuevas asignaciones necesarias (tabla ya poblada)")
            return
        
        # 4. Insertar en la base de datos
        print(f"\n" + "="*80)
        print(f"INSERTANDO {len(assignments)} NUEVAS ASIGNACIONES")
        print("="*80)
        
        # Insertar en lotes
        batch_size = 100
        for i in range(0, len(assignments), batch_size):
            batch = assignments[i:i+batch_size]
            db.execute(professor_course_table.insert(), batch)
            print(f"  Insertados {min(i+batch_size, len(assignments))}/{len(assignments)}...")
        
        db.commit()
        print(f"\n✓ {len(assignments)} asignaciones insertadas exitosamente")
        
        # 5. Verificar cursos específicos problemáticos
        print("\n" + "="*80)
        print("VERIFICANDO CURSOS PROBLEMÁTICOS")
        print("="*80)
        
        problematic_codes = ['CIEN754', 'CIEN768', 'ADMI779', 'ICSI509']
        
        for code in problematic_codes:
            course = db.query(Course).filter(Course.codigo == code).first()
            if not course:
                print(f"\n{code}: ❌ No encontrado")
                continue
            
            # Contar profesores asignados
            count = db.execute(text(
                "SELECT COUNT(*) FROM professor_courses WHERE course_id = :course_id"
            ), {"course_id": course.id}).scalar()
            
            if count == 0:
                print(f"\n{code}: ❌ SIN PROFESORES - Asignando ahora...")
                # Asignar 3 profesores random
                random_profs = random.sample(all_professors, min(3, len(all_professors)))
                for prof in random_profs:
                    db.execute(professor_course_table.insert().values(
                        professor_id=prof.id,
                        course_id=course.id
                    ))
                db.commit()
                print(f"  ✓ {len(random_profs)} profesores asignados")
            else:
                # Mostrar profesores
                profs = db.execute(text("""
                    SELECT p.codigo, p.nombre_completo
                    FROM professors p
                    JOIN professor_courses pc ON p.id = pc.professor_id
                    WHERE pc.course_id = :course_id
                """), {"course_id": course.id}).fetchall()
                
                print(f"\n{code}: ✓ {count} profesores asignados")
                for prof in profs:
                    print(f"  - {prof[0]}: {prof[1]}")
        
        # 6. Estadísticas finales
        print("\n" + "="*80)
        print("ESTADÍSTICAS FINALES")
        print("="*80)
        
        total_assignments = db.execute(text("SELECT COUNT(*) FROM professor_courses")).scalar()
        print(f"\nTotal asignaciones en professor_courses: {total_assignments}")
        
        # Cursos sin profesores
        courses_without_profs = db.execute(text("""
            SELECT COUNT(*)
            FROM courses c
            LEFT JOIN professor_courses pc ON c.id = pc.course_id
            WHERE c.active = true AND pc.professor_id IS NULL
        """)).scalar()
        
        print(f"Cursos activos sin profesores: {courses_without_profs}")
        
        if courses_without_profs > 0:
            print("\n⚠ Aún hay cursos sin profesores asignados")
        else:
            print("\n✓ Todos los cursos tienen al menos un profesor")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
