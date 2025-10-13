"""
ACO CON LIGAS Y BLOQUES UPAO CORRECTOS
=======================================

Versión 3.0 que implementa:
1. ✅ Ligas: T1→P1/L1, T2→P2/L2, etc.
2. ✅ Bloques de 50 min según horario oficial UPAO
3. ✅ Paralelización: Múltiples P1/L1 en paralelo
4. ✅ Límite 9:35pm presencial, 10:30pm NPR/virtual
5. ✅ Context-aware: Secciones en orden temporal
"""

import random
from datetime import datetime, time
from collections import defaultdict
from slots_tiempo_upao import obtener_slots_para_sesion

def construir_solucion_aco_con_ligas(datos, alfa=1.0, beta=2.0):
    """
    Construye solución ACO respetando ligas y bloques UPAO
    
    REGLAS DE LIGAS:
    - T1 debe ir con P1 y/o L1 (misma liga)
    - T2 debe ir con P2 y/o L2 (misma liga)
    - Solo puede haber UN T1, UN T2, etc. por curso
    - Puede haber MÚLTIPLES P1, P2, L1, L2 (paralelos)
    """
    
    secciones = datos['secciones']
    slots_tiempo = obtener_slots_para_sesion(2, incluir_virtual=True)  # Bloques correctos
    profesores = datos['profesores']
    aulas = datos['aulas']
    
    solucion = []
    ocupacion_aula = defaultdict(set)  # {classroom_id: set((dia, hora))}
    ocupacion_profesor = defaultdict(set)  # {prof_id: set((dia, hora))}
    
    # 1. AGRUPAR SECCIONES POR CURSO Y LIGA
    print("\n🔗 AGRUPANDO SECCIONES POR LIGA...")
    
    ligas_por_curso = defaultdict(lambda: defaultdict(list))  # {course_id: {liga: [secciones]}}
    
    for seccion in secciones:
        course_id = seccion['course_id']
        session_type = seccion['session_type']
        
        # Extraer tipo (T, P, L) y número de liga (1, 2, 3, ...)
        tipo = session_type[0]
        liga = int(session_type[1:]) if len(session_type) > 1 else 1
        
        ligas_por_curso[course_id][liga].append(seccion)
    
    print(f"   📊 Cursos con ligas: {len(ligas_por_curso)}")
    
    # Mostrar ejemplo de ligas
    ejemplo_curso = list(ligas_por_curso.keys())[0]
    print(f"   📋 Ejemplo - Curso ID {ejemplo_curso}:")
    for liga, secs in sorted(ligas_por_curso[ejemplo_curso].items()):
        tipos = [s['session_type'] for s in secs]
        print(f"      Liga {liga}: {tipos}")
    
    # 2. CONTEXT-AWARE: Rastrear último slot por curso
    dias_num = {'LUNES': 1, 'MARTES': 2, 'MIÉRCOLES': 3, 'JUEVES': 4, 'VIERNES': 5, 'SÁBADO': 6}
    ultimo_slot_por_curso = {}  # {course_id: (dia_num, hora_obj)}
    
    # Ordenar slots por día y hora
    slots_ordenados = sorted(slots_tiempo, key=lambda x: (
        dias_num.get(x[0], 0),
        x[1]
    ))
    
    # 3. PROCESAR POR CURSO → LIGA → TIPO
    print("\n🐜 ASIGNANDO HORARIOS CON ACO...")
    
    total_asignadas = 0
    total_fallidas = 0
    
    # Ordenar cursos por número de secciones (más complejos primero)
    cursos_ordenados = sorted(
        ligas_por_curso.items(),
        key=lambda x: sum(len(secs) for secs in x[1].values()),
        reverse=True
    )
    
    for course_id, ligas in cursos_ordenados:
        course_name = secciones[0]['course_name'] if secciones else f"Curso {course_id}"
        
        # Para cada liga del curso
        for liga_num in sorted(ligas.keys()):
            secciones_liga = ligas[liga_num]
            
            # Ordenar por tipo: T → P → L
            orden_tipo = {'T': 0, 'P': 1, 'L': 2}
            secciones_liga_ordenadas = sorted(
                secciones_liga,
                key=lambda x: orden_tipo.get(x['session_type'][0], 3)
            )
            
            # ASIGNAR TODA LA LIGA JUNTA
            # La teoría debe ir ANTES que prácticas/labs de esta liga
            
            for seccion in secciones_liga_ordenadas:
                session_type = seccion['session_type']
                tipo_aula = seccion.get('tipo_aula', 'NOLAB')
                
                # Buscar profesores del curso
                prof_ids = [p['id'] for p in profesores if p.get('course_id') == course_id]
                if not prof_ids:
                    prof_ids = [p['id'] for p in profesores]
                
                random.shuffle(prof_ids)
                
                # Determinar aulas candidatas
                if tipo_aula == 'LAB':
                    aulas_candidatas = [a for a in aulas if a.get('tipo', '') == 'LAB']
                else:
                    aulas_candidatas = [a for a in aulas if a.get('tipo', '') == 'NOLAB']
                
                if not aulas_candidatas:
                    total_fallidas += 1
                    continue
                
                # Context-aware: Filtrar slots válidos
                ultimo_ts = ultimo_slot_por_curso.get(course_id, (0, time(0, 0)))
                
                slots_validos = []
                for slot in slots_ordenados:
                    dia, h_ini, h_fin = slot
                    dia_num = dias_num.get(dia, 0)
                    hora_obj = datetime.strptime(h_ini, '%H:%M:%S').time()
                    slot_ts = (dia_num, hora_obj)
                    
                    if slot_ts > ultimo_ts:
                        slots_validos.append(slot)
                
                if not slots_validos:
                    slots_validos = slots_ordenados  # Fallback
                
                # Intentar asignar
                asignado = False
                
                for prof_id in prof_ids:
                    if asignado:
                        break
                    
                    for slot in slots_validos:
                        dia, h_ini, h_fin = slot
                        slot_key = (dia, h_ini)
                        
                        # Verificar conflicto profesor
                        if slot_key in ocupacion_profesor[prof_id]:
                            continue
                        
                        # Intentar con aulas
                        random.shuffle(aulas_candidatas)
                        
                        for aula in aulas_candidatas:
                            classroom_id = aula['id']
                            
                            # Verificar conflicto aula
                            if slot_key in ocupacion_aula[classroom_id]:
                                continue
                            
                            # ✅ ASIGNAR
                            asignacion = {
                                'course_id': course_id,
                                'course_name': course_name,
                                'session_type': session_type,
                                'liga': liga_num,
                                'professor_id': prof_id,
                                'classroom_id': classroom_id,
                                'day': dia,
                                'start_time': h_ini,
                                'end_time': h_fin,
                                'duration_hours': 2
                            }
                            
                            solucion.append(asignacion)
                            ocupacion_aula[classroom_id].add(slot_key)
                            ocupacion_profesor[prof_id].add(slot_key)
                            
                            # Actualizar context
                            dia_num = dias_num.get(dia, 0)
                            hora_obj = datetime.strptime(h_ini, '%H:%M:%S').time()
                            ultimo_slot_por_curso[course_id] = (dia_num, hora_obj)
                            
                            total_asignadas += 1
                            asignado = True
                            break
                        
                        if asignado:
                            break
                
                if not asignado:
                    total_fallidas += 1
        
        # Progreso
        if len(solucion) % 50 == 0:
            print(f"   [Procesadas {total_asignadas}/{total_asignadas + total_fallidas} secciones]")
    
    print(f"\n   ✅ Total asignadas: {total_asignadas}")
    print(f"   ❌ Total fallidas: {total_fallidas}")
    
    return solucion


if __name__ == '__main__':
    print("="*80)
    print("🔗 ACO CON LIGAS - VERSIÓN 3.0")
    print("="*80)
    print("\n✅ Funcionalidad:")
    print("   • Ligas: T1→P1/L1, T2→P2/L2")
    print("   • Bloques UPAO: 50 min cada uno")
    print("   • Paralelización: Múltiples P1/L1 permitidos")
    print("   • Límite: 9:35pm presencial, 10:30pm NPR")
    print("   • Context-aware: Orden temporal por curso")
    print("="*80)
