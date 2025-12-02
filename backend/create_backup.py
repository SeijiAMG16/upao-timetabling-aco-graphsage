"""
Script para crear backup de la base de datos MySQL
"""
import subprocess
import sys
from datetime import datetime
from pathlib import Path

def create_backup():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"backup_upao_timetabling_{timestamp}.sql"
    
    # Buscar mysqldump en rutas comunes
    possible_paths = [
        r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe",
        r"C:\Program Files\MySQL\MySQL Server 5.7\bin\mysqldump.exe",
        r"C:\xampp\mysql\bin\mysqldump.exe",
        r"C:\wamp64\bin\mysql\mysql8.0.27\bin\mysqldump.exe",
    ]
    
    mysqldump_path = None
    for path in possible_paths:
        if Path(path).exists():
            mysqldump_path = path
            break
    
    if not mysqldump_path:
        print("❌ No se encontró mysqldump. Intentando con comando directo...")
        mysqldump_path = "mysqldump"
    
    print(f"📦 Creando backup de la base de datos...")
    print(f"   Archivo: {backup_file}")
    
    # Crear backup
    cmd = [
        mysqldump_path,
        "-u", "root",
        "-p",
        "--databases", "upao_timetabling",
        "--routines",
        "--triggers",
        "--events",
        "--single-transaction",
        "--quick",
        "--lock-tables=false"
    ]
    
    try:
        with open(backup_file, 'w', encoding='utf-8') as f:
            result = subprocess.run(
                cmd,
                stdout=f,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
        
        file_size = Path(backup_file).stat().st_size / (1024 * 1024)
        print(f"✅ Backup creado exitosamente!")
        print(f"   Tamaño: {file_size:.2f} MB")
        print(f"   Ubicación: {Path(backup_file).absolute()}")
        return backup_file
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error al crear backup: {e.stderr}")
        return None
    except FileNotFoundError:
        print("❌ mysqldump no encontrado. Por favor ejecuta manualmente:")
        print(f"   mysqldump -u root -p --databases upao_timetabling > {backup_file}")
        return None

if __name__ == "__main__":
    create_backup()
