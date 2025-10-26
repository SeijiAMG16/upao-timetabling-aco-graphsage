import sys
from pathlib import Path
import argparse

root = Path(__file__).resolve().parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from app.database import SessionLocal
from app.aco_graphsage.pipeline import TimetablePipeline
from app.aco_graphsage.config import ACO_PARAMS, LOCAL_SEARCH_PARAMS


def main():
    parser = argparse.ArgumentParser(description="Ejecuta una corrida controlada del pipeline ACO+GraphSAGE")
    parser.add_argument("--ants", type=int, default=6, help="Número de hormigas por iteración")
    parser.add_argument("--iters", type=int, default=8, help="Número de iteraciones de ACO")
    parser.add_argument("--candidates", type=int, default=450, help="Máximo de combinaciones por sección")
    parser.add_argument("--steps", type=int, default=200, help="Pasos de búsqueda local")
    parser.add_argument(
        "--debug-sections",
        type=str,
        default="",
        help="IDs de secciones a depurar, separados por coma",
    )
    args = parser.parse_args()

    session = SessionLocal()
    try:
        session.bind.engine.echo = False
    except Exception:
        pass

    pipeline = TimetablePipeline(session, use_pretrained=False)
    pipeline.prepare()

    aco_params = dict(ACO_PARAMS)
    aco_params.update({
        "n_hormigas": max(1, args.ants),
        "n_iteraciones": max(1, args.iters),
        "max_candidate_combinations": max(1, args.candidates),
        "shuffle_candidates": True,
    })

    if args.debug_sections:
        debug_ids = []
        for token in args.debug_sections.split(','):
            token = token.strip()
            if not token:
                continue
            try:
                debug_ids.append(int(token))
            except ValueError:
                print(f"⚠️  Ignorando identificador de debug inválido: '{token}'")
        aco_params["debug_sections"] = debug_ids
    else:
        aco_params["debug_sections"] = []

    local_params = dict(LOCAL_SEARCH_PARAMS)
    local_params.update({
        "max_steps": max(10, args.steps),
        "max_iterations": max(local_params.get("max_iterations", 1000), args.steps),
        "initial_temperature": 2.0,
    })

    solution, metrics = pipeline.generate_schedule(
        aco_params=aco_params,
        local_search_params=local_params,
        save_to_db=False,
    )

    if solution is None:
        print("Sin solución válida para la configuración solicitada")
        return 1

    print("=== RESUMEN CORRIDA ===")
    print(f"Asignaciones generadas: {len(solution.assignments)}")
    print(f"Costo final: {solution.total_cost:.2f}")
    validacion = metrics.get("validacion_restricciones", {})
    print(f"Restricciones duras OK: {validacion.get('restricciones_duras_ok')}")
    print(f"Violaciones registradas: {len(validacion.get('violaciones', []))}")
    print(f"Penalización total estimada: {metrics.get('total_cost', 0.0):.2f}")

    soft = metrics.get("soft_penalties", {})
    if soft:
        top_soft = sorted(soft.items(), key=lambda item: item[1], reverse=True)[:10]
        print("Top penalizaciones blandas:")
        for name, value in top_soft:
            print(f"  - {name}: {value:.2f}")

    print("\nMuestra de 5 asignaciones:")
    for row in solution.assignments[:5]:
        print(
            f"  Sección {row.section_id} | Curso {row.course_code} | Tipo {row.session_type} | "
            f"Liga {row.league_id} | Prof {row.professor_id} | Aula {row.classroom_id} | Slots {row.timeslot_ids}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
