"""
Pydantic schemas for UPAO Timetabling System
Data validation and serialization models
"""

from pydantic import BaseModel, validator, Field
from typing import List, Optional, Dict, Any, Set
from datetime import datetime
from enum import Enum

# Enums
class ModalidadEnum(str, Enum):
    PRESENCIAL = "PRS"
    NO_PRESENCIAL = "NPR"

class TipoSeccionEnum(str, Enum):
    TEORIA = "teoria"
    PRACTICA = "practica"
    LABORATORIO = "laboratorio"

class TipoAulaEnum(str, Enum):
    TEORICA = "teorica"
    LABORATORIO = "laboratorio"
    PRACTICA = "practica"

class EdificioEnum(str, Enum):
    F = "F"
    G = "G"

class PeriodoEnum(str, Enum):
    MANANA = "mañana"
    TARDE = "tarde"
    NOCHE = "noche"

class EstadoAsignacionEnum(str, Enum):
    PROGRAMADO = "programado"
    CONFIRMADO = "confirmado"
    CANCELADO = "cancelado"

class PreferenciaEnum(str, Enum):
    ALTA = "alta"
    NORMAL = "normal"
    BAJA = "baja"

# Base schemas
class BaseSchema(BaseModel):
    class Config:
        from_attributes = True

# Course schemas
class CourseBase(BaseSchema):
    codigo: str = Field(..., description="Código único del curso")
    nombre: str = Field(..., description="Nombre de la asignatura")
    ciclo: int = Field(..., ge=1, le=10, description="Número de ciclo (1-10)")
    modalidad: ModalidadEnum = Field(default=ModalidadEnum.PRESENCIAL)
    creditos: int = Field(default=3, ge=1, le=8)
    
    alumnos_teoria: int = Field(default=0, ge=0)
    alumnos_practica: int = Field(default=0, ge=0) 
    alumnos_laboratorio: int = Field(default=0, ge=0)
    
    grupos_teoria: int = Field(default=0, ge=0)
    grupos_practica: int = Field(default=0, ge=0)
    grupos_laboratorio: int = Field(default=0, ge=0)
    
    requiere_laboratorio: bool = Field(default=False)
    requiere_practica: bool = Field(default=False)
    
    restricciones_especiales: Optional[str] = None

class CourseCreate(CourseBase):
    pass

class CourseUpdate(BaseSchema):
    nombre: Optional[str] = None
    ciclo: Optional[int] = Field(None, ge=1, le=10)
    modalidad: Optional[ModalidadEnum] = None
    creditos: Optional[int] = Field(None, ge=1, le=8)
    alumnos_teoria: Optional[int] = Field(None, ge=0)
    alumnos_practica: Optional[int] = Field(None, ge=0)
    alumnos_laboratorio: Optional[int] = Field(None, ge=0)
    grupos_teoria: Optional[int] = Field(None, ge=0)
    grupos_practica: Optional[int] = Field(None, ge=0)
    grupos_laboratorio: Optional[int] = Field(None, ge=0)
    requiere_laboratorio: Optional[bool] = None
    requiere_practica: Optional[bool] = None
    restricciones_especiales: Optional[str] = None

class Course(CourseBase):
    id: int
    active: bool
    created_at: datetime
    updated_at: datetime

# Professor schemas
class ProfessorBase(BaseSchema):
    codigo: str = Field(..., description="Código único del profesor")
    nombre_completo: str = Field(..., min_length=2)

class ProfessorCreate(ProfessorBase):
    pass

class ProfessorUpdate(BaseSchema):
    codigo: Optional[str] = Field(None, description="Código único del profesor")
    nombre_completo: Optional[str] = Field(None, min_length=2)

class Professor(ProfessorBase):
    id: int

# Classroom schemas
class ClassroomBase(BaseSchema):
    codigo: str = Field(..., description="Código único del aula")
    edificio: EdificioEnum
    piso: str
    capacidad: int = Field(..., ge=1, le=100)
    tipo: TipoAulaEnum
    
    tiene_proyector: bool = True
    tiene_aire_acondicionado: bool = True
    tiene_computadoras: bool = False
    numero_computadoras: int = Field(default=0, ge=0)
    observaciones: Optional[str] = None

class ClassroomCreate(ClassroomBase):
    pass

