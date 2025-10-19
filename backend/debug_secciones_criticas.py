"""
Debug profundo de las secciones que SIEMPRE fallan
"""
import sys
sys.path.insert(0, 'app')

from models import CourseSection, Classroom, TimeSlot, Professor
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

engine = create_engine('mysql+pymysql://root:sistemas@localhost:3306/upao_timetabling')
Session = sessionmaker(bind=engine)
session = Session()

# Las secciones que SIEMPRE fallan
secciones_criticas = [1550, 1551, 1552, 1553, 1554, 1605, 1608, 1631, 1632]

print("=" * 100)
print("ANÁLISIS PROFUNDO DE SECCIONES QUE SIEMPRE FALLAN")
print("=" * 100)

for sec_id in secciones_criticas:
    sec = session.query(CourseSection).filter_by(id=sec_id).first()
    if not sec:
        print(f"\n❌ SECCIÓN {sec_id} NO EXISTE EN LA BASE DE DATOS")
        continue
    
    print(f"\n{'='*100}")
    print(f"SECCIÓN {sec.id}: {sec.course.codigo} - {sec.course.nombre}")
    print(f"{'='*100}")
    print(f"  Tipo: {sec.tipo} | Sección: {sec.seccion} | Liga: {sec.league}")
    print(f"  Estudiantes: {sec.alumnos_proyectados}")
    print(f"  NRC: {sec.nrc}")
    print(f"  Activa: {sec.activa}")
    
    # Horas del curso
    curso = sec.course
    print(f"\n  Información del curso:")
    print(f"    Créditos: {curso.creditos}")
    print(f"    Requiere lab: {curso.requiere_laboratorio} | Requiere práctica: {curso.requiere_practica}")
    print(f"    Grupos - T:{curso.grupos_teoria} P:{curso.grupos_practica} L:{curso.grupos_laboratorio}")
    
    # Verificar tipo de aula requerido
    requiere_lab = sec.tipo.lower() == 'laboratorio'
    tipo_aula_requerido = 'LAB' if requiere_lab else 'TEORICA'
    
    print(f"\n  Tipo de aula requerido: {tipo_aula_requerido}")
    
    # Buscar aulas compatibles
    aulas_compatibles = session.query(Classroom).filter(
        Classroom.active == 1,
        Classroom.capacidad >= sec.alumnos_proyectados
    ).filter(
        Classroom.tipo == 'laboratorio' if requiere_lab else Classroom.tipo.in_(['teorica', 'laboratorio'])
    ).all()
    
    print(f"\n  Aulas compatibles (cap >= {sec.alumnos_proyectados}, tipo {tipo_aula_requerido}):")
    if aulas_compatibles:
        print(f"    Total: {len(aulas_compatibles)} aulas")
        for aula in aulas_compatibles[:5]:
            print(f"      - {aula.codigo}: cap {aula.capacidad}, tipo {aula.tipo}, edificio {aula.edificio}")
        if len(aulas_compatibles) > 5:
            print(f"      ... y {len(aulas_compatibles) - 5} más")
    else:
        print(f"    ❌ NO HAY AULAS COMPATIBLES")
        
        # Buscar la aula más grande disponible
        aula_mas_grande = session.query(Classroom).filter(
            Classroom.active == 1
        ).filter(
            Classroom.tipo == 'laboratorio' if requiere_lab else Classroom.tipo.in_(['teorica', 'laboratorio'])
        ).order_by(Classroom.capacidad.desc()).first()
        
        if aula_mas_grande:
            print(f"    Aula más grande del tipo: {aula_mas_grande.codigo} (cap {aula_mas_grande.capacidad})")
            print(f"    ⚠️  FALTAN {sec.alumnos_proyectados - aula_mas_grande.capacidad} LUGARES")
    
    # Verificar franjas horarias disponibles
    total_franjas = session.query(func.count(TimeSlot.id)).filter(
        TimeSlot.activo == 1
    ).scalar()
    
    print(f"\n  Franjas horarias disponibles: {total_franjas}")
    
    # Para este análisis, asumimos 2-4 horas según el tipo
    if sec.tipo.lower() == 'teoria':
        horas_necesarias = 4
    elif sec.tipo.lower() == 'practica':
        horas_necesarias = 4
    elif sec.tipo.lower() == 'laboratorio':
        horas_necesarias = 4
    else:
        horas_necesarias = 2
    
    print(f"  Horas estimadas necesarias para tipo {sec.tipo}: {horas_necesarias}h")
    
    # Verificar si tiene profesor asignado
    # Buscar en professor_course_assignments
    from models import ProfessorCourseAssignment
    asignacion = session.query(ProfessorCourseAssignment).filter_by(
        course_id=sec.course_id,
        tipo_sesion=sec.tipo,
        liga=sec.league
    ).first()
    
    if asignacion:
        profesor = session.query(Professor).filter_by(id=asignacion.professor_id).first()
        print(f"\n  Profesor asignado: {profesor.name} (ID: {profesor.id})")
        
        # Contar otras secciones del mismo profesor
        otras_secciones = session.query(ProfessorCourseAssignment).filter_by(
            professor_id=profesor.id
        ).count()
        print(f"    Total de asignaciones del profesor: {otras_secciones}")
    else:
        print(f"\n  ❌ NO TIENE PROFESOR ASIGNADO EN professor_course_assignments")
        print(f"     Buscando profesores que pueden enseñar {curso.codigo}...")
        
        # Buscar profesores que pueden enseñar este curso
        posibles_profesores = session.query(ProfessorCourseAssignment).filter_by(
            course_id=sec.course_id
        ).all()
        
        if posibles_profesores:
            print(f"     Profesores que enseñan este curso:")
            for asig in posibles_profesores[:3]:
                prof = session.query(Professor).filter_by(id=asig.professor_id).first()
                print(f"       - {prof.name}: {asig.tipo_sesion}, Liga {asig.liga}")
        else:
            print(f"     ❌ NO HAY PROFESORES ASIGNADOS PARA ESTE CURSO")

print("\n" + "=" * 100)
print("RESUMEN DE PROBLEMAS ENCONTRADOS")
print("=" * 100)

problemas = {
    'sin_aulas': [],
    'sin_profesor': [],
    'aula_pequena': []
}

for sec_id in secciones_criticas:
    sec = session.query(CourseSection).filter_by(id=sec_id).first()
    if not sec:
        continue
    
    # Verificar aulas
    requiere_lab = sec.tipo.lower() == 'laboratorio'
    tipo_aula = 'LAB' if requiere_lab else 'TEORICA'
    
    aulas = session.query(Classroom).filter(
        Classroom.active == 1,
        Classroom.capacidad >= sec.alumnos_proyectados
    ).filter(
        Classroom.tipo == 'laboratorio' if requiere_lab else Classroom.tipo.in_(['teorica', 'laboratorio'])
    ).count()
    
    if aulas == 0:
        problemas['sin_aulas'].append(sec_id)
    
    # Verificar profesor
    from models import ProfessorCourseAssignment
    asignacion = session.query(ProfessorCourseAssignment).filter_by(
        course_id=sec.course_id,
        tipo_sesion=sec.tipo,
        liga=sec.league
    ).first()
    
    if not asignacion:
        problemas['sin_profesor'].append(sec_id)

print(f"\nSecciones SIN AULAS compatibles: {problemas['sin_aulas']}")
print(f"Secciones SIN PROFESOR asignado: {problemas['sin_profesor']}")

session.close()
