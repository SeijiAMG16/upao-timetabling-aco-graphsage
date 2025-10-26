"""
Script de Verificación de Mapeo Profesor-Curso

Verifica que todas las secciones activas tengan profesores asignados
en la tabla professor_course_assignments antes de regenerar horarios.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os

# Conexión a BD
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:sistemas@localhost:3306/upao_timetabling")
engine = create_engine(DATABASE_URL, echo=False)
Session = sessionmaker(bind=engine)
session = Session()

print("=" * 80)
print("VERIFICACIÓN DE MAPEO PROFESOR-CURSO")
print("=" * 80)
print()

# 1. Total de secciones activas
result = session.execute(text("""
    SELECT COUNT(*) as total
    FROM course_sections
    WHERE activa = 1 AND alumnos_proyectados > 0
"""))
total_secciones = result.fetchone().total
print(f"📊 Total de secciones activas (alumnos > 0): {total_secciones}")

# 2. Secciones con asignaciones de profesor
result = session.execute(text("""
    SELECT COUNT(DISTINCT cs.id) as con_profesor
    FROM course_sections cs
    INNER JOIN professor_course_assignments pca 
        ON cs.course_id = pca.course_id
    WHERE cs.activa = 1 AND cs.alumnos_proyectados > 0
"""))
con_profesor = result.fetchone().con_profesor
print(f"✅ Secciones con profesor asignado: {con_profesor}")
print(f"❌ Secciones SIN profesor asignado: {total_secciones - con_profesor}")
print()

# 3. Desglose por curso
print("=" * 80)
print("CURSOS SIN ASIGNACIÓN DE PROFESORES")
print("=" * 80)
result = session.execute(text("""
    SELECT 
        c.codigo,
        c.nombre,
        COUNT(DISTINCT cs.id) as secciones_sin_prof
    FROM course_sections cs
    INNER JOIN courses c ON cs.course_id = c.id
    LEFT JOIN professor_course_assignments pca ON cs.course_id = pca.course_id
    WHERE cs.activa = 1 
        AND cs.alumnos_proyectados > 0
        AND pca.id IS NULL
    GROUP BY c.id, c.codigo, c.nombre
    ORDER BY secciones_sin_prof DESC, c.codigo
"""))

cursos_sin_prof = result.fetchall()
if cursos_sin_prof:
    for row in cursos_sin_prof:
        print(f"  • {row.codigo:15} {row.nombre[:50]:50} → {row.secciones_sin_prof:3} secciones")
    print()
    print(f"⚠️  TOTAL: {len(cursos_sin_prof)} cursos sin asignación de profesores")
else:
    print("✅ Todos los cursos tienen asignación de profesores")

print()
print("=" * 80)
print("RESUMEN")
print("=" * 80)
cobertura = (con_profesor / total_secciones * 100) if total_secciones > 0 else 0
print(f"Cobertura de mapeo: {cobertura:.1f}% ({con_profesor}/{total_secciones})")

if cobertura < 100:
    print()
    print("⚠️  ADVERTENCIA:")
    print("   Con el nuevo sistema ESTRICTO, las secciones sin mapeo NO podrán ser asignadas.")
    print("   Esto puede reducir el porcentaje de asignaciones exitosas.")
    print()
    print("💡 RECOMENDACIÓN:")
    print("   1. Completar las asignaciones en professor_course_assignments")
    print("   2. O regenerar con el sistema actual (menos estricto)")

session.close()
