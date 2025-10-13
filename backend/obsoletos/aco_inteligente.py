"""
ACO INTELIGENTE - Balance entre agresividad y eficiencia
=======================================================
Estrategia: Probar combinaciones pero con heurísticas inteligentes
"""

import random
from collections import defaultdict
from datetime import datetime, time

def aco_inteligente(secciones, profesores, aulas_por_tipo, slots_tiempo, restricciones_dict, 
                    num_hormigas=30, max_iteraciones=50):
    """
    ACO que maximiza asignaciones usando heurísticas inteligentes
    """
    
    print(f"\n{'='*80}")
    print(f"🧠 ACO INTELIGENTE - HEURÍSTICAS + EXPLORACIÓN")
    print(f"{'='*80}")
    print(f"⚙️  {num_hormigas} hormigas × {max_iteraciones} iteraciones")
    print(f"📊 Secciones a asignar: {len(secciones)}")
    
    prof_ids = [p['id'] for p in profesores]
    
    mejor_solucion = []
    mejor_asignadas = 0
    
    historial_asignadas = []
    
    for iter_num in range(1, max_iteraciones + 1):
        soluciones_hormigas = []
        
        for _ in range(num_hormigas):
            solucion = construir_solucion_inteligente(
                secciones, prof_ids, aulas_por_tipo, slots_tiempo, restricciones_dict
            )
            soluciones_hormigas.append(solucion)
        
        # Evaluar hormigas
        for sol in soluciones_hormigas:
            asignadas = len(sol)
            if asignadas > mejor_asignadas:
                mejor_asignadas = asignadas
                mejor_solucion = sol
        
        asignadas_iter = [len(s) for s in soluciones_hormigas]
        promedio_asig = sum(asignadas_iter) / len(asignadas_iter)
        max_iter = max(asignadas_iter)
        
        historial_asignadas.append(promedio_asig)
        
        print(f"  Iter {iter_num:2d}/{max_iteraciones} | "
              f"Mejor: {mejor_asignadas}/{len(secciones)} | "
              f"Max iter: {max_iter} | "
              f"Promedio: {promedio_asig:.1f}")
    
    print(f"{'='*80}")
    print(f"✅ MEJOR SOLUCIÓN: {mejor_asignadas}/{len(secciones)} asignadas "
          f"({100*mejor_asignadas/len(secciones):.1f}%)")
    print(f"{'='*80}\n")
    
    return mejor_solucion, historial_asignadas, []


