"""
Endpoints de API para Generación Automática de Horarios

Expone el pipeline ACO+GraphSAGE a través de FastAPI.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
import asyncio
from pathlib import Path

from app.database import get_db
from app.aco_graphsage import (
    TimetablePipeline,
    generate_timetable,
    ACO_PARAMS,
    LOCAL_SEARCH_PARAMS,
    TORCH_AVAILABLE,
)


router = APIRouter(prefix="/api/algorithm", tags=["Algorithm"])


# ============================================================================
# MODELOS PYDANTIC
# ============================================================================

class AlgorithmExecutionRequest(BaseModel):
    """Request para ejecutar el algoritmo"""
    aco_iterations: Optional[int] = Field(
        default=None,
        description="Número de iteraciones ACO (override)",
        ge=1,
        le=500,
    )
    n_hormigas: Optional[int] = Field(
        default=None,
        description="Número de hormigas por iteración",
        ge=1,
        le=200,
    )
    use_local_search: bool = Field(
        default=True,
        description="Si usar búsqueda local para refinamiento",
    )
    local_search_algorithm: str = Field(
        default="simulated_annealing",
        description="Algoritmo de búsqueda local",
    )
    use_pretrained_model: bool = Field(
        default=False,
        description="Si usar modelo GraphSAGE preentrenado",
    )
    model_path: Optional[str] = Field(
        default=None,
        description="Ruta al modelo preentrenado",
    )
    save_to_db: bool = Field(
        default=True,
        description="Si guardar resultados en BD",
    )


class AlgorithmExecutionResponse(BaseModel):
    """Response con información de ejecución"""
    execution_id: int
    status: str
    message: str
    started_at: datetime


class AlgorithmStatusResponse(BaseModel):
    """Response con estado de ejecución"""
    execution_id: int
    status: str
    progress: Optional[float] = None
    current_phase: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class TrainingRequest(BaseModel):
    """Request para entrenar modelo"""
    n_episodes: int = Field(
        default=500,
        description="Número de episodios de entrenamiento",
        ge=10,
        le=10000,
    )
    save_dir: str = Field(
        default="models/checkpoints",
        description="Directorio para guardar checkpoints",
    )


# ============================================================================
# ESTADO DE EJECUCIONES
# ============================================================================

# Diccionario global para rastrear ejecuciones en progreso
# En producción, usar Redis o similar
execution_status: Dict[int, Dict] = {}


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/execute", response_model=AlgorithmExecutionResponse)
async def execute_algorithm(
    request: AlgorithmExecutionRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Ejecuta el algoritmo ACO+GraphSAGE para generar un horario.
    
    La ejecución se realiza en background. Use /status/{id} para monitorear.
    """
    # Verificar si PyTorch está disponible
    if not TORCH_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="El algoritmo ACO+GraphSAGE requiere PyTorch, que no está instalado en este servidor. "
                   "Contacte al administrador para habilitar esta funcionalidad."
        )
    
    from app.models import AlgorithmExecution
    
    # Crear registro de ejecución
    execution = AlgorithmExecution(
        algoritmo="ACO+GraphSAGE",
        parametros="{}",
        estado="running",
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)
    
    execution_id = execution.id
    
    # Inicializar estado
    execution_status[execution_id] = {
        'status': 'running',
        'progress': 0.0,
        'current_phase': 'initialization',
        'started_at': datetime.now(),
        'error': None,
    }
    
    # Ejecutar en background
    background_tasks.add_task(
        _run_algorithm_task,
        execution_id=execution_id,
        request=request,
    )
    
    return AlgorithmExecutionResponse(
        execution_id=execution_id,
        status="running",
        message="Ejecución iniciada. Use /status/{id} para monitorear progreso.",
        started_at=execution_status[execution_id]['started_at'],
    )


