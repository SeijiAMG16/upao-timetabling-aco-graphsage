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


def pedagogical_violations(engine, schedule: List[Assignment]) -> List[Dict[str, Any]]:
    _, violations = engine.hard_validator.validate_schedule(schedule)
    return [v for v in violations if str(v.get("mensaje", "")).startswith("Secuencia pedagógica T→P→L inválida")]


def assignment_signature(a: Assignment) -> Tuple[int, int | None, int, Tuple[int, ...]]:
    return (a.professor_id, a.classroom_id, a.section_id, tuple(sorted(a.timeslot_ids)))


def repair_group(
    engine,
    current_schedule: List[Assignment],
    group_key: Tuple[str, int],
) -> Tuple[bool, List[int], List[str]]:
    course_code, league_id = group_key
    order = {"T": 0, "P": 1, "L": 2}

    group_assignments = [
        a for a in current_schedule
        if a.course_code == course_code and a.league_id == league_id
    ]
    if not group_assignments:
        return False, [], ["group_without_assignments"]

    group_assignments_sorted = sorted(
        group_assignments,
        key=lambda a: (order.get(a.session_type, 9), a.section_id),
    )

    section_ids = [a.section_id for a in group_assignments_sorted]
    section_ids_set = set(section_ids)
    base_schedule = [a for a in current_schedule if a.section_id not in section_ids_set]
    debug_log: List[str] = []

    def _attempt_rebuild(
        rebuild_sections: List[Assignment],
        fixed_sections: List[Assignment],
        strategy_name: str,
        max_attempts: int,
    ) -> Tuple[bool, List[Assignment], List[str]]:
        ordered = sorted(
            rebuild_sections,
            key=lambda a: (order.get(a.session_type, 9), a.section_id),
        )

        best_logs: List[str] = []
        for attempt in range(max_attempts):
            random.seed((attempt + 1) * 9973 + sum(section_ids))
            rebuilt: List[Assignment] = []
            logs: List[str] = [f"{strategy_name}:attempt:{attempt + 1}/{max_attempts}"]

            failed = False
            for section in ordered:
                new_assignment = engine._assign_section(
                    section.section_id,
                    base_schedule + fixed_sections + rebuilt,
                    ant_id=0,
                )
                if new_assignment is None:
                    logs.append(f"{strategy_name}:failed_section:{section.section_id}")
                    logs.extend(list(engine._last_debug_logs or []))
                    failed = True
                    break
                rebuilt.append(new_assignment)

            if failed:
                best_logs = logs
                continue

            candidate_schedule = base_schedule + fixed_sections + rebuilt
            group_violations = [
                v for v in pedagogical_violations(engine, candidate_schedule)
                if int(v.get("section_id", -1)) in section_ids_set
            ]
            if not group_violations:
                return True, candidate_schedule, logs

            logs.append(f"{strategy_name}:group_still_has_tpl_violations")
            best_logs = logs

        return False, [], best_logs

    full_ok, full_schedule, full_logs = _attempt_rebuild(
        rebuild_sections=group_assignments_sorted,
        fixed_sections=[],
        strategy_name="rebuild_all_tpl",
        max_attempts=10,
    )
    if full_ok:
        current_schedule.clear()
        current_schedule.extend(full_schedule)
        return True, section_ids, []
    debug_log.extend(full_logs)

    fixed_t = [a for a in group_assignments_sorted if a.session_type == "T"]
    rebuild_pl = [a for a in group_assignments_sorted if a.session_type in {"P", "L"}]
    if rebuild_pl:
        pl_ok, pl_schedule, pl_logs = _attempt_rebuild(
            rebuild_sections=rebuild_pl,
            fixed_sections=fixed_t,
            strategy_name="rebuild_pl_keep_t",
            max_attempts=6,
        )
        if pl_ok:
            current_schedule.clear()
            current_schedule.extend(pl_schedule)
            return True, section_ids, []
        debug_log.extend(pl_logs)

    fixed_tp = [a for a in group_assignments_sorted if a.session_type in {"T", "P"}]
    rebuild_l = [a for a in group_assignments_sorted if a.session_type == "L"]
    if rebuild_l:
        l_ok, l_schedule, l_logs = _attempt_rebuild(
            rebuild_sections=rebuild_l,
            fixed_sections=fixed_tp,
            strategy_name="rebuild_l_keep_tp",
            max_attempts=4,
        )
        if l_ok:
            current_schedule.clear()
            current_schedule.extend(l_schedule)
            return True, section_ids, []
        debug_log.extend(l_logs)

    return False, section_ids, debug_log[:80]