def construir_solucion_inteligente(secciones, prof_ids, aulas_por_tipo, slots_tiempo, restricciones_dict):
    """
    Construye solución usando heurísticas inteligentes
    
    HEURÍSTICAS:
    1. Profesores con menos carga tienen prioridad
    2. Teorías/Prácticas preferir Lun-Jue
    3. Slots tempranos mejor que tardíos
    4. Aulas con capacidad ajustada
    5. Si falla, relajar restricciones progresivamente
    """
    
    solucion = []
    profesor_slots = defaultdict(set)
    slots_usados = defaultdict(set)
    prof_carga = defaultdict(int)
    
    # Ordenar: T → P → L
    secciones_ordenadas = sorted(secciones, key=lambda x: (
        {'T': 0, 'P': 1, 'L': 2}.get(x['session_type'][0], 3),
        x['course_name']
    ))
    
    # Pre-calcular disponibilidad de profesores
    prof_disponibilidad = {}
    for prof_id in prof_ids:
        slots_sin_restriccion = [
            s for s in slots_tiempo
            if not violar_restriccion(prof_id, s[0], s[1], restricciones_dict)
        ]
        prof_disponibilidad[prof_id] = slots_sin_restriccion
    
    # Ordenar profesores por disponibilidad (más disponibles primero)
    prof_ordenados = sorted(prof_ids, 
                           key=lambda p: len(prof_disponibilidad[p]),
                           reverse=True)
    
    for seccion in secciones_ordenadas:
        tipo_sesion = seccion['session_type'][0]
        tipo_aula = 'LAB' if tipo_sesion == 'L' else 'NOLAB'
        alumnos = seccion.get('alumnos', 30)
        
        asignado = False
        
        # ESTRATEGIA NIVEL 0: Heurísticas inteligentes
        # Probar profesores en orden de disponibilidad
        for prof_id in prof_ordenados:
            if asignado:
                break
            
            # Limitar carga
            if prof_carga[prof_id] >= 40:
                continue
            
            # Slots disponibles para este profesor
            slots_candidatos = prof_disponibilidad.get(prof_id, [])
            
            # Priorizar slots según tipo de sesión
            if tipo_sesion in ['T', 'P']:
                # Preferir Lun-Jue
                slots_prioritarios = [s for s in slots_candidatos 
                                     if s[0] in ['LUNES', 'MARTES', 'MIERCOLES', 'JUEVES']]
                if not slots_prioritarios:
                    slots_prioritarios = slots_candidatos
            else:
                slots_prioritarios = slots_candidatos
            
            # Ordenar por hora (más temprano mejor)
            slots_prioritarios = sorted(slots_prioritarios, 
                                       key=lambda s: (s[0], s[1]))
            
            # Probar cada slot
            for slot in slots_prioritarios[:20]:  # Limitar a 20 mejores
                dia, h_ini, h_fin = slot
                key_slot = (dia, h_ini)
                
                # ¿Profesor ocupado?
                if key_slot in profesor_slots[prof_id]:
                    continue
                
                # Buscar aula disponible
                aulas_libres = [
                    a for a in aulas_por_tipo.get(tipo_aula, [])
                    if a['id'] not in slots_usados[key_slot]
                    and a['capacidad'] >= alumnos
                ]
                
                if not aulas_libres:
                    continue
                
                # Elegir aula con mejor ajuste
                aula = min(aulas_libres, key=lambda a: abs(a['capacidad'] - alumnos))
                
                # ASIGNAR
                solucion.append({
                    'course_id': seccion['course_id'],
                    'course_name': seccion['course_name'],
                    'session_type': seccion['session_type'],
                    'professor_id': prof_id,
                    'day': dia,
                    'start_time': h_ini,
                    'end_time': h_fin,
                    'classroom_id': aula['id'],
                    'classroom_codigo': aula['codigo'],
                    'alumnos': alumnos
                })
                
                profesor_slots[prof_id].add(key_slot)
                slots_usados[key_slot].add(aula['id'])
                prof_carga[prof_id] += 2
                
                asignado = True
                break
        
        # FALLBACK NIVEL 1: Ignorar restricciones pero mantener orden
        if not asignado:
            for prof_id in prof_ordenados:
                if asignado:
                    break
                
                if prof_carga[prof_id] >= 50:  # Límite más flexible
                    continue
                
                # Probar TODOS los slots (sin restricciones)
                for slot in slots_tiempo[:30]:  # Limitar a 30
                    dia, h_ini, h_fin = slot
                    key_slot = (dia, h_ini)
                    
                    if key_slot in profesor_slots[prof_id]:
                        continue
                    
                    aulas_libres = [
                        a for a in aulas_por_tipo.get(tipo_aula, [])
                        if a['id'] not in slots_usados[key_slot]
                        and a['capacidad'] >= alumnos
                    ]
                    
                    if not aulas_libres:
                        continue
                    
                    aula = aulas_libres[0]
                    
                    solucion.append({
                        'course_id': seccion['course_id'],
                        'course_name': seccion['course_name'],
                        'session_type': seccion['session_type'],
                        'professor_id': prof_id,
                        'day': dia,
                        'start_time': h_ini,
                        'end_time': h_fin,
                        'classroom_id': aula['id'],
                        'classroom_codigo': aula['codigo'],
                        'alumnos': alumnos
                    })
                    
                    profesor_slots[prof_id].add(key_slot)
                    slots_usados[key_slot].add(aula['id'])
                    prof_carga[prof_id] += 2
                    
                    asignado = True
                    break
        
        # FALLBACK NIVEL 2: Explorar más profesores aleatoriamente
        if not asignado:
            prof_aleatorios = random.sample(prof_ids, min(10, len(prof_ids)))
            
            for prof_id in prof_aleatorios:
                if asignado:
                    break
                
                slots_aleatorios = random.sample(slots_tiempo, min(20, len(slots_tiempo)))
                
                for slot in slots_aleatorios:
                    dia, h_ini, h_fin = slot
                    key_slot = (dia, h_ini)
                    
                    if key_slot in profesor_slots[prof_id]:
                        continue
                    
                    aulas_libres = [
                        a for a in aulas_por_tipo.get(tipo_aula, [])
                        if a['id'] not in slots_usados[key_slot]
                        and a['capacidad'] >= alumnos
                    ]
                    
                    if not aulas_libres:
                        continue
                    
                    aula = aulas_libres[0]
                    
                    solucion.append({
                        'course_id': seccion['course_id'],
                        'course_name': seccion['course_name'],
                        'session_type': seccion['session_type'],
                        'professor_id': prof_id,
                        'day': dia,
                        'start_time': h_ini,
                        'end_time': h_fin,
                        'classroom_id': aula['id'],
                        'classroom_codigo': aula['codigo'],
                        'alumnos': alumnos
                    })
                    
                    profesor_slots[prof_id].add(key_slot)
                    slots_usados[key_slot].add(aula['id'])
                    prof_carga[prof_id] += 2
                    
                    asignado = True
                    break
    
    return solucion


def violar_restriccion(profesor_id, dia, hora_inicio, restricciones_dict):
    """Verifica si el profesor tiene restricción en (día, hora)"""
    if profesor_id not in restricciones_dict:
        return False
    
    for restriccion in restricciones_dict[profesor_id]:
        if restriccion['dia'].upper() == dia.upper():
            # Convertir todo a time objects
            if isinstance(hora_inicio, time):
                h_ini = hora_inicio
            elif isinstance(hora_inicio, str):
                h_ini = datetime.strptime(hora_inicio, '%H:%M:%S').time()
            else:
                h_ini = hora_inicio
            
            # Asegurar que las restricciones también sean time
            if isinstance(restriccion['hora_inicio'], str):
                r_inicio = datetime.strptime(restriccion['hora_inicio'], '%H:%M:%S').time()
            else:
                r_inicio = restriccion['hora_inicio']
            
            if isinstance(restriccion['hora_fin'], str):
                r_fin = datetime.strptime(restriccion['hora_fin'], '%H:%M:%S').time()
            else:
                r_fin = restriccion['hora_fin']
            
            if r_inicio <= h_ini < r_fin:
                return True
    
    return False
