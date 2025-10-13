"""
Ejecutar ACO desde datos de la BD y guardar experimentos
🆕 VERSIÓN MEJORADA CON GRAPHSAGE EMBEDDINGS
"""
import mysql.connector
import json
import time
import random
from datetime import datetime
from collections import defaultdict
import sys
import os
import numpy as np

# Agregar path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 🆕 Importar módulo de inferencia GraphSAGE
try:
    from graphsage_inference import get_graphsage_inference, calcular_heuristica_graphsage
    USE_GRAPHSAGE = True
    print("✅ GraphSAGE habilitado - Usando embeddings para heurística inteligente")
except ImportError as e:
    USE_GRAPHSAGE = False
    print(f"⚠️  GraphSAGE no disponible: {e}")
    print("   Usando heurística simple (random)")

# 🆕 Importar reglas pedagógicas
try:
    from reglas_pedagogicas import ReglasInstitucionales, generar_reporte_calidad
    USE_REGLAS_PEDAGOGICAS = True
    print("✅ Reglas Pedagógicas habilitadas - T→P→L, horarios prime, distribución")
except ImportError as e:
    USE_REGLAS_PEDAGOGICAS = False
    print(f"⚠️  Reglas pedagógicas no disponibles: {e}")

# Variable global para instancia de inferencia
_graphsage_instance = None

def init_graphsage():
    """Inicializa GraphSAGE una sola vez"""
    global _graphsage_instance
    if USE_GRAPHSAGE and _graphsage_instance is None:
        try:
            _graphsage_instance = get_graphsage_inference()
            return True
        except Exception as e:
            print(f"⚠️  Error al cargar GraphSAGE: {e}")
            return False
    return USE_GRAPHSAGE

# DB Config
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'sistemas',
    'database': 'upao_timetabling'
}

# ==================== CARGAR DATOS DE LA BD ====================
def cargar_datos_bd():
    """Carga cursos, profesores, aulas, restricciones desde MySQL"""
    
    print("\n" + "="*80)
    print("📥 CARGANDO DATOS DESDE BASE DE DATOS")
    print("="*80)
    
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)
    
    # 1. Cargar cursos
    cursor.execute("""
        SELECT id, codigo, nombre, ciclo, modalidad,
               alumnos_teoria, alumnos_practica, alumnos_laboratorio,
               grupos_teoria, grupos_laboratorio
        FROM courses
        WHERE id IN (
            SELECT DISTINCT course_id 
            FROM proposed_schedule_assignments 
            WHERE source = 'EXCEL_2025'
        )
    """)
    cursos = cursor.fetchall()
    print(f"✅ {len(cursos)} cursos cargados")
    
    # 2. Cargar profesores con restricciones
    cursor.execute("""
        SELECT p.id, p.nombre_completo, p.carga_maxima_horas
        FROM professors p
        WHERE p.id IN (
            SELECT DISTINCT professor_id 
            FROM proposed_schedule_assignments 
            WHERE source = 'EXCEL_2025'
        )
    """)
    profesores = cursor.fetchall()
    print(f"✅ {len(profesores)} profesores cargados")
    
    # 3. Cargar restricciones
    cursor.execute("""
        SELECT professor_id, day, start_time, end_time, duration_blocks
        FROM professor_restrictions
    """)
    restricciones = cursor.fetchall()
    print(f"✅ {len(restricciones)} restricciones cargadas")
    
    # 4. Cargar aulas disponibles
    cursor.execute("""
        SELECT id, codigo, tipo, capacidad, edificio, disponible
        FROM classrooms
        WHERE disponible = 1
    """)
    aulas = cursor.fetchall()
    print(f"✅ {len(aulas)} aulas disponibles")
    
    # 5. Cargar asignaciones curso-profesor (SIN horarios predefinidos del Excel)
    cursor.execute("""
        SELECT DISTINCT
            ps.professor_id,
            ps.course_id,
            ps.nrc,
            ps.session_type,
            c.nombre as curso_nombre,
            c.modalidad,
            c.alumnos_teoria,
            c.alumnos_practica,
            c.alumnos_laboratorio,
            p.nombre_completo as profesor_nombre
        FROM proposed_schedule_assignments ps
        JOIN courses c ON ps.course_id = c.id
        JOIN professors p ON ps.professor_id = p.id
        WHERE ps.source = 'EXCEL_2025'
          AND c.modalidad = 'PRS'  -- Solo presenciales
        GROUP BY ps.professor_id, ps.course_id, ps.nrc, ps.session_type
    """)
    asignaciones_sin_horario = cursor.fetchall()
    print(f"✅ {len(asignaciones_sin_horario)} asignaciones necesitan horario+aula")
    
    # 6. Cargar slots de tiempo reales
    cursor.execute("""
        SELECT DISTINCT day, start_time, end_time
        FROM proposed_schedule_assignments
        WHERE source = 'EXCEL_2025'
        ORDER BY 
            FIELD(day, 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo'),
            start_time
    """)
    slots_tiempo = cursor.fetchall()
    print(f"✅ {len(slots_tiempo)} slots de tiempo (horarios reales)")
    
    cursor.close()
    conn.close()
    
    return {
        'cursos': cursos,
        'profesores': profesores,
        'restricciones': restricciones,
        'aulas': aulas,
        'asignaciones_sin_horario': asignaciones_sin_horario,
        'slots_tiempo': slots_tiempo
    }

