"""
Validación REAL de experimentos en la base de datos
Usa reglas_pedagogicas_v2 (validación correcta) y proyecciones_loader

Este script detectará las violaciones T→P→L que la validación anterior
reportaba incorrectamente como "100% cumplimiento"
"""

import mysql.connector
import json
from datetime import datetime
from reglas_pedagogicas_v2 import ReglaspedagogicasV2
from proyecciones_loader import ProyeccionesLoader


def conectar_bd():
    """Conectar a base de datos"""
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='sistemas',
        database='upao_timetabling'
    )


def obtener_experimentos():
    """Obtener lista de experimentos ejecutados"""
    conn = conectar_bd()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT id, algoritmo, semestre, parametros, funcion_objetivo, 
               iniciado_en, terminado_en
        FROM algorithm_executions
        WHERE algoritmo LIKE 'ACO%'
        ORDER BY id
    """)
    
    experimentos = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return experimentos


def obtener_sesiones_experimento(experiment_id):
    """Obtener todas las sesiones de un experimento"""
    conn = conectar_bd()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT 
            psa.id,
            c.nombre as course_name,
            psa.course_id,
            psa.session_type,
            psa.day as dia,
            psa.start_time as hora_inicio,
            psa.end_time as hora_fin,
            psa.classroom_id,
            cl.nombre as classroom_name,
            psa.professor_id,
            p.nombre as professor_name
        FROM proposed_schedule_assignments psa
        JOIN courses c ON psa.course_id = c.id
        LEFT JOIN classrooms cl ON psa.classroom_id = cl.id
        LEFT JOIN professors p ON psa.professor_id = p.id
        WHERE psa.algorithm_execution_id = %s
        ORDER BY c.nombre, psa.day, psa.start_time
    """, (experiment_id,))
    
    sesiones = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return sesiones


def agrupar_sesiones_por_curso(sesiones):
    """Agrupa sesiones por curso"""
    cursos = {}
    
    for sesion in sesiones:
        course_name = sesion['course_name']
        if course_name not in cursos:
            cursos[course_name] = []
        cursos[course_name].append(sesion)
    
    return cursos


def contar_secciones_por_tipo(sesiones):
    """Cuenta cuántas secciones de cada tipo hay"""
    conteo = {'T': 0, 'P': 0, 'L': 0}
    
    for sesion in sesiones:
        tipo = str(sesion['session_type']).upper()
        if tipo in conteo:
            conteo[tipo] += 1
    
    return conteo


def validar_experimento(experiment_id, algoritmo, semestre):
    """Valida un experimento completo"""
    experiment_name = f"{algoritmo} - {semestre}"
    print(f"\n{'='*80}")
    print(f"🔍 VALIDANDO: {experiment_name} (ID: {experiment_id})")
    print(f"{'='*80}")
    
    # Obtener sesiones
    sesiones = obtener_sesiones_experimento(experiment_id)
    
    if not sesiones:
        print("⚠️ No se encontraron sesiones para este experimento")
        return None
    
    print(f"📊 Total sesiones: {len(sesiones)}")
    
    # Agrupar por curso
    cursos = agrupar_sesiones_por_curso(sesiones)
    print(f"📚 Total cursos: {len(cursos)}")
    
    # Validar T→P→L por curso
    cursos_validos = 0
    cursos_invalidos = 0
    total_violaciones = 0
    detalle_violaciones = []
    
    for course_name, sesiones_curso in cursos.items():
        es_valido, num_viol, detalle = ReglaspedagogicasV2.validar_orden_TPL(sesiones_curso)
        
        if es_valido:
            cursos_validos += 1
        else:
            cursos_invalidos += 1
            total_violaciones += num_viol
            detalle_violaciones.append({
                'curso': course_name,
                'num_violaciones': num_viol,
                'detalle': detalle
            })
    
    porcentaje_cumplimiento = (cursos_validos / len(cursos) * 100) if len(cursos) > 0 else 0
    
    print(f"\n📈 RESULTADOS VALIDACIÓN T→P→L:")
    print(f"   ✅ Cursos válidos: {cursos_validos}/{len(cursos)} ({porcentaje_cumplimiento:.1f}%)")
    print(f"   ❌ Cursos inválidos: {cursos_invalidos}")
    print(f"   🔴 Total violaciones: {total_violaciones}")
    
    if detalle_violaciones:
        print(f"\n⚠️ DETALLE DE VIOLACIONES:")
        for i, v in enumerate(detalle_violaciones[:10], 1):  # Mostrar primeras 10
            print(f"\n   {i}. {v['curso']} - {v['num_violaciones']} violacion(es)")
            for violacion in v['detalle']['violaciones']:
                print(f"      • {violacion['tipo']}: {violacion['mensaje']}")
        
        if len(detalle_violaciones) > 10:
            print(f"\n   ... y {len(detalle_violaciones) - 10} cursos más con violaciones")
    
    # Validar contra proyecciones
    print(f"\n📋 VALIDANDO CONTRA PROYECCIONES (Libro1.xlsx):")
    loader = ProyeccionesLoader()
    
    proyecciones_invalidas = 0
    detalle_proy_invalidas = []
    
    for course_name, sesiones_curso in cursos.items():
        conteo = contar_secciones_por_tipo(sesiones_curso)
        proyeccion = loader.obtener_proyeccion(course_name)
        
        if not proyeccion:
            proyecciones_invalidas += 1
            detalle_proy_invalidas.append({
                'curso': course_name,
                'error': 'No encontrado en proyecciones',
                'generado': conteo
            })
            continue
        
        # Comparar conteos
        dif_t = conteo['T'] - proyeccion['teoria']
        dif_p = conteo['P'] - proyeccion['practica']
        dif_l = conteo['L'] - proyeccion['laboratorio']
        
        if dif_t != 0 or dif_p != 0 or dif_l != 0:
            proyecciones_invalidas += 1
            detalle_proy_invalidas.append({
                'curso': course_name,
                'esperado': f"T:{proyeccion['teoria']} P:{proyeccion['practica']} L:{proyeccion['laboratorio']}",
                'generado': f"T:{conteo['T']} P:{conteo['P']} L:{conteo['L']}",
                'diferencias': f"T:{dif_t:+d} P:{dif_p:+d} L:{dif_l:+d}"
            })
    
    porcentaje_proy = ((len(cursos) - proyecciones_invalidas) / len(cursos) * 100) if len(cursos) > 0 else 0
    
    print(f"   ✅ Cursos que cumplen proyecciones: {len(cursos) - proyecciones_invalidas}/{len(cursos)} ({porcentaje_proy:.1f}%)")
    print(f"   ❌ Cursos que NO cumplen: {proyecciones_invalidas}")
    
    if detalle_proy_invalidas:
        print(f"\n   ⚠️ EJEMPLOS DE INCUMPLIMIENTO:")
        for i, v in enumerate(detalle_proy_invalidas[:10], 1):
            print(f"      {i}. {v['curso']}")
            print(f"         Esperado: {v.get('esperado', 'N/A')}")
            print(f"         Generado: {v.get('generado', 'N/A')}")
            if 'diferencias' in v:
                print(f"         Diferencias: {v['diferencias']}")
        
        if len(detalle_proy_invalidas) > 10:
            print(f"      ... y {len(detalle_proy_invalidas) - 10} más")
    
    return {
        'experiment_id': experiment_id,
        'experiment_name': experiment_name,
        'total_cursos': len(cursos),
        'total_sesiones': len(sesiones),
        'validacion_TPL': {
            'cursos_validos': cursos_validos,
            'cursos_invalidos': cursos_invalidos,
            'total_violaciones': total_violaciones,
            'porcentaje_cumplimiento': round(porcentaje_cumplimiento, 2),
            'detalle_violaciones': detalle_violaciones
        },
        'validacion_proyecciones': {
            'cursos_validos': len(cursos) - proyecciones_invalidas,
            'cursos_invalidos': proyecciones_invalidas,
            'porcentaje_cumplimiento': round(porcentaje_proy, 2),
            'detalle_invalidos': detalle_proy_invalidas
        }
    }


