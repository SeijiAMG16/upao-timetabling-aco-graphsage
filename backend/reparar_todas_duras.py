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


MAX_OUTER_ROUNDS = 8
MAX_SECTION_ATTEMPTS = 16


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


def get_violations(engine, schedule: List[Assignment]) -> List[Dict[str, Any]]:
    _, violations = engine.hard_validator.validate_schedule(schedule)
    return violations


def count_tpl(violations: List[Dict[str, Any]]) -> int:
    return sum(1 for v in violations if str(v.get("mensaje", "")).startswith("Secuencia pedagógica T→P→L inválida"))


def section_ids_from_violation(v: Dict[str, Any]) -> List[int]:
    ids: List[int] = []
    sid = v.get("section_id")
    if sid is not None:
        ids.append(int(sid))

    detail = v.get("detalle") or {}
    for key in ("virtual_section_id", "presencial_section_id", "conflict_section_id", "other_section_id"):
        value = detail.get(key)
        if value is not None:
            ids.append(int(value))

    out: List[int] = []
    seen: set[int] = set()
    for x in ids:
        if x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


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


def assignment_to_payload(a: Assignment) -> Dict[str, Any]:
    return {
        "section_id": int(a.section_id),
        "professor_id": int(a.professor_id),
        "classroom_id": int(a.classroom_id) if a.classroom_id is not None else None,
        "timeslot_ids": [int(t) for t in sorted(a.timeslot_ids)],
        "course_code": str(a.course_code),
        "session_type": str(a.session_type),
        "league_id": int(a.league_id) if a.league_id is not None else None,
        "ciclo": str(a.ciclo),
        "alumnos_proyectados": int(a.alumnos_proyectados) if a.alumnos_proyectados is not None else 0,
        "original_section_id": int(getattr(a, "original_section_id", a.section_id)),
    }