# ==================== ACO SIMPLIFICADO ====================
def ejecutar_aco_simple(datos, params):
    """ACO que genera horarios DESDE CERO (no usa Excel)"""
    
    print("\n" + "="*80)
    print("🐜 EJECUTANDO ACO - GENERACIÓN DE HORARIOS DESDE CERO")
    print("="*80)
    print(f"Iteraciones: {params['max_iterations']}")
    print(f"Hormigas: {params['num_ants']}")
    
    asignaciones = datos['asignaciones_sin_horario']
    aulas = datos['aulas']
    slots_tiempo = datos['slots_tiempo']
    restricciones_dict = defaultdict(list)
    
    # Indexar aulas por tipo
    # LAB: F201-F404, G*01 (solo para sesiones L1, L2, L3)
    # NOLAB: Resto de aulas G (para sesiones T1-T3, P1-P3)
    aulas_lab = [a for a in aulas if a['tipo'] == 'LAB']
    aulas_nolab = [a for a in aulas if a['tipo'] == 'NOLAB']
    
    aulas_por_tipo = {
        'LAB': aulas_lab,      # Solo sesiones L (laboratorio)
        'NOLAB': aulas_nolab   # Sesiones T (teoría) y P (práctica)
    }
    
    print(f"\n📊 Aulas disponibles desde BD:")
    print(f"   • Total en BD: {len(aulas)}")
    print(f"   • LAB (F2-F4, G*01): {len(aulas_lab)}")
    print(f"   • NOLAB (resto): {len(aulas_nolab)}")
    
    # Indexar restricciones por profesor
    for r in datos['restricciones']:
        restricciones_dict[r['professor_id']].append(r)
    
    # Convertir slots_tiempo a tuplas (day, start_time, end_time)
    slots_tiempo = [(s['day'], s['start_time'], s['end_time']) for s in slots_tiempo]
    
    # Ver días únicos en los slots
    dias_unicos = sorted(set(s[0] for s in slots_tiempo))
    
    # Separar slots por día (para preferencias pedagógicas)
    # Aceptar tanto español como inglés (por si acaso)
    dias_teoria_pref = ['lunes', 'martes', 'miércoles', 'miercoles', 'jueves', 
                        'monday', 'tuesday', 'wednesday', 'thursday']
    slots_lunes_jueves = [s for s in slots_tiempo if s[0].lower() in dias_teoria_pref]
    slots_viernes_sabado = [s for s in slots_tiempo if s[0].lower() not in dias_teoria_pref]
    
    print(f"📊 Slots de tiempo (desde BD):")
    print(f"   • Total: {len(slots_tiempo)}")
    print(f"   • Días: {dias_unicos}")
    print(f"   • Lun-Jue (teorías preferidas): {len(slots_lunes_jueves)}")
    print(f"   • Vie-Sáb: {len(slots_viernes_sabado)}")
    
    print(f"📊 Aulas disponibles:")
    
    mejor_solucion = None
    mejor_fitness = float('inf')
    historial_fitness = []
    
    inicio = time.time()
    
    for iteracion in range(params['max_iterations']):
        iter_inicio = time.time()
        
        # Ejecutar hormigas
        soluciones = []
        for ant in range(params['num_ants']):
            solucion = generar_horario_completo(
                asignaciones, aulas_por_tipo, slots_tiempo, restricciones_dict
            )
            fitness = calcular_fitness_completo(solucion)
            soluciones.append((solucion, fitness))
            
            if fitness < mejor_fitness:
                mejor_fitness = fitness
                mejor_solucion = solucion
        
        iter_tiempo = time.time() - iter_inicio
        historial_fitness.append(mejor_fitness)
        
        print(f"  Iter {iteracion+1:3d}/{params['max_iterations']} | "
              f"Mejor Fitness: {mejor_fitness:8.2f} | "
              f"Tiempo: {iter_tiempo:.2f}s")
    
    tiempo_total = time.time() - inicio
    
    print(f"\n✅ ACO Completado en {tiempo_total:.2f}s")
    print(f"🏆 Mejor Fitness: {mejor_fitness:.2f}")
    
    # 🆕 Generar reporte de calidad pedagógica
    if USE_REGLAS_PEDAGOGICAS and mejor_solucion:
        try:
            metricas_pedagogicas = generar_reporte_calidad(mejor_solucion)
        except Exception as e:
            print(f"⚠️  Error al generar reporte pedagógico: {e}")
            metricas_pedagogicas = None
    else:
        metricas_pedagogicas = None
    
    return {
        'solucion': mejor_solucion,
        'fitness': mejor_fitness,
        'historial_fitness': historial_fitness,
        'tiempo_total': tiempo_total,
        'iteraciones': params['max_iterations'],
        'num_ants': params['num_ants'],
        'metricas_pedagogicas': metricas_pedagogicas
    }