class ClassroomUpdate(BaseSchema):
    edificio: Optional[EdificioEnum] = None
    piso: Optional[str] = None
    capacidad: Optional[int] = Field(None, ge=1, le=100)
    tipo: Optional[TipoAulaEnum] = None
    tiene_proyector: Optional[bool] = None
    tiene_aire_acondicionado: Optional[bool] = None
    tiene_computadoras: Optional[bool] = None
    numero_computadoras: Optional[int] = Field(None, ge=0)
    observaciones: Optional[str] = None
    disponible: Optional[bool] = None

class Classroom(ClassroomBase):
    id: int
    disponible: bool
    created_at: datetime
    updated_at: datetime

# TimeSlot schemas
class TimeSlotBase(BaseSchema):
    dia_semana: int = Field(..., ge=1, le=6, description="1=Lunes, 6=Sábado")
    hora_inicio: str = Field(..., regex=r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$")
    hora_fin: str = Field(..., regex=r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$")
    periodo: PeriodoEnum
    orden: int = Field(..., ge=1, le=16, description="Orden en el día (1-16)")

class TimeSlotCreate(TimeSlotBase):
    pass

class TimeSlot(TimeSlotBase):
    id: int
    activo: bool
    
    @property
    def dia_nombre(self) -> str:
        dias = {1: 'Lunes', 2: 'Martes', 3: 'Miércoles', 4: 'Jueves', 5: 'Viernes', 6: 'Sábado'}
        return dias.get(self.dia_semana, 'Desconocido')
    
    @property
    def franja_completa(self) -> str:
        return f"{self.dia_nombre} {self.hora_inicio}-{self.hora_fin}"

# CourseSection schemas
class CourseSectionBase(BaseSchema):
    course_id: int
    tipo: TipoSeccionEnum
    seccion: str = Field(..., description="A, B, C, etc.")
    alumnos_proyectados: int = Field(..., ge=0)
    alumnos_reales: int = Field(default=0, ge=0)

class CourseSectionCreate(CourseSectionBase):
    pass

class CourseSectionUpdate(BaseSchema):
    tipo: Optional[TipoSeccionEnum] = None
    seccion: Optional[str] = None
    alumnos_proyectados: Optional[int] = Field(None, ge=0)
    alumnos_reales: Optional[int] = Field(None, ge=0)
    activa: Optional[bool] = None

class CourseSection(CourseSectionBase):
    id: int
    activa: bool
    created_at: datetime
    
    @property
    def codigo_completo(self) -> str:
        # Note: This would need the course info to be fully implemented
        return f"COURSE-{self.tipo.upper()}-{self.seccion}"

# ProfessorAvailability schemas
class ProfessorAvailabilityBase(BaseSchema):
    professor_id: int
    time_slot_id: int
    disponible: bool = True
    preferencia: PreferenciaEnum = PreferenciaEnum.NORMAL
    observaciones: Optional[str] = None

class ProfessorAvailabilityCreate(ProfessorAvailabilityBase):
    pass

class ProfessorAvailabilityUpdate(BaseSchema):
    disponible: Optional[bool] = None
    preferencia: Optional[PreferenciaEnum] = None
    observaciones: Optional[str] = None

class ProfessorAvailability(ProfessorAvailabilityBase):
    id: int
    created_at: datetime
    updated_at: datetime

# ScheduleAssignment schemas
class ScheduleAssignmentBase(BaseSchema):
    course_id: int
    course_section_id: int
    professor_id: int
    classroom_id: int
    time_slot_id: int
    semestre: str = Field(..., description="Ej: 2025-I, 2025-II")
    estado: EstadoAsignacionEnum = EstadoAsignacionEnum.PROGRAMADO
    generado_por_algoritmo: bool = False
    confianza_asignacion: Optional[float] = Field(None, ge=0.0, le=1.0)

class ScheduleAssignmentCreate(ScheduleAssignmentBase):
    pass

class ScheduleAssignmentUpdate(BaseSchema):
    professor_id: Optional[int] = None
    classroom_id: Optional[int] = None
    time_slot_id: Optional[int] = None
    estado: Optional[EstadoAsignacionEnum] = None
    confianza_asignacion: Optional[float] = Field(None, ge=0.0, le=1.0)

class ScheduleAssignment(ScheduleAssignmentBase):
    id: int
    created_at: datetime
    updated_at: datetime

# Complex schemas for API responses
class CourseWithSections(Course):
    course_sections: List[CourseSection] = []

class ProfessorWithAvailability(Professor):
    availability_slots: List[ProfessorAvailability] = []

class ScheduleAssignmentDetailed(ScheduleAssignment):
    course: Course
    course_section: CourseSection
    professor: Professor
    classroom: Classroom
    time_slot: TimeSlot

# Algorithm schemas
class AlgorithmParametersACO(BaseSchema):
    alpha: float = Field(default=1.0, ge=0.1, le=5.0, description="Importancia de feromonas")
    beta: float = Field(default=2.0, ge=0.1, le=5.0, description="Importancia de heurística")
    rho: float = Field(default=0.1, ge=0.01, le=0.5, description="Tasa de evaporación")
    q: float = Field(default=100.0, ge=1.0, le=1000.0, description="Constante de actualización")
    max_iterations: int = Field(default=100, ge=10, le=500)
    num_ants: int = Field(default=20, ge=5, le=100)

class AlgorithmParametersGraphSAGE(BaseSchema):
    hidden_dim: int = Field(default=64, ge=16, le=256)
    num_layers: int = Field(default=3, ge=2, le=6)
    learning_rate: float = Field(default=0.01, ge=0.001, le=0.1)
    epochs: int = Field(default=100, ge=50, le=500)
    batch_size: int = Field(default=32, ge=8, le=128)

class AlgorithmExecutionCreate(BaseSchema):
    algoritmo: str = Field(..., description="ACO, GraphSAGE, Hybrid")
    semestre: str
    parametros: Optional[Dict[str, Any]] = None

class AlgorithmExecution(BaseSchema):
    id: int
    algoritmo: str
    semestre: str
    parametros: Optional[str] = None  # JSON string
    estado: str
    tiempo_ejecucion: Optional[float] = None
    funcion_objetivo: Optional[float] = None
    restricciones_violadas: int
    conflictos_profesor: int
    conflictos_aula: int
    utilizacion_aulas: Optional[float] = None
    distribucion_carga: Optional[float] = None
    log_ejecucion: Optional[str] = None
    mensaje_error: Optional[str] = None
    iniciado_en: datetime
    terminado_en: Optional[datetime] = None

# Bulk operation schemas
class CourseProjectionImport(BaseSchema):
    codigo_completo: str
    nombre_asignatura: str
    ciclo_numerico: int
    modalidad: ModalidadEnum
    alumnos_teoria: int
    alumnos_practica: int
    alumnos_laboratorio: int
    grupos_teoria: int
    grupos_practica: int
    grupos_laboratorio: int
    requiere_laboratorio: bool
    requiere_practica: bool
    creditos: int = 3
    observaciones: Optional[str] = None

class BulkImportResponse(BaseSchema):
    success: bool
    message: str
    imported_count: int
    updated_count: int
    errors: List[str] = []
    warnings: List[str] = []

# Validation schemas
class AssignmentValidation(BaseSchema):
    valid: bool
    errors: List[str] = []
    warnings: List[str] = []

class ConflictCheck(BaseSchema):
    has_conflicts: bool
    professor_conflicts: List[str] = []
    classroom_conflicts: List[str] = []
    capacity_issues: List[str] = []

# Statistics schemas
class CourseStatistics(BaseSchema):
    total_courses: int
    by_cycle: Dict[int, int]
    by_modality: Dict[str, int]
    requires_laboratory: int
    requires_practice: int
    total_theory_groups: int
    total_practice_groups: int
    total_lab_groups: int
    total_students: int

class ProfessorStatistics(BaseSchema):
    total_professors: int
    by_category: Dict[str, int]
    average_load: float
    total_assigned_hours: int
    availability_coverage: float

class ClassroomStatistics(BaseSchema):
    total_classrooms: int
    by_building: Dict[str, int]
    by_type: Dict[str, int]
    average_capacity: float
    utilization_rate: float

class SystemStatistics(BaseSchema):
    courses: CourseStatistics
    professors: ProfessorStatistics
    classrooms: ClassroomStatistics
    last_updated: datetime

# Excel import schemas
class ExcelImportRequest(BaseSchema):
    process_projections: bool = True
    create_sections: bool = True
    overwrite_existing: bool = False

class ExcelImportResponse(BulkImportResponse):
    file_info: Dict[str, Any]
    processing_time: float
    statistics: Optional[CourseStatistics] = None