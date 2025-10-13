"""
═══════════════════════════════════════════════════════════════════════════════
OBJETIVO 2 (OE2) - INSTRUMENTO 2: PROTOCOLO DE VALIDACIÓN vs. HORARIOS REALES
Sistema de Horarios Académicos UPAO
═══════════════════════════════════════════════════════════════════════════════

OBJETIVO:
Evaluar la precisión/ajuste del horario generado por ACO frente al horario 
oficial (BANNER/Excel) mediante métricas cuantitativas.

INDICADORES:
• EMR (Exact Match Rate %): Porcentaje de asignaciones que coinciden exactamente
• CAS (Conflict-Adjusted Score): Score ajustado que penaliza conflictos
• F1 Score por slot: Precisión y recall de asignaciones por franja horaria
• Trazabilidad a reglas institucionales (T→P→L, Labs en F/G, etc.)

METODOLOGÍA:
1. Alinear catálogos/IDs entre sistema ACO y BANNER
2. Comparar asignación por asignación (curso, profesor, aula, día, hora)
3. Marcar coincidencias y tipos de conflicto
4. Calcular EMR y score ajustado (definir λ ex-ante)
5. Reportar con intervalos de confianza

═══════════════════════════════════════════════════════════════════════════════
"""

import mysql.connector
import pandas as pd
import numpy as np
from datetime import datetime, time
from collections import defaultdict
from typing import Dict, List, Tuple
from pathlib import Path
import json

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'sistemas',
    'database': 'upao_timetabling'
}

