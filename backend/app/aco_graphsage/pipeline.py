"""
Pipeline Completo ACO+GraphSAGE

Orquesta las 3 fases del sistema:
1. Neural-Augmented Construction (ACO con GraphSAGE)
2. Local Search (refinamiento)
3. Offline Training (REINFORCE - opcional)

Este es el punto de entrada principal del sistema.
"""

import time
from typing import Dict, Optional, Tuple
from pathlib import Path
from sqlalchemy.orm import Session
import torch

from .config import ACO_PARAMS, LOCAL_SEARCH_PARAMS, TRAINING_PARAMS
from .graph_builder import TimetableGraphBuilder
from .graphsage_model import (
    create_model_from_graph,
    load_model,
    ACOGraphSAGEModel,
)
from .aco_engine import create_aco_engine, Solution
from .local_search import create_local_search
from .trainer import create_trainer
from .evaluator import (
    SolutionEvaluator,
    save_execution_to_db,
    save_solution_to_db,
)
from .constraints import TimeSlotInfo, ClassroomInfo


# ============================================================================
# PIPELINE PRINCIPAL
# ============================================================================

class TimetablePipeline:
    """Pipeline completo para generación automática de horarios"""
    
    def __init__(
        self,
        db_session: Session,
        model_path: Optional[str] = None,
        use_pretrained: bool = False,
    ):
        """
        Inicializa el pipeline.
        
        Args:
            db_session: Sesión de base de datos
            model_path: Ruta a modelo preentrenado (opcional)
            use_pretrained: Si usar modelo preentrenado o inicializar nuevo
        """
        self.db = db_session
        self.model_path = model_path
        self.use_pretrained = use_pretrained
        
        # Componentes (se inicializan en prepare())
        self.graph_builder: Optional[TimetableGraphBuilder] = None
        self.graph = None
        self.model: Optional[ACOGraphSAGEModel] = None
        self.evaluator: Optional[SolutionEvaluator] = None
        
        print(f"\n{'='*80}")
        print(f"Pipeline ACO+GraphSAGE inicializado")
        print(f"Base de datos: {db_session.bind.engine.url.database}")
        print(f"Modelo preentrenado: {'Sí' if use_pretrained else 'No'}")
        print(f"{'='*80}\n")
    
    def prepare(self):
        """
        Prepara todos los componentes del pipeline.
        
        1. Construye el grafo desde la BD
        2. Crea o carga el modelo GraphSAGE
        3. Inicializa evaluadores
        """
        print("📊 Preparando componentes del pipeline...")
        
        # 1. Construir grafo
        print("\n1️⃣ Construyendo grafo heterogéneo desde BD...")
        self.graph_builder = TimetableGraphBuilder(self.db)
        self.graph = self.graph_builder.build_graph()
        
        # 2. Crear o cargar modelo
        print("\n2️⃣ Inicializando modelo GraphSAGE...")
        if self.use_pretrained and self.model_path and Path(self.model_path).exists():
            print(f"   Cargando modelo desde: {self.model_path}")
            node_features_dict = {
                node_type: features.size(1)
                for node_type, features in self.graph.x_dict.items()
            }
            self.model = load_model(
                self.model_path,
                node_features_dict,
                self.graph.metadata(),
            )
        else:
            print(f"   Creando modelo nuevo")
            self.model = create_model_from_graph(self.graph)
        
        # 3. Crear evaluador
        print("\n3️⃣ Inicializando evaluador...")
        from app.models import TimeSlot, Classroom
        
        timeslots_db = self.db.query(TimeSlot).all()
        classrooms_db = self.db.query(Classroom).all()
        
        timeslots = {
            ts.id: TimeSlotInfo(
                id=ts.id,
                dia_semana=ts.dia_semana,
                hora_inicio=ts.hora_inicio,
                hora_fin=ts.hora_fin,
                orden=ts.orden,
                periodo=ts.periodo,
            )
            for ts in timeslots_db
        }
        
        classrooms = {
            c.id: ClassroomInfo(
                id=c.id,
                codigo=c.codigo,
                capacidad=c.capacidad,
                tipo=c.tipo,
                edificio=c.edificio,
                tiene_computadoras=c.tiene_computadoras,
            )
            for c in classrooms_db
        }
        
        self.evaluator = SolutionEvaluator(timeslots, classrooms)
        
        print("\n✅ Preparación completada\n")
    
    def generate_schedule(
        self,
        aco_params: Dict = None,
        local_search_params: Dict = None,
        save_to_db: bool = True,
    ) -> Tuple[Solution, Dict]:
        """
        Genera un horario completo usando las 2 primeras fases.
        
        Fases:
        1. Construcción con ACO+GraphSAGE
        2. Refinamiento con búsqueda local
        
        Args:
            aco_params: Parámetros ACO (opcional)
            local_search_params: Parámetros búsqueda local (opcional)
            save_to_db: Si guardar resultados en BD
        
        Returns:
            (solution, metrics)
        """
        if self.graph is None or self.model is None:
            raise RuntimeError("Pipeline no preparado. Ejecutar prepare() primero.")
        
        start_time = time.time()
        
        # ====================================================================
        # FASE 1: Neural-Augmented Construction
        # ====================================================================
        print(f"\n{'='*80}")
        print(f"FASE 1: Neural-Augmented Construction (ACO+GraphSAGE)")
        print(f"{'='*80}\n")
        
        aco_engine = create_aco_engine(
            graph=self.graph,
            model=self.model,
            graph_builder=self.graph_builder,
            db_session=self.db,
            params=aco_params,
        )
        
        solution_aco = aco_engine.optimize()
        
        print(f"\n✅ Fase 1 completada")
        if solution_aco is not None:
            print(f"   Costo ACO: {solution_aco.total_cost:.2f}")
            print(f"   Solución válida: {'Sí' if solution_aco.is_valid else 'No'}")
        else:
            print(f"   ⚠️  No se encontró solución en ACO")
            return None, {}
        
        # ====================================================================
        # FASE 2: Local Search
        # ====================================================================
        print(f"\n{'='*80}")
        print(f"FASE 2: Local Search (refinamiento)")
        print(f"{'='*80}\n")
        
        local_search = create_local_search(
            algorithm=local_search_params.get('algorithm', 'simulated_annealing') if local_search_params else 'simulated_annealing',
            hard_validator=aco_engine.hard_validator,
            soft_evaluator=aco_engine.soft_evaluator,
            params=local_search_params,
        )
        
        solution_refined = local_search.optimize(solution_aco)
        
        print(f"\n✅ Fase 2 completada")
        print(f"   Costo refinado: {solution_refined.total_cost:.2f}")
        print(f"   Mejora: {solution_aco.total_cost - solution_refined.total_cost:.2f}")

        print("\n🔍 Validando restricciones duras post-ejecución...")
        schedule_valid, validation_violations = aco_engine.hard_validator.validate_schedule(
            solution_refined.assignments
        )
        solution_refined.is_valid = schedule_valid

        if schedule_valid:
            print("   ✅ Validación completada sin violaciones duras")
        else:
            print("   ❌ Se encontraron violaciones duras en la solución final")
            for idx, violation in enumerate(validation_violations, start=1):
                base_msg = (f"      {idx}. Sección {violation.get('section_id')} "
                            f"({violation.get('course_code', 'sin-curso')}) - "
                            f"{violation.get('mensaje')}")
                conflict_id = violation.get('conflict_section_id')
                if conflict_id is not None:
                    base_msg += f" | Conflicto con sección {conflict_id}"
                print(base_msg)
            print("   ➜ Revise los detalles en metrics['validacion_restricciones'] para depurar")
        
        # ====================================================================
        # Evaluación final
        # ====================================================================
        execution_time = time.time() - start_time
        
        print(f"\n{'='*80}")
        print(f"EVALUACIÓN FINAL")
        print(f"{'='*80}\n")
        
        metrics = self.evaluator.evaluate(solution_refined)
        metrics['validacion_restricciones'] = {
            'restricciones_duras_ok': schedule_valid,
            'violaciones': validation_violations,
        }
        metrics['tiempo_ejecucion'] = execution_time
        
        if metrics.get('is_valid'):
            report = self.evaluator.generate_report(metrics)
            print(report)
        else:
            print("⚠️ La solución final no es válida según las restricciones duras. Reporte resumido:")
            print(f"   - Asignaciones generadas: {metrics.get('n_assignments', 0)}")
            print(f"   - Costo total estimado: {metrics.get('total_cost', 0.0):.2f}")
        
        # ====================================================================
        # Guardar en BD
        # ====================================================================
        if save_to_db:
            print("\n💾 Guardando resultados en base de datos...")
            
            params_used = {
                'aco': aco_params or ACO_PARAMS,
                'local_search': local_search_params or LOCAL_SEARCH_PARAMS,
            }
            
            execution_id = save_execution_to_db(
                db_session=self.db,
                metrics=metrics,
                parameters=params_used,
                execution_time=execution_time,
                status="completed",
            )
            
            save_solution_to_db(
                db_session=self.db,
                solution=solution_refined,
                execution_id=execution_id,
            )
            
            print(f"✅ Resultados guardados (execution_id={execution_id})")
        
        return solution_refined, metrics
    
    def train_model(
        self,
        n_episodes: int = None,
        save_dir: str = "models/checkpoints",
    ) -> ACOGraphSAGEModel:
        """
        Entrena el modelo GraphSAGE usando REINFORCE.
        
        FASE 3: Offline Training
        
        Args:
            n_episodes: Número de episodios (opcional)
            save_dir: Directorio para checkpoints
        
        Returns:
            Modelo entrenado
        """
        if self.graph is None or self.model is None:
            raise RuntimeError("Pipeline no preparado. Ejecutar prepare() primero.")
        
        print(f"\n{'='*80}")
        print(f"FASE 3: Offline Training (REINFORCE)")
        print(f"{'='*80}\n")
        
        # Factory para crear ACO engine
        def aco_factory(model):
            return create_aco_engine(
                graph=self.graph,
                model=model,
                graph_builder=self.graph_builder,
                db_session=self.db,
            )
        
        # Crear trainer
        trainer = create_trainer(
            model=self.model,
            graph=self.graph,
            aco_engine_factory=aco_factory,
            evaluator=self.evaluator,
            mode="reinforcement",
        )
        
        # Modificar n_episodes si se especifica
        if n_episodes is not None:
            trainer.n_episodes = n_episodes
        
        # Entrenar
        trained_model = trainer.train(save_dir=save_dir)
        
        self.model = trained_model
        
        print(f"\n✅ Entrenamiento completado")
        print(f"   Mejor costo alcanzado: {trainer.best_cost:.2f}")
        
        return trained_model
    
    def run_full_pipeline(
        self,
        aco_params: Dict = None,
        local_search_params: Dict = None,
        training_episodes: int = None,
        save_to_db: bool = True,
    ) -> Tuple[Solution, Dict, ACOGraphSAGEModel]:
        """
        Ejecuta el pipeline completo de 3 fases.
        
        1. Construcción (ACO+GraphSAGE)
        2. Refinamiento (Local Search)
        3. Entrenamiento (REINFORCE)
        
        Returns:
            (solution, metrics, trained_model)
        """
        # Preparar componentes
        self.prepare()
        
        # Fase 1 y 2: Generar horario
        solution, metrics = self.generate_schedule(
            aco_params=aco_params,
            local_search_params=local_search_params,
            save_to_db=save_to_db,
        )
        
        # Fase 3: Entrenar modelo (opcional)
        trained_model = None
        if training_episodes and training_episodes > 0:
            trained_model = self.train_model(n_episodes=training_episodes)
        
        return solution, metrics, trained_model


