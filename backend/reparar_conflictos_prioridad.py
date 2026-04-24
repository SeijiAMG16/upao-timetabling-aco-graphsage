from __future__ import annotations

import argparse
import json
import random
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from sqlalchemy import text

from app.database import SessionLocal
from app.aco_graphsage.aco_engine import create_aco_engine
from app.aco_graphsage.constraints import Assignment
from app.aco_graphsage.graph_builder import TimetableGraphBuilder


PRIORITY_MESSAGES = {
    "La capacidad del aula es insuficiente",
    "Curso virtual debe tener 1 franja de separación de presenciales",
}


def normalize_session(raw: str | None) -> str:
    value = (raw or "").strip().lower()
    if value.startswith("t"):
        return "T"
    if value.startswith("p"):
        return "P"
    if value.startswith("l"):
        return "L"
    return "T"


def build_current_schedule(db, graph_builder: TimetableGraphBuilder) -> List[Assignment]:
    rows = db.execute(
        text(
            """
            SELECT
                sa.course_section_id,
                sa.professor_id,
                sa.classroom_id,
                sa.time_slot_id,
                c.codigo AS course_code,
                c.ciclo,
                COALESCE(cs.league, 1) AS league,
                cs.tipo,
                cs.alumnos_proyectados
            FROM schedule_assignments sa
            JOIN course_sections cs ON cs.id = sa.course_section_id
            JOIN courses c ON c.id = cs.course_id
            WHERE cs.active = 1
            """
        )
    ).mappings().all()

    grouped: Dict[int, Dict[str, Any]] = {}
    for row in rows:
        section_id = int(row["course_section_id"])
        if section_id not in grouped:
            grouped[section_id] = {
                "section_id": section_id,
                "professor_id": int(row["professor_id"]),
                "classroom_id": int(row["classroom_id"]) if row["classroom_id"] is not None else None,
                "course_code": row["course_code"],
                "session_type": normalize_session(row["tipo"]),
                "league_id": int(row["league"]),
                "ciclo": str(row["ciclo"] or "SIN-CICLO"),
                "alumnos_proyectados": int(row["alumnos_proyectados"] or 0),
                "timeslot_ids": [],
            }
        grouped[section_id]["timeslot_ids"].append(int(row["time_slot_id"]))

    schedule: List[Assignment] = []
    for section_id, data in grouped.items():
        ordered_timeslots = sorted(
            set(data["timeslot_ids"]),
            key=lambda ts_id: graph_builder.timeslot_id_to_idx.get(ts_id, ts_id),
        )
        schedule.append(
            Assignment(
                section_id=section_id,
                professor_id=data["professor_id"],
                classroom_id=data["classroom_id"],
                timeslot_ids=ordered_timeslots,
                course_code=data["course_code"],
                session_type=data["session_type"],
                league_id=data["league_id"],
                ciclo=data["ciclo"],
                alumnos_proyectados=data["alumnos_proyectados"],
                original_section_id=section_id,
            )
        )

    return schedule


def get_all_violations(engine, schedule: List[Assignment]) -> List[Dict[str, Any]]:
    _, violations = engine.hard_validator.validate_schedule(schedule)
    return violations


def get_priority_targets(violations: List[Dict[str, Any]]) -> List[int]:
    section_ids: set[int] = set()
    for violation in violations:
        message = str(violation.get("mensaje", ""))
        if message not in PRIORITY_MESSAGES:
            continue

        section_id = violation.get("section_id")
        if section_id is not None:
            section_ids.add(int(section_id))

        detail = violation.get("detalle") or {}
        virtual_id = detail.get("virtual_section_id")
        if virtual_id is not None:
            section_ids.add(int(virtual_id))

        presencial_id = detail.get("presencial_section_id")
        if presencial_id is not None:
            section_ids.add(int(presencial_id))

    return sorted(section_ids)


def assignment_signature(a: Assignment) -> Tuple[int, int | None, int, Tuple[int, ...]]:
    return (a.professor_id, a.classroom_id, a.section_id, tuple(sorted(a.timeslot_ids)))


def persist_sections(db, repaired_assignments: List[Assignment]) -> None:
    if not repaired_assignments:
        return

    section_ids = sorted({a.section_id for a in repaired_assignments})
    ids_sql = ",".join(str(int(sid)) for sid in section_ids)
    semestre = db.execute(
        text("SELECT semestre FROM schedule_assignments WHERE semestre IS NOT NULL ORDER BY id DESC LIMIT 1")
    ).scalar() or "2025-2"

    db.execute(text(f"DELETE FROM schedule_assignments WHERE course_section_id IN ({ids_sql})"))

    for assignment in repaired_assignments:
        course_id = db.execute(
            text("SELECT course_id FROM course_sections WHERE id = :section_id"),
            {"section_id": assignment.section_id},
        ).scalar()

        for timeslot_id in assignment.timeslot_ids:
            db.execute(
                text(
                    """
                    INSERT INTO schedule_assignments
                        (course_id, course_section_id, professor_id, classroom_id, time_slot_id,
                         semestre, estado, generado_por_algoritmo, confianza_asignacion)
                    VALUES
                        (:course_id, :course_section_id, :professor_id, :classroom_id, :time_slot_id,
                         :semestre, 'programado', TRUE, 0.95)
                    """
                ),
                {
                    "course_id": int(course_id),
                    "course_section_id": int(assignment.section_id),
                    "professor_id": int(assignment.professor_id),
                    "classroom_id": int(assignment.classroom_id) if assignment.classroom_id is not None else None,
                    "time_slot_id": int(timeslot_id),
                    "semestre": str(semestre),
                },
            )


