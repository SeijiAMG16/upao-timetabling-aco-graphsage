"""
Script de backup y restauración de la base de datos UPAO Timetabling
Crea backup completo antes de hacer cambios importantes
"""
import logging
import json
from datetime import datetime
from typing import Dict, List, Any
from sqlalchemy.orm import Session
import os

from app.database import SessionLocal
from app.models import Course, Professor, CourseSection, Classroom, TimeSlot

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseBackup:
    """
    Clase para crear y restaurar backups de la base de datos
    """
    
    def __init__(self):
        self.backup_dir = "backups"
        self.ensure_backup_directory()
    
    def ensure_backup_directory(self):
        """Crear directorio de backups si no existe"""
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
            logger.info(f"📁 Directorio de backups creado: {self.backup_dir}")
    
    def create_full_backup(self) -> str:
        """
        Crea un backup completo de la base de datos
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_upao_timetabling_{timestamp}.json"
        backup_path = os.path.join(self.backup_dir, backup_filename)
        
        logger.info(f"🔄 Iniciando backup completo en: {backup_path}")
        
        session = SessionLocal()
        
        try:
            backup_data = {
                "timestamp": datetime.now().isoformat(),
                "version": "1.0",
                "tables": {}
            }
            
            # Backup de Cursos
            logger.info("📚 Respaldando cursos...")
            courses = session.query(Course).all()
            backup_data["tables"]["courses"] = []
            
            for course in courses:
                course_data = {
                    "id": course.id,
                    "codigo": course.codigo,
                    "nombre": course.nombre,
                    "ciclo": course.ciclo,
                    "modalidad": course.modalidad,
                    "alumnos_teoria": course.alumnos_teoria,
                    "alumnos_practica": course.alumnos_practica,
                    "alumnos_laboratorio": course.alumnos_laboratorio,
                    "grupos_teoria": course.grupos_teoria,
                    "grupos_practica": course.grupos_practica,
                    "grupos_laboratorio": course.grupos_laboratorio,
                    "requiere_laboratorio": course.requiere_laboratorio,
                    "requiere_practica": course.requiere_practica,
                    "creditos": course.creditos,
                    "active": course.active,
                    "created_at": course.created_at.isoformat() if course.created_at else None,
                    "updated_at": course.updated_at.isoformat() if course.updated_at else None
                }
                backup_data["tables"]["courses"].append(course_data)
            
            logger.info(f"✅ {len(courses)} cursos respaldados")
            
            # Backup de Profesores
            logger.info("👥 Respaldando profesores...")
            professors = session.query(Professor).all()
            backup_data["tables"]["professors"] = []
            
            for professor in professors:
                professor_data = {
                    "id": professor.id,
                    "codigo": professor.codigo,
                    "nombre_completo": professor.nombre_completo
                }
                backup_data["tables"]["professors"].append(professor_data)
            
            logger.info(f"✅ {len(professors)} profesores respaldados")
            
            # Backup de Secciones de Cursos
            logger.info("📋 Respaldando secciones de cursos...")
            sections = session.query(CourseSection).all()
            backup_data["tables"]["course_sections"] = []
            
            for section in sections:
                section_data = {
                    "id": section.id,
                    "course_id": section.course_id,
                    "tipo": section.tipo,
                    "seccion": section.seccion,
                    "alumnos_proyectados": section.alumnos_proyectados,
                    "alumnos_reales": section.alumnos_reales,
                    "activa": section.activa,
                    "created_at": section.created_at.isoformat() if section.created_at else None
                }
                backup_data["tables"]["course_sections"].append(section_data)
            
            logger.info(f"✅ {len(sections)} secciones respaldadas")
            
            # Backup de Aulas
            logger.info("🏢 Respaldando aulas...")
            classrooms = session.query(Classroom).all()
            backup_data["tables"]["classrooms"] = []
            
            for classroom in classrooms:
                classroom_data = {
                    "id": classroom.id,
                    "codigo": classroom.codigo,
                    "edificio": classroom.edificio,
                    "piso": classroom.piso,
                    "capacidad": classroom.capacidad,
                    "tipo": classroom.tipo,
                    "tiene_computadoras": classroom.tiene_computadoras,
                    "numero_computadoras": classroom.numero_computadoras,
                    "active": classroom.active,
                    "created_at": classroom.created_at.isoformat() if classroom.created_at else None,
                    "updated_at": classroom.updated_at.isoformat() if classroom.updated_at else None
                }
                backup_data["tables"]["classrooms"].append(classroom_data)
            
            logger.info(f"✅ {len(classrooms)} aulas respaldadas")
            
            # Backup de Time Slots
            logger.info("⏰ Respaldando franjas horarias...")
            time_slots = session.query(TimeSlot).all()
            backup_data["tables"]["time_slots"] = []
            
            for slot in time_slots:
                slot_data = {
                    "id": slot.id,
                    "dia_semana": slot.dia_semana,
                    "hora_inicio": slot.hora_inicio,
                    "hora_fin": slot.hora_fin,
                    "periodo": slot.periodo,
                    "orden": slot.orden,
                    "activo": slot.activo
                }
                backup_data["tables"]["time_slots"].append(slot_data)
            
            logger.info(f"✅ {len(time_slots)} franjas horarias respaldadas")
            
            # Guardar backup
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            # Estadísticas del backup
            total_records = (len(courses) + len(professors) + 
                           len(sections) + len(classrooms) + len(time_slots))
            
            logger.info(f"🎉 Backup completado exitosamente!")
            logger.info(f"📊 Registros respaldados:")
            logger.info(f"   📚 Cursos: {len(courses)}")
            logger.info(f"   👥 Profesores: {len(professors)}")
            logger.info(f"   📋 Secciones: {len(sections)}")
            logger.info(f"   🏢 Aulas: {len(classrooms)}")
            logger.info(f"   ⏰ Franjas: {len(time_slots)}")
            logger.info(f"   📊 Total: {total_records} registros")
            logger.info(f"💾 Archivo: {backup_path}")
            
            return backup_path
            
        except Exception as e:
            logger.error(f"❌ Error creando backup: {str(e)}")
            raise
        finally:
            session.close()
    
    def list_backups(self) -> List[str]:
        """Lista todos los backups disponibles"""
        backups = []
        for file in os.listdir(self.backup_dir):
            if file.startswith("backup_upao_timetabling_") and file.endswith(".json"):
                backups.append(os.path.join(self.backup_dir, file))
        
        backups.sort(reverse=True)  # Más recientes primero
        return backups
    
    def get_backup_info(self, backup_path: str) -> Dict[str, Any]:
        """Obtiene información de un backup"""
        try:
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            info = {
                "path": backup_path,
                "timestamp": backup_data.get("timestamp"),
                "version": backup_data.get("version"),
                "size_mb": round(os.path.getsize(backup_path) / (1024 * 1024), 2)
            }
            
            if "tables" in backup_data:
                info["records"] = {}
                for table, records in backup_data["tables"].items():
                    info["records"][table] = len(records)
                info["total_records"] = sum(info["records"].values())
            
            return info
            
        except Exception as e:
            logger.error(f"❌ Error leyendo backup {backup_path}: {str(e)}")
            return {"path": backup_path, "error": str(e)}

def create_backup():
    """Función principal para crear backup"""
    backup_manager = DatabaseBackup()
    backup_path = backup_manager.create_full_backup()
    
    # Mostrar info del backup creado
    info = backup_manager.get_backup_info(backup_path)
    print(f"\n📋 INFORMACIÓN DEL BACKUP:")
    print(f"📁 Archivo: {info['path']}")
    print(f"📅 Fecha: {info['timestamp']}")
    print(f"💾 Tamaño: {info['size_mb']} MB")
    print(f"📊 Total registros: {info['total_records']}")
    
    return backup_path

def list_all_backups():
    """Lista todos los backups disponibles"""
    backup_manager = DatabaseBackup()
    backups = backup_manager.list_backups()
    
    if not backups:
        print("📭 No hay backups disponibles")
        return
    
    print(f"\n📋 BACKUPS DISPONIBLES ({len(backups)}):")
    for i, backup_path in enumerate(backups, 1):
        info = backup_manager.get_backup_info(backup_path)
        if "error" not in info:
            print(f"  {i}. {os.path.basename(backup_path)}")
            print(f"     📅 {info['timestamp']}")
            print(f"     💾 {info['size_mb']} MB - {info['total_records']} registros")
            print()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        list_all_backups()
    else:
        create_backup()