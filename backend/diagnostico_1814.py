#!/usr/bin/env python3
"""Diagnóstico de la sección 1814 que bloquea a las hormigas exitosas."""

from app.database import SessionLocal
from app.models import CourseSection, Classroom

def main():
    session = SessionLocal()
    
    # Obtener sección 1814
    s1814 = session.query(CourseSection).filter_by(id=1814).first()
    
    print("=" * 80)
    print("DIAGNÓSTICO SECCIÓN 1814")
    print("=" * 80)
    print(f"Código: {s1814.codigo_completo}")
    print(f"Tipo: {s1814.tipo}")
    print(f"Estudiantes proyectados: {s1814.alumnos_proyectados}")
    print(f"League: {s1814.league}")
    print(f"Modalidad: {s1814.course.modalidad if s1814.course else 'N/A'}")
    print()
    
    # Normalizar tipo
    tipo_normalizado = 'laboratorio' if s1814.tipo == 'laboratorio' else (
        'teorica' if s1814.tipo in ['teorica', 'practica'] else s1814.tipo
    )
    tipo_aula = 'LAB' if tipo_normalizado == 'laboratorio' else 'NOLAB'
    
    print(f"Tipo normalizado esperado: {tipo_normalizado}")
    print(f"Tipo de aula requerido en BD: {tipo_aula}")
    print()
    
    # Buscar aulas compatibles
    aulas = session.query(Classroom).filter(
        Classroom.active == True,
        Classroom.tipo == tipo_aula,
        Classroom.capacidad >= s1814.alumnos_proyectados
    ).all()
    
    print(f"✅ Aulas compatibles encontradas: {len(aulas)}")
    if aulas:
        print("\nPrimeras 10 aulas:")
        for i, a in enumerate(aulas[:10], 1):
            print(f"  {i}. {a.codigo}: capacidad={a.capacidad}, tipo={a.tipo}")
    else:
        print("❌ NO HAY AULAS COMPATIBLES")
        print("\nBuscando aulas cercanas:")
        aulas_todas = session.query(Classroom).filter(
            Classroom.active == True,
            Classroom.tipo == tipo_aula
        ).order_by(Classroom.capacidad).all()
        print(f"Total aulas tipo {tipo_aula}: {len(aulas_todas)}")
        if aulas_todas:
            print(f"Capacidad mínima: {aulas_todas[0].capacidad}")
            print(f"Capacidad máxima: {aulas_todas[-1].capacidad}")
    
    print()
    print("=" * 80)
    print("ANÁLISIS DE SECCIONES 1810-1814")
    print("=" * 80)
    
    for sec_id in [1810, 1811, 1812, 1813, 1814]:
        sec = session.query(CourseSection).filter_by(id=sec_id).first()
        tipo_norm = 'laboratorio' if sec.tipo == 'laboratorio' else (
            'teorica' if sec.tipo in ['teorica', 'practica'] else sec.tipo
        )
        tipo_aula_req = 'LAB' if tipo_norm == 'laboratorio' else 'NOLAB'
        num_aulas = session.query(Classroom).filter(
            Classroom.active == True,
            Classroom.tipo == tipo_aula_req,
            Classroom.capacidad >= sec.alumnos_proyectados
        ).count()
        
        print(f"{sec_id}: {sec.codigo_completo:30s} tipo={sec.tipo:12s} "
              f"est={sec.alumnos_proyectados:3d} → aulas={num_aulas:3d}")
    
    session.close()

if __name__ == "__main__":
    main()
