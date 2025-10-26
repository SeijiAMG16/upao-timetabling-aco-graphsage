"""
Investigar por qué las secciones de ISIA119 (Teorías T1 y T2) no fueron asignadas
"""
from app.database import SessionLocal
from app.models import CourseSection, Course, Professor, ProfessorCourseAssignment
from sqlalchemy.orm import joinedload
from sqlalchemy import text

db = SessionLocal()

# IDs de las secciones problemáticas
section_ids = [1794, 1795]  # ISIA119 Teorías T1 y T2

print("="*80)
print("INVESTIGACIÓN: ISIA119 - MODELOS GENERATIVOS DE IA")
print("="*80)

for section_id in section_ids:
    section = db.query(CourseSection).options(
        joinedload(CourseSection.course)
    ).filter(CourseSection.id == section_id).first()
    
    if not section:
        print(f"\n❌ Sección {section_id} no encontrada")
        continue
    
    print(f"\n📚 SECCIÓN ID: {section_id}")
    print(f"   Curso: {section.course.codigo} - {section.course.nombre}")
    print(f"   Tipo: {section.tipo}")
    print(f"   Sección: {section.seccion}")
    print(f"   Liga: {section.league}")
    print(f"   Alumnos proyectados: {section.alumnos_proyectados}")
    print(f"   NRC: {section.nrc}")
    print(f"   Activa: {section.activa}")
    
    # Buscar profesores asignados en professor_course_assignments
    course_id = section.course.id
    course_code = section.course.codigo
    
    # Query directo sin ORM para evitar problema con columnas
    prof_assignments_query = db.execute(
        text("""
        SELECT pca.id, pca.professor_id, p.codigo, p.nombre_completo, 
               pca.session_type, pca.league
        FROM professor_course_assignments pca
        JOIN professors p ON p.id = pca.professor_id
        WHERE pca.course_id = :course_id
        """),
        {'course_id': course_id}
    ).fetchall()
    
    print(f"\n   👨‍🏫 PROFESORES ASIGNADOS AL CURSO {course_code}:")
    if prof_assignments_query:
        for pa in prof_assignments_query:
            print(f"      • Prof ID: {pa[1]} ({pa[2]}) - {pa[3]}")
            print(f"        Tipo: {pa[4]} | Liga: {pa[5]}")
    else:
        print(f"      ⚠️ NO HAY PROFESORES ASIGNADOS EN professor_course_assignments")
    
    # Verificar si el curso requiere laboratorio/práctica
    print(f"\n   🔧 CONFIGURACIÓN DEL CURSO:")
    print(f"      Requiere laboratorio: {section.course.requiere_laboratorio}")
    print(f"      Requiere práctica: {section.course.requiere_practica}")
    print(f"      Modalidad: {section.course.modalidad}")
    
    # Verificar grupos configurados
    print(f"\n   📊 GRUPOS CONFIGURADOS:")
    print(f"      Teoría: {section.course.grupos_teoria}")
    print(f"      Práctica: {section.course.grupos_practica}")
    print(f"      Laboratorio: {section.course.grupos_laboratorio}")

print("\n" + "="*80)
print("POSIBLES CAUSAS DE NO ASIGNACIÓN:")
print("="*80)
print("""
1. ❌ No hay profesores asignados en professor_course_assignments
2. ❌ Los profesores asignados no tienen disponibilidad (restricciones horarias)
3. ❌ No hay aulas disponibles con suficiente capacidad
4. ❌ Conflicto con otras secciones de mayor prioridad
5. ❌ El algoritmo no encontró una combinación válida de:
   - Profesor disponible
   - Aula con capacidad suficiente (55 alumnos)
   - Timeslots consecutivos sin conflictos
""")

db.close()
