"""
Analiza las secciones más problemáticas que impiden completar el horario
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:@localhost:3306/upao_timetabling")
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

# Secciones que fallan frecuentemente según el log
secciones_problematicas = [1552, 1553, 1554, 1631, 1608, 1609, 1607, 1613, 
                           1616, 1617, 1592, 1570, 1551, 1550, 1574]

print("=" * 80)
print("ANÁLISIS DE SECCIONES PROBLEMÁTICAS")
print("=" * 80)

for seccion_id in secciones_problematicas:
    query = text("""
        SELECT 
            cs.id,
            cs.code,
            cs.name,
            cs.section_number,
            cs.league_number,
            cs.session_type,
            cs.total_students,
            cs.requires_lab,
            cs.weekly_hours,
            p.name as profesor_nombre,
            p.id as profesor_id
        FROM course_sections cs
        LEFT JOIN professors p ON cs.professor_id = p.id
        WHERE cs.id = :seccion_id
    """)
    
    result = session.execute(query, {"seccion_id": seccion_id}).fetchone()
    
    if result:
        print(f"\n{'=' * 80}")
        print(f"SECCIÓN {result.id}: {result.code} - {result.name}")
        print(f"{'=' * 80}")
        print(f"  Tipo: {result.session_type}")
        print(f"  Liga: {result.league_number}")
        print(f"  Estudiantes: {result.total_students}")
        print(f"  Horas semanales: {result.weekly_hours}")
        print(f"  Requiere lab: {result.requires_lab}")
        print(f"  Profesor: {result.profesor_nombre} (ID: {result.profesor_id})")
        
        # Buscar aulas compatibles
        tipo_aula = 'LAB' if result.requires_lab or result.session_type == 'LABORATORIO' else 'TEORICA'
        
        query_aulas = text("""
            SELECT 
                c.id,
                c.name,
                c.capacity,
                c.room_type,
                c.building
            FROM classrooms c
            WHERE c.is_available = 1
                AND c.capacity >= :estudiantes
                AND (c.room_type = :tipo OR c.room_type = 'TEORICA_LAB')
            ORDER BY c.capacity ASC
            LIMIT 5
        """)
        
        aulas = session.execute(query_aulas, {
            "estudiantes": result.total_students,
            "tipo": tipo_aula
        }).fetchall()
        
        print(f"\n  Aulas compatibles (tipo {tipo_aula}, capacidad >= {result.total_students}):")
        if aulas:
            for aula in aulas:
                print(f"    - {aula.name} (ID: {aula.id}): capacidad {aula.capacity}, tipo {aula.room_type}, edificio {aula.building}")
        else:
            print(f"    ❌ NO HAY AULAS DISPONIBLES")
            
        # Verificar conflictos de profesor en franjas específicas
        if result.profesor_id:
            query_conflictos = text("""
                SELECT COUNT(*) as total_asignaciones
                FROM course_sections cs2
                WHERE cs2.professor_id = :profesor_id
                    AND cs2.id != :seccion_id
            """)
            
            conflictos = session.execute(query_conflictos, {
                "profesor_id": result.profesor_id,
                "seccion_id": seccion_id
            }).fetchone()
            
            print(f"\n  Otras secciones del mismo profesor: {conflictos.total_asignaciones}")

print("\n" + "=" * 80)
print("RESUMEN")
print("=" * 80)

# Agrupar por curso y liga
query_resumen = text("""
    SELECT 
        cs.code,
        cs.name,
        cs.league_number,
        COUNT(*) as total_secciones,
        GROUP_CONCAT(cs.id) as ids_secciones,
        SUM(CASE WHEN cs.id IN :ids THEN 1 ELSE 0 END) as secciones_problematicas
    FROM course_sections cs
    WHERE cs.id IN :ids
    GROUP BY cs.code, cs.name, cs.league_number
    ORDER BY secciones_problematicas DESC
""")

resumen = session.execute(query_resumen, {"ids": tuple(secciones_problematicas)}).fetchall()

print("\nCursos con más secciones problemáticas:")
for r in resumen:
    print(f"  {r.code} Liga {r.league_number}: {r.secciones_problematicas}/{r.total_secciones} secciones problemáticas")
    print(f"    IDs: {r.ids_secciones}")

session.close()
