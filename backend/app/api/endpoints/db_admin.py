"""
Endpoint para inicializar/restaurar la base de datos
Este endpoint es temporal y debe eliminarse después de la configuración inicial
"""

from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from ...database import engine
import logging
import httpx

router = APIRouter(prefix="/api/admin", tags=["Admin"])
logger = logging.getLogger(__name__)

# URL del backup en GitHub (raw)
BACKUP_URL = "https://raw.githubusercontent.com/SeijiAMG16/upao-timetabling-aco-graphsage/main/backend/backup_upao_timetabling_20251201_185228.sql"

@router.post("/init-database")
async def init_database():
    """
    Inicializa la base de datos con el esquema y datos básicos.
    Descarga el backup desde GitHub y lo ejecuta.
    NOTA: Este endpoint es temporal y debe eliminarse después de la configuración.
    """
    try:
        logger.info("Iniciando restauración de base de datos...")
        
        # Descargar SQL desde GitHub
        logger.info(f"Descargando backup desde: {BACKUP_URL}")
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(BACKUP_URL)
            if response.status_code != 200:
                return {"status": "error", "message": f"Error descargando backup: {response.status_code}"}
            sql_content = response.text
        
        logger.info(f"Backup descargado: {len(sql_content)} bytes")
        
        # Ejecutar SQL
        with engine.connect() as conn:
            # Deshabilitar FK checks
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            conn.execute(text("SET UNIQUE_CHECKS = 0"))
            
            # Parsear y ejecutar statements
            statements = []
            current = []
            for line in sql_content.split('\n'):
                # Saltar líneas de comentarios y vacías
                stripped = line.strip()
                if stripped.startswith('--') or stripped.startswith('/*') or not stripped:
                    continue
                # Saltar CREATE DATABASE y USE
                if 'CREATE DATABASE' in stripped.upper() or stripped.upper().startswith('USE '):
                    continue
                    
                current.append(line)
                if stripped.endswith(';'):
                    stmt = '\n'.join(current).strip()
                    if stmt:
                        statements.append(stmt)
                    current = []
            
            executed = 0
            errors = []
            for stmt in statements:
                try:
                    if stmt.strip() and not stmt.strip().startswith('--'):
                        conn.execute(text(stmt))
                        executed += 1
                except Exception as e:
                    error_msg = str(e)
                    if 'already exists' not in error_msg.lower() and 'duplicate' not in error_msg.lower():
                        errors.append(f"{error_msg[:100]}")
            
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
            conn.execute(text("SET UNIQUE_CHECKS = 1"))
            conn.commit()
        
        # Verificar tablas creadas
        with engine.connect() as conn:
            result = conn.execute(text("SHOW TABLES"))
            tables = [row[0] for row in result.fetchall()]
            
            table_counts = {}
            for table in tables:
                try:
                    count_result = conn.execute(text(f"SELECT COUNT(*) FROM `{table}`"))
                    table_counts[table] = count_result.fetchone()[0]
                except:
                    table_counts[table] = "error"
        
        return {
            "status": "success",
            "message": "Base de datos inicializada correctamente",
            "statements_executed": executed,
            "errors_count": len(errors),
            "tables": table_counts,
            "first_errors": errors[:5] if errors else []
        }
        
    except Exception as e:
        logger.error(f"Error en init_database: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/db-status")
async def db_status():
    """Verifica el estado de la base de datos"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SHOW TABLES"))
            tables = [row[0] for row in result.fetchall()]
            
            table_counts = {}
            for table in tables:
                try:
                    count_result = conn.execute(text(f"SELECT COUNT(*) FROM `{table}`"))
                    table_counts[table] = count_result.fetchone()[0]
                except:
                    table_counts[table] = "error"
        
        return {
            "status": "connected",
            "tables": table_counts
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
