"""
Test directo del sistema ACO+GraphSAGE
Evita el pipeline para no tener problemas con emojis en Windows
"""
import sys
import os
from pathlib import Path
import time
import argparse

# Configurar encoding
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

parser = argparse.ArgumentParser(description="Prueba directa del motor ACO+GraphSAGE")
parser.add_argument("--ants", type=int, default=5, help="Numero de hormigas a emplear")
parser.add_argument("--iters", type=int, default=15, help="Numero de iteraciones")
args = parser.parse_args()

backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.database import SessionLocal
from app.aco_graphsage.graph_builder import TimetableGraphBuilder
from app.aco_graphsage.graphsage_model import create_model_from_graph
from app.aco_graphsage.aco_engine import create_aco_engine
from app.models import Course, CourseSection, Professor, Classroom, TimeSlot

print("="*80)
print("PRUEBA DIRECTA: ACO+GraphSAGE")
print("="*80)
print()

db = SessionLocal()

try:
    # 1. Verificar datos
    n_sections = db.query(CourseSection).count()
    n_professors = db.query(Professor).count()
    n_classrooms = db.query(Classroom).count()
    n_timeslots = db.query(TimeSlot).count()
    
    print(f"Datos: {n_sections} secciones, {n_professors} profesores, {n_classrooms} aulas, {n_timeslots} franjas")
    print()
    
    # 2. Construir grafo
    print("1. Construyendo grafo heterogeneo...")
    builder = TimetableGraphBuilder(db)
    graph = builder.build_graph()
    print(f"   [OK] Grafo con {graph['section'].num_nodes} secciones")
    print()
    
    # 3. Crear modelo
    print("2. Creando modelo GraphSAGE...")
    model = create_model_from_graph(graph)
    model.eval()
    print(f"   [OK] Modelo con {model.hidden_dim} dimensiones ocultas")
    print()
    
    # 4. Crear motor ACO
    print("3. Inicializando motor ACO...")
    aco_engine = create_aco_engine(
        graph=graph,
        model=model,
        graph_builder=builder,
        db_session=db,
        params={
            'n_hormigas': args.ants,
            'n_iteraciones': args.iters,
        }
    )
    print("   [OK] Motor ACO inicializado")
    print()
    
    # 5. Ejecutar optimizacion
    print("="*80)
    print("EJECUTANDO OPTIMIZACION")
    print("="*80)
    print(f"Parametros: {args.ants} hormigas, {args.iters} iteraciones")
    print()
    
    start_time = time.time()
    solution = aco_engine.optimize()
    elapsed = time.time() - start_time
    
    print()
    print("="*80)
    print("RESULTADOS")
    print("="*80)
    print()
    print(f"Tiempo total: {elapsed:.2f} segundos")
    print()
    
    if solution:
        print("[OK] SOLUCION ENCONTRADA!")
        print()
        print(f"  Asignaciones realizadas: {len(solution.assignments)}")
        print(f"  Costo total: {solution.total_cost:.2f}")
        print(f"  Solucion valida: {'SI' if solution.is_valid else 'NO'}")
        print(f"  Violaciones duras: {solution.hard_violations}")
        print()
        
        if hasattr(solution, 'soft_penalties') and solution.soft_penalties:
            print("  Penalizaciones suaves:")
            for key, value in solution.soft_penalties.items():
                if value > 0:
                    print(f"    - {key}: {value:.2f}")
        
        print()
        print(f"  Cobertura: {len(solution.assignments)}/{n_sections} secciones asignadas")
        print(f"  Porcentaje: {len(solution.assignments)/n_sections*100:.1f}%")
        
    else:
        print("[ADVERTENCIA] No se encontro solucion valida")
        print("Esto puede ser normal con parametros bajos y datos complejos")
    
    print()
    print("="*80)
    print("[OK] PRUEBA COMPLETADA")
    print("="*80)
    
except Exception as e:
    print()
    print("[ERROR]", str(e))
    import traceback
    traceback.print_exc()

finally:
    db.close()
