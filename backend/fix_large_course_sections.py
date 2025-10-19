import math
import re
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

from app.database import SessionLocal
from app.models import Course, CourseSection
from app.services.section_normalizer import NRCGenerator, SectionNormalizer

MAX_SECTION_SIZE = 60
TARGET_SECTION_IDS = [1682, 1683, 1716, 1717, 1734, 1735, 1689, 1696]
SECTION_PREFIX_FALLBACK = {
    "teoria": "T",
    "practica": "P",
    "laboratorio": "L",
}
SECTION_TYPE_FIELDS: Dict[str, Tuple[str, str]] = {
    "teoria": ("alumnos_teoria", "grupos_teoria"),
    "practica": ("alumnos_practica", "grupos_practica"),
    "laboratorio": ("alumnos_laboratorio", "grupos_laboratorio"),
}
CODE_PATTERN = re.compile(r"^([A-Za-z]+)(\d+)$")


def _infer_prefix(section: CourseSection) -> str:
    section_type = (section.tipo or "").lower()
    raw = (section.seccion or "").strip().upper()
    if not raw:
        return SECTION_PREFIX_FALLBACK.get(section_type, "S")
    letters = "".join(ch for ch in raw if ch.isalpha())
    if letters:
        return letters
    return SECTION_PREFIX_FALLBACK.get(section_type, raw or "S")


def _collect_used_codes(sections: List[CourseSection]) -> Set[str]:
    return {((s.seccion or "").strip().upper()) for s in sections if s.seccion}


def _collect_used_leagues(sections: List[CourseSection]) -> Set[int]:
    return {s.league for s in sections if isinstance(s.league, int) and s.league > 0}


def _next_league(used: Set[int]) -> int:
    candidate = 1
    while candidate in used:
        candidate += 1
    used.add(candidate)
    return candidate


def _next_code(prefix: str, used_codes: Set[str]) -> str:
    match = CODE_PATTERN.match(prefix)
    base_prefix = prefix if not match else match.group(1)
    counter = 1
    while True:
        candidate = f"{base_prefix}{counter}"
        if candidate not in used_codes:
            used_codes.add(candidate)
            return candidate
        counter += 1


def _distribute_section(section: CourseSection, db) -> List[CourseSection]:
    if section.alumnos_proyectados <= MAX_SECTION_SIZE:
        return []

    same_group = (
        db.query(CourseSection)
        .filter(
            CourseSection.course_id == section.course_id,
            CourseSection.tipo == section.tipo,
            CourseSection.id != section.id,
        )
        .order_by(CourseSection.id)
        .all()
    )

    used_codes = _collect_used_codes([section] + same_group)
    used_leagues = _collect_used_leagues([section] + same_group)
    prefix = _infer_prefix(section)

    total = section.alumnos_proyectados
    section.alumnos_proyectados = min(MAX_SECTION_SIZE, total)
    remaining = total - section.alumnos_proyectados

    created: List[CourseSection] = []
    while remaining > 0:
        new_size = min(MAX_SECTION_SIZE, remaining)
        new_code = _next_code(prefix, used_codes)
        new_league = _next_league(used_leagues)
        new_section = CourseSection(
            course_id=section.course_id,
            tipo=section.tipo,
            seccion=new_code,
            league=new_league,
            alumnos_proyectados=new_size,
            alumnos_reales=0,
            activa=section.activa,
        )
        db.add(new_section)
        created.append(new_section)
        remaining -= new_size

    return created


def _recalculate_course_totals(course: Course, sections: List[CourseSection]) -> None:
    grouped: Dict[str, List[CourseSection]] = defaultdict(list)
    for section in sections:
        if not section.activa:
            continue
        key = (section.tipo or "").lower()
        grouped[key].append(section)

    for tipo, (students_field, groups_field) in SECTION_TYPE_FIELDS.items():
        entries = grouped.get(tipo, [])
        setattr(course, students_field, sum(s.alumnos_proyectados for s in entries))
        setattr(course, groups_field, len(entries))


def main(section_ids: Optional[List[int]] = None) -> None:
    ids = section_ids or TARGET_SECTION_IDS
    session = SessionLocal()
    touched_courses: Set[int] = set()
    created_total = 0
    updated_total = 0

    try:
        for section_id in ids:
            section: Optional[CourseSection] = session.query(CourseSection).get(section_id)
            if section is None:
                print(f"ADVERTENCIA: Sección {section_id} no encontrada")
                continue
            touched_courses.add(section.course_id)
            before = section.alumnos_proyectados
            created = _distribute_section(section, session)
            if created:
                updated_total += 1
                created_total += len(created)
                print(
                    f"DIVIDIR: Sección {section_id} de {before} alumnos pasa a {section.alumnos_proyectados} + {[s.alumnos_proyectados for s in created]}"
                )
            elif section.alumnos_proyectados > MAX_SECTION_SIZE:
                section.alumnos_proyectados = MAX_SECTION_SIZE
                updated_total += 1
                print(
                    f"AJUSTE: Sección {section_id} limitada a {MAX_SECTION_SIZE} alumnos sin nuevas ligas"
                )

        generator = NRCGenerator(session)
        for course_id in touched_courses:
            sections = (
                session.query(CourseSection)
                .filter(CourseSection.course_id == course_id)
                .order_by(CourseSection.id)
                .all()
            )
            if SectionNormalizer.normalize_sections(sections, generator):
                print(f"NORMALIZACION: Ligas y NRC del curso {course_id} actualizados")
            course = session.query(Course).get(course_id)
            if course:
                _recalculate_course_totals(course, sections)

        session.commit()
        print(
            f"COMPLETADO: Secciones actualizadas {updated_total}, secciones nuevas {created_total}"
        )
    except Exception as exc:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
