"""
Debug rápido: Ver estructura de aulas_por_tipo
"""

import mysql.connector

def main():
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='sistemas',
        database='upao_timetabling'
    )
    
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT id, codigo, tipo, capacidad
        FROM classrooms
        WHERE disponible = 1
    """)
    
    aulas = cursor.fetchall()
    
    print(f"Total aulas: {len(aulas)}")
    
    aulas_por_tipo = {}
    for a in aulas:
        tipo = a['tipo']
        if tipo not in aulas_por_tipo:
            aulas_por_tipo[tipo] = []
        aulas_por_tipo[tipo].append(a)
    
    print(f"\nAulas por tipo:")
    for tipo, lista in aulas_por_tipo.items():
        print(f"  {tipo}: {len(lista)} aulas")
        for aula in lista[:3]:
            print(f"    - {aula['codigo']} (cap: {aula['capacidad']})")
    
    print(f"\nClaves en dict: {list(aulas_por_tipo.keys())}")
    print(f"¿'LAB' in dict? {'LAB' in aulas_por_tipo}")
    print(f"¿'NOLAB' in dict? {'NOLAB' in aulas_por_tipo}")
    
    conn.close()

if __name__ == '__main__':
    main()