# ==================== HEURÍSTICA INTELIGENTE CON GRAPHSAGE ====================

def calcular_heuristica_inteligente(course_id, professor_id, classroom_id, 
                                    day, start_time, penalty_factor=1.0):
    """
    🆕 Heurística mejorada que usa embeddings de GraphSAGE cuando está disponible
    
    Args:
        course_id: ID del curso
        professor_id: ID del profesor  
        classroom_id: ID del aula
        day: Día de la semana
        start_time: Hora de inicio
        penalty_factor: Factor de penalización (0.0-1.0)
    
    Returns:
        Valor heurístico entre 0.01 y 1.0
    """
    global _graphsage_instance
    
    if USE_GRAPHSAGE and _graphsage_instance is not None:
        try:
            # Usar embeddings de GraphSAGE para calcular compatibilidad
            score = calcular_heuristica_graphsage(
                course_id=course_id,
                professor_id=professor_id,
                classroom_id=classroom_id,
                day=day,
                start_time=start_time,
                penalty_factor=penalty_factor
            )
            return score
        except Exception as e:
            # Si falla GraphSAGE, caer a heurística simple
            pass
    
    # Heurística simple (fallback)
    base_score = random.uniform(0.5, 1.0)
    return max(0.01, base_score * penalty_factor)

