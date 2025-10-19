import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.models import Classroom

DATABASE_URL = "mysql+pymysql://root:sistemas@localhost:3306/upao_timetabling"
engine = create_engine(DATABASE_URL, echo=False)
Session = sessionmaker(bind=engine)
session = Session()

# Buscar aula 87
aula = session.query(Classroom).filter_by(id=87).first()
if aula:
    print(f"Aula {aula.id}: {aula.codigo}")
    print(f"  Tipo: '{aula.tipo}'")
    print(f"  Capacidad: {aula.capacidad}")
    print(f"  Edificio: {aula.edificio}")
else:
    print("No se encontró aula con ID 87")

# Mostrar todas las aulas LAB disponibles
print("\nAulas tipo LAB:")
aulas_lab = session.query(Classroom).filter_by(tipo='LAB').all()
for aula in aulas_lab:
    print(f"  [{aula.id}] {aula.codigo} - cap {aula.capacidad} - {aula.edificio}")

session.close()
