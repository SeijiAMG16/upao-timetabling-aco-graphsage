"""
Diagnóstico PROFUNDO de por qué la sección 1814 NO se puede asignar
Analiza TODAS las restricciones posibles
"""
import sys
sys.path.insert(0, 'c:\\Users\\amaya\\Downloads\\10mo Ciclo\\TESIS\\upao-timetabling-aco-graphsage\\backend')

from app.database import SessionLocal
from app.models import CourseSection, Classroom, Course, TimeSlot, Professor, ProfessorCourseAssignment
from app.aco_graphsage.graph_builder import TimetableGraphBuilder
from sqlalchemy.orm import joinedload

def analizar_seccion_1814():
    print("="*80)
    print("DIAGNÓSTICO PROFUNDO - SECCIÓN 1814")
    print("="*80)
    
    db = SessionLocal()
    
    # 1. INFORMACIÓN BÁSICA DE LA SECCIÓN
    section = db.query(CourseSection).options(
        joinedload(CourseSection.course)
    ).filter_by(id=1814).first()
    
    if not section:
        print("❌ Sección 1814 NO EXISTE")
        return
    
    print(f"\n📋 SECCIÓN 1814:")
    print(f"  Código: {section.codigo_completo}")
    print(f"  Tipo: {section.tipo}")
    print(f"  Estudiantes proyectados: {section.alumnos_proyectados}")
    print(f"  League: {section.league}")
    print(f"  NRC: {section.nrc}")
    print(f"  Modalidad: {section.course.modalidad if section.course else 'N/A'}")
    
    # 2. BUSCAR OTRAS SECCIONES DE LA MISMA LEAGUE
    print(f"\n🔗 OTRAS SECCIONES EN LEAGUE {section.league}:")
    league_sections = db.query(CourseSection).filter(
        CourseSection.league == section.league,
        CourseSection.activa == True,
        CourseSection.alumnos_proyectados > 0
    ).order_by(CourseSection.id).all()
    
    print(f"  Total: {len(league_sections)} secciones")
    for sec in league_sections:
        print(f"    - {sec.id}: {sec.codigo_completo} ({sec.tipo}, {sec.alumnos_proyectados} est)")
    
    # 3. AULAS COMPATIBLES
    print(f"\n🏫 AULAS COMPATIBLES PARA SECCIÓN 1814:")
    
    classrooms = db.query(Classroom).filter(Classroom.activa == True).all()
    
    def normalize_type(tipo):
        if tipo == 'LAB':
            return 'laboratorio'
        elif tipo == 'NOLAB':
            return 'teorica'
        return tipo.lower()
    
    compatible = []
    for classroom in classrooms:
        tipo_norm = normalize_type(classroom.tipo)
        section_tipo = section.tipo.lower() if section.tipo else ''
        
        # Compatibilidad de tipo
        type_compatible = (
            (section_tipo == 'teorica' and tipo_norm in ['teorica', 'practica']) or
            (section_tipo == 'practica' and tipo_norm in ['teorica', 'practica']) or
            (section_tipo == 'laboratorio' and tipo_norm == 'laboratorio')
        )
        
        # Capacidad
        capacity_ok = classroom.capacidad >= section.alumnos_proyectados
        
        if type_compatible and capacity_ok:
            compatible.append(classroom)
    
    print(f"  Total compatibles: {len(compatible)} aulas")
    if compatible:
        print(f"  Ejemplos:")
        for c in compatible[:5]:
            print(f"    - {c.codigo}: Tipo={c.tipo}, Cap={c.capacidad}")
    
    # 4. SLOTS DE TIEMPO DISPONIBLES
    print(f"\n⏰ SLOTS DE TIEMPO:")
    timeslots = db.query(TimeSlot).order_by(TimeSlot.dia, TimeSlot.hora_inicio).all()
    print(f"  Total slots disponibles: {len(timeslots)}")
    print(f"  Días: {set(ts.dia for ts in timeslots)}")
    print(f"  Rangos horarios: {timeslots[0].hora_inicio} - {timeslots[-1].hora_fin}")
    
    # 5. SIMULAR ASIGNACIONES PREVIAS (1810-1813)
    print(f"\n🧪 SIMULANDO ASIGNACIONES PREVIAS (Hormiga exitosa):")
    print(f"  Asumiendo que 1810, 1811, 1812, 1813 ya fueron asignadas")
    
    # Contar cuántos slots quedan si asignamos las 4 secciones anteriores
    # Asumiendo 2 horas por sección
    slots_por_seccion = 2
    secciones_previas = [s for s in league_sections if s.id < 1814]
    
    print(f"\n  Secciones previas en la league: {len(secciones_previas)}")
    slots_usados_estimados = len(secciones_previas) * slots_por_seccion
    slots_disponibles_estimados = len(timeslots) - slots_usados_estimados
    
    print(f"  Slots totales: {len(timeslots)}")
    print(f"  Slots usados (estimado): {slots_usados_estimados}")
    print(f"  Slots disponibles (estimado): {slots_disponibles_estimados}")
    
    # 6. VERIFICAR PROFESOR ASIGNADO
    print(f"\n👨‍🏫 PROFESOR ASIGNADO:")
    prof_course = db.query(ProfessorCourseAssignment).filter_by(
        course_section_id=section.id
    ).first()
    
    if prof_course:
        professor = db.query(Professor).filter_by(id=prof_course.professor_id).first()
        print(f"  Profesor ID: {professor.id}")
        print(f"  Nombre: {professor.nombre_completo}")
        
        # Contar otras secciones del mismo profesor
        other_sections = db.query(ProfessorCourseAssignment).filter_by(
            professor_id=professor.id
        ).count()
        print(f"  Total secciones del profesor: {other_sections}")
    else:
        print(f"  ⚠️ NO hay profesor asignado")
    
    # 7. ANÁLISIS DE RESTRICCIONES
    print(f"\n🔍 ANÁLISIS DE RESTRICCIONES CRÍTICAS:")
    
    # 7.1 Restricción de League Coherence
    print(f"\n  a) League Coherence (NO solapamiento entre secciones de la misma league):")
    print(f"     - Secciones en League {section.league}: {len(league_sections)}")
    print(f"     - Con 5 secciones, necesitan 5 slots DIFERENTES sin solapar")
    print(f"     - Si cada sección usa 2 horas, necesitan al menos 10 horas diferentes")
    print(f"     - Slots de 2h disponibles: {len(timeslots)} (96 total / 2 = 48 bloques)")
    
    # 7.2 Restricción de profesor
    if prof_course:
        print(f"\n  b) Disponibilidad del Profesor {professor.id}:")
        print(f"     - Debe estar disponible en slot no usado por sus otras {other_sections-1} secciones")
    
    # 7.3 Modalidad virtual
    if section.course and section.course.modalidad == 'NO_PRESENCIAL':
        print(f"\n  c) Modalidad NO_PRESENCIAL:")
        print(f"     - Sección es VIRTUAL")
        print(f"     - ¿Las restricciones de league deberían ser más flexibles?")
    
    # 8. HIPÓTESIS DEL PROBLEMA
    print(f"\n" + "="*80)
    print(f"💡 HIPÓTESIS DEL PROBLEMA:")
    print(f"="*80)
    print(f"""
  ESCENARIO PROBABLE:
  
  1. Las hormigas asignan exitosamente 1810, 1811, 1812, 1813
  2. Al llegar a 1814, el validador de restricciones (`_validate_league_coherence`)
     verifica que NO haya solapamiento con las otras 4 secciones de la League 1
  3. Como las 4 secciones previas ya consumieron varios slots de tiempo,
     NO quedan suficientes slots libres que cumplan TODAS las restricciones:
     - Sin solapamiento con 1810-1813 (league coherence)
     - Profesor disponible
     - Aula compatible disponible en ese slot
  
  PROBLEMA CLAVE:
  - La restricción de league coherence es DEMASIADO ESTRICTA
  - Con 5 secciones en la misma league, es MUY difícil encontrar 5 slots
    que no se solapen entre sí Y que cumplan las demás restricciones
  
  SOLUCIÓN PROPUESTA:
  - Para cursos NO_PRESENCIAL (virtuales), RELAJAR la restricción de no solapamiento
  - Permitir que secciones virtuales de la misma league se solapen parcialmente
  - Esto aumentará dramáticamente las opciones disponibles
    """)
    
    # 9. VERIFICAR SI EL FIX YA ESTÁ APLICADO
    print(f"\n🔧 VERIFICANDO SI EL FIX YA ESTÁ APLICADO:")
    
    import inspect
    from app.aco_graphsage import constraints as constraints_module
    
    source_file = constraints_module.__file__
    print(f"  Archivo: {source_file}")
    
    with open(source_file, 'r', encoding='utf-8') as f:
        source = f.read()
    
    if 'NO_PRESENCIAL' in source and 'modalidad' in source:
        print(f"  ✅ El código menciona NO_PRESENCIAL y modalidad")
        
        # Buscar el método _validate_league_coherence
        if '_validate_league_coherence' in source:
            print(f"  ✅ Método _validate_league_coherence encontrado")
            
            # Verificar si tiene el bypass para NO_PRESENCIAL
            lines = source.split('\n')
            in_method = False
            has_bypass = False
            
            for i, line in enumerate(lines):
                if '_validate_league_coherence' in line:
                    in_method = True
                if in_method and 'NO_PRESENCIAL' in line:
                    has_bypass = True
                    print(f"  ✅ Línea {i+1}: {line.strip()}")
            
            if has_bypass:
                print(f"  ✅ El fix para NO_PRESENCIAL ESTÁ implementado")
            else:
                print(f"  ❌ NO se encontró el bypass para NO_PRESENCIAL")
        else:
            print(f"  ❌ Método _validate_league_coherence NO encontrado")
    else:
        print(f"  ❌ El fix NO está aplicado")
    
    db.close()

if __name__ == '__main__':
    analizar_seccion_1814()
