"""
Verificar aulas de laboratorio disponibles
"""
import sys
sys.path.insert(0, 'app')

from models import Classroom
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine('mysql+pymysql://root:sistemas@localhost:3306/upao_timetabling')
Session = sessionmaker(bind=engine)
session = Session()

print("="*80)
print("AULAS DE LABORATORIO EN LA BASE DE DATOS")
print("="*80)

# Todas las aulas de laboratorio
labs = session.query(Classroom).filter(
    Classroom.tipo == 'laboratorio'
).order_by(Classroom.capacidad).all()

print(f"\nTotal de aulas laboratorio: {len(labs)}")

if labs:
    print("\nListado completo:")
    for lab in labs:
        estado = "ACTIVA" if lab.active else "INACTIVA"
        print(f"  {lab.codigo}: cap {lab.capacidad}, edificio {lab.edificio}, piso {lab.piso}, PCs: {lab.numero_computadoras} [{estado}]")
else:
    print("\n*** NO HAY AULAS DE LABORATORIO REGISTRADAS ***")

# Ver todas las aulas activas
print("\n"+"="*80)
print("TODAS LAS AULAS ACTIVAS (CUALQUIER TIPO)")
print("="*80)

todas_activas = session.query(Classroom).filter(
    Classroom.active == 1
).all()

tipos = {}
for aula in todas_activas:
    if aula.tipo not in tipos:
        tipos[aula.tipo] = []
    tipos[aula.tipo].append(aula)

for tipo, aulas in tipos.items():
    print(f"\nTipo '{tipo}': {len(aulas)} aulas")
    for aula in aulas[:3]:
        print(f"  {aula.codigo}: cap {aula.capacidad}")
    if len(aulas) > 3:
        print(f"  ... y {len(aulas)-3} más")

session.close()
