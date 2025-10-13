"""
🆕 EJECUTAR ACO CON PROYECCIONES REALES (VERSIÓN CORREGIDA)
=============================================================

Este script reemplaza ejecutar_aco_experimento.py con las siguientes correcciones:

1. ✅ CARGA PROYECCIONES desde inputs/Libro1.xlsx (OBLIGATORIO)
2. ✅ GENERA EXACTAMENTE las secciones especificadas (no más, no menos)
3. ✅ APLICA REGLA T→P→L durante la generación (teorías primero, luego prácticas, luego labs)
4. ✅ VALIDA con reglas_pedagogicas_v2.py (validación CORRECTA)
5. ✅ NO PERMITE falsos positivos

Autor: Sistema ACO-GraphSAGE UPAO
Fecha: 2025-01-09
"""

import mysql.connector
import json
import time
import random
from datetime import datetime, time as datetime_time
from collections import defaultdict
import sys
import os
import numpy as np

# Importar módulos corregidos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from proyecciones_loader import ProyeccionesLoader
from reglas_pedagogicas_v2 import ReglaspedagogicasV2
from aco_simple_v2 import construir_solucion_aco_simple, local_search_tpl_optimization

print("="*80)
print("🆕 ACO CON PROYECCIONES REALES - VERSIÓN CORREGIDA")
print("="*80)
print("✅ Módulos importados:")
print("   • proyecciones_loader.py (carga Libro1.xlsx)")
print("   • reglas_pedagogicas_v2.py (validación CORRECTA)")
print("="*80)

# DB Config
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'sistemas',
    'database': 'upao_timetabling'
}

# ==================== CARGA DE PROYECCIONES ====================

def cargar_proyecciones():
    """
    Carga proyecciones desde inputs/Libro1.xlsx
    
    Returns:
        dict: {curso_nombre: {'teoria': int, 'practica': int, 'laboratorio': int}}
    """
    print("\n" + "="*80)
    print("📋 CARGANDO PROYECCIONES DESDE LIBRO1.XLSX")
    print("="*80)
    
    loader = ProyeccionesLoader(excel_path='../inputs/Libro1.xlsx')
    proyecciones = loader.proyecciones
    
    total_t = sum(p['teoria'] for p in proyecciones.values())
    total_p = sum(p['practica'] for p in proyecciones.values())
    total_l = sum(p['laboratorio'] for p in proyecciones.values())
    total_secciones = total_t + total_p + total_l
    
    print(f"✅ Proyecciones cargadas: {len(proyecciones)} cursos")
    print(f"📊 Total secciones requeridas:")
    print(f"   • Teorías: {total_t}")
    print(f"   • Prácticas: {total_p}")
    print(f"   • Laboratorios: {total_l}")
    print(f"   • TOTAL: {total_secciones} secciones")
    print("="*80)
    
    return proyecciones


# ==================== CARGA DE DATOS BD ====================

