"""
Análisis Retrospectivo de Experimentos con Reglas Pedagógicas
Aplica las reglas pedagógicas a los experimentos ya ejecutados para comparar
"""

import mysql.connector
from reglas_pedagogicas import ReglasInstitucionales
from collections import defaultdict

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'sistemas',
    'database': 'upao_timetabling'
}

def cargar_solucion_experimento(execution_id):
    """Carga la solución de un experimento desde la BD"""
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)
    
    query = """
        SELECT 
            professor_id,
            course_id,
            classroom_id as aula_id,
            nrc,
            day as dia,
            start_time as hora_inicio,
            end_time as hora_fin,
            session_type
        FROM proposed_schedule_assignments
        WHERE algorithm_execution_id = %s
    """
    
    cursor.execute(query, (execution_id,))
    solucion = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return solucion

def analizar_experimento(exp_id):
    """Analiza un experimento con reglas pedagógicas"""
    print(f"\n{'='*80}")
    print(f"📊 ANALIZANDO EXPERIMENTO {exp_id}")
    print(f"{'='*80}")
    
    try:
        solucion = cargar_solucion_experimento(exp_id)
        
        if not solucion:
            print(f"⚠️  No se encontraron asignaciones para experimento {exp_id}")
            return None
        
        print(f"✅ {len(solucion)} asignaciones cargadas")
        
        # Evaluar calidad
        metricas = ReglasInstitucionales.evaluar_calidad_horario(solucion)
        penalizacion, _ = ReglasInstitucionales.penalizacion_total(solucion)
        
        print(f"\n🎓 Reglas Pedagógicas:")
        print(f"   • Orden T→P→L correcto: {metricas['cursos_validos_TPL']}/{metricas['cursos_totales']} cursos ({metricas['porcentaje_TPL_correcto']:.1f}%)")
        print(f"   • Violaciones T→P→L: {metricas['violaciones_TPL']}")
        
        print(f"\n📅 Distribución Temporal:")
        print(f"   • Penalización distribución: {metricas['penalizacion_distribucion']}")
        print(f"   • Penalización espaciado: {metricas['penalizacion_espaciado']}")
        
        print(f"\n⏰ Horarios Prime (Teorías 8:00-12:00 Lun-Jue):")
        print(f"   • Penalización: {metricas['penalizacion_horarios_prime']}")
        
        print(f"\n⚠️  Conflictos:")
        print(f"   • Conflictos profesor: {metricas['conflictos_profesor']}")
        print(f"   • Conflictos aula: {metricas['conflictos_aula']}")
        
        print(f"\n🏆 Penalización Total Pedagógica: {penalizacion:,.0f}")
        
        return metricas
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def comparar_experimentos(exp_ids):
    """Compara múltiples experimentos"""
    print(f"\n{'='*80}")
    print(f"📊 COMPARACIÓN DE EXPERIMENTOS")
    print(f"{'='*80}\n")
    
    resultados = {}
    
    for exp_id in exp_ids:
        metricas = analizar_experimento(exp_id)
        if metricas:
            resultados[exp_id] = metricas
    
    # Tabla comparativa
    print(f"\n{'='*80}")
    print(f"📋 TABLA COMPARATIVA")
    print(f"{'='*80}\n")
    
    print(f"{'Exp':<5} | {'T→P→L OK':<10} | {'Viol TPL':<10} | {'Conf Prof':<12} | {'Conf Aula':<12} | {'Pen Total':<15}")
    print(f"{'-'*80}")
    
    for exp_id, metricas in resultados.items():
        penalizacion, _ = ReglasInstitucionales.penalizacion_total(
            cargar_solucion_experimento(exp_id)
        )
        
        print(f"{exp_id:<5} | "
              f"{metricas['cursos_validos_TPL']:>3}/{metricas['cursos_totales']:<3} "
              f"({metricas['porcentaje_TPL_correcto']:>5.1f}%) | "
              f"{metricas['violaciones_TPL']:>10} | "
              f"{metricas['conflictos_profesor']:>12} | "
              f"{metricas['conflictos_aula']:>12} | "
              f"{penalizacion:>15,.0f}")
    
    # Identificar mejor
    if resultados:
        mejor_exp = min(resultados.items(), 
                        key=lambda x: ReglasInstitucionales.penalizacion_total(
                            cargar_solucion_experimento(x[0])
                        )[0])
        
        print(f"\n🏆 MEJOR EXPERIMENTO: {mejor_exp[0]}")
        print(f"   • {mejor_exp[1]['porcentaje_TPL_correcto']:.1f}% cursos con T→P→L correcto")
        print(f"   • {mejor_exp[1]['conflictos_profesor']} conflictos profesor")
        print(f"   • {mejor_exp[1]['conflictos_aula']} conflictos aula")

if __name__ == "__main__":
    print("="*80)
    print("🔬 ANÁLISIS RETROSPECTIVO CON REGLAS PEDAGÓGICAS")
    print("="*80)
    
    # Analizar los mejores experimentos
    experimentos = [9, 10, 11, 12, 13, 14, 15]
    
    print(f"\nAnalizando experimentos: {experimentos}")
    print("Aplicando reglas pedagógicas institucionales UPAO...\n")
    
    comparar_experimentos(experimentos)
    
    print(f"\n{'='*80}")
    print("✅ ANÁLISIS COMPLETADO")
    print(f"{'='*80}")
