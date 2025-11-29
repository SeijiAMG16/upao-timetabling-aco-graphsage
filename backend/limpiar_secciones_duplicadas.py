"""
Script para limpiar secciones duplicadas en course_sections
Elimina las secciones con tipo 'T', 'P', 'L' (letras solas) que tienen NRC NULL
y son duplicadas de las secciones con tipo completo ('teoria', 'practica', 'laboratorio')
"""

from app.database import SessionLocal
from sqlalchemy import text

def main():
    print("=" * 80)
    print("LIMPIEZA DE SECCIONES DUPLICADAS")
    print("=" * 80)
    
    db = SessionLocal()
    
    try:
        # Verificar estado actual
        print("\n[1/4] Verificando secciones actuales...")
        result = db.execute(text("""
            SELECT tipo, COUNT(*) as cnt, SUM(CASE WHEN nrc IS NULL THEN 1 ELSE 0 END) as null_nrc
            FROM course_sections
            WHERE active = 1
            GROUP BY tipo
            ORDER BY tipo
        """))
        print("\nDistribución de secciones activas:")
        print(f"{'Tipo':<15} {'Total':<10} {'NRC NULL':<10}")
        print("-" * 35)
        for row in result:
            print(f"{row[0]:<15} {row[1]:<10} {row[2]:<10}")
        
        # Contar secciones a eliminar
        print("\n[2/4] Identificando secciones duplicadas a eliminar...")
        result = db.execute(text("""
            SELECT COUNT(*) 
            FROM course_sections
            WHERE active = 1
              AND tipo IN ('T', 'P', 'L')
              AND nrc IS NULL
        """))
        count_to_delete = result.fetchone()[0]
        print(f"  Secciones a eliminar: {count_to_delete}")
        
        if count_to_delete == 0:
            print("\n[OK] No hay secciones duplicadas para eliminar")
            return
        
        # Mostrar ejemplos
        print("\n[3/4] Ejemplos de secciones a eliminar:")
        result = db.execute(text("""
            SELECT course_id, tipo, seccion, league, nrc
            FROM course_sections
            WHERE active = 1
              AND tipo IN ('T', 'P', 'L')
              AND nrc IS NULL
            LIMIT 10
        """))
        print(f"{'CourseID':<10} {'Tipo':<10} {'Seccion':<10} {'Liga':<8} {'NRC':<10}")
        print("-" * 55)
        for row in result:
            print(f"{row[0]:<10} {row[1]:<10} {row[2]:<10} {row[3] or 'NULL':<8} {row[4] or 'NULL':<10}")
        
        # Eliminar secciones duplicadas
        print(f"\n[4/4] Eliminando {count_to_delete} secciones duplicadas...")
        db.execute(text("""
            DELETE FROM course_sections
            WHERE active = 1
              AND tipo IN ('T', 'P', 'L')
              AND nrc IS NULL
        """))
        db.commit()
        print("  [OK] Secciones eliminadas")
        
        # Verificar resultado
        print("\n[VERIFICACION] Estado final:")
        result = db.execute(text("""
            SELECT tipo, COUNT(*) as cnt, SUM(CASE WHEN nrc IS NULL THEN 1 ELSE 0 END) as null_nrc
            FROM course_sections
            WHERE active = 1
            GROUP BY tipo
            ORDER BY tipo
        """))
        print(f"{'Tipo':<15} {'Total':<10} {'NRC NULL':<10}")
        print("-" * 35)
        for row in result:
            print(f"{row[0]:<15} {row[1]:<10} {row[2]:<10}")
        
        print("\n" + "=" * 80)
        print(f"RESUMEN: {count_to_delete} secciones duplicadas eliminadas")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