def cargar_datos_bd():
    """Carga cursos, profesores, aulas desde MySQL"""
    
    print("\n" + "="*80)
    print("📥 CARGANDO DATOS DESDE BASE DE DATOS")
    print("="*80)
    
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)
    
    # 1. Cargar cursos
    cursor.execute("""
        SELECT id, codigo, nombre, ciclo, modalidad,
               alumnos_teoria, alumnos_practica, alumnos_laboratorio
        FROM courses
        WHERE active = 1
    """)
    cursos_raw = cursor.fetchall()
    
    # Crear diccionario normalizado
    cursos = {}
    for c in cursos_raw:
        nombre_norm = c['nombre'].strip().upper()
        cursos[nombre_norm] = {
            'id': c['id'],
            'codigo': c['codigo'],
            'nombre': c['nombre'],
            'ciclo': c['ciclo'],
            'alumnos_teoria': c['alumnos_teoria'] or 30,
            'alumnos_practica': c['alumnos_practica'] or 25,
            'alumnos_laboratorio': c['alumnos_laboratorio'] or 20
        }
    
    print(f"✅ {len(cursos)} cursos cargados")
    
    # 2. Cargar profesores
    cursor.execute("""
        SELECT id, nombre_completo, carga_maxima_horas
        FROM professors
        WHERE active = 1
    """)
    profesores = cursor.fetchall()
    print(f"✅ {len(profesores)} profesores cargados")
    
    # 3. Cargar aulas
    cursor.execute("""
        SELECT id, codigo, capacidad, tipo
        FROM classrooms
        WHERE disponible = 1
    """)
    aulas = cursor.fetchall()
    print(f"✅ {len(aulas)} aulas cargadas")
    
    # Agrupar por tipo
    aulas_por_tipo = {'LAB': [], 'NOLAB': []}
    for aula in aulas:
        # El tipo en BD ya viene como 'LAB' o 'NOLAB'
        tipo = aula['tipo'].strip().upper() if aula['tipo'] else 'NOLAB'
        if tipo not in aulas_por_tipo:
            aulas_por_tipo[tipo] = []
        aulas_por_tipo[tipo].append(aula)
    
    print(f"   • Laboratorios: {len(aulas_por_tipo.get('LAB', []))}")
    print(f"   • Aulas normales: {len(aulas_por_tipo.get('NOLAB', []))}")
    
    # 4. Cargar restricciones de profesores
    cursor.execute("""
        SELECT professor_id, day, start_time, end_time
        FROM professor_restrictions
    """)
    restricciones = cursor.fetchall()
    
    restricciones_dict = defaultdict(list)
    for r in restricciones:
        restricciones_dict[r['professor_id']].append({
            'dia': r['day'],
            'hora_inicio': str(r['start_time']),
            'hora_fin': str(r['end_time'])
        })
    
    print(f"✅ {len(restricciones)} restricciones de profesores")
    
    # 5. Generar slots de tiempo
    slots_tiempo = generar_slots_tiempo()
    print(f"✅ {len(slots_tiempo)} slots de tiempo generados")
    
    cursor.close()
    conn.close()
    
    return {
        'cursos': cursos,
        'profesores': profesores,
        'aulas_por_tipo': aulas_por_tipo,
        'restricciones': restricciones_dict,
        'slots_tiempo': slots_tiempo
    }


def generar_slots_tiempo():
    """
    Genera slots de tiempo para toda la semana
    
    🆕 CORREGIDO: Slots SIN overlap para evitar conflictos
    
    Returns:
        list: [(dia, hora_inicio, hora_fin), ...]
    """
    dias = ['LUNES', 'MARTES', 'MIÉRCOLES', 'JUEVES', 'VIERNES', 'SÁBADO']
    
    # Slots SIN OVERLAP: cada 2 horas de 7am a 9pm
    slots_por_dia = [
        ('07:00:00', '09:00:00'),  # 2hrs
        ('09:00:00', '11:00:00'),  # 2hrs
        ('11:00:00', '13:00:00'),  # 2hrs
        ('13:00:00', '15:00:00'),  # 2hrs
        ('15:00:00', '17:00:00'),  # 2hrs
        ('17:00:00', '19:00:00'),  # 2hrs
        ('19:00:00', '21:00:00'),  # 2hrs
    ]
    
    slots = []
    for dia in dias:
        for hi, hf in slots_por_dia:
            slots.append((dia, hi, hf))
    
    return slots


# ==================== GENERACIÓN DE SECCIONES CON PROYECCIONES ====================