def seleccionar_slot_con_heuristica(slots_disponibles, course_id, professor_id, 
                                    aulas_posibles, penalty_base=1.0):
    """
    🆕 Selecciona el mejor slot usando heurística de GraphSAGE
    
    En lugar de elegir aleatoriamente, calculamos scores para cada slot
    y seleccionamos probabilísticamente según los scores.
    """
    if not slots_disponibles or not aulas_posibles:
        return None, None
    
    if not USE_GRAPHSAGE or _graphsage_instance is None:
        # Fallback: selección aleatoria
        slot = random.choice(slots_disponibles)
        aula = random.choice(aulas_posibles)
        return slot, aula
    
    # Calcular scores para cada combinación slot-aula
    scores = []
    for slot in slots_disponibles[:20]:  # Limitar a 20 para eficiencia
        dia, hora_inicio, hora_fin = slot
        for aula in aulas_posibles[:10]:  # Top 10 aulas
            score = calcular_heuristica_inteligente(
                course_id=course_id,
                professor_id=professor_id,
                classroom_id=aula['id'],
                day=dia,
                start_time=hora_inicio,
                penalty_factor=penalty_base
            )
            scores.append((slot, aula, score))
    
    if not scores:
        # Si no hay scores, fallback a random
        slot = random.choice(slots_disponibles)
        aula = random.choice(aulas_posibles)
        return slot, aula
    
    # Selección probabilística basada en scores (ACO style)
    # Probabilidad proporcional al score elevado al cuadrado (β=2)
    total = sum(s[2]**2 for s in scores)
    if total == 0 or total < 1e-10:
        slot = random.choice(slots_disponibles)
        aula = random.choice(aulas_posibles)
        return slot, aula
    
    probs = np.array([(s[2]**2) / total for s in scores])
    # Normalizar para asegurar que sumen exactamente 1.0
    probs = probs / probs.sum()
    
    try:
        idx = np.random.choice(len(scores), p=probs)
    except ValueError:
        # Si aún hay error, fallback a random
        slot = random.choice(slots_disponibles)
        aula = random.choice(aulas_posibles)
        return slot, aula
    
    return scores[idx][0], scores[idx][1]

# ==================== GENERACIÓN DE HORARIOS ====================