# ============================================================================
# FUNCIÓN DE CONVENIENCIA
# ============================================================================

def generate_timetable(
    db_session: Session,
    model_path: Optional[str] = None,
    use_pretrained: bool = False,
    aco_iterations: int = None,
    save_to_db: bool = True,
) -> Tuple[Solution, Dict]:
    """
    Función de conveniencia para generar un horario completo.
    
    Args:
        db_session: Sesión de BD
        model_path: Ruta a modelo preentrenado
        use_pretrained: Si usar modelo preentrenado
        aco_iterations: Número de iteraciones ACO (override)
        save_to_db: Si guardar en BD
    
    Returns:
        (solution, metrics)
    """
    pipeline = TimetablePipeline(
        db_session=db_session,
        model_path=model_path,
        use_pretrained=use_pretrained,
    )
    
    aco_params = None
    if aco_iterations is not None:
        aco_params = ACO_PARAMS.copy()
        aco_params['n_iteraciones'] = aco_iterations
    
    solution, metrics = pipeline.generate_schedule(
        aco_params=aco_params,
        save_to_db=save_to_db,
    )
    
    return solution, metrics


def train_model_from_scratch(
    db_session: Session,
    n_episodes: int = 500,
    save_dir: str = "models/checkpoints",
) -> ACOGraphSAGEModel:
    """
    Entrena un modelo GraphSAGE desde cero.
    
    Args:
        db_session: Sesión de BD
        n_episodes: Episodios de entrenamiento
        save_dir: Directorio para guardar modelo
    
    Returns:
        Modelo entrenado
    """
    pipeline = TimetablePipeline(db_session=db_session)
    pipeline.prepare()
    
    trained_model = pipeline.train_model(
        n_episodes=n_episodes,
        save_dir=save_dir,
    )
    
    return trained_model