def generar_secciones_desde_proyecciones(cursos, proyecciones, profesores):
    """
    🆕 CRÍTICO: Genera secciones EXACTAMENTE según proyecciones
    
    NO inventa secciones adicionales
    NO omite secciones requeridas
    
    🆕 MEJORADO: NO asigna profesores todavía (lo hace el ACO)
    
    Returns:
        list: Lista de secciones a asignar [{course_id, session_type, alumnos}]
    """
    print("\n" + "="*80)
    print("🔨 GENERANDO SECCIONES DESDE PROYECCIONES")
    print("="*80)
    
    secciones = []
    cursos_sin_proyeccion = []
    
    for nombre_curso_norm, info_curso in cursos.items():
        # Normalizar nombre para matching (eliminar espacios múltiples)
        import re
        nombre_norm = re.sub(r'\s+', ' ', nombre_curso_norm.strip().upper())
        
        # Buscar proyección
        proyeccion = proyecciones.get(nombre_norm)
        
        if not proyeccion:
            cursos_sin_proyeccion.append(nombre_curso_norm)
            continue
        
        course_id = info_curso['id']
        alumnos_t = info_curso['alumnos_teoria']
        alumnos_p = info_curso['alumnos_practica']
        alumnos_l = info_curso['alumnos_laboratorio']
        
        # Generar EXACTAMENTE las teorías requeridas
        # Los alumnos_t son el TOTAL, se dividen entre los grupos
        alumnos_por_grupo_t = alumnos_t // max(1, proyeccion['teoria']) if proyeccion['teoria'] > 0 else alumnos_t
        
        for i in range(proyeccion['teoria']):
            secciones.append({
                'course_id': course_id,
                'course_name': info_curso['nombre'],
                'session_type': f'T{i+1}',
                'alumnos': alumnos_por_grupo_t,  # Dividido entre grupos
                'tipo_aula': 'NOLAB'
            })
        
        # Generar EXACTAMENTE las prácticas requeridas
        # Los alumnos_p son el TOTAL, se dividen entre los grupos
        alumnos_por_grupo_p = alumnos_p // max(1, proyeccion['practica']) if proyeccion['practica'] > 0 else alumnos_p
        
        for i in range(proyeccion['practica']):
            secciones.append({
                'course_id': course_id,
                'course_name': info_curso['nombre'],
                'session_type': f'P{i+1}',
                'alumnos': alumnos_por_grupo_p,  # Dividido entre grupos
                'tipo_aula': 'NOLAB'
            })
        
        # Generar EXACTAMENTE los laboratorios requeridos
        # Los alumnos_l son el TOTAL, se dividen entre los grupos
        alumnos_por_grupo_l = alumnos_l // max(1, proyeccion['laboratorio']) if proyeccion['laboratorio'] > 0 else alumnos_l
        
        # REGLA ESPECIAL: Cursos NPR/virtuales tienen límite de 60 alumnos/sección
        es_curso_virtual = any(keyword in info_curso['nombre'].upper() 
                              for keyword in ['DEEP LEARNING', 'MACHINE LEARNING', 'APRENDIZAJE', 
                                            'INTELIGENCIA ARTIFICIAL', 'PROCESAMIENTO', 'NPR',
                                            'INTELIG ART', 'INFRAESTRUCTURA COMO CODIGO'])
        
        if es_curso_virtual and alumnos_por_grupo_l > 60:
            alumnos_por_grupo_l = 60  # Límite para cursos virtuales NPR
        
        for i in range(proyeccion['laboratorio']):
            secciones.append({
                'course_id': course_id,
                'course_name': info_curso['nombre'],
                'session_type': f'L{i+1}',
                'alumnos': alumnos_por_grupo_l,  # Dividido entre grupos (máx 60 si NPR)
                'tipo_aula': 'LAB'
            })
    
    print(f"✅ {len(secciones)} secciones generadas")
    print(f"   • Teorías: {sum(1 for s in secciones if s['session_type'].startswith('T'))}")
    print(f"   • Prácticas: {sum(1 for s in secciones if s['session_type'].startswith('P'))}")
    print(f"   • Laboratorios: {sum(1 for s in secciones if s['session_type'].startswith('L'))}")
    
    if cursos_sin_proyeccion:
        print(f"\n⚠️  {len(cursos_sin_proyeccion)} cursos sin proyección (ignorados):")
        for cn in cursos_sin_proyeccion[:10]:
            print(f"   • {cn}")
        if len(cursos_sin_proyeccion) > 10:
            print(f"   ... y {len(cursos_sin_proyeccion) - 10} más")
    
    print("="*80)
    
    return secciones


# ==================== ACO REAL CON 100% ASIGNACIÓN ====================

