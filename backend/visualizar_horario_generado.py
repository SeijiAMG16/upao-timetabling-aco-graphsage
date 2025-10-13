"""
🎨 VISUALIZADOR DE HORARIOS GENERADOS
======================================

Muestra el horario generado por el algoritmo ACO en formato legible
Permite ver:
- Horario completo por día
- Horario por curso
- Horario por profesor
- Horario por aula
- Validación T→P→L

Uso:
    python visualizar_horario_generado.py [experiment_id]
    
    Si no se especifica experiment_id, muestra el último experimento
"""

import mysql.connector
import sys
from datetime import datetime
from collections import defaultdict

# Configuración BD
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'sistemas',
    'database': 'upao_timetabling'
}

DIAS_ORDEN = ['LUNES', 'MARTES', 'MIÉRCOLES', 'JUEVES', 'VIERNES', 'SÁBADO']

def conectar_bd():
    """Conecta a la base de datos"""
    return mysql.connector.connect(**DB_CONFIG)

def obtener_ultimo_experimento():
    """Obtiene el ID del último experimento"""
    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(id) FROM algorithm_executions")
    ultimo_id = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return ultimo_id

def cargar_experimento(experiment_id):
    """Carga todas las asignaciones de un experimento"""
    conn = conectar_bd()
    cursor = conn.cursor(dictionary=True)
    
    # Cargar asignaciones con información completa
    cursor.execute("""
        SELECT 
            a.id,
            c.nombre as course_name,
            c.codigo as course_code,
            a.session_type,
            p.nombre_completo as professor_name,
            cl.codigo as classroom_name,
            cl.tipo as classroom_type,
            cl.capacidad as classroom_capacity,
            a.day,
            a.start_time,
            a.end_time
        FROM proposed_schedule_assignments a
        JOIN courses c ON a.course_id = c.id
        JOIN professors p ON a.professor_id = p.id
        JOIN classrooms cl ON a.classroom_id = cl.id
        WHERE a.algorithm_execution_id = %s
        ORDER BY 
            FIELD(a.day, 'LUNES', 'MARTES', 'MIÉRCOLES', 'JUEVES', 'VIERNES', 'SÁBADO'),
            a.start_time,
            c.nombre
    """, (experiment_id,))
    
    asignaciones = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return asignaciones

def mostrar_horario_completo(asignaciones):
    """Muestra el horario completo organizado por día y hora"""
    print("\n" + "="*120)
    print("📅 HORARIO COMPLETO - ORGANIZADO POR DÍA Y HORA")
    print("="*120)
    
    # Agrupar por día
    por_dia = defaultdict(list)
    for asig in asignaciones:
        por_dia[asig['day']].append(asig)
    
    for dia in DIAS_ORDEN:
        if dia not in por_dia:
            continue
            
        print(f"\n{'='*120}")
        print(f"📆 {dia}")
        print(f"{'='*120}")
        print(f"{'Hora':<12} {'Curso':<35} {'Tipo':<6} {'Profesor':<25} {'Aula':<15}")
        print("-"*120)
        
        for asig in sorted(por_dia[dia], key=lambda x: x['start_time']):
            hora = f"{asig['start_time']}-{asig['end_time']}"
            curso = asig['course_name'][:33]
            tipo = asig['session_type']
            profesor = asig['professor_name'][:23]
            aula = f"{asig['classroom_name']} ({asig['classroom_type']})"
            
            print(f"{hora:<12} {curso:<35} {tipo:<6} {profesor:<25} {aula:<15}")

def mostrar_horario_por_curso(asignaciones):
    """Muestra el horario agrupado por curso"""
    print("\n" + "="*120)
    print("📚 HORARIO POR CURSO (verificar secuencia T→P→L)")
    print("="*120)
    
    # Agrupar por curso
    por_curso = defaultdict(list)
    for asig in asignaciones:
        por_curso[asig['course_name']].append(asig)
    
    dias_num = {'LUNES': 1, 'MARTES': 2, 'MIÉRCOLES': 3, 'JUEVES': 4, 'VIERNES': 5, 'SÁBADO': 6}
    
    for curso in sorted(por_curso.keys()):
        print(f"\n📖 {curso}")
        print("-"*120)
        print(f"{'Tipo':<6} {'Día':<12} {'Hora':<12} {'Profesor':<25} {'Aula':<20}")
        print("-"*120)
        
        # Ordenar por día y hora
        asigs_curso = sorted(por_curso[curso], key=lambda x: (
            dias_num.get(x['day'], 0),
            x['start_time']
        ))
        
        for asig in asigs_curso:
            tipo = asig['session_type']
            dia = asig['day']
            hora = f"{asig['start_time']}-{asig['end_time']}"
            profesor = asig['professor_name'][:23]
            aula = f"{asig['classroom_name']} ({asig['classroom_type']})"
            
            # Marcar con color según tipo
            if tipo[0] == 'T':
                tipo_str = f"✓ {tipo}"
            elif tipo[0] == 'P':
                tipo_str = f"→ {tipo}"
            else:
                tipo_str = f"⚗ {tipo}"
            
            print(f"{tipo_str:<6} {dia:<12} {hora:<12} {profesor:<25} {aula:<20}")

