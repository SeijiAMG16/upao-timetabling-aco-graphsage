# 🎓 Sistema de Asignación de Horarios UPAO - ACO + GraphSAGE

Sistema inteligente de generación de horarios universitarios para la Escuela de Ingeniería de Sistemas e Informática de la (UPAO), utilizando **Ant Colony Optimization (ACO)** potenciado por redes neuronales en grafos (**GraphSAGE**). El sistema incluye validación estricta de las reglas pedagógicas institucionales, como la restricción T→P→L (Teoría → Práctica → Laboratorio).

## 📊 Estado Actual del Proyecto

### ✅ Implementado y Funcionando
- **Algoritmo ACO (Ant Colony Optimization)**: Motor principal de búsqueda metaheurística y optimización global.
- **GraphSAGE (Graph Neural Network)**: Integrado con el motor ACO para generar heurísticas inteligentes (embeddings) que previenen conflictos y dirigen la búsqueda de los agentes.
- **Validación Pedagógica (T→P→L)**: El algoritmo garantiza el correcto orden pedagógico de cada tipo de sesión.
- **Integración con Excel**: Importación automática de las proyecciones de cursos reales (`inputs/Libro1.xlsx`).
- **Sistema Híbrido**: El orquestador ejecuta ACO utilizando la inteligencia pre-entrenada de GraphSAGE o hace fallback de forma transparente si es necesario.

## 🚀 Uso Rápido

### 1. Generar un Nuevo Horario Completo
```bash
cd backend
# Ejecuta el algoritmo principal que integra ACO y GraphSAGE
python ejecutar_aco_completo.py
```

### 2. Entrenamiento del Modelo GraphSAGE
Si deseas entrenar a la red neuronal desde cero con el grafo más reciente:
```bash
cd backend
python entrenar_graphsage_estable.py
```

## 🏗️ Arquitectura del Sistema

**Backend:**
- **FastAPI** (Python 3.11+) para API REST.
- **PyTorch + PyTorch Geometric** para entrenamiento e inferencia de GraphSAGE.
- **SQLAlchemy + MySQL 8.0** para base de datos.
- Scripts de procesamiento de proyecciones y validación estricta.

**Frontend:**
- Aplicación planificada en **React 18 + Vite** para visualización intuitiva.

## 📋 Reglas Pedagógicas y Restricciones
- **T→P→L**: Las teorías se programan antes que las prácticas, y estas antes que los laboratorios.
- **Regla de laboratorios**: Secciones de ≤ 20 estudiantes → Piso F. Más de 20 estudiantes → Piso G.
- **Aulas**: Respeto de capacidad máxima y cero solapamientos físicos u horarios.
- **Profesores**: Respeto absoluto de su disponibilidad de horas contratadas.

## 📁 Estructura del Proyecto Destacada
```
upao-timetabling-aco-graphsage/
├── backend/
│   ├── app/
│   │   ├── algorithms/        # Implementaciones y variaciones del motor ACO
│   │   ├── aco_graphsage/     # Archivos core de la integración ACO + GNN 🧠
│   │   │   ├── aco_engine.py      # Combina la IA de grafos con la búsqueda por hormigas
│   │   │   ├── graph_builder.py   # Convierte cursos, aulas y profesores en grafos
│   │   │   └── ...
│   ├── ejecutar_aco_completo.py   # Punto de entrada principal
│   ├── entrenar_graphsage_estable.py # Entrenamiento manual
│   └── ...
├── frontend/                  # UI (React)
├── inputs/
│   └── Libro1.xlsx            # Data original con las proyecciones de secciones
└── README.md
```

## contacto
**Autor**: Seiji Amaya
**Universidad**: Universidad Privada Antenor Orrego (UPAO)
**Escuela**: Ingeniería de Sistemas e Informática