#!/usr/bin/env python3
"""Populate course session durations from Excel + manual overrides into MySQL.

This script extracts the per-session duration (in minutes) for each course and
writes the canonical values into the ``course_session_hours`` table. Manual
overrides always take priority over extracted values.
"""
from __future__ import annotations

import json
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Dict, Tuple

from sqlalchemy import text

from app.database import SessionLocal, engine
from app.excel.course_hours_parser import extract_course_hours

ROOT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT_DIR.parent

INPUT_EXCEL = ROOT_DIR / "inputs" / "Horario_Docentes(2025-20).xlsx"
if not INPUT_EXCEL.exists():
    INPUT_EXCEL = PROJECT_ROOT / "inputs" / "Horario_Docentes(2025-20).xlsx"

MANUAL_OVERRIDES = ROOT_DIR / "manual_course_hours_overrides.json"
MAPEO_ABREVIATURAS = ROOT_DIR / "mapeo_manual_cursos.json"
MAPEO_NOMBRES = ROOT_DIR / "mapeo_nombres_cursos.json"


SessionMap = Dict[str, Dict[str, Dict[str, object]]]
DurationEntry = Dict[str, object]


def normalize(value: str | None) -> str:
    if not value:
        return ""
    decomposed = unicodedata.normalize("NFD", value)
    without_marks = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    collapsed = " ".join(without_marks.upper().split())
    return collapsed


def parse_duration(label: str | None) -> int | None:
    if not label:
        return None
    parts = label.split(":", 1)
    if len(parts) != 2:
        return None
    try:
        hours = int(parts[0])
        minutes = int(parts[1])
    except ValueError:
        return None
    return hours * 60 + minutes


def format_duration(minutes: int) -> str:
    hours = minutes // 60
    rem = minutes % 60
    return f"{hours}:{rem:02d}"


