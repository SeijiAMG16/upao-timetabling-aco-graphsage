"""
Identifica información de las secciones problemáticas
"""
import sys
sys.path.insert(0, 'app')

from models import CourseSection, Classroom
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine('mysql+pymysql://root:sistemas@localhost:3306/upao_timetabling')
Session = sessionmaker(bind=engine)
session = Session()

secciones_ids = [1552, 1553, 1554, 1608, 1609, 1610, 1611, 1612, 1613, 1631,
                 1550, 1551, 1616, 1617, 1574, 1592, 1570]

print("=" * 80)
print("SECCIONES PROBLEMÁTICAS")
print("=" * 80)

grupos = {}

for sec_id in sorted(secciones_ids):
    sec = session.query(CourseSection).filter_by(id=sec_id).first()
    if sec:
        codigo = sec.course.codigo if sec.course else "???"
        nombre = sec.course.nombre if sec.course else "???"
        print(f"\n{sec.id}: {codigo} - {nombre}")
        print(f"  Tipo: {sec.tipo}, Sección: {sec.seccion}")
        print(f"  Liga: {sec.league}, Alumnos: {sec.alumnos_proyectados}")
        print(f"  NRC: {sec.nrc}")
        
        # Agrupar por curso y liga
        key = (codigo, sec.league if sec.league else 0)
        if key not in grupos:
            grupos[key] = []
        grupos[key].append(sec)

print("\n" + "=" * 80)
print("GRUPOS IDENTIFICADOS")
print("=" * 80)

for (codigo, liga), secciones in sorted(grupos.items()):
    print(f"\n{codigo} - Liga {liga}:")
    for sec in secciones:
        print(f"  [{sec.id}] {sec.tipo}-{sec.seccion}: {sec.alumnos_proyectados} estudiantes")
    
    # Verificar aulas disponibles
    max_estudiantes = max(s.alumnos_proyectados for s in secciones)
    requiere_lab = any(s.tipo.lower() == 'laboratorio' for s in secciones)
    
    tipo_aula = 'LAB' if requiere_lab else 'TEORICA'
    
    aulas = session.query(Classroom).filter(
        Classroom.is_available == 1,
        Classroom.capacity >= max_estudiantes
    ).filter(
        (Classroom.room_type == tipo_aula) | (Classroom.room_type == 'TEORICA_LAB')
    ).order_by(Classroom.capacity).limit(3).all()
    
    print(f"\n  Aulas disponibles (tipo {tipo_aula}, cap >= {max_estudiantes}):")
    if aulas:
        for aula in aulas:
            print(f"    {aula.name}: capacidad {aula.capacity}, tipo {aula.room_type}")
    else:
        print(f"    ❌ NO HAY AULAS DISPONIBLES")

print("\n" + "=" * 80)
print("LISTA DE PRIORIDADES SUGERIDA")
print("=" * 80)
print("\npriority_course_groups = [")
for (codigo, liga), secciones in sorted(grupos.items(), key=lambda item: max(s.alumnos_proyectados for s in item[1]), reverse=True):
    max_est = max(s.alumnos_proyectados for s in secciones)
    print(f'    ("{codigo}", {liga}),  # {max_est} estudiantes')
print("]")

session.close()
