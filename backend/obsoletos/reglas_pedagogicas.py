"""
Reglas Pedagógicas para Optimización de Horarios Académicos
Implementa las restricciones institucionales UPAO para horarios de calidad
"""

from collections import defaultdict
from datetime import datetime, time

class ReglasInstitucionales:
    """
    Reglas pedagógicas basadas en mejores prácticas académicas:
    1. T→P→L: Teorías antes que Prácticas/Laboratorios
    2. Distribución temporal: Evitar sobrecarga en un día
    3. Espaciado: Teorías y prácticas con días de separación
    4. Preferencias horarias: Teorías en horarios prime (Lun-Jue mañana)
    """
    
    # Mapeo de días a números para comparación
    DIA_NUMERO = {
        'LUNES': 1,
        'MARTES': 2,
        'MIÉRCOLES': 3,
        'MIERCOLES': 3,  # Variante sin tilde
        'JUEVES': 4,
        'VIERNES': 5,
        'SÁBADO': 6,
        'SABADO': 6  # Variante sin tilde
    }
    
    # Horarios prime para teorías (8:00-12:00, Lun-Jue)
    HORARIOS_PRIME_TEORIA = [
        ('08:00:00', '10:00:00'),
        ('10:00:00', '12:00:00'),
        ('08:00:00', '09:00:00'),
        ('09:00:00', '10:00:00'),
        ('10:00:00', '11:00:00'),
        ('11:00:00', '12:00:00'),
    ]
    
    DIAS_TEORIA_PREFERIDOS = ['LUNES', 'MARTES', 'MIÉRCOLES', 'MIERCOLES', 'JUEVES']
    
    @staticmethod
    def normalizar_dia(dia):
        """Normaliza el día a mayúsculas sin tildes"""
        dia_upper = str(dia).upper()
        # Reemplazar vocales con tilde
        dia_upper = dia_upper.replace('Á', 'A').replace('É', 'E').replace('Í', 'I')
        dia_upper = dia_upper.replace('Ó', 'O').replace('Ú', 'U')
        return dia_upper
    
    @staticmethod
    def normalizar_tiempo(tiempo):
        """Convierte tiempo a objeto time para comparación"""
        if isinstance(tiempo, time):
            return tiempo
        elif isinstance(tiempo, str):
            try:
                # Formato HH:MM:SS o HH:MM
                partes = tiempo.split(':')
                if len(partes) == 2:
                    return time(int(partes[0]), int(partes[1]), 0)
                elif len(partes) == 3:
                    return time(int(partes[0]), int(partes[1]), int(partes[2]))
            except:
                pass
        return None
    
    @classmethod
    def agrupar_por_curso(cls, solucion):
        """Agrupa asignaciones por curso"""
        cursos = defaultdict(list)
        for asig in solucion:
            cursos[asig['course_id']].append(asig)
        return cursos
    
    @classmethod
    def validar_orden_TPL(cls, sesiones_curso):
        """
        Valida que Teorías (T) ocurran antes que Prácticas (P) o Laboratorios (L)
        
        Args:
            sesiones_curso: Lista de sesiones de un mismo curso
        
        Returns:
            (bool, int): (válido, cantidad de violaciones)
        """
        teorias = []
        practicas = []
        laboratorios = []
        
        for sesion in sesiones_curso:
            tipo = str(sesion.get('session_type', '')).upper()
            dia = cls.normalizar_dia(sesion.get('dia', ''))
            dia_num = cls.DIA_NUMERO.get(dia, 99)
            
            if tipo == 'T' or tipo == 'TEORIA':
                teorias.append((dia_num, sesion))
            elif tipo == 'P' or tipo == 'PRACTICA':
                practicas.append((dia_num, sesion))
            elif tipo == 'L' or tipo == 'LABORATORIO':
                laboratorios.append((dia_num, sesion))
        
        violaciones = 0
        
        # Si hay prácticas o labs, debe haber al menos una teoría
        if (practicas or laboratorios) and not teorias:
            violaciones += len(practicas) + len(laboratorios)
            return False, violaciones
        
        # La primera teoría debe ser antes que cualquier práctica/lab
        if teorias:
            min_teoria_dia = min(t[0] for t in teorias)
            
            for dia_num, _ in practicas + laboratorios:
                if dia_num < min_teoria_dia:
                    violaciones += 1
        
        return violaciones == 0, violaciones
    
    @classmethod
    def validar_distribucion_temporal(cls, sesiones_curso):
        """
        Valida que no haya sobrecarga en un solo día
        Máximo 2 sesiones del mismo curso por día (idealmente 1)
        
        Returns:
            (bool, int): (válido, penalización)
        """
        sesiones_por_dia = defaultdict(list)
        
        for sesion in sesiones_curso:
            dia = cls.normalizar_dia(sesion.get('dia', ''))
            sesiones_por_dia[dia].append(sesion)
        
        penalizacion = 0
        for dia, sesiones in sesiones_por_dia.items():
            if len(sesiones) > 2:
                # Penalización severa por más de 2 sesiones/día
                penalizacion += (len(sesiones) - 2) * 100
            elif len(sesiones) == 2:
                # Penalización leve por 2 sesiones/día
                penalizacion += 20
        
        return penalizacion == 0, penalizacion
    
    @classmethod
    def validar_espaciado_sesiones(cls, sesiones_curso):
        """
        Valida que haya al menos 1 día entre teoría y práctica del mismo curso
        
        Returns:
            (bool, int): (válido, penalización)
        """
        teorias = []
        practicas = []
        
        for sesion in sesiones_curso:
            tipo = str(sesion.get('session_type', '')).upper()
            dia = cls.normalizar_dia(sesion.get('dia', ''))
            dia_num = cls.DIA_NUMERO.get(dia, 99)
            
            if tipo == 'T' or tipo == 'TEORIA':
                teorias.append(dia_num)
            elif tipo in ['P', 'L', 'PRACTICA', 'LABORATORIO']:
                practicas.append(dia_num)
        
        penalizacion = 0
        for teoria_dia in teorias:
            for practica_dia in practicas:
                diff = abs(practica_dia - teoria_dia)
                if diff == 0:
                    # Teoría y práctica el mismo día (malo)
                    penalizacion += 50
                elif diff == 1:
                    # Muy juntas (días consecutivos)
                    penalizacion += 10
        
        return penalizacion == 0, penalizacion
    
    @classmethod
    def validar_horarios_prime_teoria(cls, sesiones_curso):
        """
        Valida que teorías estén en horarios prime (8:00-12:00, Lun-Jue)
        
        Returns:
            (bool, int): (válido, penalización)
        """
        penalizacion = 0
        
        for sesion in sesiones_curso:
            tipo = str(sesion.get('session_type', '')).upper()
            
            if tipo == 'T' or tipo == 'TEORIA':
                dia = cls.normalizar_dia(sesion.get('dia', ''))
                hora_inicio = cls.normalizar_tiempo(sesion.get('hora_inicio', ''))
                
                # Verificar día
                if dia not in cls.DIAS_TEORIA_PREFERIDOS:
                    penalizacion += 30  # Teoría en viernes/sábado
                
                # Verificar horario
                if hora_inicio:
                    hora_prime = False
                    for inicio_prime, fin_prime in cls.HORARIOS_PRIME_TEORIA:
                        inicio_t = cls.normalizar_tiempo(inicio_prime)
                        fin_t = cls.normalizar_tiempo(fin_prime)
                        
                        if inicio_t and fin_t:
                            if inicio_t <= hora_inicio < fin_t:
                                hora_prime = True
                                break
                    
                    if not hora_prime:
                        penalizacion += 20  # Teoría fuera de horario prime
        
        return penalizacion == 0, penalizacion
    
    @classmethod
    def validar_conflicto_profesor_aula(cls, solucion):
        """
        Valida que no haya conflictos de profesor o aula en el mismo slot
        
        Returns:
            (conflictos_profesor, conflictos_aula)
        """
        slots = defaultdict(lambda: {'profesores': set(), 'aulas': set()})
        
        conflictos_profesor = 0
        conflictos_aula = 0
        
        for asig in solucion:
            dia = cls.normalizar_dia(asig.get('dia', ''))
            hora_inicio = str(asig.get('hora_inicio', ''))
            slot_key = f"{dia}_{hora_inicio}"
            
            profesor_id = asig.get('professor_id')
            aula_id = asig.get('aula_id')
            
            # Verificar conflicto de profesor
            if profesor_id in slots[slot_key]['profesores']:
                conflictos_profesor += 1
                asig['conflicto_profesor'] = True
            else:
                slots[slot_key]['profesores'].add(profesor_id)
            
            # Verificar conflicto de aula
            if aula_id in slots[slot_key]['aulas']:
                conflictos_aula += 1
                asig['conflicto_aula'] = True
            else:
                slots[slot_key]['aulas'].add(aula_id)
        
        return conflictos_profesor, conflictos_aula
    
    @classmethod
    def evaluar_calidad_horario(cls, solucion):
        """
        Evaluación integral de calidad del horario
        
        Returns:
            dict con todas las métricas de calidad
        """
        cursos = cls.agrupar_por_curso(solucion)
        
        # Métricas
        violaciones_TPL = 0
        penalizacion_distribucion = 0
        penalizacion_espaciado = 0
        penalizacion_horarios_prime = 0
        
        cursos_validos_TPL = 0
        cursos_totales = len(cursos)
        
        for course_id, sesiones in cursos.items():
            # Regla 1: Orden T→P→L
            valido_TPL, viols = cls.validar_orden_TPL(sesiones)
            violaciones_TPL += viols
            if valido_TPL:
                cursos_validos_TPL += 1
            
            # Regla 2: Distribución temporal
            _, pen_dist = cls.validar_distribucion_temporal(sesiones)
            penalizacion_distribucion += pen_dist
            
            # Regla 3: Espaciado
            _, pen_esp = cls.validar_espaciado_sesiones(sesiones)
            penalizacion_espaciado += pen_esp
            
            # Regla 4: Horarios prime
            _, pen_prime = cls.validar_horarios_prime_teoria(sesiones)
            penalizacion_horarios_prime += pen_prime
        
        # Regla 5: Conflictos
        conflictos_prof, conflictos_aula = cls.validar_conflicto_profesor_aula(solucion)
        
        return {
            'violaciones_TPL': violaciones_TPL,
            'penalizacion_distribucion': penalizacion_distribucion,
            'penalizacion_espaciado': penalizacion_espaciado,
            'penalizacion_horarios_prime': penalizacion_horarios_prime,
            'conflictos_profesor': conflictos_prof,
            'conflictos_aula': conflictos_aula,
            'cursos_validos_TPL': cursos_validos_TPL,
            'cursos_totales': cursos_totales,
            'porcentaje_TPL_correcto': (cursos_validos_TPL / cursos_totales * 100) if cursos_totales > 0 else 0
        }
    
    @classmethod
    def penalizacion_total(cls, solucion):
        """
        Calcula penalización total para usar en función de fitness
        
        Returns:
            float: Penalización total acumulada
        """
        metricas = cls.evaluar_calidad_horario(solucion)
        
        # Pesos de penalización
        PESO_TPL = 500          # Crítico: orden pedagógico
        PESO_CONFLICTO = 1000   # Crítico: conflictos
        PESO_DISTRIBUCION = 1   # Importante: distribución
        PESO_ESPACIADO = 1      # Importante: espaciado
        PESO_HORARIOS = 1       # Deseable: horarios prime
        
        penalizacion = (
            metricas['violaciones_TPL'] * PESO_TPL +
            metricas['conflictos_profesor'] * PESO_CONFLICTO +
            metricas['conflictos_aula'] * PESO_CONFLICTO +
            metricas['penalizacion_distribucion'] * PESO_DISTRIBUCION +
            metricas['penalizacion_espaciado'] * PESO_ESPACIADO +
            metricas['penalizacion_horarios_prime'] * PESO_HORARIOS
        )
        
        return penalizacion, metricas


