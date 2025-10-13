"""
ACO Simple con Context-Aware Scheduling + Local Search Post-Processing
Versión optimizada con búsqueda local para mejorar T→P→L después de ACO
"""
import random
from datetime import datetime, time
from collections import defaultdict

def construir_solucion_aco_simple(datos, alfa=1.0, beta=2.0):
    """
    Construye una solución usando ACO con context-aware scheduling
    """
    secciones = datos['secciones']
    slots_tiempo = datos['slots_tiempo']
    profesores = datos['profesores']
    disponibilidad_prof = datos['disponibilidad_prof']
    aulas = datos['aulas']
    secciones_por_curso = datos['secciones_por_curso']
    
    solucion = []
    ocupacion_aula = defaultdict(set)
    ocupacion_profesor = defaultdict(set)
    secciones_restantes = secciones.copy()
    
    # Context-aware: rastrear último slot asignado por curso
    ultimo_slot_por_curso = {}  # {course_id: (dia_num, hora_obj)}
    dias_num = {'LUNES': 1, 'MARTES': 2, 'MIÉRCOLES': 3, 'JUEVES': 4, 'VIERNES': 5, 'SÁBADO': 6}
    
    # Ordenar secciones por CURSO y TIPO
    secciones_ordenadas = sorted(secciones, key=lambda x: (
        x['course_name'],  # Primero: agrupar por curso
        {'T': 0, 'P': 1, 'L': 2}.get(x['session_type'][0], 3),  # Segundo: tipo T→P→L
        random.random()  # Tercero: exploración
    ))
    
    # Ordenar slots por día y hora
    slots_ordenados = sorted(slots_tiempo, key=lambda x: (
        dias_num.get(x[0], 0),
        x[1]
    ))
    
    for idx, seccion in enumerate(secciones_ordenadas):
        if idx % 50 == 0:
            print(f"    [Procesando sección {idx+1}/{len(secciones_ordenadas)} - Asignadas: {len(solucion)}]")
        
        course_id = seccion['course_id']
        session_type = seccion['session_type']
        
        # Buscar profesores del curso
        prof_ids = [p['id'] for p in profesores if p.get('course_id') == course_id or course_id in p.get('course_ids', [])]
        if not prof_ids:
            prof_ids = [p['id'] for p in profesores]  # Fallback: todos los profesores
        
        # Duración: 2h para teoría, 2h para práctica, 2h para lab
        duracion = 2
        
        # Context-aware: obtener último slot de este curso
        ultimo_ts = ultimo_slot_por_curso.get(course_id, (0, time(0,0)))
        
        # Filtrar slots válidos (solo aquellos DESPUÉS del último slot)
        slots_validos = []
        for slot in slots_ordenados:
            dia, h_ini, h_fin = slot
            dia_num = dias_num.get(dia, 0)
            hora_obj = datetime.strptime(h_ini, '%H:%M:%S').time()
            slot_ts = (dia_num, hora_obj)
            
            if slot_ts > ultimo_ts:
                slots_validos.append(slot)
        
        # Fallback: si no hay slots válidos, usar todos
        if not slots_validos:
            slots_validos = slots_ordenados
        
        # Determinar aula según tipo
        if session_type[0] == 'L':
            aulas_candidatas = [a for a in aulas if a['classroom_type'] == 'LABORATORIO']
        else:
            aulas_candidatas = [a for a in aulas if a['classroom_type'] in ('AULA', 'AUDITORIO')]
        
        if not aulas_candidatas:
            continue
        
        # Intentar asignar
        asignada = False
        random.shuffle(prof_ids)
        
        for prof_id in prof_ids:
            if asignada:
                break
            
            for slot in slots_validos:
                dia, h_ini, h_fin = slot
                
                # Verificar disponibilidad profesor
                if (prof_id, dia, h_ini) not in disponibilidad_prof:
                    continue
                
                # Verificar conflictos profesor
                if (dia, h_ini) in ocupacion_profesor[prof_id]:
                    continue
                
                # Intentar con aulas
                random.shuffle(aulas_candidatas)
                for aula in aulas_candidatas:
                    classroom_id = aula['id']
                    
                    # Verificar conflictos aula
                    if (dia, h_ini) in ocupacion_aula[classroom_id]:
                        continue
                    
                    # ASIGNAR
                    asignacion = {
                        'course_id': course_id,
                        'course_name': seccion['course_name'],
                        'session_type': session_type,
                        'professor_id': prof_id,
                        'classroom_id': classroom_id,
                        'day': dia,
                        'start_time': h_ini,
                        'end_time': h_fin,
                        'duration_hours': duracion
                    }
                    
                    solucion.append(asignacion)
                    ocupacion_aula[classroom_id].add((dia, h_ini))
                    ocupacion_profesor[prof_id].add((dia, h_ini))
                    
                    # Actualizar context
                    dia_num = dias_num.get(dia, 0)
                    hora_obj = datetime.strptime(h_ini, '%H:%M:%S').time()
                    ultimo_slot_por_curso[course_id] = (dia_num, hora_obj)
                    
                    asignada = True
                    break
                
                if asignada:
                    break
    
    print(f"    ✅ Total asignadas: {len(solucion)}/{len(secciones)}")
    print(f"    ❌ Total fallidas: {len(secciones) - len(solucion)}/{len(secciones)}")
    
    return solucion