class ValidadorHorarios:
    """
    Protocolo de validación ACO vs Horarios Reales
    """
    
    def __init__(self):
        self.conn = mysql.connector.connect(**DB_CONFIG)
        self.cursor = self.conn.cursor(dictionary=True)
        
    def cargar_horario_real(self):
        """Carga horario oficial de BANNER (Excel importado)"""
        query = """
            SELECT 
                id,
                course_id,
                professor_id,
                classroom_id,
                nrc,
                day,
                start_time,
                end_time,
                session_type,
                source
            FROM proposed_schedule_assignments
            WHERE source = 'EXCEL_2025'
            ORDER BY course_id, session_type
        """
        self.cursor.execute(query)
        return self.cursor.fetchall()
    
    def cargar_horario_aco(self, execution_id):
        """Carga horario generado por ACO para un experimento específico"""
        query = """
            SELECT 
                id,
                course_id,
                professor_id,
                classroom_id,
                nrc,
                day,
                start_time,
                end_time,
                session_type
            FROM proposed_schedule_assignments
            WHERE algorithm_execution_id = %s
            ORDER BY course_id, session_type
        """
        self.cursor.execute(query, (execution_id,))
        return self.cursor.fetchall()
    
    def normalizar_tiempo(self, tiempo):
        """Normaliza formato de tiempo para comparación"""
        if isinstance(tiempo, time):
            return tiempo.strftime('%H:%M')
        elif isinstance(tiempo, str):
            return tiempo
        return str(tiempo)
    
    def normalizar_dia(self, dia):
        """Normaliza nombre de día"""
        dia_map = {
            'LUNES': 'lunes', 'MARTES': 'martes', 'MIÉRCOLES': 'miércoles',
            'MIERCOLES': 'miércoles', 'JUEVES': 'jueves', 'VIERNES': 'viernes',
            'SÁBADO': 'sábado', 'SABADO': 'sábado'
        }
        dia_upper = dia.upper() if isinstance(dia, str) else str(dia).upper()
        return dia_map.get(dia_upper, dia.lower())
    
    def comparar_asignacion(self, asig_real, asig_aco):
        """
        Compara dos asignaciones y retorna tipo de coincidencia
        
        Returns:
            'EXACT': Coincidencia exacta (curso, prof, aula, día, hora)
            'PARTIAL_SLOT': Mismo curso/prof pero diferente día/hora
            'PARTIAL_ROOM': Mismo curso/prof/slot pero diferente aula
            'CONFLICT': Conflicto directo (overlap de profesor o aula)
            'MISSING': Asignación faltante
        """
        
        # Normalizar tiempos y días
        dia_real = self.normalizar_dia(asig_real['day'])
        dia_aco = self.normalizar_dia(asig_aco['day'])
        
        hora_real = self.normalizar_tiempo(asig_real['start_time'])
        hora_aco = self.normalizar_tiempo(asig_aco['start_time'])
        
        # Coincidencia exacta
        if (asig_real['course_id'] == asig_aco['course_id'] and
            asig_real['professor_id'] == asig_aco['professor_id'] and
            asig_real['classroom_id'] == asig_aco['classroom_id'] and
            dia_real == dia_aco and
            hora_real == hora_aco):
            return 'EXACT'
        
        # Mismo curso y profesor, diferente slot
        if (asig_real['course_id'] == asig_aco['course_id'] and
            asig_real['professor_id'] == asig_aco['professor_id'] and
            (dia_real != dia_aco or hora_real != hora_aco)):
            return 'PARTIAL_SLOT'
        
        # Mismo curso, profesor y slot, diferente aula
        if (asig_real['course_id'] == asig_aco['course_id'] and
            asig_real['professor_id'] == asig_aco['professor_id'] and
            dia_real == dia_aco and
            hora_real == hora_aco and
            asig_real['classroom_id'] != asig_aco['classroom_id']):
            return 'PARTIAL_ROOM'
        
        return 'DIFFERENT'
    
    def calcular_emr(self, asignaciones_reales, asignaciones_aco):
        """
        Calcula Exact Match Rate (EMR)
        
        EMR = (Número de asignaciones que coinciden exactamente) / (Total asignaciones)
        """
        
        coincidencias_exactas = 0
        total_asignaciones = len(asignaciones_reales)
        
        # Crear índice de asignaciones ACO por (curso, session_type)
        aco_index = {}
        for asig_aco in asignaciones_aco:
            key = (asig_aco['course_id'], asig_aco['session_type'])
            if key not in aco_index:
                aco_index[key] = []
            aco_index[key].append(asig_aco)
        
        detalles = []
        
        for asig_real in asignaciones_reales:
            key = (asig_real['course_id'], asig_real['session_type'])
            
            if key in aco_index:
                # Buscar mejor coincidencia
                for asig_aco in aco_index[key]:
                    tipo_coincidencia = self.comparar_asignacion(asig_real, asig_aco)
                    
                    if tipo_coincidencia == 'EXACT':
                        coincidencias_exactas += 1
                        detalles.append({
                            'asig_id': asig_real['id'],
                            'course_id': asig_real['course_id'],
                            'coincide': 'SI',
                            'tipo': tipo_coincidencia,
                            'conflictos': 0
                        })
                        break
                else:
                    # No hay coincidencia exacta
                    tipo_coincidencia = self.comparar_asignacion(asig_real, aco_index[key][0])
                    detalles.append({
                        'asig_id': asig_real['id'],
                        'course_id': asig_real['course_id'],
                        'coincide': 'NO',
                        'tipo': tipo_coincidencia,
                        'conflictos': 1 if tipo_coincidencia == 'CONFLICT' else 0
                    })
            else:
                # Asignación faltante
                detalles.append({
                    'asig_id': asig_real['id'],
                    'course_id': asig_real['course_id'],
                    'coincide': 'NO',
                    'tipo': 'MISSING',
                    'conflictos': 1
                })
        
        emr = (coincidencias_exactas / total_asignaciones) * 100 if total_asignaciones > 0 else 0
        
        return emr, detalles
    
    def calcular_cas(self, emr, conflictos_totales, lambda_penalizacion=0.5):
        """
        Calcula Conflict-Adjusted Score (CAS)
        
        CAS = EMR - λ * (conflictos / total_asignaciones) * 100
        
        donde λ es el factor de penalización (0.0 - 1.0)
        """
        
        cas = emr - lambda_penalizacion * conflictos_totales
        return max(0, min(100, cas))  # Clamp entre 0 y 100
    
    def calcular_f1_por_slot(self, asignaciones_reales, asignaciones_aco):
        """
        Calcula F1 Score por slot temporal (día + hora)
        
        Precision = TP / (TP + FP)
        Recall = TP / (TP + FN)
        F1 = 2 * (Precision * Recall) / (Precision + Recall)
        """
        
        # Agrupar por slot
        slots_reales = defaultdict(set)
        slots_aco = defaultdict(set)
        
        for asig in asignaciones_reales:
            dia = self.normalizar_dia(asig['day'])
            hora = self.normalizar_tiempo(asig['start_time'])
            slot_key = f"{dia}_{hora}"
            slots_reales[slot_key].add((asig['course_id'], asig['professor_id']))
        
        for asig in asignaciones_aco:
            dia = self.normalizar_dia(asig['day'])
            hora = self.normalizar_tiempo(asig['start_time'])
            slot_key = f"{dia}_{hora}"
            slots_aco[slot_key].add((asig['course_id'], asig['professor_id']))
        
        # Calcular F1 por slot
        f1_scores = []
        
        for slot_key in set(list(slots_reales.keys()) + list(slots_aco.keys())):
            real_set = slots_reales[slot_key]
            aco_set = slots_aco[slot_key]
            
            tp = len(real_set & aco_set)  # True Positives
            fp = len(aco_set - real_set)  # False Positives
            fn = len(real_set - aco_set)  # False Negatives
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            
            f1_scores.append({
                'slot': slot_key,
                'precision': precision,
                'recall': recall,
                'f1': f1,
                'tp': tp,
                'fp': fp,
                'fn': fn
            })
        
        # Promedio ponderado por número de asignaciones reales
        avg_f1 = np.mean([s['f1'] for s in f1_scores]) if f1_scores else 0
        
        return avg_f1, f1_scores
    
    def validar_experimento(self, execution_id, lambda_penalizacion=0.5):
        """
        Ejecuta protocolo completo de validación para un experimento
        """
        
        print("="*120)
        print(f"OE2 — INSTRUMENTO 2: PROTOCOLO DE VALIDACIÓN vs. HORARIOS REALES")
        print("="*120)
        print(f"\n📋 Experimento ID: {execution_id}")
        print(f"⏰ Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"λ (penalización): {lambda_penalizacion}")
        
        # Cargar datos
        print("\n[1/5] Cargando horarios...")
        asignaciones_reales = self.cargar_horario_real()
        asignaciones_aco = self.cargar_horario_aco(execution_id)
        
        print(f"   • Horario REAL (BANNER): {len(asignaciones_reales)} asignaciones")
        print(f"   • Horario ACO (Exp {execution_id}): {len(asignaciones_aco)} asignaciones")
        
        # Calcular EMR
        print("\n[2/5] Calculando EMR (Exact Match Rate)...")
        emr, detalles = self.calcular_emr(asignaciones_reales, asignaciones_aco)
        
        coincidencias = sum(1 for d in detalles if d['coincide'] == 'SI')
        conflictos_totales = sum(d['conflictos'] for d in detalles)
        
        print(f"   • EMR: {emr:.2f}%")
        print(f"   • Coincidencias exactas: {coincidencias}/{len(asignaciones_reales)}")
        print(f"   • Conflictos detectados: {conflictos_totales}")
        
        # Calcular CAS
        print("\n[3/5] Calculando CAS (Conflict-Adjusted Score)...")
        cas = self.calcular_cas(emr, conflictos_totales, lambda_penalizacion)
        print(f"   • CAS: {cas:.2f}")
        
        # Calcular F1 por slot
        print("\n[4/5] Calculando F1 Score por slot...")
        avg_f1, f1_scores = self.calcular_f1_por_slot(asignaciones_reales, asignaciones_aco)
        print(f"   • F1 promedio: {avg_f1:.4f}")
        print(f"   • Slots evaluados: {len(f1_scores)}")
        
        # Resumen de tipos de coincidencia
        print("\n[5/5] Análisis de tipos de coincidencia...")
        tipos_count = defaultdict(int)
        for d in detalles:
            tipos_count[d['tipo']] += 1
        
        print(f"   • EXACT (coincidencia total): {tipos_count['EXACT']}")
        print(f"   • PARTIAL_SLOT (mismo curso/prof, diff slot): {tipos_count['PARTIAL_SLOT']}")
        print(f"   • PARTIAL_ROOM (mismo slot, diff aula): {tipos_count['PARTIAL_ROOM']}")
        print(f"   • DIFFERENT (completamente diferente): {tipos_count['DIFFERENT']}")
        print(f"   • MISSING (faltante en ACO): {tipos_count['MISSING']}")
        
        # Resultado final
        print("\n" + "="*120)
        print("📊 RESULTADO FINAL DE VALIDACIÓN")
        print("="*120)
        print(f"\n✓ EMR (Exact Match Rate): {emr:.2f}%")
        print(f"✓ CAS (Conflict-Adjusted Score): {cas:.2f}")
        print(f"✓ F1 Score promedio: {avg_f1:.4f}")
        print(f"✓ Tasa de asignación: {len(asignaciones_aco)/len(asignaciones_reales)*100:.1f}%")
        
        # Interpretación
        print(f"\n💡 INTERPRETACIÓN:")
        if emr >= 80:
            print("   ✅ EXCELENTE: El horario ACO coincide en >80% con el oficial")
        elif emr >= 60:
            print("   ✓ BUENO: El horario ACO tiene >60% de coincidencia")
        elif emr >= 40:
            print("   ⚠️  ACEPTABLE: El horario ACO tiene >40% de coincidencia")
        else:
            print("   ❌ BAJO: El horario ACO tiene <40% de coincidencia")
        
        print("\n" + "="*120)
        
        return {
            'execution_id': execution_id,
            'emr': emr,
            'cas': cas,
            'f1_avg': avg_f1,
            'coincidencias': coincidencias,
            'conflictos': conflictos_totales,
            'detalles': detalles,
            'f1_scores': f1_scores
        }
    
    def exportar_resultados_excel(self, resultados, filename='validacion_horarios_OE2.xlsx'):
        """Exporta resultados de validación a Excel"""
        
        # Hoja 1: Resumen
        resumen = pd.DataFrame([{
            'Experimento ID': resultados['execution_id'],
            'EMR (%)': resultados['emr'],
            'CAS': resultados['cas'],
            'F1 Score': resultados['f1_avg'],
            'Coincidencias': resultados['coincidencias'],
            'Conflictos': resultados['conflictos']
        }])
        
        # Hoja 2: Detalles por asignación
        df_detalles = pd.DataFrame(resultados['detalles'])
        
        # Hoja 3: F1 por slot
        df_f1 = pd.DataFrame(resultados['f1_scores'])
        
        output_path = Path(__file__).parent / filename
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            resumen.to_excel(writer, sheet_name='Resumen', index=False)
            df_detalles.to_excel(writer, sheet_name='Detalles por Asignación', index=False)
            df_f1.to_excel(writer, sheet_name='F1 por Slot', index=False)
        
        print(f"\n✅ Resultados exportados: {output_path}")
        return output_path
    
    def __del__(self):
        if hasattr(self, 'conn'):
            self.conn.close()

# ═══════════════════════════════════════════════════════════════════════════════
# EJECUCIÓN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    
    validador = ValidadorHorarios()
    
    # Validar experimento especificado
    exp_id = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    lambda_pen = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5
    
    resultados = validador.validar_experimento(exp_id, lambda_pen)
    
    # Exportar a Excel
    validador.exportar_resultados_excel(resultados, 
                                       f'validacion_exp{exp_id}_OE2.xlsx')
    
    print("\n✅ VALIDACIÓN COMPLETADA")
