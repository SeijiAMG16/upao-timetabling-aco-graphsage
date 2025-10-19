#!/usr/bin/env python3
"""
Analiza la base de datos actual para detectar posibles problemas
que impidan la generacion de horarios con el modelo ACO+GraphSAGE.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Set, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session, joinedload

from app.database import SessionLocal
from app.models import (
    Classroom,
    Course,
    CourseSection,
    Professor,
    ProfessorRestriction,
    TimeSlot,
)


@dataclass
class SectionDiagnostics:
    section_id: int
    course_code: str
    section_type: str
    section_label: str
    projected_students: int
    candidate_professors: int
    candidate_classrooms: int
    has_valid_timeslot: bool
    max_allowed_capacity: int


def duration_blocks(section: CourseSection) -> int:
    """Calcula la duracion en bloques de 50 minutos."""
    tipo = (section.tipo or "").upper()
    if tipo == "L":
        return 3
    if tipo in ("T", "P"):
        return 2
    return 1


def load_sections(db: Session) -> List[CourseSection]:
    """Carga secciones activas con sus relaciones necesarias."""
    return (
        db.query(CourseSection)
        .options(
            joinedload(CourseSection.course).joinedload(Course.professors),
            joinedload(CourseSection.course),
        )
        .filter(CourseSection.activa == True)  # noqa: E712
        .all()
    )


def load_professors(db: Session) -> List[Professor]:
    return db.query(Professor).options(joinedload(Professor.restrictions)).all()


def load_classrooms(db: Session) -> List[Classroom]:
    return (
        db.query(Classroom)
        .filter(Classroom.active == True)  # noqa: E712
        .all()
    )


def load_timeslots(db: Session) -> List[TimeSlot]:
    return (
        db.query(TimeSlot)
        .filter(TimeSlot.activo == True)  # noqa: E712
        .order_by(TimeSlot.dia_semana, TimeSlot.orden)
        .all()
    )


def analyze_sections(
    sections: Iterable[CourseSection],
    classrooms: List[Classroom],
    timeslots: List[TimeSlot],
    assign_by_league: Dict[Tuple[int, str, int], List[int]],
    assign_by_type: Dict[Tuple[int, str], List[int]],
    assign_by_course: Dict[int, List[int]],
) -> Tuple[List[SectionDiagnostics], List[str], Dict[int, int]]:
    """Genera diagnosticos por seccion y alertas globales."""
    alerts: List[str] = []
    diagnostics: List[SectionDiagnostics] = []

    classrooms_by_id = {room.id: room for room in classrooms}
    classrooms_sorted = list(classrooms_by_id.values())

    timeslots_by_day: Dict[int, List[TimeSlot]] = defaultdict(list)
    for ts in timeslots:
        timeslots_by_day[ts.dia_semana].append(ts)
    for day_slots in timeslots_by_day.values():
        day_slots.sort(key=lambda x: x.orden)

    valid_starts_cache: Dict[int, int] = {}

    for section in sections:
        sec_type = (section.tipo or "").upper()
        course = section.course
        candidate_professors = count_candidate_professors(
            section,
            assign_by_league,
            assign_by_type,
            assign_by_course,
        )

        compatible_classrooms = 0
        projected = section.alumnos_proyectados or 0
        max_allowed_capacity = 0
        for room in classrooms_sorted:
            room_type = (room.tipo or "").lower()
            if sec_type == "L" and room_type not in {"laboratorio", "lab"}:
                continue
            room_capacity = room.capacidad or 0
            if room_capacity > max_allowed_capacity:
                max_allowed_capacity = room_capacity
            if room_capacity < projected:
                continue
            compatible_classrooms += 1

        duration = duration_blocks(section)
        if duration not in valid_starts_cache:
            valid_starts_cache[duration] = count_valid_starts(timeslots_by_day, duration)
        has_valid_ts = valid_starts_cache[duration] > 0

        diagnostics.append(
            SectionDiagnostics(
                section_id=section.id,
                course_code=course.codigo,
                section_type=sec_type,
                section_label=section.seccion,
                projected_students=projected,
                candidate_professors=candidate_professors,
                candidate_classrooms=compatible_classrooms,
                has_valid_timeslot=has_valid_ts,
                max_allowed_capacity=max_allowed_capacity,
            )
        )

    # Alertas globales
    missing_prof_sections = [d for d in diagnostics if d.candidate_professors == 0]
    if missing_prof_sections:
        alerts.append(
            f"Secciones sin profesores asignados: {len(missing_prof_sections)}"
        )

    no_classroom_sections = [d for d in diagnostics if d.candidate_classrooms == 0]
    if no_classroom_sections:
        alerts.append(
            f"Secciones sin aulas compatibles: {len(no_classroom_sections)}"
        )

    over_capacity_sections = [
        d
        for d in diagnostics
        if d.projected_students > (d.max_allowed_capacity or 0)
    ]
    if over_capacity_sections:
        alerts.append(
            "Secciones con alumnos proyectados mayores a la capacidad maxima disponible: "
            f"{len(over_capacity_sections)}"
        )

    no_slot_sections = [d for d in diagnostics if not d.has_valid_timeslot]
    if no_slot_sections:
        alerts.append(
            f"Secciones sin bloques horarios consecutivos disponibles: {len(no_slot_sections)}"
        )

    return diagnostics, alerts, valid_starts_cache


def count_valid_starts(
    timeslots_by_day: Dict[int, List[TimeSlot]],
    duration: int,
) -> int:
    if duration <= 1:
        return sum(len(day_slots) for day_slots in timeslots_by_day.values())
    total = 0
    for day_slots in timeslots_by_day.values():
        for idx in range(len(day_slots)):
            start_slot = day_slots[idx]
            if idx + duration - 1 >= len(day_slots):
                continue
            consecutive = True
            for offset in range(1, duration):
                next_slot = day_slots[idx + offset]
                if next_slot.orden != start_slot.orden + offset:
                    consecutive = False
                    break
            if consecutive:
                total += 1
    return total


def analyze_professor_restrictions(
    professors: Iterable[Professor],
    timeslots: List[TimeSlot],
) -> Tuple[List[str], List[str]]:
    """Devuelve alertas y detalles sobre restricciones de profesores."""
    alerts: List[str] = []
    details: List[str] = []

    timeslots_by_day: Dict[int, List[TimeSlot]] = defaultdict(list)
    for ts in timeslots:
        timeslots_by_day[ts.dia_semana].append(ts)
    for day_slots in timeslots_by_day.values():
        day_slots.sort(key=lambda x: x.orden)

    day_names = {1: "Lunes", 2: "Martes", 3: "Miercoles", 4: "Jueves", 5: "Viernes", 6: "Sabado"}

    for prof in professors:
        restricted_slots = map_restrictions_to_slots(prof.restrictions, timeslots_by_day)
        total_slots = sum(len(day_slots) for day_slots in timeslots_by_day.values())

        if total_slots == 0:
            continue

        if len(restricted_slots) >= total_slots:
            alerts.append(
                f"El profesor {prof.nombre_completo} tiene restricciones en todas las franjas"
            )
            continue

        slots_by_day = defaultdict(list)
        for ts_id in restricted_slots:
            day = find_day_for_slot(ts_id, timeslots_by_day)
            if day is not None:
                slots_by_day[day].append(ts_id)

        for day, slots in slots_by_day.items():
            if len(slots) == len(timeslots_by_day[day]):
                details.append(
                    f"Profesor {prof.nombre_completo} sin disponibilidad el {day_names.get(day, str(day))}"
                )

    return alerts, details


def map_restrictions_to_slots(
    restrictions: Iterable[ProfessorRestriction],
    timeslots_by_day: Dict[int, List[TimeSlot]],
) -> Set[int]:
    """Mapea restricciones a identificadores de franjas."""
    result: Set[int] = set()
    day_map = {
        "Monday": 1,
        "Tuesday": 2,
        "Wednesday": 3,
        "Thursday": 4,
        "Friday": 5,
        "Saturday": 6,
    }
    for restriction in restrictions:
        day_num = day_map.get(restriction.day)
        if day_num is None:
            continue
        day_slots = timeslots_by_day.get(day_num, [])
        for ts in day_slots:
            if time_slot_in_range(ts, restriction.start_time, restriction.end_time):
                result.add(ts.id)
    return result


def time_to_minutes(value: str) -> int:
    hour, minute = value.split(":")
    return int(hour) * 60 + int(minute)


def time_slot_in_range(ts: TimeSlot, start: str, end: str) -> bool:
    ts_start = time_to_minutes(ts.hora_inicio)
    range_start = time_to_minutes(start)
    range_end = time_to_minutes(end)
    return range_start <= ts_start < range_end


def find_day_for_slot(slot_id: int, timeslots_by_day: Dict[int, List[TimeSlot]]) -> int:
    for day, slots in timeslots_by_day.items():
        for ts in slots:
            if ts.id == slot_id:
                return day
    return -1


def summarize_counts(
    sections: Iterable[CourseSection],
    professors: Iterable[Professor],
    classrooms: Iterable[Classroom],
    timeslots: Iterable[TimeSlot],
) -> None:
    sections_list = list(sections)
    professors_list = list(professors)
    classrooms_list = list(classrooms)
    timeslots_list = list(timeslots)

    print("=== RESUMEN DE TABLAS PRINCIPALES ===")
    print(f"Cursos: {len({sec.course_id for sec in sections_list})}")
    print(f"Secciones activas: {len(sections_list)}")
    print(f"Profesores: {len(professors_list)}")
    print(f"Aulas activas: {len(classrooms_list)}")
    print(f"Franjas horarias activas: {len(timeslots_list)}")

    type_counter = Counter((sec.tipo or "").upper() for sec in sections_list)
    print("Tipos de seccion:")
    for sec_type, count in sorted(type_counter.items()):
        print(f"  {sec_type or 'DESCONOCIDO'}: {count}")

    ciclo_counter = Counter(sec.course.ciclo for sec in sections_list if sec.course and sec.course.ciclo)
    print("Secciones por ciclo:")
    for ciclo, count in sorted(ciclo_counter.items()):
        print(f"  Ciclo {ciclo}: {count}")

    classroom_types = Counter(room.tipo for room in classrooms_list)
    print("Aulas por tipo:")
    for room_type, count in sorted(classroom_types.items()):
        print(f"  {room_type}: {count}")

    slots_by_day = Counter(ts.dia_semana for ts in timeslots_list)
    print("Franjas por dia:")
    for day, count in sorted(slots_by_day.items()):
        print(f"  Dia {day}: {count}")


def load_professor_assignments(db: Session) -> Tuple[
    Dict[Tuple[int, str, int], List[int]],
    Dict[Tuple[int, str], List[int]],
    Dict[int, List[int]],
]:
    assign_by_league: Dict[Tuple[int, str, int], List[int]] = {}
    assign_by_type: Dict[Tuple[int, str], List[int]] = {}
    assign_by_course: Dict[int, List[int]] = {}

    result = db.execute(
        text(
            "SELECT course_id, professor_id, session_type, league "
            "FROM professor_course_assignments"
        )
    )

    for row in result:
        course_id = row.course_id
        professor_id = row.professor_id
        session_type = (row.session_type or "").upper()
        league = row.league or 1

        key_league = (course_id, session_type, league)
        key_type = (course_id, session_type)

        assign_by_league.setdefault(key_league, []).append(professor_id)
        assign_by_type.setdefault(key_type, []).append(professor_id)
        assign_by_course.setdefault(course_id, []).append(professor_id)

    return assign_by_league, assign_by_type, assign_by_course


def map_section_type(section: CourseSection) -> str:
    tipo = (section.tipo or "").upper()
    if tipo.startswith("T"):
        return "T"
    if tipo.startswith("P"):
        return "P"
    if tipo.startswith("L"):
        return "L"
    return "T"


def count_candidate_professors(
    section: CourseSection,
    assign_by_league: Dict[Tuple[int, str, int], List[int]],
    assign_by_type: Dict[Tuple[int, str], List[int]],
    assign_by_course: Dict[int, List[int]],
) -> int:
    ids: Set[int] = set()
    course = section.course
    if course and course.professors:
        ids.update(prof.id for prof in course.professors)

    course_id = section.course_id
    session_type = map_section_type(section)
    league = section.league or 1

    ids.update(assign_by_league.get((course_id, session_type, league), []))
    ids.update(assign_by_type.get((course_id, session_type), []))
    ids.update(assign_by_course.get(course_id, []))

    return len(ids)


def main() -> None:
    db = SessionLocal()
    try:
        sections = load_sections(db)
        professors = load_professors(db)
        classrooms = load_classrooms(db)
        timeslots = load_timeslots(db)
        assign_by_league, assign_by_type, assign_by_course = load_professor_assignments(db)

        summarize_counts(sections, professors, classrooms, timeslots)
        print()

        section_diags, section_alerts, valid_starts = analyze_sections(
            sections,
            classrooms,
            timeslots,
            assign_by_league,
            assign_by_type,
            assign_by_course,
        )
        if section_alerts:
            print("=== ALERTAS DE SECCIONES ===")
            for alert in section_alerts:
                print(f"- {alert}")
            print()

        if valid_starts:
            print("=== BLOQUES CONSECUTIVOS DISPONIBLES ===")
            for duration, count in sorted(valid_starts.items()):
                print(f"Duracion {duration} bloques: {count} inicios posibles")
            print()

        professor_alerts, professor_details = analyze_professor_restrictions(professors, timeslots)
        if professor_alerts or professor_details:
            print("=== ALERTAS DE RESTRICCIONES DE PROFESORES ===")
            for alert in professor_alerts:
                print(f"- {alert}")
            for detail in professor_details:
                print(f"- {detail}")
            print()

        # Mostrar ejemplos problematicos
        print("=== TOP SECCIONES SIN PROFESORES O AULAS ===")
        problematic = [diag for diag in section_diags if diag.candidate_professors == 0 or diag.candidate_classrooms == 0]
        for diag in sorted(problematic, key=lambda d: (d.candidate_professors, d.candidate_classrooms))[:15]:
            print(
                f"Curso {diag.course_code} seccion {diag.section_type}-{diag.section_label}: "
                f"profesores={diag.candidate_professors}, aulas={diag.candidate_classrooms}, "
                f"alumnos={diag.projected_students}, cap_max={diag.max_allowed_capacity}, "
                f"bloques_validos={diag.has_valid_timeslot}"
            )

        if not problematic:
            print("Sin secciones problematicas detectadas.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
