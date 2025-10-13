"""
Endpoints para gestionar restricciones de profesores y asignaciones curso-profesor.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import time
from typing import Dict, Iterable, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, validator
from sqlalchemy import text, bindparam
from sqlalchemy.orm import Session

from ...database import get_db

router = APIRouter(prefix="/api/assignments", tags=["Assignments"])

SECTION_TYPE_MAP: Dict[str, Tuple[str, str]] = {
    "T": ("T", "Teoria"),
    "TEORIA": ("T", "Teoria"),
    "TEORICO": ("T", "Teoria"),
    "TEORICA": ("T", "Teoria"),
    "P": ("P", "Practica"),
    "PRACTICA": ("P", "Practica"),
    "PRACTICO": ("P", "Practica"),
    "LAB": ("L", "Laboratorio"),
    "LABORATORIO": ("L", "Laboratorio"),
    "L": ("L", "Laboratorio"),
}
SESSION_LABELS: Dict[str, str] = {
    "T": "Teoria",
    "P": "Practica",
    "L": "Laboratorio",
}
DEFAULT_SEMESTER = "2025-20"


# ============================================================================
# Pydantic models
# ============================================================================


class ProfessorRestrictionBase(BaseModel):
    professor_id: int
    day: str
    start_time: str
    end_time: str
    duration_blocks: int
    reason: Optional[str] = None

    @validator("day")
    def validate_day(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("day is required")
        return cleaned

    @validator("start_time", "end_time")
    def validate_time(cls, value: str) -> str:
        _parse_time(value)
        return value

    @validator("duration_blocks")
    def validate_duration(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("duration_blocks must be positive")
        return value


class ProfessorRestrictionCreate(ProfessorRestrictionBase):
    pass


class ProfessorRestrictionResponse(ProfessorRestrictionBase):
    id: int
    professor_name: str


class ProfessorCourseAssignmentBase(BaseModel):
    professor_id: int
    session_type: str
    league: Optional[int] = 1

    @validator("session_type")
    def validate_session_type(cls, value: str) -> str:
        resolved = _resolve_session_type(value)
        if not resolved:
            raise ValueError("Invalid session type")
        return resolved[0]

    @validator("league")
    def validate_league(cls, value: Optional[int]) -> int:
        league_value = value or 1
        if league_value <= 0:
            raise ValueError("league must be >= 1")
        return league_value


class ProfessorCourseAssignmentCreate(ProfessorCourseAssignmentBase):
    course_id: int
    semestre: Optional[str] = None


class ProfessorCourseAssignmentResponse(ProfessorCourseAssignmentBase):
    assignment_id: int
    course_id: int
    course_code: str
    course_name: str
    professor_name: str
    semestre: Optional[str]


class CourseAssignmentUpdatePayload(BaseModel):
    assignments: List[ProfessorCourseAssignmentBase] = []
    semestre: Optional[str] = None

    @validator("assignments", each_item=False)
    def ensure_unique_assignments(
        cls, assignments: List[ProfessorCourseAssignmentBase]
    ) -> List[ProfessorCourseAssignmentBase]:
        seen = set()
        for item in assignments:
            key = (item.professor_id, item.session_type, item.league)
            if key in seen:
                raise ValueError("Duplicate assignment for the same professor and slot")
            seen.add(key)
        return assignments


class CourseSessionDetail(BaseModel):
    session_type: str
    label: str
    section_count: int
    sections: List[str]
    section_details: List[Dict[str, Optional[str]]]


class CourseLeagueDetail(BaseModel):
    league: int
    sessions: List[CourseSessionDetail]


class CourseAssignmentSummary(BaseModel):
    assignment_id: int
    course_id: int
    session_type: str
    league: int
    professor_id: int
    professor_name: str
    semestre: Optional[str]


class CourseWithAssignments(BaseModel):
    id: int
    codigo: str
    nombre: str
    ciclo: Optional[int]
    modalidad: Optional[str]
    creditos: Optional[int]
    grupos_teoria: Optional[int]
    grupos_practica: Optional[int]
    grupos_laboratorio: Optional[int]
    alumnos_teoria: Optional[int]
    alumnos_practica: Optional[int]
    alumnos_laboratorio: Optional[int]
    session_types: List[CourseSessionDetail]
    leagues: List[CourseLeagueDetail]
    assignments: List[CourseAssignmentSummary]

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Helper utilities
# ============================================================================


def _parse_time(value: str) -> time:
    try:
        hours, minutes, seconds = value.split(":")
        return time(int(hours), int(minutes), int(seconds))
    except Exception as exc:  # pragma: no cover - defensive guard
        raise ValueError(f"Invalid time format: {value}") from exc


def _resolve_session_type(raw: Optional[str]) -> Optional[Tuple[str, str]]:
    if not raw:
        return None
    key = raw.strip().upper()
    return SECTION_TYPE_MAP.get(key)


def _normalize_sections(
    sections: Iterable[Dict[str, Optional[str]]],
    desired_total: int,
    session_type: str,
    *,
    pad_missing: bool = True,
) -> List[Dict[str, Optional[str]]]:
    normalized: List[Dict[str, Optional[str]]] = []
    used_names: set[str] = set()
    for index, section in enumerate(sections):
        if index >= desired_total:
            break
        entry = {
            "seccion": section.get("seccion"),
            "nrc": section.get("nrc"),
            "league": section.get("league"),
            "placeholder": False,
        }
        proposed_name = (entry["seccion"] or "").strip()
        if not proposed_name or proposed_name in used_names:
            proposed_name = f"{session_type}{len(normalized) + 1}"
        entry["seccion"] = proposed_name
        used_names.add(proposed_name)
        normalized.append(entry)
    if pad_missing:
        while len(normalized) < desired_total:
            next_index = len(normalized) + 1
            normalized.append(
                {
                    "seccion": f"{session_type}{next_index}",
                    "nrc": None,
                    "league": None,
                    "placeholder": True,
                }
            )
    return normalized


def _clone_section_entry(entry: Dict[str, Optional[str]]) -> Dict[str, Optional[str]]:
    return {
        "seccion": entry.get("seccion"),
        "nrc": entry.get("nrc"),
        "placeholder": bool(entry.get("placeholder")),
    }


def _prepare_league_entry(
    entry: Dict[str, Optional[str]],
    session_type: str,
    league_id: int,
) -> Dict[str, Optional[str]]:
    prepared = _clone_section_entry(entry)
    prepared["original_seccion"] = prepared.get("seccion")
    prepared["seccion"] = f"{session_type}{league_id}"
    return prepared


def _round_robin_assignments(
    entries: Iterable[Dict[str, Optional[str]]],
    league_map: Dict[int, Dict[str, List[Dict[str, Optional[str]]]]],
    session_type: str,
) -> None:
    league_ids = sorted(league_map.keys())
    if not league_ids:
        return
    for idx, entry in enumerate(entries):
        league_id = league_ids[idx % len(league_ids)]
        league_map[league_id][session_type].append(
            _prepare_league_entry(entry, session_type, league_id)
        )


def _build_league_payload(
    league_map: Dict[int, Dict[str, List[Dict[str, Optional[str]]]]]
) -> Tuple[List[CourseLeagueDetail], Dict[Tuple[str, int], int]]:
    league_details: List[CourseLeagueDetail] = []
    capacity: Dict[Tuple[str, int], int] = {}

    for league_id in sorted(league_map.keys()):
        sessions: List[CourseSessionDetail] = []
        for session_type in ("T", "P", "L"):
            entries = league_map[league_id][session_type]
            if not entries:
                continue
            sessions.append(
                CourseSessionDetail(
                    session_type=session_type,
                    label=SESSION_LABELS[session_type],
                    section_count=len(entries),
                    sections=[entry.get("seccion") for entry in entries],
                    section_details=[
                        {
                            "seccion": entry.get("seccion"),
                            "nrc": entry.get("nrc"),
                        }
                        for entry in entries
                    ],
                )
            )
            capacity[(session_type, league_id)] = len(entries)
        if sessions:
            league_details.append(CourseLeagueDetail(league=league_id, sessions=sessions))

    return league_details, capacity


def _build_course_layout(
    desired_counts: Dict[str, int],
    sections_by_type: Dict[str, List[Dict[str, Optional[str]]]],
) -> Tuple[List[CourseSessionDetail], List[CourseLeagueDetail], Dict[Tuple[str, int], int]]:
    """Generate normalized session summaries, league breakdown, and capacity."""

    normalized_sections: Dict[str, List[Dict[str, Optional[str]]]] = {}

    for session_type in ("T", "P", "L"):
        desired_total = int(desired_counts.get(session_type, 0) or 0)
        normalized_sections[session_type] = _normalize_sections(
            sections_by_type.get(session_type, []), desired_total, session_type
        )

    session_types_summary: List[CourseSessionDetail] = []
    for session_type in ("T", "P", "L"):
        entries = normalized_sections.get(session_type, [])
        if not entries:
            continue
        session_types_summary.append(
            CourseSessionDetail(
                session_type=session_type,
                label=SESSION_LABELS[session_type],
                section_count=len(entries),
                sections=[entry.get("seccion") for entry in entries],
                section_details=[
                    {
                        "seccion": entry.get("seccion"),
                        "nrc": entry.get("nrc"),
                    }
                    for entry in entries
                ],
            )
        )

    league_details: List[CourseLeagueDetail] = []
    capacity: Dict[Tuple[str, int], int] = {}

    base_type: Optional[str] = next(
        (candidate for candidate in ("T", "P", "L") if normalized_sections.get(candidate)),
        None,
    )

    if not base_type:
        return session_types_summary, league_details, capacity

    base_entries = normalized_sections.get(base_type, [])
    league_count = len(base_entries)
    if league_count == 0:
        return session_types_summary, league_details, capacity

    league_map: Dict[int, Dict[str, List[Dict[str, Optional[str]]]]] = {
        idx + 1: {"T": [], "P": [], "L": []} for idx in range(league_count)
    }

    for idx, entry in enumerate(base_entries):
        league_id = (idx % league_count) + 1
        league_map[league_id][base_type].append(
            _prepare_league_entry(entry, base_type, league_id)
        )

    for session_type in ("T", "P", "L"):
        if session_type == base_type:
            continue
        _round_robin_assignments(normalized_sections.get(session_type, []), league_map, session_type)

    league_details, capacity = _build_league_payload(league_map)
    return session_types_summary, league_details, capacity


def _build_capacity_by_league(
    db: Session,
    course_id: int,
) -> Dict[Tuple[str, int], int]:
    """Compute available professor slots per (session_type, league)."""

    course_row = db.execute(
        text(
            """
            SELECT grupos_teoria, grupos_practica, grupos_laboratorio
            FROM courses
            WHERE id = :course_id
            """
        ),
        {"course_id": course_id},
    ).first()
    if not course_row:
        return {}

    desired_counts = {
        "T": int(course_row[0] or 0),
        "P": int(course_row[1] or 0),
        "L": int(course_row[2] or 0),
    }

    sections_query = text(
        """
        SELECT tipo, seccion, league, nrc
        FROM course_sections
        WHERE course_id = :course_id AND activa = 1
        ORDER BY id
        """
    )
    sections_result = db.execute(sections_query, {"course_id": course_id})
    sections_by_type: Dict[str, List[Dict[str, Optional[str]]]] = defaultdict(list)
    for raw_type, seccion, league, nrc in sections_result:
        resolved = _resolve_session_type(raw_type)
        if not resolved:
            continue
        session_type = resolved[0]
        sections_by_type[session_type].append(
            {"seccion": seccion, "nrc": nrc, "league": league}
        )

    _session_summary, _league_details, capacity = _build_course_layout(desired_counts, sections_by_type)
    return capacity


def _synchronize_assignments_with_sections(
    db: Session, course_id: int
) -> Tuple[Dict[Tuple[str, int], int], bool]:
    """Remove assignments that no longer match active sections."""

    capacity = _build_capacity_by_league(db, course_id)
    assignments_query = text(
        """
        SELECT id, session_type, COALESCE(league, 1) AS league
        FROM professor_course_assignments
        WHERE course_id = :course_id
        ORDER BY session_type, league, id
        """
    )
    rows = list(db.execute(assignments_query, {"course_id": course_id}))
    if not rows:
        return capacity, False

    ids_to_delete: List[int] = []
    if not capacity:
        ids_to_delete = [row[0] for row in rows]
    else:
        usage: Dict[Tuple[str, int], List[int]] = defaultdict(list)
        for assignment_id, session_type, league in rows:
            key = (session_type, int(league or 1))
            if key not in capacity:
                ids_to_delete.append(assignment_id)
                continue
            usage[key].append(assignment_id)

        for key, assignment_ids in usage.items():
            allowed = capacity.get(key, 0)
            if allowed <= 0:
                ids_to_delete.extend(assignment_ids)
                continue
            if len(assignment_ids) > allowed:
                ids_to_delete.extend(assignment_ids[allowed:])

    if ids_to_delete:
        delete_query = (
            text("DELETE FROM professor_course_assignments WHERE id IN :ids")
            .bindparams(bindparam("ids", expanding=True))
        )
        db.execute(delete_query, {"ids": ids_to_delete})
        return capacity, True

    return capacity, False


def _validate_assignment_capacity(
    assignments: Iterable[ProfessorCourseAssignmentBase],
    capacity: Dict[Tuple[str, int], int],
) -> None:
    """Ensure assignments respect the per-league capacity derived from NRC counts."""

    if not capacity:
        raise HTTPException(
            status_code=400,
            detail="El curso no tiene secciones activas; no se pueden registrar asignaciones.",
        )

    usage: Dict[Tuple[str, int], int] = defaultdict(int)
    for item in assignments:
        league_id = int(item.league or 1)
        key = (item.session_type, league_id)
        max_slots = capacity.get(key)
        if not max_slots:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"No existe una sección activa para el tipo '{item.session_type}' en la liga {league_id}."
                ),
            )
        usage[key] += 1
        if usage[key] > max_slots:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Se excedió el número máximo de profesores permitidos: "
                    f"tipo '{item.session_type}', liga {league_id} admite {max_slots} NRC."
                ),
            )

# ============================================================================
# Restricciones de profesores
# ============================================================================


@router.get("/restrictions", response_model=List[ProfessorRestrictionResponse])
async def get_all_restrictions(db: Session = Depends(get_db)) -> List[ProfessorRestrictionResponse]:
    query = text(
        """
        SELECT 
            r.id,
            r.professor_id,
            p.nombre_completo,
            r.day,
            DATE_FORMAT(r.start_time, '%H:%i:%s'),
            DATE_FORMAT(r.end_time, '%H:%i:%s'),
            r.duration_blocks,
            r.reason
        FROM professor_restrictions r
        JOIN professors p ON r.professor_id = p.id
        ORDER BY p.nombre_completo, r.day, r.start_time
        """
    )
    result = db.execute(query)
    restrictions: List[ProfessorRestrictionResponse] = []
    for row in result:
        restrictions.append(
            ProfessorRestrictionResponse(
                id=row[0],
                professor_id=row[1],
                professor_name=row[2],
                day=row[3],
                start_time=row[4],
                end_time=row[5],
                duration_blocks=row[6],
                reason=row[7],
            )
        )
    return restrictions


@router.get("/restrictions/professor/{professor_id}", response_model=List[ProfessorRestrictionResponse])
async def get_professor_restrictions(
    professor_id: int, db: Session = Depends(get_db)
) -> List[ProfessorRestrictionResponse]:
    query = text(
        """
        SELECT 
            r.id,
            r.professor_id,
            p.nombre_completo,
            r.day,
            DATE_FORMAT(r.start_time, '%H:%i:%s'),
            DATE_FORMAT(r.end_time, '%H:%i:%s'),
            r.duration_blocks,
            r.reason
        FROM professor_restrictions r
        JOIN professors p ON r.professor_id = p.id
        WHERE r.professor_id = :professor_id
        ORDER BY r.day, r.start_time
        """
    )
    result = db.execute(query, {"professor_id": professor_id})
    restrictions: List[ProfessorRestrictionResponse] = []
    for row in result:
        restrictions.append(
            ProfessorRestrictionResponse(
                id=row[0],
                professor_id=row[1],
                professor_name=row[2],
                day=row[3],
                start_time=row[4],
                end_time=row[5],
                duration_blocks=row[6],
                reason=row[7],
            )
        )
    return restrictions


@router.post("/restrictions")
async def create_restriction(
    restriction: ProfessorRestrictionCreate, db: Session = Depends(get_db)
) -> Dict[str, str]:
    insert_query = text(
        """
        INSERT INTO professor_restrictions
            (professor_id, day, start_time, end_time, duration_blocks, reason)
        VALUES
            (:professor_id, :day, :start_time, :end_time, :duration_blocks, :reason)
        """
    )
    payload = restriction.dict()
    try:
        db.execute(insert_query, payload)
        db.commit()
    except Exception as exc:  # pragma: no cover - DB guard
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"message": "Restriccion creada", "success": True}


@router.delete("/restrictions/{restriction_id}")
async def delete_restriction(restriction_id: int, db: Session = Depends(get_db)) -> Dict[str, str]:
    delete_query = text("DELETE FROM professor_restrictions WHERE id = :id")
    try:
        result = db.execute(delete_query, {"id": restriction_id})
        db.commit()
    except Exception as exc:  # pragma: no cover
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Restriction not found")
    return {"message": "Restriccion eliminada", "success": True}


@router.delete("/restrictions/all")
async def delete_all_restrictions(db: Session = Depends(get_db)) -> Dict[str, str]:
    query = text("DELETE FROM professor_restrictions")
    db.execute(query)
    db.commit()
    return {"message": "Todas las restricciones fueron eliminadas", "success": True}


@router.post("/restrictions/bulk")
async def create_restrictions_bulk(
    restrictions: List[ProfessorRestrictionCreate], db: Session = Depends(get_db)
) -> Dict[str, int]:
    if not restrictions:
        return {"inserted": 0}
    insert_query = text(
        """
        INSERT INTO professor_restrictions
            (professor_id, day, start_time, end_time, duration_blocks, reason)
        VALUES
            (:professor_id, :day, :start_time, :end_time, :duration_blocks, :reason)
        """
    )
    payloads = [item.dict() for item in restrictions]
    try:
        db.execute_many(insert_query, payloads)  # type: ignore[attr-defined]
        db.commit()
    except AttributeError:
        for payload in payloads:
            db.execute(insert_query, payload)
        db.commit()
    except Exception as exc:  # pragma: no cover
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"inserted": len(payloads)}


@router.put("/restrictions/professor/{professor_id}")
async def replace_professor_restrictions(
    professor_id: int,
    restrictions: List[ProfessorRestrictionCreate],
    db: Session = Depends(get_db),
) -> Dict[str, object]:
    db.execute(text("DELETE FROM professor_restrictions WHERE professor_id = :id"), {"id": professor_id})
    if restrictions:
        insert_query = text(
            """
            INSERT INTO professor_restrictions
                (professor_id, day, start_time, end_time, duration_blocks, reason)
            VALUES
                (:professor_id, :day, :start_time, :end_time, :duration_blocks, :reason)
            """
        )
        for item in restrictions:
            payload = item.dict()
            payload["professor_id"] = professor_id
            db.execute(insert_query, payload)
    db.commit()
    return {"message": "Restricciones actualizadas", "count": len(restrictions)}


@router.get("/restrictions/summary")
async def restriction_summary(db: Session = Depends(get_db)) -> List[Dict[str, object]]:
    query = text(
        """
        SELECT p.id, p.nombre_completo, p.codigo, COUNT(r.id) AS restriction_count
        FROM professors p
        LEFT JOIN professor_restrictions r ON r.professor_id = p.id
        GROUP BY p.id, p.nombre_completo, p.codigo
        ORDER BY p.nombre_completo
        """
    )
    result = db.execute(query)
    summary: List[Dict[str, object]] = []
    for row in result:
        summary.append(
            {
                "professor_id": row[0],
                "professor_name": row[1],
                "professor_code": row[2],
                "restrictions": row[3],
            }
        )
    return summary


# ============================================================================
# Asignaciones curso-profesor
# ============================================================================


@router.get("/professor-courses", response_model=List[ProfessorCourseAssignmentResponse])
async def get_all_assignments(db: Session = Depends(get_db)) -> List[ProfessorCourseAssignmentResponse]:
    query = text(
        """
        SELECT 
            pca.id,
            pca.professor_id,
            p.nombre_completo,
            pca.course_id,
            c.codigo,
            c.nombre,
            pca.session_type,
            pca.league,
            pca.semestre
        FROM professor_course_assignments pca
        JOIN professors p ON pca.professor_id = p.id
        JOIN courses c ON pca.course_id = c.id
        ORDER BY c.codigo, pca.league, pca.session_type, p.nombre_completo
        """
    )
    result = db.execute(query)
    assignments: List[ProfessorCourseAssignmentResponse] = []
    for row in result:
        assignments.append(
            ProfessorCourseAssignmentResponse(
                assignment_id=row[0],
                professor_id=row[1],
                professor_name=row[2],
                course_id=row[3],
                course_code=row[4],
                course_name=row[5],
                session_type=row[6],
                league=row[7],
                semestre=row[8],
            )
        )
    return assignments


@router.get("/courses-with-assignments", response_model=List[CourseWithAssignments])
async def get_courses_with_assignments(db: Session = Depends(get_db)) -> List[CourseWithAssignments]:
    courses_query = text(
        """
        SELECT 
            id,
            codigo,
            nombre,
            ciclo,
            modalidad,
            creditos,
            grupos_teoria,
            grupos_practica,
            grupos_laboratorio,
            alumnos_teoria,
            alumnos_practica,
            alumnos_laboratorio
        FROM courses
        WHERE active = 1
        ORDER BY codigo
        """
    )
    course_rows = list(db.execute(courses_query))
    any_cleansed = False
    for course_row in course_rows:
        course_id = course_row[0]
        _capacity, cleaned = _synchronize_assignments_with_sections(db, course_id)
        if cleaned:
            any_cleansed = True
    if any_cleansed:
        db.commit()

    sections_query = text(
        """
        SELECT course_id, tipo, seccion, COALESCE(league, 1) AS league, nrc
        FROM course_sections
        WHERE activa = 1
        ORDER BY course_id, tipo, seccion, id
        """
    )
    assignments_query = text(
        """
        SELECT 
            pca.id,
            pca.course_id,
            pca.session_type,
            pca.league,
            pca.professor_id,
            p.nombre_completo,
            pca.semestre
        FROM professor_course_assignments pca
        JOIN professors p ON pca.professor_id = p.id
        ORDER BY pca.course_id, pca.league, pca.session_type, p.nombre_completo
        """
    )

    sections_result = db.execute(sections_query)
    sections_by_course: Dict[int, Dict[str, List[Dict[str, Optional[str]]]]] = defaultdict(lambda: defaultdict(list))

    for course_id, raw_type, seccion, league, nrc in sections_result:
        resolved = _resolve_session_type(raw_type)
        if not resolved:
            continue
        session_type = resolved[0]
        section_entry = {"seccion": seccion, "nrc": nrc, "league": league}
        sections_by_course[course_id][session_type].append(section_entry)

    assignments_result = db.execute(assignments_query)
    assignments_by_course: Dict[int, List[CourseAssignmentSummary]] = defaultdict(list)
    for row in assignments_result:
        assignments_by_course[row[1]].append(
            CourseAssignmentSummary(
                assignment_id=row[0],
                course_id=row[1],
                session_type=row[2],
                league=row[3],
                professor_id=row[4],
                professor_name=row[5],
                semestre=row[6],
            )
        )

    courses_payload: List[CourseWithAssignments] = []

    for course_row in course_rows:
        (
            course_id,
            codigo,
            nombre,
            ciclo,
            modalidad,
            creditos,
            grupos_teoria,
            grupos_practica,
            grupos_laboratorio,
            alumnos_teoria,
            alumnos_practica,
            alumnos_laboratorio,
        ) = course_row

        desired_counts = {
            "T": int(grupos_teoria or 0),
            "P": int(grupos_practica or 0),
            "L": int(grupos_laboratorio or 0),
        }

        course_sections = sections_by_course.get(course_id, {})
        session_types_summary, league_details, _ = _build_course_layout(desired_counts, course_sections)

        course_payload = CourseWithAssignments(
            id=course_id,
            codigo=codigo,
            nombre=nombre,
            ciclo=ciclo,
            modalidad=modalidad,
            creditos=creditos,
            grupos_teoria=grupos_teoria,
            grupos_practica=grupos_practica,
            grupos_laboratorio=grupos_laboratorio,
            alumnos_teoria=alumnos_teoria,
            alumnos_practica=alumnos_practica,
            alumnos_laboratorio=alumnos_laboratorio,
            session_types=session_types_summary,
            leagues=league_details,
            assignments=assignments_by_course.get(course_id, []),
        )
        courses_payload.append(course_payload)

    return courses_payload


@router.post("/professor-courses", response_model=ProfessorCourseAssignmentResponse)
async def create_assignment(
    assignment: ProfessorCourseAssignmentCreate, db: Session = Depends(get_db)
) -> ProfessorCourseAssignmentResponse:
    capacity, _ = _synchronize_assignments_with_sections(db, assignment.course_id)
    if not capacity:
        raise HTTPException(
            status_code=400,
            detail="El curso no tiene secciones activas; no se pueden registrar asignaciones.",
        )

    usage_query = text(
        """
        SELECT session_type, COALESCE(league, 1)
        FROM professor_course_assignments
        WHERE course_id = :course_id
        """
    )
    usage: Dict[Tuple[str, int], int] = defaultdict(int)
    for session_type, league in db.execute(usage_query, {"course_id": assignment.course_id}):
        usage[(session_type, int(league or 1))] += 1

    key = (assignment.session_type, int(assignment.league or 1))
    max_slots = capacity.get(key)
    if not max_slots:
        raise HTTPException(
            status_code=400,
            detail=(
                f"No existe una sección activa para el tipo '{assignment.session_type}' en la liga {key[1]}."
            ),
        )
    if usage.get(key, 0) >= max_slots:
        raise HTTPException(
            status_code=400,
            detail=(
                "Se excedió el número máximo de profesores permitidos: "
                f"tipo '{assignment.session_type}', liga {key[1]} admite {max_slots} NRC."
            ),
        )

    insert_query = text(
        """
        INSERT INTO professor_course_assignments
            (professor_id, course_id, session_type, league, semestre)
        VALUES
            (:professor_id, :course_id, :session_type, :league, :semestre)
        """
    )
    values = {
        "professor_id": assignment.professor_id,
        "course_id": assignment.course_id,
        "session_type": assignment.session_type,
        "league": assignment.league or 1,
        "semestre": assignment.semestre or DEFAULT_SEMESTER,
    }
    try:
        result = db.execute(insert_query, values)
        assignment_id = result.lastrowid  # type: ignore[attr-defined]
        db.commit()
    except Exception as exc:  # pragma: no cover
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    select_query = text(
        """
        SELECT 
            pca.id,
            pca.professor_id,
            p.nombre_completo,
            pca.course_id,
            c.codigo,
            c.nombre,
            pca.session_type,
            pca.league,
            pca.semestre
        FROM professor_course_assignments pca
        JOIN professors p ON pca.professor_id = p.id
        JOIN courses c ON pca.course_id = c.id
        WHERE pca.id = :id
        """
    )
    row = db.execute(select_query, {"id": assignment_id}).first()
    if not row:
        raise HTTPException(status_code=404, detail="Assignment not found after insert")
    return ProfessorCourseAssignmentResponse(
        assignment_id=row[0],
        professor_id=row[1],
        professor_name=row[2],
        course_id=row[3],
        course_code=row[4],
        course_name=row[5],
        session_type=row[6],
        league=row[7],
        semestre=row[8],
    )


@router.put("/professor-courses/course/{course_id}")
async def update_course_assignments(
    course_id: int,
    payload: CourseAssignmentUpdatePayload,
    db: Session = Depends(get_db),
) -> Dict[str, object]:
    course_exists = db.execute(text("SELECT 1 FROM courses WHERE id = :id"), {"id": course_id}).first()
    if not course_exists:
        raise HTTPException(status_code=404, detail="Course not found")

    capacity, _ = _synchronize_assignments_with_sections(db, course_id)
    _validate_assignment_capacity(payload.assignments, capacity)

    delete_query = text("DELETE FROM professor_course_assignments WHERE course_id = :course_id")
    db.execute(delete_query, {"course_id": course_id})

    if payload.assignments:
        insert_query = text(
            """
            INSERT INTO professor_course_assignments
                (professor_id, course_id, session_type, league, semestre)
            VALUES
                (:professor_id, :course_id, :session_type, :league, :semestre)
            """
        )
        semestre_value = payload.semestre or DEFAULT_SEMESTER
        for item in payload.assignments:
            values = {
                "professor_id": item.professor_id,
                "course_id": course_id,
                "session_type": item.session_type,
                "league": item.league or 1,
                "semestre": semestre_value,
            }
            db.execute(insert_query, values)

    db.commit()
    return {
        "message": "Asignaciones actualizadas",
        "course_id": course_id,
        "count": len(payload.assignments),
    }


@router.delete("/professor-courses/{assignment_id}")
async def delete_assignment(assignment_id: int, db: Session = Depends(get_db)) -> Dict[str, str]:
    delete_query = text("DELETE FROM professor_course_assignments WHERE id = :id")
    result = db.execute(delete_query, {"id": assignment_id})
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return {"message": "Asignacion eliminada", "success": True}


# ============================================================================
# Apoyos para frontend (profesores y bloques horarios)
# ============================================================================


@router.get("/professors")
async def get_professors(db: Session = Depends(get_db)) -> Dict[str, List[Dict[str, Optional[str]]]]:
    query = text(
        """
        SELECT id, nombre_completo, email, especialidad, codigo
        FROM professors
        WHERE nombre_completo IS NOT NULL
        ORDER BY nombre_completo
        """
    )
    result = db.execute(query)
    professors: List[Dict[str, Optional[str]]] = []
    for row in result:
        professors.append(
            {
                "id": row[0],
                "nombre_completo": row[1],
                "email": row[2],
                "especialidad": row[3],
                "codigo": row[4],
            }
        )
    return {"professors": professors}


@router.get("/time-blocks")
async def get_time_blocks(db: Session = Depends(get_db)) -> List[Dict[str, object]]:
    query = text(
        """
        SELECT id, dia_semana, DATE_FORMAT(hora_inicio, '%H:%i:%s'), DATE_FORMAT(hora_fin, '%H:%i:%s'), periodo, orden
        FROM time_slots
        WHERE activo = 1
        ORDER BY dia_semana, orden
        """
    )
    result = db.execute(query)
    blocks: List[Dict[str, object]] = []
    for row in result:
        blocks.append(
            {
                "id": row[0],
                "day": row[1],
                "start": row[2],
                "end": row[3],
                "period": row[4],
                "order": row[5],
                "label": f"{row[1]} {row[2]}-{row[3]}",
            }
        )
    return blocks
