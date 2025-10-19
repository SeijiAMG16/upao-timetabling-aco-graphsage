#!/usr/bin/env python3
"""Agrega asignaciones placeholder para cursos sin profesor asignado."""

from typing import Dict, Tuple

from sqlalchemy import text

from app.database import SessionLocal
from app.models import CourseSection

PLACEHOLDER_PROFESSOR_ID = 353  # CONVOCATORIA
SEMESTER_CODE = "2025-20"


def map_section_type(section_type: str) -> str:
    tipo = (section_type or "").upper()
    if tipo.startswith("T"):
        return "T"
    if tipo.startswith("P"):
        return "P"
    if tipo.startswith("L"):
        return "L"
    return "T"


def find_sections_without_professor(db) -> Dict[Tuple[int, str, int], CourseSection]:
    sections = (
        db.query(CourseSection)
        .filter(CourseSection.activa == True)  # noqa: E712
        .all()
    )
    result: Dict[Tuple[int, str, int], CourseSection] = {}

    # Pre-cargar asignaciones existentes
    existing = db.execute(
        text(
            "SELECT course_id, session_type, league "
            "FROM professor_course_assignments"
        )
    ).fetchall()

    assigned_keys = {
        (row.course_id, (row.session_type or "").upper(), row.league or 1)
        for row in existing
    }

    for section in sections:
        course_id = section.course_id
        session_type = map_section_type(section.tipo)
        league = section.league or 1
        key = (course_id, session_type, league)
        if key not in assigned_keys:
            result[key] = section

    return result


def insert_placeholder_assignments(db, missing_sections: Dict[Tuple[int, str, int], CourseSection]) -> None:
    for (course_id, session_type, league), section in missing_sections.items():
        exists = db.execute(
            text(
                "SELECT id FROM professor_course_assignments "
                "WHERE course_id = :course_id AND session_type = :session_type AND league = :league"
            ),
            {
                "course_id": course_id,
                "session_type": session_type,
                "league": league,
            },
        ).fetchone()
        if exists:
            continue

        db.execute(
            text(
                "INSERT INTO professor_course_assignments "
                "(professor_id, course_id, session_type, league, semestre) "
                "VALUES (:professor_id, :course_id, :session_type, :league, :semestre)"
            ),
            {
                "professor_id": PLACEHOLDER_PROFESSOR_ID,
                "course_id": course_id,
                "session_type": session_type,
                "league": league,
                "semestre": SEMESTER_CODE,
            },
        )
        print(
            f"Asignacion placeholder creada: curso {course_id}, tipo {session_type}, liga {league}, seccion {section.seccion}"
        )


def main() -> None:
    db = SessionLocal()
    try:
        missing_sections = find_sections_without_professor(db)
        if not missing_sections:
            print("No hay secciones sin profesor asignado.")
            return

        insert_placeholder_assignments(db, missing_sections)
        db.commit()
        print("Placeholders insertados correctamente.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
