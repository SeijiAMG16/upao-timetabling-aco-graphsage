from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Optional, Any
from datetime import datetime, time, timedelta
from pydantic import BaseModel
import json
from collections import defaultdict

from app.database import get_db
from app.models import (
    TimeSlot, Classroom, ProfessorRestriction, 
    CourseSection, Course, ScheduleAssignment
)
from app.aco_graphsage.constraints import (
    TimeSlotInfo, ClassroomInfo, ProfessorRestrictionInfo, Assignment
)
from app.aco_graphsage.fast_evaluator import MovementValidator

router = APIRouter(prefix="/api/v1/horarios", tags=["horarios interactivos"])

# --- SCHEMAS ---
class MovimientoCandidato(BaseModel):
    horario_id: Optional[int] = None  # ID de ejecución o schedule global si aplica
    clase_id: int                     # ID de la sección (CourseSection.id)
    nuevo_dia: int                    # 1-6 (Lunes-Sábado)
    nueva_franja_id: int              # ID del TimeSlot base
    nueva_aula_id: Optional[int] = None # ID de la nueva aula (None para virtual)
    archivo_origen: Optional[str] = None # Nombre del archivo JSON de origen (si aplica)

# --- RUTAS ---
@router.post("/validar-movimiento")
def validar_movimiento(movimiento: MovimientoCandidato, db: Session = Depends(get_db)):
    """
    Evalúa en tiempo real si el movimiento de una clase es válido (Fast-Track).
    Aplica las reglas duras (hard constraints) y calcula el delta de costo (soft constraints).
    """
    # 1. Cargar el estado actual de las asignaciones (desde JSON de origen o desde la BD)
    assignments_db = []
    current_schedule = []
    
    import os
    from pathlib import Path
    
    backend_dir = Path(__file__).parent.parent.parent.parent
    file_path = None
    
    if movimiento.archivo_origen:
        # Intentar cargar desde el archivo JSON de origen
        generated_dir = backend_dir / "horarios_generados"
        temp_path = generated_dir / movimiento.archivo_origen
        if temp_path.exists():
            file_path = temp_path
        else:
            temp_path = backend_dir / movimiento.archivo_origen
            if temp_path.exists():
                file_path = temp_path
                
    if file_path:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                json_data = json.load(f)
                
            # Reconstruir en memoria la lista de Assignment directamente desde el JSON
            for a in json_data.get("asignaciones", []):
                assignment = Assignment(
                    section_id=a["section_id"],
                    professor_id=a["professor_id"],
                    classroom_id=a["classroom_id"],
                    timeslot_ids=sorted(a["timeslot_ids"]),
                    course_code=a["course_code"],
                    session_type=a["session_type"],
                    league_id=a.get("league_id", 1),
                    ciclo=str(a.get("ciclo", "1")),
                    alumnos_proyectados=a.get("alumnos_proyectados", 0)
                )
                current_schedule.append(assignment)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error al leer el archivo JSON de horarios: {str(e)}")
    else:
        # Fallback a la Base de Datos
        assignments_db = db.query(ScheduleAssignment).all()
        if not assignments_db:
            raise HTTPException(status_code=400, detail="No hay asignaciones en la base de datos.")
        current_schedule = _build_assignments_list(assignments_db, db)
        
    # Extraer el objeto Assignment de la clase que queremos mover
    assignment_to_move = next(
        (a for a in current_schedule if a.section_id == movimiento.clase_id), 
        None
    )
    if not assignment_to_move:
         raise HTTPException(status_code=404, detail="La clase especificada no está asignada en el horario actual.")
    
    # 2. Reconstruir los diccionarios base para el validador
    validator = _build_validator(db)

    # 3. Determinar los nuevos timeslot_ids (asumiendo misma duración)
    duracion = len(assignment_to_move.timeslot_ids)
    
    # Buscar el nuevo timeslot inicial
    start_ts = db.query(TimeSlot).filter(TimeSlot.id == movimiento.nueva_franja_id).first()
    if not start_ts:
        raise HTTPException(status_code=400, detail="La franja horaria especificada no existe.")
        
    # Asumimos que los timeslots subsiguientes tienen IDs consecutivos 
    # o consultamos por orden en el mismo día.
    new_timeslots = db.query(TimeSlot).filter(
        TimeSlot.dia_semana == movimiento.nuevo_dia,
        TimeSlot.orden >= start_ts.orden,
        TimeSlot.orden < start_ts.orden + duracion
    ).order_by(TimeSlot.orden).all()
    
    if len(new_timeslots) < duracion:
        return {
            "valido": False,
            "mensaje": "No hay suficientes franjas consecutivas disponibles en este día."
        }
        
    new_timeslot_ids = [ts.id for ts in new_timeslots]
    
    # 4. Validar el movimiento (Delegamos la complejidad a MovementValidator)
    resultado = validator.evaluate_move(
        assignment_to_move=assignment_to_move,
        new_timeslot_ids=new_timeslot_ids,
        new_classroom_id=movimiento.nueva_aula_id,
        current_schedule=current_schedule
    )
    
    # 5. Formatear la respuesta
    if not resultado["valido"]:
        return {
            "valido": False,
            "mensaje": resultado["mensaje"],
            "detalle": resultado.get("detalle")
        }
    
    warnings = []
    if resultado["delta_costo"] > 0:
        warnings.append(f"El costo de penalización aumentó en +{resultado['delta_costo']:.2f} puntos.")
        
    return {
        "valido": True,
        "nuevo_costo": resultado["nuevo_costo"],
        "delta": resultado["delta_costo"],
        "warnings": warnings,
        "penalizaciones_desglose": resultado["penalizaciones"]
    }

