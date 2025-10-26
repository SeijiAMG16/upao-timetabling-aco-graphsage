"""
Módulo CORREGIDO de validación de reglas pedagógicas
Versión 2.0 - Validación REAL de orden T→P→L
Autor: Sistema ACO-GraphSAGE UPAO
Fecha: 2025

CORRECCIONES CRÍTICAS:
- Validación ahora compara timestamps reales (día + hora)
- Verifica que TODAS las teorías ocurran antes que CUALQUIER práctica/lab
- Verifica que TODAS las prácticas ocurran antes que CUALQUIER lab
- Elimina falsos positivos de versión anterior
"""

from datetime import time
from typing import List, Dict, Tuple


class ReglaspedagogicasV2:
    """
    Validador de reglas pedagógicas para horarios universitarios
    
    REGLA PRINCIPAL: T → P → L (Teoría antes de Práctica antes de Laboratorio)
    """
    
    # Mapeo de días a números (para ordenamiento)
    DIA_NUMERO = {
        'LUNES': 1,
        'MARTES': 2,
        'MIERCOLES': 3,
        'MIÉRCOLES': 3,
        'JUEVES': 4,
        'VIERNES': 5,
        'SABADO': 6,
        'SÁBADO': 6,
        'DOMINGO': 7
    }
    
    @classmethod
    def normalizar_dia(cls, dia: str) -> str:
        """Normaliza nombre de día"""
        if not dia:
            return ''
        dia_upper = str(dia).strip().upper()
        # Remover acentos
        dia_upper = dia_upper.replace('Á', 'A').replace('É', 'E').replace('Í', 'I')
        dia_upper = dia_upper.replace('Ó', 'O').replace('Ú', 'U')
        return dia_upper
    
    @classmethod
    def normalizar_tiempo(cls, hora_str: str) -> time:
        """
        Convierte string de hora a objeto time
        
        Formatos aceptados:
        - "08:00:00"
        - "08:00"
        - "8:00"
        """
        if not hora_str:
            return time(0, 0)
        
        hora_str = str(hora_str).strip()
        
        try:
            parts = hora_str.split(':')
            hora = int(parts[0])
            minuto = int(parts[1]) if len(parts) > 1 else 0
            
            return time(hora, minuto)
        except:
            return time(0, 0)
    
    @classmethod
    def crear_timestamp(cls, dia: str, hora: str) -> Tuple[int, time]:
        """
        Crea timestamp comparable (día_numero, hora_objeto)
        
        Returns:
            tuple (dia_num, hora_obj) para comparación
        """
        dia_norm = cls.normalizar_dia(dia)
        dia_num = cls.DIA_NUMERO.get(dia_norm, 99)
        hora_obj = cls.normalizar_tiempo(hora)
        
        return (dia_num, hora_obj)
    
    @classmethod
    def validar_orden_TPL(cls, sesiones_curso: List[Dict]) -> Tuple[bool, int, Dict]:
        """
        VALIDACIÓN CORREGIDA de orden T→P→L
        
        Args:
            sesiones_curso: Lista de sesiones del curso con keys:
                - session_type: 'T', 'P', 'L'
                - dia: Día de la semana
                - hora_inicio: Hora de inicio
        
        Returns:
            tuple (es_valido, num_violaciones, detalle_violaciones)
        
        REGLAS:
        1. Si hay P o L sin T → VIOLACIÓN
        2. TODAS las T deben ocurrir antes que CUALQUIER P o L
        3. TODAS las P deben ocurrir antes que CUALQUIER L
        """
        if not sesiones_curso:
            return True, 0, {}
        
        teorias = []
        practicas = []
        laboratorios = []
        
        # Clasificar sesiones y crear timestamps
        for sesion in sesiones_curso:
            tipo_raw = str(sesion.get('session_type', '')).strip().upper()
            # Extraer solo la primera letra (T1, T2 -> T; P1, P2 -> P; L1, L2 -> L)
            tipo = tipo_raw[0] if tipo_raw else ''
            
            dia = sesion.get('dia', sesion.get('day', ''))
            hora = sesion.get('hora_inicio', sesion.get('start_time', ''))
            
            timestamp = cls.crear_timestamp(dia, hora)
            
            if tipo in ['T', 'TEORIA', 'TEORÍA']:
                teorias.append((timestamp, sesion))
            elif tipo in ['P', 'PRACTICA', 'PRÁCTICA']:
                practicas.append((timestamp, sesion))
            elif tipo in ['L', 'LABORATORIO', 'LAB']:
                laboratorios.append((timestamp, sesion))
        
        violaciones = []
        detalle = {
            'teorias': len(teorias),
            'practicas': len(practicas),
            'laboratorios': len(laboratorios)
        }
        
        # REGLA 1: Si hay P o L sin T → VIOLACIÓN
        if (practicas or laboratorios) and not teorias:
            violaciones.append({
                'tipo': 'SIN_TEORIA',
                'mensaje': f'Curso tiene {len(practicas)} P y {len(laboratorios)} L pero 0 T'
            })
        
        # REGLA 2: TODAS las T antes que CUALQUIER P o L
        if teorias and (practicas or laboratorios):
            max_teoria_ts = max(t[0] for t in teorias)
            
            # Verificar contra prácticas
            for p_ts, p_sesion in practicas:
                if p_ts <= max_teoria_ts:
                    violaciones.append({
                        'tipo': 'P_ANTES_QUE_T',
                        'mensaje': f'Práctica en {p_sesion.get("dia")} {p_sesion.get("hora_inicio")} ' +
                                   f'ocurre antes/durante teorías'
                    })
            
            # Verificar contra laboratorios
            for l_ts, l_sesion in laboratorios:
                if l_ts <= max_teoria_ts:
                    violaciones.append({
                        'tipo': 'L_ANTES_QUE_T',
                        'mensaje': f'Laboratorio en {l_sesion.get("dia")} {l_sesion.get("hora_inicio")} ' +
                                   f'ocurre antes/durante teorías'
                    })
        
        # REGLA 3: TODAS las P antes que CUALQUIER L
        if practicas and laboratorios:
            max_practica_ts = max(p[0] for p in practicas)
            
            for l_ts, l_sesion in laboratorios:
                if l_ts <= max_practica_ts:
                    violaciones.append({
                        'tipo': 'L_ANTES_QUE_P',
                        'mensaje': f'Laboratorio en {l_sesion.get("dia")} {l_sesion.get("hora_inicio")} ' +
                                   f'ocurre antes/durante prácticas'
                    })
        
        detalle['violaciones'] = violaciones
        detalle['num_violaciones'] = len(violaciones)
        
        es_valido = len(violaciones) == 0
        
        return es_valido, len(violaciones), detalle
    
    @classmethod
    def validar_sin_solapamientos(cls, sesiones_profesor: List[Dict]) -> Tuple[bool, int]:
        """
        Valida que un profesor no tenga sesiones solapadas
        
        Args:
            sesiones_profesor: Lista de sesiones del profesor
        
        Returns:
            tuple (es_valido, num_solapamientos)
        """
        if len(sesiones_profesor) <= 1:
            return True, 0
        
        # Crear lista de (timestamp_inicio, timestamp_fin, sesion)
        sesiones_con_tiempo = []
        
        for sesion in sesiones_profesor:
            dia = sesion.get('dia', sesion.get('day', ''))
            hora_inicio = sesion.get('hora_inicio', sesion.get('start_time', ''))
            hora_fin = sesion.get('hora_fin', sesion.get('end_time', ''))
            
            ts_inicio = cls.crear_timestamp(dia, hora_inicio)
            ts_fin = cls.crear_timestamp(dia, hora_fin)
            
            sesiones_con_tiempo.append((ts_inicio, ts_fin, sesion))
        
        # Ordenar por timestamp de inicio
        sesiones_con_tiempo.sort(key=lambda x: x[0])
        
        solapamientos = 0
        
        # Verificar solapamientos
        for i in range(len(sesiones_con_tiempo) - 1):
            ts_fin_i = sesiones_con_tiempo[i][1]
            ts_inicio_j = sesiones_con_tiempo[i + 1][0]
            
            if ts_inicio_j < ts_fin_i:
                solapamientos += 1
        
        es_valido = solapamientos == 0
        
        return es_valido, solapamientos
    
    @classmethod
    def calcular_penalizacion_pedagogica(cls, horario_completo: Dict) -> Dict:
        """
        Calcula penalizaciones pedagógicas para un horario completo
        
        Args:
            horario_completo: dict {curso_id: [sesiones]}
        
        Returns:
            dict con métricas de penalización
        """
        total_cursos = len(horario_completo)
        cursos_validos_TPL = 0
        total_violaciones_TPL = 0
        detalle_violaciones = []
        
        for curso_id, sesiones in horario_completo.items():
            es_valido, num_violaciones, detalle = cls.validar_orden_TPL(sesiones)
            
            if es_valido:
                cursos_validos_TPL += 1
            else:
                total_violaciones_TPL += num_violaciones
                detalle_violaciones.append({
                    'curso_id': curso_id,
                    'violaciones': num_violaciones,
                    'detalle': detalle
                })
        
        porcentaje_cumplimiento = (cursos_validos_TPL / total_cursos * 100) if total_cursos > 0 else 0
        
        return {
            'total_cursos': total_cursos,
            'cursos_validos_TPL': cursos_validos_TPL,
            'cursos_invalidos_TPL': total_cursos - cursos_validos_TPL,
            'total_violaciones_TPL': total_violaciones_TPL,
            'porcentaje_cumplimiento_TPL': round(porcentaje_cumplimiento, 2),
            'detalle_violaciones': detalle_violaciones
        }


