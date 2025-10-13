"""
API Endpoints para gestión de profesores (CRUD completo)
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from ...database import get_db
from ...models import Professor

router = APIRouter(prefix="/api/professors", tags=["Professors"])

# ============================================================================
# SCHEMAS
# ============================================================================

class ProfessorCreate(BaseModel):
    codigo: str
    nombres: str
    apellidos: str
    categoria: str = 'TC'
    carga_maxima_horas: int = 20
    lunes_disponible: bool = True
    martes_disponible: bool = True
    miercoles_disponible: bool = True
    jueves_disponible: bool = True
    viernes_disponible: bool = True
    sabado_disponible: bool = True

class ProfessorUpdate(BaseModel):
    nombres: Optional[str] = None
    apellidos: Optional[str] = None
    categoria: Optional[str] = None
    carga_maxima_horas: Optional[int] = None
    lunes_disponible: Optional[bool] = None
    martes_disponible: Optional[bool] = None
    miercoles_disponible: Optional[bool] = None
    jueves_disponible: Optional[bool] = None
    viernes_disponible: Optional[bool] = None
    sabado_disponible: Optional[bool] = None

# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("")
async def get_professors(
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """Obtener todos los profesores"""
    
    query = db.query(Professor)
    if active_only:
        query = query.filter_by(active=True)
    
    professors = query.order_by(Professor.nombre_completo).all()
    
    return {
        'success': True,
        'professors': [
            {
                'id': p.id,
                'codigo': p.codigo,
                'nombre_completo': p.nombre_completo,
                'carga_maxima_horas': p.carga_maxima_horas,
                'disponible_lunes': p.disponible_lunes,
                'disponible_martes': p.disponible_martes,
                'disponible_miercoles': p.disponible_miercoles,
                'disponible_jueves': p.disponible_jueves,
                'disponible_viernes': p.disponible_viernes,
                'disponible_sabado': p.disponible_sabado,
                'prefiere_manana': p.prefiere_manana,
                'prefiere_tarde': p.prefiere_tarde,
                'prefiere_noche': p.prefiere_noche,
                'active': p.active
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
            'nombres': professor.nombres,
            'apellidos': professor.apellidos,
            'nombre_completo': professor.nombre_completo,
            'categoria': professor.categoria,
            'carga_maxima_horas': professor.carga_maxima_horas
        }
    }


@router.post("")
async def create_professor(
    data: ProfessorCreate,
    db: Session = Depends(get_db)
):
    """Crear un nuevo profesor"""
    
    # Verificar que no exista el código
    existing = db.query(Professor).filter_by(codigo=data.codigo).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Ya existe un profesor con código {data.codigo}")
    
    professor = Professor(
        codigo=data.codigo,
        nombres=data.nombres,
        apellidos=data.apellidos,
        nombre_completo=f"{data.apellidos}, {data.nombres}",
        categoria=data.categoria,
        carga_maxima_horas=data.carga_maxima_horas,
        lunes_disponible=data.lunes_disponible,
        martes_disponible=data.martes_disponible,
        miercoles_disponible=data.miercoles_disponible,
        jueves_disponible=data.jueves_disponible,
        viernes_disponible=data.viernes_disponible,
        sabado_disponible=data.sabado_disponible
    )
    
    db.add(professor)
    db.commit()
    db.refresh(professor)
    
    return {
        'success': True,
        'message': 'Profesor creado correctamente',
        'professor_id': professor.id
    }


@router.put("/{professor_id}")
async def update_professor(
    professor_id: int,
    data: ProfessorUpdate,
    db: Session = Depends(get_db)
):
    """Actualizar un profesor existente"""
    
    professor = db.query(Professor).filter_by(id=professor_id).first()
    if not professor:
        raise HTTPException(status_code=404, detail="Profesor no encontrado")
    
    if data.nombres is not None:
        professor.nombres = data.nombres
    if data.apellidos is not None:
        professor.apellidos = data.apellidos
    
    # Actualizar nombre_completo si cambió nombres o apellidos
    if data.nombres is not None or data.apellidos is not None:
        professor.nombre_completo = f"{professor.apellidos}, {professor.nombres}"
    
    if data.categoria is not None:
        professor.categoria = data.categoria
    if data.carga_maxima_horas is not None:
        professor.carga_maxima_horas = data.carga_maxima_horas
    
    if data.lunes_disponible is not None:
        professor.lunes_disponible = data.lunes_disponible
    if data.martes_disponible is not None:
        professor.martes_disponible = data.martes_disponible
    if data.miercoles_disponible is not None:
        professor.miercoles_disponible = data.miercoles_disponible
    if data.jueves_disponible is not None:
        professor.jueves_disponible = data.jueves_disponible
    if data.viernes_disponible is not None:
        professor.viernes_disponible = data.viernes_disponible
    if data.sabado_disponible is not None:
        professor.sabado_disponible = data.sabado_disponible
    
    db.commit()
    
    return {
        'success': True,
        'message': 'Profesor actualizado correctamente'
    }


@router.delete("/{professor_id}")
async def delete_professor(professor_id: int, db: Session = Depends(get_db)):
    """Eliminar un profesor (soft delete)"""
    
    professor = db.query(Professor).filter_by(id=professor_id).first()
    if not professor:
        raise HTTPException(status_code=404, detail="Profesor no encontrado")
    
    professor.active = False
    db.commit()
    
    return {
        'success': True,
        'message': 'Profesor eliminado correctamente'
    }