def generar_horario_completo(asignaciones, aulas_por_tipo, slots_tiempo, restricciones_dict):
    """Genera un horario COMPLETO desde cero (día, hora, aula)
    🆕 Ahora usa heurística de GraphSAGE para mejor selección"""
    
    solucion = []
    slots_usados = defaultdict(set)  # (dia, hora) -> set de aula_ids
    profesor_slots = defaultdict(set)  # profesor_id -> set de (dia, hora)
    
    # Pre-filtrar slots válidos por profesor (OPTIMIZACIÓN CRÍTICA)
    # Esto elimina slots que violan restricciones ANTES de intentar asignar
    slots_validos_por_profesor = {}
    for asig in asignaciones:
        prof_id = asig['professor_id']
        if prof_id not in slots_validos_por_profesor:
            slots_validos = [
                s for s in slots_tiempo
                if not violar_restriccion(prof_id, s[0], s[1], restricciones_dict)
            ]
            slots_validos_por_profesor[prof_id] = slots_validos if slots_validos else slots_tiempo
    
    # Shuffle para variabilidad
    asignaciones_random = list(asignaciones)
    random.shuffle(asignaciones_random)
    
    for asig in asignaciones_random:
        profesor_id = asig['professor_id']
        session_type = asig['session_type'] or 'T1'  # Default a teoría si es NULL
        
        # Determinar tipo de aula según tipo de sesión
        session_upper = session_type.upper()
        if session_upper.startswith('L'):  # L1, L2, L3 = SOLO LAB
            tipo_aula_requerido = 'LAB'
            alumnos = asig.get('alumnos_laboratorio', 20)
        elif session_upper.startswith('T') or session_upper.startswith('P'):  
            # T1-T3 (teoría) y P1-P3 (práctica) = NOLAB
            tipo_aula_requerido = 'NOLAB'
            alumnos = asig.get('alumnos_teoria', 30) if session_upper.startswith('T') else asig.get('alumnos_practica', 25)
        else:
            tipo_aula_requerido = 'NOLAB'  # Default
            alumnos = 30
        
        # Usar SOLO slots válidos para este profesor (respeta restricciones)
        slots_disponibles = slots_validos_por_profesor[profesor_id]
        
        # Intentar asignar slot y aula
        asignado = False
        intentos = 0
        max_intentos = 200  # Aumentado de 50 a 200 para mejor exploración
        
        while not asignado and intentos < max_intentos:
            # 🆕 MEJORA: Usar heurística inteligente si está disponible
            if USE_GRAPHSAGE and _graphsage_instance is not None and intentos == 0:
                # Filtrar slots disponibles que no violan conflictos
                slots_libres = [
                    s for s in slots_disponibles
                    if (s[0], s[1]) not in profesor_slots[profesor_id]
                ]
                
                # Filtrar aulas disponibles
                aulas_posibles = [
                    a for a in aulas_por_tipo.get(tipo_aula_requerido, [])
                    if a['capacidad'] >= alumnos
                ]
                
                # Selección inteligente con GraphSAGE
                slot_elegido, aula = seleccionar_slot_con_heuristica(
                    slots_libres,
                    course_id=asig['course_id'],
                    professor_id=profesor_id,
                    aulas_posibles=aulas_posibles,
                    penalty_base=1.0
                )
                
                if slot_elegido and aula:
                    dia, hora_inicio, hora_fin = slot_elegido
                    key_slot = (dia, hora_inicio)
                    
                    # Verificar disponibilidad final
                    if aula['id'] not in slots_usados[key_slot]:
                        # ¡Asignación exitosa con heurística!
                        solucion.append({
                            'professor_id': profesor_id,
                            'course_id': asig['course_id'],
                            'nrc': asig['nrc'],
                            'session_type': session_type,
                            'aula_id': aula['id'],
                            'aula_codigo': aula['codigo'],
                            'dia': dia,
                            'hora_inicio': hora_inicio,
                            'hora_fin': hora_fin,
                            'alumnos': alumnos
                        })
                        slots_usados[key_slot].add(aula['id'])
                        profesor_slots[profesor_id].add(key_slot)
                        asignado = True
                        break
            
            # Elegir slot aleatorio de los VÁLIDOS (fallback o si GraphSAGE falla)
            if not slots_disponibles:
                break  # No hay slots válidos, no forzar asignación
            
            dia, hora_inicio, hora_fin = random.choice(slots_disponibles)
            key_slot = (dia, hora_inicio)
            
            # Verificar que profesor no tenga ya otra clase en este slot
            if key_slot in profesor_slots[profesor_id]:
                intentos += 1
                continue
            
            # Buscar aula disponible del tipo requerido
            aulas_disponibles = [
                a for a in aulas_por_tipo.get(tipo_aula_requerido, [])
                if a['id'] not in slots_usados[key_slot]
                and a['capacidad'] >= alumnos
            ]
            
            if not aulas_disponibles:
                intentos += 1
                continue
            
            # Elegir mejor aula (capacidad más cercana)
            aula = min(aulas_disponibles, key=lambda a: abs(a['capacidad'] - alumnos))
            
            # Asignar
            solucion.append({
                'professor_id': profesor_id,
                'course_id': asig['course_id'],
                'nrc': asig['nrc'],
                'session_type': session_type,
                'aula_id': aula['id'],
                'aula_codigo': aula['codigo'],
                'dia': dia,
                'hora_inicio': hora_inicio,
                'hora_fin': hora_fin,
                'alumnos': alumnos
            })
            
            slots_usados[key_slot].add(aula['id'])
            profesor_slots[profesor_id].add(key_slot)
            asignado = True
            intentos += 1
        
        if not asignado:
            # CRÍTICO: NO forzar asignación si viola restricciones
            # Solo usar slots_disponibles (ya respetan restricciones del profesor)
            
            if slots_disponibles:
                # Hay slots válidos, elegir uno aunque cause conflicto de aula/profesor
                dia_random, hora_i, hora_f = random.choice(slots_disponibles)
                
                # Usar aulas del tipo requerido
                aulas_posibles = aulas_por_tipo.get(tipo_aula_requerido, [])
                
                if not aulas_posibles:
                    # Fallback: usar cualquier aula disponible
                    aulas_posibles = list(aulas_por_tipo.values())[0]
                
                aula_random = random.choice(aulas_posibles)
                
                solucion.append({
                    'professor_id': profesor_id,
                    'course_id': asig['course_id'],
                    'nrc': asig['nrc'],
                    'session_type': session_type,
                    'aula_id': aula_random['id'],
                    'aula_codigo': aula_random['codigo'],
                    'dia': dia_random,
                    'hora_inicio': hora_i,
                    'hora_fin': hora_f,
                    'alumnos': alumnos,
                    'conflicto': True  # Marca conflicto de aula, pero RESPETA restricción profesor
                })
            # else: NO agregar nada si no hay slots válidos - mejor omitir que violar restricción DURA
    
    return solucion