def persist_sections(db, repaired_assignments: List[Assignment]) -> None:
    if not repaired_assignments:
        return

    section_ids = sorted({a.section_id for a in repaired_assignments})
    semestre = db.execute(
        text("SELECT semestre FROM schedule_assignments WHERE semestre IS NOT NULL ORDER BY id DESC LIMIT 1")
    ).scalar() or "2025-2"

    ids_sql = ",".join(str(int(sid)) for sid in section_ids)
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Repara violaciones T→P→L reprogramando por curso/liga")
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

        before_tpl = pedagogical_violations(engine, working_schedule)
        violating_section_ids = sorted({
            int(v.get("section_id")) for v in before_tpl if v.get("section_id") is not None
        })

        by_section = {a.section_id: a for a in working_schedule}
        groups = sorted({
            (by_section[sid].course_code, by_section[sid].league_id)
            for sid in violating_section_ids
            if sid in by_section
        })

        repaired_groups: List[Tuple[str, int]] = []
        failed_groups: Dict[str, Any] = {}
        touched_section_ids: set[int] = set()

        for group in groups:
            ok, section_ids, debug = repair_group(engine, working_schedule, group)
            key = f"{group[0]}|liga_{group[1]}"
            if ok:
                repaired_groups.append(group)
                touched_section_ids.update(section_ids)
            else:
                failed_groups[key] = {
                    "section_ids": section_ids,
                    "debug": debug,
                }

        after_tpl = pedagogical_violations(engine, working_schedule)

        original_by_section = {a.section_id: a for a in original_schedule}
        working_by_section = {a.section_id: a for a in working_schedule}
        changed_sections = [
            sid for sid in sorted(touched_section_ids)
            if sid in original_by_section
            and sid in working_by_section
            and assignment_signature(original_by_section[sid]) != assignment_signature(working_by_section[sid])
        ]

        all_valid_after, all_violations_after = engine.hard_validator.validate_schedule(working_schedule)

        report: Dict[str, Any] = {
            "timestamp": timestamp,
            "mode": "apply" if args.apply else "dry-run",
            "tpl_before": len(before_tpl),
            "tpl_after": len(after_tpl),
            "groups_total": len(groups),
            "groups_repaired": len(repaired_groups),
            "groups_failed": len(failed_groups),
            "repaired_groups": [{"course_code": c, "league_id": l} for c, l in repaired_groups],
            "failed_groups": failed_groups,
            "changed_sections": changed_sections,
            "hard_constraints_ok_after": bool(all_valid_after),
            "hard_violations_after": len(all_violations_after),
            "hard_violations_preview": all_violations_after[:20],
            "applied": False,
        }

        if args.apply and len(after_tpl) == 0:
            repaired_assignments = [working_by_section[sid] for sid in changed_sections if sid in working_by_section]
            persist_sections(db, repaired_assignments)
            db.commit()
            report["applied"] = True
        elif args.apply:
            report["apply_block_reason"] = "tpl_not_zero"

        output_dir = Path("logs")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"reparar_tpl_{timestamp}.json"
        output_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

        print("=" * 80)
        print("REPARACIÓN T→P→L")
        print("=" * 80)
        print(f"Modo: {report['mode']}")
        print(f"Violaciones T→P→L antes: {report['tpl_before']}")
        print(f"Violaciones T→P→L después: {report['tpl_after']}")
        print(f"Grupos reparados: {report['groups_repaired']} / {report['groups_total']}")
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
