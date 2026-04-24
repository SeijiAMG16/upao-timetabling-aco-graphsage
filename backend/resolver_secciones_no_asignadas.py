from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

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


def main() -> None:
    parser = argparse.ArgumentParser(description="Resuelve secciones no asignadas usando ACO dirigido")
    parser.add_argument("--apply", action="store_true", help="Aplica asignaciones en BD")
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
                "pedagogical_relaxation_attempts": 8,
                "pedagogical_relaxation_rank_step": 40,
                "pedagogical_relaxation_min_cycle": 1,
            },
        )

        current_schedule = build_current_schedule(db, graph_builder)

        missing_rows = db.execute(
            text(
                """
                SELECT
                    cs.id AS section_id,
                    cs.course_id,
                    c.codigo AS course_code,
                    COALESCE(cs.league, 1) AS league,
                    cs.tipo,
                    cs.alumnos_proyectados,
                    c.ciclo
                FROM course_sections cs
                JOIN courses c ON c.id = cs.course_id
                LEFT JOIN schedule_assignments sa ON sa.course_section_id = cs.id
                WHERE cs.active = 1
                                    AND cs.alumnos_proyectados > 0
                  AND sa.id IS NULL
                ORDER BY c.codigo, cs.tipo, COALESCE(cs.league, 1), cs.id
                """
            )
        ).mappings().all()

        missing_ids = [int(r["section_id"]) for r in missing_rows]
        engine.debug_sections = set(missing_ids)

        assigned_now: List[Assignment] = []
        failed_ids: List[int] = []
        skipped_not_in_graph: List[int] = []
        failed_debug: Dict[int, List[str]] = {}

        for section_id in missing_ids:
            if section_id not in graph_builder.section_id_to_idx:
                skipped_not_in_graph.append(section_id)
                failed_ids.append(section_id)
                failed_debug[section_id] = ["section_not_in_graph_index"]
                continue

            new_assignment = engine._assign_section(section_id, current_schedule, ant_id=0)
            if new_assignment is None:
                failed_ids.append(section_id)
                failed_debug[section_id] = list(engine._last_debug_logs or [])
                continue
            current_schedule.append(new_assignment)
            assigned_now.append(new_assignment)

        valid_all, violations = engine.hard_validator.validate_schedule(current_schedule)

        report = {
            "timestamp": timestamp,
            "mode": "apply" if args.apply else "dry-run",
            "missing_before": len(missing_ids),
            "assigned_now": len(assigned_now),
            "failed_now": len(failed_ids),
            "failed_ids": failed_ids,
            "skipped_not_in_graph": skipped_not_in_graph,
            "failed_debug": failed_debug,
            "hard_constraints_ok": bool(valid_all),
            "hard_violations_count": len(violations),
            "hard_violations_preview": violations[:15],
            "assigned_sections": [
                {
                    "section_id": a.section_id,
                    "professor_id": a.professor_id,
                    "classroom_id": a.classroom_id,
                    "timeslot_ids": a.timeslot_ids,
                }
                for a in assigned_now
            ],
        }

        if args.apply and assigned_now and valid_all:
            semestre = db.execute(
                text(
                    "SELECT semestre FROM schedule_assignments WHERE semestre IS NOT NULL ORDER BY id DESC LIMIT 1"
                )
            ).scalar() or "2025-2"

            for assignment in assigned_now:
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

            db.commit()
            report["applied"] = True
        else:
            report["applied"] = False
            if args.apply and not valid_all:
                report["apply_block_reason"] = "hard_constraints_failed"

        output_dir = Path("logs")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"resolver_no_asignadas_{timestamp}.json"
        output_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

        print("=" * 80)
        print("RESOLUCIÓN DE SECCIONES NO ASIGNADAS")
        print("=" * 80)
        print(f"Modo: {report['mode']}")
        print(f"Faltantes antes: {report['missing_before']}")
        print(f"Asignadas ahora: {report['assigned_now']}")
        print(f"No resueltas: {report['failed_now']} -> {report['failed_ids']}")
        print(f"Hard constraints OK: {report['hard_constraints_ok']}")
        print(f"Violaciones duras: {report['hard_violations_count']}")
        print(f"Aplicado en BD: {report['applied']}")
        print(f"Reporte: {output_file}")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