def count_priority_violations(violations: List[Dict[str, Any]]) -> int:
    return sum(1 for v in violations if str(v.get("mensaje", "")) in PRIORITY_MESSAGES)


def main() -> None:
    parser = argparse.ArgumentParser(description="Repara conflictos duros prioritarios (capacidad/virtual-spacing)")
    parser.add_argument("--apply", action="store_true", help="Aplica cambios en BD")
    args = parser.parse_args()

    db = SessionLocal()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    try:
        graph_builder = TimetableGraphBuilder(db)
        graph = graph_builder.build_graph()

        engine = create_aco_engine(
            graph=graph,
            model=None,
            graph_builder=graph_builder,
            db_session=db,
            params={
                "shuffle_candidates": True,
                "max_professors_per_section": 40,
                "max_classrooms_per_section": 60,
                "max_timeslots_per_section": 20,
                "max_candidate_combinations": 1200,
                "pedagogical_relaxation_attempts": 0,
                "pedagogical_relaxation_rank_step": 0,
                "pedagogical_relaxation_min_cycle": 99,
            },
        )

        original_schedule = build_current_schedule(db, graph_builder)
        working_schedule = list(original_schedule)

        violations_before = get_all_violations(engine, working_schedule)
        targets = get_priority_targets(violations_before)

        by_section = {a.section_id: a for a in working_schedule}
        changed_sections: set[int] = set()
        failed_targets: Dict[int, List[str]] = {}

        for section_id in targets:
            if section_id not in by_section:
                continue
            if section_id not in graph_builder.section_id_to_idx:
                failed_targets[section_id] = ["section_not_in_graph_index"]
                continue

            original_assignment = by_section[section_id]
            base_schedule = [a for a in working_schedule if a.section_id != section_id]

            repaired = None
            best_logs: List[str] = []
            for attempt in range(12):
                random.seed((attempt + 1) * 7919 + section_id)
                candidate = engine._assign_section(section_id, base_schedule, ant_id=0)
                if candidate is not None:
                    repaired = candidate
                    break
                best_logs = list(engine._last_debug_logs or [])

            if repaired is None:
                failed_targets[section_id] = best_logs[:40]
                continue

            working_schedule = base_schedule + [repaired]
            by_section[section_id] = repaired
            if assignment_signature(original_assignment) != assignment_signature(repaired):
                changed_sections.add(section_id)

        violations_after = get_all_violations(engine, working_schedule)

        original_by_section = {a.section_id: a for a in original_schedule}
        working_by_section = {a.section_id: a for a in working_schedule}
        changed_assignments = [working_by_section[sid] for sid in sorted(changed_sections) if sid in working_by_section]

        report = {
            "timestamp": timestamp,
            "mode": "apply" if args.apply else "dry-run",
            "priority_targets": targets,
            "priority_before": count_priority_violations(violations_before),
            "priority_after": count_priority_violations(violations_after),
            "hard_before": len(violations_before),
            "hard_after": len(violations_after),
            "failed_targets": failed_targets,
            "changed_sections": sorted(changed_sections),
            "hard_violations_preview_after": violations_after[:20],
            "applied": False,
        }

        if args.apply and report["priority_after"] == 0:
            persist_sections(db, changed_assignments)
            db.commit()
            report["applied"] = True
        elif args.apply:
            report["apply_block_reason"] = "priority_conflicts_not_zero"

        output_dir = Path("logs")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"reparar_conflictos_prioridad_{timestamp}.json"
        output_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

        print("=" * 80)
        print("REPARACIÓN CONFLICTOS PRIORITARIOS")
        print("=" * 80)
        print(f"Modo: {report['mode']}")
        print(f"Conflictos prioritarios antes: {report['priority_before']}")
        print(f"Conflictos prioritarios después: {report['priority_after']}")
        print(f"Violaciones duras totales antes: {report['hard_before']}")
        print(f"Violaciones duras totales después: {report['hard_after']}")
        print(f"Secciones cambiadas: {len(report['changed_sections'])}")
        print(f"Aplicado en BD: {report['applied']}")
        print(f"Reporte: {output_file}")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
