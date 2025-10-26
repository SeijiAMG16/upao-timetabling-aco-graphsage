from app.database import SessionLocal
from app.aco_graphsage.graph_builder import TimetableGraphBuilder
from app.aco_graphsage.graphsage_model import create_model_from_graph
from app.aco_graphsage.aco_engine import create_aco_engine


def main():
    session = SessionLocal()
    builder = TimetableGraphBuilder(session)
    graph = builder.build_graph()
    model = create_model_from_graph(graph)
    model.eval()
    engine = create_aco_engine(
        graph,
        model,
        builder,
        db_session=session,
        params={"n_hormigas": 1, "n_iteraciones": 1},
    )

    solution = engine._construct_solution(0, 0)
    print("valid solution?", solution.is_valid)
    print("assigned sections:", [a.section_id for a in solution.assignments])

    current_schedule = solution.assignments
    sec_id = 1572
    candidates = engine._get_candidate_assignments(sec_id)
    sec_idx = builder.section_id_to_idx[sec_id]
    prof_edges = graph[('section', 'assigned_to', 'professor')].edge_index
    classroom_edges = graph[('section', 'uses', 'classroom')].edge_index
    timeslot_edges = graph[('section', 'starts_at', 'timeslot')].edge_index
    prof_candidates = prof_edges[1][prof_edges[0] == sec_idx]
    classroom_candidates = classroom_edges[1][classroom_edges[0] == sec_idx]
    timeslot_candidates = timeslot_edges[1][timeslot_edges[0] == sec_idx]
    print(
        "candidate pool sizes:",
        {
            "professors": len(prof_candidates),
            "classrooms": len(classroom_candidates),
            "timeslots": len(timeslot_candidates),
        },
    )
    print(f"total candidates: {len(candidates)}")
    valids = []
    reasons = {}

    for cand in candidates:
        assignment = engine._build_assignment_object(sec_id, *cand)
        result = engine.hard_validator.validate_all(assignment, current_schedule, return_details=True)
        ok, msg, detail = result
        if ok:
            valids.append((cand, tuple(assignment.timeslot_ids)))
        else:
            reasons.setdefault(msg, []).append((cand, tuple(assignment.timeslot_ids), detail))

    print(f"valid count with current schedule: {len(valids)}")
    if valids:
        print("sample valid candidate:", valids[0])
    print("rejection reasons:")
    for msg, items in reasons.items():
        print(f"  {msg}: {len(items)} combos")
        sample_cand, sample_slots, detail = items[0]
        print("    sample:", sample_cand, sample_slots)
        print("    detail:", detail)

    session.close()


if __name__ == "__main__":
    main()