def validar_tpl_visual(asignaciones):
    """Valida y muestra visualmente las violaciones T→P→L"""
    print("\n" + "="*120)
    print("✓ VALIDACIÓN T→P→L")
    print("="*120)
    
    dias_num = {'LUNES': 1, 'MARTES': 2, 'MIÉRCOLES': 3, 'JUEVES': 4, 'VIERNES': 5, 'SÁBADO': 6}
    
    def get_timestamp(asig):
        return (dias_num.get(asig['day'], 0), asig['start_time'])
    
    # Agrupar por curso
    por_curso = defaultdict(list)
    for asig in asignaciones:
        por_curso[asig['course_name']].append(asig)
    
    cursos_validos = 0
    cursos_invalidos = 0
    
    for curso, asigs in sorted(por_curso.items()):
        teorias = [a for a in asigs if a['session_type'][0] == 'T']
        practicas = [a for a in asigs if a['session_type'][0] == 'P']
        labs = [a for a in asigs if a['session_type'][0] == 'L']
        
        violaciones = []
        
        # Verificar T→P
        if teorias and practicas:
            max_t = max(teorias, key=get_timestamp)
            min_p = min(practicas, key=get_timestamp)
            if get_timestamp(max_t) >= get_timestamp(min_p):
                violaciones.append(f"T→P: última T ({max_t['day']} {max_t['start_time']}) >= primera P ({min_p['day']} {min_p['start_time']})")
        
        # Verificar P→L
        if practicas and labs:
            max_p = max(practicas, key=get_timestamp)
            min_l = min(labs, key=get_timestamp)
            if get_timestamp(max_p) >= get_timestamp(min_l):
                violaciones.append(f"P→L: última P ({max_p['day']} {max_p['start_time']}) >= primer L ({min_l['day']} {min_l['start_time']})")
        
        # Verificar T→L
        if teorias and labs:
            max_t = max(teorias, key=get_timestamp)
            min_l = min(labs, key=get_timestamp)
            if get_timestamp(max_t) >= get_timestamp(min_l):
                violaciones.append(f"T→L: última T ({max_t['day']} {max_t['start_time']}) >= primer L ({min_l['day']} {min_l['start_time']})")
        
        if violaciones:
            cursos_invalidos += 1
            print(f"\n❌ {curso}")
            for v in violaciones:
                print(f"   {v}")
        else:
            cursos_validos += 1
    
    print(f"\n{'='*120}")
    print(f"📊 RESUMEN T→P→L:")
    print(f"   ✓ Cursos válidos: {cursos_validos}/{len(por_curso)} ({cursos_validos/len(por_curso)*100:.1f}%)")
    print(f"   ✗ Cursos inválidos: {cursos_invalidos}/{len(por_curso)}")
    print("="*120)

def mostrar_estadisticas(asignaciones):
    """Muestra estadísticas generales del horario"""
    print("\n" + "="*120)
    print("📊 ESTADÍSTICAS DEL HORARIO GENERADO")
    print("="*120)
    
    total = len(asignaciones)
    por_tipo = defaultdict(int)
    por_dia = defaultdict(int)
    profesores = set()
    aulas = set()
    cursos = set()
    
    for asig in asignaciones:
        por_tipo[asig['session_type'][0]] += 1
        por_dia[asig['day']] += 1
        profesores.add(asig['professor_name'])
        aulas.add(asig['classroom_name'])
        cursos.add(asig['course_name'])
    
    print(f"\n📌 Totales:")
    print(f"   • Total asignaciones: {total}")
    print(f"   • Teorías: {por_tipo.get('T', 0)}")
    print(f"   • Prácticas: {por_tipo.get('P', 0)}")
    print(f"   • Laboratorios: {por_tipo.get('L', 0)}")
    
    print(f"\n👥 Recursos:")
    print(f"   • Cursos diferentes: {len(cursos)}")
    print(f"   • Profesores utilizados: {len(profesores)}")
    print(f"   • Aulas utilizadas: {len(aulas)}")
    
    print(f"\n📅 Distribución por día:")
    for dia in DIAS_ORDEN:
        if dia in por_dia:
            print(f"   • {dia}: {por_dia[dia]} sesiones")
    
    print("="*120)

def main():
    """Función principal"""
    # Obtener experiment_id
    if len(sys.argv) > 1:
        experiment_id = int(sys.argv[1])
    else:
        experiment_id = obtener_ultimo_experimento()
        print(f"ℹ️  No se especificó ID, usando último experimento: {experiment_id}")
    
    print("="*120)
    print(f"🎨 VISUALIZADOR DE HORARIOS - Experimento #{experiment_id}")
    print("="*120)
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*120)
    
    # Cargar datos
    print("\n🔄 Cargando asignaciones...")
    asignaciones = cargar_experimento(experiment_id)
    
    if not asignaciones:
        print(f"❌ No se encontraron asignaciones para el experimento {experiment_id}")
        return
    
    print(f"✅ {len(asignaciones)} asignaciones cargadas")
    
    # Mostrar menú
    while True:
        print("\n" + "="*120)
        print("OPCIONES DE VISUALIZACIÓN:")
        print("="*120)
        print("1. Horario completo (por día y hora)")
        print("2. Horario por curso (verificar T→P→L)")
        print("3. Validación T→P→L detallada")
        print("4. Estadísticas generales")
        print("5. Todo (todas las vistas)")
        print("0. Salir")
        print("="*120)
        
        opcion = input("\n👉 Selecciona una opción: ").strip()
        
        if opcion == "1":
            mostrar_horario_completo(asignaciones)
        elif opcion == "2":
            mostrar_horario_por_curso(asignaciones)
        elif opcion == "3":
            validar_tpl_visual(asignaciones)
        elif opcion == "4":
            mostrar_estadisticas(asignaciones)
        elif opcion == "5":
            mostrar_estadisticas(asignaciones)
            mostrar_horario_completo(asignaciones)
            mostrar_horario_por_curso(asignaciones)
            validar_tpl_visual(asignaciones)
        elif opcion == "0":
            print("\n👋 ¡Hasta luego!")
            break
        else:
            print("❌ Opción inválida")
        
        input("\n⏸️  Presiona ENTER para continuar...")

if __name__ == '__main__':
    main()
