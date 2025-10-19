import sys
sys.path.insert(0, 'app')
from models import CourseSection, Course
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine('mysql+pymysql://root:sistemas@localhost:3306/upao_timetabling')
Session = sessionmaker(bind=engine)
s = Session()

# Buscar todas las secciones de ICSI506
curso = s.query(Course).filter_by(codigo='ICSI506').first()
if curso:
    secciones = s.query(CourseSection).filter_by(course_id=curso.id).order_by(CourseSection.league, CourseSection.tipo).all()
    
    print(f"Curso: {curso.codigo} - {curso.nombre}")
    print(f"Total secciones: {len(secciones)}\n")
    
    by_league = {}
    for sec in secciones:
        key = sec.league if sec.league else 0
        if key not in by_league:
            by_league[key] = []
        by_league[key].append(sec)
    
    for liga, secs in sorted(by_league.items()):
        print(f"Liga {liga}:")
        for sec in secs:
            print(f"  [{sec.id}] {sec.tipo.upper():12} {sec.seccion:4} - {sec.alumnos_proyectados:2} est")
        print()
