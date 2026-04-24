from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy import text

from app.database import SessionLocal


DAY_CASE_SQL = """
CASE
    WHEN LOWER(pr.day) LIKE 'lun%' OR LOWER(pr.day) LIKE 'mon%' THEN 1
    WHEN LOWER(pr.day) LIKE 'mar%' OR LOWER(pr.day) LIKE 'tue%' THEN 2
    WHEN LOWER(pr.day) LIKE 'mie%' OR LOWER(pr.day) LIKE 'mié%' OR LOWER(pr.day) LIKE 'wed%' THEN 3
    WHEN LOWER(pr.day) LIKE 'jue%' OR LOWER(pr.day) LIKE 'thu%' THEN 4
    WHEN LOWER(pr.day) LIKE 'vie%' OR LOWER(pr.day) LIKE 'fri%' THEN 5
    WHEN LOWER(pr.day) LIKE 'sab%' OR LOWER(pr.day) LIKE 'sáb%' OR LOWER(pr.day) LIKE 'sat%' THEN 6
    ELSE 0
END
"""


def normalize_session(tipo: str | None) -> str:
    value = (tipo or "").strip().lower()
    if value.startswith("t"):
        return "T"
    if value.startswith("p"):
        return "P"
    if value.startswith("l"):
        return "L"
    return "T"


def get_suggested_professor(db, course_id: int, session_type: str, league: int, prof032_id: int | None):
    exact = db.execute(
        text(
            """
            SELECT professor_id
            FROM professor_course_assignments
            WHERE course_id = :course_id
              AND UPPER(LEFT(session_type, 1)) = :session_type
              AND COALESCE(league, 1) = :league
            LIMIT 1
            """
        ),
        {"course_id": course_id, "session_type": session_type, "league": league},
    ).scalar()

    if exact:
        return int(exact), "exact"

    by_type = db.execute(
        text(
            """
            SELECT professor_id
            FROM professor_course_assignments
            WHERE course_id = :course_id
              AND UPPER(LEFT(session_type, 1)) = :session_type
            LIMIT 1
            """
        ),
        {"course_id": course_id, "session_type": session_type},
    ).scalar()

    if by_type:
        return int(by_type), "type"

    by_course = db.execute(
        text(
            """
            SELECT professor_id
            FROM professor_course_assignments
            WHERE course_id = :course_id
            LIMIT 1
            """
        ),
        {"course_id": course_id},
    ).scalar()

    if by_course:
        return int(by_course), "course"

    return prof032_id, "PROF_032"


