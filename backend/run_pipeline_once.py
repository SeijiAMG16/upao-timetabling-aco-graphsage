from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent))

from app.database import SessionLocal
from app.aco_graphsage.pipeline import TimetablePipeline

ACO_PARAMS = {
    "n_iteraciones": 60,
    "n_hormigas": 35,
}

LOCAL_PARAMS = {
    "algorithm": "simulated_annealing",
    "max_iterations": 1200,
}


def main() -> None:
    db = SessionLocal()
    try:
        pipeline = TimetablePipeline(db_session=db, use_pretrained=False)
        pipeline.prepare()
        solution, metrics = pipeline.generate_schedule(
            aco_params=ACO_PARAMS,
            local_search_params=LOCAL_PARAMS,
            save_to_db=True,
        )
        print("RESULTADO PIPELINE:")
        if solution is None:
            print("  Sin solución devuelta")
        else:
            print(f"  Costo: {solution.total_cost}")
            print(f"  Asignaciones: {len(solution.assignments)}")
            print(f"  Penalizaciones: {solution.soft_penalties}")
            print(f"  ¿Válida?: {solution.is_valid}")
        print(f"  Métricas: {metrics}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
