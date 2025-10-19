"""
Database Models for UPAO Timetabling System
SQLAlchemy models for courses, professors, classrooms, and schedules
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import List, Optional

Base = declarative_base()

# Tabla de asociación para relación many-to-many entre profesores y cursos
professor_course_table = Table(
    'professor_courses', Base.metadata,
    Column('professor_id', Integer, ForeignKey('professors.id'), primary_key=True),
    Column('course_id', Integer, ForeignKey('courses.id'), primary_key=True),
    Column('assigned_at', DateTime, default=func.now()),
    Column('assignment_type', String(20), default='main')  # main, assistant, substitute
)

class Course(Base):
    """Modelo para cursos/asignaturas"""
    __tablename__ = 'courses'
    
    id = Column(Integer, primary_key=True)
    codigo = Column(String(20), unique=True, nullable=False, index=True)
    nombre = Column(String(200), nullable=False)
    ciclo = Column(Integer, nullable=False, index=True)
    modalidad = Column(String(20), default='presencial')  # presencial/no_presencial
    
    # Proyecciones de alumnos
    alumnos_teoria = Column(Integer, default=0)
    alumnos_practica = Column(Integer, default=0)
    alumnos_laboratorio = Column(Integer, default=0)
    
    # Grupos requeridos
    grupos_teoria = Column(Integer, default=0)
    grupos_practica = Column(Integer, default=0)
    grupos_laboratorio = Column(Integer, default=0)
    
    # Características del curso
    requiere_laboratorio = Column(Boolean, default=False)
    requiere_practica = Column(Boolean, default=False)
    creditos = Column(Integer, default=3)
    
    # Metadatos
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    active = Column(Boolean, default=True)
    
    # Relaciones
    professors = relationship("Professor", secondary=professor_course_table, back_populates="courses")
    course_sections = relationship("CourseSection", back_populates="course", cascade="all, delete-orphan")
    schedule_assignments = relationship("ScheduleAssignment", back_populates="course")
    
    def __repr__(self):
        return f"<Course(codigo='{self.codigo}', nombre='{self.nombre}', ciclo={self.ciclo})>"

class Professor(Base):
    """Modelo simplificado para profesores"""
    __tablename__ = 'professors'

    id = Column(Integer, primary_key=True)
    codigo = Column(String(20), unique=True, nullable=False, index=True)
    nombre_completo = Column(String(200), nullable=False)

    # Relaciones
    courses = relationship("Course", secondary=professor_course_table, back_populates="professors")
    availability_slots = relationship("ProfessorAvailability", back_populates="professor", cascade="all, delete-orphan")
    schedule_assignments = relationship("ScheduleAssignment", back_populates="professor")

    def __repr__(self):
        return f"<Professor(codigo='{self.codigo}', nombre='{self.nombre_completo}')>"

class Classroom(Base):
    """Modelo para aulas"""
    __tablename__ = 'classrooms'
    
    id = Column(Integer, primary_key=True)
    codigo = Column(String(20), unique=True, nullable=False, index=True)
    edificio = Column(String(10), nullable=False, index=True)  # F, G
    piso = Column(String(10), nullable=False)
    capacidad = Column(Integer, nullable=False)
    tipo = Column(String(20), nullable=False, index=True)  # teorica, laboratorio, practica
    tiene_computadoras = Column(Boolean, default=False)
    numero_computadoras = Column(Integer, default=0)
    active = Column(Boolean, default=True)
    
    # Metadatos
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relaciones
    schedule_assignments = relationship("ScheduleAssignment", back_populates="classroom")
    
    @property
    def es_laboratorio_f(self):
        """Laboratorio F para grupos ≤20 alumnos"""
        return self.edificio == 'F' and self.tipo == 'laboratorio'
    
    @property
    def es_laboratorio_g(self):
        """Laboratorio G para grupos >20 alumnos"""
        return self.edificio == 'G' and self.tipo == 'laboratorio'
    
    def __repr__(self):
        return f"<Classroom(codigo='{self.codigo}', tipo='{self.tipo}', capacidad={self.capacidad})>"

class TimeSlot(Base):
    """Modelo para franjas horarias"""
    __tablename__ = 'time_slots'
    
    id = Column(Integer, primary_key=True)
    dia_semana = Column(Integer, nullable=False, index=True)  # 1=Lunes, 6=Sábado
    hora_inicio = Column(String(5), nullable=False)  # "07:00"
    hora_fin = Column(String(5), nullable=False)     # "07:50"
    periodo = Column(String(10), nullable=False, index=True)  # mañana, tarde, noche
    
    # Orden dentro del día (1-16)
    orden = Column(Integer, nullable=False)
    
    # Metadatos
    activo = Column(Boolean, default=True)
    
    # Relaciones
    schedule_assignments = relationship("ScheduleAssignment", back_populates="time_slot")
    professor_availability = relationship("ProfessorAvailability", back_populates="time_slot")
    
    @property
    def dia_nombre(self):
        dias = {1: 'Lunes', 2: 'Martes', 3: 'Miércoles', 
                4: 'Jueves', 5: 'Viernes', 6: 'Sábado'}
        return dias.get(self.dia_semana, 'Desconocido')
    
    @property
    def franja_completa(self):
        return f"{self.dia_nombre} {self.hora_inicio}-{self.hora_fin}"
    
    def __repr__(self):
        return f"<TimeSlot(dia={self.dia_nombre}, hora='{self.hora_inicio}-{self.hora_fin}')>"

class CourseSection(Base):
    """Modelo para secciones de curso (teoría, práctica, laboratorio)"""
    __tablename__ = 'course_sections'
    
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey('courses.id'), nullable=False)
    tipo = Column(String(20), nullable=False, index=True)  # teoria, practica, laboratorio
    seccion = Column(String(10), nullable=False)  # A, B, C, etc.
    league = Column(Integer, nullable=True)  # Liga a la que pertenece (1, 2, ...)
    nrc = Column(String(20), nullable=True, unique=True)  # Identificador único NRC
    
    # Estudiantes proyectados
    alumnos_proyectados = Column(Integer, nullable=False)
    alumnos_reales = Column(Integer, default=0)
    
    # Estado
    activa = Column(Boolean, default=True)
    
    # Metadatos
    created_at = Column(DateTime, default=func.now())
    
    # Relaciones
    course = relationship("Course", back_populates="course_sections")
    schedule_assignments = relationship("ScheduleAssignment", back_populates="course_section")
    
    @property
    def codigo_completo(self):
        return f"{self.course.codigo}-{self.tipo.upper()}-{self.seccion}"
    
    def __repr__(self):
        return f"<CourseSection(codigo='{self.codigo_completo}', alumnos={self.alumnos_proyectados})>"

class ProfessorCourseAssignment(Base):
    """Asignaciones explícitas de profesores a cursos por tipo y liga"""
    __tablename__ = 'professor_course_assignments'

    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey('courses.id'), nullable=False, index=True)
    professor_id = Column(Integer, ForeignKey('professors.id'), nullable=False, index=True)
    session_type = Column(String(10), nullable=True)
    league = Column(Integer, nullable=True)
    priority = Column(Integer, default=1)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    course = relationship("Course", backref="explicit_professor_assignments")
    professor = relationship("Professor", backref="explicit_course_assignments")

class ProfessorRestriction(Base):
    """Modelo para restricciones horarias de profesores"""
    __tablename__ = 'professor_restrictions'
    
    id = Column(Integer, primary_key=True)
    professor_id = Column(Integer, ForeignKey('professors.id'), nullable=False)
    day = Column(String(20), nullable=False)  # Monday, Tuesday, etc.
    start_time = Column(String(10), nullable=False)  # "07:00"
    end_time = Column(String(10), nullable=False)  # "09:40"
    duration_blocks = Column(Integer, default=1)  # Número de bloques de 50 minutos
    reason = Column(Text, nullable=True)  # Motivo de la restricción
    
    # Metadatos
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relación
    professor = relationship("Professor", backref="restrictions")
    
    def __repr__(self):
        return f"<ProfessorRestriction(professor_id={self.professor_id}, day='{self.day}', {self.start_time}-{self.end_time})>"

class ProfessorAvailability(Base):
    """Modelo para disponibilidad horaria de profesores"""
    __tablename__ = 'professor_availability'
    
    id = Column(Integer, primary_key=True)
    professor_id = Column(Integer, ForeignKey('professors.id'), nullable=False)
    time_slot_id = Column(Integer, ForeignKey('time_slots.id'), nullable=False)
    
    # Disponibilidad
    disponible = Column(Boolean, default=True)
    preferencia = Column(String(10), default='normal')  # alta, normal, baja
    
    # Observaciones
    observaciones = Column(Text, nullable=True)
    
    # Metadatos
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relaciones
    professor = relationship("Professor", back_populates="availability_slots")
    time_slot = relationship("TimeSlot", back_populates="professor_availability")
    
    def __repr__(self):
        return f"<ProfessorAvailability(profesor='{self.professor.codigo}', disponible={self.disponible})>"

class ScheduleAssignment(Base):
    """Modelo para asignaciones finales de horarios"""
    __tablename__ = 'schedule_assignments'
    
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey('courses.id'), nullable=False)
    course_section_id = Column(Integer, ForeignKey('course_sections.id'), nullable=False)
    professor_id = Column(Integer, ForeignKey('professors.id'), nullable=False)
    classroom_id = Column(Integer, ForeignKey('classrooms.id'), nullable=False)
    time_slot_id = Column(Integer, ForeignKey('time_slots.id'), nullable=False)
    
    # Información adicional
    semestre = Column(String(20), nullable=False)  # "2025-I", "2025-II"
    estado = Column(String(20), default='programado')  # programado, confirmado, cancelado
    
    # Metadatos del algoritmo
    generado_por_algoritmo = Column(Boolean, default=False)
    confianza_asignacion = Column(Float, nullable=True)  # Para GraphSAGE
    
    # Metadatos
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relaciones
    course = relationship("Course", back_populates="schedule_assignments")
    course_section = relationship("CourseSection", back_populates="schedule_assignments")
    professor = relationship("Professor", back_populates="schedule_assignments")
    classroom = relationship("Classroom", back_populates="schedule_assignments")
    time_slot = relationship("TimeSlot", back_populates="schedule_assignments")
    
    def __repr__(self):
        return f"<ScheduleAssignment(curso='{self.course.codigo}', aula='{self.classroom.codigo}', {self.time_slot.franja_completa})>"

class AlgorithmExecution(Base):
    """Modelo para seguimiento de ejecuciones de algoritmos"""
    __tablename__ = 'algorithm_executions'
    
    id = Column(Integer, primary_key=True)
    algoritmo = Column(String(50), nullable=False)  # ACO, GraphSAGE, Hybrid
    semestre = Column(String(20), nullable=False)
    
    # Parámetros de entrada
    parametros = Column(Text, nullable=True)  # JSON con parámetros
    
    # Resultados
    estado = Column(String(20), default='running')  # running, completed, failed
    tiempo_ejecucion = Column(Float, nullable=True)  # segundos
    funcion_objetivo = Column(Float, nullable=True)
    restricciones_violadas = Column(Integer, default=0)
    
    # Métricas específicas
    conflictos_profesor = Column(Integer, default=0)
    conflictos_aula = Column(Integer, default=0)
    utilizacion_aulas = Column(Float, nullable=True)
    distribucion_carga = Column(Float, nullable=True)
    
    # Detalles
    log_ejecucion = Column(Text, nullable=True)
    mensaje_error = Column(Text, nullable=True)
    
    # Metadatos
    iniciado_en = Column(DateTime, default=func.now())
    terminado_en = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<AlgorithmExecution(algoritmo='{self.algoritmo}', estado='{self.estado}')>"

# Índices adicionales para optimización
from sqlalchemy import Index

# Índices compuestos para consultas frecuentes
Index('idx_course_ciclo_modalidad', Course.ciclo, Course.modalidad)
Index('idx_schedule_semestre_curso', ScheduleAssignment.semestre, ScheduleAssignment.course_id)
Index('idx_availability_profesor_dia', ProfessorAvailability.professor_id, ProfessorAvailability.time_slot_id)
Index('idx_classroom_tipo_edificio', Classroom.tipo, Classroom.edificio)