# Guía Completa: Sistema ACO+GraphSAGE para Generación de Horarios UPAO

## 📋 Índice

1. [Resumen del Sistema](#resumen)
2. [Arquitectura](#arquitectura)
3. [Instalación](#instalación)
4. [Uso Básico](#uso-básico)
5. [API Endpoints](#api-endpoints)
6. [Configuración Avanzada](#configuración)
7. [Exportación de Resultados](#exportación)
8. [Troubleshooting](#troubleshooting)

---

## 🎯 Resumen del Sistema

El sistema implementa un framework híbrido para generación automática de horarios académicos basado en:

- **Ant Colony Optimization (ACO)** con Max-Min Ant System (MMAS)
- **GraphSAGE** (Graph Neural Network) como heurística aprendida
- **Reinforcement Learning** (REINFORCE) para entrenamiento offline

### Características Principales

✅ **Restricciones Duras** (inviolables):
- No solapamiento de profesores/aulas
- Disponibilidad de profesores
- Conflictos curriculares (mismo ciclo)
- Coherencia de liga (T1, P1, L1 no se solapan)
- Capacidad y tipo de aula
- Duración de sesiones (bloques consecutivos)

✅ **Restricciones Blandas** (penalizaciones ponderadas):
- Minimizar huecos en horarios de estudiantes (peso=10)
- Minimizar cambios de edificio (peso=5)
- Minimizar huecos de profesores (peso=2)
- Preferencias de franjas horarias (peso=1)

---

## 🏗️ Arquitectura

```
backend/app/aco_graphsage/
├── config.py              # Parámetros del sistema
├── graph_builder.py       # Construcción de grafo heterogéneo
├── graphsage_model.py     # Red neuronal GNN
├── constraints.py         # Validadores de restricciones
├── aco_engine.py          # Motor ACO con integración neural
├── local_search.py        # Refinamiento (SA/Hill Climbing)
├── trainer.py             # Entrenamiento REINFORCE
├── evaluator.py           # Métricas de calidad
├── pipeline.py            # Orquestador principal
└── __init__.py            # Exports

backend/app/api/endpoints/
└── algorithm.py           # Endpoints FastAPI

backend/
├── export_schedules_excel.py  # Exportación a Excel
└── tests/
    └── test_aco_graphsage_integration.py  # Tests
```

### Pipeline de 3 Fases

1. **Neural-Augmented Construction**: ACO + GraphSAGE generan solución inicial
2. **Local Search**: Simulated Annealing refina la solución
3. **Offline Training** (opcional): REINFORCE entrena el modelo GraphSAGE

---

## 📦 Instalación

### Requisitos

```bash
# Python 3.13+
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install torch-geometric
pip install torch-scatter torch-sparse -f https://data.pyg.org/whl/torch-2.0.0+cu118.html

# Dependencias adicionales
pip install fastapi uvicorn sqlalchemy pymysql pandas openpyxl pytest
```

### Configurar Base de Datos

Asegúrate de que la BD `upao_timetabling` esté poblada con:
- Cursos (`courses`)
- Secciones (`course_sections`)
- Profesores (`professors`)
- Aulas (`classrooms`)
- Franjas horarias (`time_slots`)
- Asignaciones profesor-curso (`professor_course_assignments`)

---

## 🚀 Uso Básico

### Opción 1: Desde Python

```python
from app.database import SessionLocal
from app.aco_graphsage import generate_timetable

# Crear sesión de BD
db = SessionLocal()

try:
    # Generar horario
    solution, metrics = generate_timetable(
        db_session=db,
        aco_iterations=100,  # Número de iteraciones ACO
        save_to_db=True,     # Guardar en schedule_assignments
    )
    
    print(f"✅ Horario generado!")
    print(f"   Costo total: {metrics['total_cost']:.2f}")
    print(f"   Conflictos: {metrics['conflictos_profesor'] + metrics['conflictos_aula']}")
    print(f"   Utilización aulas: {metrics['utilizacion_aulas']:.1f}%")
    
finally:
    db.close()
```

### Opción 2: Desde API (Recomendado)

```bash
# Iniciar servidor FastAPI
cd backend
uvicorn app.main:app --reload --port 8000

# En otra terminal, ejecutar algoritmo
curl -X POST "http://localhost:8000/api/algorithm/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "aco_iterations": 100,
    "n_hormigas": 50,
    "use_local_search": true,
    "save_to_db": true
  }'

# Response:
# {
#   "execution_id": 1,
#   "status": "running",
#   "message": "Ejecución iniciada..."
# }

# Monitorear progreso
curl "http://localhost:8000/api/algorithm/status/1"
```

### Opción 3: Pipeline Completo con Entrenamiento

```python
from app.aco_graphsage import TimetablePipeline

pipeline = TimetablePipeline(db_session=db)

# 3 fases completas
solution, metrics, trained_model = pipeline.run_full_pipeline(
    aco_params={'n_iteraciones': 100, 'n_hormigas': 50},
    training_episodes=500,  # Entrenar modelo
    save_to_db=True,
)
```

---

## 🌐 API Endpoints

### POST `/api/algorithm/execute`

Ejecuta el algoritmo en background.

**Request Body:**
```json
{
  "aco_iterations": 100,
  "n_hormigas": 50,
  "use_local_search": true,
  "local_search_algorithm": "simulated_annealing",
  "use_pretrained_model": false,
  "model_path": null,
  "save_to_db": true
}
```

**Response:**
```json
{
  "execution_id": 1,
  "status": "running",
  "message": "Ejecución iniciada. Use /status/{id} para monitorear.",
  "started_at": "2025-01-13T10:30:00"
}
```

### GET `/api/algorithm/status/{execution_id}`

Obtiene el estado de una ejecución.

**Response:**
```json
{
  "execution_id": 1,
  "status": "completed",
  "progress": 1.0,
  "current_phase": "completed",
  "metrics": {
    "total_cost": 45.2,
    "conflictos_profesor": 0,
    "conflictos_aula": 0,
    "utilizacion_aulas": 68.5,
    "tiempo_ejecucion": 125.3
  },
  "error": null
}
```

### GET `/api/algorithm/executions`

Lista ejecuciones recientes.

**Query Params:**
- `limit`: Número de resultados (default=10)
- `offset`: Offset para paginación (default=0)

### POST `/api/algorithm/train`

Entrena un modelo GraphSAGE.

**Request Body:**
```json
{
  "n_episodes": 500,
  "save_dir": "models/checkpoints"
}
```

### GET `/api/algorithm/parameters`

Obtiene parámetros por defecto del sistema.

---

## ⚙️ Configuración Avanzada

### Modificar Parámetros ACO

```python
from app.aco_graphsage import ACO_PARAMS

custom_params = ACO_PARAMS.copy()
custom_params['n_hormigas'] = 100      # Más hormigas = mejor exploración
custom_params['n_iteraciones'] = 200   # Más iteraciones = mejor convergencia
custom_params['alpha'] = 1.5           # Mayor influencia de feromona
custom_params['beta'] = 2.5            # Mayor influencia de heurística neural
custom_params['rho'] = 0.15            # Mayor evaporación

solution, metrics = generate_timetable(db, aco_params=custom_params)
```

### Modificar Pesos de Restricciones Blandas

Editar `backend/app/aco_graphsage/config.py`:

```python
CONSTRAINT_WEIGHTS = {
    "huecos_estudiantes": 15.0,  # Aumentar prioridad
    "cambio_edificio": 8.0,
    "huecos_profesores": 3.0,
    "preferencia_franja": 0.5,
}
```

### Cambiar Algoritmo de Búsqueda Local

```python
local_search_params = {
    'algorithm': 'hill_climbing',  # o 'simulated_annealing'
    'max_iterations': 2000,
    'initial_temperature': 150.0,  # Solo para SA
    'cooling_rate': 0.98,
}

solution, metrics = pipeline.generate_schedule(
    local_search_params=local_search_params
)
```

---

## 📊 Exportación de Resultados

### Desde Python

```python
from export_schedules_excel import export_all_formats

# Exportar todos los formatos
export_all_formats(
    db=db,
    execution_id=1,
    output_dir="resultados/horarios"
)
```

Esto genera:
- `horarios_profesores_TIMESTAMP.xlsx` - Una hoja por profesor
- `horarios_aulas_TIMESTAMP.xlsx` - Una hoja por aula
- `horarios_ciclos_TIMESTAMP.xlsx` - Una hoja por ciclo
- `resumen_ejecucion_TIMESTAMP.xlsx` - Métricas y todas las asignaciones

### Desde CLI

```bash
cd backend
python export_schedules_excel.py 1  # execution_id
```

### Formato del Excel

Cada hoja contiene:
- **Filas**: Franjas horarias (07:00-07:50, etc.)
- **Columnas**: Días de la semana (Lun-Sáb)
- **Celdas**: Curso, Sección, Aula
- **Colores**: Azul=Teoría, Morado=Práctica, Verde=Laboratorio

---

## 🐛 Troubleshooting

### Error: "No module named 'torch_geometric'"

```bash
pip install torch-geometric
pip install torch-scatter torch-sparse -f https://data.pyg.org/whl/torch-2.0.0+cu118.html
```

### Error: "No se encontraron soluciones válidas"

**Causas posibles:**
1. Restricciones demasiado estrictas
2. Insuficientes aulas/franjas horarias
3. Conflictos en `professor_course_assignments`

**Soluciones:**
- Aumentar número de hormigas: `n_hormigas: 100`
- Aumentar iteraciones: `n_iteraciones: 200`
- Revisar disponibilidad de profesores en `professor_restrictions`
- Verificar que hay suficientes aulas de cada tipo

### Rendimiento Lento

**Optimizaciones:**
1. Reducir iteraciones iniciales: `n_iteraciones: 50`
2. Reducir hormigas: `n_hormigas: 30`
3. Limitar búsqueda local: `max_iterations: 500`
4. Usar modelo preentrenado: `use_pretrained_model: true`

### Conflictos en Solución Final

Si `conflictos_profesor > 0` o `conflictos_aula > 0`:
- Verificar lógica en `constraints.py`
- Aumentar penalizaciones en restricciones blandas
- Ejecutar con más iteraciones de búsqueda local

---

## 📈 Métricas y Evaluación

### Métricas Clave

| Métrica | Descripción | Objetivo |
|---------|-------------|----------|
| `total_cost` | Suma ponderada de todas las penalizaciones | Minimizar |
| `conflictos_profesor` | Solapamientos de profesor | 0 |
| `conflictos_aula` | Solapamientos de aula | 0 |
| `conflictos_curriculo` | Solapamientos de ciclo | 0 |
| `utilizacion_aulas` | % de ocupación de aulas | 60-80% |
| `huecos_estudiantes` | Espacios libres en horarios | Minimizar |
| `tiempo_ejecucion` | Tiempo total (segundos) | <300s |

### Interpretación

**Solución Excelente:**
- Costo total < 50
- Conflictos = 0
- Huecos estudiantes < 10
- Utilización aulas > 60%

**Solución Aceptable:**
- Costo total < 100
- Conflictos = 0
- Huecos estudiantes < 20

**Requiere Ajustes:**
- Costo total > 150
- Conflictos > 0
- Utilización < 40%

---

## 🔬 Experimentación

### Comparar Diferentes Configuraciones

```python
configs = [
    {'n_hormigas': 30, 'n_iteraciones': 50},
    {'n_hormigas': 50, 'n_iteraciones': 100},
    {'n_hormigas': 100, 'n_iteraciones': 200},
]

results = []
for config in configs:
    solution, metrics = generate_timetable(db, aco_params=config)
    results.append({
        'config': config,
        'cost': metrics['total_cost'],
        'time': metrics['tiempo_ejecucion'],
    })

# Analizar mejores parámetros
best = min(results, key=lambda x: x['cost'])
print(f"Mejor configuración: {best['config']}")
```

---

## 📚 Referencias

**Paper Base:**
- DeepACO: Neural-enhanced Ant Colony Optimization ([arXiv:2309.14032](https://arxiv.org/abs/2309.14032))

**Documentación Adicional:**
- [PyTorch Geometric](https://pytorch-geometric.readthedocs.io/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [REGLAS_NEGOCIO_UPAO.md](./REGLAS_NEGOCIO_UPAO.md)

---

## 📞 Soporte

Para problemas o dudas:
1. Revisar logs en `backend/logs/`
2. Consultar tabla `algorithm_executions` en BD
3. Ejecutar tests: `pytest tests/test_aco_graphsage_integration.py -v`

---

**Última actualización**: 13 de Enero de 2025  
**Versión**: 1.0.0  
**Estado**: ✅ Sistema Completo Funcional
