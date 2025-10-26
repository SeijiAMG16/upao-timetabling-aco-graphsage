"""
Genera secciones con números de liga basado en las proyecciones de Libro1.xlsx

REGLAS:
1. Número de ligas = Número de grupos de teoría (N° Grupos Teoría)
2. Cada liga tiene: 1 teoría + N prácticas + M laboratorios
3. P/L se distribuyen equitativamente entre ligas
4. Cursos especiales (TESIS, PROYECTO) usan laboratorios aunque sean teoría
"""
import pandas as pd
import mysql.connector
from typing import List, Dict
import math

# Cursos que usan laboratorio aunque sean teoría
CURSOS_TEORIA_CON_LAB = [
    'PROYECTO DE INVESTIGACION',
    'TESIS I',
    'TESIS II'
]


def conectar_db():
    """Conecta a la base de datos"""
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='sistemas',
        database='upao_timetabling'
    )


def cargar_curso_desde_db(codigo_curso: str) -> Dict:
    """Carga información de un curso desde la BD"""
    conn = conectar_db()
    cursor = conn.cursor(dictionary=True)
    
    query = """
        SELECT id, codigo, nombre 
        FROM courses 
        WHERE codigo = %s OR nombre LIKE %s
        LIMIT 1
    """
    cursor.execute(query, (codigo_curso, f"%{codigo_curso}%"))
    curso = cursor.fetchone()
    
    # Consumir resultados pendientes
    cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return curso


