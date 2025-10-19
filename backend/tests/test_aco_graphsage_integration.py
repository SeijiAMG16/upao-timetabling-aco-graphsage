"""
Tests de Integración para ACO+GraphSAGE

Valida el pipeline completo del sistema.
"""

import sys
from pathlib import Path

# Agregar el directorio backend al path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import torch

from app.models import (
    Base,
    Course,
    CourseSection,
    Professor,
    Classroom,
    TimeSlot,
    ProfessorCourseAssignment,
)
from app.aco_graphsage import (
    TimetableGraphBuilder,
    create_model_from_graph,
    ACOEngine,
    create_aco_engine,
    SolutionEvaluator,
    TimetablePipeline,
)
from app.aco_graphsage.constraints import (
    TimeSlotInfo,
    ClassroomInfo,
    HardConstraintValidator,
    SoftConstraintEvaluator,
    Assignment,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def test_db():
    """Crea una BD de prueba en memoria"""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    # Poblar con datos de prueba
    _populate_test_data(db)
    
    yield db
    
    db.close()


def _populate_test_data(db):
    """Pobla la BD con datos mínimos de prueba"""
    
    # Crear curso
    course = Course(
        codigo="ISIA001",
        nombre="Algoritmia",
        ciclo="ISIA-V",
        grupos_teoria=2,
        grupos_practica=2,
        grupos_laboratorio=2,
        alumnos_teoria=30,
    )
    db.add(course)
    db.flush()
    
    # Crear secciones
    for i in range(1, 3):
        db.add(CourseSection(
            course_id=course.id,
            tipo='T',
            seccion=f'T{i}',
            league=i,
            alumnos_proyectados=30,
            activa=True,
        ))
        db.add(CourseSection(
            course_id=course.id,
            tipo='P',
            seccion=f'P{i}',
            league=i,
            alumnos_proyectados=30,
            activa=True,
        ))
        db.add(CourseSection(
            course_id=course.id,
            tipo='L',
            seccion=f'L{i}',
            league=i,
            alumnos_proyectados=30,
            activa=True,
        ))
    
    # Crear profesores y vincularlos con el curso
    profs = []
    for i in range(1, 3):
        prof = Professor(
            codigo=f"PROF{i}",
            nombre_completo=f"Profesor {i}",
        )
        db.add(prof)
        profs.append(prof)
    
    db.flush()
    
    # Vincular profesores con curso (relación many-to-many)
    course.professors = profs

    # Asignaciones explícitas por tipo/league para cubrir consultas directas
    for session_type in ("T", "P", "L"):
        db.add(ProfessorCourseAssignment(
            course_id=course.id,
            professor_id=profs[0].id,
            session_type=session_type,
            league=1,
        ))
    
    # Crear aulas
    for i in range(1, 5):
        db.add(Classroom(
            codigo=f"A{i}",
            edificio="A",
            piso="1",
            capacidad=40,
            tipo='teorica' if i <= 2 else 'laboratorio',
            active=True,
        ))
    
    # Crear franjas horarias
    for dia in range(1, 3):  # Solo lun-mar para simplicidad
        for orden in range(1, 5):  # 4 bloques
            hora_inicio = 7 + (orden - 1)
            db.add(TimeSlot(
                dia_semana=dia,
                hora_inicio=f"{hora_inicio:02d}:00",  # Formato HH:MM
                hora_fin=f"{hora_inicio:02d}:50",     # Formato HH:MM
                orden=orden,
                periodo="mañana",
            ))
    
    db.commit()


# ============================================================================
# TESTS DE CONSTRUCCIÓN DE GRAFO
# ============================================================================

def test_graph_construction(test_db):
    """Test: Construcción del grafo heterogéneo"""
    
    builder = TimetableGraphBuilder(test_db)
    graph = builder.build_graph()
    
    # Verificar que el grafo tiene todos los tipos de nodos
    assert 'section' in graph.x_dict
    assert 'professor' in graph.x_dict
    assert 'classroom' in graph.x_dict
    assert 'timeslot' in graph.x_dict
    assert 'curriculum' in graph.x_dict
    
    # Verificar dimensiones
    assert graph['section'].x.size(0) > 0
    assert graph['professor'].x.size(0) > 0
    
    print(f"✅ Grafo construido: {graph}")


def test_graph_features_shape(test_db):
    """Test: Dimensiones de features"""
    
    builder = TimetableGraphBuilder(test_db)
    graph = builder.build_graph()
    
    # Todas las features deben tener dimensión consistente
    for node_type, features in graph.x_dict.items():
        assert features.size(1) > 0, f"{node_type} features vacías"
        print(f"  {node_type}: {features.shape}")


# ============================================================================
# TESTS DE RESTRICCIONES
# ============================================================================

def test_hard_constraints_validator(test_db):
    """Test: Validación de restricciones duras"""
    
    # Crear estructuras de prueba
    timeslots = {
        1: TimeSlotInfo(1, 1, "07:00", "07:50", 1, "mañana"),
        2: TimeSlotInfo(2, 1, "07:55", "08:45", 2, "mañana"),
    }
    
    classrooms = {
        1: ClassroomInfo(1, "A1", 40, "teorica", "A", False),
    }
    
    validator = HardConstraintValidator(
        timeslots=timeslots,
        classrooms=classrooms,
        professor_restrictions={},
        sections_by_league={},
    )
    
    # Crear asignación de prueba
    assign1 = Assignment(
        section_id=1,
        professor_id=1,
        classroom_id=1,
        timeslot_ids=[1],
        course_code="ISIA001",
        session_type="T",
        league_id=1,
        ciclo="ISIA-V",
        alumnos_proyectados=30,
    )
    
    # Validar
    is_valid, msg = validator.validate_all(assign1, [])
    
    assert is_valid, f"Asignación válida marcada como inválida: {msg}"
    print(f"✅ Validación de restricciones duras OK")


def test_soft_constraints_evaluator(test_db):
    """Test: Cálculo de penalizaciones blandas"""
    
    timeslots = {
        1: TimeSlotInfo(1, 1, "07:00", "07:50", 1, "mañana"),
        2: TimeSlotInfo(2, 1, "10:00", "10:50", 5, "mañana"),  # Hueco
    }
    
    classrooms = {
        1: ClassroomInfo(1, "A1", 40, "teorica", "A", False),
    }
    
    evaluator = SoftConstraintEvaluator(
        timeslots=timeslots,
        classrooms=classrooms,
    )
    
    # Crear horario con huecos
    assignments = [
        Assignment(1, 1, 1, [1], "C1", "T", 1, "ISIA-V", 30),
        Assignment(2, 1, 1, [2], "C1", "T", 1, "ISIA-V", 30),
    ]
    
    total_cost, penalties = evaluator.calculate_total_penalty(assignments)
    
    assert total_cost > 0, "Debería haber penalización por hueco"
    assert 'huecos_estudiantes' in penalties
    
    print(f"✅ Evaluación de restricciones blandas OK")
    print(f"   Costo total: {total_cost:.2f}")
    print(f"   Penalizaciones: {penalties}")


# ============================================================================
# TESTS DE MODELO
# ============================================================================

def test_model_creation(test_db):
    """Test: Creación del modelo GraphSAGE"""
    
    builder = TimetableGraphBuilder(test_db)
    graph = builder.build_graph()
    
    model = create_model_from_graph(graph)
    
    assert model is not None
    assert hasattr(model, 'gnn')
    assert hasattr(model, 'scorer')
    
    print(f"✅ Modelo GraphSAGE creado: {model.hidden_dim} dims ocultas")


def test_model_forward_pass(test_db):
    """Test: Forward pass del modelo"""
    
    builder = TimetableGraphBuilder(test_db)
    graph = builder.build_graph()
    model = create_model_from_graph(graph)
    model.eval()  # Modo evaluación para BatchNorm
    
    # Preparar inputs
    section_idx = torch.tensor([0])
    professor_idx = torch.tensor([0])
    classroom_idx = torch.tensor([0])
    timeslot_idx = torch.tensor([0])
    
    # Forward pass
    with torch.no_grad():
        scores = model(graph, section_idx, professor_idx, classroom_idx, timeslot_idx)
    
    assert scores.size(0) == 1
    print(f"✅ Forward pass OK: score={scores.item():.4f}")


# ============================================================================
# TESTS DE PIPELINE COMPLETO
# ============================================================================

@pytest.mark.slow
def test_full_pipeline_construction(test_db):
    """Test: Pipeline completo de construcción"""
    
    pipeline = TimetablePipeline(db_session=test_db)
    pipeline.prepare()
    
    # Generar horario (parámetros mínimos para velocidad)
    solution, metrics = pipeline.generate_schedule(
        aco_params={'n_hormigas': 5, 'n_iteraciones': 10},
        local_search_params={'max_iterations': 50},
        save_to_db=False,
    )
    
    # El pipeline puede no encontrar solución con datos pequeños de prueba
    # Lo importante es que no crashee
    print(f"✅ Pipeline completo OK (sin crash)")
    if solution is not None:
        print(f"   Solución encontrada!")
        print(f"   Asignaciones: {len(solution.assignments)}")
        print(f"   Costo: {solution.total_cost:.2f}")
        print(f"   Métricas: {metrics}")
    else:
        print(f"   ⚠️  No se encontró solución válida (esperado con datos pequeños)")


# ============================================================================
# TESTS DE INTEGRACIÓN
# ============================================================================

def test_integration_graph_to_model_to_aco(test_db):
    """Test: Integración completa grafo -> modelo -> ACO"""
    
    # 1. Construir grafo
    builder = TimetableGraphBuilder(test_db)
    graph = builder.build_graph()
    
    # 2. Crear modelo
    model = create_model_from_graph(graph)
    
    # 3. Crear motor ACO (parámetros mínimos)
    aco_engine = create_aco_engine(
        graph=graph,
        model=model,
        graph_builder=builder,
        db_session=test_db,
        params={'n_hormigas': 3, 'n_iteraciones': 5},
    )
    
    # 4. Optimizar (puede no encontrar solución con datos pequeños)
    solution = aco_engine.optimize()
    
    # Lo importante es que el flujo completo funcione sin errores
    print(f"✅ Integración completa OK (grafo -> modelo -> ACO)")
    if solution is not None:
        print(f"   Solución encontrada!")
        print(f"   Solución válida: {solution.is_valid}")
        print(f"   Costo: {solution.total_cost:.2f}")
    else:
        print(f"   ⚠️  No se encontró solución (esperado con datos pequeños)")


# ============================================================================
# EJECUTAR TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
