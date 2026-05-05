"""
API endpoints for schedule generation and Excel download
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from typing import Optional, Dict, Any
import logging
import subprocess
import os
import glob
import shutil
from datetime import datetime
from pathlib import Path
import json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/horario", tags=["horario"])

# Store generation status
generation_status: Dict[str, Any] = {
    "is_running": False,
    "progress": 0,
    "message": "",
    "error": None,
    "filename": None,
    "started_at": None,
    "completed_at": None
}

def reset_status():
    """Reset generation status"""
    global generation_status
    generation_status = {
        "is_running": False,
        "progress": 0,
        "message": "",
        "error": None,
        "filename": None,
        "started_at": None,
        "completed_at": None
    }

def ejecutar_generacion_completa():
    """
    Execute the complete schedule generation process:
    1. Run ACO+GraphSAGE algorithm (ejecutar_aco_completo.py)
    2. Generate Excel with professor schedules (exportar_horarios_un_archivo.py)
    """
    global generation_status
    
    try:
        # Get the backend directory
        backend_dir = Path(__file__).parent.parent.parent.parent
        
        # Update status
        generation_status["is_running"] = True
        generation_status["progress"] = 10
        generation_status["message"] = "Iniciando generación de horarios..."
        generation_status["started_at"] = datetime.now().isoformat()
        
        logger.info("=== STEP 1: Ejecutando ACO+GraphSAGE (ejecutar_aco_completo.py) ===")
        generation_status["progress"] = 20
        generation_status["message"] = "Ejecutando algoritmo ACO con GraphSAGE..."
        
        # Execute ACO+GraphSAGE generation script with optimized parameters
        aco_script = backend_dir / "ejecutar_aco_completo.py"
        
        logger.info(f"[DEBUG] Ejecutando script: {aco_script}")
        logger.info(f"[DEBUG] Directorio de trabajo: {backend_dir}")
        logger.info(f"[DEBUG] Parámetros: 10 hormigas, 5 iteraciones (Optimizado para evitar OOM)")
        
        # Parámetros ajustados para evitar Out of Memory en Droplet de 4GB
        result_aco = subprocess.run(
            [
                "python", str(aco_script),
                "--hormigas", "10",
                "--iteraciones", "5",
                "--alpha", "1.0",
                "--beta", "5.0",               # Siguiendo Exp 10 (Mejor resultado)
                "--rho", "0.1",                # Sincronizado con config.py
                "--q0", "0.9",                 # Sincronizado con config.py
                "--patiencia", "5",            # Sincronizado con config.py
                "--max-candidatos", "600",     # Sincronizado con config.py
                "--max-profesores", "6",
                "--max-aulas", "12",
                "--max-timeslots", "12"
            ],
            cwd=backend_dir,
            timeout=10800  # 3 hours timeout
        )
        
        logger.info(f"[DEBUG] Script completado con código: {result_aco.returncode}")
        
        if result_aco.returncode != 0:
            raise Exception(f"Error en ACO+GraphSAGE: código de salida {result_aco.returncode}")
        
        logger.info("✅ ACO+GraphSAGE completado exitosamente")
        
        # Find the generated JSON file
        json_files = glob.glob(str(backend_dir / "horario_generado_*.json"))
        if not json_files:
            raise Exception("No se encontró el archivo JSON generado por ACO+GraphSAGE")
        
        latest_json = max(json_files, key=os.path.getctime)
        logger.info(f"Archivo JSON encontrado: {latest_json}")
        
        # Log statistics from JSON
        try:
            with open(latest_json, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
                total_asignaciones = len(json_data.get('asignaciones', []))
                logger.info(f"📊 Total de asignaciones generadas: {total_asignaciones}")
                if 'mejor_solucion' in json_data:
                    logger.info(f"💯 Score final: {json_data['mejor_solucion'].get('score', 'N/A')}")
        except Exception as e:
            logger.warning(f"No se pudo leer estadísticas del JSON: {e}")
        
        # Update progress
        generation_status["progress"] = 60
        generation_status["message"] = "Generando archivo Excel con horarios de profesores..."
        
        logger.info("=== STEP 2: Excel ya generado automáticamente por ejecutar_aco_completo.py ===")
        
        # Find the generated Excel file (formato profesores)
        excel_files = glob.glob(str(backend_dir / "horario_generado_*_formato_profesores.xlsx"))
        if not excel_files:
            raise Exception("No se encontró el archivo Excel formateado generado")
        
        latest_excel = max(excel_files, key=os.path.getctime)
        excel_filename = os.path.basename(latest_excel)
        
        logger.info(f"✅ Archivo Excel generado: {excel_filename}")
        
        # Move files to generated_dir for persistence
        generated_dir = backend_dir / "horarios_generados"
        if not os.path.exists(generated_dir):
            os.makedirs(generated_dir)
            
        for f_path in glob.glob(str(backend_dir / "horario_generado_*")):
            try:
                shutil.move(f_path, str(generated_dir / os.path.basename(f_path)))
                logger.info(f"Archivo movido a persistencia: {os.path.basename(f_path)}")
            except Exception as e:
                logger.warning(f"No se pudo mover {f_path}: {e}")
        
        # Update filename to the new location (relative for the API)
        excel_filename = os.path.basename(latest_excel)
        
        # Update status - SUCCESS
        generation_status["is_running"] = False
        generation_status["progress"] = 100
        generation_status["message"] = "Horario generado exitosamente"
        generation_status["filename"] = excel_filename
        generation_status["completed_at"] = datetime.now().isoformat()
        
        logger.info("=== GENERACIÓN COMPLETA EXITOSA ===")
        
    except subprocess.TimeoutExpired:
        error_msg = "Timeout: La generación tardó demasiado tiempo"
        logger.error(error_msg)
        generation_status["is_running"] = False
        generation_status["error"] = error_msg
        generation_status["message"] = "Error: Timeout en la generación"
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error en generación: {error_msg}")
        generation_status["is_running"] = False
        generation_status["error"] = error_msg
        generation_status["message"] = f"Error: {error_msg}"


@router.post("/generar")
async def generar_horario(background_tasks: BackgroundTasks):
    """
    Start the schedule generation process
    
    This endpoint triggers:
    1. ACO algorithm execution with GraphSAGE heuristics
    2. Excel file generation with professor schedules
    
    Returns immediately with status, actual generation runs in background
    """
    global generation_status
    
    # Check if generation is already running
    if generation_status["is_running"]:
        return JSONResponse(
            status_code=409,
            content={
                "error": "Ya hay una generación en progreso",
                "status": generation_status
            }
        )
    
    # Reset status and start generation
    reset_status()
    background_tasks.add_task(ejecutar_generacion_completa)
    
    return {
        "message": "Generación de horario iniciada",
        "status": "started",
        "algorithm": "ACO + GraphSAGE",
        "estimated_time_minutes": 3,
        "parameters": {
            "hormigas": 10,
            "iteraciones": 5,
            "alpha": 1.0,
            "beta": 5.0,
            "rho": 0.1,
            "q0": 0.9
        }
    }


@router.get("/status")
async def get_status():
    """
    Get the current status of schedule generation
    
    Returns:
    - is_running: Whether generation is currently in progress
    - progress: Completion percentage (0-100)
    - message: Current status message
    - error: Error message if generation failed
    - filename: Generated Excel filename if completed successfully
    - started_at: ISO timestamp when generation started
    - completed_at: ISO timestamp when generation completed
    """
    return generation_status


@router.get("/descargar/{filename}")
async def descargar_horario(filename: str):
    """
    Download the generated Excel file
    
    Parameters:
    - filename: Name of the Excel file to download
    
    Returns:
    - FileResponse with the Excel file
    """
    # Validate filename to prevent directory traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Nombre de archivo inválido")
    
    # Check if filename matches expected pattern (acepta ambos formatos)
    valid_patterns = [
        filename.startswith("HORARIOS_PROFESORES_UPAO_") and filename.endswith(".xlsx"),
        filename.startswith("horario_generado_") and filename.endswith("_formato_profesores.xlsx")
    ]
    if not any(valid_patterns):
        raise HTTPException(status_code=400, detail="Nombre de archivo no válido")
    
    # Get backend directory and generated schedules directory
    backend_dir = Path(__file__).parent.parent.parent.parent
    generated_dir = backend_dir / "horarios_generados"
    file_path = generated_dir / filename
    
    # Fallback to backend root if not in generated_dir (for legacy files)
    if not file_path.exists():
        file_path = backend_dir / filename
    
    # Check if file exists
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    # Return file
    return FileResponse(
        path=file_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=filename,
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )


@router.get("/archivos")
async def listar_archivos():
    """
    List all generated Excel files
    
    Returns:
    - List of available Excel files with metadata
    """
    backend_dir = Path(__file__).parent.parent.parent.parent
    generated_dir = backend_dir / "horarios_generados"
    
    # Asegurar que el directorio existe
    if not os.path.exists(generated_dir):
        os.makedirs(generated_dir)
    
    # Buscar archivos en el directorio específico y en la raíz (compatibilidad)
    excel_files = []
    excel_files.extend(glob.glob(str(generated_dir / "HORARIOS_PROFESORES_UPAO_*.xlsx")))
    excel_files.extend(glob.glob(str(generated_dir / "horario_generado_*_formato_profesores.xlsx")))
    excel_files.extend(glob.glob(str(backend_dir / "HORARIOS_PROFESORES_UPAO_*.xlsx")))
    excel_files.extend(glob.glob(str(backend_dir / "horario_generado_*_formato_profesores.xlsx")))
    
    files = []
    for file_path in excel_files:
        file_stat = os.stat(file_path)
        files.append({
            "filename": os.path.basename(file_path),
            "size_mb": round(file_stat.st_size / (1024 * 1024), 2),
            "created_at": datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
            "modified_at": datetime.fromtimestamp(file_stat.st_mtime).isoformat()
        })
    
    # Sort by creation time (newest first)
    files.sort(key=lambda x: x["created_at"], reverse=True)
    
    return {
        "files": files,
        "count": len(files)
    }
