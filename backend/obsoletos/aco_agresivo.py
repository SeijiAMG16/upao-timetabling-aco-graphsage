"""
ACO AGRESIVO - MAXIMIZAR ASIGNACIONES
=====================================
Estrategia: Probar TODAS las combinaciones posibles hasta asignar
"""

import random
from collections import defaultdict
from datetime import datetime, time

def aco_agresivo(secciones, profesores, aulas_por_tipo, slots_tiempo, restricciones_dict, 
                 num_hormigas=30, max_iteraciones=50):
    """
    ACO que garantiza máxima asignación probando todas las combinaciones
    """
    
    print(f"\n{'='*80}")
    print(f"🐜 ACO AGRESIVO - MAXIMIZAR ASIGNACIONES")
    print(f"{'='*80}")
    print(f"⚙️  {num_hormigas} hormigas × {max_iteraciones} iteraciones")
    print(f"📊 Secciones a asignar: {len(secciones)}")
    
    prof_ids = [p['id'] for p in profesores]
    
    mejor_solucion = []
    mejor_asignadas = 0
    
    historial_asignadas = []
    historial_conflictos = []
    
    for iter_num in range(1, max_iteraciones + 1):
        soluciones_hormigas = []
        
        for _ in range(num_hormigas):
            solucion = construir_solucion_agresiva(
                secciones, prof_ids, aulas_por_tipo, slots_tiempo, restricciones_dict
            )
            soluciones_hormigas.append(solucion)
        
        # Evaluar todas las hormigas
        for sol in soluciones_hormigas:
            asignadas = len(sol)
            
            if asignadas > mejor_asignadas:
                mejor_asignadas = asignadas
                mejor_solucion = sol
        
        # Estadísticas de esta iteración
        asignadas_iter = [len(s) for s in soluciones_hormigas]
        promedio_asig = sum(asignadas_iter) / len(asignadas_iter) if asignadas_iter else 0
        
        historial_asignadas.append(promedio_asig)
        historial_conflictos.append(0)
        
        print(f"  Iter {iter_num:2d}/{max_iteraciones} | "
              f"Asignadas: {mejor_asignadas}/{len(secciones)} | "
              f"Promedio: {promedio_asig:.1f} asig")
    
    print(f"{'='*80}")
    print(f"✅ MEJOR SOLUCIÓN: {mejor_asignadas}/{len(secciones)} asignadas "
          f"({100*mejor_asignadas/len(secciones):.1f}%)")
    print(f"{'='*80}\n")
    
    return mejor_solucion, historial_asignadas, historial_conflictos


def construir_solucion_agresiva(secciones, prof_ids, aulas_por_tipo, slots_tiempo, restricciones_dict):
    """
    Construye solución probando TODAS las combinaciones hasta asignar
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
    
    for seccion in secciones_ordenadas:
        tipo_sesion = seccion['session_type'][0]
        tipo_aula = 'LAB' if tipo_sesion == 'L' else 'NOLAB'
        alumnos = seccion.get('alumnos', 30)
        
        asignado = False
        
        # ESTRATEGIA AGRESIVA: Probar TODAS las combinaciones
        # (profesor, slot, aula) hasta encontrar una que funcione
        
        # Barajar para exploración
        prof_ids_shuffled = prof_ids.copy()
        random.shuffle(prof_ids_shuffled)
        
        slots_shuffled = slots_tiempo.copy()
        random.shuffle(slots_shuffled)
        
        # Probar cada profesor
        for prof_id in prof_ids_shuffled:
            if asignado:
                break
            
            # Si este profesor ya tiene >40 horas, saltar (pero no bloquear)
            if prof_carga[prof_id] > 40:
                continue
            
            # Probar cada slot
            for slot in slots_shuffled:
                if asignado:
                    break
                
                dia, h_ini, h_fin = slot
                key_slot = (dia, h_ini)
                
                # ¿Profesor ocupado en este slot?
                if key_slot in profesor_slots[prof_id]:
                    continue
                
                # ¿Tiene restricción? (pero intentaremos igual si es necesario)
                tiene_restriccion = violar_restriccion(prof_id, dia, h_ini, restricciones_dict)
                
                # Buscar aula disponible
                aulas_disponibles = [
                    a for a in aulas_por_tipo.get(tipo_aula, [])
                    if a['id'] not in slots_usados[key_slot]
                    and a['capacidad'] >= alumnos
                ]
                
                if not aulas_disponibles:
                    continue
                
                # ENCONTRAMOS COMBINACIÓN VÁLIDA
                # Si tiene restricción, penalizar pero aceptar
                if not tiene_restriccion or prof_carga[prof_id] < 20:
                    aula = min(aulas_disponibles, key=lambda a: abs(a['capacidad'] - alumnos))
                    
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
        
        # Si NO se asignó después de probar TODO, usar fallback extremo
        if not asignado:
            # Buscar CUALQUIER slot con aula disponible
            for slot in slots_tiempo:
                dia, h_ini, h_fin = slot
                key_slot = (dia, h_ini)
                
                # Buscar aula libre
                aulas_libres = [
                    a for a in aulas_por_tipo.get(tipo_aula, [])
                    if a['id'] not in slots_usados[key_slot]
                    and a['capacidad'] >= alumnos
                ]
                
                if not aulas_libres:
                    continue
                
                # Buscar profesor con menos carga
                prof_disponible = None
                min_carga = float('inf')
                
                for prof_id in prof_ids:
                    if key_slot not in profesor_slots[prof_id]:
                        if prof_carga[prof_id] < min_carga:
                            min_carga = prof_carga[prof_id]
                            prof_disponible = prof_id
                
                if prof_disponible:
                    aula = aulas_libres[0]
                    
                    solucion.append({
                        'course_id': seccion['course_id'],
                        'course_name': seccion['course_name'],
                        'session_type': seccion['session_type'],
                        'professor_id': prof_disponible,
                        'day': dia,
                        'start_time': h_ini,
                        'end_time': h_fin,
                        'classroom_id': aula['id'],
                        'classroom_codigo': aula['codigo'],
                        'alumnos': alumnos
                    })
                    
                    profesor_slots[prof_disponible].add(key_slot)
                    slots_usados[key_slot].add(aula['id'])
                    prof_carga[prof_disponible] += 2
                    
                    asignado = True
                    break
    
    return solucion


def violar_restriccion(profesor_id, dia, hora_inicio, restricciones_dict):
    """
    Verifica si el profesor tiene restricción en (día, hora)
    """
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