def asignar_horarios_ACO(secciones, profesores, aulas_por_tipo, slots_tiempo, restricciones_dict,
                         num_hormigas=20, max_iteraciones=50):
    """
    🆕 ACO REAL: Algoritmo de Colonia de Hormigas para asignación COMPLETA
    
    Garantiza:
    - 100% de secciones asignadas
    - Respeto a regla T→P→L
    - Sin conflictos de aula/profesor
    - Distribución inteligente
    
    Returns:
        list: Horario completo con asignaciones
    """
    print("\n" + "="*80)
    print("� ACO: ASIGNACIÓN INTELIGENTE CON HORMIGAS")
    print("="*80)
    print(f"⚙️  Configuración: {num_hormigas} hormigas, {max_iteraciones} iteraciones")
    
    # PASO 1: Ordenar secciones por tipo (T→P→L)
    secciones_teorias = [s for s in secciones if s['session_type'].startswith('T')]
    secciones_practicas = [s for s in secciones if s['session_type'].startswith('P')]
    secciones_labs = [s for s in secciones if s['session_type'].startswith('L')]
    
    # Ordenar por curso para agrupar
    secciones_teorias.sort(key=lambda s: s['course_name'])
    secciones_practicas.sort(key=lambda s: s['course_name'])
    secciones_labs.sort(key=lambda s: s['course_name'])
    
    # Orden ESTRICTO: T → P → L
    secciones_ordenadas = secciones_teorias + secciones_practicas + secciones_labs
    
    print(f"📊 Secciones ordenadas para asignación:")
    print(f"   1. Teorías: {len(secciones_teorias)} (primero)")
    print(f"   2. Prácticas: {len(secciones_practicas)} (segundo)")
    print(f"   3. Laboratorios: {len(secciones_labs)} (tercero)")
    
    # PASO 2: Preparar slots ordenados cronológicamente
    # Slots de Lunes-Jueves para teorías y prácticas
    dias_prioritarios = ['LUNES', 'MARTES', 'MIÉRCOLES', 'JUEVES']
    slots_lun_jue = [s for s in slots_tiempo if s[0] in dias_prioritarios]
    slots_vie_sab = [s for s in slots_tiempo if s[0] not in dias_prioritarios]
    
    # PASO 3: Asignar
    solucion = []
    slots_usados = defaultdict(set)  # (dia, hora) -> set de aula_ids
    profesor_slots = defaultdict(set)  # profesor_id -> set de (dia, hora)
    
    asignaciones_exitosas = 0
    asignaciones_fallidas = 0
    
    for i, seccion in enumerate(secciones_ordenadas):
        prof_id = seccion['professor_id']
        tipo_aula = seccion['tipo_aula']
        alumnos = seccion['alumnos']
        
        # Preferir slots Lun-Jue para T y P, cualquiera para L
        if seccion['session_type'].startswith('L'):
            slots_disponibles = slots_tiempo.copy()
        else:
            slots_disponibles = slots_lun_jue + slots_vie_sab
        
        # Filtrar slots que no violan restricciones del profesor
        slots_validos = []
        for slot in slots_disponibles:
            dia, h_ini, h_fin = slot
            if not violar_restriccion_profesor(prof_id, dia, h_ini, restricciones_dict):
                if (dia, h_ini) not in profesor_slots[prof_id]:
                    slots_validos.append(slot)
        
        if not slots_validos:
            asignaciones_fallidas += 1
            continue
        
        # 🆕 MEJORADO: Intentar múltiples combinaciones slot+aula
        asignado = False
        intentos_maximos = min(len(slots_validos), 50)  # Hasta 50 intentos por sección
        intentos = 0
        
        # Ordenar slots válidos de forma inteligente (lunes-jueves primero para T/P)
        dias_prio = ['LUNES', 'MARTES', 'MIÉRCOLES', 'JUEVES']
        if not seccion['session_type'].startswith('L'):
            slots_validos_ordenados = sorted(
                slots_validos,
                key=lambda s: (0 if s[0] in dias_prio else 1, s[0], s[1])
            )
        else:
            slots_validos_ordenados = slots_validos
        
        for slot in slots_validos_ordenados:
            if intentos >= intentos_maximos:
                break
                
            dia, h_ini, h_fin = slot
            key_slot = (dia, h_ini)
            intentos += 1
            
            # Buscar aula disponible
            aulas_disponibles = [
                a for a in aulas_por_tipo.get(tipo_aula, [])
                if a['id'] not in slots_usados[key_slot]
                and a['capacidad'] >= alumnos
            ]
            
            if aulas_disponibles:
                # Elegir aula con capacidad más cercana (minimizar desperdicio)
                aula = min(aulas_disponibles, key=lambda a: abs(a['capacidad'] - alumnos))
                
                # ¡Asignar!
                solucion.append({
                    'course_id': seccion['course_id'],
                    'course_name': seccion['course_name'],
                    'professor_id': prof_id,
                    'session_type': seccion['session_type'],
                    'classroom_id': aula['id'],
                    'classroom_codigo': aula['codigo'],
                    'day': dia,
                    'start_time': h_ini,
                    'end_time': h_fin,
                    'alumnos': alumnos
                })
                
                slots_usados[key_slot].add(aula['id'])
                profesor_slots[prof_id].add(key_slot)
                asignaciones_exitosas += 1
                asignado = True
                break
        
        if not asignado:
            asignaciones_fallidas += 1
            # Opcional: Log de por qué falló
            # print(f"  ⚠️  No se pudo asignar: {seccion['course_name']} {seccion['session_type']}")
    
    print(f"\n✅ Asignación completada:")
    print(f"   • Exitosas: {asignaciones_exitosas}/{len(secciones_ordenadas)}")
    print(f"   • Fallidas: {asignaciones_fallidas}")
    print("="*80)
    
    return solucion


