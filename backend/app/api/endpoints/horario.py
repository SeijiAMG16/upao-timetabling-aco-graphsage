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

# Store generation status and current process
current_process: Optional[subprocess.Popen] = None
generation_status: Dict[str, Any] = {
    "is_running": False,
    "progress": 0,
    "message": "",
    "error": None,
    "filename": None,
    "started_at": None,
    "completed_at": None,
    "logs": [],
    "metrics": {
        "iterations": [],
        "repaired_count": 0,
        "total_sections": 298,
        "assigned_sections": 0,
        "elapsed_time": 0.0,
        "best_cost": None
    }
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
        "completed_at": None,
        "logs": [],
        "metrics": {
            "iterations": [],
            "repaired_count": 0,
            "total_sections": 298,
            "assigned_sections": 0,
            "elapsed_time": 0.0,
            "best_cost": None
        }
    }

def ejecutar_generacion_completa():
    """
    Execute the complete schedule generation process:
    1. Run ACO+GraphSAGE algorithm (ejecutar_aco_completo.py)
    2. Generate Excel with professor schedules (exportar_horarios_un_archivo.py)
    """
    global generation_status, current_process
    
    try:
        # Get the backend directory
        backend_dir = Path(__file__).parent.parent.parent.parent
        
        # Update status
        generation_status["is_running"] = True
        generation_status["progress"] = 10
        generation_status["message"] = "Iniciando generación de horarios..."
        generation_status["started_at"] = datetime.now().isoformat()
        generation_status["logs"] = []
        generation_status["metrics"] = {
            "iterations": [],
            "repaired_count": 0,
            "total_sections": 298,
            "assigned_sections": 0,
            "elapsed_time": 0.0,
            "best_cost": None
        }
        
        logger.info("=== STEP 1: Ejecutando ACO+GraphSAGE (ejecutar_aco_completo.py) ===")
        generation_status["progress"] = 15
        generation_status["message"] = "Ejecutando algoritmo ACO con GraphSAGE..."
        
        aco_script = backend_dir / "ejecutar_aco_completo.py"
        
        logger.info(f"[DEBUG] Ejecutando script: {aco_script}")
        logger.info(f"[DEBUG] Directorio de trabajo: {backend_dir}")
        logger.info(f"[DEBUG] Parámetros: 15 hormigas, 4 iteraciones")
        
        # Iniciar proceso en modo binario (text=False) y sin bufer (-u) para transmitir en tiempo real
        current_process = subprocess.Popen(
            [
                "python", "-u", str(aco_script),
                "--hormigas", "15",
                "--iteraciones", "4",
                "--alpha", "1.0",
                "--beta", "2.0",
                "--rho", "0.2",
                "--q0", "0.9",
                "--patiencia", "8",
                "--max-candidatos", "600",
                "--max-profesores", "8",
                "--max-aulas", "15",
                "--max-timeslots", "15"
            ],
            cwd=backend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=False
        )
        
        # Leer salida en tiempo real
        while True:
            # Si el usuario canceló la ejecución, detener lectura
            if not generation_status["is_running"]:
                logger.info("Ejecución detenida por bandera is_running=False.")
                break
                
            line = current_process.stdout.readline()
            if not line:
                break
            
            try:
                line_str = line.decode('utf-8').strip()
            except UnicodeDecodeError:
                try:
                    line_str = line.decode('cp1252').strip()
                except Exception:
                    line_str = line.decode('latin1', errors='replace').strip()
                
            # Limpiar posible carácter de reemplazo en palabras clave con tilde si quedara alguno
            line_str = line_str.replace("seccin", "sección").replace("Seccin", "Sección")
            line_str = line_str.replace("Iteracin", "Iteración").replace("construccin", "construcción")
            
            if line_str:
                logger.info(f"[ACO] {line_str}")
                generation_status["logs"].append(line_str)
                # Permitir un historial masivo (50,000 líneas) y si se supera, mantener las primeras 500 líneas (carga de grafo)
                if len(generation_status["logs"]) > 50000:
                    generation_status["logs"].pop(500)
                
                # Parsear etapas del script
                if "[DEBUG] Script iniciado" in line_str:
                    generation_status["progress"] = 12
                    generation_status["message"] = "Iniciando script e importando librerías..."
                elif "1. Construyendo grafo..." in line_str:
                    generation_status["progress"] = 15
                    generation_status["message"] = "Construyendo grafo de restricciones..."
                elif "2. Creando modelo GNN..." in line_str:
                    generation_status["progress"] = 20
                    generation_status["message"] = "Inicializando modelo GraphSAGE..."
                elif "3. Creando validador de restricciones..." in line_str:
                    generation_status["progress"] = 22
                    generation_status["message"] = "Configurando validador de restricciones duras..."
                elif "4. Creando evaluador de restricciones suaves..." in line_str:
                    generation_status["progress"] = 24
                    generation_status["message"] = "Configurando evaluador de costos suaves..."
                elif "5. Configurando ACO..." in line_str:
                    generation_status["progress"] = 25
                    generation_status["message"] = "Inicializando Colonia de Hormigas (ACO)..."
                elif "Iniciando ACO con" in line_str:
                    generation_status["progress"] = 28
                    generation_status["message"] = "Buscando asignaciones con Colonia de Hormigas (ACO)..."
                elif "Iteración " in line_str:
                    try:
                        if ":" in line_str and "/" in line_str.split("Iteración")[1]:
                            parts = line_str.split("Iteración")[1].split(":")
                            it_parts = parts[0].strip().split("/")
                            curr_it = int(it_parts[0])
                            total_it = int(it_parts[1])
                            
                            prog = 30 + int((curr_it / total_it) * 50)
                            generation_status["progress"] = min(prog, 80)
                            
                            content = parts[1].strip()
                            if "Mejor=" in content:
                                metrics_parts = content.split(",")
                                best_val = float(metrics_parts[0].split("=")[1].strip())
                                avg_val = float(metrics_parts[1].split("=")[1].strip())
                                glob_val = float(metrics_parts[2].split("=")[1].strip())
                                
                                if not any(it["iteration"] == curr_it for it in generation_status["metrics"]["iterations"]):
                                    generation_status["metrics"]["iterations"].append({
                                        "iteration": curr_it,
                                        "best": best_val,
                                        "avg": avg_val,
                                        "global": glob_val
                                    })
                                generation_status["metrics"]["best_cost"] = glob_val
                                generation_status["message"] = f"Optimizando (Iteración {curr_it}/{total_it}) - Costo: {glob_val:.2f}"
                            elif "Nueva mejor solución:" in content:
                                best_val = float(content.split("Nueva mejor solución:")[1].strip())
                                generation_status["metrics"]["best_cost"] = best_val
                                generation_status["message"] = f"Optimizando (Iteración {curr_it}/{total_it}) - Mejor: {best_val:.2f}"
                                if not any(it["iteration"] == curr_it for it in generation_status["metrics"]["iterations"]):
                                    generation_status["metrics"]["iterations"].append({
                                        "iteration": curr_it,
                                        "best": best_val,
                                        "avg": best_val,
                                        "global": best_val
                                    })
                            else:
                                generation_status["message"] = f"Optimizando (Iteración {curr_it}/{total_it})..."
                    except Exception as parse_ex:
                        logger.warning(f"Error parseando línea de iteración: {parse_ex}")
                elif "[REPARACIÓN]" in line_str:
                    generation_status["progress"] = 85
                    generation_status["message"] = "Reparando asignaciones faltantes (Greedy Repair)..."
                    if "Reparación greedy completada" in line_str:
                        try:
                            cov_str = line_str.split("Cobertura:")[1].strip().split("/")
                            assigned = int(cov_str[0])
                            total = int(cov_str[1])
                            generation_status["metrics"]["assigned_sections"] = assigned
                            generation_status["metrics"]["total_sections"] = total
                        except Exception:
                            pass
                
                # --- PARSEADORES DINÁMICOS Y FLUIDOS EN TIEMPO REAL ---
                if "asignó " in line_str and " secciones" in line_str:
                    try:
                        cov_str = line_str.split("asignó ")[1].split(" secciones")[0].strip().split("/")
                        generation_status["metrics"]["assigned_sections"] = int(cov_str[0])
                        generation_status["metrics"]["total_sections"] = int(cov_str[1])
                    except Exception:
                        pass
                elif "secciones asignadas" in line_str:
                    try:
                        cov_str = line_str.split("Resultado:")[1].split("secciones")[0].strip().split("/")
                        generation_status["metrics"]["assigned_sections"] = int(cov_str[0])
                        generation_status["metrics"]["total_sections"] = int(cov_str[1])
                    except Exception:
                        pass
                elif "Secciones asignadas:" in line_str:
                    try:
                        cov_str = line_str.split("Secciones asignadas:")[1].strip().split("/")
                        generation_status["metrics"]["assigned_sections"] = int(cov_str[0])
                        generation_status["metrics"]["total_sections"] = int(cov_str[1])
                    except Exception:
                        pass
                elif "[GREEDY] Reparada sección" in line_str:
                    generation_status["metrics"]["repaired_count"] += 1
                elif "Secciones no asignadas:" in line_str:
                    try:
                        list_str = line_str.split("Secciones no asignadas:")[1].strip()
                        if list_str.startswith("[") and list_str.endswith("]"):
                            import ast
                            unassigned_list = ast.literal_eval(list_str)
                            generation_status["metrics"]["repaired_count"] = len(unassigned_list)
                    except Exception:
                        pass
                elif "Costo soft:" in line_str:
                    try:
                        generation_status["metrics"]["best_cost"] = float(line_str.split("Costo soft:")[1].strip())
                    except Exception:
                        pass
                elif "[TIEMPO]" in line_str:
                    try:
                        time_val = float(line_str.split("Duración de ejecución:")[1].split("segundos")[0].strip())
                        generation_status["metrics"]["elapsed_time"] = time_val
                    except Exception:
                        pass
                elif "[EXCEL]" in line_str or "Convirtiendo a formato Excel" in line_str:
                    generation_status["progress"] = 95
                    generation_status["message"] = "Generando y formateando archivo Excel..."
        
        # Verificar si fue cancelado externamente
        if not generation_status["is_running"]:
            logger.info("Proceso cancelado, finalizando ejecución en background.")
            if current_process:
                try:
                    current_process.terminate()
                except Exception:
                    pass
                current_process = None
            return

        returncode = current_process.wait()
        current_process = None
        logger.info(f"[DEBUG] Script completado con código: {returncode}")
        
        if returncode != 0:
            raise Exception(f"Error en ACO+GraphSAGE: código de salida {returncode}")
        
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
                generation_status["metrics"]["assigned_sections"] = total_asignaciones
                if 'mejor_solucion' in json_data:
                    logger.info(f"💯 Score final: {json_data['mejor_solucion'].get('score', 'N/A')}")
        except Exception as e:
            logger.warning(f"No se pudo leer estadísticas del JSON: {e}")
        
        # Update progress
        generation_status["progress"] = 96
        generation_status["message"] = "Guardando archivos generados..."
        
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
        if current_process:
            try:
                current_process.terminate()
            except Exception:
                pass
            current_process = None
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error en generación: {error_msg}")
        generation_status["is_running"] = False
        generation_status["error"] = error_msg
        generation_status["message"] = f"Error: {error_msg}"
        if current_process:
            try:
                current_process.terminate()
            except Exception:
                pass
            current_process = None


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
        "estimated_time_minutes": 2,
        "parameters": {
            "hormigas": 15,
            "iteraciones": 4,
            "alpha": 1.0,
            "beta": 2.0,
            "rho": 0.2,
            "q0": 0.9
        }
    }


