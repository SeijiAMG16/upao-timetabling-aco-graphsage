"""
Deep Analysis of ACO Algorithm - Why exactly 191?
Análisis profundo para entender por qué siempre 191 asignaciones
"""

import json
import logging
from collections import defaultdict, Counter
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def deep_analysis_191():
    """Análisis profundo del comportamiento del algoritmo"""
    
    print("\n" + "="*80)
    print("🔬 ANÁLISIS PROFUNDO - ¿POR QUÉ SIEMPRE 191?")
    print("="*80)
    
    # Cargar datos
    with open('upao_data_for_aco.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    courses = {c['id']: c for c in data['courses']}
    professors = {p['id']: p for p in data['professors']}
    classrooms = {c['id']: c for c in data['classrooms']}
    time_slots = data['time_slots']
    
    # Simular el mismo proceso de generación de tareas que ACO
    print("🔄 SIMULANDO GENERACIÓN DE TAREAS...")
    
    scheduling_tasks = []
    for course_id, course in courses.items():
        # Grupos de teoría
        for i in range(1, course['grupos_teoria'] + 1):
            scheduling_tasks.append({
                'course_id': course_id,
                'section_type': 'teoria',
                'section_number': i,
                'students_count': course['alumnos_teoria']
            })
        
        # Grupos de práctica
        for i in range(1, course['grupos_practica'] + 1):
            scheduling_tasks.append({
                'course_id': course_id,
                'section_type': 'practica',
                'section_number': i,
                'students_count': course['alumnos_practica']
            })
        
        # Grupos de laboratorio
        for i in range(1, course['grupos_laboratorio'] + 1):
            scheduling_tasks.append({
                'course_id': course_id,
                'section_type': 'laboratorio',
                'section_number': i,
                'students_count': course['alumnos_laboratorio']
            })
    
    print(f"📊 Total tareas generadas: {len(scheduling_tasks)}")
    
    # Analizar cada tarea individualmente
    print("\n🔍 ANALIZANDO OPCIONES VÁLIDAS POR TAREA...")
    
    tasks_by_type = defaultdict(list)
    for i, task in enumerate(scheduling_tasks):
        tasks_by_type[task['section_type']].append((i, task))
    
    print(f"📋 Distribución:")
    for section_type, task_list in tasks_by_type.items():
        print(f"   {section_type}: {len(task_list)} tareas")
    
    # Simular el pre-filtrado de opciones válidas
    print("\n⚙️ SIMULANDO PRE-FILTRADO DE OPCIONES...")
    
    total_valid_combinations = 0
    tasks_with_no_options = 0
    tasks_with_few_options = []
    
    for i, task in enumerate(scheduling_tasks):
        course = courses[task['course_id']]
        students = task['students_count']
        section_type = task['section_type']
        
        valid_combinations = 0
        
        # Filtrar aulas válidas
        valid_classrooms = []
        for classroom_id, classroom in classrooms.items():
            # Verificar capacidad
            if students > classroom['capacidad']:
                continue
            
            # Verificar tipo de aula
            if section_type == 'laboratorio':
                if classroom['tipo'] != 'laboratorio':
                    continue
                # Regla F/G para laboratorios
                if students <= 20 and classroom['edificio'] != 'F':
                    continue
                if students > 20 and classroom['edificio'] != 'G':
                    continue
            
            valid_classrooms.append(classroom_id)
        
        # Filtrar franjas horarias por preferencia de ciclo
        preferred_periods = ['mañana'] if course['ciclo'] % 2 == 1 else ['tarde', 'noche']
        valid_time_slots = [ts for ts in time_slots if ts['periodo'] in preferred_periods]
        
        if not valid_time_slots:
            valid_time_slots = time_slots
        
        # Contar combinaciones válidas
        for prof_id in professors:
            prof = professors[prof_id]
            for classroom_id in valid_classrooms:
                for time_slot in valid_time_slots:
                    # Verificar disponibilidad del profesor
                    slot_tuple = (time_slot['dia'], time_slot['franja'])
                    if slot_tuple in [tuple(slot) for slot in prof['disponibilidad']]:
                        valid_combinations += 1
        
        total_valid_combinations += valid_combinations
        
        if valid_combinations == 0:
            tasks_with_no_options += 1
            print(f"❌ Tarea {i}: {task['course_id']} {section_type} - SIN OPCIONES")
            print(f"    Estudiantes: {students}, Aulas válidas: {len(valid_classrooms)}")
        elif valid_combinations < 100:
            tasks_with_few_options.append((i, task, valid_combinations))
    
    print(f"\n📊 RESUMEN PRE-FILTRADO:")
    print(f"   Total combinaciones válidas: {total_valid_combinations:,}")
    print(f"   Tareas sin opciones: {tasks_with_no_options}")
    print(f"   Tareas con pocas opciones (<100): {len(tasks_with_few_options)}")
    print(f"   Promedio opciones/tarea: {total_valid_combinations / len(scheduling_tasks):.1f}")
    
    # Mostrar tareas problemáticas
    if tasks_with_few_options:
        print(f"\n⚠️ TAREAS MÁS PROBLEMÁTICAS:")
        tasks_with_few_options.sort(key=lambda x: x[2])  # Ordenar por número de opciones
        for i, (task_idx, task, options) in enumerate(tasks_with_few_options[:10]):
            course = courses[task['course_id']]
            print(f"   {i+1:2d}. {task['course_id']} {task['section_type']} - "
                  f"{options} opciones (estudiantes: {task['students_count']}, "
                  f"ciclo: {course['ciclo']})")
    
    # Simular asignación greedy simple
    print(f"\n🤖 SIMULANDO ASIGNACIÓN GREEDY SIMPLE...")
    
    occupied_slots = defaultdict(set)
    professor_loads = defaultdict(int)
    successful_assignments = 0
    
    # Ordenar tareas por dificultad (menos opciones primero)
    task_difficulties = []
    for i, task in enumerate(scheduling_tasks):
        course = courses[task['course_id']]
        students = task['students_count']
        section_type = task['section_type']
        
        # Contar opciones rápidamente
        valid_classrooms = [
            c_id for c_id, c in classrooms.items()
            if (students <= c['capacidad'] and 
                (section_type != 'laboratorio' or 
                 (c['tipo'] == 'laboratorio' and 
                  ((students <= 20 and c['edificio'] == 'F') or
                   (students > 20 and c['edificio'] == 'G')))))
        ]
        
        difficulty = len(valid_classrooms) * len(time_slots) * len(professors)
        task_difficulties.append((difficulty, i, task))
    
    # Ordenar por dificultad (más difíciles primero)
    task_difficulties.sort()
    
    for difficulty, task_idx, task in task_difficulties:
        course = courses[task['course_id']]
        students = task['students_count']
        section_type = task['section_type']
        
        assignment_made = False
        
        # Buscar primera asignación válida
        for prof_id, prof in professors.items():
            if assignment_made:
                break
                
            # Verificar carga
            if professor_loads[prof_id] >= prof['carga_maxima']:
                continue
            
            for classroom_id, classroom in classrooms.items():
                if assignment_made:
                    break
                
                # Verificar compatibilidad aula
                if students > classroom['capacidad']:
                    continue
                
                if section_type == 'laboratorio':
                    if classroom['tipo'] != 'laboratorio':
                        continue
                    if students <= 20 and classroom['edificio'] != 'F':
                        continue
                    if students > 20 and classroom['edificio'] != 'G':
                        continue
                
                # Buscar franja horaria disponible
                preferred_periods = ['mañana'] if course['ciclo'] % 2 == 1 else ['tarde', 'noche']
                
                for time_slot in time_slots:
                    if time_slot['periodo'] not in preferred_periods:
                        continue
                    
                    slot_key = (time_slot['dia'], time_slot['franja'])
                    slot_tuple = tuple(slot_key)
                    
                    # Verificar disponibilidad profesor
                    if slot_tuple not in [tuple(slot) for slot in prof['disponibilidad']]:
                        continue
                    
                    # Verificar conflictos
                    if (prof_id in occupied_slots[slot_key] or 
                        classroom_id in occupied_slots[slot_key]):
                        continue
                    
                    # ¡Asignación exitosa!
                    occupied_slots[slot_key].add(prof_id)
                    occupied_slots[slot_key].add(classroom_id)
                    professor_loads[prof_id] += 1
                    successful_assignments += 1
                    assignment_made = True
                    break
    
    print(f"🎯 RESULTADO SIMULACIÓN GREEDY: {successful_assignments}/297 ({successful_assignments/297*100:.1f}%)")
    
    # Analizar por qué exactamente ese número
    print(f"\n🔍 ¿POR QUÉ EXACTAMENTE {successful_assignments}?")
    
    remaining_tasks = 297 - successful_assignments
    print(f"   Tareas no asignadas: {remaining_tasks}")
    
    # Analizar qué quedó ocupado
    occupied_count = len(occupied_slots)
    total_slots = 96  # 16 franjas × 6 días
    
    print(f"   Franjas ocupadas: {occupied_count}/96 ({occupied_count/96*100:.1f}%)")
    
    # Distribución de carga de profesores
    load_distribution = Counter(professor_loads.values())
    print(f"   Distribución carga profesores:")
    for load, count in sorted(load_distribution.items()):
        if load > 0:
            print(f"     {count} profesores con {load} asignaciones")
    
    # Uso de aulas
    classroom_usage = defaultdict(int)
    for slot_assignments in occupied_slots.values():
        for item in slot_assignments:
            if item in classrooms:
                classroom_usage[item] += 1
    
    print(f"   Aulas más usadas:")
    for classroom_id, usage in Counter(classroom_usage).most_common(5):
        classroom = classrooms[classroom_id]
        print(f"     {classroom_id} ({classroom['tipo']}, {classroom['edificio']}): {usage} usos")
    
    print("="*80)
    
    # Conclusión
    if successful_assignments == 191:
        print("🎯 CONCLUSIÓN: El algoritmo greedy simple también obtiene 191!")
        print("   Esto sugiere que 191 puede ser realmente el máximo práctico")
        print("   debido a restricciones complejas no consideradas en el análisis teórico.")
    else:
        print(f"🤔 DISCREPANCIA: Greedy simple obtiene {successful_assignments}, ACO obtiene 191")
        print("   Esto indica que hay diferencias en la implementación.")
    
    print("\n💡 RECOMENDACIONES:")
    print("1. 🔬 Investigar las 106 tareas no asignadas específicamente")
    print("2. 🎛️ Considerar relajar algunas restricciones suaves")
    print("3. 📊 GraphSAGE puede ayudar a priorizar mejor las asignaciones")
    print("4. 🏗️ Considerar expandir recursos (más aulas/horarios)")


if __name__ == "__main__":
    deep_analysis_191()