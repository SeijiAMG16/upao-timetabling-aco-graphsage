# Agent Guide - UPAO Timetabling System

## Architecture

**Dual-stack monorepo**: Backend (FastAPI/Python) + Frontend (React/Vite) + Docker orchestration.

- `backend/` - FastAPI app with ACO+GraphSAGE algorithms
- `frontend/` - React 18 + Vite + Material-UI
- `inputs/` - Required Excel files (`Libro1.xlsx` for course projections, `Horario_Docentes(2025-20).xlsx`)
- `obsoletos/` - 100+ legacy/experimental scripts; do not modify unless explicitly asked
- `backend/app/aco_graphsage/` - Core scheduling engine (GraphSAGE model, ACO engine, constraints)
- `backend/app/algorithms/` - Algorithm implementations (aco.py, aco_enhanced.py, aco_optimized.py)

## Critical Setup

**Database**: MySQL 8.0 ONLY. SQLite is explicitly blocked (see `backend/app/database.py:29`). Default local credentials: `root:sistemas@localhost:3306/upao_timetabling`.

**Environment variables**:
- `DATABASE_URL` - MySQL connection string (pymysql format)
- See `backend/.env.example` for template
- Frontend requires `REACT_APP_API_URL` (default: `http://localhost:8000`)

**Python**: 3.11.0 (see `backend/runtime.txt`)

## Commands

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload      # Dev server on :8000
python ejecutar_aco_completo.py    # Run ACO algorithm (has fallback if PyTorch missing)
```

**Main script**: `ejecutar_aco_completo.py` - Runs ACO+GraphSAGE or falls back to basic ACO if PyTorch unavailable.

### Frontend

```bash
cd frontend
npm install
npm run dev          # Vite dev server on :3000
npm run build        # Production build
```

### Docker

```bash
docker-compose up -d                    # Full stack (MySQL, Redis, backend, frontend, Celery)
docker-compose --profile monitoring up  # Add Flower, Prometheus, Grafana
docker-compose --profile production up  # Add Nginx
```

**Services**: MySQL (:3306), Redis (:6379), Backend (:8000), Frontend (:3000), Flower (:5555), Grafana (:3001).

## Domain Knowledge

**Problem**: Assign 298 course sections to time slots, classrooms, and professors while satisfying hard/soft constraints.

**Key constraints**:
- **T→P→L Rule**: Teoría sessions MUST be scheduled before Práctica, which MUST be before Laboratorio (pedagogical requirement)
- **Lab floor rule**: ≤20 students → Floor F, >20 students → Floor G
- **Prime hours**: Teorías prefer Mon-Thu 8:00-12:00; odd cycles (1,3,5,7,9) prefer morning slots
- Hard: No professor/classroom conflicts, capacity limits, professor availability
- Soft: Minimize gaps in professor schedules, balanced distribution

**Data**: 75 courses, 106 theory groups, 85 practice groups, 111 lab groups, 10,746 students, 48 classrooms, 96 time slots (16/day × 6 days).

**Metrics** (Experiment 36): 100% assignments, 73.8% T→P→L compliance, 0 conflicts, 98.4% projection match.

## Testing

```bash
cd backend
pytest tests/                # Run all tests
pytest tests/test_aco_graphsage_integration.py  # Integration test
```

**No pytest.ini**: Tests auto-discover from `tests/` directory.

## GraphSAGE Notes

**Status**: Planned for Phase 2, not fully integrated. Backend has PyTorch dependency but ACO runs without it (fallback mode in `ejecutar_aco_completo.py:46`).

**Module location**: `backend/app/aco_graphsage/` (graph_builder, graphsage_model, aco_engine, constraints).

## Common Gotchas

1. **Database required**: All scripts expect MySQL; no mock/in-memory DB for most operations.
2. **Libro1.xlsx is critical**: Main input file at `inputs/Libro1.xlsx` contains course projections; many scripts will fail without it.
3. **SSL handling**: Database URL auto-strips `ssl-mode=` params for pymysql compatibility (see `database.py:21-26`).
4. **Obsoletos folder**: Contains 100+ legacy scripts; avoid unless user explicitly references them.
5. **ACO parameters**: Default is 50 iterations, 15 ants, β=2.0; best results in README from Exp 12 (β=2.0) and Exp 10 (β=5.0 with GraphSAGE).
6. **Result storage**: Experiments saved to MySQL `experiments` table AND JSON files (`experimento_proy_*.json`).

## API Structure

FastAPI app at `backend/app/main.py`:
- `/docs` - Swagger UI
- `/api/algorithms/aco/run` - Execute ACO
- `/api/courses`, `/api/classrooms`, `/api/time-slots` - Resource endpoints
- `/api/excel/upload` - Upload projections
- Routers in `backend/app/api/endpoints/`

CORS: Allows all origins in dev (see `main.py:42`).

## Deployment

- **Backend**: Heroku via Procfile (`uvicorn app.main:app --host 0.0.0.0 --port $PORT`)
- **Frontend**: Heroku buildpack for static sites or serve via Vite preview
- **Docker**: Multi-profile setup for dev/prod/monitoring (see `docker-compose.yml`)

## Key Files to Read First

When investigating issues:
1. `README.md` - Comprehensive overview, metrics, usage examples
2. `backend/ejecutar_aco_completo.py` - Main algorithm entrypoint
3. `backend/app/main.py` - FastAPI app setup
4. `backend/app/database.py` - DB connection logic
5. `docker-compose.yml` - Full stack orchestration
6. `backend/app/algorithms/aco.py` - Core ACO implementation
