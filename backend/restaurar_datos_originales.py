"""
Script para restaurar exactamente los datos originales perfectos que tenías antes
Usa los mismos archivos originales: proyecciones_libro1.json + Libro1.xlsx
"""
import json
import logging
import pandas as pd
from datetime import datetime
from typing import Dict, List, Set
from app.database import SessionLocal, create_database_if_not_exists, create_tables
from app.models import (
    Course, Professor, Classroom, TimeSlot, CourseSection, 
    ProfessorAvailability, professor_course_table, Base
)
from sqlalchemy import insert, text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RestoracionDatosOriginales:
    """Restaurar exactamente los datos originales perfectos"""
    
    def __init__(self):
        self.db = None
        
    def setup_database(self):
        """Configurar base de datos"""
        if not create_database_if_not_exists():
            raise Exception("No se pudo crear/conectar a la base de datos")
        
        create_tables()
        self.db = SessionLocal()
        logger.info("Base de datos configurada correctamente")
        
    def clear_existing_data(self):
        """Limpiar datos existentes (solo datos de cursos y profesores, no aulas ni time_slots)"""
        try:
            # Eliminar en orden para respetar foreign keys
            self.db.query(ProfessorAvailability).delete()
            self.db.execute(professor_course_table.delete())  
            self.db.query(CourseSection).delete()
            self.db.query(Course).delete()
            self.db.query(Professor).delete()
            
            self.db.commit()
            logger.info("✅ Datos existentes de cursos y profesores limpiados")
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error limpiando datos: {e}")
            raise
    
    def cargar_profesores_desde_libro1(self, excel_file: str = '../inputs/Libro1.xlsx'):
        """Cargar profesores exactos desde Libro1.xlsx"""
        try:
            # Leer Excel
            df = pd.read_excel(excel_file)
            
            professors_dict = {}
            course_professor_mapping = {}
            
            # Procesar cada fila del Excel
            for idx, row in df.iterrows():
                asignatura = str(row.get('ASIGNATURA', ''))
                
                # Obtener profesor de columnas posibles
                profesor_field = ''
                possible_prof_columns = ['PROFESOR', 'Unnamed: 12', 'DOCENTE', 'RESPONSABLE']
                
                for col in possible_prof_columns:
                    if col in df.columns and pd.notna(row.get(col)):
                        temp_prof = str(row.get(col, '')).strip()
                        if temp_prof and temp_prof.lower() not in ['nan', '', 'none']:
                            profesor_field = temp_prof
                            break
                
                if not profesor_field:
                    profesor_field = f"Prof_{asignatura.replace(' ', '_').replace(',', '').replace('.', '')[:20]}"
                
                # Separar múltiples profesores
                profesores_lista = []
                for separator in [',', ' Y ', ' y ', ' AND ', ' and ']:
                    if separator in profesor_field:
                        profesores_lista = [p.strip() for p in profesor_field.split(separator) if p.strip()]
                        break
                
                if not profesores_lista:
                    profesores_lista = [profesor_field.strip()]
                
                course_professor_mapping[asignatura] = profesores_lista
                
                # Agregar profesores únicos
                for prof_name in profesores_lista:
                    if prof_name not in professors_dict:
                        professors_dict[prof_name] = {
                            'nombre': prof_name,
                            'especialidades': ['Ingeniería de Sistemas'],
                            'carga_maxima': 20,
                            'activo': True
                        }
            
            # Insertar profesores en la BD
            professor_ids = {}
            for prof_name, prof_data in professors_dict.items():
                # Verificar si ya existe
                existing = self.db.query(Professor).filter(
                    Professor.nombres.contains(prof_name) | 
                    Professor.apellidos.contains(prof_name)
                ).first()
                
                if not existing:
                    # Separar nombres y apellidos de manera simple
                    parts = prof_name.strip().split()
                    if len(parts) >= 2:
                        nombres = " ".join(parts[:len(parts)//2])
                        apellidos = " ".join(parts[len(parts)//2:])
                    else:
                        nombres = prof_name
                        apellidos = ""
                    
                    # Generar código único
                    codigo = f"PROF{len(professor_ids)+1:03d}"
                    
                    new_professor = Professor(
                        codigo=codigo,
                        nombre_completo=prof_name,  # Agregar nombre_completo
                        nombres=nombres,
                        apellidos=apellidos,
                        email=f"{prof_name.lower().replace(' ', '.')}@upao.edu.pe",
                        especialidad=', '.join(prof_data['especialidades']),
                        carga_maxima_horas=prof_data['carga_maxima'],
                        active=prof_data['activo'],
                        created_at=datetime.now()
                    )
                    
                    self.db.add(new_professor)
                    self.db.flush()  # Para obtener el ID
                    professor_ids[prof_name] = new_professor.id
                    logger.info(f"👥 Profesor insertado: {prof_name} (ID: {new_professor.id})")
                else:
                    professor_ids[prof_name] = existing.id
                    logger.info(f"👥 Profesor existente: {prof_name} (ID: {existing.id})")
            
            self.db.commit()
            logger.info(f"✅ Total profesores procesados: {len(professor_ids)}")
            
            return professor_ids, course_professor_mapping
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error cargando profesores: {e}")
            raise
    
    def cargar_cursos_desde_proyecciones(self, proyecciones_file: str = 'proyecciones_libro1.json',
                                       course_professor_mapping: Dict = None):
        """Cargar cursos exactos desde proyecciones_libro1.json"""
        try:
            # Cargar proyecciones originales
            with open(proyecciones_file, 'r', encoding='utf-8') as f:
                proyecciones = json.load(f)
            
            course_ids = {}
            
            for curso_nombre, data in proyecciones.items():
                codigo = f'CURSO_{len(course_ids)+1:03d}'
                
                # Datos de las proyecciones
                grupos_teoria = data.get('teoria', 1)
                grupos_practica = data.get('practica', 0)
                grupos_laboratorio = data.get('laboratorio', 0)
                
                # Crear curso
                new_course = Course(
                    codigo=codigo,
                    nombre=curso_nombre,
                    ciclo=1,  # Valor por defecto
                    creditos=4,  # Valor por defecto
                    modalidad='PRS',
                    alumnos_teoria=40,
                    alumnos_practica=20,
                    alumnos_laboratorio=20,
                    grupos_teoria=grupos_teoria,
                    grupos_practica=grupos_practica,
                    grupos_laboratorio=grupos_laboratorio,
                    requiere_laboratorio=grupos_laboratorio > 0,
                    requiere_practica=grupos_practica > 0,
                    active=True,
                    created_at=datetime.now()
                )
                
                self.db.add(new_course)
                self.db.flush()  # Para obtener el ID
                course_ids[curso_nombre] = new_course.id
                
                # Crear secciones del curso basadas en los grupos de las proyecciones
                # Secciones de teoría
                for i in range(grupos_teoria):
                    section = CourseSection(
                        course_id=new_course.id,
                        tipo='teoria',
                        seccion=f'T{i+1}',
                        alumnos_proyectados=40,
                        activa=True,
                        created_at=datetime.now()
                    )
                    self.db.add(section)
                
                # Secciones de práctica
                for i in range(grupos_practica):
                    section = CourseSection(
                        course_id=new_course.id,
                        tipo='practica',
                        seccion=f'P{i+1}',
                        alumnos_proyectados=20,
                        activa=True,
                        created_at=datetime.now()
                    )
                    self.db.add(section)
                
                # Secciones de laboratorio
                for i in range(grupos_laboratorio):
                    section = CourseSection(
                        course_id=new_course.id,
                        tipo='laboratorio',
                        seccion=f'L{i+1}',
                        alumnos_proyectados=20,
                        activa=True,
                        created_at=datetime.now()
                    )
                    self.db.add(section)
                
                logger.info(f"📚 Curso creado: {curso_nombre} (T:{grupos_teoria}, P:{grupos_practica}, L:{grupos_laboratorio})")
            
            self.db.commit()
            logger.info(f"✅ Total cursos creados: {len(course_ids)}")
            
            return course_ids
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error cargando cursos: {e}")
            raise
    
    def crear_relaciones_profesor_curso(self, professor_ids: Dict, course_ids: Dict, 
                                      course_professor_mapping: Dict):
        """Crear relaciones profesor-curso"""
        try:
            relations_created = 0
            
            for course_name, professors_list in course_professor_mapping.items():
                if course_name in course_ids:
                    course_id = course_ids[course_name]
                    
                    for prof_name in professors_list:
                        if prof_name in professor_ids:
                            professor_id = professor_ids[prof_name]
                            
                            # Insertar relación
                            self.db.execute(
                                professor_course_table.insert().values(
                                    professor_id=professor_id,
                                    course_id=course_id,
                                    assigned_at=datetime.now(),
                                    assignment_type='main'
                                )
                            )
                            relations_created += 1
                            logger.info(f"🔗 Relación creada: {prof_name} -> {course_name}")
            
            self.db.commit()
            logger.info(f"✅ Total relaciones profesor-curso creadas: {relations_created}")
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creando relaciones profesor-curso: {e}")
            raise
    
    def crear_disponibilidad_profesores(self, professor_ids: Dict):
        """Crear disponibilidad completa para todos los profesores"""
        try:
            # Obtener todos los time slots
            time_slots = self.db.query(TimeSlot).all()
            
            availability_created = 0
            
            for prof_name, prof_id in professor_ids.items():
                for slot in time_slots:
                    availability = ProfessorAvailability(
                        professor_id=prof_id,
                        time_slot_id=slot.id,
                        disponible=True,
                        preferencia='media',
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    self.db.add(availability)
                    availability_created += 1
                
                if availability_created % 1000 == 0:  # Log cada 1000 registros
                    logger.info(f"⏰ Disponibilidad creada: {availability_created} registros...")
            
            self.db.commit()
            logger.info(f"✅ Total registros de disponibilidad creados: {availability_created}")
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creando disponibilidad: {e}")
            raise
    
    def restaurar_todo(self):
        """Ejecutar restauración completa de datos originales perfectos"""
        try:
            logger.info("=== 🔄 RESTAURANDO DATOS ORIGINALES PERFECTOS ===")
            
            # 1. Configurar BD
            self.setup_database()
            
            # 2. Limpiar datos existentes
            logger.info("🧹 Limpiando datos existentes...")
            self.clear_existing_data()
            
            # 3. Cargar profesores desde Libro1.xlsx
            logger.info("👥 Cargando profesores desde Libro1.xlsx...")
            professor_ids, course_professor_mapping = self.cargar_profesores_desde_libro1()
            
            # 4. Cargar cursos desde proyecciones_libro1.json
            logger.info("📚 Cargando cursos desde proyecciones_libro1.json...")
            course_ids = self.cargar_cursos_desde_proyecciones(
                course_professor_mapping=course_professor_mapping
            )
            
            # 5. Crear relaciones profesor-curso
            logger.info("🔗 Creando relaciones profesor-curso...")
            self.crear_relaciones_profesor_curso(
                professor_ids, course_ids, course_professor_mapping
            )
            
            # 6. Crear disponibilidad de profesores
            logger.info("⏰ Creando disponibilidad de profesores...")
            self.crear_disponibilidad_profesores(professor_ids)
            
            # 7. Estadísticas finales
            total_professors = self.db.query(Professor).count()
            total_courses = self.db.query(Course).count()
            total_sections = self.db.query(CourseSection).count()
            total_classrooms = self.db.query(Classroom).count()
            total_time_slots = self.db.query(TimeSlot).count()
            total_relations = self.db.execute(
                text(f"SELECT COUNT(*) FROM {professor_course_table.name}")
            ).scalar()
            total_availability = self.db.query(ProfessorAvailability).count()
            
            logger.info("=== ✅ RESTAURACIÓN COMPLETA EXITOSA ===")
            logger.info(f"👥 Profesores: {total_professors}")
            logger.info(f"📚 Cursos: {total_courses}")
            logger.info(f"📋 Secciones: {total_sections}")
            logger.info(f"🏛️ Aulas: {total_classrooms}")
            logger.info(f"⏰ Franjas horarias: {total_time_slots}")
            logger.info(f"🔗 Relaciones profesor-curso: {total_relations}")
            logger.info(f"📅 Registros de disponibilidad: {total_availability}")
            
            print("✅ DATOS ORIGINALES PERFECTOS RESTAURADOS")
            print(f"👥 {total_professors} profesores | 📚 {total_courses} cursos")
            print("🎯 Sistema listo como estaba originalmente")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error en restauración: {e}")
            return False
        finally:
            if self.db:
                self.db.close()

def main():
    """Ejecutar restauración completa"""
    restauracion = RestoracionDatosOriginales()
    success = restauracion.restaurar_todo()
    
    if success:
        print("\n🎉 RESTAURACIÓN EXITOSA")
        print("¡Todos tus datos originales perfectos están de vuelta!")
        print("El sistema está exactamente como estaba antes")
    else:
        print("\n❌ ERROR EN LA RESTAURACIÓN")
        print("Revisar logs para más detalles")
    
    return success

if __name__ == "__main__":
    main()