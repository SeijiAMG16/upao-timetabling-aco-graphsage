"""
API Endpoints para gestión de aulas/salones (CRUD)
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from ...database import get_db
from ...models import Classroom

router = APIRouter(prefix="/api/classrooms", tags=["Classrooms"])

# ============================================================================
# SCHEMAS
# ============================================================================

class ClassroomCreate(BaseModel):
    codigo: str
    edificio: str
    piso: int
    capacidad: int
    tipo: str = 'Aula'
    tiene_computadoras: bool = False
    numero_computadoras: int = 0

class ClassroomUpdate(BaseModel):
    edificio: Optional[str] = None
    piso: Optional[int] = None
    capacidad: Optional[int] = None
    tipo: Optional[str] = None
    tiene_computadoras: Optional[bool] = None
    numero_computadoras: Optional[int] = None

# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("")
async def get_classrooms(
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """Obtener todas las aulas"""
    
    query = db.query(Classroom)
    if active_only:
        query = query.filter_by(active=True)
    
    classrooms = query.order_by(Classroom.codigo).all()
    
    return {
        'success': True,
        'classrooms': [
            {
                'id': c.id,
                'codigo': c.codigo,
                'edificio': c.edificio,
                'piso': c.piso,
                'capacidad': c.capacidad,
                'tipo': c.tipo,
                'tiene_computadoras': c.tiene_computadoras,
                'numero_computadoras': c.numero_computadoras
            }
            for c in classrooms
        ],
        'total': len(classrooms)
    }


@router.post("")
async def create_classroom(
    data: ClassroomCreate,
    db: Session = Depends(get_db)
):
    """Crear una nueva aula"""
    
    # Verificar que no exista el código
    existing = db.query(Classroom).filter_by(codigo=data.codigo).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Ya existe un aula con código {data.codigo}")
    
    classroom = Classroom(
        codigo=data.codigo,
        edificio=data.edificio,
        piso=data.piso,
        capacidad=data.capacidad,
        tipo=data.tipo,
        tiene_computadoras=data.tiene_computadoras,
        numero_computadoras=data.numero_computadoras
    )
    
    db.add(classroom)
    db.commit()
    db.refresh(classroom)
    
    return {
        'success': True,
        'message': 'Aula creada correctamente',
        'classroom_id': classroom.id
    }


@router.put("/{classroom_id}")
async def update_classroom(
    classroom_id: int,
    data: ClassroomUpdate,
    db: Session = Depends(get_db)
):
    """Actualizar un aula existente"""
    
    classroom = db.query(Classroom).filter_by(id=classroom_id).first()
    if not classroom:
        raise HTTPException(status_code=404, detail="Aula no encontrada")
    
    if data.edificio is not None:
        classroom.edificio = data.edificio
    if data.piso is not None:
        classroom.piso = data.piso
    if data.capacidad is not None:
        classroom.capacidad = data.capacidad
    if data.tipo is not None:
        classroom.tipo = data.tipo
    if data.tiene_computadoras is not None:
        classroom.tiene_computadoras = data.tiene_computadoras
    if data.numero_computadoras is not None:
        classroom.numero_computadoras = data.numero_computadoras
    
    db.commit()
    
    return {
        'success': True,
        'message': 'Aula actualizada correctamente'
    }


@router.delete("/{classroom_id}")
async def delete_classroom(classroom_id: int, db: Session = Depends(get_db)):
    """Eliminar un aula (soft delete)"""
    
    classroom = db.query(Classroom).filter_by(id=classroom_id).first()
    if not classroom:
        raise HTTPException(status_code=404, detail="Aula no encontrada")
    
    classroom.active = False
    db.commit()
    
    return {
        'success': True,
        'message': 'Aula eliminada correctamente'
    }
