"""
Main FastAPI application for UPAO Timetabling System
"""

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import uvicorn
import logging
from typing import List, Dict, Any
import os
from pathlib import Path

# Import application modules
from .database import get_db, create_tables, initialize_database, check_database_connection
from .excel.excel_processor import ExcelProcessor
from .models import Course, Professor, Classroom, TimeSlot, ScheduleAssignment
from .api.endpoints import assignments

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="UPAO Timetabling System",
    description="Sistema de generación automática de horarios para ISIA-UPAO usando ACO y GraphSAGE",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
# Obtener origins desde variable de entorno o usar defaults para desarrollo
default_origins = "http://localhost:3000,http://localhost:3001,http://localhost:5173,https://upao-timetabling-99157d62b924.herokuapp.com"
cors_origins = os.getenv("CORS_ORIGINS", default_origins).split(",")
# En producción, permitir cualquier origen de herokuapp.com
cors_origins.append("https://*.herokuapp.com")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Temporarily allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(assignments.router)
from .api.endpoints import projections, professors, classrooms, auth, professors_upload, courses, algorithm, horario, db_admin
app.include_router(projections.router)
app.include_router(professors.router)
app.include_router(classrooms.router)
app.include_router(auth.router)
app.include_router(professors_upload.router)
app.include_router(algorithm.router)
app.include_router(courses.router)
app.include_router(horario.router)
app.include_router(db_admin.router)

# Global variables
excel_processor = ExcelProcessor()

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("Starting UPAO Timetabling System...")
    logger.info("Application startup completed!")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "UPAO Timetabling System API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    db_status = check_database_connection()
    return {
        "status": "healthy" if db_status else "unhealthy",
        "database": "connected" if db_status else "disconnected",
        "timestamp": "2025-09-23T00:00:00Z"
    }

# Excel Processing Endpoints
@app.post("/api/excel/upload-projections")
async def upload_projections(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload and process course projections Excel file"""
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="File must be an Excel file (.xlsx or .xls)")
    
    # Save uploaded file temporarily
    upload_dir = Path("temp_uploads")
    upload_dir.mkdir(exist_ok=True)
    file_path = upload_dir / file.filename
    
    try:
        # Save file
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Process Excel
        projections, analysis = excel_processor.process_projections_excel(str(file_path))
        
        if not projections:
            return JSONResponse(
                status_code=400,
                content={"error": "No valid course projections found in Excel file", "analysis": analysis}
            )
        
        # Save to database in background
        background_tasks.add_task(save_projections_to_db, projections, db)
        
        return {
            "message": f"Successfully processed {len(projections)} course projections",
            "projections_count": len(projections),
            "analysis": analysis,
            "processing_status": "completed"
        }
        
    except Exception as e:
        logger.error(f"Error processing Excel file: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
    
    finally:
        # Clean up temporary file
        if file_path.exists():
            os.remove(file_path)

@app.get("/api/excel/analyze-structure")
async def analyze_excel_structure(file_path: str):
    """Analyze Excel file structure (for debugging)"""
    try:
        analysis = excel_processor.analyze_excel_structure(file_path)
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing file: {str(e)}")

# Time Slot Endpoints
@app.get("/api/time-slots")
async def get_time_slots(
    dia_semana: int = None,
    periodo: str = None,
    db: Session = Depends(get_db)
):
    """Get time slots with optional filtering"""
    query = db.query(TimeSlot).filter(TimeSlot.activo == True)
    
    if dia_semana:
        query = query.filter(TimeSlot.dia_semana == dia_semana)
    if periodo:
        query = query.filter(TimeSlot.periodo == periodo)
    
    slots = query.order_by(TimeSlot.dia_semana, TimeSlot.orden).all()
    
    return [
        {
            "id": slot.id,
            "dia_semana": slot.dia_semana,
            "dia_nombre": slot.dia_nombre,
            "hora_inicio": slot.hora_inicio,
            "hora_fin": slot.hora_fin,
            "periodo": slot.periodo,
            "orden": slot.orden,
            "franja_completa": slot.franja_completa
        }
        for slot in slots
    ]

# Schedule Endpoints
@app.get("/api/schedules")
async def get_schedules(
    semestre: str = None,
    curso_id: int = None,
    profesor_id: int = None,
    db: Session = Depends(get_db)
):
    """Get schedule assignments with optional filtering"""
    query = db.query(ScheduleAssignment)
    
    if semestre:
        query = query.filter(ScheduleAssignment.semestre == semestre)
    if curso_id:
        query = query.filter(ScheduleAssignment.course_id == curso_id)
    if profesor_id:
        query = query.filter(ScheduleAssignment.professor_id == profesor_id)
    
    assignments = query.all()
    
    return [
        {
            "id": assignment.id,
            "course": {
                "codigo": assignment.course.codigo,
                "nombre": assignment.course.nombre,
                "ciclo": assignment.course.ciclo
            },
            "professor": {
                "codigo": assignment.professor.codigo,
                "nombre": assignment.professor.nombre_completo
            },
            "classroom": {
                "codigo": assignment.classroom.codigo,
                "tipo": assignment.classroom.tipo,
                "capacidad": assignment.classroom.capacidad
            },
            "time_slot": {
                "dia": assignment.time_slot.dia_nombre,
                "hora": f"{assignment.time_slot.hora_inicio}-{assignment.time_slot.hora_fin}",
                "periodo": assignment.time_slot.periodo
            },
            "semestre": assignment.semestre,
            "estado": assignment.estado
        }
        for assignment in assignments
    ]

# Utility function for background tasks
async def save_projections_to_db(projections: List, db: Session):
    """Save course projections to database"""
    try:
        for proj_data in projections:
            # Check if course already exists
            existing = db.query(Course).filter(Course.codigo == proj_data.codigo_curso).first()
            
            if existing:
                # Update existing course
                existing.alumnos_teoria = proj_data.alumnos_teoria
                existing.grupos_teoria = proj_data.grupos_teoria
                existing.alumnos_practica = proj_data.alumnos_practica
                existing.grupos_practica = proj_data.grupos_practica
                existing.alumnos_laboratorio = proj_data.alumnos_laboratorio
                existing.grupos_laboratorio = proj_data.grupos_laboratorio
                existing.requiere_laboratorio = proj_data.requiere_laboratorio
                existing.requiere_practica = proj_data.requiere_practica
                existing.modalidad = proj_data.modalidad
            else:
                # Create new course
                course = Course(
                    codigo=proj_data.codigo_curso,
                    nombre=proj_data.nombre_curso,
                    ciclo=proj_data.ciclo,
                    modalidad=proj_data.modalidad,
                    alumnos_teoria=proj_data.alumnos_teoria,
                    grupos_teoria=proj_data.grupos_teoria,
                    alumnos_practica=proj_data.alumnos_practica,
                    grupos_practica=proj_data.grupos_practica,
                    alumnos_laboratorio=proj_data.alumnos_laboratorio,
                    grupos_laboratorio=proj_data.grupos_laboratorio,
                    requiere_laboratorio=proj_data.requiere_laboratorio,
                    requiere_practica=proj_data.requiere_practica
                )
                db.add(course)
        
        db.commit()
        logger.info(f"Successfully saved {len(projections)} course projections to database")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving projections to database: {e}")

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )