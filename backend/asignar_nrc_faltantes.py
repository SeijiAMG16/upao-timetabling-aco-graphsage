"""
Script para asignar NRCs a las secciones que no los tienen
"""

from app.database import SessionLocal
from sqlalchemy import text

def main():
    print("=" * 80)
    print("ASIGNACION DE NRCs FALTANTES")
    print("=" * 80)
    
    db = SessionLocal()
    
    try:
        # Identificar secciones sin NRC
        print("\n[1/3] Identificando secciones sin NRC...")
        result = db.execute(text("""
            SELECT id, course_id, tipo, seccion, league
            FROM course_sections
            WHERE active = 1 AND nrc IS NULL
            ORDER BY course_id, tipo, league
        """))
        
        sections_without_nrc = list(result)
        print(f"  Secciones sin NRC: {len(sections_without_nrc)}")
        
        if not sections_without_nrc:
            print("\n[OK] Todas las secciones tienen NRC")
            return
        
        # Obtener el próximo NRC disponible
        result = db.execute(text("""
            SELECT COALESCE(MAX(CAST(nrc AS UNSIGNED)), 2000) + 1
            FROM course_sections
            WHERE nrc IS NOT NULL AND nrc REGEXP '^[0-9]+$'
        """))
        next_nrc = result.fetchone()[0]
        print(f"  Próximo NRC disponible: {next_nrc}")
        
        # Asignar NRCs
        print("\n[2/3] Asignando NRCs...")
        for idx, (sec_id, course_id, tipo, seccion, league) in enumerate(sections_without_nrc):
            new_nrc = str(next_nrc + idx)
            db.execute(text("""
                UPDATE course_sections
                SET nrc = :nrc
                WHERE id = :id
            """), {"nrc": new_nrc, "id": sec_id})
            print(f"  CourseID {course_id}, {tipo}, {seccion}, Liga {league} -> NRC {new_nrc}")
        
        db.commit()
        print("  [OK] NRCs asignados")
        
        # Verificar
        print("\n[3/3] Verificación final...")
        result = db.execute(text("""
            SELECT COUNT(*)
            FROM course_sections
            WHERE active = 1 AND nrc IS NULL
        """))
        remaining = result.fetchone()[0]
        print(f"  Secciones sin NRC: {remaining}")
        
        print("\n" + "=" * 80)
        print(f"RESUMEN: {len(sections_without_nrc)} NRCs asignados correctamente")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
