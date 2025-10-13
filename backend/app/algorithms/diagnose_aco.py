"""
Diagnostic Tool for ACO Algorithm
Diagnostica por qué el ACO obtiene siempre el mismo fitness
"""

import json
import logging
from collections import defaultdict, Counter
from typing import Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_aco_behavior():
    """Analiza el comportamiento del algoritmo ACO para encontrar problemas"""
    
    print("\n" + "="*60)
    print("🔍 DIAGNÓSTICO ACO - ¿POR QUÉ MISMO FITNESS?")
    print("="*60)
    
    # 1. Analizar datos de entrada
    with open('upao_data_for_aco.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    courses = {c['id']: c for c in data['courses']}
    professors = {p['id']: p for p in data['professors']}  
    classrooms = {c['id']: c for c in data['classrooms']}
    
    print(f"\n📊 DATOS DE ENTRADA:")
    print(f"   Cursos: {len(courses)}")
    print(f"   Profesores: {len(professors)}")
    print(f"   Aulas: {len(classrooms)}")
    
    # 2. Analizar distribución de tareas
    theory_tasks = sum(c['grupos_teoria'] for c in courses.values())
    practice_tasks = sum(c['grupos_practica'] for c in courses.values()) 
    lab_tasks = sum(c['grupos_laboratorio'] for c in courses.values())
    total_tasks = theory_tasks + practice_tasks + lab_tasks
    
    print(f"\n📋 DISTRIBUCIÓN DE TAREAS:")
    print(f"   Teoría: {theory_tasks}")
    print(f"   Práctica: {practice_tasks}")
    print(f"   Laboratorio: {lab_tasks}")
    print(f"   TOTAL: {total_tasks}")
    
    # 3. Analizar restricciones de aulas
    lab_classrooms = [c for c in classrooms.values() if c['tipo'] == 'laboratorio']
    theory_classrooms = [c for c in classrooms.values() if c['tipo'] == 'teorica']
    
    f_labs = [c for c in lab_classrooms if c['edificio'] == 'F']
    g_labs = [c for c in lab_classrooms if c['edificio'] == 'G']
    
    print(f"\n🏢 ANÁLISIS DE AULAS:")
    print(f"   Laboratorios F (≤20): {len(f_labs)}")
    print(f"   Laboratorios G (>20): {len(g_labs)}")
    print(f"   Aulas teóricas: {len(theory_classrooms)}")
    
    # 4. Analizar distribución de estudiantes en labs
    small_lab_courses = []
    large_lab_courses = []
    
    for course in courses.values():
        if course['grupos_laboratorio'] > 0:
            if course['alumnos_laboratorio'] <= 20:
                small_lab_courses.append(course)
            else:
                large_lab_courses.append(course)
    
    print(f"\n🧪 ANÁLISIS LABORATORIOS:")
    print(f"   Cursos lab ≤20 estudiantes: {len(small_lab_courses)} (necesitan aulas F)")
    print(f"   Cursos lab >20 estudiantes: {len(large_lab_courses)} (necesitan aulas G)")
    print(f"   Total grupos lab pequeños: {sum(c['grupos_laboratorio'] for c in small_lab_courses)}")
    print(f"   Total grupos lab grandes: {sum(c['grupos_laboratorio'] for c in large_lab_courses)}")
    
    # 5. Detectar posibles cuellos de botella
    print(f"\n⚠️ CUELLOS DE BOTELLA DETECTADOS:")
    
    # Cuello de botella 1: Laboratorios F
    small_lab_groups = sum(c['grupos_laboratorio'] for c in small_lab_courses)
    if small_lab_groups > len(f_labs) * 96:  # 96 franjas por aula
        print(f"   🔴 CRÍTICO: {small_lab_groups} grupos lab ≤20 vs {len(f_labs)} aulas F")
        print(f"       Capacidad máxima aulas F: {len(f_labs) * 96} asignaciones")
        print(f"       Déficit: {small_lab_groups - len(f_labs) * 96}")
    else:
        utilization_f = (small_lab_groups / (len(f_labs) * 96)) * 100
        print(f"   ✅ Aulas F: {utilization_f:.1f}% utilización")
    
    # Cuello de botella 2: Laboratorios G 
    large_lab_groups = sum(c['grupos_laboratorio'] for c in large_lab_courses)
    if large_lab_groups > len(g_labs) * 96:
        print(f"   🔴 CRÍTICO: {large_lab_groups} grupos lab >20 vs {len(g_labs)} aulas G")
        print(f"       Capacidad máxima aulas G: {len(g_labs) * 96} asignaciones")
        print(f"       Déficit: {large_lab_groups - len(g_labs) * 96}")
    else:
        utilization_g = (large_lab_groups / (len(g_labs) * 96)) * 100
        print(f"   ✅ Aulas G lab: {utilization_g:.1f}% utilización")
    
    # Cuello de botella 3: Total de recursos
    total_capacity = len(classrooms) * 96  # Total franjas disponibles
    if total_tasks > total_capacity:
        print(f"   🔴 CRÍTICO: {total_tasks} tareas vs {total_capacity} capacidad total")
        print(f"       Déficit: {total_tasks - total_capacity}")
    else:
        total_utilization = (total_tasks / total_capacity) * 100
        print(f"   📊 Utilización total: {total_utilization:.1f}%")
    
    # 6. Analizar por qué 191 específicamente
    print(f"\n🎯 ¿POR QUÉ EXACTAMENTE 191?")
    
    # Teoría: Si hay exactamente 191 asignaciones "fáciles" y el resto son imposibles
    available_f_slots = len(f_labs) * 96
    available_g_lab_slots = len(g_labs) * 96
    available_theory_slots = len(theory_classrooms) * 96
    
    max_small_labs = min(small_lab_groups, available_f_slots)
    max_large_labs = min(large_lab_groups, available_g_lab_slots)
    remaining_slots = available_theory_slots + (available_f_slots - max_small_labs) + (available_g_lab_slots - max_large_labs)
    max_theory_practice = min(theory_tasks + practice_tasks, remaining_slots)
    
    theoretical_max = max_small_labs + max_large_labs + max_theory_practice
    
    print(f"   Máximo teórico calculado: {theoretical_max}")
    print(f"   ACO obtiene: 191")
    
    if theoretical_max <= 191:
        print(f"   💡 EXPLICACIÓN: El ACO está encontrando el máximo absoluto posible!")
        print(f"      No hay más mejoras porque los recursos están al límite.")
    else:
        print(f"   ❓ MISTERIO: El ACO debería poder hacer mejor ({theoretical_max} vs 191)")
        print(f"      Posible problema en el algoritmo o parámetros.")
    
    # 7. Analizar solución actual
    try:
        with open('aco_optimized_final_solution.json', 'r', encoding='utf-8') as f:
            solution = json.load(f)
        
        assignments = solution['assignments']
        
        print(f"\n🔬 ANÁLISIS SOLUCIÓN ACTUAL:")
        
        # Contar por tipo
        by_type = Counter(a['section_type'] for a in assignments)
        print(f"   Asignaciones por tipo:")
        for section_type, count in by_type.items():
            print(f"     {section_type}: {count}")
        
        # Aulas más usadas
        classroom_usage = Counter(a['classroom_id'] for a in assignments)
        print(f"\n   Top 5 aulas más usadas:")
        for classroom_id, count in classroom_usage.most_common(5):
            classroom_info = classrooms[classroom_id]
            print(f"     {classroom_id} ({classroom_info['tipo']}, {classroom_info['edificio']}): {count} usos")
        
        # Profesores más usados
        prof_usage = Counter(a['professor_id'] for a in assignments)
        print(f"\n   Distribución carga profesores:")
        load_dist = Counter(prof_usage.values())
        for load, count in sorted(load_dist.items()):
            print(f"     {count} profesores con {load} asignaciones")
            
    except FileNotFoundError:
        print("   ❌ No se encontró el archivo de solución")
    
    # 8. Recomendaciones
    print(f"\n💡 RECOMENDACIONES:")
    
    if theoretical_max <= 191:
        print("   1. 🎯 El ACO está funcionando perfectamente!")
        print("   2. 📈 Para mejorar, necesitas MÁS RECURSOS:")
        print("      - Más aulas (especialmente laboratorios)")
        print("      - Más profesores")
        print("      - Más franjas horarias (extender horario)")
        print("   3. 🔄 GraphSAGE ayudará a optimizar la CALIDAD de asignaciones")
        print("   4. 🎛️ Considerar asignaciones compartidas o flexibles")
    else:
        print("   1. 🔧 Ajustar parámetros ACO para más exploración:")
        print("      - Aumentar rho (evaporación) a 0.3")
        print("      - Reducir beta (menos greedy) a 1.5") 
        print("      - Más hormigas (15-20)")
        print("      - Más iteraciones (30-50)")
        print("   2. 🎲 Agregar más randomización en construcción")
        print("   3. 📊 GraphSAGE puede ayudar a encontrar mejores heurísticas")
    
    print("="*60)


if __name__ == "__main__":
    analyze_aco_behavior()