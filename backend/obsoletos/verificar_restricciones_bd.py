"""Pruebas rápidas de validación sobre datos reales en MySQL.

Se valida un subconjunto de restricciones duras y blandas utilizando
HardConstraintValidator y SoftConstraintEvaluator directamente contra la BD.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, time
from typing import Dict, List, Tuple

from sqlalchemy.orm import joinedload

from app.database import SessionLocal
from app.models import (
    Course,
    CourseSection,
    Classroom,
    ProfessorRestriction,
    TimeSlot,
)
from app.aco_graphsage.constraints import (
    Assignment,
    ClassroomInfo,
    HardConstraintValidator,
    ProfessorRestrictionInfo,
    SoftConstraintEvaluator,
    TimeSlotInfo,
)


# -------------------------------------------------------------
# Utilidades de normalización (replican lógica del GraphBuilder)
# -------------------------------------------------------------

def normalize_session_type(raw: str) -> str:
    value = (raw or "").strip().lower()
    if value in {"t", "teoria", "teoría", "theory"}:
        return "T"
    if value in {"p", "practica", "práctica", "practice"}:
        return "P"
    if value in {"l", "lab", "laboratorio", "laboratory"}:
        return "L"
    if value in {"v", "virtual"}:
        return "V"
    return "T"


def normalize_classroom_type(raw: str) -> str:
    value = (raw or "").strip().lower()
    if value in {"lab", "laboratorio", "laboratory"}:
        return "laboratorio"
    if value in {"practica", "práctica", "practice"}:
        return "practica"
    return "teorica"


def normalize_day(raw) -> int:
    if raw is None:
        return 0
    if isinstance(raw, int):
        return raw
    mapping = {
        "monday": 1,
        "lunes": 1,
        "lun": 1,
        "tuesday": 2,
        "martes": 2,
        "mar": 2,
        "wednesday": 3,
        "miercoles": 3,
        "miércoles": 3,
        "mie": 3,
        "thursday": 4,
        "jueves": 4,
        "jue": 4,
        "friday": 5,
        "viernes": 5,
        "vie": 5,
        "saturday": 6,
        "sabado": 6,
        "sábado": 6,
        "sab": 6,
    }
    return mapping.get(str(raw).lower().strip(), 0)


def ensure_time(value) -> time:
    if value is None:
        return time(0, 0)
    if isinstance(value, time):
        return value
    if isinstance(value, str):
        return datetime.strptime(value, "%H:%M").time()
    if hasattr(value, "hour") and hasattr(value, "minute"):
        return time(int(value.hour) % 24, int(value.minute) % 60)
    if hasattr(value, "total_seconds"):
        total = int(value.total_seconds())
        hours, remainder = divmod(total, 3600)
        minutes = (remainder // 60) % 60
        return time(hours % 24, minutes)
    raise ValueError(f"No se puede convertir {value!r} a time")


def cargar_datos():
    session = SessionLocal()
    session.bind.echo = False

    sections = (
        session.query(CourseSection)
        .options(joinedload(CourseSection.course))
        .filter(CourseSection.activa == True)
        .all()
    )

    section_metadata: Dict[int, Dict[str, object]] = {}
    sections_by_league: Dict[Tuple[str, int], List[int]] = defaultdict(list)
    league_session_types: Dict[Tuple[str, int], set[str]] = defaultdict(set)
    section_session_types: Dict[int, str] = {}
    sections_by_course_type: Dict[Tuple[str, str], List[int]] = defaultdict(list)

    for section in sections:
        course: Course | None = section.course
        course_code = course.codigo if course else f"SEC-{section.id}"
        league = section.league or 1
        session_type = normalize_session_type(section.tipo)
        ciclo = course.ciclo if course else "SIN-CICLO"
        alumnos = section.alumnos_proyectados or 0

        section_metadata[section.id] = {
            "course_code": course_code,
            "league": league,
            "session_type": session_type,
            "ciclo": ciclo,
            "alumnos": alumnos,
        }

        sections_by_league[(course_code, league)].append(section.id)
        league_session_types[(course_code, league)].add(session_type)
        section_session_types[section.id] = session_type
        sections_by_course_type[(course_code, session_type)].append(section.id)

    timeslots = {
        ts.id: TimeSlotInfo(
            id=ts.id,
            dia_semana=ts.dia_semana,
            hora_inicio=ensure_time(ts.hora_inicio),
            hora_fin=ensure_time(ts.hora_fin),
            orden=ts.orden,
            periodo=ts.periodo,
        )
        for ts in session.query(TimeSlot).all()
    }

    classrooms = {
        c.id: ClassroomInfo(
            id=c.id,
            codigo=c.codigo,
            capacidad=c.capacidad,
            tipo=normalize_classroom_type(c.tipo),
            edificio=(c.edificio or "").strip().upper(),
            tiene_computadoras=bool(c.tiene_computadoras),
        )
        for c in session.query(Classroom).all()
    }

    professor_restrictions = defaultdict(list)
    for r in session.query(ProfessorRestriction).all():
        day = normalize_day(r.day)
        if day == 0:
            continue
        start = ensure_time(r.start_time)
        end = ensure_time(r.end_time)
        professor_restrictions[r.professor_id].append(
            ProfessorRestrictionInfo(
                professor_id=r.professor_id,
                dia_semana=day,
                hora_inicio=start,
                hora_fin=end,
            )
        )

    session.close()

    hard_validator = HardConstraintValidator(
        timeslots=timeslots,
        classrooms=classrooms,
        professor_restrictions=dict(professor_restrictions),
        sections_by_league=dict(sections_by_league),
        league_session_types=dict(league_session_types),
        section_session_types=section_session_types,
    )

    soft_validator = SoftConstraintEvaluator(
        timeslots=timeslots,
        classrooms=classrooms,
    )

    referencia = {
        "sections": sections,
        "section_metadata": section_metadata,
        "sections_by_course_type": sections_by_course_type,
    }

    return hard_validator, soft_validator, referencia


def crear_assignment(section_id: int, professor_id: int, classroom_id: int, timeslot_ids: List[int], metadata: Dict[str, object], alumnos_override: int | None = None) -> Assignment:
    return Assignment(
        section_id=section_id,
        professor_id=professor_id,
        classroom_id=classroom_id,
        timeslot_ids=timeslot_ids,
        course_code=metadata["course_code"],
        session_type=metadata["session_type"],
        league_id=metadata["league"],
        ciclo=metadata["ciclo"],
        alumnos_proyectados=alumnos_override if alumnos_override is not None else int(metadata["alumnos"]),
    )


@dataclass
class ResultadoPrueba:
    nombre: str
    exitoso: bool
    detalle: str


def probar_profesor_solapado(hard_validator: HardConstraintValidator, datos: Dict[str, object]) -> ResultadoPrueba:
    sections: List[CourseSection] = datos["sections"]
    metadata = datos["section_metadata"]
    timeslot_id = next(iter(hard_validator.timeslots.keys()))
    classroom_id = next(iter(hard_validator.classrooms.keys()))
    professor_id = next(iter(hard_validator.professor_restrictions.keys()), 1)

    base_section = sections[0]
    other_section = sections[1]

    asignacion_existente = crear_assignment(
        base_section.id,
        professor_id,
        classroom_id,
        [timeslot_id],
        metadata[base_section.id],
    )

    nueva_asignacion = crear_assignment(
        other_section.id,
        professor_id,
        classroom_id,
        [timeslot_id],
        metadata[other_section.id],
    )

    valido, mensaje = hard_validator.validate_all(nueva_asignacion, [asignacion_existente])
    return ResultadoPrueba(
        nombre="Conflicto de profesor",
        exitoso=not valido,
        detalle=mensaje or "",
    )


def probar_disponibilidad_profesor(hard_validator: HardConstraintValidator, datos: Dict[str, object]) -> ResultadoPrueba:
    if not hard_validator.professor_restrictions:
        return ResultadoPrueba("Disponibilidad profesor", False, "No hay restricciones registradas")

    prof_id, restricciones = next(iter(hard_validator.professor_restrictions.items()))
    restriccion = restricciones[0]

    timeslot_id = None
    for ts_id, ts in hard_validator.timeslots.items():
        if ts.dia_semana != restriccion.dia_semana:
            continue
        if ts.hora_inicio < restriccion.hora_fin and restriccion.hora_inicio < ts.hora_fin:
            timeslot_id = ts_id
            break

    if timeslot_id is None:
        return ResultadoPrueba("Disponibilidad profesor", False, "No se encontró franja que solape la restricción")

    classroom_id = next(iter(hard_validator.classrooms.keys()))
    section = datos["sections"][0]
    metadata = datos["section_metadata"][section.id]

    assignment = crear_assignment(section.id, prof_id, classroom_id, [timeslot_id], metadata)
    valido, mensaje = hard_validator.validate_all(assignment, [])
    return ResultadoPrueba(
        nombre="Disponibilidad profesor",
        exitoso=not valido,
        detalle=mensaje or "",
    )


def probar_capacidad_aula(hard_validator: HardConstraintValidator, datos: Dict[str, object]) -> ResultadoPrueba:
    classroom_id, info = next(iter(hard_validator.classrooms.items()))
    section = datos["sections"][0]
    metadata = datos["section_metadata"][section.id]

    alumnos = info.capacidad + 5
    assignment = crear_assignment(section.id, 9999, classroom_id, [next(iter(hard_validator.timeslots.keys()))], metadata, alumnos_override=alumnos)
    valido, mensaje = hard_validator.validate_all(assignment, [])
    return ResultadoPrueba(
        nombre="Capacidad de aula",
        exitoso=not valido,
        detalle=mensaje or "",
    )


def probar_laboratorio_edificio(hard_validator: HardConstraintValidator, datos: Dict[str, object]) -> ResultadoPrueba:
    sections_by_course_type: Dict[Tuple[str, str], List[int]] = datos["sections_by_course_type"]
    metadata = datos["section_metadata"]

    lab_section_id = None
    teoria_section_id = None
    practica_section_id = None
    for (course_code, tipo), ids in sections_by_course_type.items():
        if tipo == "L" and ids:
            lab_section_id = ids[0]
            league = metadata[lab_section_id]["league"]
            # Buscar teoría y práctica de la misma liga si existen
            for sid in sections_by_course_type.get((course_code, "T"), []):
                if metadata[sid]["league"] == league:
                    teoria_section_id = sid
                    break
            for sid in sections_by_course_type.get((course_code, "P"), []):
                if metadata[sid]["league"] == league:
                    practica_section_id = sid
                    break
            break

    if lab_section_id is None:
        return ResultadoPrueba("Laboratorio edificio", False, "No hay secciones de laboratorio en la BD")

    lab_metadata = metadata[lab_section_id]
    alumnos = int(lab_metadata["alumnos"])

    # Determinar edificio incorrecto
    expected = "F" if alumnos <= 20 else "G"
    wrong_building = "G" if expected == "F" else "F"

    classroom_id = None
    for cid, info in hard_validator.classrooms.items():
        if info.tipo == "laboratorio" and (info.edificio or "").upper() == wrong_building:
            classroom_id = cid
            break

    if classroom_id is None:
        return ResultadoPrueba("Laboratorio edificio", False, f"No hay laboratorio en edificio {wrong_building}")

    timeslots = list(hard_validator.timeslots.keys())
    if len(timeslots) < 3:
        return ResultadoPrueba("Laboratorio edificio", False, "No hay suficientes franjas para simular la liga completa")

    current_schedule: List[Assignment] = []
    profesor_base = 7777
    classroom_base = next(iter(hard_validator.classrooms.keys()))

    if teoria_section_id is not None:
        current_schedule.append(
            crear_assignment(
                teoria_section_id,
                profesor_base,
                classroom_base,
                [timeslots[0]],
                metadata[teoria_section_id],
            )
        )

    if practica_section_id is not None:
        current_schedule.append(
            crear_assignment(
                practica_section_id,
                profesor_base,
                classroom_base,
                [timeslots[1]],
                metadata[practica_section_id],
            )
        )

    assignment = crear_assignment(lab_section_id, profesor_base, classroom_id, [timeslots[2]], lab_metadata)
    valido, mensaje = hard_validator.validate_all(assignment, current_schedule)
    return ResultadoPrueba(
        nombre="Laboratorio edificio",
        exitoso=not valido,
        detalle=mensaje or "",
    )


def probar_orden_pedagogico(hard_validator: HardConstraintValidator, datos: Dict[str, object]) -> ResultadoPrueba:
    sections_by_course_type: Dict[Tuple[str, str], List[int]] = datos["sections_by_course_type"]
    metadata = datos["section_metadata"]

    curso_elegido = None
    for (course_code, tipo), ids in sections_by_course_type.items():
        if tipo == "T" and ids:
            league_ids = {metadata[sid]["league"] for sid in ids}
            for league in league_ids:
                key_prac = (course_code, "P")
                key_lab = (course_code, "L")
                if key_prac in sections_by_course_type and sections_by_course_type[key_prac]:
                    curso_elegido = (course_code, league)
                    break
            if curso_elegido:
                break

    if not curso_elegido:
        return ResultadoPrueba("Orden pedagógico", False, "No hay curso con T y P para probar")

    course_code, league = curso_elegido
    seccion_teoria = next(sid for sid in sections_by_course_type[(course_code, "T")] if metadata[sid]["league"] == league)
    seccion_practica = next(sid for sid in sections_by_course_type[(course_code, "P")] if metadata[sid]["league"] == league)

    timeslots = list(hard_validator.timeslots.keys())
    if len(timeslots) < 2:
        return ResultadoPrueba("Orden pedagógico", False, "No hay suficientes franjas para la prueba")

    profesor_id = 8000
    classroom_id = next(iter(hard_validator.classrooms.keys()))

    teoria = crear_assignment(seccion_teoria, profesor_id, classroom_id, [timeslots[1]], metadata[seccion_teoria])
    practica_antes = crear_assignment(seccion_practica, profesor_id, classroom_id, [timeslots[0]], metadata[seccion_practica])

    valido, mensaje = hard_validator.validate_all(practica_antes, [teoria])
    return ResultadoPrueba(
        nombre="Secuencia T->P",
        exitoso=not valido,
        detalle=mensaje or "",
    )


def evaluar_blandas(soft_validator: SoftConstraintEvaluator, datos: Dict[str, object], hard_validator: HardConstraintValidator) -> Dict[str, float]:
    metadata = datos["section_metadata"]
    timeslots = list(hard_validator.timeslots.keys())
    classrooms = list(hard_validator.classrooms.keys())

    if len(timeslots) < 4 or len(classrooms) < 2:
        return {}

    assignments = [
        crear_assignment(datos["sections"][0].id, 1, classrooms[0], [timeslots[0]], metadata[datos["sections"][0].id]),
        crear_assignment(datos["sections"][1].id, 2, classrooms[1], [timeslots[2]], metadata[datos["sections"][1].id]),
    ]

    total, breakdown = soft_validator.calculate_total_penalty(assignments)
    breakdown["total_ponderado"] = total
    return breakdown


def main():
    hard_validator, soft_validator, datos = cargar_datos()

    pruebas = [
        probar_profesor_solapado,
        probar_disponibilidad_profesor,
        probar_capacidad_aula,
        probar_laboratorio_edificio,
        probar_orden_pedagogico,
    ]

    resultados: List[ResultadoPrueba] = []
    for prueba in pruebas:
        try:
            resultados.append(prueba(hard_validator, datos))
        except Exception as exc:
            resultados.append(ResultadoPrueba(prueba.__name__, False, f"Error al ejecutar: {exc}"))

    print("PRUEBAS DE RESTRICCIONES DURAS")
    for r in resultados:
        estado = "OK" if r.exitoso else "FALLA"
        print(f"- {estado:6} | {r.nombre}: {r.detalle}")

    print()
    print("EVALUACIÓN RÁPIDA DE RESTRICCIONES BLANDAS")
    blandas = evaluar_blandas(soft_validator, datos, hard_validator)
    if not blandas:
        print("(No se pudo construir un ejemplo de penalización)")
    else:
        for clave, valor in blandas.items():
            print(f"- {clave}: {valor:.2f}")


if __name__ == "__main__":
    main()