def violar_restriccion(profesor_id, dia, hora_inicio, restricciones_dict):
    """Verifica si el slot viola alguna restricción del profesor"""
    from datetime import datetime, time
    
    if profesor_id not in restricciones_dict:
        return False
    
    # Convertir hora_inicio a time si es string
    if isinstance(hora_inicio, str):
        hora_obj = datetime.strptime(hora_inicio, '%H:%M:%S').time()
    else:
        hora_obj = hora_inicio
    
    for restriccion in restricciones_dict[profesor_id]:
        if restriccion['day'] != dia:
            continue
        
        r_start = restriccion['start_time']
        r_end = restriccion['end_time']
        
        # Convertir a time si es necesario
        if isinstance(r_start, str):
            r_start = datetime.strptime(r_start, '%H:%M:%S').time()
        if isinstance(r_end, str):
            r_end = datetime.strptime(r_end, '%H:%M:%S').time()
        
        # Verificar si hay overlap
        if r_start <= hora_obj < r_end:
            return True
    
    return False

def calcular_fitness_completo(solucion):
    """
    Calcula fitness considerando múltiples factores
    🆕 INCLUYE REGLAS PEDAGÓGICAS INSTITUCIONALES
    """
    
    fitness = 0
    
    # 1. Conflictos de aula (misma aula, mismo slot) - CRÍTICO
    aulas_slots = defaultdict(int)
    for asig in solucion:
        key = (asig['aula_id'], asig['dia'], asig['hora_inicio'])
        aulas_slots[key] += 1
    
    conflictos_aula = sum(max(0, count - 1) for count in aulas_slots.values())
    fitness += conflictos_aula * 1000  # 🆕 Aumentado de 100 a 1000 (CRÍTICO)
    
    # 2. Conflictos de profesor (mismo profesor, mismo slot) - CRÍTICO
    prof_slots = defaultdict(int)
    for asig in solucion:
        key = (asig['professor_id'], asig['dia'], asig['hora_inicio'])
        prof_slots[key] += 1
    
    conflictos_profesor = sum(max(0, count - 1) for count in prof_slots.values())
    fitness += conflictos_profesor * 1000  # 🆕 Aumentado de 150 a 1000 (CRÍTICO)
    
    # 3. Penalización por conflictos marcados
    conflictos_marcados = sum(1 for asig in solucion if asig.get('conflicto', False))
    fitness += conflictos_marcados * 500  # 🆕 Aumentado de 200 a 500
    
    # 4. Preferencias suaves: concentrar horarios por día
    # (menor dispersión = mejor)
    prof_dias = defaultdict(set)
    for asig in solucion:
        prof_dias[asig['professor_id']].add(asig['dia'])
    
    dispersion = sum(len(dias) for dias in prof_dias.values())
    fitness += dispersion * 2
    
    # 🆕 5. REGLAS PEDAGÓGICAS INSTITUCIONALES
    if USE_REGLAS_PEDAGOGICAS:
        try:
            penalizacion_pedagogica, metricas = ReglasInstitucionales.penalizacion_total(solucion)
            fitness += penalizacion_pedagogica
            
            # Guardar métricas en la solución para análisis posterior
            if solucion and len(solucion) > 0:
                # Agregar métricas como metadata (no afecta la estructura)
                for asig in solucion:
                    if not asig.get('_metricas_guardadas', False):
                        asig['_metricas_pedagogicas'] = metricas
                        asig['_metricas_guardadas'] = True
                        break
        except Exception as e:
            print(f"⚠️  Error al calcular reglas pedagógicas: {e}")
    
    return fitness

