"""
🔒 BACKUP CRÍTICO DE ASIGNACIONES DE PROFESORES
Este script crea un backup de la tabla professor_course_assignments
"""
import mysql.connector
import json
from datetime import datetime
import os

# Conexión a la base de datos
conn = mysql.connector.connect(
    host="localhost",
    port=3306,
    user="root",
    password="root_password",
    database="upao_timetabling"
)

cursor = conn.cursor(dictionary=True)

# Obtener TODAS las asignaciones
cursor.execute("""
    SELECT 
        pca.id,
        pca.professor_id,
        p.nombre_completo AS professor_name,
        p.codigo AS professor_code,
        pca.course_id,
        c.codigo AS course_code,
        c.nombre AS course_name,
        pca.session_type,
        pca.league,
        pca.semestre,
        pca.created_at,
        pca.updated_at
    FROM professor_course_assignments pca
    JOIN professors p ON pca.professor_id = p.id
    JOIN courses c ON pca.course_id = c.id
    ORDER BY pca.course_id, pca.league, pca.session_type
""")

asignaciones = cursor.fetchall()

# Convertir datetime a string
for a in asignaciones:
    if a.get('created_at'):
        a['created_at'] = a['created_at'].isoformat()
    if a.get('updated_at'):
        a['updated_at'] = a['updated_at'].isoformat()

# Crear backup JSON
fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_dir = "../backups"
os.makedirs(backup_dir, exist_ok=True)

backup_file = f"{backup_dir}/asignaciones_profesores_CRITICO_{fecha}.json"

backup_data = {
    "fecha_backup": datetime.now().isoformat(),
    "total_asignaciones": len(asignaciones),
    "descripcion": "Backup de asignaciones de profesores - SISTEMA FUNCIONANDO CORRECTAMENTE",
    "asignaciones": asignaciones
}

with open(backup_file, 'w', encoding='utf-8') as f:
    json.dump(backup_data, f, indent=2, ensure_ascii=False)

# Crear también backup SQL
sql_backup_file = f"{backup_dir}/asignaciones_profesores_CRITICO_{fecha}.sql"

with open(sql_backup_file, 'w', encoding='utf-8') as f:
    f.write("-- BACKUP CRÍTICO DE ASIGNACIONES DE PROFESORES\n")
    f.write(f"-- Fecha: {datetime.now().isoformat()}\n")
    f.write(f"-- Total asignaciones: {len(asignaciones)}\n\n")
    
    f.write("-- Limpiar tabla antes de restaurar\n")
    f.write("-- DELETE FROM professor_course_assignments;\n\n")
    
    for a in asignaciones:
        f.write(f"INSERT INTO professor_course_assignments (id, professor_id, course_id, session_type, league, semestre) VALUES ")
        f.write(f"({a['id']}, {a['professor_id']}, {a['course_id']}, '{a['session_type']}', {a['league']}, '{a['semestre']}');\n")

cursor.close()
conn.close()

# Mostrar resumen
print("=" * 80)
print("🔒 BACKUP CRÍTICO CREADO EXITOSAMENTE")
print("=" * 80)
print(f"\n✅ Total de asignaciones respaldadas: {len(asignaciones)}")
print(f"\n📁 Archivos creados:")
print(f"   JSON: {backup_file}")
print(f"   SQL:  {sql_backup_file}")

# Mostrar estadísticas
cursos_unicos = len(set([a['course_id'] for a in asignaciones]))
profesores_unicos = len(set([a['professor_id'] for a in asignaciones]))

print(f"\n📊 Estadísticas:")
print(f"   Cursos con asignaciones: {cursos_unicos}")
print(f"   Profesores asignados: {profesores_unicos}")

# Mostrar algunas asignaciones de ejemplo
print(f"\n📝 Primeras 5 asignaciones:")
for i, a in enumerate(asignaciones[:5], 1):
    print(f"   [{i}] {a['course_code']} - {a['professor_name']} ({a['session_type']}, liga {a['league']})")

print("\n" + "=" * 80)
print("🔒 GUARDA ESTOS ARCHIVOS - SON CRÍTICOS")
print("=" * 80)
