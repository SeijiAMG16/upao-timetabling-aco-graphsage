from app.database import SessionLocal
from app.models import Classroom
from sqlalchemy import func

session = SessionLocal()

print('AULAS TEORIA/PRACTICA (Top 10 más pequeñas):')
for c in session.query(Classroom).filter(
    Classroom.active==True, 
    Classroom.tipo.in_(['TEORIA','PRACTICA'])
).order_by(Classroom.capacidad).limit(10).all():
    print(f'  {c.codigo}: {c.tipo}, Cap={c.capacidad}')

print('\nAULAS LABORATORIO/COMPUTO (Top 10 más pequeñas):')
for c in session.query(Classroom).filter(
    Classroom.active==True,
    Classroom.tipo.in_(['LABORATORIO','COMPUTO'])
).order_by(Classroom.capacidad).limit(10).all():
    print(f'  {c.codigo}: {c.tipo}, Cap={c.capacidad}')

print('\nCAPACIDAD MÁXIMA DISPONIBLE:')
maxprac = session.query(func.max(Classroom.capacidad)).filter(
    Classroom.active==True, 
    Classroom.tipo.in_(['TEORIA','PRACTICA'])
).scalar()
maxlab = session.query(func.max(Classroom.capacidad)).filter(
    Classroom.active==True,
    Classroom.tipo.in_(['LABORATORIO','COMPUTO'])
).scalar()

print(f'  TEORIA/PRACTICA: {maxprac}')
print(f'  LABORATORIO/COMPUTO: {maxlab}')

session.close()