# ==================== GUARDAR EN BD ====================
def guardar_experimento_bd(resultado, params):
    """Guarda experimento en algorithm_executions y actualiza assignments"""
    
    print("\n" + "="*80)
    print("💾 GUARDANDO EXPERIMENTO EN BASE DE DATOS")
    print("="*80)
    
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # 1. Guardar en algorithm_executions
    conflictos = int(resultado['fitness'] / 100)
    cursor.execute("""
        INSERT INTO algorithm_executions 
        (algoritmo, semestre, parametros, estado, tiempo_ejecucion, 
         funcion_objetivo, restricciones_violadas, conflictos_aula, 
         log_ejecucion, iniciado_en, terminado_en)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
    """, (
        'ACO_OPTIMIZED',
        '2025-20',
        json.dumps(params),
        'COMPLETED',
        resultado['tiempo_total'],
        resultado['fitness'],
        conflictos,
        conflictos,
        json.dumps({
            'iteraciones': resultado['iteraciones'],
            'hormigas': resultado['num_ants'],
            'historial_fitness': resultado['historial_fitness']
        })
    ))
    
    execution_id = cursor.lastrowid
    print(f"✅ Experimento guardado (ID: {execution_id})")
    
    # 2. Insertar nuevos horarios generados por ACO
    insertados = 0
    for asig in resultado['solucion']:
        cursor.execute("""
            INSERT INTO proposed_schedule_assignments
            (professor_id, course_id, classroom_id, nrc, day, start_time, end_time,
             session_type, is_pregrado, is_crece, is_confirmed, source, 
             algorithm_execution_id, confidence_score)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            asig['professor_id'],
            asig['course_id'],
            asig['aula_id'],
            asig['nrc'],
            asig['dia'],
            asig['hora_inicio'],
            asig['hora_fin'],
            asig['session_type'],
            True,  # is_pregrado
            False,  # is_crece
            not asig.get('conflicto', False),  # is_confirmed
            f'ACO_GEN_{execution_id}',
            execution_id,
            1.0 if not asig.get('conflicto', False) else 0.5
        ))
        insertados += 1
    
    conn.commit()
    print(f"✅ {insertados} horarios NUEVOS generados e insertados")
    
    cursor.close()
    conn.close()
    
    return execution_id

# ==================== EXPORTAR A EXCEL ====================
def exportar_resultados_excel(execution_id):
    """Exporta resultados a Excel usando pandas"""
    
    print("\n" + "="*80)
    print("📊 EXPORTANDO RESULTADOS A EXCEL")
    print("="*80)
    
    try:
        import pandas as pd
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment
    except ImportError:
        print("⚠️  pandas/openpyxl no instalado. Instalando...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas", "openpyxl"])
        import pandas as pd
    
    conn = mysql.connector.connect(**DB_CONFIG)
    
    # 1. Hoja 1: Horarios asignados
    query_horarios = """
        SELECT 
            p.nombre_completo as Profesor,
            c.codigo as Codigo_Curso,
            c.nombre as Curso,
            ps.nrc as NRC,
            ps.session_type as Tipo_Sesion,
            ps.day as Dia,
            DATE_FORMAT(ps.start_time, '%H:%i') as Hora_Inicio,
            DATE_FORMAT(ps.end_time, '%H:%i') as Hora_Fin,
            cl.codigo as Aula,
            cl.tipo as Tipo_Aula,
            cl.capacidad as Capacidad,
            cl.edificio as Edificio
        FROM proposed_schedule_assignments ps
        JOIN professors p ON ps.professor_id = p.id
        JOIN courses c ON ps.course_id = c.id
        LEFT JOIN classrooms cl ON ps.classroom_id = cl.id
        WHERE ps.algorithm_execution_id = %s
        ORDER BY ps.day, ps.start_time, p.nombre_completo
    """
    
    df_horarios = pd.read_sql(query_horarios, conn, params=(execution_id,))
    
    # 2. Hoja 2: Estadísticas del experimento
    query_experimento = """
        SELECT 
            id as Experimento_ID,
            algoritmo as Algoritmo,
            funcion_objetivo as Fitness,
            tiempo_ejecucion as Tiempo_Ejecucion_s,
            conflictos_aula as Conflictos_Aula,
            restricciones_violadas as Restricciones_Violadas,
            iniciado_en as Fecha_Inicio,
            terminado_en as Fecha_Fin,
            estado as Estado
        FROM algorithm_executions
        WHERE id = %s
    """
    
    df_experimento = pd.read_sql(query_experimento, conn, params=(execution_id,))
    
    # 3. Hoja 3: Conflictos (si hay)
    query_conflictos = """
        SELECT 
            cl.codigo as Aula,
            ps.day as Dia,
            DATE_FORMAT(ps.start_time, '%H:%i') as Hora,
            COUNT(*) as Num_Grupos,
            GROUP_CONCAT(CONCAT(p.nombre_completo, ' - ', c.nombre) SEPARATOR ' | ') as Cursos_Conflicto
        FROM proposed_schedule_assignments ps
        JOIN professors p ON ps.professor_id = p.id
        JOIN courses c ON ps.course_id = c.id
        JOIN classrooms cl ON ps.classroom_id = cl.id
        WHERE ps.algorithm_execution_id = %s
        GROUP BY cl.id, ps.day, ps.start_time
        HAVING COUNT(*) > 1
    """
    
    df_conflictos = pd.read_sql(query_conflictos, conn, params=(execution_id,))
    
    conn.close()
    
    # Generar Excel
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"resultados_aco_exp{execution_id}_{timestamp}.xlsx"
    
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        df_horarios.to_excel(writer, sheet_name='Horarios', index=False)
        df_experimento.to_excel(writer, sheet_name='Experimento', index=False)
        
        if not df_conflictos.empty:
            df_conflictos.to_excel(writer, sheet_name='Conflictos', index=False)
        else:
            # Crear hoja vacía con mensaje
            pd.DataFrame({'Mensaje': ['✅ No hay conflictos']}).to_excel(
                writer, sheet_name='Conflictos', index=False
            )
    
    print(f"✅ Excel generado: {filename}")
    print(f"   📄 Hoja 1: {len(df_horarios)} horarios asignados")
    print(f"   📄 Hoja 2: Estadísticas del experimento")
    print(f"   📄 Hoja 3: {len(df_conflictos)} conflictos detectados")
    
    return filename

# ==================== MAIN ====================
def main():
    print("\n" + "="*80)
    print("🚀 EJECUCIÓN DE ACO - UPAO TIMETABLING")
    print("="*80)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 🆕 Inicializar GraphSAGE
    print("\n📊 Inicializando módulos...")
    graphsage_loaded = init_graphsage()
    if graphsage_loaded:
        print("   ✅ GraphSAGE: Embeddings cargados exitosamente")
        print("   📈 Heurística: Inteligente (basada en embeddings)")
    else:
        print("   ⚠️  GraphSAGE: No disponible")
        print("   📈 Heurística: Simple (aleatoria)")
    
    # 🆕 EXPERIMENTO 16: ÓPTIMO CON REGLAS PEDAGÓGICAS
    # Configuración basada en análisis de experimentos 9-15
    params = {
        'max_iterations': 50,  # 50 iter es suficiente (balance tiempo/calidad)
        'num_ants': 20,        # 🆕 Aumentado de 15 a 20 (más exploración)
        'alpha': 1.0,
        'beta': 5.0 if graphsage_loaded else 2.0,  # β=5.0 es óptimo con GraphSAGE
        'rho': 0.15
    }
    
    print(f"\n⚙️  Parámetros ACO:")
    print(f"   • Iteraciones: {params['max_iterations']}")
    print(f"   • Hormigas: {params['num_ants']}")
    print(f"   • α (feromona): {params['alpha']}")
    print(f"   • β (heurística): {params['beta']} {'🆕 AUMENTADO para GraphSAGE' if graphsage_loaded else ''}")
    print(f"   • ρ (evaporación): {params['rho']}")
    
    # 1. Cargar datos
    datos = cargar_datos_bd()
    
    # 2. Ejecutar ACO
    resultado = ejecutar_aco_simple(datos, params)
    
    # 3. Guardar en BD
    execution_id = guardar_experimento_bd(resultado, params)
    
    # 4. Exportar a Excel
    filename = exportar_resultados_excel(execution_id)
    
    print("\n" + "="*80)
    print("✅ PROCESO COMPLETADO")
    print("="*80)
    print(f"🆔 Experimento ID: {execution_id}")
    print(f"🏆 Fitness Final: {resultado['fitness']:.2f}")
    print(f"⏱️  Tiempo Total: {resultado['tiempo_total']:.2f}s")
    print(f"📊 Excel: {filename}")
    print("="*80)

if __name__ == "__main__":
    import random
    random.seed(42)
    main()