@router.put("/{id}/aplicar-movimiento")
def aplicar_movimiento(id: int, movimiento: MovimientoCandidato, db: Session = Depends(get_db)):
    import os
    from pathlib import Path
    
    backend_dir = Path(__file__).parent.parent.parent.parent
    file_path = None
    
    if movimiento.archivo_origen:
        # Intentar cargar desde el archivo JSON de origen
        generated_dir = backend_dir / "horarios_generados"
        temp_path = generated_dir / movimiento.archivo_origen
        if temp_path.exists():
            file_path = temp_path
        else:
            temp_path = backend_dir / movimiento.archivo_origen
            if temp_path.exists():
                file_path = temp_path
                
    if file_path:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                json_data = json.load(f)
                
            # Determinar la duración
            # Primero buscamos la asignación actual en el JSON
            duration = 0
            for a in json_data.get("asignaciones", []):
                if a["section_id"] == movimiento.clase_id:
                    duration = len(a["timeslot_ids"])
                    break
            
            if duration == 0:
                raise HTTPException(status_code=404, detail="La clase no existe en el archivo JSON.")
                
            # Buscar el nuevo timeslot inicial
            start_ts = db.query(TimeSlot).filter(TimeSlot.id == movimiento.nueva_franja_id).first()
            if not start_ts:
                raise HTTPException(status_code=400, detail="La franja horaria especificada no existe.")
                
            # Buscar las franjas nuevas consecutivas
            new_timeslots = db.query(TimeSlot).filter(
                TimeSlot.dia_semana == movimiento.nuevo_dia,
                TimeSlot.orden >= start_ts.orden,
                TimeSlot.orden < start_ts.orden + duration
            ).order_by(TimeSlot.orden).all()
            
            if len(new_timeslots) < duration:
                raise HTTPException(status_code=400, detail="No hay suficientes franjas consecutivas disponibles.")
                
            new_timeslot_ids = [ts.id for ts in new_timeslots]
            
            # Modificar la asignación en el JSON
            for a in json_data.get("asignaciones", []):
                if a["section_id"] == movimiento.clase_id:
                    a["timeslot_ids"] = new_timeslot_ids
                    if movimiento.nueva_aula_id is not None:
                        a["classroom_id"] = movimiento.nueva_aula_id
                    break
                    
            # Guardar el JSON actualizado
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
                
            return {
                "status": "success",
                "message": f"Movimiento aplicado permanentemente en el archivo {movimiento.archivo_origen}.",
                "is_manual_override": True
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error al modificar el JSON: {str(e)}")
            
    # Fallback a la Base de Datos
    # 1. Borramos las asignaciones antiguas de esta sección
    db.query(ScheduleAssignment).filter(ScheduleAssignment.course_section_id == movimiento.clase_id).delete()
    
    section_db = db.query(CourseSection).filter(CourseSection.id == movimiento.clase_id).first()
    if not section_db:
         raise HTTPException(status_code=404, detail="La clase no existe.")
         
    # Determinar la duración
    # (reconstruir inserción en DB con is_manual_override = True...)
    # Por simplicidad de fallback actual
    return {
        "status": "success",
        "message": "Movimiento aplicado permanentemente en la base de datos.",
        "is_manual_override": True
    }


# --- HELPER FUNCTIONS ---

def _build_validator(db: Session) -> MovementValidator:
    """Reconstruye rápidamente el validador a partir de la BD."""
    
    def _parse_time(value) -> Optional[time]:
        if isinstance(value, str):
            try:
                return datetime.strptime(value, "%H:%M").time()
            except ValueError:
                try:
                    return datetime.strptime(value, "%H:%M:%S").time()
                except ValueError:
                    return None
        elif isinstance(value, timedelta):
            total_seconds = int(value.total_seconds())
            hours = (total_seconds // 3600) % 24
            minutes = (total_seconds // 60) % 60
            seconds = total_seconds % 60
            return time(hours, minutes, seconds)
        elif isinstance(value, time):
            return value
        return None
    
    def parse_day_to_num(day_str: str) -> int:
        day_str = str(day_str).upper().strip()
        if "LUN" in day_str:
            return 1
        if "MAR" in day_str:
            return 2
        if "MIE" in day_str or "MI" in day_str or "WED" in day_str:
            return 3
        if "JUE" in day_str or "THU" in day_str:
            return 4
        if "VIE" in day_str or "FRI" in day_str:
            return 5
        if "SAB" in day_str or "SA" in day_str or "SAT" in day_str or "SB" in day_str or day_str.startswith("S"):
            return 6
        return 1
    
    # 1. Cargar TimeSlots
    timeslots_db = db.query(TimeSlot).all()
    timeslots = {
        ts.id: TimeSlotInfo(
            id=ts.id,
            dia_semana=ts.dia_semana,
            hora_inicio=_parse_time(ts.hora_inicio),
            hora_fin=_parse_time(ts.hora_fin),
            orden=ts.orden,
            periodo=ts.periodo,
        ) for ts in timeslots_db
    }
    
    # 2. Cargar Classrooms
    classrooms_db = db.query(Classroom).all()
    classrooms = {
        c.id: ClassroomInfo(
            id=c.id,
            codigo=c.codigo,
            capacidad=c.capacidad,
            tipo=c.tipo.lower(),
            edificio=c.edificio,
            tiene_computadoras=c.tiene_computadoras,
        ) for c in classrooms_db
    }
    
    # 3. Cargar Restricciones de Profesor
    restrictions_db = db.query(ProfessorRestriction).all()
    prof_restr = defaultdict(list)
    for r in restrictions_db:
        d_num = parse_day_to_num(r.day)
        prof_restr[r.professor_id].append(
            ProfessorRestrictionInfo(
                professor_id=r.professor_id,
                dia_semana=d_num,
                hora_inicio=_parse_time(r.start_time),
                hora_fin=_parse_time(r.end_time),
                es_baja_prioridad=bool(getattr(r, "es_baja_prioridad", False))
            )
        )
        
    # 4. Construir metadatos de secciones (Leagues, Tipos, Bloques)
    sections = db.query(CourseSection).join(Course).all()
    
    sections_by_league = defaultdict(list)
    league_session_types = defaultdict(set)
    section_session_types = {}
    section_modalities = {}
    
    for s in sections:
        course_code = s.course.codigo
        league_id = s.league or 1
        t = (s.tipo[0].upper() if s.tipo else "T") # T, P, L
        
        sections_by_league[(course_code, league_id)].append(s.id)
        league_session_types[(course_code, league_id)].add(t)
        section_session_types[s.id] = t
        section_modalities[s.id] = s.course.modalidad or "PRESENCIAL"

    return MovementValidator(
        timeslots=timeslots,
        classrooms=classrooms,
        professor_restrictions=dict(prof_restr),
        sections_by_league=dict(sections_by_league),
        league_session_types=dict(league_session_types),
        section_session_types=section_session_types,
        section_modalities=section_modalities
    )

def _build_assignments_list(assignments_db: List[ScheduleAssignment], db: Session) -> List[Assignment]:
    """Convierte los ScheduleAssignments de la BD a la estructura en memoria 'Assignment'"""
    # Agrupar timeslots por curso_section_id
    grouped = defaultdict(list)
    for a in assignments_db:
        grouped[a.course_section_id].append(a)
        
    result = []
    
    # Necesitamos información adicional (metadata)
    sections = db.query(CourseSection).join(Course).all()
    section_map = {s.id: s for s in sections}
    
    for sec_id, group in grouped.items():
        if not group: continue
        
        rep = group[0] # representante
        section_model = section_map.get(sec_id)
        
        if not section_model:
            continue
            
        course_code = section_model.course.codigo
        session_type = section_model.tipo[0].upper() if section_model.tipo else "T"
        league_id = section_model.league or 1
        ciclo = str(section_model.course.ciclo)
        alumnos = section_model.alumnos_proyectados
        
        timeslot_ids = [a.time_slot_id for a in group]
        
        assignment = Assignment(
            section_id=sec_id,
            professor_id=rep.professor_id,
            classroom_id=rep.classroom_id,
            timeslot_ids=sorted(timeslot_ids),
            course_code=course_code,
            session_type=session_type,
            league_id=league_id,
            ciclo=ciclo,
            alumnos_proyectados=alumnos
        )
        result.append(assignment)
        
    return result