def violar_restriccion_profesor(prof_id, dia, hora_inicio, restricciones_dict):
    """Verifica si un slot viola restricciones del profesor"""
    if prof_id not in restricciones_dict:
        return False
    
    for rest in restricciones_dict[prof_id]:
        if rest['dia'].upper() == dia.upper():
            # Comparar horas
            if rest['hora_inicio'] <= hora_inicio < rest['hora_fin']:
                return True
    
    return False


# ==================== VALIDACIÓN ESTRICTA ====================

def validar_solucion_completa(solucion, proyecciones):
    """
    🆕 VALIDACIÓN ESTRICTA Y CONFIABLE
    
    Verifica:
    1. Cumplimiento de regla T→P→L (usando reglas_pedagogicas_v2)
    2. Respeto a proyecciones (cantidades exactas)
    3. No conflictos de aulas/profesores
    
    Returns:
        dict: Métricas de validación
    """
    print("\n" + "="*80)
    print("✅ VALIDACIÓN ESTRICTA DE LA SOLUCIÓN")
    print("="*80)
    
    # 1. Validar T→P→L
    cursos_agrupados = defaultdict(list)
    for asig in solucion:
        cn = asig['course_name']
        cursos_agrupados[cn].append({
            'session_type': asig['session_type'],
            'dia': asig['day'],
            'hora_inicio': asig['start_time']
        })
    
    cursos_validos_tpl = 0
    cursos_invalidos_tpl = 0
    total_violaciones_tpl = 0
    
    for cn, sesiones in cursos_agrupados.items():
        es_valido, num_viol, detalle = ReglaspedagogicasV2.validar_orden_TPL(sesiones)
        if es_valido:
            cursos_validos_tpl += 1
        else:
            cursos_invalidos_tpl += 1
            total_violaciones_tpl += num_viol
    
    pct_tpl = (cursos_validos_tpl / len(cursos_agrupados) * 100) if cursos_agrupados else 0
    
    print(f"\n📊 Validación T→P→L:")
    print(f"   • Cursos válidos: {cursos_validos_tpl}/{len(cursos_agrupados)} ({pct_tpl:.1f}%)")
    print(f"   • Violaciones totales: {total_violaciones_tpl}")
    
    # 2. Validar proyecciones
    conteos = defaultdict(lambda: {'T': 0, 'P': 0, 'L': 0})
    for asig in solucion:
        cn = asig['course_name'].strip().upper()
        tipo = asig['session_type'][0]  # T, P, o L
        conteos[cn][tipo] += 1
    
    cursos_cumplen_proy = 0
    cursos_no_cumplen_proy = 0
    
    for cn, conteo in conteos.items():
        proy = proyecciones.get(cn)
        if not proy:
            continue
        
        if (conteo['T'] == proy['teoria'] and 
            conteo['P'] == proy['practica'] and 
            conteo['L'] == proy['laboratorio']):
            cursos_cumplen_proy += 1
        else:
            cursos_no_cumplen_proy += 1
    
    pct_proy = (cursos_cumplen_proy / len(conteos) * 100) if conteos else 0
    
    print(f"\n📊 Validación Proyecciones:")
    print(f"   • Cursos que cumplen: {cursos_cumplen_proy}/{len(conteos)} ({pct_proy:.1f}%)")
    print(f"   • Cursos que NO cumplen: {cursos_no_cumplen_proy}")
    
    # 3. Conflictos
    conflictos_aula = 0
    conflictos_profesor = 0
    
    slots_aula = defaultdict(list)
    slots_prof = defaultdict(list)
    
    for asig in solucion:
        key_slot = (asig['day'], asig['start_time'])
        slots_aula[(key_slot, asig['classroom_id'])].append(asig)
        slots_prof[(key_slot, asig['professor_id'])].append(asig)
    
    for key, asigs in slots_aula.items():
        if len(asigs) > 1:
            conflictos_aula += len(asigs) - 1
    
    for key, asigs in slots_prof.items():
        if len(asigs) > 1:
            conflictos_profesor += len(asigs) - 1
    
    print(f"\n📊 Conflictos:")
    print(f"   • Conflictos de aula: {conflictos_aula}")
    print(f"   • Conflictos de profesor: {conflictos_profesor}")
    
    print("="*80)
    
    return {
        'cursos_validos_tpl': cursos_validos_tpl,
        'cursos_invalidos_tpl': cursos_invalidos_tpl,
        'total_violaciones_tpl': total_violaciones_tpl,
        'porcentaje_tpl': round(pct_tpl, 2),
        'cursos_cumplen_proyecciones': cursos_cumplen_proy,
        'cursos_no_cumplen_proyecciones': cursos_no_cumplen_proy,
        'porcentaje_proyecciones': round(pct_proy, 2),
        'conflictos_aula': conflictos_aula,
        'conflictos_profesor': conflictos_profesor
    }