# ==================== FUNCIONES DE UTILIDAD ====================

def generar_reporte_calidad(solucion):
    """Genera reporte legible de calidad del horario"""
    metricas = ReglasInstitucionales.evaluar_calidad_horario(solucion)
    
    print("\n" + "="*80)
    print("📋 REPORTE DE CALIDAD DEL HORARIO")
    print("="*80)
    
    print(f"\n🎓 Reglas Pedagógicas:")
    print(f"   • Orden T→P→L correcto: {metricas['cursos_validos_TPL']}/{metricas['cursos_totales']} cursos ({metricas['porcentaje_TPL_correcto']:.1f}%)")
    print(f"   • Violaciones T→P→L: {metricas['violaciones_TPL']}")
    
    print(f"\n📅 Distribución Temporal:")
    print(f"   • Penalización distribución: {metricas['penalizacion_distribucion']}")
    print(f"   • Penalización espaciado: {metricas['penalizacion_espaciado']}")
    
    print(f"\n⏰ Horarios Prime:")
    print(f"   • Penalización horarios: {metricas['penalizacion_horarios_prime']}")
    
    print(f"\n⚠️  Conflictos:")
    print(f"   • Conflictos profesor: {metricas['conflictos_profesor']}")
    print(f"   • Conflictos aula: {metricas['conflictos_aula']}")
    
    penalizacion_total, _ = ReglasInstitucionales.penalizacion_total(solucion)
    print(f"\n🏆 Penalización Total: {penalizacion_total:,.0f}")
    print("="*80)
    
    return metricas


if __name__ == "__main__":
    print("✅ Módulo de Reglas Pedagógicas cargado correctamente")
    print("\nReglas implementadas:")
    print("  1. T→P→L: Teorías antes que Prácticas/Laboratorios")
    print("  2. Distribución temporal: Evitar sobrecarga en un día")
    print("  3. Espaciado: Separación entre teoría y práctica")
    print("  4. Horarios prime: Teorías en Lun-Jue 8:00-12:00")
    print("  5. Conflictos: Sin conflictos profesor/aula")
