"""
Script para verificar todas las tablas relacionadas con profesores y cursos
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from sqlalchemy import text
from app.database import SessionLocal

def main():
    db = SessionLocal()
    
    try:
        print("="*80)
        print("VERIFICACIÓN DE TABLAS DE PROFESORES Y CURSOS")
        print("="*80)
        
        # 1. professor_courses
        print("\n1. TABLA: professor_courses")
        print("-" * 80)
        result = db.execute(text("SELECT COUNT(*) as count FROM professor_courses")).fetchone()
        print(f"Registros: {result[0]}")
        
        if result[0] > 0:
            print("\nPrimeras 5 filas:")
            result = db.execute(text("""
                SELECT pc.professor_id, p.nombre_completo, pc.course_id, c.codigo, c.nombre
                FROM professor_courses pc
                JOIN professors p ON pc.professor_id = p.id
                JOIN courses c ON pc.course_id = c.id
                LIMIT 5
            """))
            for row in result:
                print(f"  Prof {row[0]} ({row[1][:30]}) -> Curso {row[2]} ({row[3]})")
        
        # 2. professor_course_assignments
        print("\n2. TABLA: professor_course_assignments")
        print("-" * 80)
        result = db.execute(text("DESCRIBE professor_course_assignments"))
        print("Estructura:")
        for row in result:
            print(f"  {row[0]}: {row[1]}")
        
        result = db.execute(text("SELECT COUNT(*) as count FROM professor_course_assignments")).fetchone()
        print(f"\nRegistros: {result[0]}")
        
        if result[0] > 0:
            print("\nPrimeras 10 filas:")
            result = db.execute(text("""
                SELECT * FROM professor_course_assignments LIMIT 10
            """))
            for row in result:
                print(f"  {row}")
        
        # 3. professor_course_history
        print("\n3. TABLA: professor_course_history")
        print("-" * 80)
        result = db.execute(text("DESCRIBE professor_course_history"))
        print("Estructura:")
        for row in result:
            print(f"  {row[0]}: {row[1]}")
        
        result = db.execute(text("SELECT COUNT(*) as count FROM professor_course_history")).fetchone()
        print(f"\nRegistros: {result[0]}")
        
        if result[0] > 0:
            print("\nPrimeras 5 filas:")
            result = db.execute(text("""
                SELECT * FROM professor_course_history LIMIT 5
            """))
            for row in result:
                print(f"  {row}")
        
        # 4. Verificar si professor_course_assignments tiene datos útiles
        print("\n" + "="*80)
        print("ANÁLISIS DE professor_course_assignments")
        print("="*80)
        
        result = db.execute(text("SELECT COUNT(*) FROM professor_course_assignments")).fetchone()
        if result[0] > 0:
            # Ver qué columnas relacionan profesor con curso
            result = db.execute(text("""
                SELECT * FROM professor_course_assignments LIMIT 1
            """))
            first_row = result.fetchone()
            if first_row:
                print(f"\nEjemplo de registro:")
                print(f"  Columnas: {result.keys()}")
                print(f"  Valores: {first_row}")
                
            # Contar profesores únicos
            result = db.execute(text("""
                SELECT COUNT(DISTINCT professor_id) as count 
                FROM professor_course_assignments
            """))
            print(f"\nProfesores únicos: {result.fetchone()[0]}")
            
            # Contar cursos únicos (si existe course_id)
            try:
                result = db.execute(text("""
                    SELECT COUNT(DISTINCT course_id) as count 
                    FROM professor_course_assignments
                """))
                print(f"Cursos únicos: {result.fetchone()[0]}")
            except:
                print("No hay columna course_id")
        
        # 5. Verificar secciones y sus profesores asignados
        print("\n" + "="*80)
        print("SECCIONES Y SUS PROFESORES")
        print("="*80)
        
        result = db.execute(text("""
            SELECT 
                cs.id as section_id,
                c.codigo,
                c.nombre,
                cs.tipo,
                cs.league,
                COUNT(DISTINCT p.id) as n_profesores
            FROM course_sections cs
            JOIN courses c ON cs.course_id = c.id
            LEFT JOIN professor_courses pc ON c.id = pc.course_id
            LEFT JOIN professors p ON pc.professor_id = p.id
            WHERE cs.activa = true
            GROUP BY cs.id, c.codigo, c.nombre, cs.tipo, cs.league
            HAVING n_profesores = 0
            LIMIT 10
        """))
        
        no_prof_sections = list(result)
        if no_prof_sections:
            print(f"\n⚠ {len(no_prof_sections)} secciones SIN profesores asignados:")
            for row in no_prof_sections:
                print(f"  Sección {row[0]}: {row[1]} - {row[2][:40]} ({row[3]}, Liga {row[4]})")
        else:
            print("\n✓ Todas las secciones tienen profesores asignados")
        
    finally:
        db.close()

if __name__ == "__main__":
    main()
