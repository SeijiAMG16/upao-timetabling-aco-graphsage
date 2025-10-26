"""
Script para inicializar datos maestros (seed data)
Profesores, Cursos, Aulas, Time Slots
"""

import pymysql
from datetime import time

def init_seed_data():
    """Inicializar datos base si las tablas están vacías"""
    
    conn = pymysql.connect(
        host='localhost',
        user='root',
        password='sistemas',
        database='upao_timetabling',
        charset='utf8mb4'
    )
    
    cursor = conn.cursor()
    
    # ============================================================================
    # TIME SLOTS (Bloques horarios)
    # ============================================================================
    
    cursor.execute("SELECT COUNT(*) FROM time_slots")
    if cursor.fetchone()[0] == 0:
        print("Inicializando time_slots...")
        
        time_blocks = [
            ('Lunes', '07:00:00', '07:50:00', 'M', 1),
            ('Lunes', '07:50:00', '08:40:00', 'M', 2),
            ('Lunes', '08:40:00', '09:30:00', 'M', 3),
            ('Lunes', '09:40:00', '10:30:00', 'M', 4),
            ('Lunes', '10:30:00', '11:20:00', 'M', 5),
            ('Lunes', '11:20:00', '12:10:00', 'M', 6),
            ('Lunes', '12:10:00', '13:00:00', 'T', 7),
            ('Lunes', '13:00:00', '13:50:00', 'T', 8),
            ('Lunes', '14:00:00', '14:50:00', 'T', 9),
            ('Lunes', '14:50:00', '15:40:00', 'T', 10),
            ('Lunes', '15:40:00', '16:30:00', 'T', 11),
            ('Lunes', '16:30:00', '17:20:00', 'T', 12),
            ('Lunes', '17:20:00', '18:10:00', 'N', 13),
            ('Lunes', '18:20:00', '19:10:00', 'N', 14),
            ('Lunes', '19:10:00', '20:00:00', 'N', 15),
            ('Lunes', '20:00:00', '20:50:00', 'N', 16),
            ('Lunes', '20:50:00', '21:40:00', 'N', 17),
        ]
        
        # Crear para todos los días
        days = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado']
        all_slots = []
        for day in days:
            for block in time_blocks:
                all_slots.append((day, block[1], block[2], block[3], block[4]))
        
        cursor.executemany(
            "INSERT INTO time_slots (dia_semana, hora_inicio, hora_fin, periodo, orden, activo) VALUES (%s, %s, %s, %s, %s, TRUE)",
            all_slots
        )
        print(f"✅ {len(all_slots)} time slots creados")
    else:
        print("⏭️  Time slots ya existen")
    
    # ============================================================================
    # AULAS (Classrooms)
    # ============================================================================
    
    cursor.execute("SELECT COUNT(*) FROM classrooms")
    if cursor.fetchone()[0] == 0:
        print("Inicializando classrooms...")
        
        classrooms = [
            # Edificio F - Aulas teóricas
            ('F101', 'F', '1', 40, 'Aula'),
            ('F102', 'F', '1', 40, 'Aula'),
            ('F201', 'F', '2', 40, 'Aula'),
            ('F202', 'F', '2', 40, 'Aula'),
            ('F301', 'F', '3', 35, 'Aula'),
            ('F302', 'F', '3', 35, 'Aula'),
            # Edificio G - Aulas teóricas grandes
            ('G101', 'G', '1', 50, 'Aula'),
            ('G102', 'G', '1', 50, 'Aula'),
            ('G201', 'G', '2', 45, 'Aula'),
            ('G202', 'G', '2', 45, 'Aula'),
            # Laboratorios F (grupos pequeños ≤20)
            ('LAB-F1', 'F', '1', 20, 'Laboratorio'),
            ('LAB-F2', 'F', '2', 20, 'Laboratorio'),
            ('LAB-F3', 'F', '3', 18, 'Laboratorio'),
            # Laboratorios G (grupos grandes >20)
            ('LAB-G1', 'G', '1', 30, 'Laboratorio'),
            ('LAB-G2', 'G', '2', 30, 'Laboratorio'),
            ('LAB-G3', 'G', '3', 25, 'Laboratorio'),
        ]
        
        cursor.executemany(
            "INSERT INTO classrooms (codigo, edificio, piso, capacidad, tipo) VALUES (%s, %s, %s, %s, %s)",
            classrooms
        )
        print(f"✅ {len(classrooms)} aulas creadas")
    else:
        print("⏭️  Classrooms ya existen")
    
    conn.commit()
    conn.close()
    print("\n🎉 Seed data inicializado correctamente!")

if __name__ == "__main__":
    init_seed_data()
