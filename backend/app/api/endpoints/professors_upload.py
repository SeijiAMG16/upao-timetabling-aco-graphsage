"""
API Endpoints para carga de profesores desde Horario_Docentes(2025-20).xlsx
INTEGRACIÓN COMPLETA CON extraer_por_colores_v4.py
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
import os
import tempfile
import sys
from pathlib import Path

from ...database import get_db
from ...models import Professor, ProfessorRestriction

# Importar el script de extracción V4
backend_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

try:
    import extraer_por_colores_v4
    EXTRACTOR_AVAILABLE = True
    print("[✓] Extractor V4 cargado correctamente")
except Exception as e:
    EXTRACTOR_AVAILABLE = False
    print(f"[!] Error importando extractor: {e}")

router = APIRouter(prefix="/api/professors-upload", tags=["Professors Upload"])

# ============================================================================
# SCHEMAS
# ============================================================================

class ProfessorPreview(BaseModel):
    id: int
    codigo: str
    nombre_completo: str
    restrictions_count: int

class RestrictionPreview(BaseModel):
    professor_id: int
    professor_name: str
    day: str
    start_time: str
    end_time: str
    duration_blocks: int

class UploadPreviewResponse(BaseModel):
    professors: List[ProfessorPreview]
    restrictions: List[RestrictionPreview]
    total_professors: int
    total_restrictions: int
    stats: dict

class ConfirmData(BaseModel):
    save_restrictions: bool = True
    save_history: bool = True

# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/upload")
async def upload_professors_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload Horario_Docentes(2025-20).xlsx y extraer profesores + restricciones
    
    1. Guarda el Excel temporalmente
    2. Ejecuta extraer_por_colores_v4.py para extraer asignaciones y restricciones
    3. Retorna preview de datos extraídos
    """
    
    if not EXTRACTOR_AVAILABLE:
        raise HTTPException(
            status_code=500,
            detail="Extractor no disponible. Revisa configuración del servidor."
        )
    
    # Validar archivo
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Archivo debe ser Excel (.xlsx)")
    
    # Crear archivo temporal
    tmp_fd, tmp_path = tempfile.mkstemp(suffix='.xlsx')
    
    try:
        # Guardar Excel en temporal
        content = await file.read()
        os.write(tmp_fd, content)
        os.close(tmp_fd)
        
        print(f"\n{'='*80}")
        print("EJECUTANDO EXTRACTOR V4 SOBRE EXCEL")
        print(f"Archivo: {tmp_path}")
        print(f"{'='*80}\n")
        
        # EJECUTAR EL SCRIPT DE EXTRACCIÓN
        # Modificar temporalmente EXCEL_PATH en el módulo
        original_path = extraer_por_colores_v4.EXCEL_PATH
        extraer_por_colores_v4.EXCEL_PATH = tmp_path
        
        # Ejecutar extracción
        asignaciones, lista_restricciones, estadisticas = extraer_por_colores_v4.extraer_asignaciones_v4()
        
        # Restaurar path original
        extraer_por_colores_v4.EXCEL_PATH = original_path
        
        print(f"\n[✓] Extracción completada:")
        print(f"    Asignaciones: {len(asignaciones)}")
        print(f"    Restricciones: {len(lista_restricciones)}")
        
        # Crear previews de profesores únicos encontrados
        profesores_ids = set(asig['profesor_id'] for asig in asignaciones)
        profesores_preview = []
        
        for prof_id in profesores_ids:
            prof = db.query(Professor).filter_by(id=prof_id).first()
            if prof:
                # Contar restricciones de este profesor
                rest_count = len([r for r in lista_restricciones if r['professor_id'] == prof_id])
                profesores_preview.append(ProfessorPreview(
                    id=prof.id,
                    codigo=prof.codigo,
                    nombre_completo=prof.nombre_completo,
                    restrictions_count=rest_count
                ))
        
        # Crear previews de restricciones (primeras 50 para no saturar)
        restricciones_preview = []
        for rest in lista_restricciones[:50]:
            prof = db.query(Professor).filter_by(id=rest['professor_id']).first()
            if prof:
                restricciones_preview.append(RestrictionPreview(
                    professor_id=rest['professor_id'],
                    professor_name=prof.nombre_completo,
                    day=rest['day'],
                    start_time=rest['start_time'],
                    end_time=rest['end_time'],
                    duration_blocks=rest['duration_blocks']
                ))
        
        return UploadPreviewResponse(
            professors=profesores_preview,
            restrictions=restricciones_preview,
            total_professors=len(profesores_preview),
            total_restrictions=len(lista_restricciones),
            stats=estadisticas
        )
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error procesando archivo: {str(e)}")
    
    finally:
        # Limpiar archivo temporal
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except:
                pass


@router.post("/confirm")
async def confirm_professors_upload(
    data: ConfirmData,
    db: Session = Depends(get_db)
):
    """
    Confirmar carga de restricciones en BD
    
    NOTA: El script extraer_por_colores_v4.py YA guardó las asignaciones
          en la tabla professor_course_history. Este endpoint solo
          verifica y reporta el estado.
    """
    
    try:
        # Verificar cuántas restricciones hay actualmente
        restrictions_count = db.query(ProfessorRestriction).filter_by(
            reason='Extraido de Excel'
        ).count()
        
        return {
            'success': True,
            'message': f"Datos cargados exitosamente",
            'restrictions_saved': restrictions_count,
            'note': 'El script ya insertó asignaciones y restricciones en BD'
        }
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/stats")
async def get_upload_stats(db: Session = Depends(get_db)):
    """
    Obtiene estadísticas de datos cargados desde Excel
    """
    
    professors_count = db.query(Professor).count()
    restrictions_count = db.query(ProfessorRestriction).filter_by(
        reason='Extraido de Excel'
    ).count()
    
    return {
        'total_professors': professors_count,
        'total_restrictions_from_excel': restrictions_count,
        'extractor_available': EXTRACTOR_AVAILABLE
    }
