"""
Script para restaurar el backup de la base de datos
"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración de base de datos
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "sistemas")
DB_NAME = os.getenv("DB_NAME", "upao_timetabling")

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"

def restore_backup(backup_file: str):
    """Restaura la base de datos desde un archivo SQL"""
    
    if not os.path.exists(backup_file):
        print(f"❌ El archivo de backup no existe: {backup_file}")
        return False
    
    print(f"📂 Leyendo backup: {backup_file}")
    
    with open(backup_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # Dividir por comandos SQL (separados por ;)
    commands = [cmd.strip() for cmd in sql_content.split(';') if cmd.strip()]
    
    print(f"📊 Total de comandos SQL: {len(commands)}")
    
    engine = create_engine(DATABASE_URL, echo=False)
    
    success_count = 0
    error_count = 0
    
    with engine.connect() as conn:
        for i, command in enumerate(commands, 1):
            # Saltar comentarios y comandos USE
            if command.startswith('--') or command.strip().upper().startswith('USE'):
                continue
            
            try:
                conn.execute(text(command))
                conn.commit()
                success_count += 1
                
                if i % 50 == 0:
                    print(f"⏳ Procesado {i}/{len(commands)} comandos...")
                    
            except Exception as e:
                error_count += 1
                if "already exists" not in str(e).lower():
                    print(f"⚠️ Error en comando {i}: {str(e)[:100]}")
    
    print(f"\n✅ Restauración completada:")
    print(f"   - Comandos exitosos: {success_count}")
    print(f"   - Comandos con error: {error_count}")
    
    return True

if __name__ == "__main__":
    backup_path = "../backups/bd_backup_20251026_183505.sql"
    
    print("🔄 RESTAURACIÓN DE BASE DE DATOS")
    print("=" * 50)
    print("⚠️  ADVERTENCIA: Esto sobrescribirá las tablas existentes")
    print("=" * 50)
    
    respuesta = input("\n¿Deseas continuar? (SI/NO): ").strip().upper()
    
    if respuesta == "SI":
        restore_backup(backup_path)
    else:
        print("❌ Restauración cancelada")
