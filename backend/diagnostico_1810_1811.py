"""
Diagnóstico profundo de las secciones 1810 y 1811 que bloquean el ACO
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from app.database import SessionLocal
from app.models import CourseSection, Course, Classroom
from sqlalchemy import func

session = SessionLocal()

print("="*80)
print("DIAGNÓSTICO DE SECCIONES BLOQUEADORAS: 1810 y 1811")
print("="*80)

# Consulta específica de las 2 secciones
sections_ids = [1810, 1811]

for sec_id in sections_ids:
    section = session.query(CourseSection).filter(CourseSection.id == sec_id).first()
    
    if not section:
        print(f"\n❌ Sección {sec_id} NO ENCONTRADA")
        continue
    
    course = section.course
    
    print(f"\n{'='*80}")
    print(f"Sección ID: {sec_id}")
    print(f"Código completo: {section.codigo_completo}")
    print(f"{'='*80}")
    
    print(f"\n📚 DATOS CURSO:")
    print(f"  - Curso: {course.nombre} ({course.codigo})")
    print(f"  - Ciclo: {course.ciclo}")
    print(f"  - Modalidad curso: {course.modalidad}")
    print(f"  - Créditos: {course.creditos}")
    print(f"  - Requiere laboratorio: {course.requiere_laboratorio}")
    print(f"  - Requiere práctica: {course.requiere_practica}")
    
    print(f"\n🎓 DATOS SECCIÓN:")
    print(f"  - Tipo: {section.tipo}")
    print(f"  - Sección: {section.seccion}")
    print(f"  - Liga: {section.league}")
    print(f"  - NRC: {section.nrc}")
    print(f"  - Alumnos proyectados: {section.alumnos_proyectados}")
    print(f"  - Alumnos reales: {section.alumnos_reales}")
    print(f"  - Activa: {section.activa}")
    
    # Buscar otras secciones de la misma liga
    if section.league:
        league_sections = (
            session.query(CourseSection)
            .filter(CourseSection.league == section.league)
            .filter(CourseSection.id != sec_id)
            .all()
        )
        
        print(f"\n🔗 LIGA {section.league} ({len(league_sections)} otras secciones):")
        
        # Contar por tipo
        type_count = {}
        for ls in league_sections:
            tipo = ls.tipo
            type_count[tipo] = type_count.get(tipo, 0) + 1
        
        for tipo, count in sorted(type_count.items()):
            print(f"  - {tipo}: {count} secciones")
        
        # Buscar secciones del MISMO curso en la misma liga
        same_course_league = [
            ls for ls in league_sections 
            if ls.course_id == section.course_id
        ]
        
        if same_course_league:
            print(f"\n📌 Secciones del MISMO curso ({course.codigo}) en Liga {section.league}:")
            for ls in same_course_league:
                print(f"  - Sección {ls.id} ({ls.codigo_completo}): {ls.tipo}, Est: {ls.alumnos_proyectados}")
    
    # Buscar TODAS las secciones del mismo curso (todas las ligas)
    all_course_sections = (
        session.query(CourseSection)
        .filter(CourseSection.course_id == section.course_id)
        .filter(CourseSection.id != sec_id)
        .all()
    )
    
    if all_course_sections:
        print(f"\n📊 TODAS las secciones del curso {course.codigo}:")
        for cs in all_course_sections:
            league_label = f"Liga {cs.league}" if cs.league else "Sin liga"
            print(f"  - Sección {cs.id} ({cs.codigo_completo}): {cs.tipo}, Est: {cs.alumnos_proyectados}, {league_label}")
    
    # Buscar aulas compatibles
    print(f"\n🏫 AULAS COMPATIBLES:")
    
    # Para PRACTICA: buscar aulas tipo 'TEORIA' o 'PRACTICA' con capacidad >= alumnos
    # Para LABORATORIO: buscar aulas tipo 'LABORATORIO' o 'COMPUTO' con capacidad >= alumnos
    
    if section.tipo.upper() == 'LABORATORIO':
        compatible_classrooms = (
            session.query(Classroom)
            .filter(Classroom.active == True)
            .filter(Classroom.tipo.in_(['LABORATORIO', 'COMPUTO']))
            .filter(Classroom.capacidad >= section.alumnos_proyectados)
            .all()
        )
        search_types = "LABORATORIO o COMPUTO"
    elif section.tipo.upper() == 'PRACTICA':
        compatible_classrooms = (
            session.query(Classroom)
            .filter(Classroom.active == True)
            .filter(Classroom.tipo.in_(['TEORIA', 'PRACTICA']))
            .filter(Classroom.capacidad >= section.alumnos_proyectados)
            .all()
        )
        search_types = "TEORIA o PRACTICA"
    else:  # TEORIA
        compatible_classrooms = (
            session.query(Classroom)
            .filter(Classroom.active == True)
            .filter(Classroom.tipo == 'TEORIA')
            .filter(Classroom.capacidad >= section.alumnos_proyectados)
            .all()
        )
        search_types = "TEORIA"
    
    print(f"  - Buscando tipo: {search_types}")
    print(f"  - Capacidad mínima: {section.alumnos_proyectados}")
    print(f"  - Aulas encontradas: {len(compatible_classrooms)}")
    
    if compatible_classrooms:
        print(f"\n  Top 5 aulas compatibles:")
        for cr in compatible_classrooms[:5]:
            print(f"    - {cr.codigo}: Tipo={cr.tipo}, Cap={cr.capacidad}, Piso={cr.piso}")
    else:
        print(f"\n  ❌ NO HAY AULAS COMPATIBLES")
        print(f"     Esto explica por qué el ACO no puede asignar esta sección.")
        
        # Verificar si existen aulas del tipo correcto (sin filtro de capacidad)
        all_type_classrooms = (
            session.query(Classroom)
            .filter(Classroom.active == True)
            .filter(Classroom.tipo.in_(search_types.split(' o ')))
            .all()
        )
        
        if all_type_classrooms:
            max_capacity = max(cr.capacidad for cr in all_type_classrooms)
            print(f"     - Existen {len(all_type_classrooms)} aulas tipo {search_types}")
            print(f"     - Capacidad máxima disponible: {max_capacity}")
            print(f"     - Necesario: {section.alumnos_proyectados}")
            print(f"     - Exceso: {section.alumnos_proyectados - max_capacity} estudiantes")
            print(f"\n  ✅ SOLUCIÓN: Dividir esta sección en grupos más pequeños")
        else:
            print(f"     - NO EXISTEN aulas tipo {search_types}")
            print(f"\n  ✅ SOLUCIÓN: Crear aulas tipo {search_types} o cambiar tipo de sección")

session.close()
print("\n" + "="*80)
print("FIN DEL DIAGNÓSTICO")
print("="*80)