def generar_secciones_con_ligas(proyecciones_excel: str = '../inputs/Libro1.xlsx') -> List[Dict]:
    """
    Genera secciones con números de liga basado en proyecciones
    
    Returns:
        Lista de secciones con estructura:
        {
            'course_id': int,
            'course_code': str,
            'course_name': str,
            'session_type': str (T1, T2, P1, P2, L1, L2, etc.),
            'liga': int,
            'tipo': str ('T', 'P', 'L'),
            'modalidad': str ('PRS' o 'NPR'),
            'requiere_lab': bool,
            'alumnos': int
        }
    """
    # Leer proyecciones
    df = pd.read_excel(proyecciones_excel)
    
    # Renombrar columnas
    df = df.rename(columns={
        'ASIGNATURA': 'curso',
        'COD': 'codigo_area',
        'NUM': 'codigo_num',
        'PRESENCIAL (PRS)/ NO PRESENCIAL (NPR)': 'modalidad',
        'N° Grupos Teoría': 'grupos_teoria',
        'N° Grupos Práctica': 'grupos_practica',
        'N° Grupos Laboratorio': 'grupos_laboratorio',
        'N° alumnos para Teoría': 'alumnos_teoria',
        'N° alumnos para Práctica': 'alumnos_practica',
        'N° alumnos para Laboratorio': 'alumnos_laboratorio'
    })
    
    # Filtrar cursos válidos
    df_cursos = df[df['curso'].notna()].copy()
    df_cursos = df_cursos[df_cursos['modalidad'].isin(['PRS', 'NPR', 'NPRS'])]
    
    secciones = []
    cursos_sin_bd = []
    
    print("=" * 80)
    print("GENERACIÓN DE SECCIONES CON LIGAS")
    print("=" * 80)
    
    for idx, row in df_cursos.iterrows():
        curso_nombre = str(row['curso']).strip()
        modalidad = row['modalidad']
        
        # Número de grupos
        grupos_t = int(row['grupos_teoria']) if pd.notna(row['grupos_teoria']) else 0
        grupos_p = int(row['grupos_practica']) if pd.notna(row['grupos_practica']) else 0
        grupos_l = int(row['grupos_laboratorio']) if pd.notna(row['grupos_laboratorio']) else 0
        
        # Alumnos
        alumnos_t = int(row['alumnos_teoria']) if pd.notna(row['alumnos_teoria']) else 0
        alumnos_p = int(row['alumnos_practica']) if pd.notna(row['alumnos_practica']) else 0
        alumnos_l = int(row['alumnos_laboratorio']) if pd.notna(row['alumnos_laboratorio']) else 0
        
        # Buscar en BD
        curso_db = cargar_curso_desde_db(curso_nombre)
        
        if not curso_db:
            cursos_sin_bd.append(curso_nombre)
            continue
        
        # Número de ligas = Número de teorías
        # Si no hay teorías pero hay prácticas/labs, crear al menos 1 liga
        num_ligas = max(grupos_t, 1) if (grupos_p > 0 or grupos_l > 0) else grupos_t
        
        if num_ligas == 0:
            continue
        
        # Calcular distribución por liga
        practicas_por_liga = grupos_p // num_ligas if num_ligas > 0 else 0
        practicas_extra = grupos_p % num_ligas if num_ligas > 0 else 0
        
        labs_por_liga = grupos_l // num_ligas if num_ligas > 0 else 0
        labs_extra = grupos_l % num_ligas if num_ligas > 0 else 0
        
        # Determinar si requiere laboratorio
        requiere_lab = any(keyword in curso_nombre.upper() for keyword in 
                          ['PROYECTO', 'TESIS', 'LABORATORIO', 'LAB', 'PROGRAMACION', 
                           'BASE DE DATOS', 'REDES', 'SOFTWARE'])
        
        print(f"\n📚 {curso_nombre[:50]}")
        print(f"   ID: {curso_db['id']}, Modalidad: {modalidad}")
        print(f"   Ligas: {num_ligas} | T:{grupos_t} P:{grupos_p} L:{grupos_l}")
        
        # Generar secciones por liga
        for liga in range(1, num_ligas + 1):
            # TEORÍA (1 por liga)
            if grupos_t > 0 and liga <= grupos_t:
                # Determinar tipo de aula para teoría
                if any(nombre in curso_nombre.upper() for nombre in CURSOS_TEORIA_CON_LAB):
                    tipo_aula_teoria = 'LAB'
                else:
                    tipo_aula_teoria = 'NOLAB'
                
                secciones.append({
                    'course_id': curso_db['id'],
                    'course_code': curso_db['codigo'],
                    'course_name': curso_nombre,
                    'session_type': f'T{liga}',
                    'liga': liga,
                    'tipo': 'T',
                    'modalidad': modalidad,
                    'requiere_lab': tipo_aula_teoria == 'LAB',
                    'alumnos': alumnos_t // grupos_t if grupos_t > 0 else alumnos_t
                })
            
            # PRÁCTICAS (distribuidas por liga)
            num_practicas_esta_liga = practicas_por_liga
            if liga <= practicas_extra:
                num_practicas_esta_liga += 1
            
            for i in range(num_practicas_esta_liga):
                secciones.append({
                    'course_id': curso_db['id'],
                    'course_code': curso_db['codigo'],
                    'course_name': curso_nombre,
                    'session_type': f'P{liga}',
                    'liga': liga,
                    'tipo': 'P',
                    'modalidad': modalidad,
                    'requiere_lab': False,
                    'alumnos': alumnos_p // grupos_p if grupos_p > 0 else 0
                })
            
            # LABORATORIOS (distribuidos por liga)
            num_labs_esta_liga = labs_por_liga
            if liga <= labs_extra:
                num_labs_esta_liga += 1
            
            for i in range(num_labs_esta_liga):
                secciones.append({
                    'course_id': curso_db['id'],
                    'course_code': curso_db['codigo'],
                    'course_name': curso_nombre,
                    'session_type': f'L{liga}',
                    'liga': liga,
                    'tipo': 'L',
                    'modalidad': modalidad,
                    'requiere_lab': True,
                    'alumnos': alumnos_l // grupos_l if grupos_l > 0 else 0
                })
        
        # Mostrar estructura generada
        tipos_en_liga = {}
        for seccion in [s for s in secciones if s['course_id'] == curso_db['id']]:
            liga_num = seccion['liga']
            tipo = seccion['tipo']
            if liga_num not in tipos_en_liga:
                tipos_en_liga[liga_num] = {'T': 0, 'P': 0, 'L': 0}
            tipos_en_liga[liga_num][tipo] += 1
        
        for liga_num in sorted(tipos_en_liga.keys()):
            counts = tipos_en_liga[liga_num]
            print(f"      Liga {liga_num}: {counts['T']}T + {counts['P']}P + {counts['L']}L")
    
    print("\n" + "=" * 80)
    print(f"✅ SECCIONES GENERADAS: {len(secciones)}")
    print("=" * 80)
    
    # Estadísticas
    tipos = {'T': 0, 'P': 0, 'L': 0}
    modalidades = {'PRS': 0, 'NPR': 0}
    
    for sec in secciones:
        tipos[sec['tipo']] += 1
        if sec['modalidad'] in ['PRS', 'NPRS']:
            modalidades['PRS'] += 1
        else:
            modalidades['NPR'] += 1
    
    print(f"  📊 Por tipo: T:{tipos['T']} P:{tipos['P']} L:{tipos['L']}")
    print(f"  📍 Por modalidad: PRS:{modalidades['PRS']} NPR:{modalidades['NPR']}")
    
    if cursos_sin_bd:
        print(f"\n⚠️  CURSOS NO ENCONTRADOS EN BD ({len(cursos_sin_bd)}):")
        for curso in cursos_sin_bd[:5]:
            print(f"  • {curso}")
        if len(cursos_sin_bd) > 5:
            print(f"  ... y {len(cursos_sin_bd) - 5} más")
    
    return secciones


if __name__ == '__main__':
    secciones = generar_secciones_con_ligas()
    
    print("\n" + "=" * 80)
    print("EJEMPLOS DE SECCIONES GENERADAS:")
    print("=" * 80)
    
    # Mostrar algunos ejemplos
    for seccion in secciones[:20]:
        req_lab = "🧪LAB" if seccion['requiere_lab'] else "📝AULA"
        print(f"{seccion['session_type']:<4} | {seccion['course_name'][:40]:<40} | "
              f"{seccion['modalidad']:<4} | {req_lab} | {seccion['alumnos']} alumnos")
