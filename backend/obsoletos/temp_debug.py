import random

import numpy as np
import torch
from app.database import SessionLocal
from app.aco_graphsage.pipeline import TimetablePipeline
from app.aco_graphsage.aco_engine import create_aco_engine
from pprint import pprint


torch.manual_seed(42)
np.random.seed(42)
random.seed(42)


def main():
    session = SessionLocal()
    try:
        pipeline = TimetablePipeline(session)
        pipeline.prepare()
        pipeline.model.eval()

        params = {
            "n_hormigas": 1,
            "n_iteraciones": 1,
            "alpha": 1.0,
            "beta": 3.0,
            "rho": 0.1,
            "q0": 0.9,
            "shuffle_candidates": False,
            "max_timeslots_per_section": 48,
            "max_candidate_combinations": 1200,
            "max_professors_per_section": 50,
            "max_classrooms_per_section": 50,
            "debug_sections": [1563, 1564, 1565, 1590, 1632, 1598, 1631, 1683],
        }

        engine = create_aco_engine(
            graph=pipeline.graph,
            model=pipeline.model,
            graph_builder=pipeline.graph_builder,
            db_session=session,
            params=params,
        )

        solution = engine._construct_solution(0, 0)

        print("Solution valid:", solution.is_valid)
        print("Assignments count:", len(solution.assignments))
        print("Last log entries:")
        for line in solution.construction_log[-20:]:
            print(line)

        ts_info = engine.hard_validator.timeslots

        def describe_assignment(assign):
            slots = [ts_info[tid] for tid in assign.timeslot_ids]
            return {
                "section_id": assign.section_id,
                "course": assign.course_code,
                "session_type": assign.session_type,
                "league": assign.league_id,
                "times": [
                    {
                        "slot_id": ts.id,
                        "day": ts.dia_semana,
                        "orden": ts.orden,
                        "start": ts.hora_inicio.strftime("%H:%M"),
                        "end": ts.hora_fin.strftime("%H:%M"),
                    }
                    for ts in slots
                ],
            }

        filtered = [
            a for a in solution.assignments
            if (a.ciclo == 2 or str(a.ciclo) == "2") and a.league_id == 1
        ]

        print("Filtered assignments (ciclo 2, liga 1):", len(filtered))
        for assign in filtered:
            pprint(describe_assignment(assign))
    finally:
        session.close()


if __name__ == "__main__":
    main()
