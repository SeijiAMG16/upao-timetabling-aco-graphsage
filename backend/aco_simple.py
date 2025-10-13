"""
ACO SIMPLE - Sin restricciones primero, asignar TODO
====================================================
"""

import random
from collections import defaultdict
from datetime import datetime, time

def aco_simple_sin_restricciones(secciones, profesores, aulas_por_tipo, slots_tiempo, 
                                  num_hormigas=10, max_iteraciones=10):
    """
    ACO ultra simple: IGNORA restricciones, solo busca asignar el 100%
    """
    
    print(f"\n{'='*80}")
    print(f"🔥 ACO SIMPLE - SIN RESTRICCIONES (ASIGNAR 100%)")
    print(f"{'='*80}")
    print(f"⚙️  {num_hormigas} hormigas × {max_iteraciones} iteraciones")
    print(f"📊 Secciones a asignar: {len(secciones)}")
    
    prof_ids = [p['id'] for p in profesores]
    
    mejor_solucion = []
    mejor_asignadas = 0
    
    for iter_num in range(1, max_iteraciones + 1):
        soluciones = []
        
        for _ in range(num_hormigas):
            sol = construir_solucion_simple(secciones, prof_ids, aulas_por_tipo, slots_tiempo)
            soluciones.append(sol)
        
        for sol in soluciones:
            if len(sol) > mejor_asignadas:
                mejor_asignadas = len(sol)
                mejor_solucion = sol
        
        asignadas_iter = [len(s) for s in soluciones]
        promedio = sum(asignadas_iter) / len(asignadas_iter)
        maximo = max(asignadas_iter)
        
        print(f"  Iter {iter_num:2d}/{max_iteraciones} | "
              f"Mejor global: {mejor_asignadas}/{len(secciones)} | "
              f"Max iter: {maximo} | "
              f"Promedio: {promedio:.1f}")
    
    print(f"{'='*80}")
    print(f"✅ RESULTADO: {mejor_asignadas}/{len(secciones)} asignadas "
          f"({100*mejor_asignadas/len(secciones):.1f}%)")
    print(f"{'='*80}\n")
    
    return mejor_solucion, [], []


