import pymysql

conn = pymysql.connect(
    host='localhost',
    user='root',
    password='sistemas',
    database='upao_timetabling'
)

cursor = conn.cursor()

# Modificar columna
cursor.execute('ALTER TABLE courses MODIFY COLUMN modalidad VARCHAR(20) DEFAULT "PRS"')
conn.commit()

# Verificar
cursor.execute('SHOW COLUMNS FROM courses WHERE Field="modalidad"')
result = cursor.fetchone()
print(f"✅ Column modalidad: {result}")

conn.close()
print("✅ Column updated successfully!")
