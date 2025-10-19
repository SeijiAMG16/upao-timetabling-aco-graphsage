"""
Test simple para verificar imports y estructura básica
"""

import sys
from pathlib import Path

# Agregar el directorio backend al path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


def test_imports():
    """Test: Verificar que todos los imports funcionan"""
    try:
        from app.aco_graphsage import (
            ACO_PARAMS,
            GRAPHSAGE_PARAMS,
            CONSTRAINT_WEIGHTS,
            TRAINING_PARAMS,
            LOCAL_SEARCH_PARAMS,
            TimetablePipeline,
            generate_timetable,
            train_model_from_scratch,
            TimetableGraphBuilder,
            ACOGraphSAGEModel,
            create_model_from_graph,
            ACOEngine,
            Solution,
            create_aco_engine,
            SolutionEvaluator,
            create_local_search,
        )
        print("✅ Todos los imports exitosos")
        assert True
    except ImportError as e:
        print(f"❌ Error en imports: {e}")
        assert False, f"Fallo al importar: {e}"


def test_config():
    """Test: Verificar configuración"""
    from app.aco_graphsage import ACO_PARAMS, GRAPHSAGE_PARAMS, CONSTRAINT_WEIGHTS
    
    assert ACO_PARAMS['n_hormigas'] == 50
    assert ACO_PARAMS['n_iteraciones'] == 100
    assert ACO_PARAMS['alpha'] == 1.0
    assert ACO_PARAMS['beta'] == 2.0
    
    assert GRAPHSAGE_PARAMS['hidden_dim'] == 128
    assert GRAPHSAGE_PARAMS['n_layers'] == 3
    
    assert CONSTRAINT_WEIGHTS['huecos_estudiantes'] == 10.0
    assert CONSTRAINT_WEIGHTS['cambio_edificio'] == 5.0
    assert CONSTRAINT_WEIGHTS['huecos_profesores'] == 2.0
    
    print("✅ Configuración correcta")


def test_constraints_structure():
    """Test: Verificar estructura de constraints"""
    from app.aco_graphsage.constraints import (
        TimeSlotInfo,
        ClassroomInfo,
        HardConstraintValidator,
        SoftConstraintEvaluator,
        Assignment,
    )
    
    # Verificar que las clases existen
    assert TimeSlotInfo is not None
    assert ClassroomInfo is not None
    assert HardConstraintValidator is not None
    assert SoftConstraintEvaluator is not None
    assert Assignment is not None
    
    print("✅ Estructura de constraints correcta")


def test_models_exist():
    """Test: Verificar que los modelos existen"""
    from app.models import (
        Base, Course, CourseSection, Professor, 
        Classroom, TimeSlot, ScheduleAssignment
    )
    
    assert Base is not None
    assert Course is not None
    assert CourseSection is not None
    assert Professor is not None
    assert Classroom is not None
    assert TimeSlot is not None
    assert ScheduleAssignment is not None
    
    print("✅ Modelos correctos")


if __name__ == "__main__":
    test_imports()
    test_config()
    test_constraints_structure()
    test_models_exist()
    print("\n🎉 Todos los tests básicos pasaron!")