def generar_reporte_completo():
    """Genera reporte completo de todos los experimentos"""
    print("="*80)
    print("🔍 VALIDACIÓN REAL DE EXPERIMENTOS EN BASE DE DATOS")
    print("="*80)
    print("📅 Fecha:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("\nUSANDO:")
    print("   • reglas_pedagogicas_v2.py (validación CORRECTA)")
    print("   • proyecciones_loader.py (proyecciones de Libro1.xlsx)")
    print("="*80)
    
    experimentos = obtener_experimentos()
    print(f"\n📊 Total de experimentos encontrados: {len(experimentos)}")
    
    resultados = []
    
    for exp in experimentos:
        resultado = validar_experimento(exp['id'], exp['algoritmo'], exp['semestre'])
        if resultado:
            resultados.append(resultado)
    
    # Resumen general
    print(f"\n\n{'='*80}")
    print("📊 RESUMEN GENERAL DE TODOS LOS EXPERIMENTOS")
    print(f"{'='*80}")
    
    print(f"\n{'Experimento':<20} | {'T→P→L %':<10} | {'Viol.':<8} | {'Proy. %':<10}")
    print("-" * 80)
    
    for r in resultados:
        tpl_pct = r['validacion_TPL']['porcentaje_cumplimiento']
        tpl_viol = r['validacion_TPL']['total_violaciones']
        proy_pct = r['validacion_proyecciones']['porcentaje_cumplimiento']
        
        estado_tpl = "✅" if tpl_pct == 100 else "❌"
        estado_proy = "✅" if proy_pct == 100 else "❌"
        
        print(f"{r['experiment_name']:<20} | {estado_tpl} {tpl_pct:>5.1f}% | {tpl_viol:>6} | {estado_proy} {proy_pct:>5.1f}%")
    
    # Guardar resultados
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"validacion_real_experimentos_{timestamp}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n✅ Resultados guardados en: {output_file}")
    
    # Estadísticas finales
    print(f"\n{'='*80}")
    print("📈 ESTADÍSTICAS FINALES")
    print(f"{'='*80}")
    
    exps_100_tpl = sum(1 for r in resultados if r['validacion_TPL']['porcentaje_cumplimiento'] == 100)
    exps_100_proy = sum(1 for r in resultados if r['validacion_proyecciones']['porcentaje_cumplimiento'] == 100)
    
    print(f"\n🎯 Experimentos con 100% T→P→L: {exps_100_tpl}/{len(resultados)}")
    print(f"🎯 Experimentos con 100% Proyecciones: {exps_100_proy}/{len(resultados)}")
    
    if exps_100_tpl == 0:
        print("\n⚠️ NINGÚN EXPERIMENTO cumple 100% la regla T→P→L")
        print("   Esto confirma que la validación anterior tenía FALSOS POSITIVOS")
    
    if exps_100_proy == 0:
        print("\n⚠️ NINGÚN EXPERIMENTO respeta las proyecciones de Libro1.xlsx")
        print("   El sistema está inventando secciones que no están en las proyecciones")


if __name__ == '__main__':
    generar_reporte_completo()