@router.get("/status/{execution_id}", response_model=AlgorithmStatusResponse)
async def get_algorithm_status(
    execution_id: int,
    db: Session = Depends(get_db),
):
    """
    Obtiene el estado actual de una ejecución.
    """
    from app.models import AlgorithmExecution
    
    # Buscar en estado en memoria
    if execution_id in execution_status:
        status_info = execution_status[execution_id]
        return AlgorithmStatusResponse(
            execution_id=execution_id,
            status=status_info['status'],
            progress=status_info.get('progress'),
            current_phase=status_info.get('current_phase'),
            metrics=status_info.get('metrics'),
            error=status_info.get('error'),
        )
    
    # Buscar en BD
    execution = db.query(AlgorithmExecution).filter(
        AlgorithmExecution.id == execution_id
    ).first()
    
    if not execution:
        raise HTTPException(status_code=404, detail="Ejecución no encontrada")
    
    return AlgorithmStatusResponse(
        execution_id=execution_id,
        status=execution.estado,
        progress=None,
        current_phase=None,
        metrics={
            'funcion_objetivo': execution.funcion_objetivo,
            'conflictos_profesor': execution.conflictos_profesor,
            'conflictos_aula': execution.conflictos_aula,
            'utilizacion_aulas': execution.utilizacion_aulas,
            'tiempo_ejecucion': execution.tiempo_ejecucion,
        } if execution.estado == 'completed' else None,
        error=None,
    )


