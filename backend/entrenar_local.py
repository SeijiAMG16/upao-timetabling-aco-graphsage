"""
Entrenamiento Local por Chunks - ACO+GraphSAGE UPAO
====================================================
Entrena el modelo GraphSAGE en sesiones cortas (chunks) que puedes
detener y reanudar sin perder progreso.

Meta: ≥95% cobertura de secciones, 0 hard violations.

Uso:
    # Primera vez (inicia desde cero):
    python entrenar_local.py

    # Reanudar desde último checkpoint:
    python entrenar_local.py --resume

    # Forzar modo de recurso específico:
    python entrenar_local.py --mode safe_lite
    python entrenar_local.py --mode lite
    python entrenar_local.py --resume --mode lite

    # Ver estadísticas del progreso actual:
    python entrenar_local.py --stats
"""

import argparse
import gc
import json
import sys
import time
from pathlib import Path

# ── Asegurar que se ejecuta desde /backend ─────────────────────────────────────
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

import torch
from app.database import SessionLocal
from app.aco_graphsage.config import TRAINING_PARAMS
from app.aco_graphsage.pipeline import TimetablePipeline
from app.aco_graphsage.graphsage_model import load_model, save_model, create_model_from_graph

# ── Configuración de rutas ─────────────────────────────────────────────────────
SAVE_DIR = ROOT / "models" / "entrenamiento_local"
PROGRESS_FILE = SAVE_DIR / "progreso.json"
BEST_MODEL_PATH = SAVE_DIR / "mejor_modelo.pt"

# ── Parámetros por modo de recurso ─────────────────────────────────────────────
RESOURCE_MODES = {
    "safe_lite": {
        "description": "Laptops con <8GB RAM libre. Lento pero estable.",
        "n_episodes_per_chunk": 10,   # episodios por sesión
        "resource_mode": "safe_lite",
        "torch_num_threads": 2,
        "batch_size": 8,
        "n_episodes": 150,
    },
    "lite": {
        "description": "Laptops con 8-12GB RAM libre. Balance velocidad/memoria.",
        "n_episodes_per_chunk": 20,
        "resource_mode": "lite",
        "torch_num_threads": 2,
        "batch_size": 16,
        "n_episodes": 150,
    },
    "balanced": {
        "description": "Máquinas con >12GB RAM. Puede saturar laptops.",
        "n_episodes_per_chunk": 50,
        "resource_mode": "balanced",
        "torch_num_threads": 4,
        "batch_size": 32,
        "n_episodes": 200,
    },
}


def load_progress() -> dict:
    """Carga el progreso guardado, o devuelve estado inicial."""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "total_episodes_done": 0,
        "best_coverage": 0.0,
        "best_hard_violations": 999,
        "best_objective": float("inf"),
        "best_model_path": None,
        "chunks_completed": 0,
        "history": [],
    }


def save_progress(progress: dict):
    """Guarda el estado del progreso."""
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, indent=2, ensure_ascii=False)


def print_stats(progress: dict):
    """Imprime estadísticas del progreso actual."""
    print("\n" + "=" * 70)
    print("📊 ESTADÍSTICAS DEL ENTRENAMIENTO LOCAL")
    print("=" * 70)
    print(f"  Episodios completados : {progress['total_episodes_done']}")
    print(f"  Chunks completados    : {progress['chunks_completed']}")
    print(f"  Mejor cobertura       : {progress['best_coverage']*100:.1f}%")
    print(f"  Mejor hard violations : {progress['best_hard_violations']}")
    print(f"  Mejor objetivo        : {progress['best_objective']:.2f}")
    if progress.get("best_model_path"):
        print(f"  Mejor modelo en       : {progress['best_model_path']}")
    if progress.get("history"):
        print(f"\n  Últimos {min(5, len(progress['history']))} episodios:")
        for ep in progress["history"][-5:]:
            feasible = "✅" if ep["hard_violations"] == 0 else "❌"
            print(
                f"    Ep.{ep['episode']:>4} | {feasible} cov={ep['coverage']*100:.1f}% "
                f"hard={ep['hard_violations']} obj={ep['objective']:.0f}"
            )
    print("=" * 70 + "\n")


