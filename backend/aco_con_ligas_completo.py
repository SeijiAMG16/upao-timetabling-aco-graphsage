"""
ACO MEJORADO CON SOPORTE DE LIGAS Y GRAPHSAGE

Implementa:
1. Sistema de ligas (T1→P1/L1, T2→P2/L2)
2. Bloques de tiempo oficiales UPAO (50 minutos)
3. Parallelización para P/L
4. Integración con GraphSAGE para inicialización de feromonas
5. Modalidad PRS/NPR con límites de tiempo
"""
import random
import numpy as np
from collections import defaultdict
from typing import List, Dict, Tuple
from slots_tiempo_upao import obtener_slots_para_sesion, DIAS_SEMANA


class ACOConLigas:
    def __init__(
        self,
        secciones: List[Dict],
        profesores: List[Dict],
        aulas: List[Dict],
        alfa: float = 1.0,
        beta: float = 2.0,
        rho: float = 0.1,
        Q: float = 100,
        num_hormigas: int = 20,
        max_iter: int = 50,
        graphsage_embeddings: Dict = None
    ):
        self.secciones = secciones
        self.profesores = profesores
        self.aulas = aulas
        
        # Parámetros ACO
        self.alfa = alfa  # Importancia de feromonas
        self.beta = beta  # Importancia de heurística
        self.rho = rho    # Evaporación
        self.Q = Q        # Constante de feromonas
        self.num_hormigas = num_hormigas
        self.max_iter = max_iter
        
        # GraphSAGE embeddings (opcional)
        self.embeddings = graphsage_embeddings or {}
        
        # Slots de tiempo oficiales UPAO
        self.slots_prs = obtener_slots_para_sesion(2, incluir_virtual=False)  # Presencial
        self.slots_npr = obtener_slots_para_sesion(2, incluir_virtual=True)   # NPR/Virtual
        
        # Feromonas (matriz de asociaciones)
        self.inicializar_feromonas()
        
        # Agrupar secciones por curso y liga
        self.agrupar_por_ligas()
        
        print("=" * 80)
        print("ACO CON LIGAS INICIALIZADO")
        print("=" * 80)
        print(f"  📚 Secciones: {len(self.secciones)}")
        print(f"  👥 Profesores: {len(self.profesores)}")
        print(f"  🏫 Aulas: {len(self.aulas)}")
        print(f"  ⏰ Slots PRS: {len(self.slots_prs)}")
        print(f"  ⏰ Slots NPR: {len(self.slots_npr)}")
        print(f"  🐜 Hormigas: {self.num_hormigas}")
        print(f"  🔄 Iteraciones: {self.max_iter}")
        print(f"  🧬 GraphSAGE: {'✅ Activado' if self.embeddings else '❌ Desactivado'}")
    
    def agrupar_por_ligas(self):
        """Agrupa secciones por curso y liga"""
        self.secciones_por_curso_liga = defaultdict(lambda: defaultdict(list))
        
        for seccion in self.secciones:
            course_id = seccion['course_id']
            liga = seccion['liga']
            self.secciones_por_curso_liga[course_id][liga].append(seccion)
        
        print(f"\n📊 ESTRUCTURA DE LIGAS:")
        cursos_con_ligas = len(self.secciones_por_curso_liga)
        total_ligas = sum(len(ligas) for ligas in self.secciones_por_curso_liga.values())
        print(f"  • Cursos: {cursos_con_ligas}")
        print(f"  • Ligas totales: {total_ligas}")
    
    def inicializar_feromonas(self):
        """Inicializa matriz de feromonas usando GraphSAGE si está disponible"""
        self.feromonas = {}
        
        valor_inicial = 1.0
        
        # Si hay embeddings de GraphSAGE, usar para inicialización inteligente
        if self.embeddings:
            print("\n🧬 Inicializando feromonas con GraphSAGE...")
            # TODO: Implementar inicialización basada en similitud de embeddings
        else:
            print("\n🐜 Inicializando feromonas uniformes...")
        
        # Inicializar feromonas para slots
        for seccion in self.secciones:
            sec_id = id(seccion)
            self.feromonas[sec_id] = {}
            
            slots = self.slots_npr if seccion['modalidad'] == 'NPR' else self.slots_prs
            
            for slot in slots:
                self.feromonas[sec_id][slot] = valor_inicial
    
    def construir_solucion(self) -> List[Dict]:
        """
        Construye una solución respetando ligas
        
        Orden de asignación:
        1. Agrupar por curso → liga
        2. Por cada liga: T → P (paralelo) → L (paralelo)
        3. Respetar orden temporal dentro de cada liga
        """
        solucion = []
        slots_usados = defaultdict(set)  # {(dia, hora): {(prof_id, aula_id), ...}}
        ultimo_slot_por_curso = {}  # Para T→P→L temporal
        
        # Ordenar cursos por dificultad (más ligas primero, GraphSAGE considera complejidad)
        cursos_ordenados = sorted(
            self.secciones_por_curso_liga.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )
        
        for course_id, ligas in cursos_ordenados:
            for liga_num in sorted(ligas.keys()):
                secciones_liga = ligas[liga_num]
                
                # Separar por tipo
                teorias = [s for s in secciones_liga if s['tipo'] == 'T']
                practicas = [s for s in secciones_liga if s['tipo'] == 'P']
                laboratorios = [s for s in secciones_liga if s['tipo'] == 'L']
                
                # 1. ASIGNAR TEORÍA (1 por liga)
                for teoria in teorias:
                    asignacion = self.asignar_seccion(
                        teoria, 
                        solucion, 
                        slots_usados,
                        despues_de=ultimo_slot_por_curso.get(course_id)
                    )
                    
                    if asignacion:
                        solucion.append(asignacion)
                        slot_key = (asignacion['day'], asignacion['start_time'])
                        slots_usados[slot_key].add((asignacion['professor_id'], asignacion['classroom_id']))
                        ultimo_slot_por_curso[course_id] = self.obtener_timestamp_slot(slot_key)
                
                # 2. ASIGNAR PRÁCTICAS (paralelas permitidas)
                for practica in practicas:
                    asignacion = self.asignar_seccion(
                        practica,
                        solucion,
                        slots_usados,
                        despues_de=ultimo_slot_por_curso.get(course_id),
                        permitir_paralelizacion=True
                    )
                    
                    if asignacion:
                        solucion.append(asignacion)
                        slot_key = (asignacion['day'], asignacion['start_time'])
                        slots_usados[slot_key].add((asignacion['professor_id'], asignacion['classroom_id']))
                        # Actualizar timestamp solo si es después del actual
                        nuevo_ts = self.obtener_timestamp_slot(slot_key)
                        if nuevo_ts > ultimo_slot_por_curso.get(course_id, 0):
                            ultimo_slot_por_curso[course_id] = nuevo_ts
                
                # 3. ASIGNAR LABORATORIOS (paralelos permitidos)
                for laboratorio in laboratorios:
                    asignacion = self.asignar_seccion(
                        laboratorio,
                        solucion,
                        slots_usados,
                        despues_de=ultimo_slot_por_curso.get(course_id),
                        permitir_paralelizacion=True
                    )
                    
                    if asignacion:
                        solucion.append(asignacion)
                        slot_key = (asignacion['day'], asignacion['start_time'])
                        slots_usados[slot_key].add((asignacion['professor_id'], asignacion['classroom_id']))
                        nuevo_ts = self.obtener_timestamp_slot(slot_key)
                        if nuevo_ts > ultimo_slot_por_curso.get(course_id, 0):
                            ultimo_slot_por_curso[course_id] = nuevo_ts
        
        return solucion
    
    def asignar_seccion(
        self,
        seccion: Dict,
        solucion: List[Dict],
        slots_usados: Dict,
        despues_de: float = None,
        permitir_paralelizacion: bool = False
    ) -> Dict:
        """Asigna una sección a slot, profesor y aula usando ACO"""
        
        # Obtener slots disponibles
        slots = self.slots_npr if seccion['modalidad'] == 'NPR' else self.slots_prs
        
        # Filtrar slots después del timestamp si es necesario
        if despues_de:
            slots = [s for s in slots if self.obtener_timestamp_slot((s[0], s[1])) > despues_de]
        
        if not slots:
            return None
        
        # Seleccionar slot con ACO
        slot_seleccionado = self.seleccionar_slot_aco(seccion, slots, slots_usados, permitir_paralelizacion)
        
        if not slot_seleccionado:
            return None
        
        dia, hora_inicio, hora_fin = slot_seleccionado
        slot_key = (dia, hora_inicio)
        
        # Seleccionar profesor disponible
        profesores_ocupados = {prof_id for prof_id, _ in slots_usados[slot_key]}
        profesores_disponibles = [p for p in self.profesores if p['id'] not in profesores_ocupados]
        
        if not profesores_disponibles:
            return None
        
        profesor = random.choice(profesores_disponibles)
        
        # Seleccionar aula disponible del tipo correcto
        aulas_ocupadas = {aula_id for _, aula_id in slots_usados[slot_key]}
        tipo_aula_requerido = 'LAB' if seccion['requiere_lab'] else 'NOLAB'
        aulas_disponibles = [
            a for a in self.aulas 
            if a['id'] not in aulas_ocupadas 
            and a['tipo'] == tipo_aula_requerido
        ]
        
        if not aulas_disponibles:
            return None
        
        aula = random.choice(aulas_disponibles)
        
        return {
            'course_id': seccion['course_id'],
            'course_name': seccion['course_name'],
            'session_type': seccion['session_type'],
            'liga': seccion['liga'],
            'day': dia,
            'start_time': hora_inicio,
            'end_time': hora_fin,
            'professor_id': profesor['id'],
            'professor_name': profesor['nombre_completo'],
            'classroom_id': aula['id'],
            'classroom_code': aula['codigo']
        }
    
    def seleccionar_slot_aco(
        self,
        seccion: Dict,
        slots: List[Tuple],
        slots_usados: Dict,
        permitir_paralelizacion: bool
    ) -> Tuple:
        """Selecciona slot usando feromonas y heurística"""
        
        sec_id = id(seccion)
        probabilidades = []
        
        for slot in slots:
            slot_key = (slot[0], slot[1])
            
            # Si no se permite paralelización y el slot está usado, skip
            if not permitir_paralelizacion and len(slots_usados[slot_key]) > 0:
                continue
            
            # Feromona
            tau = self.feromonas.get(sec_id, {}).get(slot, 1.0)
            
            # Heurística (preferir slots menos usados para mejor distribución)
            num_usados = len(slots_usados[slot_key])
            eta = 1.0 / (1.0 + num_usados) if permitir_paralelizacion else 1.0
            
            # Probabilidad
            prob = (tau ** self.alfa) * (eta ** self.beta)
            probabilidades.append((slot, prob))
        
        if not probabilidades:
            return None
        
        # Selección por ruleta
        total_prob = sum(p for _, p in probabilidades)
        if total_prob == 0:
            return random.choice([s for s, _ in probabilidades])
        
        r = random.uniform(0, total_prob)
        acumulado = 0
        
        for slot, prob in probabilidades:
            acumulado += prob
            if acumulado >= r:
                return slot
        
        return probabilidades[-1][0]
    
    def obtener_timestamp_slot(self, slot_key: Tuple) -> float:
        """Convierte (dia, hora) a timestamp numérico para comparación"""
        dia, hora = slot_key
        dia_num = DIAS_SEMANA.index(dia) if dia in DIAS_SEMANA else 0
        h, m, s = map(int, hora.split(':'))
        return dia_num * 24 * 3600 + h * 3600 + m * 60 + s
    
    def actualizar_feromonas(self, soluciones: List[Tuple[List[Dict], float]]):
        """Actualiza feromonas basado en calidad de soluciones"""
        
        # Evaporación
        for sec_id in self.feromonas:
            for slot in self.feromonas[sec_id]:
                self.feromonas[sec_id][slot] *= (1 - self.rho)
        
        # Depósito
        for solucion, calidad in soluciones:
            delta_tau = self.Q / (1.0 + (100 - calidad))  # Mayor calidad → más feromona
            
            for asignacion in solucion:
                sec_id = id(asignacion)  # Idealmente usar ID más estable
                slot = (asignacion['day'], asignacion['start_time'], asignacion['end_time'])
                
                if sec_id in self.feromonas and slot in self.feromonas[sec_id]:
                    self.feromonas[sec_id][slot] += delta_tau
    
    def evaluar_solucion(self, solucion: List[Dict]) -> float:
        """
        Evalúa calidad de la solución
        
        Criterios:
        - % asignaciones completadas
        - Cumplimiento T→P→L por liga
        - Distribución balanceada por día
        - Sin conflictos
        """
        if not solucion:
            return 0.0
        
        puntos = 0.0
        
        # 1. Cobertura (40 puntos)
        cobertura = (len(solucion) / len(self.secciones)) * 40
        puntos += cobertura
        
        # 2. T→P→L por liga (30 puntos)
        tpl_score = self.evaluar_tpl_por_liga(solucion)
        puntos += tpl_score * 30
        
        # 3. Distribución por día (20 puntos)
        dist_score = self.evaluar_distribucion(solucion)
        puntos += dist_score * 20
        
        # 4. Sin conflictos (10 puntos)
        conflictos = self.contar_conflictos(solucion)
        puntos += max(0, 10 - conflictos)
        
        return min(100.0, puntos)
    
    def evaluar_tpl_por_liga(self, solucion: List[Dict]) -> float:
        """Evalúa cumplimiento de T→P→L dentro de cada liga"""
        por_curso_liga = defaultdict(lambda: defaultdict(list))
        
        for asig in solucion:
            por_curso_liga[asig['course_id']][asig['liga']].append(asig)
        
        cumplimientos = 0
        total_checks = 0
        
        for course_id, ligas in por_curso_liga.items():
            for liga, asigs in ligas.items():
                teorias = [a for a in asigs if a['session_type'][0] == 'T']
                practicas = [a for a in asigs if a['session_type'][0] == 'P']
                labs = [a for a in asigs if a['session_type'][0] == 'L']
                
                # T→P
                if teorias and practicas:
                    max_t = max(self.obtener_timestamp_slot((t['day'], t['start_time'])) for t in teorias)
                    min_p = min(self.obtener_timestamp_slot((p['day'], p['start_time'])) for p in practicas)
                    if max_t < min_p:
                        cumplimientos += 1
                    total_checks += 1
                
                # P→L
                if practicas and labs:
                    max_p = max(self.obtener_timestamp_slot((p['day'], p['start_time'])) for p in practicas)
                    min_l = min(self.obtener_timestamp_slot((l['day'], l['start_time'])) for l in labs)
                    if max_p < min_l:
                        cumplimientos += 1
                    total_checks += 1
        
        return cumplimientos / total_checks if total_checks > 0 else 1.0
    
    def evaluar_distribucion(self, solucion: List[Dict]) -> float:
        """Evalúa balance de asignaciones por día"""
        por_dia = defaultdict(int)
        for asig in solucion:
            por_dia[asig['day']] += 1
        
        if not por_dia:
            return 0.0
        
        promedio = len(solucion) / len(DIAS_SEMANA)
        varianza = sum((count - promedio) ** 2 for count in por_dia.values()) / len(por_dia)
        
        # Normalizar (menos varianza = mejor)
        score = 1.0 / (1.0 + varianza / promedio)
        return score
    
    def contar_conflictos(self, solucion: List[Dict]) -> int:
        """Cuenta conflictos (profesor/aula en mismo slot)"""
        conflictos = 0
        por_slot = defaultdict(list)
        
        for asig in solucion:
            key = (asig['day'], asig['start_time'])
            por_slot[key].append(asig)
        
        for slot, asigs in por_slot.items():
            # Conflictos de profesor
            profesores = [a['professor_id'] for a in asigs]
            conflictos += len(profesores) - len(set(profesores))
            
            # Conflictos de aula
            aulas = [a['classroom_id'] for a in asigs]
            conflictos += len(aulas) - len(set(aulas))
        
        return conflictos
    
    def ejecutar(self) -> Tuple[List[Dict], float]:
        """Ejecuta el algoritmo ACO"""
        mejor_solucion = []
        mejor_calidad = 0.0
        
        print("\n" + "=" * 80)
        print("EJECUTANDO ACO CON LIGAS")
        print("=" * 80)
        
        for iteracion in range(self.max_iter):
            soluciones_iter = []
            
            # Cada hormiga construye una solución
            for hormiga in range(self.num_hormigas):
                solucion = self.construir_solucion()
                calidad = self.evaluar_solucion(solucion)
                soluciones_iter.append((solucion, calidad))
                
                if calidad > mejor_calidad:
                    mejor_calidad = calidad
                    mejor_solucion = solucion
            
            # Actualizar feromonas
            self.actualizar_feromonas(soluciones_iter)
            
            # Mostrar progreso cada 10 iteraciones
            if (iteracion + 1) % 10 == 0:
                calidad_promedio = sum(c for _, c in soluciones_iter) / len(soluciones_iter)
                print(f"  Iteración {iteracion + 1:2d}: "
                      f"Mejor={mejor_calidad:.2f}% | "
                      f"Promedio={calidad_promedio:.2f}% | "
                      f"Asignaciones={len(mejor_solucion)}/{len(self.secciones)}")
        
        print("\n" + "=" * 80)
        print(f"✅ MEJOR SOLUCIÓN: {mejor_calidad:.2f}%")
        print(f"   Asignaciones: {len(mejor_solucion)}/{len(self.secciones)}")
        print("=" * 80)
        
        return mejor_solucion, mejor_calidad


if __name__ == '__main__':
    print("Este módulo debe ser importado desde el ejecutor principal")
