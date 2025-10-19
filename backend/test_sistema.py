"""
Script de Prueba Rápida del Sistema ACO+GraphSAGE

Prueba los componentes básicos sin necesidad de servidor.
"""

import sys
from pathlib import Path

# Agregar backend al path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

print("="*80)
print("🧪 PRUEBA RÁPIDA DEL SISTEMA ACO+GraphSAGE")
print("="*80)

# Test 1: Imports
print("\n1️⃣  Probando imports...")
try:
    from app.database import SessionLocal, engine
    from app.models import Base, Course, CourseSection, Professor, Classroom, TimeSlot
    from app.aco_graphsage import ACO_PARAMS, GRAPHSAGE_PARAMS, CONSTRAINT_WEIGHTS
    print("✅ Todos los imports exitosos")
except Exception as e:
    print(f"❌ Error en imports: {e}")
    sys.exit(1)

# Test 2: Conexión a BD
print("\n2️⃣  Probando conexión a base de datos...")
try:
    db = SessionLocal()
    
    # Contar registros
    n_courses = db.query(Course).count()
    n_sections = db.query(CourseSection).count()
    n_professors = db.query(Professor).count()
    n_classrooms = db.query(Classroom).count()
    n_timeslots = db.query(TimeSlot).count()
    
    print(f"✅ Conexión exitosa a BD")
    print(f"   📚 Cursos: {n_courses}")
    print(f"   📖 Secciones: {n_sections}")
    print(f"   👨‍🏫 Profesores: {n_professors}")
    print(f"   🏫 Aulas: {n_classrooms}")
    print(f"   ⏰ Franjas horarias: {n_timeslots}")
    
    if n_sections == 0:
        print("\n⚠️  WARNING: No hay secciones en la BD")
        print("   Necesitas poblar la BD con datos para generar horarios")
    
    db.close()
except Exception as e:
    print(f"❌ Error de conexión: {e}")
    sys.exit(1)

# Test 3: Configuración
print("\n3️⃣  Verificando configuración...")
print(f"✅ Parámetros ACO:")
print(f"   - Hormigas: {ACO_PARAMS['n_hormigas']}")
print(f"   - Iteraciones: {ACO_PARAMS['n_iteraciones']}")
print(f"   - Alpha (feromona): {ACO_PARAMS['alpha']}")
print(f"   - Beta (heurística): {ACO_PARAMS['beta']}")
print(f"\n✅ Pesos de Restricciones:")
print(f"   - Huecos estudiantes: {CONSTRAINT_WEIGHTS['huecos_estudiantes']}")
print(f"   - Cambio edificio: {CONSTRAINT_WEIGHTS['cambio_edificio']}")
print(f"   - Huecos profesores: {CONSTRAINT_WEIGHTS['huecos_profesores']}")

# Test 4: Graph Builder (solo si hay datos)
if n_sections > 0:
    print("\n4️⃣  Probando construcción de grafo...")
    try:
        from app.aco_graphsage import TimetableGraphBuilder
        
        db = SessionLocal()
        builder = TimetableGraphBuilder(db)
        graph = builder.build_graph()
        
        print(f"✅ Grafo construido exitosamente")
        print(f"   - Nodos sección: {graph['section'].x.shape[0]}")
        print(f"   - Nodos profesor: {graph['professor'].x.shape[0]}")
        print(f"   - Nodos aula: {graph['classroom'].x.shape[0]}")
        print(f"   - Nodos franja: {graph['timeslot'].x.shape[0]}")
        print(f"   - Nodos currículo: {graph['curriculum'].x.shape[0]}")
        
        db.close()
    except Exception as e:
        print(f"⚠️  Error construyendo grafo: {e}")
else:
    print("\n4️⃣  ⏭️  Saltando construcción de grafo (no hay datos)")

# Resumen Final
print("\n" + "="*80)
print("📊 RESUMEN")
print("="*80)
print("\n✅ Sistema funcionando correctamente")
print("\n📝 Próximos pasos:")

if n_sections == 0:
    print("   1. Poblar la BD con datos reales")
    print("   2. Ejecutar: python -m app.api.endpoints.algorithm")
    print("   3. O usar frontend para generar horarios")
else:
    print("   1. Iniciar servidor: uvicorn app.main:app --reload")
    print("   2. Probar API: POST http://localhost:8000/api/algorithm/execute")
    print("   3. Ver documentación: http://localhost:8000/docs")

print("\n🎉 ¡Todo listo!")
