"""
DIAGNÓSTICO: ¿Por qué solo 45 asignaciones?
==========================================
"""

import random
from collections import defaultdict
import mysql.connector
from datetime import time, timedelta

def conectar_bd():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='sistemas',
        database='upao_timetabling'
    )

def generar_slots():
    """Genera todos los slots de tiempo disponibles"""
    dias = ['LUNES', 'MARTES', 'MIERCOLES', 'JUEVES', 'VIERNES', 'SABADO']
    horas = [
        ('07:00:00', '09:00:00'),
        ('09:00:00', '11:00:00'),
        ('11:00:00', '13:00:00'),
        ('13:00:00', '15:00:00'),
        ('15:00:00', '17:00:00'),
        ('17:00:00', '19:00:00'),
        ('19:00:00', '21:00:00'),
    ]
    
    slots = []
    for dia in dias:
        for h_ini, h_fin in horas:
            slots.append((dia, h_ini, h_fin))
    
    return slots

def diagnosticar():
    """Ejecuta asignación y diagnóstica dónde falla"""
    
    conn = conectar_bd()
    cursor = conn.cursor(dictionary=True)
    
    # Cargar aulas
    cursor.execute("""
        SELECT id, codigo, tipo, capacidad
        FROM classrooms
        WHERE disponible = 1
    """)
    aulas = cursor.fetchall()
    
    aulas_por_tipo = {
        'LAB': [a for a in aulas if a['tipo'] == 'LAB'],
        'NOLAB': [a for a in aulas if a['tipo'] == 'NOLAB']
    }
    
    # Cargar profesores
    cursor.execute("SELECT id, nombre_completo FROM professors")
    profesores = cursor.fetchall()
    prof_ids = [p['id'] for p in profesores]
    
    slots_tiempo = generar_slots()
    
    print(f"\n{'='*80}")
    print(f"🔍 DIAGNÓSTICO DE ASIGNACIÓN")
    print(f"{'='*80}")
    print(f"📦 Recursos disponibles:")
    print(f"   • Profesores: {len(prof_ids)}")
    print(f"   • Aulas LAB: {len(aulas_por_tipo['LAB'])}")
    print(f"   • Aulas NOLAB: {len(aulas_por_tipo['NOLAB'])}")
    print(f"   • Slots de tiempo: {len(slots_tiempo)}")
    print(f"   • Capacidad teórica: {len(prof_ids)} × {len(slots_tiempo)} = {len(prof_ids) * len(slots_tiempo)} espacios")
    print(f"{'='*80}\n")
    
    # Simular 300 secciones ficticias
    secciones = []
    for i in range(100):
        secciones.append({'tipo_aula': 'NOLAB', 'alumnos': 30, 'nombre': f'TEORIA_{i}'})
    for i in range(100):
        secciones.append({'tipo_aula': 'NOLAB', 'alumnos': 25, 'nombre': f'PRACTICA_{i}'})
    for i in range(100):
        secciones.append({'tipo_aula': 'LAB', 'alumnos': 20, 'nombre': f'LAB_{i}'})
    
    random.shuffle(secciones)
    
    # Intentar asignar
    profesor_slots = defaultdict(set)
    slots_usados = defaultdict(set)
    asignadas = 0
    
    # Estadísticas de fallo
    fallos_profesor_ocupado = 0
    fallos_sin_aula = 0
    fallos_sin_slot_libre = 0
    
    for idx, seccion in enumerate(secciones):
        tipo_aula = seccion['tipo_aula']
        alumnos = seccion['alumnos']
        
        asignado = False
        
        # Barajar profesores y slots
        prof_shuffled = random.sample(prof_ids, len(prof_ids))
        slots_shuffled = random.sample(slots_tiempo, len(slots_tiempo))
        
        intentos_profesor = 0
        intentos_slot = 0
        
        for prof_id in prof_shuffled:
            if asignado:
                break
            
            intentos_profesor += 1
            
            for slot in slots_shuffled:
                intentos_slot += 1
                
                dia, h_ini, h_fin = slot
                key_slot = (dia, h_ini)
                
                # ¿Profesor ocupado?
                if key_slot in profesor_slots[prof_id]:
                    fallos_profesor_ocupado += 1
                    continue
                
                # ¿Hay aula disponible?
                aulas_disponibles = [
                    a for a in aulas_por_tipo.get(tipo_aula, [])
                    if a['id'] not in slots_usados[key_slot]
                    and a['capacidad'] >= alumnos
                ]
                
                if not aulas_disponibles:
                    fallos_sin_aula += 1
                    continue
                
                # ASIGNAR
                aula = aulas_disponibles[0]
                profesor_slots[prof_id].add(key_slot)
                slots_usados[key_slot].add(aula['id'])
                asignadas += 1
                asignado = True
                break
        
        if not asignado:
            fallos_sin_slot_libre += 1
            print(f"\n❌ FALLO EN SECCIÓN {idx+1}: {seccion['nombre']}")
            print(f"   • Tipo aula: {tipo_aula}")
            print(f"   • Alumnos: {alumnos}")
            print(f"   • Profesores probados: {intentos_profesor}")
            print(f"   • Slots probados: {intentos_slot}")
            print(f"   • Asignadas hasta ahora: {asignadas}")
            
            # Analizar estado actual
            slots_totales_usados = len(slots_usados)
            aulas_usadas_por_slot = {k: len(v) for k, v in slots_usados.items()}
            promedio_aulas_por_slot = sum(aulas_usadas_por_slot.values()) / max(1, len(aulas_usadas_por_slot))
            
            print(f"\n   📊 Estado actual:")
            print(f"      • Slots con al menos 1 aula usada: {slots_totales_usados}/{len(slots_tiempo)}")
            print(f"      • Promedio aulas usadas por slot: {promedio_aulas_por_slot:.2f}")
            print(f"      • Total aulas LAB: {len(aulas_por_tipo['LAB'])}")
            print(f"      • Total aulas NOLAB: {len(aulas_por_tipo['NOLAB'])}")
            
            # Ver cuántos profesores tienen slots libres
            profs_con_espacio = 0
            for prof_id in prof_ids:
                if len(profesor_slots[prof_id]) < len(slots_tiempo):
                    profs_con_espacio += 1
            
            print(f"      • Profesores con slots libres: {profs_con_espacio}/{len(prof_ids)}")
            
            # Ver slots con aulas disponibles
            slots_con_aulas_disp = 0
            for slot in slots_tiempo:
                key_slot = (slot[0], slot[1])
                aulas_disp = [
                    a for a in aulas_por_tipo.get(tipo_aula, [])
                    if a['id'] not in slots_usados.get(key_slot, set())
                    and a['capacidad'] >= alumnos
                ]
                if aulas_disp:
                    slots_con_aulas_disp += 1
            
            print(f"      • Slots con aulas {tipo_aula} disponibles: {slots_con_aulas_disp}/{len(slots_tiempo)}")
            
            # Si hay muchos fallos, parar
            if asignadas >= 50:
                print(f"\n⚠️  Deteniéndose después de {asignadas} asignaciones para análisis")
                break
    
    print(f"\n{'='*80}")
    print(f"📊 RESUMEN DEL DIAGNÓSTICO")
    print(f"{'='*80}")
    print(f"✅ Asignadas: {asignadas}/300 ({100*asignadas/300:.1f}%)")
    print(f"❌ Fallos:")
    print(f"   • Profesor ocupado: {fallos_profesor_ocupado}")
    print(f"   • Sin aula disponible: {fallos_sin_aula}")
    print(f"   • Sin slot válido: {fallos_sin_slot_libre}")
    print(f"{'='*80}\n")
    
    conn.close()

if __name__ == '__main__':
    diagnosticar()
