"""
Test ultra-rápido del ACO optimizado
Solo 3 hormigas × 5 iteraciones para ver velocidad
"""
import sys
import time
from pathlib import Path

# Agregar backend al path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from app.database.config import SessionLocal
from app.aco_graphsage.graph_builder import GraphBuilder
from app.aco_graphsage.gnn_model import TimetableGNN
from app.aco_graphsage.aco_engine import ACOEngine
from app.aco_graphsage.constraints import HardConstraintValidator, SoftConstraintValidator

def main():
    print("=" * 80)
    print("TEST ULTRA-RÁPIDO DE ACO OPTIMIZADO")
    print("=" * 80)
    print()
    
    db = SessionLocal()
    
    try:
        # 1. Construir grafo
        print("1. Construyendo grafo...")
        t0 = time.time()
        builder = GraphBuilder(db)
        graph = builder.build_graph()
        t_graph = time.time() - t0
        print(f"   ✓ Grafo listo en {t_graph:.2f}s")
        print()
        
        # 2. Crear modelo
        print("2. Creando modelo GNN...")
        t0 = time.time()
        model = TimetableGNN(
            section_in=graph['section'].x.shape[1],
            prof_in=graph['professor'].x.shape[1],
            classroom_in=graph['classroom'].x.shape[1],
            timeslot_in=graph['timeslot'].x.shape[1],
            hidden_dim=32,
            out_dim=16
        )
        t_model = time.time() - t0
        print(f"   ✓ Modelo listo en {t_model:.2f}s")
        print()
        
        # 3. Validadores
        print("3. Preparando validadores...")
        t0 = time.time()
        hard_validator = HardConstraintValidator(db)
        soft_validator = SoftConstraintValidator(db)
        t_val = time.time() - t0
        print(f"   ✓ Validadores listos en {t_val:.2f}s")
        print()
        
        # 4. ACO ultra-rápido
        print("4. Ejecutando ACO ULTRA-RÁPIDO...")
        print("   Configuración: 3 hormigas × 5 iteraciones")
        print()
        
        params = {
            "n_hormigas": 3,
            "n_iteraciones": 5,
            "alpha": 1.0,
            "beta": 3.0,  # Más peso a heurística
            "rho": 0.2,   # Evaporación rápida
            "q0": 0.9     # Más explotación
        }
        
        aco = ACOEngine(
            graph=graph,
            gnn_model=model,
            hard_validator=hard_validator,
            soft_validator=soft_validator,
            **params
        )
        
        t0 = time.time()
        solution = aco.optimize()
        t_aco = time.time() - t0
        
        print()
        print("=" * 80)
        print("RESULTADOS DEL TEST")
        print("=" * 80)
        print()
        print(f"⏱️  Tiempo total de ACO: {t_aco:.1f}s ({t_aco/60:.2f} minutos)")
        print()
        
        if solution and solution.is_valid:
            print(f"✅ Solución válida encontrada!")
            print(f"   Secciones asignadas: {len(solution.assignments)}")
            print(f"   Costo total: {solution.total_cost:.2f}")
        elif solution:
            print(f"⚠️  Solución parcial:")
            print(f"   Secciones asignadas: {len(solution.assignments)}")
            print(f"   Costo: {solution.total_cost:.2f}")
        else:
            print("❌ No se encontró solución")
        
        print()
        print("=" * 80)
        print("ANÁLISIS DE VELOCIDAD")
        print("=" * 80)
        print()
        print(f"Tiempo por iteración promedio: {t_aco/5:.1f}s")
        print(f"Tiempo por hormiga promedio: {t_aco/15:.1f}s")
        print()
        
        # Extrapolar a configuración completa
        estimado_15_100 = (t_aco / 15) * 1500  # 15 hormigas × 100 iter
        estimado_15_50 = (t_aco / 15) * 750   # 15 hormigas × 50 iter
        estimado_10_30 = (t_aco / 15) * 300   # 10 hormigas × 30 iter
        
        print("📊 ESTIMACIONES para configuraciones completas:")
        print()
        print(f"   10 hormigas × 30 iter:  ~{estimado_10_30/60:.1f} minutos")
        print(f"   15 hormigas × 50 iter:  ~{estimado_15_50/60:.1f} minutos")
        print(f"   15 hormigas × 100 iter: ~{estimado_15_100/60:.1f} minutos")
        print()
        
        if estimado_10_30 < 1800:  # Menos de 30 min
            print("✅ ¡Excelente! Tiempo estimado aceptable (<30 min con early stopping)")
        elif estimado_15_50 < 3600:  # Menos de 1 hora
            print("⚠️  Tiempo aceptable pero podría mejorarse")
        else:
            print("❌ Aún muy lento, necesita más optimización")
        
    finally:
        db.close()

if __name__ == "__main__":
    main()
