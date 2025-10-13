"""
Endpoints para gestión de cursos
Incluye extracción desde Excel y reemplazo de cursos
"""
import os
import tempfile
import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.course_extractor import CourseExtractorService, CourseIntegratorService
from app.models import Course, Professor

# Configuración de logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/courses", tags=["courses"])

@router.post("/extract-from-excel")
async def extract_courses_from_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Extrae cursos desde archivo Excel (Libro1.xlsx format)
    """
    try:
        # Validar tipo de archivo
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Archivo debe ser Excel (.xlsx o .xls)"
            )
        
        # Guardar archivo temporalmente
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        try:
            # Extraer cursos
            extractor = CourseExtractorService()
            result = extractor.extract_courses_from_excel(tmp_path)
            
            if not result["success"]:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Error extrayendo cursos: {result.get('error', 'Error desconocido')}"
                )
            
            logger.info(f"✅ Extraídos {result['total_courses']} cursos desde {file.filename}")
            
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "message": f"Extraídos {result['total_courses']} cursos exitosamente",
                    "data": result
                }
            )
            
        finally:
            # Limpiar archivo temporal
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error inesperado extrayendo cursos: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )

@router.post("/replace-all-from-excel")
async def replace_all_courses_from_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Reemplaza TODOS los cursos en la base de datos con los del Excel
    ⚠️ PELIGROSO: Elimina todos los cursos existentes
    """
    try:
        # Validar tipo de archivo
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Archivo debe ser Excel (.xlsx o .xls)"
            )
        
        # Guardar archivo temporalmente
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        try:
            # Extraer cursos
            extractor = CourseExtractorService()
            extraction_result = extractor.extract_courses_from_excel(tmp_path)
            
            if not extraction_result["success"]:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Error extrayendo cursos: {extraction_result.get('error', 'Error desconocido')}"
                )
            
            # Integrar a base de datos
            integrator = CourseIntegratorService()
            integration_result = integrator.replace_all_courses(
                extraction_result["courses"], 
                db
            )
            
            if not integration_result["success"]:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Error integrando cursos: {integration_result.get('error', 'Error desconocido')}"
                )
            
            logger.info(f"✅ Reemplazados todos los cursos con {integration_result['courses_inserted']} del archivo {file.filename}")
            
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "message": f"Reemplazados exitosamente {integration_result['courses_inserted']} cursos",
                    "extraction": extraction_result,
                    "integration": integration_result
                }
            )
            
        finally:
            # Limpiar archivo temporal
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error inesperado reemplazando cursos: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )

@router.get("/")
async def get_all_courses(db: Session = Depends(get_db)):
    """
    Obtiene todos los cursos
    """
    try:
        courses = db.query(Course).all()
        
        courses_data = []
        for course in courses:
            courses_data.append({
                "id": course.id,
                "codigo": course.codigo,
                "nombre": course.nombre,
                "ciclo": course.ciclo,
                "modalidad": course.modalidad,
                "creditos": course.creditos,
                "alumnos_teoria": course.alumnos_teoria,
                "alumnos_practica": course.alumnos_practica,
                "alumnos_laboratorio": course.alumnos_laboratorio,
                "requiere_laboratorio": course.requiere_laboratorio,
                "requiere_practica": course.requiere_practica,
                "active": course.active
            })
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "total": len(courses_data),
                "courses": courses_data
            }
        )
    
    except Exception as e:
        logger.error(f"❌ Error obteniendo cursos: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )

@router.get("/summary")
async def get_courses_summary(db: Session = Depends(get_db)):
    """
    Obtiene resumen de cursos y profesores
    """
    try:
        total_courses = db.query(Course).count()
        total_professors = db.query(Professor).count()
        
        # Estadísticas por ciclo
        courses_by_cycle = {}
        courses = db.query(Course).all()
        
        for course in courses:
            cycle = course.ciclo
            if cycle not in courses_by_cycle:
                courses_by_cycle[cycle] = 0
            courses_by_cycle[cycle] += 1
        
        # Modalidades
        modalidad_counts = {}
        for course in courses:
            modalidad = course.modalidad
            if modalidad not in modalidad_counts:
                modalidad_counts[modalidad] = 0
            modalidad_counts[modalidad] += 1
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "summary": {
                    "total_courses": total_courses,
                    "total_professors": total_professors,
                    "courses_by_cycle": courses_by_cycle,
                    "courses_by_modalidad": modalidad_counts,
                    "with_lab": len([c for c in courses if c.requiere_laboratorio]),
                    "with_practice": len([c for c in courses if c.requiere_practica])
                }
            }
        )
    
    except Exception as e:
        logger.error(f"❌ Error obteniendo resumen: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )