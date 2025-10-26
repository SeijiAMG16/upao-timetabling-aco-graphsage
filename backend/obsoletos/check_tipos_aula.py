import sys
sys.path.insert(0, 'app')
from models import Classroom
from sqlalchemy import create_engine, distinct
from sqlalchemy.orm import sessionmaker

engine = create_engine('mysql+pymysql://root:sistemas@localhost:3306/upao_timetabling')
Session = sessionmaker(bind=engine)
s = Session()

tipos_unicos = s.query(distinct(Classroom.tipo)).all()
print("Tipos de aula en la BD:")
for tipo in tipos_unicos:
    count = s.query(Classroom).filter_by(tipo=tipo[0]).count()
    print(f"  '{tipo[0]}': {count} aulas")
