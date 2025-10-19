import json
import re
import sys
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent
REPO_DIR = ROOT_DIR.parent
BACKEND_DIR = ROOT_DIR
INPUTS_DIR = REPO_DIR / "inputs"
EXCEL_FILENAME = "Horario_Docentes(2025-20).xlsx"
MAPEO_MANUAL_PATH = ROOT_DIR / "mapeo_manual_cursos.json"
MAPEO_NOMBRES_PATH = ROOT_DIR / "mapeo_nombres_cursos.json"
OUTPUT_PATH = ROOT_DIR / "mapeo_cursos_sugerido.json"

sys.path.append(str(ROOT_DIR))

from app.database import SessionLocal  # type: ignore  # noqa: E402
from app.models import Course  # type: ignore  # noqa: E402


@dataclass
class CourseRecord:
    codigo: str
    nombre: str
    ciclo: int
    nombre_normalizado: str


@dataclass
class MappingSuggestion:
    excel_nombre_base: str
    excel_variantes: List[str]
    normalizado: str
    match_automatico: Optional[str]
    codigo_curso: Optional[str]
    tipo_coincidencia: Optional[str]
    candidatos: List[Tuple[str, str, float]]


def _fix_encoding(value: str) -> str:
    try:
        return value.encode("latin1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value


def _normalize_text(value: str) -> str:
    value = value.upper()
    value = value.replace("Ñ", "N")
    value = unicodedata.normalize("NFD", value)
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    value = value.replace("/", " ")
    value = re.sub(r"[^A-Z0-9 ]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _load_manual_maps() -> Dict[str, str]:
    manual: Dict[str, str] = {}

    if MAPEO_MANUAL_PATH.exists():
        manual_data = json.loads(MAPEO_MANUAL_PATH.read_text(encoding="utf-8"))
        for src, target in manual_data.get("mapeo_abreviaturas", {}).items():
            manual[_normalize_text(src)] = target.upper()

    if MAPEO_NOMBRES_PATH.exists():
        manual_nombres = json.loads(MAPEO_NOMBRES_PATH.read_text(encoding="utf-8"))
        for src, target in manual_nombres.get("mapeo_manual", {}).items():
            manual[_normalize_text(src)] = target.upper()

    return manual


def _extract_course_base(text: str) -> Optional[str]:
    text = _fix_encoding(text).strip()
    text = text.replace("\r", " ").replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    text = text.strip(" -")

    if not text:
        return None

    if "(" not in text or ")" not in text:
        return None

    if "(" in text:
        match = re.match(r"^(.*?)\(", text)
        if match:
            base = match.group(1).strip(" -")
            if base:
                return base

    return None


def _collect_excel_entries() -> Dict[str, Set[str]]:
    excel_path = INPUTS_DIR / EXCEL_FILENAME
    if not excel_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo de Excel en {excel_path}")

    excel = pd.ExcelFile(excel_path)
    grouped: Dict[str, Set[str]] = defaultdict(set)

    for sheet_name in excel.sheet_names:
        df = excel.parse(sheet_name=sheet_name, header=None, dtype=str)
        for value in df.values.flatten():
            if not isinstance(value, str):
                continue
            base = _extract_course_base(value)
            if base is None:
                continue
            normalizado = _normalize_text(base)
            if not normalizado:
                continue
            grouped[normalizado].add(base)

    return grouped


def _load_courses() -> List[CourseRecord]:
    session = SessionLocal()
    try:
        rows = session.query(Course).filter(Course.active.is_(True)).all()
        records: List[CourseRecord] = []
        for row in rows:
            records.append(
                CourseRecord(
                    codigo=row.codigo,
                    nombre=row.nombre,
                    ciclo=row.ciclo,
                    nombre_normalizado=_normalize_text(row.nombre),
                )
            )
        return records
    finally:
        session.close()


def _find_best_candidates(
    normalizado: str,
    courses: List[CourseRecord],
    limit: int = 5,
) -> List[Tuple[str, str, float]]:
    scored: List[Tuple[str, str, float]] = []
    for course in courses:
        score = SequenceMatcher(None, normalizado, course.nombre_normalizado).ratio()
        scored.append((course.codigo, course.nombre, score))
    scored.sort(key=lambda item: item[2], reverse=True)
    return scored[:limit]


def _resolve_match(
    normalizado: str,
    manual_map: Dict[str, str],
    courses: List[CourseRecord],
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    manual_target = manual_map.get(normalizado)
    if manual_target:
        for course in courses:
            if course.nombre == manual_target:
                return course.nombre, course.codigo, "manual"
            if _normalize_text(course.nombre) == _normalize_text(manual_target):
                return course.nombre, course.codigo, "manual-normalizado"

    for course in courses:
        if normalizado == course.nombre_normalizado:
            return course.nombre, course.codigo, "exacto"

    for course in courses:
        if normalizado in course.nombre_normalizado or course.nombre_normalizado in normalizado:
            return course.nombre, course.codigo, "contenida"

    return None, None, None


def generar_mapeo() -> Dict[str, List[MappingSuggestion]]:
    manual_map = _load_manual_maps()
    grouped_entries = _collect_excel_entries()
    courses = _load_courses()

    auto: List[MappingSuggestion] = []
    revisar: List[MappingSuggestion] = []

    for normalizado, variantes in sorted(grouped_entries.items()):
        match_nombre, match_codigo, match_tipo = _resolve_match(normalizado, manual_map, courses)
        candidatos = _find_best_candidates(normalizado, courses)

        if not match_nombre and candidatos:
            best_codigo, best_nombre, best_score = candidatos[0]
            if best_score >= 0.88:
                match_nombre = best_nombre
                match_codigo = best_codigo
                match_tipo = "heuristico"

        suggestion = MappingSuggestion(
            excel_nombre_base=next(iter(variantes)),
            excel_variantes=sorted(variantes),
            normalizado=normalizado,
            match_automatico=match_nombre,
            codigo_curso=match_codigo,
            tipo_coincidencia=match_tipo,
            candidatos=candidatos,
        )

        if match_nombre:
            auto.append(suggestion)
        else:
            revisar.append(suggestion)

    return {
        "auto": auto,
        "revisar": revisar,
    }


def exportar_resultados(resultados: Dict[str, List[MappingSuggestion]]) -> None:
    salida = {
        "generado_en": datetime.now().isoformat(timespec="seconds"),
        "archivo_excel": EXCEL_FILENAME,
        "auto": [asdict(item) for item in resultados["auto"]],
        "revisar": [asdict(item) for item in resultados["revisar"]],
    }
    OUTPUT_PATH.write_text(json.dumps(salida, indent=2, ensure_ascii=False), encoding="utf-8")


def imprimir_resumen(resultados: Dict[str, List[MappingSuggestion]]) -> None:
    print("\n=== COINCIDENCIAS AUTOMÁTICAS ===")
    for item in resultados["auto"]:
        print(f"- {item.excel_nombre_base} -> {item.match_automatico} ({item.codigo_curso}) [{item.tipo_coincidencia}]")

    print("\n=== REVISIÓN MANUAL REQUERIDA ===")
    for item in resultados["revisar"]:
        print(f"\n* {item.excel_nombre_base}")
        print(f"  - Normalizado: {item.normalizado}")
        print("  - Variantes:")
        for variante in item.excel_variantes:
            print(f"      · {variante}")
        print("  - Candidatos sugeridos:")
        for codigo, nombre, score in item.candidatos:
            print(f"      · {codigo}: {nombre} (score={score:.3f})")


def main() -> None:
    resultados = generar_mapeo()
    exportar_resultados(resultados)
    imprimir_resumen(resultados)


if __name__ == "__main__":
    main()
