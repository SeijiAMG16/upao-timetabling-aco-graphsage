from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

from sqlalchemy import text

from app.database import SessionLocal


@dataclass
class SectionNeed:
    section_id: int
    current_classroom_id: int
    required_capacity: int
    session_type: str
    projected_students: int
    timeslot_ids: Set[int]


def normalize_session(raw: str | None) -> str:
    value = (raw or "").strip().lower()
    if value.startswith("t"):
        return "T"
    if value.startswith("p"):
        return "P"
    if value.startswith("l"):
        return "L"
    return "T"


def normalize_classroom_type(raw: str | None) -> str:
    value = (raw or "").strip().lower()
    if value in {"lab", "laboratorio", "laboratory"}:
        return "laboratorio"
    if value in {"practica", "práctica", "practice"}:
        return "practica"
    return "teorica"


def classroom_valid_for_section(session_type: str, projected_students: int, classroom_type: str, building: str) -> bool:
    if session_type == "L":
        if classroom_type != "laboratorio":
            return False
        expected = "F" if projected_students <= 20 else "G"
        return (building or "").strip().upper() == expected

    if session_type == "P":
        return classroom_type in {"practica", "laboratorio", "teorica"}

    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Repara secciones con aula de capacidad insuficiente")
    parser.add_argument("--apply", action="store_true", help="Aplica cambios en BD")
    args = parser.parse_args()

    db = SessionLocal()

    try:
        rows = db.execute(
            text(
                """
                SELECT
                    sa.course_section_id AS section_id,
                    sa.classroom_id,
                    sa.time_slot_id,
                    cs.alumnos_proyectados,
                    cs.tipo,
                    cl.capacidad
                FROM schedule_assignments sa
                JOIN course_sections cs ON cs.id = sa.course_section_id
                JOIN classrooms cl ON cl.id = sa.classroom_id
                WHERE cl.capacidad < cs.alumnos_proyectados
                ORDER BY sa.course_section_id
                """
            )
        ).mappings().all()

        sections: Dict[int, SectionNeed] = {}
        for row in rows:
            section_id = int(row["section_id"])
            if section_id not in sections:
                sections[section_id] = SectionNeed(
                    section_id=section_id,
                    current_classroom_id=int(row["classroom_id"]),
                    required_capacity=int(row["alumnos_proyectados"]),
                    session_type=normalize_session(row["tipo"]),
                    projected_students=int(row["alumnos_proyectados"]),
                    timeslot_ids=set(),
                )
            sections[section_id].timeslot_ids.add(int(row["time_slot_id"]))

        classroom_rows = db.execute(
            text(
                """
                SELECT id, codigo, capacidad, tipo, edificio, active
                FROM classrooms
                WHERE active = 1
                """
            )
        ).mappings().all()

        classrooms = [
            {
                "id": int(r["id"]),
                "codigo": r["codigo"],
                "capacidad": int(r["capacidad"]),
                "tipo": normalize_classroom_type(r["tipo"]),
                "edificio": (r["edificio"] or "").strip().upper(),
            }
            for r in classroom_rows
        ]

        occupied: Dict[int, Set[int]] = defaultdict(set)
        occ_rows = db.execute(
            text("SELECT classroom_id, time_slot_id FROM schedule_assignments")
        ).mappings().all()
        for r in occ_rows:
            occupied[int(r["classroom_id"])].add(int(r["time_slot_id"]))

        fixes = []
        unresolved = []

        for section in sections.values():
            current_occupied = occupied.get(section.current_classroom_id, set())
            for ts in section.timeslot_ids:
                current_occupied.discard(ts)

            candidates = sorted(
                classrooms,
                key=lambda c: (c["capacidad"], c["id"]),
            )

            selected: Optional[dict] = None
            for classroom in candidates:
                if classroom["id"] == section.current_classroom_id:
                    continue
                if classroom["capacidad"] < section.required_capacity:
                    continue
                if not classroom_valid_for_section(
                    section.session_type,
                    section.projected_students,
                    classroom["tipo"],
                    classroom["edificio"],
                ):
                    continue
                if any(ts in occupied[classroom["id"]] for ts in section.timeslot_ids):
                    continue
                selected = classroom
                break

            for ts in section.timeslot_ids:
                current_occupied.add(ts)

            if selected is None:
                unresolved.append(section)
                continue

            fixes.append(
                {
                    "section_id": section.section_id,
                    "from_classroom_id": section.current_classroom_id,
                    "to_classroom_id": int(selected["id"]),
                    "to_classroom_code": selected["codigo"],
                    "required_capacity": section.required_capacity,
                    "new_capacity": selected["capacidad"],
                }
            )

            if args.apply:
                db.execute(
                    text(
                        """
                        UPDATE schedule_assignments
                        SET classroom_id = :new_classroom_id
                        WHERE course_section_id = :section_id
                        """
                    ),
                    {
                        "new_classroom_id": int(selected["id"]),
                        "section_id": section.section_id,
                    },
                )

                for ts in section.timeslot_ids:
                    occupied[section.current_classroom_id].discard(ts)
                    occupied[selected["id"]].add(ts)

        if args.apply:
            db.commit()

        print("=" * 80)
        print("REPARACIÓN DE CAPACIDAD DE AULAS")
        print("=" * 80)
        print(f"Modo: {'apply' if args.apply else 'dry-run'}")
        print(f"Secciones con violación detectada: {len(sections)}")
        print(f"Secciones reparables: {len(fixes)}")
        print(f"Secciones no resueltas: {len(unresolved)}")

        if fixes:
            print("\nPrimeras reparaciones:")
            for fix in fixes[:12]:
                print(
                    f"  - Sección {fix['section_id']}: aula {fix['from_classroom_id']} -> "
                    f"{fix['to_classroom_id']} ({fix['to_classroom_code']}) "
                    f"cap {fix['required_capacity']}->{fix['new_capacity']}"
                )

        if unresolved:
            print("\nSecciones no resueltas (primeras 12):")
            for sec in unresolved[:12]:
                print(
                    f"  - Sección {sec.section_id} tipo={sec.session_type} "
                    f"cap={sec.required_capacity} slots={sorted(sec.timeslot_ids)}"
                )

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
