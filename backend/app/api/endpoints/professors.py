"""
API Endpoints para gestión de profesores (CRUD simplificado)
Actualizado después de la migración de limpieza de columnas
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from ...database import get_db
from ...models import Professor

router = APIRouter(prefix="/api/professors", tags=["Professors"])

# ============================================================================
# SCHEMAS ACTUALIZADOS
# ============================================================================

class ProfessorCreate(BaseModel):
    codigo: str
    nombre_completo: str

class ProfessorUpdate(BaseModel):
    codigo: Optional[str] = None
    nombre_completo: Optional[str] = None

# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("")
@router.get("/")
async def get_professors(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    """Obtener lista de profesores"""
    
    professors = (
        db.query(Professor)
        .order_by(Professor.nombre_completo)
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    return {
        'success': True,
        'professors': [
            {
                'id': p.id,
                'codigo': p.codigo,
                'nombre_completo': p.nombre_completo
            }
            for p in professors
        ],
        'total': len(professors)
    }

@router.get("/{professor_id}")
async def get_professor(professor_id: int, db: Session = Depends(get_db)):
    """Obtener un profesor específico"""
    
    professor = db.query(Professor).filter_by(id=professor_id).first()
    if not professor:
        raise HTTPException(status_code=404, detail="Profesor no encontrado")
    
    return {
        'success': True,
        'professor': {
            'id': professor.id,
            'codigo': professor.codigo,
            'nombre_completo': professor.nombre_completo
        }
    }

@router.post("")
@router.post("/")
async def create_professor(data: ProfessorCreate, db: Session = Depends(get_db)):
    """Crear un nuevo profesor"""
    
    # Verificar que no exista el código
    existing = db.query(Professor).filter_by(codigo=data.codigo).first()
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe un profesor con ese código")
    
    professor = Professor(
        codigo=data.codigo,
        nombre_completo=data.nombre_completo
    )
    
    db.add(professor)
    db.commit()
    db.refresh(professor)
    
    return {
        'success': True,
        'message': 'Profesor creado exitosamente',
        'professor': {
            'id': professor.id,
            'codigo': professor.codigo,
            'nombre_completo': professor.nombre_completo
        }
    }

@router.put("/{professor_id}")
async def update_professor(professor_id: int, data: ProfessorUpdate, db: Session = Depends(get_db)):
    """Actualizar un profesor"""
    
    professor = db.query(Professor).filter_by(id=professor_id).first()
    if not professor:
        raise HTTPException(status_code=404, detail="Profesor no encontrado")
    
    # Actualizar campos si se proporcionan
    if data.codigo is not None and data.codigo != professor.codigo:
        duplicate = db.query(Professor).filter(Professor.codigo == data.codigo).first()
        if duplicate:
            raise HTTPException(status_code=400, detail="Ya existe un profesor con ese código")
        professor.codigo = data.codigo
    if data.nombre_completo is not None:
        professor.nombre_completo = data.nombre_completo
    
    db.commit()
    
    return {
        'success': True,
        'message': 'Profesor actualizado exitosamente'
    }

@router.delete("/{professor_id}")
async def delete_professor(professor_id: int, db: Session = Depends(get_db)):
    """Eliminar (desactivar) un profesor"""
    
    professor = db.query(Professor).filter_by(id=professor_id).first()
    if not professor:
        raise HTTPException(status_code=404, detail="Profesor no encontrado")
    
    db.delete(professor)
    db.commit()

    return {
        'success': True,
        'message': 'Profesor eliminado exitosamente'
    }