def assignment_from_payload(payload: Dict[str, Any]) -> Assignment:
    return Assignment(
        section_id=int(payload["section_id"]),
        professor_id=int(payload["professor_id"]),
        classroom_id=int(payload["classroom_id"]) if payload.get("classroom_id") is not None else None,
        timeslot_ids=[int(t) for t in payload.get("timeslot_ids", [])],
        course_code=str(payload.get("course_code", "UNKNOWN")),
        session_type=str(payload.get("session_type", "T")),
        league_id=int(payload.get("league_id")) if payload.get("league_id") is not None else 1,
        ciclo=str(payload.get("ciclo", "SIN-CICLO")),
        alumnos_proyectados=int(payload.get("alumnos_proyectados", 0)),
        original_section_id=int(payload.get("original_section_id", payload["section_id"])),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Repara todas las restricciones duras restantes de forma iterativa")
    parser.add_argument("--apply", action="store_true", help="Aplica cambios en BD")
    parser.add_argument(
        "--apply-from-report",
        type=str,
        default=None,
        help="Aplica directamente desde un reporte dry-run previo con proposed_assignments",
    )
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
                "max_professors_per_section": 45,
                "max_classrooms_per_section": 70,
                "max_timeslots_per_section": 24,
                "max_candidate_combinations": 1600,
                "pedagogical_relaxation_attempts": 0,
                "pedagogical_relaxation_rank_step": 0,
                "pedagogical_relaxation_min_cycle": 99,
            },
        )

        original_schedule = build_current_schedule(db, graph_builder)
        working_schedule = list(original_schedule)

        if args.apply_from_report:
            report_path = Path(args.apply_from_report)
            source_report = json.loads(report_path.read_text(encoding="utf-8"))
            proposed_payload = source_report.get("proposed_assignments", [])
            proposed_assignments = [assignment_from_payload(p) for p in proposed_payload]

            proposed_map = {a.section_id: a for a in proposed_assignments}
            base_schedule = [a for a in working_schedule if a.section_id not in proposed_map]
            working_schedule = base_schedule + proposed_assignments

            before_violations = get_violations(engine, original_schedule)
            after_violations = get_violations(engine, working_schedule)

            report = {
                "timestamp": timestamp,
                "mode": "apply-from-report",
                "source_report": str(report_path),
                "hard_before": len(before_violations),
                "hard_after": len(after_violations),
                "tpl_before": count_tpl(before_violations),
                "tpl_after": count_tpl(after_violations),
                "changed_sections": sorted(proposed_map.keys()),
                "hard_violations_preview_after": after_violations[:30],
                "applied": False,
            }

            if args.apply and len(after_violations) == 0:
                persist_sections(db, proposed_assignments)
                db.commit()
                report["applied"] = True
            elif args.apply:
                report["apply_block_reason"] = "hard_not_zero"

            output_dir = Path("logs")
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / f"reparar_todas_duras_{timestamp}.json"
            output_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

            print("=" * 80)
            print("REPARACIÓN TOTAL DE DURAS")
            print("=" * 80)
            print(f"Modo: {report['mode']}")
            print(f"Hard antes: {report['hard_before']}")
            print(f"Hard después: {report['hard_after']}")
            print(f"T→P→L antes: {report['tpl_before']}")
            print(f"T→P→L después: {report['tpl_after']}")
            print(f"Secciones cambiadas: {len(report['changed_sections'])}")
            print(f"Aplicado en BD: {report['applied']}")
            print(f"Reporte: {output_file}")
            return

        before_violations = get_violations(engine, working_schedule)
        rounds_trace: List[Dict[str, Any]] = []
        changed_sections: set[int] = set()

        for round_idx in range(1, MAX_OUTER_ROUNDS + 1):
            violations = get_violations(engine, working_schedule)
            if not violations:
                rounds_trace.append({"round": round_idx, "violations": 0, "changed": 0})
                break

            violation_sections: List[int] = []
            seen_sections: set[int] = set()
            for v in violations:
                for sid in section_ids_from_violation(v):
                    if sid in seen_sections:
                        continue
                    seen_sections.add(sid)
                    violation_sections.append(sid)

            round_changed = 0
            for section_id in violation_sections:
                if section_id not in graph_builder.section_id_to_idx:
                    continue

                current_by_id = {a.section_id: a for a in working_schedule}
                current_assignment = current_by_id.get(section_id)
                if current_assignment is None:
                    continue

                base_schedule = [a for a in working_schedule if a.section_id != section_id]
                current_violation_count = len(get_violations(engine, base_schedule + [current_assignment]))

                best_assignment = current_assignment
                best_violation_count = current_violation_count

                for attempt in range(MAX_SECTION_ATTEMPTS):
                    random.seed(round_idx * 100000 + section_id * 101 + attempt)
                    candidate = engine._assign_section(section_id, base_schedule, ant_id=0)
                    if candidate is None:
                        continue

                    candidate_schedule = base_schedule + [candidate]
                    candidate_violations = len(get_violations(engine, candidate_schedule))
                    if candidate_violations < best_violation_count:
                        best_assignment = candidate
                        best_violation_count = candidate_violations

                    if candidate_violations == 0:
                        break

                if assignment_signature(best_assignment) != assignment_signature(current_assignment):
                    working_schedule = base_schedule + [best_assignment]
                    changed_sections.add(section_id)
                    round_changed += 1

            post_round_violations = len(get_violations(engine, working_schedule))
            rounds_trace.append(
                {
                    "round": round_idx,
                    "violations": post_round_violations,
                    "changed": round_changed,
                }
            )

            if round_changed == 0:
                break

        after_violations = get_violations(engine, working_schedule)

        original_by_section = {a.section_id: a for a in original_schedule}
        working_by_section = {a.section_id: a for a in working_schedule}
        changed_assignments = [working_by_section[sid] for sid in sorted(changed_sections) if sid in working_by_section]

        report = {
            "timestamp": timestamp,
            "mode": "apply" if args.apply else "dry-run",
            "hard_before": len(before_violations),
            "hard_after": len(after_violations),
            "tpl_before": count_tpl(before_violations),
            "tpl_after": count_tpl(after_violations),
            "rounds_trace": rounds_trace,
            "changed_sections": sorted(changed_sections),
            "proposed_assignments": [assignment_to_payload(a) for a in changed_assignments],
            "hard_violations_preview_after": after_violations[:30],
            "applied": False,
        }

        if args.apply and len(after_violations) == 0:
            persist_sections(db, changed_assignments)
            db.commit()
            report["applied"] = True
        elif args.apply:
            report["apply_block_reason"] = "hard_not_zero"

        output_dir = Path("logs")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"reparar_todas_duras_{timestamp}.json"
        output_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

        print("=" * 80)
        print("REPARACIÓN TOTAL DE DURAS")
        print("=" * 80)
        print(f"Modo: {report['mode']}")
        print(f"Hard antes: {report['hard_before']}")
        print(f"Hard después: {report['hard_after']}")
        print(f"T→P→L antes: {report['tpl_before']}")
        print(f"T→P→L después: {report['tpl_after']}")
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
