"""
Depurar qué candidatos se están obteniendo para TESIS II por liga
"""
import os
import sys
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Enum
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()

class ProfessorCourseAssignment(Base):
    __tablename__ = 'professor_course_assignments'
    id = Column(Integer, primary_key=True)
    course_id = Column(String(50))
    professor_id = Column(Integer)
    session_type = Column(Enum('T', 'P', 'L'))
    league = Column(Integer)

class CourseSection(Base):
    __tablename__ = 'course_sections'
    id = Column(Integer, primary_key=True)
    course_id = Column(String(50))
    tipo = Column(Enum('teoria', 'practica', 'laboratorio'))
    league = Column(Integer)
    alumnos_proyectados = Column(Integer)
    activa = Column(Boolean)

def main():
    # Conectar a BD
    DB_URL = "mysql+pymysql://root:upaotesis2024@localhost:3306/timetabling_sys"
    engine = create_engine(DB_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    print("\n" + "="*80)
    print("TESIS II (HUMA900) - Asignaciones en BD")
    print("="*80)
    
    # Obtener asignaciones de profesores para HUMA900
    assignments = session.query(ProfessorCourseAssignment).filter(
        ProfessorCourseAssignment.course_id == 'HUMA900'
    ).all()
    
    print(f"\nTotal de asignaciones en BD: {len(assignments)}")
    for assign in assignments:
        print(f"  Profesor {assign.professor_id} - Tipo: {assign.session_type} - Liga: {assign.league}")
    
    print("\n" + "="*80)
    print("Secciones de TESIS II activas")
    print("="*80)
    
    sections = session.query(CourseSection).filter(
        CourseSection.course_id == 'HUMA900',
        CourseSection.activa == True
    ).all()
    
    print(f"\nTotal de secciones: {len(sections)}")
    for sec in sections:
        print(f"  Sección {sec.id} - Tipo: {sec.tipo} - Liga: {sec.league} - Alumnos: {sec.alumnos_proyectados}")
    
    # Ahora vamos a simular lo que hace _candidate_professors_for_section
    print("\n" + "="*80)
    print("SIMULACIÓN: Candidatos por sección")
    print("="*80)
    
    # Agrupar asignaciones como lo hace _load_professor_assignments
    from collections import defaultdict
    
    prof_assign_by_league = {}
    prof_assign_by_type = {}
    prof_assign_by_course = defaultdict(set)
    
    # Agrupar por (course_id, session_type)
    grouped = defaultdict(list)
    for assign in assignments:
        key = (assign.course_id, assign.session_type)
        grouped[key].append((assign.league, assign.professor_id))
        prof_assign_by_course[assign.course_id].add(assign.professor_id)
    
    # Detectar cursos con diferenciación de liga
    courses_with_leagues = set()
    for (course_id, session_type), leagues_data in grouped.items():
        unique_leagues = {league for league, _ in leagues_data}
        if len(unique_leagues) > 1:
            courses_with_leagues.add((course_id, session_type))
            print(f"\n✓ Curso {course_id}-{session_type} TIENE diferenciación de liga ({len(unique_leagues)} ligas)")
        
        # Construir diccionarios
        for league, prof_id in leagues_data:
            key_league = (course_id, session_type, league)
            if key_league not in prof_assign_by_league:
                prof_assign_by_league[key_league] = set()
            prof_assign_by_league[key_league].add(prof_id)
        
        # Solo agregar a prof_assign_by_type si NO hay diferenciación de liga
        if (course_id, session_type) not in courses_with_leagues:
            key_type = (course_id, session_type)
            if key_type not in prof_assign_by_type:
                prof_assign_by_type[key_type] = set()
            for league, prof_id in leagues_data:
                prof_assign_by_type[key_type].add(prof_id)
    
    print("\n" + "-"*80)
    print("Diccionarios construidos:")
    print("-"*80)
    print(f"\nprof_assign_by_league (por liga exacta):")
    for key, profs in prof_assign_by_league.items():
        if key[0] == 'HUMA900':
            print(f"  {key}: {sorted(profs)}")
    
    print(f"\nprof_assign_by_type (por tipo, sin diferenciación):")
    for key, profs in prof_assign_by_type.items():
        if key[0] == 'HUMA900':
            print(f"  {key}: {sorted(profs)}")
    
    print(f"\nprof_assign_by_course (por curso general):")
    print(f"  HUMA900: {sorted(prof_assign_by_course['HUMA900'])}")
    
    # Simular _candidate_professors_for_section para cada sección
    print("\n" + "="*80)
    print("PASO A PASO: Búsqueda de candidatos (LÓGICA V5)")
    print("="*80)
    
    for sec in sections:
        course_id = sec.course_id
        session_type = sec.tipo
        league = sec.league or 1
        
        print(f"\nSección {sec.id} - {course_id} - {session_type} - Liga {league}")
        print(f"  Alumnos: {sec.alumnos_proyectados}")
        
        # PASO 1: Buscar por liga exacta
        key_league = (course_id, session_type, league)
        if key_league in prof_assign_by_league:
            candidates = sorted(prof_assign_by_league[key_league])
            print(f"  ✓ PASO 1 (liga exacta): {candidates}")
            continue
        else:
            print(f"  ✗ PASO 1 (liga exacta): NO encontrado")
        
        # PASO 2: Buscar por tipo general (SOLO si NO hay diferenciación de liga)
        key_type = (course_id, session_type)
        if key_type in prof_assign_by_type:
            candidates = sorted(prof_assign_by_type[key_type])
            print(f"  ✓ PASO 2 (tipo general): {candidates}")
            continue
        else:
            print(f"  ✗ PASO 2 (tipo general): NO encontrado")
        
        # PASO 3: Buscar por curso
        if course_id in prof_assign_by_course:
            candidates = sorted(prof_assign_by_course[course_id])
            print(f"  ✓ PASO 3 (curso general): {candidates}")
            continue
        else:
            print(f"  ✗ PASO 3 (curso general): NO encontrado")
        
        print(f"  ❌ SIN CANDIDATOS")
    
    session.close()

if __name__ == "__main__":
    main()