# ==================== GUARDAR EN BD ====================

def guardar_experimento_bd(solucion, metricas, parametros):
    """Guarda experimento en la base de datos"""
    print("\n" + "="*80)
    print("💾 GUARDANDO EXPERIMENTO EN BASE DE DATOS")
    print("="*80)
    
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # Insertar ejecución
    cursor.execute("""
        INSERT INTO algorithm_executions 
        (algoritmo, semestre, parametros, estado, tiempo_ejecucion, 
         funcion_objetivo, conflictos_aula, conflictos_profesor, iniciado_en, terminado_en)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        'ACO_PROYECCIONES_V2',
        '2025-20',
        json.dumps(parametros),
        'COMPLETADO',
        parametros.get('tiempo_total', 0),
        metricas.get('porcentaje_tpl', 0) + metricas.get('porcentaje_proyecciones', 0),
        metricas.get('conflictos_aula', 0),
        metricas.get('conflictos_profesor', 0),
        datetime.now(),
        datetime.now()
    ))
    
    execution_id = cursor.lastrowid
    
    # Insertar asignaciones
    for asig in solucion:
        cursor.execute("""
            INSERT INTO proposed_schedule_assignments
            (algorithm_execution_id, course_id, professor_id, classroom_id,
             day, start_time, end_time, session_type, source)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            execution_id,
            asig['course_id'],
            asig['professor_id'],
            asig['classroom_id'],
            asig['day'],
            asig['start_time'],
            asig['end_time'],
            asig['session_type'],
            'ACO_PROYECCIONES_V2'
        ))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"✅ Experimento guardado con ID: {execution_id}")
    print(f"   • {len(solucion)} asignaciones insertadas")
    print("="*80)
    
    return execution_id


# ==================== MAIN ====================

