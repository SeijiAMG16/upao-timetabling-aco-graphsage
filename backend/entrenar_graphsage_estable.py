from __future__ import annotations

import argparse
import json
import random
from datetime import datetime
from pathlib import Path

import numpy as np
import torch

from app.database import SessionLocal
from app.aco_graphsage.pipeline import TimetablePipeline
from app.aco_graphsage import config as cfg


def main() -> None:
    parser = argparse.ArgumentParser(description="Entrenamiento GraphSAGE estable (baja varianza)")
    parser.add_argument("--episodes", type=int, default=5)
    parser.add_argument("--aco-iterations", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--save-to-db", action="store_true")
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    cfg.TRAINING_PARAMS["resource_mode"] = "safe_lite"
    cfg.TRAINING_PARAMS["torch_num_threads"] = 2
    cfg.TRAINING_PARAMS["epsilon_start"] = 0.20
    cfg.TRAINING_PARAMS["epsilon_end"] = 0.05
    cfg.TRAINING_PARAMS["epsilon_decay"] = 0.995
    cfg.TRAINING_PARAMS["patience"] = 12
    cfg.TRAINING_PARAMS["min_improvement"] = 0.002
    cfg.TRAINING_PARAMS["soft_cost_weight"] = 0.01
    cfg.TRAINING_PARAMS["coverage_target_start"] = 0.85
    cfg.TRAINING_PARAMS["coverage_target_end"] = 0.95
    cfg.ACO_PARAMS["n_iteraciones"] = max(1, int(args.aco_iterations))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    checkpoints_dir = Path("models") / "checkpoints_estable" / f"run_{timestamp}"
    checkpoints_dir.mkdir(parents=True, exist_ok=True)

    db = SessionLocal()
    try:
        pipeline = TimetablePipeline(db_session=db, use_pretrained=False)
        pipeline.prepare()

        pipeline.train_model(n_episodes=args.episodes, save_dir=str(checkpoints_dir))
        solution, metrics = pipeline.generate_schedule(save_to_db=args.save_to_db)

        stats_path = checkpoints_dir / "training_stats.json"
        stats = {}
        if stats_path.exists():
            stats = json.loads(stats_path.read_text(encoding="utf-8"))

        report = {
            "timestamp": timestamp,
            "seed": args.seed,
            "episodes_requested": args.episodes,
            "checkpoints_dir": str(checkpoints_dir),
            "best_objective": stats.get("best_objective"),
            "best_signature": stats.get("best_signature"),
            "best_metrics": stats.get("best_metrics"),
            "episodes_executed": stats.get("n_episodes"),
            "final_epsilon": stats.get("final_epsilon"),
            "generated_solution": {
                "found": solution is not None,
                "is_valid": bool(metrics.get("is_valid", False)) if metrics else False,
                "n_assignments": int(metrics.get("n_assignments", 0)) if metrics else 0,
                "total_cost": float(metrics.get("total_cost", 0.0)) if metrics else 0.0,
                "tiempo_ejecucion": float(metrics.get("tiempo_ejecucion", 0.0)) if metrics else 0.0,
                "validacion_restricciones": metrics.get("validacion_restricciones", {}) if metrics else {},
            },
        }

        output_dir = Path("logs")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"entrenamiento_graphsage_estable_{timestamp}.json"
        output_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

        print("=" * 80)
        print("ENTRENAMIENTO GRAPHSAGE ESTABLE")
        print("=" * 80)
        print(f"Episodios solicitados: {args.episodes}")
        print(f"Iteraciones ACO: {cfg.ACO_PARAMS['n_iteraciones']}")
        print(f"Episodios ejecutados: {report['episodes_executed']}")
        print(f"Mejor objetivo: {report['best_objective']}")
        print(f"Solución válida: {report['generated_solution']['is_valid']}")
        print(f"Asignaciones: {report['generated_solution']['n_assignments']}")
        print(f"Reporte: {output_file}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
