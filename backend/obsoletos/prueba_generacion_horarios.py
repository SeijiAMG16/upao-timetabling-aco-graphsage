"""
Prueba de Generacion de Horarios con ACO+GraphSAGE
Script sin emojis para compatibilidad con Windows
"""
import sys
import os
from pathlib import Path
import time
import json

# Configurar encoding UTF-8
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Agregar backend al path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.database import SessionLocal
from app.aco_graphsage.pipeline import TimetablePipeline

def prueba_generacion():
    """Prueba de generacion de horarios con el sistema hibrido"""
    
    print("="*80)
    print("PRUEBA DE GENERACION DE HORARIOS - ACO+GraphSAGE")
    print("="*80)
    print()
    
    # Conectar a la base de datos
    db = SessionLocal()
    
    try:
        # Verificar datos disponibles
        from app.models import Course, CourseSection, Professor, Classroom, TimeSlot
        
        n_courses = db.query(Course).count()
        n_sections = db.query(CourseSection).count()
        n_professors = db.query(Professor).count()
        n_classrooms = db.query(Classroom).count()
        n_timeslots = db.query(TimeSlot).count()
        
        print("DATOS DISPONIBLES:")
        print(f"  - Cursos: {n_courses}")
        print(f"  - Secciones: {n_sections}")
        print(f"  - Profesores: {n_professors}")
        print(f"  - Aulas: {n_classrooms}")
        print(f"  - Franjas horarias: {n_timeslots}")
        print()
        
        if n_sections == 0:
            print("[ERROR] No hay secciones en la base de datos")
            return
        
        # Inicializar el pipeline (silenciosamente)
        print("Inicializando pipeline...")
        old_stdout = sys.stdout
        sys.stdout = open(os.devnull, 'w')
        
        pipeline = TimetablePipeline(db_session=db)
        pipeline.prepare()
        
        sys.stdout = old_stdout
        print("[OK] Pipeline inicializado")
        print()
        
        # PRUEBA 1: Generacion rapida (parametros minimos)
        print("="*80)
        print("PRUEBA 1: GENERACION RAPIDA")
        print("="*80)
        print("Parametros: 5 hormigas, 10 iteraciones")
        print()
        
        start_time = time.time()
        
        solution1, metrics1 = pipeline.generate_schedule(
            aco_params={
                'n_hormigas': 5,
                'n_iteraciones': 10,
            },
            local_search_params={
                'algorithm': 'simulated_annealing',
                'max_iterations': 50,
            },
            save_to_db=False,
        )
        
        elapsed1 = time.time() - start_time
        
        print(f"Tiempo: {elapsed1:.2f} segundos")
        
        if solution1:
            print(f"[OK] Solucion encontrada!")
            print(f"  - Asignaciones: {len(solution1.assignments)}")
            print(f"  - Costo total: {solution1.total_cost:.2f}")
            print(f"  - Valida: {'SI' if solution1.is_valid else 'NO'}")
            print(f"  - Violaciones duras: {solution1.hard_violations}")
        else:
            print("[ADVERTENCIA] No se encontro solucion")
        
        print()
        
        # PRUEBA 2: Generacion normal (parametros moderados)
        print("="*80)
        print("PRUEBA 2: GENERACION NORMAL")
        print("="*80)
        print("Parametros: 10 hormigas, 30 iteraciones")
        print()
        
        start_time = time.time()
        
        solution2, metrics2 = pipeline.generate_schedule(
            aco_params={
                'n_hormigas': 10,
                'n_iteraciones': 30,
            },
            local_search_params={
                'algorithm': 'simulated_annealing',
                'max_iterations': 100,
            },
            save_to_db=False,
        )
        
        elapsed2 = time.time() - start_time
        
        print(f"Tiempo: {elapsed2:.2f} segundos")
        
        if solution2:
            print(f"[OK] Solucion encontrada!")
            print(f"  - Asignaciones: {len(solution2.assignments)}")
            print(f"  - Costo total: {solution2.total_cost:.2f}")
            print(f"  - Valida: {'SI' if solution2.is_valid else 'NO'}")
            print(f"  - Violaciones duras: {solution2.hard_violations}")
            
            if metrics2:
                print()
                print("Metricas:")
                for key, value in metrics2.items():
                    if isinstance(value, (int, float)):
                        if isinstance(value, float):
                            print(f"  - {key}: {value:.2f}")
                        else:
                            print(f"  - {key}: {value}")
        else:
            print("[ADVERTENCIA] No se encontro solucion")
        
        print()
        
        # PRUEBA 3: Generacion con calidad (parametros altos)
        print("="*80)
        print("PRUEBA 3: GENERACION CON CALIDAD")
        print("="*80)
        print("Parametros: 20 hormigas, 50 iteraciones")
        print("(Esto puede tomar varios minutos...)")
        print()
        
        start_time = time.time()
        
        solution3, metrics3 = pipeline.generate_schedule(
            aco_params={
                'n_hormigas': 20,
                'n_iteraciones': 50,
            },
            local_search_params={
                'algorithm': 'simulated_annealing',
                'max_iterations': 200,
            },
            save_to_db=True,  # Guardar esta solucion
        )
        
        elapsed3 = time.time() - start_time
        
        print(f"Tiempo: {elapsed3:.2f} segundos ({elapsed3/60:.1f} minutos)")
        
        if solution3:
            print(f"[OK] Solucion encontrada y GUARDADA en la BD!")
            print(f"  - Asignaciones: {len(solution3.assignments)}")
            print(f"  - Costo total: {solution3.total_cost:.2f}")
            print(f"  - Valida: {'SI' if solution3.is_valid else 'NO'}")
            print(f"  - Violaciones duras: {solution3.hard_violations}")
            
            # Mostrar penalizaciones suaves
            if hasattr(solution3, 'soft_penalties') and solution3.soft_penalties:
                print()
                print("Penalizaciones suaves:")
                total_soft = 0
                for key, value in solution3.soft_penalties.items():
                    if value > 0:
                        print(f"  - {key}: {value:.2f}")
                        total_soft += value
                print(f"  TOTAL SOFT: {total_soft:.2f}")
            
            if metrics3:
                print()
                print("Metricas finales:")
                for key, value in metrics3.items():
                    if isinstance(value, (int, float)):
                        if isinstance(value, float):
                            print(f"  - {key}: {value:.2f}")
                        else:
                            print(f"  - {key}: {value}")
        else:
            print("[ADVERTENCIA] No se encontro solucion")
        
        print()
        print("="*80)
        print("RESUMEN DE PRUEBAS")
        print("="*80)
        print()
        print(f"Prueba 1 (Rapida):  {elapsed1:.2f}s - {'OK' if solution1 else 'SIN SOLUCION'}")
        print(f"Prueba 2 (Normal):  {elapsed2:.2f}s - {'OK' if solution2 else 'SIN SOLUCION'}")
        print(f"Prueba 3 (Calidad): {elapsed3:.2f}s - {'OK' if solution3 else 'SIN SOLUCION'}")
        print()
        
        # Comparar soluciones si existen
        if solution1 and solution2 and solution3:
            print("COMPARACION DE CALIDAD:")
            print(f"  Prueba 1: costo={solution1.total_cost:.2f}, asig={len(solution1.assignments)}")
            print(f"  Prueba 2: costo={solution2.total_cost:.2f}, asig={len(solution2.assignments)}")
            print(f"  Prueba 3: costo={solution3.total_cost:.2f}, asig={len(solution3.assignments)}")
            print()
            
            best = min([solution1, solution2, solution3], key=lambda s: s.total_cost)
            print(f"  MEJOR SOLUCION: Prueba {[solution1, solution2, solution3].index(best) + 1}")
        
        print()
        print("="*80)
        print("[OK] PRUEBAS COMPLETADAS EXITOSAMENTE")
        print("="*80)
        
    except KeyboardInterrupt:
        print()
        print("[INTERRUMPIDO] Prueba cancelada por el usuario")
        
    except Exception as e:
        print()
        print("="*80)
        print("[ERROR] Error durante la ejecucion")
        print("="*80)
        print()
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        db.close()

if __name__ == "__main__":
    prueba_generacion()
