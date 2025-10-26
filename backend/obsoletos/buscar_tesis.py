import pymysql

conn = pymysql.connect(host='localhost', user='root', password='210605', database='timetabling_sys')
cursor = conn.cursor()

# Buscar cursos TESIS
cursor.execute("SELECT id, codigo, nombre_completo FROM courses WHERE codigo LIKE '%TESIS%' OR nombre_completo LIKE '%TESIS%'")
tesis_courses = cursor.fetchall()

print("="*80)
print("CURSOS CON 'TESIS' EN BD:")
print("="*80)
for row in tesis_courses:
    print(f"  ID: {row[0]}, Codigo: {row[1]}, Nombre: {row[2]}")

# Buscar HUMA900
cursor.execute("SELECT id, codigo, nombre_completo FROM courses WHERE codigo = 'HUMA900'")
huma900 = cursor.fetchone()

if huma900:
    print("\n" + "="*80)
    print("HUMA900:")
    print("="*80)
    print(f"  ID: {huma900[0]}, Codigo: {huma900[1]}, Nombre: {huma900[2]}")
    
    # Buscar secciones
    cursor.execute(f"SELECT id, tipo, league, seccion, alumnos_proyectados, activa FROM course_sections WHERE course_id = {huma900[0]}")
    sections = cursor.fetchall()
    
    print(f"\n  Secciones ({len(sections)}):")
    for sec in sections:
        print(f"    ID {sec[0]}: Tipo {sec[1]}, Liga {sec[2]}, Seccion {sec[3]}, Alumnos {sec[4]}, Activa {sec[5]}")
else:
    print("\n⚠️ HUMA900 NO encontrado en BD")

conn.close()
