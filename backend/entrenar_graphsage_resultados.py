from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from app.database import SessionLocal
from app.aco_graphsage.pipeline import TimetablePipeline


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def main() -> None:
    parser = argparse.ArgumentParser(description="Entrena GraphSAGE y genera reporte de resultados")
    parser.add_argument("--episodes", type=int, default=20, help="Número de episodios REINFORCE")
    parser.add_argument("--save-to-db", action="store_true", help="Guardar horario generado en BD")
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    checkpoints_dir = Path("models") / "checkpoints" / f"run_{timestamp}"
    checkpoints_dir.mkdir(parents=True, exist_ok=True)

    db = SessionLocal()
    try:
        pipeline = TimetablePipeline(db_session=db, use_pretrained=False)
        pipeline.prepare()

        pipeline.train_model(n_episodes=args.episodes, save_dir=str(checkpoints_dir))

        solution, metrics = pipeline.generate_schedule(save_to_db=args.save_to_db)

        training_stats_path = checkpoints_dir / "training_stats.json"
        training_stats: Dict[str, Any] = {}
        if training_stats_path.exists():
            training_stats = json.loads(training_stats_path.read_text(encoding="utf-8"))

        report = {
            "timestamp": timestamp,
            "episodes_requested": args.episodes,
            "checkpoints_dir": str(checkpoints_dir),
            "training": {
                "episodes_executed": training_stats.get("n_episodes"),
                "best_objective": training_stats.get("best_objective"),
                "best_signature": training_stats.get("best_signature"),
                "best_metrics": training_stats.get("best_metrics"),
                "final_epsilon": training_stats.get("final_epsilon"),
            },
            "generation": {
                "solution_found": solution is not None,
                "total_cost": safe_float(metrics.get("total_cost")),
                "n_assignments": int(metrics.get("n_assignments", 0)) if metrics else 0,
                "is_valid": bool(metrics.get("is_valid", False)) if metrics else False,
                "tiempo_ejecucion": safe_float(metrics.get("tiempo_ejecucion", 0.0)) if metrics else 0.0,
                "validacion_restricciones": metrics.get("validacion_restricciones", {}) if metrics else {},
            },
            "save_to_db": bool(args.save_to_db),
        }

        output_dir = Path("logs")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"entrenamiento_graphsage_{timestamp}.json"
        output_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

        print("=" * 80)
        print("ENTRENAMIENTO GRAPHSAGE + EVALUACIÓN")
        print("=" * 80)
        print(f"Episodios solicitados: {args.episodes}")
        print(f"Episodios ejecutados: {report['training']['episodes_executed']}")
        print(f"Mejor objetivo: {report['training']['best_objective']}")
        print(f"Costo solución generada: {report['generation']['total_cost']:.2f}")
        print(f"Asignaciones: {report['generation']['n_assignments']}")
        print(f"Solución válida: {report['generation']['is_valid']}")
        print(f"Reporte: {output_file}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