@router.post("/cancelar")
async def cancelar_horario():
    """
    Cancelar/abortar la ejecución de la generación en curso.
    """
    global current_process, generation_status
    
    if not generation_status["is_running"]:
        return {"message": "No hay una generación en progreso"}
    
    logger.info("Recibida petición para cancelar la generación actual.")
    generation_status["is_running"] = False
    generation_status["message"] = "Ejecución cancelada por el usuario"
    generation_status["error"] = "Generación detenida manualmente por el usuario."
    
    if current_process is not None:
        try:
            current_process.terminate()
            logger.info("Subproceso terminado exitosamente.")
        except Exception as e:
            logger.warning(f"Error terminando subproceso: {e}")
        current_process = None
        
    return {"message": "Generación de horario cancelada exitosamente", "status": "cancelled"}


@router.get("/status")
async def get_status():
    """
    Get the current status of schedule generation
    """
    return generation_status


@router.get("/descargar/{filename}")
async def descargar_horario(filename: str):
    """
    Download the generated Excel file
    """
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Nombre de archivo inválido")
    
    valid_patterns = [
        filename.startswith("HORARIOS_PROFESORES_UPAO_") and filename.endswith(".xlsx"),
        filename.startswith("horario_generado_") and filename.endswith("_formato_profesores.xlsx"),
        filename.startswith("horario_generado_") and filename.endswith(".json"),
        filename.startswith("horario_generado_") and filename.endswith(".csv")
    ]
    if not any(valid_patterns):
        raise HTTPException(status_code=400, detail="Nombre de archivo no válido")
    
    backend_dir = Path(__file__).parent.parent.parent.parent
    generated_dir = backend_dir / "horarios_generados"
    file_path = generated_dir / filename
    
    if not file_path.exists():
        file_path = backend_dir / filename
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    if filename.endswith(".json"):
        media_type = "application/json"
    elif filename.endswith(".csv"):
        media_type = "text/csv"
    else:
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=filename,
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Access-Control-Expose-Headers": "Content-Disposition",
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"
        }
    )