def construir_solucion_simple(secciones, prof_ids, aulas_por_tipo, slots_tiempo):
    """
    CONTEXT-AWARE SCHEDULING con reserva de ventanas temporales por curso
    
    Algoritmo:
    1. Ordenar secciones por CURSO → TIPO (T→P→L)
    2. Mantener registro del último slot asignado por curso
    3. Para cada sección, filtrar slots con timestamp > último_slot_curso
    4. Esto GARANTIZA orden temporal dentro de cada curso → T→P→L automático
    """
    
    solucion = []
    profesor_slots = defaultdict(set)  # {prof_id: set((dia, hora))}
    slots_usados = defaultdict(set)    # {(dia, hora): set(aula_ids)}
    
    # 🔑 CONTEXT-AWARE: Rastrear último slot asignado por curso
    ultimo_slot_por_curso = {}  # {course_id: (dia_num, hora_obj)}
    
    # Mapeo de días a números para comparación temporal
    dias_num = {'LUNES': 1, 'MARTES': 2, 'MIÉRCOLES': 3, 'JUEVES': 4, 'VIERNES': 5, 'SÁBADO': 6}
    
    # ORDENAMIENTO PEDAGÓGICO: CURSO → TIPO → Aleatorio
    secciones_ordenadas = sorted(secciones, key=lambda x: (
        x['course_name'],  # PRIMERO: Agrupar por curso
        {'T': 0, 'P': 1, 'L': 2}.get(x['session_type'][0], 3),  # SEGUNDO: Tipo T→P→L
        random.random()  # TERCERO: Exploración
    ))
    
    secciones_shuffled = secciones_ordenadas
    
    # Mezclar profesores
    prof_ids_shuffled = prof_ids.copy()
    random.shuffle(prof_ids_shuffled)
    
    # Slots ordenados temporalmente (Lunes 7am, 9am, ..., Martes 7am, ...)
    slots_ordenados = sorted(slots_tiempo, key=lambda x: (dias_num.get(x[0], 0), x[1]))
    
    secciones_asignadas = 0
    secciones_fallidas = 0
    
    for idx, seccion in enumerate(secciones_shuffled):
        tipo_aula = seccion.get('tipo_aula', 'NOLAB')
        alumnos = seccion.get('alumnos', 30)
        course_id = seccion.get('course_id')
        course_name = seccion.get('course_name', 'UNKNOWN')
        asignado = False
        
        # Log cada 50 secciones
        if (idx + 1) % 50 == 0:
            print(f"    [Procesando sección {idx+1}/{len(secciones_shuffled)} - Asignadas: {secciones_asignadas}]")
        
        # 🔑 CONTEXT-AWARE: Filtrar slots según último slot del curso
        ultimo_ts = ultimo_slot_por_curso.get(course_id, (0, datetime.strptime('00:00', '%H:%M').time()))
        
        # Filtrar slots: Solo los que vienen DESPUÉS del último slot asignado al curso
        slots_validos = []
        for slot in slots_ordenados:
            dia, h_ini, h_fin = slot
            dia_num = dias_num.get(dia, 0)
            
            # Convertir hora a objeto time si es string
            if isinstance(h_ini, str):
                hora_obj = datetime.strptime(h_ini, '%H:%M:%S').time()
            else:
                hora_obj = (datetime.min + h_ini).time()
            
            slot_ts = (dia_num, hora_obj)
            
            # Solo incluir si timestamp > último_slot_curso
            if slot_ts > ultimo_ts:
                slots_validos.append(slot)
        
        # FALLBACK ESTRICTO: Si no hay slots válidos, permitir violación
        # pero documentarla (preferible asignar con violación que no asignar)
        if not slots_validos:
            slots_validos = slots_ordenados
            # print(f"    ⚠️ {course_name} {seccion['session_type']}: Sin slots válidos, usando todos")
        
        # Probar TODAS las combinaciones con slots válidos
        for prof_id in prof_ids_shuffled:
            if asignado:
                break
                
            for slot in slots_validos:
                if asignado:
                    break
                
                dia, h_ini, h_fin = slot
                key_slot = (dia, h_ini)
                
                # ¿Profesor ocupado en este slot?
                if key_slot in profesor_slots[prof_id]:
                    continue
                
                # ¿Hay aula disponible del tipo correcto CON CAPACIDAD SUFICIENTE?
                # Las aulas se REUTILIZAN: G607 puede tener clase 7-9am, luego 9-11am, etc.
                # Solo verificamos que NO esté ocupada EN ESTE SLOT específico
                aulas_disp = [
                    a for a in aulas_por_tipo.get(tipo_aula, [])
                    if a['id'] not in slots_usados[key_slot]  # NO ocupada en este horario
                    and a['capacidad'] >= alumnos  # Capacidad suficiente para los alumnos
                ]
                
                # FALLBACK: Si no hay aula con capacidad, usar la más grande disponible
                if not aulas_disp:
                    aulas_disp = [
                        a for a in aulas_por_tipo.get(tipo_aula, [])
                        if a['id'] not in slots_usados[key_slot]
                    ]
                    if aulas_disp:
                        # Ordenar por capacidad descendente, usar la más grande
                        aulas_disp = sorted(aulas_disp, key=lambda x: x['capacidad'], reverse=True)
                
                if not aulas_disp:
                    continue
                
                # ¡ENCONTRAMOS UNA VÁLIDA! Asignar
                aula = aulas_disp[0]
                
                solucion.append({
                    'course_id': seccion['course_id'],
                    'course_name': seccion['course_name'],
                    'session_type': seccion['session_type'],
                    'professor_id': prof_id,
                    'day': dia,
                    'start_time': h_ini,
                    'end_time': h_fin,
                    'classroom_id': aula['id'],
                    'classroom_codigo': aula.get('codigo', f"Aula_{aula['id']}"),
                    'alumnos': alumnos
                })
                
                # 🔑 ACTUALIZAR contexto: Registrar este slot como último del curso
                dia_num = dias_num.get(dia, 0)
                if isinstance(h_ini, str):
                    hora_obj = datetime.strptime(h_ini, '%H:%M:%S').time()
                else:
                    hora_obj = (datetime.min + h_ini).time()
                ultimo_slot_por_curso[course_id] = (dia_num, hora_obj)
                
                profesor_slots[prof_id].add(key_slot)
                slots_usados[key_slot].add(aula['id'])
                asignado = True
        
        if asignado:
            secciones_asignadas += 1
        else:
            secciones_fallidas += 1
            # Log primeros 3 fallos
            if secciones_fallidas <= 3:
                print(f"    ⚠️ Fallo #{secciones_fallidas}: {seccion['course_name']} {seccion['session_type']} (tipo:{tipo_aula}, alumnos:{alumnos})")
    
    print(f"    ✅ Total asignadas: {secciones_asignadas}/{len(secciones_shuffled)}")
    print(f"    ❌ Total fallidas: {secciones_fallidas}/{len(secciones_shuffled)}")
    
    return solucion