def local_search_tpl_optimization(solucion, datos, max_intentos=100):
    """
    Búsqueda local para mejorar T→P→L intercambiando slots
    """
    print()
    print("🔍 INICIANDO LOCAL SEARCH PARA OPTIMIZAR T→P→L...")
    print()
    
    dias_num = {'LUNES': 1, 'MARTES': 2, 'MIÉRCOLES': 3, 'JUEVES': 4, 'VIERNES': 5, 'SÁBADO': 6}
    
    # Identificar violaciones T→P→L
    def encontrar_violaciones(sol):
        """Encuentra todas las violaciones T→P→L en la solución"""
        # Agrupar asignaciones por curso
        asignaciones_por_curso = defaultdict(list)
        for asig in sol:
            asignaciones_por_curso[asig['course_id']].append(asig)
        
        violaciones = []
        for course_id, asigs in asignaciones_por_curso.items():
            # Separar por tipo
            teorias = [a for a in asigs if a['session_type'][0] == 'T']
            practicas = [a for a in asigs if a['session_type'][0] == 'P']
            labs = [a for a in asigs if a['session_type'][0] == 'L']
            
            # Obtener timestamps
            def get_timestamp(asig):
                dia = asig['day']
                hora = asig['start_time']
                dia_num = dias_num.get(dia, 0)
                hora_obj = datetime.strptime(hora, '%H:%M:%S').time()
                return (dia_num, hora_obj)
            
            # Verificar T→P
            if teorias and practicas:
                ultima_teoria = max(teorias, key=get_timestamp)
                primera_practica = min(practicas, key=get_timestamp)
                if get_timestamp(ultima_teoria) >= get_timestamp(primera_practica):
                    violaciones.append({
                        'tipo': 'T→P',
                        'course_id': course_id,
                        'teoria': ultima_teoria,
                        'practica': primera_practica
                    })
            
            # Verificar P→L
            if practicas and labs:
                ultima_practica = max(practicas, key=get_timestamp)
                primer_lab = min(labs, key=get_timestamp)
                if get_timestamp(ultima_practica) >= get_timestamp(primer_lab):
                    violaciones.append({
                        'tipo': 'P→L',
                        'course_id': course_id,
                        'practica': ultima_practica,
                        'lab': primer_lab
                    })
            
            # Verificar T→L
            if teorias and labs:
                ultima_teoria = max(teorias, key=get_timestamp)
                primer_lab = min(labs, key=get_timestamp)
                if get_timestamp(ultima_teoria) >= get_timestamp(primer_lab):
                    violaciones.append({
                        'tipo': 'T→L',
                        'course_id': course_id,
                        'teoria': ultima_teoria,
                        'lab': primer_lab
                    })
        
        return violaciones
    
    # Función para validar si un swap es factible
    def validar_swap(sol, idx1, idx2):
        """Verifica si intercambiar slots de idx1 e idx2 es factible"""
        asig1 = sol[idx1]
        asig2 = sol[idx2]
        
        # Crear copia temporal
        sol_temp = sol.copy()
        
        # Intercambiar slots (día, hora, aula)
        sol_temp[idx1] = {
            **asig1,
            'day': asig2['day'],
            'start_time': asig2['start_time'],
            'end_time': asig2['end_time'],
            'classroom_id': asig2['classroom_id']
        }
        
        sol_temp[idx2] = {
            **asig2,
            'day': asig1['day'],
            'start_time': asig1['start_time'],
            'end_time': asig1['end_time'],
            'classroom_id': asig1['classroom_id']
        }
        
        # Verificar conflictos
        ocupacion_aula = defaultdict(set)
        ocupacion_profesor = defaultdict(set)
        
        for asig in sol_temp:
            slot_key = (asig['day'], asig['start_time'])
            
            # Conflicto aula
            if slot_key in ocupacion_aula[asig['classroom_id']]:
                return False
            ocupacion_aula[asig['classroom_id']].add(slot_key)
            
            # Conflicto profesor
            if slot_key in ocupacion_profesor[asig['professor_id']]:
                return False
            ocupacion_profesor[asig['professor_id']].add(slot_key)
        
        return True
    
    # Realizar búsqueda local
    mejor_solucion = solucion.copy()
    violaciones_iniciales = encontrar_violaciones(mejor_solucion)
    print(f"   📊 Violaciones iniciales: {len(violaciones_iniciales)}")
    
    mejoras = 0
    for intento in range(max_intentos):
        violaciones_actuales = encontrar_violaciones(mejor_solucion)
        
        if not violaciones_actuales:
            print(f"   🎉 ¡Todas las violaciones resueltas en intento {intento+1}!")
            break
        
        # Seleccionar una violación aleatoria
        violacion = random.choice(violaciones_actuales)
        
        # Identificar asignaciones involucradas
        if violacion['tipo'] == 'T→P':
            asig_temprana = violacion['practica']
            asig_tardia = violacion['teoria']
        elif violacion['tipo'] == 'P→L':
            asig_temprana = violacion['lab']
            asig_tardia = violacion['practica']
        else:  # T→L
            asig_temprana = violacion['lab']
            asig_tardia = violacion['teoria']
        
        # Buscar índices
        idx_temprana = mejor_solucion.index(asig_temprana)
        idx_tardia = mejor_solucion.index(asig_tardia)
        
        # Intentar swap
        if validar_swap(mejor_solucion, idx_temprana, idx_tardia):
            # Realizar swap
            asig1 = mejor_solucion[idx_temprana].copy()
            asig2 = mejor_solucion[idx_tardia].copy()
            
            mejor_solucion[idx_temprana] = {
                **asig1,
                'day': asig2['day'],
                'start_time': asig2['start_time'],
                'end_time': asig2['end_time'],
                'classroom_id': asig2['classroom_id']
            }
            
            mejor_solucion[idx_tardia] = {
                **asig2,
                'day': asig1['day'],
                'start_time': asig1['start_time'],
                'end_time': asig1['end_time'],
                'classroom_id': asig1['classroom_id']
            }
            
            mejoras += 1
            if mejoras % 10 == 0:
                print(f"   ✅ Mejoras aplicadas: {mejoras}")
    
    violaciones_finales = encontrar_violaciones(mejor_solucion)
    print()
    print(f"   📊 Violaciones finales: {len(violaciones_finales)}")
    print(f"   📈 Mejora: -{len(violaciones_iniciales) - len(violaciones_finales)} violaciones")
    print(f"   🔄 Total swaps realizados: {mejoras}")
    print()
    
    return mejor_solucion


if __name__ == '__main__':
    # Este archivo solo define las funciones
    # Se usa desde ejecutar_aco_con_proyecciones.py
    pass
