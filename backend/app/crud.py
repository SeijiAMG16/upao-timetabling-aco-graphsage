"""
CRUD Operations for UPAO Timetabling System
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional, Dict, Any
from . import models, schemas
import json

# Course CRUD operations
def get_course(db: Session, course_id: int) -> Optional[models.Course]:
    return db.query(models.Course).filter(models.Course.id == course_id).first()

def get_course_by_codigo(db: Session, codigo: str) -> Optional[models.Course]:
    return db.query(models.Course).filter(models.Course.codigo == codigo).first()

def get_courses(db: Session, skip: int = 0, limit: int = 100, ciclo: Optional[int] = None, modalidad: Optional[str] = None) -> List[models.Course]:
    query = db.query(models.Course).filter(models.Course.active == True)
    
    if ciclo:
        query = query.filter(models.Course.ciclo == ciclo)
    if modalidad:
        query = query.filter(models.Course.modalidad == modalidad)
    
    return query.offset(skip).limit(limit).all()

def create_course(db: Session, course_data: dict) -> models.Course:
    db_course = models.Course(
        codigo=course_data['codigo_completo'],
        nombre=course_data['nombre_asignatura'],
        ciclo=course_data['ciclo_numerico'],
        modalidad=course_data['modalidad'],
        alumnos_teoria=course_data['alumnos_teoria'],
        alumnos_practica=course_data['alumnos_practica'],
        alumnos_laboratorio=course_data['alumnos_laboratorio'],
        grupos_teoria=course_data['grupos_teoria'],
        grupos_practica=course_data['grupos_practica'],
        grupos_laboratorio=course_data['grupos_laboratorio'],
        requiere_laboratorio=course_data['requiere_laboratorio'],
        requiere_practica=course_data['requiere_practica'],
        creditos=course_data.get('creditos', 3)
    )
    db.add(db_course)
    db.commit()
    db.refresh(db_course)
    return db_course

def update_course(db: Session, course_id: int, course_data: dict) -> Optional[models.Course]:
    db_course = get_course(db, course_id)
    if db_course:
        for key, value in course_data.items():
            if hasattr(db_course, key):
                setattr(db_course, key, value)
        db.commit()
        db.refresh(db_course)
    return db_course

# Professor CRUD operations
def get_professor(db: Session, professor_id: int) -> Optional[models.Professor]:
    return db.query(models.Professor).filter(models.Professor.id == professor_id).first()

def get_professor_by_codigo(db: Session, codigo: str) -> Optional[models.Professor]:
    return db.query(models.Professor).filter(models.Professor.codigo == codigo).first()

def get_professors(db: Session, skip: int = 0, limit: int = 100) -> List[models.Professor]:
    return (
        db.query(models.Professor)
        .order_by(models.Professor.nombre_completo)
        .offset(skip)
        .limit(limit)
        .all()
    )

def create_professor(db: Session, professor_data: dict) -> models.Professor:
    nombre = professor_data.get('nombre_completo')
    if not nombre:
        nombre = f"{professor_data.get('nombres', '').strip()} {professor_data.get('apellidos', '').strip()}".strip()
    db_professor = models.Professor(
        codigo=professor_data['codigo'],
        nombre_completo=nombre
    )
    db.add(db_professor)
    db.commit()
    db.refresh(db_professor)
    return db_professor

# Classroom CRUD operations
def get_classroom(db: Session, classroom_id: int) -> Optional[models.Classroom]:
    return db.query(models.Classroom).filter(models.Classroom.id == classroom_id).first()

def get_classroom_by_codigo(db: Session, codigo: str) -> Optional[models.Classroom]:
    return db.query(models.Classroom).filter(models.Classroom.codigo == codigo).first()

def get_classrooms(db: Session, edificio: Optional[str] = None, tipo: Optional[str] = None) -> List[models.Classroom]:
    query = db.query(models.Classroom).filter(models.Classroom.disponible == True)
    
    if edificio:
        query = query.filter(models.Classroom.edificio == edificio)
    if tipo:
        query = query.filter(models.Classroom.tipo == tipo)
    
    return query.all()

def create_classroom(db: Session, classroom_data: dict) -> models.Classroom:
    db_classroom = models.Classroom(
        codigo=classroom_data['codigo'],
        edificio=classroom_data['edificio'],
        piso=classroom_data['piso'],
        capacidad=classroom_data['capacidad'],
        tipo=classroom_data['tipo'],
        tiene_proyector=classroom_data.get('tiene_proyector', True),
        tiene_aire_acondicionado=classroom_data.get('tiene_aire_acondicionado', True),
        tiene_computadoras=classroom_data.get('tiene_computadoras', False),
        numero_computadoras=classroom_data.get('numero_computadoras', 0)
    )
    db.add(db_classroom)
    db.commit()
    db.refresh(db_classroom)
    return db_classroom

# TimeSlot CRUD operations
def get_time_slots(db: Session, dia_semana: Optional[int] = None, periodo: Optional[str] = None) -> List[models.TimeSlot]:
    query = db.query(models.TimeSlot).filter(models.TimeSlot.activo == True)
    
    if dia_semana:
        query = query.filter(models.TimeSlot.dia_semana == dia_semana)
    if periodo:
        query = query.filter(models.TimeSlot.periodo == periodo)
    
    return query.order_by(models.TimeSlot.dia_semana, models.TimeSlot.orden).all()

def create_time_slot(db: Session, time_slot_data: dict) -> models.TimeSlot:
    db_time_slot = models.TimeSlot(
        dia_semana=time_slot_data['dia_semana'],
        hora_inicio=time_slot_data['hora_inicio'],
        hora_fin=time_slot_data['hora_fin'],
        periodo=time_slot_data['periodo'],
        orden=time_slot_data['orden']
    )
    db.add(db_time_slot)
    db.commit()
    db.refresh(db_time_slot)
    return db_time_slot

# CourseSection CRUD operations
def get_course_sections(db: Session, course_id: Optional[int] = None) -> List[models.CourseSection]:
    query = db.query(models.CourseSection).filter(models.CourseSection.activa == True)
    
    if course_id:
        query = query.filter(models.CourseSection.course_id == course_id)
    
    return query.all()

def create_course_sections_from_projections(db: Session, course: models.Course) -> List[models.CourseSection]:
    """Crea secciones de curso basado en las proyecciones"""
    sections = []
    
    # Secciones de teoría
    for i in range(course.grupos_teoria):
        section = models.CourseSection(
            course_id=course.id,
            tipo='teoria',
            seccion=chr(65 + i),  # A, B, C, etc.
            alumnos_proyectados=course.alumnos_teoria // course.grupos_teoria if course.grupos_teoria > 0 else 0
        )
        db.add(section)
        sections.append(section)
    
    # Secciones de práctica
    for i in range(course.grupos_practica):
        section = models.CourseSection(
            course_id=course.id,
            tipo='practica',
            seccion=chr(65 + i),  # A, B, C, etc.
            alumnos_proyectados=course.alumnos_practica // course.grupos_practica if course.grupos_practica > 0 else 0
        )
        db.add(section)
        sections.append(section)
    
    # Secciones de laboratorio
    for i in range(course.grupos_laboratorio):
        section = models.CourseSection(
            course_id=course.id,
            tipo='laboratorio',
            seccion=chr(65 + i),  # A, B, C, etc.
            alumnos_proyectados=course.alumnos_laboratorio // course.grupos_laboratorio if course.grupos_laboratorio > 0 else 0
        )
        db.add(section)
        sections.append(section)
    
    db.commit()
    return sections

# ScheduleAssignment CRUD operations
def get_schedule_assignments(db: Session, semestre: Optional[str] = None, course_id: Optional[int] = None, professor_id: Optional[int] = None) -> List[models.ScheduleAssignment]:
    query = db.query(models.ScheduleAssignment)
    
    if semestre:
        query = query.filter(models.ScheduleAssignment.semestre == semestre)
    if course_id:
        query = query.filter(models.ScheduleAssignment.course_id == course_id)
    if professor_id:
        query = query.filter(models.ScheduleAssignment.professor_id == professor_id)
    
    return query.all()

def create_schedule_assignment(db: Session, assignment_data: dict) -> models.ScheduleAssignment:
    db_assignment = models.ScheduleAssignment(
        course_id=assignment_data['course_id'],
        course_section_id=assignment_data['course_section_id'],
        professor_id=assignment_data['professor_id'],
        classroom_id=assignment_data['classroom_id'],
        time_slot_id=assignment_data['time_slot_id'],
        semestre=assignment_data['semestre'],
        estado=assignment_data.get('estado', 'programado'),
        generado_por_algoritmo=assignment_data.get('generado_por_algoritmo', False),
        confianza_asignacion=assignment_data.get('confianza_asignacion')
    )
    db.add(db_assignment)
    db.commit()
    db.refresh(db_assignment)
    return db_assignment

def delete_schedule_assignment(db: Session, assignment_id: int) -> bool:
    db_assignment = db.query(models.ScheduleAssignment).filter(models.ScheduleAssignment.id == assignment_id).first()
    if db_assignment:
        db.delete(db_assignment)
        db.commit()
        return True
    return False

def get_conflicting_assignments(db: Session, time_slot_id: int, professor_id: Optional[int] = None, classroom_id: Optional[int] = None) -> List[models.ScheduleAssignment]:
    """Obtiene asignaciones que conflictan en la misma franja horaria"""
    query = db.query(models.ScheduleAssignment).filter(models.ScheduleAssignment.time_slot_id == time_slot_id)
    
    if professor_id:
        query = query.filter(models.ScheduleAssignment.professor_id == professor_id)
    if classroom_id:
        query = query.filter(models.ScheduleAssignment.classroom_id == classroom_id)
    
    return query.all()

# Professor Availability CRUD operations
def get_professor_availability(db: Session, professor_id: int) -> List[models.ProfessorAvailability]:
    return db.query(models.ProfessorAvailability).filter(
        models.ProfessorAvailability.professor_id == professor_id,
        models.ProfessorAvailability.disponible == True
    ).all()

def create_professor_availability(db: Session, professor_id: int, time_slot_id: int, preferencia: str = 'normal') -> models.ProfessorAvailability:
    db_availability = models.ProfessorAvailability(
        professor_id=professor_id,
        time_slot_id=time_slot_id,
        disponible=True,
        preferencia=preferencia
    )
    db.add(db_availability)
    db.commit()
    db.refresh(db_availability)
    return db_availability

def update_professor_availability(db: Session, professor_id: int, time_slot_id: int, disponible: bool, preferencia: str = 'normal') -> Optional[models.ProfessorAvailability]:
    db_availability = db.query(models.ProfessorAvailability).filter(
        and_(
            models.ProfessorAvailability.professor_id == professor_id,
            models.ProfessorAvailability.time_slot_id == time_slot_id
        )
    ).first()
    
    if db_availability:
        db_availability.disponible = disponible
        db_availability.preferencia = preferencia
        db.commit()
        db.refresh(db_availability)
    else:
        # Crear nueva disponibilidad si no existe
        db_availability = create_professor_availability(db, professor_id, time_slot_id, preferencia)
    
    return db_availability

# Algorithm Execution CRUD operations
def create_algorithm_execution(db: Session, algoritmo: str, semestre: str, parametros: dict = None) -> models.AlgorithmExecution:
    db_execution = models.AlgorithmExecution(
        algoritmo=algoritmo,
        semestre=semestre,
        parametros=json.dumps(parametros) if parametros else None,
        estado='running'
    )
    db.add(db_execution)
    db.commit()
    db.refresh(db_execution)
    return db_execution

def update_algorithm_execution(db: Session, execution_id: int, update_data: dict) -> Optional[models.AlgorithmExecution]:
    db_execution = db.query(models.AlgorithmExecution).filter(models.AlgorithmExecution.id == execution_id).first()
    
    if db_execution:
        for key, value in update_data.items():
            if hasattr(db_execution, key):
                setattr(db_execution, key, value)
        db.commit()
        db.refresh(db_execution)
    
    return db_execution

def get_algorithm_executions(db: Session, algoritmo: Optional[str] = None, semestre: Optional[str] = None, limit: int = 10) -> List[models.AlgorithmExecution]:
    query = db.query(models.AlgorithmExecution)
    
    if algoritmo:
        query = query.filter(models.AlgorithmExecution.algoritmo == algoritmo)
    if semestre:
        query = query.filter(models.AlgorithmExecution.semestre == semestre)
    
    return query.order_by(models.AlgorithmExecution.iniciado_en.desc()).limit(limit).all()

# Utility functions for bulk operations
def load_courses_from_projections(db: Session, projections_data: List[dict]) -> List[models.Course]:
    """Carga cursos en lote desde datos de proyecciones"""
    courses = []
    
    for proj_data in projections_data:
        # Verificar si el curso ya existe
        existing_course = get_course_by_codigo(db, proj_data['codigo_completo'])
        
        if existing_course:
            # Actualizar curso existente
            update_data = {
                'alumnos_teoria': proj_data['alumnos_teoria'],
                'alumnos_practica': proj_data['alumnos_practica'],
                'alumnos_laboratorio': proj_data['alumnos_laboratorio'],
                'grupos_teoria': proj_data['grupos_teoria'],
                'grupos_practica': proj_data['grupos_practica'],
                'grupos_laboratorio': proj_data['grupos_laboratorio'],
                'requiere_laboratorio': proj_data['requiere_laboratorio'],
                'requiere_practica': proj_data['requiere_practica'],
                'modalidad': proj_data['modalidad']
            }
            updated_course = update_course(db, existing_course.id, update_data)
            courses.append(updated_course)
        else:
            # Crear nuevo curso
            new_course = create_course(db, proj_data)
            courses.append(new_course)
            
            # Crear secciones automáticamente
            create_course_sections_from_projections(db, new_course)
    
    return courses

def load_classrooms_from_data(db: Session, classrooms_data: List[dict]) -> List[models.Classroom]:
    """Carga aulas en lote desde datos"""
    classrooms = []
    
    for classroom_data in classrooms_data:
        # Verificar si el aula ya existe
        existing_classroom = get_classroom_by_codigo(db, classroom_data['codigo'])
        
        if not existing_classroom:
            new_classroom = create_classroom(db, classroom_data)
            classrooms.append(new_classroom)
        else:
            classrooms.append(existing_classroom)
    
    return classrooms

def validate_schedule_assignment(db: Session, assignment_data: dict) -> Dict[str, Any]:
    """Valida una asignación de horario antes de crearla"""
    errors = []
    warnings = []
    
    # Verificar conflictos de profesor
    prof_conflicts = get_conflicting_assignments(
        db, 
        assignment_data['time_slot_id'], 
        professor_id=assignment_data['professor_id']
    )
    if prof_conflicts:
        errors.append(f"Profesor ya tiene asignación en esta franja horaria")
    
    # Verificar conflictos de aula
    classroom_conflicts = get_conflicting_assignments(
        db,
        assignment_data['time_slot_id'],
        classroom_id=assignment_data['classroom_id']
    )
    if classroom_conflicts:
        errors.append(f"Aula ya está ocupada en esta franja horaria")
    
    # Verificar capacidad del aula
    classroom = get_classroom(db, assignment_data['classroom_id'])
    course_section = db.query(models.CourseSection).filter(
        models.CourseSection.id == assignment_data['course_section_id']
    ).first()
    
    if classroom and course_section:
        if course_section.alumnos_proyectados > classroom.capacidad:
            errors.append(f"Capacidad del aula ({classroom.capacidad}) insuficiente para {course_section.alumnos_proyectados} estudiantes")
    
    # Verificar disponibilidad del profesor
    prof_availability = db.query(models.ProfessorAvailability).filter(
        and_(
            models.ProfessorAvailability.professor_id == assignment_data['professor_id'],
            models.ProfessorAvailability.time_slot_id == assignment_data['time_slot_id'],
            models.ProfessorAvailability.disponible == True
        )
    ).first()
    
    if not prof_availability:
        warnings.append("Profesor no tiene disponibilidad registrada para esta franja horaria")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings
    }