@router.get("/executions")
async def list_executions(
    limit: int = 10,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """
    Lista las ejecuciones más recientes del algoritmo.
    """
    from app.models import AlgorithmExecution
    
    executions = (
        db.query(AlgorithmExecution)
        .filter(AlgorithmExecution.algoritmo == "ACO+GraphSAGE")
        .order_by(AlgorithmExecution.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    
    return [
        {
            'id': e.id,
            'estado': e.estado,
            'funcion_objetivo': e.funcion_objetivo,
            'tiempo_ejecucion': e.tiempo_ejecucion,
            'created_at': e.created_at,
        }
        for e in executions
    ]


@router.post("/train")
async def train_model(
    request: TrainingRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Entrena un modelo GraphSAGE usando REINFORCE.
    
    El entrenamiento se realiza en background.
    """
    # Verificar si PyTorch está disponible
    if not TORCH_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="El entrenamiento GraphSAGE requiere PyTorch, que no está instalado en este servidor. "
                   "Contacte al administrador para habilitar esta funcionalidad."
        )
    
    from app.models import AlgorithmExecution
    
    # Crear registro
    execution = AlgorithmExecution(
        algoritmo="GraphSAGE-Training",
        parametros=f'{{"n_episodes": {request.n_episodes}}}',
        estado="running",
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)
    
    execution_id = execution.id
    
    # Ejecutar en background
    background_tasks.add_task(
        _train_model_task,
        execution_id=execution_id,
        n_episodes=request.n_episodes,
        save_dir=request.save_dir,
    )
    
    return {
        'execution_id': execution_id,
        'status': 'running',
        'message': 'Entrenamiento iniciado',
    }


@router.get("/parameters")
async def get_parameters():
    """
    Obtiene los parámetros por defecto del algoritmo.
    """
    return {
        'aco': ACO_PARAMS,
        'local_search': LOCAL_SEARCH_PARAMS,
        'torch_available': TORCH_AVAILABLE,
    }


@router.get("/health")
async def algorithm_health():
    """
    Verifica el estado del módulo de algoritmo.
    """
    return {
        'status': 'available' if TORCH_AVAILABLE else 'limited',
        'torch_available': TORCH_AVAILABLE,
        'message': 'ACO+GraphSAGE completamente funcional' if TORCH_AVAILABLE 
                   else 'PyTorch no instalado - funcionalidad de algoritmo deshabilitada',
    }


# ============================================================================
# TAREAS EN BACKGROUND
# ============================================================================

def _run_algorithm_task(execution_id: int, request: AlgorithmExecutionRequest):
    """Tarea para ejecutar el algoritmo en background"""
    from app.database import SessionLocal
    from app.models import AlgorithmExecution
    import traceback
    
    db = SessionLocal()
    
    try:
        # Actualizar estado
        execution_status[execution_id]['current_phase'] = 'preparation'
        execution_status[execution_id]['progress'] = 0.1
        
        # Preparar parámetros
        aco_params = ACO_PARAMS.copy() if request.aco_iterations or request.n_hormigas else None
        if aco_params:
            if request.aco_iterations:
                aco_params['n_iteraciones'] = request.aco_iterations
            if request.n_hormigas:
                aco_params['n_hormigas'] = request.n_hormigas
        
        local_search_params = None
        if request.use_local_search:
            local_search_params = LOCAL_SEARCH_PARAMS.copy()
            local_search_params['algorithm'] = request.local_search_algorithm
        
        # Crear pipeline
        execution_status[execution_id]['current_phase'] = 'graph_construction'
        execution_status[execution_id]['progress'] = 0.2
        
        pipeline = TimetablePipeline(
            db_session=db,
            model_path=request.model_path,
            use_pretrained=request.use_pretrained_model,
        )
        
        pipeline.prepare()
        
        # Ejecutar generación
        execution_status[execution_id]['current_phase'] = 'aco_optimization'
        execution_status[execution_id]['progress'] = 0.4
        
        solution, metrics = pipeline.generate_schedule(
            aco_params=aco_params,
            local_search_params=local_search_params if request.use_local_search else None,
            save_to_db=request.save_to_db,
        )
        
        # Actualizar BD
        execution_status[execution_id]['current_phase'] = 'completed'
        execution_status[execution_id]['progress'] = 1.0
        execution_status[execution_id]['status'] = 'completed'
        execution_status[execution_id]['metrics'] = metrics
        
        # Actualizar registro en BD
        execution = db.query(AlgorithmExecution).filter(
            AlgorithmExecution.id == execution_id
        ).first()
        
        if execution:
            execution.estado = 'completed'
            execution.funcion_objetivo = metrics['total_cost']
            execution.conflictos_profesor = metrics.get('conflictos_profesor', 0)
            execution.conflictos_aula = metrics.get('conflictos_aula', 0)
            execution.utilizacion_aulas = metrics.get('utilizacion_aulas', 0)
            execution.tiempo_ejecucion = metrics.get('tiempo_ejecucion', 0)
            db.commit()
        
    except Exception as e:
        error_msg = f"Error: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        
        execution_status[execution_id]['status'] = 'failed'
        execution_status[execution_id]['error'] = str(e)
        
        # Actualizar BD
        execution = db.query(AlgorithmExecution).filter(
            AlgorithmExecution.id == execution_id
        ).first()
        
        if execution:
            execution.estado = 'failed'
            execution.log_ejecucion = error_msg
            db.commit()
    
    finally:
        db.close()


def _train_model_task(execution_id: int, n_episodes: int, save_dir: str):
    """Tarea para entrenar modelo en background"""
    from app.database import SessionLocal
    from app.models import AlgorithmExecution
    import traceback
    
    db = SessionLocal()
    
    try:
        # Crear pipeline
        pipeline = TimetablePipeline(db_session=db)
        pipeline.prepare()
        
        # Entrenar
        trained_model = pipeline.train_model(
            n_episodes=n_episodes,
            save_dir=save_dir,
        )
        
        # Actualizar BD
        execution = db.query(AlgorithmExecution).filter(
            AlgorithmExecution.id == execution_id
        ).first()
        
        if execution:
            execution.estado = 'completed'
            db.commit()
        
    except Exception as e:
        error_msg = f"Error: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        
        execution = db.query(AlgorithmExecution).filter(
            AlgorithmExecution.id == execution_id
        ).first()
        
        if execution:
            execution.estado = 'failed'
            execution.log_ejecucion = error_msg
            db.commit()
    
    finally:
        db.close()
