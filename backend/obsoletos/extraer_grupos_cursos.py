#!/usr/bin/env python3
"""
EXTRACTOR DE GRUPOS DE CURSOS DEL EXCEL
Analiza el Excel para extraer información de grupos de teoría/práctica/laboratorio
"""

import mysql.connector
import pandas as pd
from collections import defaultdict
import re

def conectar_bd():
    """Conectar a la base de datos"""
    return mysql.connector.connect(
        host='localhost',
        database='upao_timetabling',
        user='root',
        password='sistemas'
    )

def extraer_grupos_del_excel():
    """Extrae información de grupos de todos los cursos del Excel"""
    
    excel_file = r"..\inputs\Horario_Docentes(2025-20).xlsx"
    
    # Contadores de grupos por curso
    grupos_por_curso = defaultdict(lambda: {'teoria': set(), 'practica': set(), 'laboratorio': set()})
    
    # Leer todas las hojas
    xl = pd.ExcelFile(excel_file)
    print(f"Analizando {len(xl.sheet_names)} hojas...")
    
    for sheet_name in xl.sheet_names:
        print(f"  Procesando hoja: {sheet_name}")
        
        # Leer hoja sin headers
        df = pd.read_excel(excel_file, sheet_name=sheet_name, header=None)
        
        # Buscar todas las celdas con información de cursos
        for i in range(df.shape[0]):
            for j in range(df.shape[1]):
                celda = df.iloc[i, j]
                
                if pd.isna(celda):
                    continue
                    
                contenido = str(celda).strip()
                
                # Buscar patrones (T1), (P2), (L1), etc.
                match = re.search(r'(.+?)\s*\(([TPL])([12])\)', contenido, re.IGNORECASE)
                if match:
                    nombre_curso_raw = match.group(1).strip()
                    tipo = match.group(2).upper()
                    numero_grupo = int(match.group(3))
                    
                    # Limpiar nombre del curso
                    # Remover códigos de curso al final
                    nombre_curso = re.sub(r'\s*\d{4,}\s*-.*$', '', nombre_curso_raw)
                    nombre_curso = nombre_curso.strip()
                    
                    if len(nombre_curso) > 5:  # Filtrar nombres muy cortos
                        if tipo == 'T':
                            grupos_por_curso[nombre_curso]['teoria'].add(numero_grupo)
                        elif tipo == 'P':
                            grupos_por_curso[nombre_curso]['practica'].add(numero_grupo)
                        elif tipo == 'L':
                            grupos_por_curso[nombre_curso]['laboratorio'].add(numero_grupo)
    
    return grupos_por_curso

def actualizar_grupos_en_bd(grupos_por_curso):
    """Actualiza la tabla courses con la información de grupos"""
    
    conn = conectar_bd()
    cursor = conn.cursor()
    
    # Obtener cursos existentes
    cursor.execute("SELECT id, codigo, nombre FROM courses")
    cursos_bd = cursor.fetchall()
    
    actualizaciones = 0
    
    for curso_id, curso_codigo, curso_nombre in cursos_bd:
        # Buscar match con los grupos extraídos
        match_encontrado = None
        mejor_score = 0
        
        for nombre_excel, grupos in grupos_por_curso.items():
            # Calcular similitud (simple)
            if nombre_excel.upper() in curso_nombre.upper() or curso_nombre.upper() in nombre_excel.upper():
                score = len(set(nombre_excel.upper().split()) & set(curso_nombre.upper().split()))
                if score > mejor_score:
                    mejor_score = score
                    match_encontrado = grupos
        
        if match_encontrado:
            grupos_teoria = len(match_encontrado['teoria'])
            grupos_practica = len(match_encontrado['practica']) 
            grupos_laboratorio = len(match_encontrado['laboratorio'])
            
            if grupos_teoria > 0 or grupos_practica > 0 or grupos_laboratorio > 0:
                # Actualizar en BD
                cursor.execute("""
                    UPDATE courses 
                    SET grupos_teoria = %s, grupos_practica = %s, grupos_laboratorio = %s
                    WHERE id = %s
                """, (grupos_teoria, grupos_practica, grupos_laboratorio, curso_id))
                
                print(f"✅ {curso_codigo} - {curso_nombre}")
                print(f"   T:{grupos_teoria} P:{grupos_practica} L:{grupos_laboratorio}")
                actualizaciones += 1
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return actualizaciones

def main():
    print("🔍 EXTRAYENDO GRUPOS DE CURSOS DEL EXCEL")
    print("=" * 60)
    
    # Extraer grupos del Excel
    grupos_por_curso = extraer_grupos_del_excel()
    
    print(f"\n📊 RESUMEN DE GRUPOS ENCONTRADOS:")
    for curso, grupos in list(grupos_por_curso.items())[:10]:  # Mostrar primeros 10
        teoria = len(grupos['teoria'])
        practica = len(grupos['practica'])
        laboratorio = len(grupos['laboratorio'])
        if teoria > 0 or practica > 0 or laboratorio > 0:
            print(f"  {curso[:40]:<40} T:{teoria} P:{practica} L:{laboratorio}")
    
    # Actualizar BD
    print(f"\n💾 ACTUALIZANDO BASE DE DATOS...")
    actualizaciones = actualizar_grupos_en_bd(grupos_por_curso)
    
    print(f"\n✅ PROCESO COMPLETADO")
    print(f"   Cursos actualizados: {actualizaciones}")
    print(f"   Cursos analizados: {len(grupos_por_curso)}")

if __name__ == "__main__":
    main()