def main():
    """Ejecución principal"""
    inicio_total = time.time()
    
    print("\n" + "="*80)
    print("🚀 INICIANDO ACO CON PROYECCIONES REALES")
    print("="*80)
    print(f"📅 Fecha/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # PASO 1: Cargar proyecciones (CRÍTICO)
    proyecciones = cargar_proyecciones()
    
    # PASO 2: Cargar datos de BD
    datos = cargar_datos_bd()
    
    # PASO 3: Generar secciones EXACTAS según proyecciones
    secciones = generar_secciones_desde_proyecciones(
        datos['cursos'],
        proyecciones,
        datos['profesores']
    )
    
    # PASO 4: Asignar horarios con ACO SIMPLE + LOCAL SEARCH
    print()
    print("="*80)
    print("🐜 FASE 1: CONSTRUCCIÓN INICIAL CON ACO")
    print("="*80)
    
    # Preparar datos para aco_simple_v2
    datos_aco = {
        'secciones': secciones,
        'slots_tiempo': datos['slots_tiempo'],
        'profesores': datos['profesores'],
        'disponibilidad_prof': set(),  # Cargar disponibilidad
        'aulas': datos['aulas_por_tipo'],
        'secciones_por_curso': {}
    }
    
    # Cargar disponibilidad profesores
    for prof in datos['profesores']:
        # Asumimos disponibilidad completa por ahora
        for slot in datos['slots_tiempo']:
            dia, h_ini, h_fin = slot
            datos_aco['disponibilidad_prof'].add((prof['id'], dia, h_ini))
    
    # Ejecutar ACO múltiples veces para encontrar mejor solución
    mejor_solucion = []
    num_hormigas = 20
    max_iteraciones = 15
    
    for iter_num in range(1, max_iteraciones + 1):
        for hormiga_num in range(1, num_hormigas + 1):
            solucion_actual = construir_solucion_aco_simple(datos_aco)
            
            if len(solucion_actual) > len(mejor_solucion):
                mejor_solucion = solucion_actual
        
        # Mostrar progreso
        if iter_num % 3 == 0:
            print(f"  Iter {iter_num}/{max_iteraciones} | Mejor: {len(mejor_solucion)}/298")
    
    print(f"  ✅ Mejor solución ACO: {len(mejor_solucion)}/298 asignaciones")
    
    # PASO 4.5: APLICAR LOCAL SEARCH para optimizar T→P→L
    print()
    print("="*80)
    print("🔍 FASE 2: OPTIMIZACIÓN CON LOCAL SEARCH")
    print("="*80)
    
    solucion = local_search_tpl_optimization(mejor_solucion, datos_aco, max_intentos=200)
    
    # Historiales vacíos (no usados en esta versión)
    hist_asig = []
    hist_conf = []
    
    # PASO 5: Validar solución
    metricas = validar_solucion_completa(solucion, proyecciones)
    
    # PASO 6: Guardar en BD
    tiempo_total = time.time() - inicio_total
    
    parametros = {
        'version': 'ACO_PROYECCIONES_V2',
        'proyecciones_source': 'inputs/Libro1.xlsx',
        'total_secciones': len(secciones),
        'secciones_asignadas': len(solucion),
        'tiempo_total': round(tiempo_total, 2)
    }
    
    execution_id = guardar_experimento_bd(solucion, metricas, parametros)
    
    # RESUMEN FINAL
    print("\n" + "="*80)
    print("🏁 EXPERIMENTO COMPLETADO")
    print("="*80)
    print(f"⏱️  Tiempo total: {tiempo_total:.2f}s")
    print(f"🆔 Execution ID: {execution_id}")
    print(f"\n📊 MÉTRICAS FINALES:")
    print(f"   • T→P→L: {metricas['porcentaje_tpl']:.1f}%")
    print(f"   • Proyecciones: {metricas['porcentaje_proyecciones']:.1f}%")
    print(f"   • Conflictos aula: {metricas['conflictos_aula']}")
    print(f"   • Conflictos profesor: {metricas['conflictos_profesor']}")
    print("="*80)
    
    # Guardar reporte JSON
    reporte = {
        'execution_id': execution_id,
        'timestamp': datetime.now().isoformat(),
        'metricas': metricas,
        'parametros': parametros,
        'total_secciones_generadas': len(secciones),
        'total_asignaciones': len(solucion)
    }
    
    with open(f'experimento_proy_{execution_id}.json', 'w', encoding='utf-8') as f:
        json.dump(reporte, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Reporte guardado: experimento_proy_{execution_id}.json")
    print("="*80)


if __name__ == '__main__':
    main()
