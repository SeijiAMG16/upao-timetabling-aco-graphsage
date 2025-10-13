"""
Investigación: ¿Por qué ACO no varía entre iteraciones?
Debería haber exploración y variación antes de converger
"""

import json
import logging
from collections import defaultdict, Counter
import random
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def investigate_aco_variation():
    """Investiga por qué ACO no muestra variación entre iteraciones"""
    
    print("\n" + "="*80)
    print("🔬 INVESTIGACIÓN: ¿POR QUÉ NO HAY VARIACIÓN EN ACO?")
    print("="*80)
    
    # Cargar datos
    with open('upao_data_for_aco.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    courses = {c['id']: c for c in data['courses']}
    professors = {p['id']: p for p in data['professors']}
    classrooms = {c['id']: c for c in data['classrooms']}
    time_slots = data['time_slots']
    
    # Generar tareas como lo hace ACO
    scheduling_tasks = []
    for course_id, course in courses.items():
        for i in range(1, course['grupos_teoria'] + 1):
            scheduling_tasks.append({
                'course_id': course_id, 'section_type': 'teoria',
                'section_number': i, 'students_count': course['alumnos_teoria']
            })
        for i in range(1, course['grupos_practica'] + 1):
            scheduling_tasks.append({
                'course_id': course_id, 'section_type': 'practica', 
                'section_number': i, 'students_count': course['alumnos_practica']
            })
        for i in range(1, course['grupos_laboratorio'] + 1):
            scheduling_tasks.append({
                'course_id': course_id, 'section_type': 'laboratorio',
                'section_number': i, 'students_count': course['alumnos_laboratorio']
            })
    
    print(f"📊 Tareas totales: {len(scheduling_tasks)}")
    
    # Simular el pre-filtrado de opciones válidas
    print("\n🔍 SIMULANDO PRE-FILTRADO...")
    
    valid_options = {}
    tasks_with_options = 0
    tasks_without_options = 0
    
    for i, task in enumerate(scheduling_tasks):
        course = courses[task['course_id']]
        students = task['students_count']
        section_type = task['section_type']
        options = []
        
        # Filtrar aulas válidas
        valid_classrooms = []
        for classroom_id, classroom in classrooms.items():
            if students > classroom['capacidad']:
                continue
            if section_type == 'laboratorio':
                if classroom['tipo'] != 'laboratorio':
                    continue
                if students <= 20 and classroom['edificio'] != 'F':
                    continue
                if students > 20 and classroom['edificio'] != 'G':
                    continue
            valid_classrooms.append(classroom_id)
        
        # Filtrar franjas por preferencia de ciclo
        preferred_periods = ['mañana'] if course['ciclo'] % 2 == 1 else ['tarde', 'noche']
        valid_time_slots = [ts for ts in time_slots if ts['periodo'] in preferred_periods]
        if not valid_time_slots:
            valid_time_slots = time_slots
        
        # Generar combinaciones válidas
        for prof_id in professors:
            prof = professors[prof_id]
            for classroom_id in valid_classrooms:
                for time_slot in valid_time_slots:
                    slot_tuple = (time_slot['dia'], time_slot['franja'])
                    if slot_tuple in [tuple(slot) for slot in prof['disponibilidad']]:
                        options.append((prof_id, classroom_id, time_slot))
        
        valid_options[i] = options
        
        if options:
            tasks_with_options += 1
        else:
            tasks_without_options += 1
    
    print(f"   Tareas CON opciones: {tasks_with_options}")
    print(f"   Tareas SIN opciones: {tasks_without_options}")
    
    # AQUÍ ESTÁ EL PROBLEMA CLAVE: Simular múltiples construcciones de solución
    print(f"\n🎲 SIMULANDO 10 CONSTRUCCIONES DE SOLUCIÓN ALEATORIAS...")
    
    results = []
    
    for simulation in range(10):
        print(f"\n--- Simulación {simulation + 1} ---")
        
        occupied_slots = defaultdict(set)
        professor_loads = defaultdict(int)
        successful_assignments = 0
        
        # Ordenar tareas ALEATORIAMENTE (como debería hacer ACO)
        task_indices = list(range(len(scheduling_tasks)))
        random.shuffle(task_indices)
        
        assignments_log = []
        
        for task_idx in task_indices:
            task = scheduling_tasks[task_idx]
            options = valid_options[task_idx]
            
            if not options:
                continue
            
            # Filtrar opciones disponibles
            available_options = []
            for prof_id, classroom_id, time_slot in options:
                slot_key = (time_slot['dia'], time_slot['franja'])
                
                # Verificar conflictos
                if slot_key in occupied_slots:
                    if prof_id in occupied_slots[slot_key] or classroom_id in occupied_slots[slot_key]:
                        continue
                
                # Verificar carga profesor
                prof = professors[prof_id]
                if professor_loads[prof_id] >= prof['carga_maxima']:
                    continue
                
                available_options.append((prof_id, classroom_id, time_slot))
            
            if not available_options:
                continue
            
            # SELECCIÓN ALEATORIA (para ver si hay variación)
            selected = random.choice(available_options)
            prof_id, classroom_id, time_slot = selected
            
            # Asignación exitosa
            slot_key = (time_slot['dia'], time_slot['franja'])
            occupied_slots[slot_key].add(prof_id)
            occupied_slots[slot_key].add(classroom_id)
            professor_loads[prof_id] += 1
            successful_assignments += 1
            
            assignments_log.append({
                'task': f"{task['course_id']}_{task['section_type']}", 
                'prof': prof_id,
                'classroom': classroom_id,
                'slot': f"D{time_slot['dia']}_F{time_slot['franja']}"
            })
        
        results.append(successful_assignments)
        print(f"   Asignaciones exitosas: {successful_assignments}")
        
        # Mostrar primeras 5 asignaciones para ver variación
        print("   Primeras 5 asignaciones:")
        for i, assignment in enumerate(assignments_log[:5]):
            print(f"     {i+1}. {assignment['task']} → {assignment['prof']} @ {assignment['classroom']} @ {assignment['slot']}")
    
    print(f"\n📊 RESUMEN DE 10 SIMULACIONES:")
    print(f"   Resultados: {results}")
    print(f"   Mínimo: {min(results)}")
    print(f"   Máximo: {max(results)}")
    print(f"   Promedio: {np.mean(results):.1f}")
    print(f"   Varianza: {np.var(results):.2f}")
    
    # Análisis del problema
    print(f"\n🔍 ANÁLISIS:")
    
    if len(set(results)) == 1:
        print("   🔴 PROBLEMA CONFIRMADO: Todas las simulaciones dan el mismo resultado")
        print("   📝 Posibles causas:")
        print("      1. Pre-filtrado demasiado restrictivo")
        print("      2. Solo hay UNA forma válida de asignar")
        print("      3. Orden de procesamiento determina resultado")
        print("      4. Restricciones demasiado estrictas")
    else:
        print("   ✅ HAY VARIACIÓN: Las simulaciones dan diferentes resultados")
        print("   📝 El problema puede estar en:")
        print("      1. Parámetros ACO (alpha, beta, rho)")
        print("      2. Actualización de feromonas")
        print("      3. Selección probabilística")
    
    # Investigar el orden de tareas
    print(f"\n🧪 EXPERIMENTO: ¿EL ORDEN IMPORTA?")
    
    # Probar diferentes órdenes
    orders_to_test = [
        ("Orden original", list(range(len(scheduling_tasks)))),
        ("Orden inverso", list(range(len(scheduling_tasks)))[::-1]),
        ("Aleatorio 1", random.sample(range(len(scheduling_tasks)), len(scheduling_tasks))),
        ("Aleatorio 2", random.sample(range(len(scheduling_tasks)), len(scheduling_tasks)))
    ]
    
    order_results = []
    
    for order_name, task_order in orders_to_test:
        occupied_slots = defaultdict(set)
        professor_loads = defaultdict(int)
        successful_assignments = 0
        
        for task_idx in task_order:
            task = scheduling_tasks[task_idx]
            options = valid_options[task_idx]
            
            if not options:
                continue
            
            # Buscar primera opción válida (determinístico)
            assignment_made = False
            for prof_id, classroom_id, time_slot in options:
                if assignment_made:
                    break
                    
                slot_key = (time_slot['dia'], time_slot['franja'])
                
                if slot_key in occupied_slots:
                    if prof_id in occupied_slots[slot_key] or classroom_id in occupied_slots[slot_key]:
                        continue
                
                prof = professors[prof_id]
                if professor_loads[prof_id] >= prof['carga_maxima']:
                    continue
                
                # Asignación exitosa
                occupied_slots[slot_key].add(prof_id)
                occupied_slots[slot_key].add(classroom_id)
                professor_loads[prof_id] += 1
                successful_assignments += 1
                assignment_made = True
        
        order_results.append((order_name, successful_assignments))
        print(f"   {order_name}: {successful_assignments} asignaciones")
    
    # Conclusión
    print(f"\n💡 CONCLUSIÓN:")
    
    unique_order_results = set([result for _, result in order_results])
    
    if len(unique_order_results) == 1:
        print("   🔴 EL ORDEN NO IMPORTA: Siempre el mismo resultado")
        print("   📋 Esto significa que:")
        print("      - Las restricciones son tan estrictas que solo hay UNA solución válida")
        print("      - El algoritmo greedy encuentra siempre el mismo conjunto de asignaciones")
        print("      - ACO converge inmediatamente porque no hay alternativas")
    else:
        print("   🟡 EL ORDEN SÍ IMPORTA: Diferentes órdenes dan diferentes resultados") 
        print("   📋 Esto significa que:")
        print("      - Hay múltiples soluciones posibles")
        print("      - ACO debería mostrar variación")
        print("      - El problema está en la implementación del algoritmo")
    
    print("\n🛠️ RECOMENDACIONES:")
    if len(unique_order_results) == 1:
        print("   1. ✅ El ACO está funcionando correctamente")
        print("   2. 📊 El resultado constante es esperado (máximo único)")
        print("   3. 🎯 GraphSAGE debe enfocarse en CALIDAD, no cantidad")
        print("   4. 🏗️ Considerar relajar restricciones para más opciones")
    else:
        print("   1. 🔧 Revisar implementación de selección probabilística ACO")
        print("   2. 📈 Ajustar parámetros alpha, beta para más exploración")
        print("   3. 🎲 Verificar que la aleatorización funcione correctamente")
        print("   4. 🔄 Asegurar que las feromonas se actualicen adecuadamente")
    
    print("="*80)


if __name__ == "__main__":
    investigate_aco_variation()