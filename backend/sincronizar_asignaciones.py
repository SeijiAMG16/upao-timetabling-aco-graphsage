"""
Script de sincronizacion: schedule_assignments -> professor_course_assignments
Extrae las asignaciones unicas de schedule_assignments y las inserta en professor_course_assignments
"""
from app.database import get_db
from sqlalchemy import text

def main():
    db = next(get_db())
    
    print("=" * 80)
    print("SINCRONIZACION: schedule_assignments -> professor_course_assignments")
    print("=" * 80)
    
    # Verificar estado inicial
    print("\n[1/4] Verificando estado actual...")
    sa_count = db.execute(text("SELECT COUNT(*) FROM schedule_assignments")).scalar()
    pca_count = db.execute(text("SELECT COUNT(*) FROM professor_course_assignments")).scalar()
    print(f"  schedule_assignments: {sa_count} registros")
    print(f"  professor_course_assignments: {pca_count} registros")
    
    # Limpiar tabla destino
    print("\n[2/4] Limpiando professor_course_assignments...")
    db.execute(text("DELETE FROM professor_course_assignments"))
    db.commit()
    print("  [OK] Tabla limpiada")
    
    # Sincronizar datos
    print("\n[3/4] Extrayendo asignaciones unicas de schedule_assignments...")
    sync_query = text("""
        INSERT INTO professor_course_assignments 
            (professor_id, course_id, session_type, league, semestre, created_at)
        SELECT DISTINCT 
            sa.professor_id,
            sa.course_id,
            CASE cs.tipo 
                WHEN 'teoria' THEN 'teoria'
                WHEN 'T' THEN 'teoria'
                WHEN 'practica' THEN 'practica'
                WHEN 'P' THEN 'practica'
                WHEN 'laboratorio' THEN 'laboratorio'
                WHEN 'L' THEN 'laboratorio'
            END as session_type,
            COALESCE(cs.league, 1) as league,
            sa.semestre as semestre,
            NOW() as created_at
        FROM schedule_assignments sa
        JOIN course_sections cs ON sa.course_section_id = cs.id
        WHERE sa.generado_por_algoritmo = TRUE
            AND cs.tipo IN ('teoria', 'T', 'practica', 'P', 'laboratorio', 'L')
    """)
    
    try:
        result = db.execute(sync_query)
        db.commit()
        print(f"  [OK] Sincronizacion completada")
    except Exception as e:
        print(f"  [ERROR] {e}")
        db.rollback()
        return
    
    # Verificar resultado
    print("\n[4/4] Verificando resultado...")
    pca_new_count = db.execute(text("SELECT COUNT(*) FROM professor_course_assignments")).scalar()
    print(f"  professor_course_assignments: {pca_new_count} registros")
    
    # Mostrar ejemplos
    print("\n" + "=" * 80)
    print("EJEMPLOS DE ASIGNACIONES SINCRONIZADAS")
    print("=" * 80)
    
    examples = db.execute(text("""
        SELECT 
            c.codigo,
            c.nombre,
            pca.session_type,
            pca.league,
            p.nombre_completo,
            pca.semestre
        FROM professor_course_assignments pca
        JOIN courses c ON pca.course_id = c.id
        JOIN professors p ON pca.professor_id = p.id
        ORDER BY c.codigo, pca.session_type, pca.league
        LIMIT 15
    """)).fetchall()
    
    for row in examples:
        print(f"{row[0]:10} | {row[1]:40} | {row[2]:12} | Liga {row[3]} | {row[4]:30} | {row[5]}")
    
    print("\n" + "=" * 80)
    print(f"RESUMEN: {pca_new_count} asignaciones sincronizadas correctamente")
    print("=" * 80)

if __name__ == "__main__":
    main()
