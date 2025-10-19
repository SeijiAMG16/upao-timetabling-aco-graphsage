"""
Analizar la sección 1815 que está bloqueando el ACO
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import CourseSection, Course, Classroom

engine = create_engine('mysql+pymysql://root:sistemas@localhost:3306/upao_timetabling')
Session = sessionmaker(bind=engine)
session = Session()

print("="*80)
print("ANÁLISIS DE SECCIÓN 1815")
print("="*80)

# Buscar sección 1815
seccion = session.query(CourseSection).filter_by(id=1815).first()

if not seccion:
    print("❌ No se encontró la sección 1815")
    session.close()
    exit(1)

print(f"\n📋 DATOS DE LA SECCIÓN:")
print(f"  ID: {seccion.id}")
print(f"  Sección: {seccion.seccion}")
print(f"  Tipo: {seccion.tipo}")
print(f"  Liga: {seccion.league}")
print(f"  Estudiantes proyectados: {seccion.alumnos_proyectados}")
print(f"  Duración (si está en DB): {getattr(seccion, 'duracion_bloques', 'N/A')}")

# Buscar curso
curso = session.query(Course).filter_by(id=seccion.course_id).first()
if curso:
    print(f"\n📚 CURSO ASOCIADO:")
    print(f"  Código: {curso.codigo}")
    print(f"  Nombre: {curso.nombre}")
    print(f"  Ciclo: {curso.ciclo}")
    print(f"  Requiere laboratorio: {curso.requiere_laboratorio}")
    print(f"  Requiere práctica: {curso.requiere_practica}")

# Verificar qué aulas son compatibles
print(f"\n🏢 AULAS COMPATIBLES:")

# Determinar tipo de aula necesario
tipo_section_key = (seccion.tipo or "")[0].upper() if seccion.tipo else ""
print(f"  Tipo sección clave: '{tipo_section_key}'")

if tipo_section_key == 'L':
    tipo_aula_requerido = 'LAB'
    print(f"  ➡️ Necesita aulas tipo: {tipo_aula_requerido}")
elif tipo_section_key in ['T', 'P']:
    tipo_aula_requerido = 'NOLAB'
    print(f"  ➡️ Necesita aulas tipo: {tipo_aula_requerido}")
else:
    tipo_aula_requerido = 'DESCONOCIDO'
    print(f"  ⚠️ Tipo no reconocido: '{seccion.tipo}'")

# Buscar aulas compatibles
aulas_compatibles = session.query(Classroom).filter(
    Classroom.tipo == tipo_aula_requerido,
    Classroom.capacidad >= (seccion.alumnos_proyectados or 0)
).all()

print(f"\n  Total aulas compatibles: {len(aulas_compatibles)}")
if aulas_compatibles:
    print(f"  Primeras 10 aulas:")
    for aula in aulas_compatibles[:10]:
        print(f"    - {aula.codigo}: cap {aula.capacidad}, tipo {aula.tipo}, edificio {aula.edificio}")
else:
    print(f"  ❌ NO HAY AULAS COMPATIBLES")
    print(f"\n  Buscando aulas disponibles:")
    todas_aulas = session.query(Classroom).all()
    print(f"    Total aulas en DB: {len(todas_aulas)}")
    aulas_lab = session.query(Classroom).filter_by(tipo='LAB').all()
    aulas_nolab = session.query(Classroom).filter_by(tipo='NOLAB').all()
    print(f"    Aulas LAB: {len(aulas_lab)}")
    print(f"    Aulas NOLAB: {len(aulas_nolab)}")
    
    # Buscar aulas con capacidad suficiente
    aulas_capacidad = session.query(Classroom).filter(
        Classroom.capacidad >= (seccion.alumnos_proyectados or 0)
    ).all()
    print(f"    Aulas con capacidad >={seccion.alumnos_proyectados}: {len(aulas_capacidad)}")
    
    # Buscar aulas del tipo correcto (sin filtro de capacidad)
    if tipo_aula_requerido != 'DESCONOCIDO':
        aulas_tipo = session.query(Classroom).filter_by(tipo=tipo_aula_requerido).all()
        print(f"    Aulas tipo {tipo_aula_requerido}: {len(aulas_tipo)}")
        if aulas_tipo:
            print(f"    Capacidades disponibles:")
            for aula in sorted(aulas_tipo, key=lambda x: x.capacidad, reverse=True)[:5]:
                print(f"      - {aula.codigo}: cap {aula.capacidad}")

# Verificar otras secciones del mismo curso/liga
print(f"\n🔗 OTRAS SECCIONES DE LA MISMA LIGA:")
otras_secciones = session.query(CourseSection).filter(
    CourseSection.course_id == seccion.course_id,
    CourseSection.league == seccion.league,
    CourseSection.id != seccion.id
).all()

print(f"  Total: {len(otras_secciones)}")
for sec in otras_secciones:
    print(f"    - [{sec.id}] {sec.seccion}: tipo {sec.tipo}, {sec.alumnos_proyectados} est")

session.close()
