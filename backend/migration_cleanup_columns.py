"""
Script de migración para eliminar columnas innecesarias
Ejecuta las consultas ALTER TABLE para limpiar la base de datos
"""
import logging
from sqlalchemy import text
from app.database import SessionLocal, engine

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def execute_migration():
    """
    Ejecuta la migración para eliminar columnas innecesarias
    """
    logger.info("🔧 Iniciando migración: eliminación de columnas innecesarias")
    
    session = SessionLocal()
    
    try:
        # Lista de operaciones de migración
        migrations = [
            # Eliminar columnas de professors
            {
                "description": "Eliminar columna nombres de professors",
                "sql": "ALTER TABLE professors DROP COLUMN nombres"
            },
            {
                "description": "Eliminar columna apellidos de professors", 
                "sql": "ALTER TABLE professors DROP COLUMN apellidos"
            },
            {
                "description": "Eliminar columna email de professors",
                "sql": "ALTER TABLE professors DROP COLUMN email"
            },
            {
                "description": "Eliminar columna telefono de professors",
                "sql": "ALTER TABLE professors DROP COLUMN telefono"
            },
            {
                "description": "Eliminar columna categoria de professors",
                "sql": "ALTER TABLE professors DROP COLUMN categoria"
            },
            {
                "description": "Eliminar columna especialidad de professors",
                "sql": "ALTER TABLE professors DROP COLUMN especialidad"
            },
            {
                "description": "Eliminar columna grado_academico de professors",
                "sql": "ALTER TABLE professors DROP COLUMN grado_academico"
            },
            
            # Eliminar columnas de courses
            {
                "description": "Eliminar columna restricciones_especiales de courses",
                "sql": "ALTER TABLE courses DROP COLUMN restricciones_especiales"
            },
            
            # Actualizar valores de modalidad en courses
            {
                "description": "Actualizar modalidad PRS a presencial",
                "sql": "UPDATE courses SET modalidad = 'presencial' WHERE modalidad = 'PRS'"
            },
            {
                "description": "Actualizar modalidad NPR a no_presencial", 
                "sql": "UPDATE courses SET modalidad = 'no_presencial' WHERE modalidad = 'NPR'"
            }
        ]
        
        # Ejecutar cada migración
        for i, migration in enumerate(migrations, 1):
            try:
                logger.info(f"🔄 [{i}/{len(migrations)}] {migration['description']}")
                session.execute(text(migration['sql']))
                session.commit()
                logger.info(f"✅ [{i}/{len(migrations)}] Completado")
            except Exception as e:
                logger.warning(f"⚠️  [{i}/{len(migrations)}] No aplicado (posiblemente ya ejecutado): {str(e)}")
                session.rollback()
        
        logger.info("🎉 Migración completada exitosamente")
        
        # Verificar estado final
        verify_migration(session)
        
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Error en migración: {str(e)}")
        raise
    finally:
        session.close()

def verify_migration(session):
    """
    Verifica que la migración se aplicó correctamente
    """
    logger.info("🔍 Verificando estado de la migración...")
    
    try:
        # Verificar estructura de professors
        result = session.execute(text("DESCRIBE professors"))
        professors_columns = [row[0] for row in result.fetchall()]
        
        removed_professor_columns = ['nombres', 'apellidos', 'email', 'telefono', 'categoria', 'especialidad', 'grado_academico']
        still_present = [col for col in removed_professor_columns if col in professors_columns]
        
        if still_present:
            logger.warning(f"⚠️  Columnas de professors aún presentes: {still_present}")
        else:
            logger.info("✅ Todas las columnas innecesarias eliminadas de professors")
        
        # Verificar estructura de courses
        result = session.execute(text("DESCRIBE courses"))
        courses_columns = [row[0] for row in result.fetchall()]
        
        if 'restricciones_especiales' in courses_columns:
            logger.warning("⚠️  Columna restricciones_especiales aún presente en courses")
        else:
            logger.info("✅ Columna restricciones_especiales eliminada de courses")
        
        # Verificar valores de modalidad
        result = session.execute(text("SELECT DISTINCT modalidad FROM courses"))
        modalidades = [row[0] for row in result.fetchall()]
        
        old_modalidades = [m for m in modalidades if m in ['PRS', 'NPR']]
        if old_modalidades:
            logger.warning(f"⚠️  Modalidades antiguas aún presentes: {old_modalidades}")
        else:
            logger.info("✅ Modalidades actualizadas correctamente")
        
        logger.info(f"📊 Modalidades actuales: {modalidades}")
        
    except Exception as e:
        logger.error(f"❌ Error verificando migración: {str(e)}")

def rollback_migration():
    """
    Script de rollback (opcional - solo para emergencias)
    ADVERTENCIA: Este script recreará las columnas pero sin datos
    """
    logger.warning("🚨 EJECUTANDO ROLLBACK - Las columnas se recrearán VACÍAS")
    
    session = SessionLocal()
    
    try:
        rollback_operations = [
            # Recrear columnas de professors (VACÍAS)
            "ALTER TABLE professors ADD COLUMN nombres VARCHAR(100)",
            "ALTER TABLE professors ADD COLUMN apellidos VARCHAR(100)", 
            "ALTER TABLE professors ADD COLUMN email VARCHAR(150)",
            "ALTER TABLE professors ADD COLUMN telefono VARCHAR(20)",
            "ALTER TABLE professors ADD COLUMN categoria VARCHAR(50)",
            "ALTER TABLE professors ADD COLUMN especialidad VARCHAR(200)",
            "ALTER TABLE professors ADD COLUMN grado_academico VARCHAR(100)",
            
            # Recrear columna de courses
            "ALTER TABLE courses ADD COLUMN restricciones_especiales TEXT"
        ]
        
        for operation in rollback_operations:
            try:
                session.execute(text(operation))
                session.commit()
                logger.info(f"✅ Rollback aplicado: {operation}")
            except Exception as e:
                logger.warning(f"⚠️  Rollback no aplicado: {str(e)}")
                session.rollback()
        
        logger.warning("🚨 ROLLBACK COMPLETADO - Revisa los datos manualmente")
        
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Error en rollback: {str(e)}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
        rollback_migration()
    else:
        execute_migration()