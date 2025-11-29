"""
🔒 BACKUP CRÍTICO DE ASIGNACIONES DE PROFESORES - SISTEMA FUNCIONANDO
Este backup contiene las asignaciones que están mostrándose correctamente en el frontend
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal
from sqlalchemy import text
import json
from datetime import datetime

print("=" * 80)
print("🔒 BACKUP CRÍTICO DE ASIGNACIONES DE PROFESORES")
print("=" * 80)

session = SessionLocal()

try:
    # Obtener TODAS las asignaciones con información completa
    query = text("""
        SELECT 
            pca.id,
            pca.professor_id,
            p.codigo AS professor_code,
            p.nombre_completo AS professor_name,
            pca.course_id,
            c.codigo AS course_code,
            c.nombre AS course_name,
            pca.session_type,
            pca.league,
            pca.semestre,
            pca.created_at
        FROM professor_course_assignments pca
        JOIN professors p ON pca.professor_id = p.id
        JOIN courses c ON pca.course_id = c.id
        ORDER BY pca.course_id, pca.league, pca.session_type
    """)
    
    result = session.execute(query)
    asignaciones = []
    
    for row in result:
        asignaciones.append({
            "id": row[0],
            "professor_id": row[1],
            "professor_code": row[2],
            "professor_name": row[3],
            "course_id": row[4],
            "course_code": row[5],
            "course_name": row[6],
            "session_type": row[7],
            "league": row[8],
            "semestre": row[9],
            "created_at": row[10].isoformat() if row[10] else None,
        })
    
    # Crear directorio de backups
    backup_dir = "../backups"
    os.makedirs(backup_dir, exist_ok=True)
    
    fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Backup JSON
    json_file = f"{backup_dir}/CRITICO_asignaciones_profesores_{fecha}.json"
    backup_data = {
        "fecha_backup": datetime.now().isoformat(),
        "total_asignaciones": len(asignaciones),
        "estado": "SISTEMA FUNCIONANDO CORRECTAMENTE",
        "descripcion": "Backup de asignaciones mostrándose correctamente en frontend",
        "nota": "🔒 NO BORRAR - CONTIENE CONFIGURACIÓN FUNCIONANDO",
        "asignaciones": asignaciones
    }
    
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(backup_data, f, indent=2, ensure_ascii=False)
    
    # Backup SQL para restauración rápida
    sql_file = f"{backup_dir}/CRITICO_asignaciones_profesores_{fecha}.sql"
    
    with open(sql_file, 'w', encoding='utf-8') as f:
        f.write("-- 🔒 BACKUP CRÍTICO DE ASIGNACIONES DE PROFESORES\n")
        f.write(f"-- Fecha: {datetime.now().isoformat()}\n")
        f.write(f"-- Total asignaciones: {len(asignaciones)}\n")
        f.write("-- Estado: SISTEMA FUNCIONANDO CORRECTAMENTE\n")
        f.write("-- NO BORRAR ESTE ARCHIVO\n\n")
        
        f.write("-- Para restaurar:\n")
        f.write("-- 1. DELETE FROM professor_course_assignments WHERE semestre = '2025-20';\n")
        f.write("-- 2. Ejecutar los INSERT siguientes:\n\n")
        
        for a in asignaciones:
            created = a['created_at'] if a['created_at'] else 'NOW()'
            
            if not a['created_at']:
                created = 'NOW()'
            else:
                created = f"'{a['created_at']}'"
            
            f.write(
                f"INSERT INTO professor_course_assignments "
                f"(id, professor_id, course_id, session_type, league, semestre, created_at) "
                f"VALUES ({a['id']}, {a['professor_id']}, {a['course_id']}, '{a['session_type']}', "
                f"{a['league']}, '{a['semestre']}', {created});\n"
            )
    
    # Estadísticas
    cursos_unicos = len(set([a['course_id'] for a in asignaciones]))
    profesores_unicos = len(set([a['professor_id'] for a in asignaciones]))
    
    print(f"\n✅ BACKUP CREADO EXITOSAMENTE")
    print(f"\n📊 ESTADÍSTICAS:")
    print(f"   Total asignaciones: {len(asignaciones)}")
    print(f"   Cursos con asignaciones: {cursos_unicos}")
    print(f"   Profesores asignados: {profesores_unicos}")
    
    print(f"\n📁 ARCHIVOS CREADOS:")
    print(f"   JSON: {json_file}")
    print(f"   SQL:  {sql_file}")
    
    # Mostrar distribución por tipo de sesión
    tipos = {}
    for a in asignaciones:
        tipo = a['session_type']
        tipos[tipo] = tipos.get(tipo, 0) + 1
    
    print(f"\n📋 DISTRIBUCIÓN POR TIPO:")
    for tipo, count in sorted(tipos.items()):
        print(f"   {tipo}: {count}")
    
    # Mostrar algunas asignaciones de ejemplo
    print(f"\n📝 PRIMERAS 10 ASIGNACIONES:")
    for i, a in enumerate(asignaciones[:10], 1):
        print(f"   [{i:2d}] {a['course_code']:10s} | {a['professor_name'][:30]:30s} | {a['session_type']:10s} | Liga {a['league']}")
    
    if len(asignaciones) > 10:
        print(f"   ... y {len(asignaciones) - 10} más")
    
    print("\n" + "=" * 80)
    print("🔒 GUARDA ESTOS ARCHIVOS EN UN LUGAR SEGURO")
    print("💾 Estos backups contienen el sistema funcionando correctamente")
    print("=" * 80)

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

finally:
    session.close()
