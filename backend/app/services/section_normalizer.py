from __future__ import annotations

from typing import List

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import CourseSection


class NRCGenerator:
    """Genera códigos NRC únicos de manera incremental."""

    def __init__(self, db: Session):
        max_nrc = db.query(func.max(CourseSection.nrc)).scalar()
        start = 1999
        if isinstance(max_nrc, (int, float)):
            start = int(max_nrc)
        elif isinstance(max_nrc, str) and max_nrc.isdigit():
            start = int(max_nrc)
        self._value = start

    def next(self) -> str:
        self._value += 1
        return str(self._value)


class SectionNormalizer:
    """Normaliza ligas y NRC de secciones de un curso."""

    @staticmethod
    def _balanced_distribution(total: int, buckets: int) -> List[int]:
        if buckets <= 0:
            return []
        base = total // buckets
        remainder = total % buckets
        return [base + (1 if idx < remainder else 0) for idx in range(buckets)]

    @staticmethod
    def normalize_sections(sections: List[CourseSection], generator: NRCGenerator) -> bool:
        """Normaliza ligas, secciones y NRC. Retorna True si hubo cambios."""
        if not sections:
            return False

        changed = False

        theories = sorted((s for s in sections if s.tipo == 'teoria'), key=lambda s: s.id)
        practices = sorted((s for s in sections if s.tipo == 'practica'), key=lambda s: s.id)
        labs = sorted((s for s in sections if s.tipo == 'laboratorio'), key=lambda s: s.id)

        total_leagues = len(theories)
        effective_leagues = total_leagues if total_leagues > 0 else (1 if (practices or labs) else 0)

        for idx, section in enumerate(theories, start=1):
            if section.league != idx:
                section.league = idx
                changed = True
            expected_seccion = f"T{idx}"
            if section.seccion != expected_seccion:
                section.seccion = expected_seccion
                changed = True
            if not section.nrc:
                section.nrc = generator.next()
                changed = True

        def assign_to_leagues(section_list: List[CourseSection], prefix: str) -> None:
            nonlocal changed
            if not section_list:
                return
            buckets = effective_leagues or 1
            distribution = SectionNormalizer._balanced_distribution(len(section_list), buckets)
            pointer = 0
            for league_index, count in enumerate(distribution, start=1):
                target_league = league_index if effective_leagues else 1
                for _ in range(count):
                    if pointer >= len(section_list):
                        return
                    section = section_list[pointer]
                    pointer += 1
                    expected_seccion = f"{prefix}{target_league}"
                    if section.league != target_league:
                        section.league = target_league
                        changed = True
                    if section.seccion != expected_seccion:
                        section.seccion = expected_seccion
                        changed = True
                    if not section.nrc:
                        section.nrc = generator.next()
                        changed = True

        assign_to_leagues(practices, 'P')
        assign_to_leagues(labs, 'L')

        return changed


def normalize_all_courses(db: Session) -> dict:
    """Normaliza todas las secciones existentes en la base de datos."""
    generator = NRCGenerator(db)
    course_ids = [row[0] for row in db.query(CourseSection.course_id).distinct().order_by(CourseSection.course_id)]

    courses_updated = 0
    sections_updated = 0

    for course_id in course_ids:
        sections = (
            db.query(CourseSection)
            .filter(CourseSection.course_id == course_id)
            .order_by(CourseSection.id)
            .all()
        )

        if SectionNormalizer.normalize_sections(sections, generator):
            courses_updated += 1
            sections_updated += len(sections)

    if sections_updated:
        db.commit()

    return {
        'courses_processed': len(course_ids),
        'courses_updated': courses_updated,
        'sections_updated': sections_updated,
    }