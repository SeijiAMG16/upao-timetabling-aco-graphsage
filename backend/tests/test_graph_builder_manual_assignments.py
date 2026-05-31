import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.models import (
    Base,
    Course,
    CourseSection,
    Professor,
    ProfessorCourseAssignment,
)
from app.aco_graphsage.graph_builder import TimetableGraphBuilder


@pytest.fixture
def session():
    """Provide an isolated in-memory database for each test."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db_session = SessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()
        Base.metadata.drop_all(engine)


def _create_course_with_section(db_session, *, league=1, session_type="T"):
    course = Course(
        codigo="TEST101",
        nombre="Validación Manual",
        ciclo=1,
        modalidad="presencial",
        alumnos_teoria=30,
    )
    db_session.add(course)
    db_session.flush()

    section = CourseSection(
        course_id=course.id,
        tipo=session_type,
        seccion="01",
        league=league,
        alumnos_proyectados=30,
        active=True,
    )
    db_session.add(section)
    db_session.flush()

    return course, section


def test_candidate_professors_prioritises_manual_assignments(session):
    course, section = _create_course_with_section(session)

    prof_relationship_only = Professor(codigo="P100", nombre_completo="Relacionado")
    prof_by_league = Professor(codigo="P200", nombre_completo="Manual Liga")
    prof_by_type = Professor(codigo="P300", nombre_completo="Manual Tipo")
    prof_by_course = Professor(codigo="P400", nombre_completo="Manual Curso")

    session.add_all([
        prof_relationship_only,
        prof_by_league,
        prof_by_type,
        prof_by_course,
    ])
    session.flush()

    course.professors = [
        prof_relationship_only,
        prof_by_league,
        prof_by_type,
        prof_by_course,
    ]
    session.flush()

    session.add_all([
        ProfessorCourseAssignment(
            course_id=course.id,
            professor_id=prof_by_league.id,
            session_type="T",
            league=section.league,
        ),
        ProfessorCourseAssignment(
            course_id=course.id,
            professor_id=prof_by_type.id,
            session_type="T",
            league=None,
        ),
        ProfessorCourseAssignment(
            course_id=course.id,
            professor_id=prof_by_course.id,
            session_type=None,
            league=None,
        ),
    ])
    session.commit()

    builder = TimetableGraphBuilder(session)
    builder._load_professor_assignments()

    candidates = builder._candidate_professors_for_section(section)

    expected_manual_ids = sorted(
        [prof_by_league.id, prof_by_type.id, prof_by_course.id]
    )
    assert candidates == expected_manual_ids


def test_candidate_professors_falls_back_to_course_professors(session):
    course, section = _create_course_with_section(session, league=2)

    prof_primary = Professor(codigo="P500", nombre_completo="Docente 1")
    prof_secondary = Professor(codigo="P600", nombre_completo="Docente 2")
    session.add_all([prof_primary, prof_secondary])
    session.flush()

    session.add_all([
        ProfessorCourseAssignment(course_id=course.id, professor_id=prof_primary.id, session_type=None, league=None),
        ProfessorCourseAssignment(course_id=course.id, professor_id=prof_secondary.id, session_type=None, league=None),
    ])
    session.commit()

    builder = TimetableGraphBuilder(session)
    builder._load_professor_assignments()

    candidates = builder._candidate_professors_for_section(section)

    expected_ids = sorted([prof_primary.id, prof_secondary.id])
    assert candidates == expected_ids
