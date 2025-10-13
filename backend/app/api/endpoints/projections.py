"""
API Endpoints para gestión de proyecciones (Upload Excel + CRUD)
USANDO proyecciones_loader.py QUE YA FUNCIONA
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from pydantic import BaseModel
import os
import tempfile
import sys
from pathlib import Path

from ...database import get_db
from ...models import Course

# Importar el script que SÍ FUNCIONA
backend_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

try:
    from proyecciones_loader import ProyeccionesLoader
    LOADER_OK = True
    print("[✓] ProyeccionesLoader importado correctamente")
except Exception as e:
    LOADER_OK = False
    print(f"[!] Error: {e}")

router = APIRouter(prefix="/api/projections", tags=["Projections"])

# ============================================================================
# SCHEMAS
# ============================================================================

class CourseProjection(BaseModel):
    codigo: str
    nombre: str
    ciclo: int
    modalidad: str = "PRESENCIAL"
    alumnos_teoria: int
    alumnos_practica: int
    alumnos_laboratorio: int
    grupos_teoria: int = 0
    grupos_practica: int = 0
    grupos_laboratorio: int = 0
    creditos: int
    requiere_laboratorio: bool
    requiere_practica: bool

class ProjectionConfirmData(BaseModel):
    courses: List[CourseProjection]

# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/upload")
async def upload_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload y parseo de Libro1.xlsx
    Retorna datos para confirmación (NO guarda aún)
    """
    
    # Validar extensión
    if not file.filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos .xlsx")
    
    # Guardar temporalmente
    tmp_path = None
    try:
        # Create temp file and get path
        tmp_fd, tmp_path = tempfile.mkstemp(suffix='.xlsx')
        # Write content to temp file
        content = await file.read()
        os.write(tmp_fd, content)
        os.close(tmp_fd)
        # Parsear Excel CON EL SCRIPT QUE SÍ FUNCIONA
        if not LOADER_OK:
            raise HTTPException(status_code=500, detail="ProyeccionesLoader no disponible")
        
        print(f"\n{'='*80}")
        print("PROCESANDO LIBRO1.XLSX CON PROYECCIONES_LOADER")
        print(f"{'='*80}")
        
        # USAR EL SCRIPT QUE SÍ FUNCIONA
        loader = ProyeccionesLoader(excel_path=tmp_path)
        
        # Convertir proyecciones a formato de cursos para el frontend
        courses = []
        for nombre_curso, proyeccion in loader.proyecciones.items():
            # Intentar encontrar el curso en BD por nombre (fuzzy match)
            existing = None
            # Buscar primero por coincidencia exacta en nombre
            exact_match = db.query(Course).filter(Course.nombre == nombre_curso).first()
            if exact_match:
                existing = exact_match
            else:
                # Buscar por coincidencia parcial
                partial_matches = db.query(Course).filter(
                    Course.nombre.like(f"%{nombre_curso[:15]}%")
                ).all()
                if partial_matches:
                    existing = partial_matches[0]  # Tomar el primero
            
            # Si no existe, crear código temporal
            codigo = existing.codigo if existing else f"TEMP_{len(courses)+1:03d}"
            ciclo = existing.ciclo if existing else 1
            creditos = existing.creditos if existing else 3
            modalidad = existing.modalidad if existing else 'PRESENCIAL'
            
            course_data = {
                'codigo': codigo,
                'nombre': nombre_curso,
                'ciclo': ciclo,
                'modalidad': modalidad,
                'alumnos_teoria': proyeccion['teoria'] * 40,  # Estimar 40 alumnos por grupo
                'alumnos_practica': proyeccion['practica'] * 40,
                'alumnos_laboratorio': proyeccion['laboratorio'] * 20,
                'grupos_teoria': proyeccion['teoria'],
                'grupos_practica': proyeccion['practica'],
                'grupos_laboratorio': proyeccion['laboratorio'],
                'creditos': creditos,
                'requiere_laboratorio': proyeccion['laboratorio'] > 0,
                'requiere_practica': proyeccion['practica'] > 0,
                'id': existing.id if existing else None,
                'exists': existing is not None
            }
            
            courses.append(course_data)
        
        print(f"[✓] Procesados {len(courses)} cursos desde Libro1.xlsx")
        
        result = {
            'success': True,
            'courses': courses,
            'total': len(courses)
        }
        
        if not result['success']:
            raise HTTPException(status_code=400, detail="Error procesando Excel")
        
        # Los datos ya están procesados arriba
        return {
            'success': True,
            'message': f"{len(courses)} cursos extraídos. Revisa y confirma.",
            'courses': courses
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # Eliminar archivo temporal
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.post("/confirm")
async def confirm_projections(
    data: ProjectionConfirmData,
    db: Session = Depends(get_db)
):
    """
    Confirmar y guardar proyecciones en BD
    Actualiza cursos existentes o crea nuevos
    """
    
    try:
        updated = 0
        created = 0
        
        for course_data in data.courses:
            course = db.query(Course).filter_by(codigo=course_data.codigo).first()
            
            if course:
                # Actualizar existente CON DATOS DE PROYECCIÓN (mantener nombre de BD)
                course.ciclo = course_data.ciclo
                course.modalidad = course_data.modalidad
                course.alumnos_teoria = course_data.alumnos_teoria
                course.alumnos_practica = course_data.alumnos_practica
                course.alumnos_laboratorio = course_data.alumnos_laboratorio
                course.grupos_teoria = course_data.grupos_teoria
                course.grupos_practica = course_data.grupos_practica
                course.grupos_laboratorio = course_data.grupos_laboratorio
                course.creditos = course_data.creditos
                course.requiere_laboratorio = course_data.requiere_laboratorio
                course.requiere_practica = course_data.requiere_practica
                updated += 1
            else:
                # Crear nuevo
                course = Course(
                    codigo=course_data.codigo,
                    nombre=course_data.nombre,
                    ciclo=course_data.ciclo,
                    modalidad=course_data.modalidad,
                    alumnos_teoria=course_data.alumnos_teoria,
                    alumnos_practica=course_data.alumnos_practica,
                    alumnos_laboratorio=course_data.alumnos_laboratorio,
                    grupos_teoria=course_data.grupos_teoria,
                    grupos_practica=course_data.grupos_practica,
                    grupos_laboratorio=course_data.grupos_laboratorio,
                    creditos=course_data.creditos,
                    requiere_laboratorio=course_data.requiere_laboratorio,
                    requiere_practica=course_data.requiere_practica
                )
                db.add(course)
                created += 1
        
        db.commit()
        
        return {
            'success': True,
            'message': f"Proyecciones guardadas: {created} nuevos, {updated} actualizados",
            'created': created,
            'updated': updated
        }
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al guardar proyecciones: {str(e)}")


@router.get("/courses")
async def get_all_courses(db: Session = Depends(get_db)):
    """Obtener todos los cursos con sus proyecciones"""
    
    courses = db.query(Course).filter_by(active=True).order_by(Course.ciclo, Course.nombre).all()
    
    return {
        'success': True,
        'courses': [
            {
                'id': c.id,
                'codigo': c.codigo,
                'nombre': c.nombre,
                'ciclo': c.ciclo,
                'modalidad': c.modalidad,
                'alumnos_teoria': c.alumnos_teoria,
                'alumnos_practica': c.alumnos_practica,
                'alumnos_laboratorio': c.alumnos_laboratorio,
                'grupos_teoria': c.grupos_teoria,
                'grupos_practica': c.grupos_practica,
                'grupos_laboratorio': c.grupos_laboratorio,
                'creditos': c.creditos,
                'requiere_laboratorio': c.requiere_laboratorio,
                'requiere_practica': c.requiere_practica
            }
            for c in courses
        ],
        'total': len(courses)
    }


@router.put("/courses/{course_id}")
async def update_course(
    course_id: int,
    data: CourseProjection,
    db: Session = Depends(get_db)
):
    """Actualizar un curso específico"""
    
    course = db.query(Course).filter_by(id=course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    
    if data.codigo.upper().strip() != course.codigo.upper().strip():
        existing = db.query(Course).filter_by(codigo=data.codigo.upper().strip()).first()
        if existing:
            raise HTTPException(status_code=400, detail="Ya existe un curso con ese código")
        course.codigo = data.codigo.upper().strip()

    course.nombre = data.nombre.strip()
    course.ciclo = data.ciclo
    course.modalidad = data.modalidad.upper().strip()
    course.alumnos_teoria = data.alumnos_teoria
    course.alumnos_practica = data.alumnos_practica
    course.alumnos_laboratorio = data.alumnos_laboratorio
    course.grupos_teoria = data.grupos_teoria
    course.grupos_practica = data.grupos_practica
    course.grupos_laboratorio = data.grupos_laboratorio
    course.creditos = data.creditos
    course.requiere_laboratorio = data.requiere_laboratorio
    course.requiere_practica = data.requiere_practica
    
    db.commit()
    
    return {'success': True, 'message': 'Curso actualizado'}


@router.post("/courses", status_code=201)
async def create_course(
    data: CourseProjection,
    db: Session = Depends(get_db)
):
    """Crear un curso nuevo manualmente"""

    codigo = data.codigo.upper().strip()
    if not codigo:
        raise HTTPException(status_code=400, detail="El código es obligatorio")

    duplicated = db.query(Course).filter_by(codigo=codigo).first()
    if duplicated:
        raise HTTPException(status_code=400, detail="Ya existe un curso con ese código")

    new_course = Course(
        codigo=codigo,
        nombre=data.nombre.strip(),
        ciclo=data.ciclo,
        modalidad=data.modalidad.upper().strip(),
        alumnos_teoria=data.alumnos_teoria,
        alumnos_practica=data.alumnos_practica,
        alumnos_laboratorio=data.alumnos_laboratorio,
        grupos_teoria=data.grupos_teoria,
        grupos_practica=data.grupos_practica,
        grupos_laboratorio=data.grupos_laboratorio,
        creditos=data.creditos,
        requiere_laboratorio=data.requiere_laboratorio,
        requiere_practica=data.requiere_practica,
        active=True
    )

    db.add(new_course)
    db.commit()
    db.refresh(new_course)

    return {
        'success': True,
        'message': 'Curso creado',
        'course': {
            'id': new_course.id,
            'codigo': new_course.codigo,
            'nombre': new_course.nombre,
            'ciclo': new_course.ciclo,
            'modalidad': new_course.modalidad,
            'alumnos_teoria': new_course.alumnos_teoria,
            'alumnos_practica': new_course.alumnos_practica,
            'alumnos_laboratorio': new_course.alumnos_laboratorio,
            'grupos_teoria': new_course.grupos_teoria,
            'grupos_practica': new_course.grupos_practica,
            'grupos_laboratorio': new_course.grupos_laboratorio,
            'creditos': new_course.creditos,
            'requiere_laboratorio': new_course.requiere_laboratorio,
            'requiere_practica': new_course.requiere_practica
        }
    }


@router.delete("/courses/{course_id}")
async def delete_course(course_id: int, db: Session = Depends(get_db)):
    """Eliminar un curso (soft delete)"""
    
    course = db.query(Course).filter_by(id=course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    
    course.active = False
    db.commit()
    
    return {'success': True, 'message': 'Curso eliminado'}
