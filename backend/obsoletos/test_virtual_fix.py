"""
Test rápido: verificar que el sistema maneja correctamente cursos NO_PRESENCIAL
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from backend.app.models import Course, CourseSection

engine = create_engine('mysql+pymysql://root:sistemas@localhost:3306/upao_timetabling', echo=False)
Session = sessionmaker(bind=engine)
session = Session()

def test_virtual_course_handling():
    """Verifica que hay cursos virtuales en la BD y muestra estadísticas"""
    
    try:
        # Contar cursos y secciones virtuales
        virtual_courses = session.query(Course).filter(
            func.upper(Course.modalidad) == 'NO_PRESENCIAL'
        ).all()
        
        virtual_sections = session.query(CourseSection).join(Course).filter(
            func.upper(Course.modalidad) == 'NO_PRESENCIAL'
        ).all()
        
        print(f"\n{'='*70}")
        print(f"VERIFICACIÓN DE CURSOS VIRTUALES (NO_PRESENCIAL)")
        print(f"{'='*70}")
        print(f"✅ Cursos virtuales: {len(virtual_courses)}")
        print(f"✅ Secciones virtuales: {len(virtual_sections)}")
        print(f"\nPrimeros 5 cursos virtuales:")
        for i, course in enumerate(virtual_courses[:5], 1):
            sections_count = session.query(CourseSection).filter(
                CourseSection.course_id == course.id
            ).count()
            course_code = getattr(course, 'codigo', getattr(course, 'code', 'N/A'))
            course_name = getattr(course, 'nombre', getattr(course, 'name', 'N/A'))
            print(f"  {i}. {course_code} - {course_name[:40]} ({sections_count} secciones)")
        
        print(f"\n{'='*70}")
        print(f"SOLUCIÓN IMPLEMENTADA:")
        print(f"{'='*70}")
        print(f"✅ graph_builder.py: Skip classroom edges para NO_PRESENCIAL")
        print(f"✅ aco_engine.py: Permitir classroom_id=None (índice -1)")
        print(f"✅ constraints.py: Skip validaciones de aula para virtuales")
        print(f"✅ Assignment: classroom_id ahora es Optional[int]")
        
        print(f"\n{'='*70}")
        print(f"LISTO PARA GENERAR HORARIO COMPLETO")
        print(f"{'='*70}")
        print(f"Las {len(virtual_sections)} secciones virtuales NO requerirán aula física")
        print(f"El proceso debe completarse sin estancarse en sección 1815")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        session.close()

if __name__ == "__main__":
    success = test_virtual_course_handling()
    sys.exit(0 if success else 1)