def run_chunk(
    mode_cfg: dict,
    progress: dict,
    resume_model_path: str | None,
    n_episodes_this_chunk: int,
) -> dict:
    """
    Ejecuta un chunk de episodios de entrenamiento.

    Returns: progreso actualizado
    """
    db = SessionLocal()
    try:
        # Construir pipeline y grafo
        print("\n📐 Construyendo grafo desde base de datos...")
        pipeline = TimetablePipeline(
            db_session=db,
            model_path=resume_model_path,
            use_pretrained=resume_model_path is not None,
        )
        pipeline.prepare()

        # Ajustar parámetros del trainer para este chunk
        from app.aco_graphsage.trainer import create_trainer
        from app.aco_graphsage.config import ACO_PARAMS

        chunk_params = dict(TRAINING_PARAMS)
        chunk_params.update({
            "resource_mode": mode_cfg["resource_mode"],
            "torch_num_threads": mode_cfg["torch_num_threads"],
            "batch_size": mode_cfg["batch_size"],
            "n_episodes": n_episodes_this_chunk,
            # Early stopping más corto dentro del chunk
            "patience": min(20, n_episodes_this_chunk // 2),
            "save_every": max(5, n_episodes_this_chunk // 4),
            "eval_every": max(5, n_episodes_this_chunk // 5),
        })

        def aco_factory(model):
            from app.aco_graphsage.aco_engine import create_aco_engine
            return create_aco_engine(
                graph=pipeline.graph,
                model=model,
                graph_builder=pipeline.graph_builder,
                db_session=db,
            )

        chunk_save_dir = SAVE_DIR / f"chunk_{progress['chunks_completed'] + 1:03d}"

        trainer = create_trainer(
            model=pipeline.model,
            graph=pipeline.graph,
            aco_engine_factory=aco_factory,
            evaluator=pipeline.evaluator,
            mode="reinforcement",
            params=chunk_params,
        )

        # Entrenar chunk
        t_start = time.time()
        trained_model = trainer.train(save_dir=str(chunk_save_dir))
        elapsed = time.time() - t_start

        # Extraer métricas del chunk
        ep_offset = progress["total_episodes_done"]
        n_done = len(trainer.episode_costs)
        best_cov = max(trainer.episode_coverages) if trainer.episode_coverages else 0.0
        best_hard = min(trainer.episode_hard_violations) if trainer.episode_hard_violations else 999

        # Actualizar progreso global
        progress["total_episodes_done"] += n_done
        progress["chunks_completed"] += 1

        # Guardar mejor modelo global si este chunk mejoró
        if trainer.best_metrics is not None:
            chunk_cov = trainer.best_metrics["coverage"]
            chunk_hard = trainer.best_metrics["hard_violations"]
            chunk_obj = trainer.best_metrics["training_objective"]

            curr_sig = (progress["best_hard_violations"], -progress["best_coverage"])
            new_sig = (chunk_hard, -chunk_cov)

            if new_sig < curr_sig or (
                new_sig == curr_sig and chunk_obj < progress["best_objective"]
            ):
                progress["best_coverage"] = chunk_cov
                progress["best_hard_violations"] = chunk_hard
                progress["best_objective"] = chunk_obj
                save_model(trained_model, str(BEST_MODEL_PATH))
                progress["best_model_path"] = str(BEST_MODEL_PATH)
                print(f"\n🏆 Nuevo mejor modelo global: cov={chunk_cov*100:.1f}% hard={chunk_hard}")

        # Guardar historial de episodios
        for i in range(n_done):
            progress["history"].append({
                "episode": ep_offset + i + 1,
                "chunk": progress["chunks_completed"],
                "coverage": trainer.episode_coverages[i] if i < len(trainer.episode_coverages) else 0,
                "hard_violations": trainer.episode_hard_violations[i] if i < len(trainer.episode_hard_violations) else 0,
                "objective": trainer.episode_training_objective[i] if i < len(trainer.episode_training_objective) else 0,
                "strict_feasible": trainer.episode_strict_feasible[i] if i < len(trainer.episode_strict_feasible) else False,
            })

        print(f"\n⏱️  Chunk completado en {elapsed:.1f}s ({elapsed/max(1,n_done):.1f}s/episodio)")
        print(f"   Mejor cobertura en chunk: {best_cov*100:.1f}%")
        print(f"   Mínimos hard violations:  {best_hard}")

        return progress

    finally:
        db.close()
        gc.collect()


def main():
    parser = argparse.ArgumentParser(description="Entrenamiento local por chunks")
    parser.add_argument("--resume", action="store_true", help="Reanudar desde último checkpoint")
    parser.add_argument("--mode", default="safe_lite", choices=list(RESOURCE_MODES.keys()),
                        help="Perfil de recursos (default: safe_lite)")
    parser.add_argument("--stats", action="store_true", help="Mostrar estadísticas y salir")
    parser.add_argument("--chunks", type=int, default=1,
                        help="Número de chunks a ejecutar en esta sesión (default: 1)")
    args = parser.parse_args()

    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    progress = load_progress()

    if args.stats:
        print_stats(progress)
        return

    mode_cfg = RESOURCE_MODES[args.mode]
    print("\n" + "=" * 70)
    print(f"🚀 ENTRENAMIENTO LOCAL ACO+GraphSAGE")
    print("=" * 70)
    print(f"  Modo          : {args.mode} — {mode_cfg['description']}")
    print(f"  Resume        : {'Sí' if args.resume else 'No (inicio desde cero)'}")
    print(f"  Chunks sesión : {args.chunks}")
    print(f"  Eps/chunk     : {mode_cfg['n_episodes_per_chunk']}")
    print(f"  Total previo  : {progress['total_episodes_done']} episodios")
    print("=" * 70)

    # Determinar modelo de inicio
    resume_model_path = None
    if args.resume and progress.get("best_model_path") and Path(progress["best_model_path"]).exists():
        resume_model_path = progress["best_model_path"]
        print(f"\n📂 Reanudando desde: {resume_model_path}")
        print(f"   Mejor cobertura previa: {progress['best_coverage']*100:.1f}%")
    elif args.resume:
        print("\n⚠️  No se encontró checkpoint previo, iniciando desde cero.")

    # Ejecutar chunks
    for chunk_i in range(args.chunks):
        print(f"\n{'─'*70}")
        print(f"🔁 CHUNK {chunk_i + 1}/{args.chunks} (chunk global #{progress['chunks_completed'] + 1})")
        print(f"{'─'*70}")

        try:
            progress = run_chunk(
                mode_cfg=mode_cfg,
                progress=progress,
                resume_model_path=resume_model_path,
                n_episodes_this_chunk=mode_cfg["n_episodes_per_chunk"],
            )
            save_progress(progress)

            # Para el siguiente chunk, usar el mejor modelo global
            if progress.get("best_model_path"):
                resume_model_path = progress["best_model_path"]

            # Verificar si ya alcanzamos la meta
            if (
                progress["best_coverage"] >= 0.95
                and progress["best_hard_violations"] == 0
            ):
                print("\n🎯 ¡META ALCANZADA! ≥95% cobertura y 0 hard violations.")
                break

        except KeyboardInterrupt:
            print("\n\n⏹️  Entrenamiento interrumpido por usuario. Guardando progreso...")
            save_progress(progress)
            break
        except Exception as e:
            print(f"\n❌ Error en chunk {chunk_i + 1}: {e}")
            save_progress(progress)
            raise

    print_stats(progress)
    print(f"\n✅ Sesión terminada. Para continuar:")
    print(f"   python entrenar_local.py --resume --mode {args.mode} --chunks {args.chunks}")


if __name__ == "__main__":
    main()
