import sys
sys.path.insert(0, 'app')
from models import CourseSection
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine('mysql+pymysql://root:sistemas@localhost:3306/upao_timetabling')
Session = sessionmaker(bind=engine)
s = Session()

for sec_id in [1550, 1551, 1552]:
    sec = s.query(CourseSection).filter_by(id=sec_id).first()
    print(f'{sec.id}: {sec.tipo.upper()} seccion {sec.seccion} liga {sec.league} - {sec.alumnos_proyectados} est')