def main() -> None:
    parser = argparse.ArgumentParser(description="Inventario de conflictos + sugerencias de mapeo profesor-sección")
    parser.add_argument("--apply-mapping", action="store_true", help="Inserta mapeos exactos faltantes en professor_course_assignments")
    args = parser.parse_args()

    db = SessionLocal()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    try:
        prof032_id = db.execute(
            text("SELECT id FROM professors WHERE codigo = 'PROF_032' LIMIT 1")
        ).scalar()

        total_sections = db.execute(text("SELECT COUNT(*) FROM course_sections WHERE active = 1")).scalar() or 0
        assigned_sections = db.execute(
            text("SELECT COUNT(DISTINCT course_section_id) FROM schedule_assignments")
        ).scalar() or 0

        missing_rows = db.execute(
            text(
                """
                SELECT
                    cs.id AS section_id,
                    cs.course_id,
                    c.codigo AS course_code,
                    c.nombre AS course_name,
                    cs.tipo,
                    COALESCE(cs.league, 1) AS league,
                    cs.nrc
                FROM course_sections cs
                JOIN courses c ON c.id = cs.course_id
                LEFT JOIN schedule_assignments sa ON sa.course_section_id = cs.id
                WHERE cs.active = 1
                  AND sa.id IS NULL
                ORDER BY c.codigo, cs.tipo, COALESCE(cs.league, 1), cs.id
                """
            )
        ).mappings().all()

        missing_sections: List[Dict[str, Any]] = []
        inserted_mappings = 0

        for row in missing_rows:
            session_type = normalize_session(row["tipo"])
            professor_id, source = get_suggested_professor(
                db,
                int(row["course_id"]),
                session_type,
                int(row["league"]),
                int(prof032_id) if prof032_id else None,
            )

            item = {
                "section_id": int(row["section_id"]),
                "course_id": int(row["course_id"]),
                "course_code": row["course_code"],
                "course_name": row["course_name"],
                "tipo": row["tipo"],
                "session_type": session_type,
                "league": int(row["league"]),
                "nrc": row["nrc"],
                "suggested_professor_id": professor_id,
                "source": source,
            }
            missing_sections.append(item)

            if args.apply_mapping and professor_id is not None:
                exists = db.execute(
                    text(
                        """
                        SELECT id
                        FROM professor_course_assignments
                        WHERE course_id = :course_id
                          AND professor_id = :professor_id
                          AND UPPER(LEFT(session_type, 1)) = :session_type
                          AND COALESCE(league, 1) = :league
                        LIMIT 1
                        """
                    ),
                    {
                        "course_id": item["course_id"],
                        "professor_id": professor_id,
                        "session_type": session_type,
                        "league": item["league"],
                    },
                ).scalar()

                if not exists:
                    db.execute(
                        text(
                            """
                            INSERT INTO professor_course_assignments (course_id, professor_id, session_type, league, semestre)
                            VALUES (:course_id, :professor_id, :session_type, :league, '2025-2')
                            """
                        ),
                        {
                            "course_id": item["course_id"],
                            "professor_id": professor_id,
                            "session_type": session_type,
                            "league": item["league"],
                        },
                    )
                    inserted_mappings += 1

        prof_overlap_pairs = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM schedule_assignments a
                JOIN schedule_assignments b
                  ON a.professor_id = b.professor_id
                 AND a.time_slot_id = b.time_slot_id
                 AND a.id < b.id
                """
            )
        ).scalar() or 0

        room_overlap_pairs = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM schedule_assignments a
                JOIN schedule_assignments b
                  ON a.classroom_id = b.classroom_id
                 AND a.time_slot_id = b.time_slot_id
                 AND a.id < b.id
                """
            )
        ).scalar() or 0

        restriction_conflicts = db.execute(
            text(
                f"""
                SELECT COUNT(*)
                FROM schedule_assignments sa
                JOIN time_slots ts ON ts.id = sa.time_slot_id
                JOIN professor_restrictions pr ON pr.professor_id = sa.professor_id
                WHERE ({DAY_CASE_SQL}) = ts.dia_semana
                  AND ts.hora_inicio < pr.end_time
                  AND pr.start_time < ts.hora_fin
                """
            )
        ).scalar() or 0

        capacity_violations = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM schedule_assignments sa
                JOIN classrooms cl ON cl.id = sa.classroom_id
                JOIN course_sections cs ON cs.id = sa.course_section_id
                WHERE cl.capacidad < cs.alumnos_proyectados
                """
            )
        ).scalar() or 0

        lab_building_violations = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM schedule_assignments sa
                JOIN classrooms cl ON cl.id = sa.classroom_id
                JOIN course_sections cs ON cs.id = sa.course_section_id
                WHERE (LOWER(cs.tipo) LIKE 'lab%' OR LOWER(cs.tipo) = 'l' OR LOWER(cs.tipo) = 'laboratorio')
                  AND (
                        (cs.alumnos_proyectados <= 20 AND UPPER(cl.edificio) <> 'F')
                     OR (cs.alumnos_proyectados > 20 AND UPPER(cl.edificio) <> 'G')
                  )
                """
            )
        ).scalar() or 0

        summary = {
            "timestamp": timestamp,
            "total_sections": int(total_sections),
            "assigned_sections": int(assigned_sections),
            "coverage_pct": round((assigned_sections / total_sections * 100) if total_sections else 0.0, 2),
            "missing_sections_count": len(missing_sections),
            "prof_032_id": int(prof032_id) if prof032_id else None,
            "prof_overlap_pairs": int(prof_overlap_pairs),
            "room_overlap_pairs": int(room_overlap_pairs),
            "prof_restriction_conflicts": int(restriction_conflicts),
            "capacity_violations": int(capacity_violations),
            "lab_building_violations": int(lab_building_violations),
            "inserted_mappings": int(inserted_mappings),
            "mode": "apply-mapping" if args.apply_mapping else "dry-run",
        }

        if args.apply_mapping:
            db.commit()

        report = {
            "summary": summary,
            "missing_sections": missing_sections,
        }

        output_dir = Path("logs")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"inventario_conflictos_mapeo_{timestamp}.json"
        output_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

        print("=" * 80)
        print("INVENTARIO DE CONFLICTOS Y MAPEO")
        print("=" * 80)
        print(f"Modo: {summary['mode']}")
        print(f"Cobertura: {summary['assigned_sections']}/{summary['total_sections']} ({summary['coverage_pct']}%)")
        print(f"Secciones sin horario: {summary['missing_sections_count']}")
        print(f"Conflictos profesor (pares): {summary['prof_overlap_pairs']}")
        print(f"Conflictos aula (pares): {summary['room_overlap_pairs']}")
        print(f"Conflictos disponibilidad: {summary['prof_restriction_conflicts']}")
        print(f"Violaciones capacidad: {summary['capacity_violations']}")
        print(f"Violaciones edificio labs: {summary['lab_building_violations']}")
        print(f"Mapeos insertados: {summary['inserted_mappings']}")
        print(f"Reporte JSON: {output_file}")

        if missing_sections:
            print("\nPrimeras secciones faltantes (con sugerencia):")
            for row in missing_sections[:10]:
                print(
                    f"  - Sec {row['section_id']} {row['course_code']} ({row['session_type']}, liga {row['league']}), "
                    f"prof sugerido={row['suggested_professor_id']} [{row['source']}]"
                )

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
