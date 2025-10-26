"""Inspecciona las franjas candidatas por liga para un curso específico."""

import argparse

from app.database import SessionLocal
from app.aco_graphsage.graph_builder import TimetableGraphBuilder
from app.models import TimeSlot


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspecciona las secciones generadas por liga y sus franjas candidatas.",
        epilog="Ejemplo: python inspect_league_admi779.py --curso ADMI779 --liga 1 --tipo P",
    )
    parser.add_argument(
        "--curso",
        required=True,
        help="Código del curso (por ejemplo, ADMI779).",
    )
    parser.add_argument(
        "--liga",
        type=int,
        help="Liga específica a inspeccionar. Si se omite, se listan todas las ligas del curso.",
    )
    parser.add_argument(
        "--tipo",
        choices=["T", "P", "L"],
        help="Filtra por tipo de sesión (T, P o L).",
    )
    return parser.parse_args()


def build_timeslot_map(session) -> dict:
    return {ts.id: ts for ts in session.query(TimeSlot).all()}


def format_hora(value) -> str:
    return value.strftime("%H:%M") if hasattr(value, "strftime") else str(value)


def print_section_details(
    builder: TimetableGraphBuilder,
    timeslot_records: dict,
    section_id: int,
) -> None:
    meta = builder.section_metadata.get(section_id, {})
    stats = builder.section_candidate_stats.get(section_id, {})
    duration = builder.section_durations.get(section_id)
    section_idx = builder.section_id_to_idx.get(section_id)

    if section_idx is None:
        print(f"  ⚠️  Sección {section_id} no está indexada en el grafo.")
        return

    edge_index = builder.graph_data[("section", "starts_at", "timeslot")].edge_index
    candidate_indices = edge_index[1][edge_index[0] == section_idx].tolist()
    candidate_timeslot_ids = [builder.idx_to_timeslot_id[idx] for idx in candidate_indices]

    print(f"  Sección {section_id}:")
    print(f"    Metadata: {meta}")
    print(f"    Duración bloques: {duration}")
    print(
        "    Candidatos → Profesores: {prof} | Aulas: {room} | Franjas: {slot}".format(
            prof=stats.get("professors"),
            room=stats.get("classrooms"),
            slot=stats.get("timeslots"),
        )
    )
    print(f"    Franjas candidatas (IDs inicio): {sorted(candidate_timeslot_ids)}")

    if not candidate_timeslot_ids:
        return

    print("    Detalle de franjas:")
    for ts_id in sorted(candidate_timeslot_ids):
        ts = timeslot_records.get(ts_id)
        if not ts:
            continue
        print(
            "      - ID {id}: día={dia}, orden={orden}, {inicio} - {fin}".format(
                id=ts.id,
                dia=ts.dia_semana,
                orden=ts.orden,
                inicio=format_hora(ts.hora_inicio),
                fin=format_hora(ts.hora_fin),
            )
        )


def main():
    args = parse_args()
    session = SessionLocal()
    try:
        builder = TimetableGraphBuilder(session)
        builder.graph_data = builder.build_graph()

        selected_keys = [
            key
            for key in builder.sections_by_league.keys()
            if key[0] == args.curso
        ]

        if args.liga is not None:
            selected_keys = [key for key in selected_keys if key[1] == args.liga]

        if not selected_keys:
            print(f"No se encontraron ligas para el curso {args.curso} con los filtros dados.")
            return

        timeslot_records = build_timeslot_map(session)

        for league_key in sorted(selected_keys, key=lambda x: x[1]):
            sections = builder.sections_by_league.get(league_key, [])
            print(f"\nLiga {league_key}: {len(sections)} secciones registradas")

            if args.tipo:
                filtered_sections = [
                    sec
                    for sec in sections
                    if builder.section_metadata.get(sec, {}).get("session_type") == args.tipo
                ]
            else:
                filtered_sections = sections

            if not filtered_sections:
                print("  (Sin secciones que coincidan con el filtro de tipo)")
                continue

            for section_id in sorted(filtered_sections):
                print_section_details(builder, timeslot_records, section_id)
    finally:
        session.close()


if __name__ == "__main__":
    main()