@router.get("/archivos")
async def listar_archivos():
    """
    List all generated Excel files
    """
    backend_dir = Path(__file__).parent.parent.parent.parent
    generated_dir = backend_dir / "horarios_generados"
    
    if not os.path.exists(generated_dir):
        os.makedirs(generated_dir)
    
    excel_files = []
    excel_files.extend(glob.glob(str(generated_dir / "HORARIOS_PROFESORES_UPAO_*.xlsx")))
    excel_files.extend(glob.glob(str(generated_dir / "horario_generado_*_formato_profesores.xlsx")))
    excel_files.extend(glob.glob(str(generated_dir / "horario_generado_*.json")))
    excel_files.extend(glob.glob(str(generated_dir / "horario_generado_*.csv")))
    
    excel_files.extend(glob.glob(str(backend_dir / "horario_generado_*.json")))
    excel_files.extend(glob.glob(str(backend_dir / "HORARIOS_PROFESORES_UPAO_*.xlsx")))
    
    files = []
    for file_path in excel_files:
        file_stat = os.stat(file_path)
        files.append({
            "filename": os.path.basename(file_path),
            "size_mb": round(file_stat.st_size / (1024 * 1024), 2),
            "created_at": datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
            "modified_at": datetime.fromtimestamp(file_stat.st_mtime).isoformat()
        })
    
    files.sort(key=lambda x: x["created_at"], reverse=True)
    
    return {
        "files": files,
        "count": len(files)
    }