def test_validacion():
    """Test de validación con casos conocidos"""
    print("="*70)
    print("TEST DE VALIDACIÓN T→P→L (VERSIÓN CORREGIDA)")
    print("="*70)
    
    # Caso 1: Orden correcto T→P→L
    print("\n1️⃣ CASO CORRECTO: T (Lunes 8:00) → P (Martes 10:00) → L (Miércoles 14:00)")
    sesiones_correctas = [
        {'session_type': 'T', 'dia': 'LUNES', 'hora_inicio': '08:00'},
        {'session_type': 'P', 'dia': 'MARTES', 'hora_inicio': '10:00'},
        {'session_type': 'L', 'dia': 'MIERCOLES', 'hora_inicio': '14:00'}
    ]
    valido, num_viol, detalle = ReglaspedagogicasV2.validar_orden_TPL(sesiones_correctas)
    print(f"   Resultado: {'✅ VÁLIDO' if valido else '❌ INVÁLIDO'}")
    print(f"   Violaciones: {num_viol}")
    
    # Caso 2: L antes que T (VIOLACIÓN)
    print("\n2️⃣ CASO INCORRECTO: L (Lunes 8:00) antes que T (Martes 10:00)")
    sesiones_incorrectas = [
        {'session_type': 'L', 'dia': 'LUNES', 'hora_inicio': '08:00'},
        {'session_type': 'T', 'dia': 'MARTES', 'hora_inicio': '10:00'}
    ]
    valido, num_viol, detalle = ReglaspedagogicasV2.validar_orden_TPL(sesiones_incorrectas)
    print(f"   Resultado: {'✅ VÁLIDO' if valido else '❌ INVÁLIDO'}")
    print(f"   Violaciones: {num_viol}")
    if detalle['violaciones']:
        for v in detalle['violaciones']:
            print(f"   • {v['tipo']}: {v['mensaje']}")
    
    # Caso 3: P sin T (VIOLACIÓN)
    print("\n3️⃣ CASO INCORRECTO: Solo P sin T")
    sesiones_sin_teoria = [
        {'session_type': 'P', 'dia': 'LUNES', 'hora_inicio': '08:00'},
        {'session_type': 'P', 'dia': 'MARTES', 'hora_inicio': '10:00'}
    ]
    valido, num_viol, detalle = ReglaspedagogicasV2.validar_orden_TPL(sesiones_sin_teoria)
    print(f"   Resultado: {'✅ VÁLIDO' if valido else '❌ INVÁLIDO'}")
    print(f"   Violaciones: {num_viol}")
    if detalle['violaciones']:
        for v in detalle['violaciones']:
            print(f"   • {v['tipo']}: {v['mensaje']}")
    
    print("\n" + "="*70)


if __name__ == '__main__':
    test_validacion()
