from app.database import SessionLocal
from app.models import Classroom

db = SessionLocal()
aulas = db.query(Classroom).filter(Classroom.active == True).all()
tipos_unicos = set([a.tipo for a in aulas])
print(f'Tipos de aulas únicos: {tipos_unicos}')

labs = [a for a in aulas if 'LAB' in (a.tipo or '').upper()]
print(f'\nAulas de laboratorio (con LAB en el nombre): {len(labs)}')
for a in labs[:10]:
    print(f'  {a.codigo}: tipo="{a.tipo}", capacidad={a.capacidad}')

# Buscar tipo 'laboratorio'
labs_lower = [a for a in aulas if a.tipo == 'laboratorio']
print(f'\nAulas con tipo="laboratorio": {len(labs_lower)}')
for a in labs_lower[:5]:
    print(f'  {a.codigo}: tipo="{a.tipo}", capacidad={a.capacidad}')

db.close()
