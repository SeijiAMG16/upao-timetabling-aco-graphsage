import json
import mysql.connector

conn = mysql.connector.connect(host='localhost', user='root', password='sistemas', database='upao_timetabling')
cursor = conn.cursor()

# Leer asignaciones del JSON
with open('asignaciones_actuales.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Insertar asignaciones históricas
cursor.execute('DELETE FROM professor_course_history')
print(f"🗑️  Limpiando tabla...")

insertadas = 0
for asig in data['asignaciones']:
    try:
        cursor.execute('''
            INSERT INTO professor_course_history 
            (professor_id, course_id, semestre, veces_asignado)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE veces_asignado = veces_asignado + 1
        ''', (asig['profesor_id'], asig['curso_id'], '2025-20', 1))
        insertadas += 1
    except Exception as e:
        print(f"Error insertando {asig['curso_codigo']}: {e}")

conn.commit()

print(f'✅ {insertadas} asignaciones históricas insertadas')

# Mostrar algunas
cursor.execute('''
    SELECT p.nombre_completo, c.codigo, c.nombre
    FROM professor_course_history h
    JOIN professors p ON h.professor_id = p.id
    JOIN courses c ON h.course_id = c.id
''')

print('\n📚 Asignaciones históricas registradas:')
for row in cursor.fetchall():
    print(f'  {row[0][:35]:35} -> {row[1]:20} {row[2][:40]}')

cursor.close()
conn.close()