def ensure_table_exists() -> None:
    ddl = text(
        """
        CREATE TABLE IF NOT EXISTS course_session_hours (
            id INT AUTO_INCREMENT PRIMARY KEY,
            course_id INT NOT NULL,
            session_type ENUM('T', 'P', 'L') NOT NULL,
            duration_minutes INT NOT NULL,
            duration_hours DECIMAL(5, 2) NOT NULL,
            duration_label VARCHAR(10) NOT NULL,
            source VARCHAR(20) DEFAULT 'excel',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uq_course_session (course_id, session_type),
            CONSTRAINT fk_course_session_course FOREIGN KEY (course_id)
                REFERENCES courses(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
    )
    with engine.begin() as connection:
        connection.execute(ddl)


def load_mapping() -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    if MAPEO_ABREVIATURAS.exists():
        payload = json.loads(MAPEO_ABREVIATURAS.read_text(encoding="utf-8"))
        for source, target in payload.get("mapeo_abreviaturas", {}).items():
            mapping[normalize(source)] = normalize(target)
    if MAPEO_NOMBRES.exists():
        payload = json.loads(MAPEO_NOMBRES.read_text(encoding="utf-8"))
        for source, target in payload.get("mapeo_manual", {}).items():
            mapping[normalize(source)] = normalize(target)
    return mapping


def build_excel_durations() -> SessionMap:
    extracted, _issues = extract_course_hours(str(INPUT_EXCEL))
    excel_map: SessionMap = defaultdict(dict)
    for raw_course, sessions in extracted.items():
        normalized_course = normalize(raw_course)
        target = excel_map[normalized_course]
        for raw_type, details in sessions.items():
            session_type = (raw_type or "").strip().upper()
            if session_type not in {"T", "P", "L"}:
                continue
            minutes = None
            label = None
            per_occ = details.get("per_occurrence") or {}
            minutes_val = per_occ.get("minutes")
            if isinstance(minutes_val, int):
                minutes = minutes_val
                label = per_occ.get("duration_label")
            else:
                occurrences = details.get("occurrences") or []
                labels = {occ.get("duration_label") for occ in occurrences if occ.get("duration_label")}
                if len(labels) == 1:
                    label = labels.pop()  # type: ignore[arg-type]
                    minutes = parse_duration(label)
                else:
                    total_label = details.get("total_duration_label")
                    entries = details.get("entries") or len(occurrences)
                    total_minutes = parse_duration(total_label)
                    if total_minutes and entries:
                        minutes = total_minutes // max(entries, 1)
            if minutes is None:
                continue
            target[session_type] = {
                "minutes": minutes,
                "label": label or format_duration(minutes),
                "source": "excel",
            }
    return excel_map


def apply_manual_overrides(data: SessionMap) -> None:
    if not MANUAL_OVERRIDES.exists():
        return
    overrides = json.loads(MANUAL_OVERRIDES.read_text(encoding="utf-8"))
    for course_name, sessions in overrides.items():
        normalized_course = normalize(course_name)
        target = data.setdefault(normalized_course, {})
        for raw_type, duration_label in sessions.items():
            session_type = (raw_type or "").strip().upper()
            if session_type not in {"T", "P", "L"}:
                continue
            minutes = parse_duration(duration_label)
            if minutes is None:
                continue
            target[session_type] = {
                "minutes": minutes,
                "label": format_duration(minutes),
                "source": "manual",
            }


def map_to_db_courses(raw_map: SessionMap, alias_map: Dict[str, str]) -> SessionMap:
    mapped: SessionMap = defaultdict(dict)
    for course_name, sessions in raw_map.items():
        target_name = alias_map.get(course_name, course_name)
        bucket = mapped[target_name]
        for session_type, entry in sessions.items():
            existing = bucket.get(session_type)
            if existing and existing.get("source") == "manual":
                continue
            bucket[session_type] = entry
    return mapped


def load_courses_by_name() -> Dict[str, Tuple[int, str]]:
    result: Dict[str, Tuple[int, str]] = {}
    with SessionLocal() as session:
        rows = session.execute(text("SELECT id, nombre FROM courses WHERE active = 1"))
        for course_id, name in rows:
            key = normalize(name)
            if key and key not in result:
                result[key] = (course_id, name)
    return result


def upsert_course_hours(
    mapped_sessions: SessionMap, courses_index: Dict[str, Tuple[int, str]]
) -> Tuple[int, int, Dict[str, Dict[str, DurationEntry]]]:
    records: list[Dict[str, object]] = []
    payload: Dict[str, Dict[str, DurationEntry]] = {}
    for norm_name, sessions in mapped_sessions.items():
        course_info = courses_index.get(norm_name)
        if not course_info:
            continue
        course_id, original_name = course_info
        course_payload = payload.setdefault(original_name, {})
        for session_type, entry in sessions.items():
            minutes = entry.get("minutes")
            source = entry.get("source", "excel")
            if minutes is None:
                continue
            minutes_int = int(minutes)
            label = format_duration(minutes_int)
            course_payload[session_type] = {
                "minutes": minutes_int,
                "label": label,
                "source": source,
            }
            records.append(
                {
                    "course_id": course_id,
                    "session_type": session_type,
                    "duration_minutes": minutes_int,
                    "duration_hours": round(minutes_int / 60.0, 2),
                    "duration_label": label,
                    "source": source,
                }
            )
    if not records:
        return 0, 0, {}

    insert_stmt = text(
        """
        INSERT INTO course_session_hours (course_id, session_type, duration_minutes, duration_hours, duration_label, source)
        VALUES (:course_id, :session_type, :duration_minutes, :duration_hours, :duration_label, :source)
        ON DUPLICATE KEY UPDATE
            duration_minutes = VALUES(duration_minutes),
            duration_hours = VALUES(duration_hours),
            duration_label = VALUES(duration_label),
            source = VALUES(source),
            updated_at = CURRENT_TIMESTAMP
        """
    )

    with engine.begin() as connection:
        for params in records:
            connection.execute(insert_stmt, params)

    operations = len(records)
    return operations, operations, payload


def main() -> None:
    if not INPUT_EXCEL.exists():
        raise SystemExit(f"No se encontró el archivo Excel esperado en {INPUT_EXCEL}")

    ensure_table_exists()

    alias_map = load_mapping()
    excel_durations = build_excel_durations()
    apply_manual_overrides(excel_durations)
    mapped_sessions = map_to_db_courses(excel_durations, alias_map)
    courses_index = load_courses_by_name()
    inserted, updated, snapshot = upsert_course_hours(mapped_sessions, courses_index)

    print(f"Cursos con horas actualizados: {len(snapshot)}")
    print(f"Registros insertados/actualizados: {updated}")
    for course_name in sorted(snapshot):
        entries = snapshot[course_name]
        summary = ", ".join(
            f"{session_type}: {entry['label']} ({entry['source']})"
            for session_type, entry in sorted(entries.items())
        )
        print(f"  - {course_name}: {summary}")


if __name__ == "__main__":
    main()
