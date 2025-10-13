"""
Script para crear tabla professor_course_assignments
"""

import mysql.connector

conn = mysql.connector.connect(
    host='localhost',
    user='root',
    password='sistemas',
    database='upao_timetabling'
)

cursor = conn.cursor()

# Crear tabla si no existe
create_table_query = """
CREATE TABLE IF NOT EXISTS professor_course_assignments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    professor_id INT NOT NULL,
    course_id INT NOT NULL,
    session_type ENUM('T', 'P', 'L') NOT NULL COMMENT 'T=Teoria, P=Practica, L=Laboratorio',
    semestre VARCHAR(10) DEFAULT '2025-20',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (professor_id) REFERENCES professors(id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
    UNIQUE KEY unique_assignment (professor_id, course_id, session_type, semestre),
    INDEX idx_professor (professor_id),
    INDEX idx_course (course_id),
    INDEX idx_session_type (session_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

try:
    cursor.execute(create_table_query)
    conn.commit()
    print("[OK] Tabla 'professor_course_assignments' creada/verificada")
    
    # Migrar datos de professor_course_history si existen
    print("\n[INFO] Migrando datos de professor_course_history...")
    
    # Primero verificar si hay datos en history
    cursor.execute("SELECT COUNT(*) FROM professor_course_history")
    count = cursor.fetchone()[0]
    
    if count > 0:
        print(f"  Encontrados {count} registros en professor_course_history")
        
        # Insertar datos migrando a formato nuevo (asumiendo tipo T por defecto)
        migrate_query = """
        INSERT IGNORE INTO professor_course_assignments 
        (professor_id, course_id, session_type, semestre)
        SELECT 
            professor_id,
            course_id,
            'T' as session_type,
            semestre
        FROM professor_course_history
        """
        
        cursor.execute(migrate_query)
        conn.commit()
        print(f"  [OK] {cursor.rowcount} registros migrados")
    else:
        print("  No hay datos para migrar")
    
    # Mostrar estructura de la tabla
    print("\n[INFO] Estructura de la tabla:")
    cursor.execute("DESCRIBE professor_course_assignments")
    for row in cursor.fetchall():
        print(f"  {row}")
    
    # Contar registros
    cursor.execute("SELECT COUNT(*) FROM professor_course_assignments")
    total = cursor.fetchone()[0]
    print(f"\n[OK] Total de asignaciones en tabla: {total}")
    
except Exception as e:
    print(f"[ERROR] {e}")
    conn.rollback()
finally:
    cursor.close()
    conn.close()
