"""
Database configuration and connection setup
"""

from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from sqlalchemy.engine.url import make_url
import os
import ssl
from typing import Generator

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "mysql+pymysql://root:sistemas@localhost:3306/upao_timetabling"
)

# Clean up URL for pymysql compatibility
# DigitalOcean uses ssl-mode=REQUIRED but pymysql expects different SSL config
if "ssl-mode=" in DATABASE_URL or "ssl_mode=" in DATABASE_URL:
    # Remove ssl-mode parameter from URL, we'll handle SSL via connect_args
    import re
    DATABASE_URL = re.sub(r'[\?&]ssl[-_]mode=[^&]*', '', DATABASE_URL)
    # Clean up any double ? or trailing ?
    DATABASE_URL = DATABASE_URL.replace('?&', '?').rstrip('?')

# Validamos que la URL de base de datos no use SQLite, ya que debemos operar solo con la BD oficial
if make_url(DATABASE_URL).get_backend_name().startswith("sqlite"):
    raise RuntimeError(
        "DATABASE_URL apunta a SQLite; configure credenciales MySQL para usar la base de datos oficial"
    )

# Configure SSL for DigitalOcean Managed MySQL
ssl_args = {}
if "ondigitalocean.com" in DATABASE_URL or "REQUIRE" in os.getenv("DATABASE_URL", ""):
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    ssl_args = {"ssl": ssl_context}

# Engine configuration
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Disabled for ACO execution (too much output)
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args=ssl_args,
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



def create_tables():
    """Create all tables"""
    from .models import Base
    Base.metadata.create_all(bind=engine)



def drop_tables():
    """Drop all tables (use with caution!)"""
    from .models import Base
    Base.metadata.drop_all(bind=engine)

def create_database_if_not_exists():
    """Create database if it doesn't exist"""
    import pymysql
    
    try:
        # Connect to MySQL server without specifying database
        connection = pymysql.connect(
            host='localhost',
            user='root',
            password='sistemas',
            charset='utf8mb4'
        )
        
        with connection.cursor() as cursor:
            # Create database if it doesn't exist
            cursor.execute("CREATE DATABASE IF NOT EXISTS upao_timetabling CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            print("Database 'upao_timetabling' created or already exists")
        
        connection.close()
        return True
        
    except Exception as e:
        print(f"Error creating database: {e}")
        return False

# Database initialization functions
def init_time_slots(db: Session):
    """Initialize time slots with UPAO schedule"""
    from .models import TimeSlot
    
    # Check if already initialized
    existing = db.query(TimeSlot).first()
    if existing:
        return
    
    # UPAO time slots
    horarios = [
        ("07:00", "07:50"), ("07:55", "08:45"), ("08:50", "09:40"), ("09:45", "10:35"),
        ("10:40", "11:30"), ("11:35", "12:25"), ("12:30", "13:20"), ("13:25", "14:15"),
        ("14:20", "15:10"), ("15:15", "16:05"), ("16:10", "17:00"), ("17:05", "17:55"),
        ("18:00", "18:50"), ("18:55", "19:45"), ("19:50", "20:40"), ("20:45", "21:35")
    ]
    
    dias = [1, 2, 3, 4, 5, 6]  # Lunes a Sábado
    
    for dia in dias:
        for orden, (inicio, fin) in enumerate(horarios, 1):
            # Determinar período
            hora_inicio = int(inicio.split(':')[0])
            if hora_inicio < 12:
                periodo = "mañana"
            elif hora_inicio < 18:
                periodo = "tarde"
            else:
                periodo = "noche"
            
            time_slot = TimeSlot(
                dia_semana=dia,
                hora_inicio=inicio,
                hora_fin=fin,
                periodo=periodo,
                orden=orden,
                activo=True
            )
            db.add(time_slot)
    
    db.commit()

def init_classrooms(db: Session):
    """Initialize classrooms with UPAO infrastructure"""
    from .models import Classroom
    
    # Check if already initialized
    existing = db.query(Classroom).first()
    if existing:
        return
    
    classrooms = []
    
    # Aulas F (TODOS son laboratorios ≤20 alumnos) - F201 a F404
    for piso in [2, 3, 4]:
        for num in range(1, 5):  # F201-F404
            classroom = Classroom(
                codigo=f"F{piso}0{num}",
                edificio='F',
                piso=f"F{piso}",
                capacidad=20,
                tipo='laboratorio',
                tiene_computadoras=True,
                numero_computadoras=20
            )
            classrooms.append(classroom)
    
    # Aulas G - G601 a G809
    for piso in [6, 7, 8]:
        for num in range(1, 10):  # G601-G809
            # Solo G601, G701, G801 son laboratorios
            if num == 1:  # Primer aula de cada piso es laboratorio
                classroom = Classroom(
                    codigo=f"G{piso}0{num}",
                    edificio='G',
                    piso=f"G{piso}",
                    capacidad=30,  # Laboratorios G >20 alumnos
                    tipo='laboratorio',
                    tiene_computadoras=True,
                    numero_computadoras=30
                )
            else:  # G602-G809 (excepto G601, G701, G801) son aulas teóricas
                classroom = Classroom(
                    codigo=f"G{piso}0{num}",
                    edificio='G',
                    piso=f"G{piso}",
                    capacidad=40,  # Aulas teóricas con mayor capacidad
                    tipo='teorica',
                    tiene_computadoras=False,
                    numero_computadoras=0
                )
            classrooms.append(classroom)
    
    # Add all classrooms
    for classroom in classrooms:
        db.add(classroom)
    
    db.commit()

def initialize_database(db: Session):
    """Initialize database with basic data"""
    print("Initializing time slots...")
    init_time_slots(db)
    
    print("Initializing classrooms...")
    init_classrooms(db)
    
    print("Database initialization completed!")

# Health check function
def check_database_connection() -> bool:
    """Check if database connection is working"""
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False