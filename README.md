# 🎓 Sistema de Asignación de Horarios UPAO - ACO# 🎓 UPAO Timetabling: ACO + GraphSAGE# UPAO Timetabling System - ACO & GraphSAGE



Sistema inteligente de generación de horarios universitarios usando **Ant Colony Optimization (ACO)** con validación pedagógica T→P→L (Teoría → Práctica → Laboratorio).



## 📊 Estado Actual del Proyecto**Sistema de Optimización de Horarios Académicos con Algoritmos Híbridos**Sistema de generación automática de horarios para la Escuela de Ingeniería de Sistemas e Informática de la Universidad Privada Antenor Orrego (UPAO), utilizando algoritmos de Optimización por Colonias de Hormigas (ACO) y GraphSAGE.



### ✅ Implementado y Funcionando



- **ACO Simple con Context-Aware Scheduling**: 73.8% cumplimiento T→P→LUniversidad Privada Antenor Orrego - Tesis de Ingeniería de Sistemas## 🎯 Descripción del Proyecto

- **100% de asignaciones exitosas**: 298/298 secciones asignadas

- **0 conflictos**: Sin conflictos de aula ni profesor

- **98.4% cumplimiento de proyecciones**: Respeta casi todas las proyecciones de Libro1.xlsx

---Este sistema reemplaza el proceso manual de asignación de horarios académicos con un enfoque automatizado inteligente que considera múltiples restricciones y optimiza la distribución de recursos educativos.

### ❌ No Implementado (Futuro)



- **GraphSAGE**: Graph Neural Network para optimización (planeado, no implementado)

## 📋 Descripción### Características Principales

## 🚀 Uso Rápido



### 1. Generar un Nuevo Horario

Sistema híbrido de optimización de horarios académicos que combina:- **Algoritmo ACO (Ant Colony Optimization)**: Optimización global de horarios

```bash

cd backend- **ACO (Ant Colony Optimization)** para búsqueda metaheurística- **GraphSAGE**: Predicción de conflictos y recomendaciones inteligentes

python ejecutar_aco_con_proyecciones.py

```- **GraphSAGE (Graph Neural Network)** para heurística inteligente basada en embeddings- **Procesamiento de Excel**: Importación automática de proyecciones de cursos



**Salida esperada:**- **Reglas Pedagógicas Institucionales** para calidad académica- **Validación en tiempo real**: Detección inmediata de conflictos

```

✅ RESULTADO: 298/298 asignadas (100.0%)- **Interface web moderna**: Frontend React con drag & drop

📊 Validación T→P→L: 45/61 cursos válidos (73.8%)

📊 Validación Proyecciones: 60/61 cursos (98.4%)### 🎯 Objetivos- **API REST completa**: Backend FastAPI con documentación automática

📊 Conflictos: 0 aula, 0 profesor

💾 Experimento guardado con ID: XX

```

1. Generar horarios académicos óptimos minimizando conflictos## 🏗️ Arquitectura del Sistema

### 2. Visualizar el Horario Generado

2. Cumplir reglas pedagógicas (T→P→L, horarios prime, distribución temporal)

```bash

python visualizar_horario_generado.py3. Validar resultados contra horarios oficiales BANNER### Tecnologías Utilizadas

```

4. Comparar desempeño ACO vs. ACO+GraphSAGE

**Opciones disponibles:**

1. Horario completo (por día y hora)**Backend:**

2. Horario por curso (verificar T→P→L)

3. Validación T→P→L detallada---- FastAPI (Python 3.11+)

4. Estadísticas generales

5. Todo (todas las vistas)- SQLAlchemy + MySQL



También puedes especificar un experimento específico:## 🚀 Instalación Rápida- PyTorch Geometric (GraphSAGE)

```bash

python visualizar_horario_generado.py 36- NumPy/Pandas (Procesamiento de datos)

```

```bash- Celery + Redis (Tareas asíncronas)

### 3. Comparar Experimentos

# 1. Clonar repositorio

```bash

python comparar_experimentos_real.pygit clone https://github.com/SeijiAMG16/upao-timetabling-aco-graphsage.git**Frontend:**

```

cd upao-timetabling-aco-graphsage/backend- React 18 + TypeScript

Muestra la evolución de todos los experimentos realizados.

- Vite (Build tool)

## 📁 Estructura del Proyecto

# 2. Instalar dependencias- TailwindCSS

```

backend/pip install -r requirements.txt- React Query (State management)

├── ejecutar_aco_con_proyecciones.py  # 🎯 Script principal - Genera horarios

├── visualizar_horario_generado.py    # 🎨 Visualizador de horarios- React DnD (Drag & drop)

├── aco_simple.py                      # 🐜 Algoritmo ACO con context-aware

├── proyecciones_loader.py             # 📋 Carga datos de Libro1.xlsx# 3. Configurar MySQL (o usar Docker)

├── reglas_pedagogicas_v2.py           # ✓ Validación T→P→L

├── comparar_experimentos_real.py      # 📊 Análisis de evolucióndocker-compose up -d**DevOps:**

├── obsoletos/                         # 🗑️ Archivos antiguos/experimentales

└── experimento_proy_XX.json          # 💾 Resultados de experimentos- Docker + Docker Compose



inputs/# 4. Cargar datos- GitHub Actions (CI/CD)

└── Libro1.xlsx                        # 📊 Proyecciones de cursos (REQUERIDO)

```python ingest_data_to_db.py- MySQL 8.0



## 🔧 Configuración



### Base de Datos# 5. Ejecutar experimento## 📊 Contexto UPAO



Editar en `ejecutar_aco_con_proyecciones.py`:python ejecutar_aco_experimento.py



```python```### Restricciones del Sistema

DB_CONFIG = {

    'host': 'localhost',

    'user': 'root',

    'password': 'sistemas',  # ← Cambiar tu password---**Hard Constraints (Obligatorias):**

    'database': 'upao_timetabling'

}- No solapamiento de profesores en misma franja

```

## 📊 Resultados Principales- No solapamiento de aulas en misma franja  

### Parámetros ACO

- Respeto a capacidad máxima de aulas

Editar línea ~678 en `ejecutar_aco_con_proyecciones.py`:

### **🏆 Mejor Configuración (Experimento 12)**- Disponibilidad horaria de docentes

```python

num_hormigas=20,      # Número de soluciones por iteración```- **Regla de laboratorios**: ≤20 alumnos → Piso F, >20 alumnos → Piso G

max_iteraciones=15    # Número de iteraciones

```β = 2.0, Iteraciones = 50, Hormigas = 15



**Más hormigas/iteraciones** = Más tiempo pero mejores resultados✅ Fitness: 27,116**Soft Constraints (Preferibles):**



## 📊 Métricas y Resultados✅ Conflictos aula: 0 (PERFECTO)- Ciclos impares (1,3,5,7,9) → Horarios matutinos



### Evolución del Algoritmo✅ T→P→L correcto: 100% (28/28 cursos)- Ciclos pares (2,4,6,8) → Horarios vespertinos/nocturnos



| Exp | T→P→L % | Mejora | Técnica |✅ Horarios prime: 100%- Mínimo 2, máximo 3 franjas por ciclo

|-----|---------|--------|---------|

| 27  | 8.6%    | baseline | ACO básico |```- Minimizar huecos en horarios docentes

| 32  | 34.4%   | +300%  | Ordenamiento por CURSO |

| **34-36** | **73.8%** | **+758%** | **Context-aware scheduling** ✓ |- Distribución equilibrada de carga



### Validación T→P→L### **🥈 Mejor con GraphSAGE (Experimento 10)**



**Regla pedagógica:** Las teorías deben programarse ANTES que las prácticas, y las prácticas ANTES que los laboratorios.```### Infraestructura UPAO



**Ejemplo válido:**β = 5.0, Iteraciones = 30, Hormigas = 15

```

FÍSICA:✅ Fitness: 27,068 (MEJOR FITNESS)**Horarios de trabajo:** Lunes a Sábado, 7:00 AM - 9:35 PM (16 franjas diarias)

  T1: Lunes 07:00     ✓

  T2: Martes 09:00    ✓✅ Conflictos aula: 1

  P1: Miércoles 11:00 ✓ (después de teorías)

  L1: Jueves 13:00    ✓ (después de prácticas)✅ Mejora vs baseline: -0.77%**Aulas disponibles:**

```

```- **Piso F**: F201-F404 (Laboratorios ≤20 estudiantes)

**Ejemplo inválido:**

```- **Pisos G6-G8**: G601-G809 (Aulas teóricas), G610-G812 (Laboratorios >20 estudiantes)

QUÍMICA:

  T1: Lunes 07:00     ✓### **Comparación 15 Experimentos**

  L1: Martes 09:00    ✗ (lab ANTES de práctica)

  P1: Miércoles 11:00 ✗## 🚀 Instalación y Configuración

```

| Exp | Algoritmo | β | Fitness | T→P→L | Conf Aula | Estado |

## 🧬 Algoritmo ACO - Context-Aware Scheduling

|-----|-----------|---|---------|-------|-----------|--------|### Prerrequisitos

### Innovación Principal

| **12** | ACO | 2.0 | 27,116 | ✅ 100% | **0** 🏆 | MEJOR GLOBAL |

El algoritmo implementa **"context-aware scheduling"**: rastrea el último slot asignado por curso y filtra slots disponibles para garantizar ordenamiento temporal.

| **10** | ACO+GS | 5.0 | **27,068** | ✅ 100% | 1 | MEJOR FITNESS |- Python 3.11+

```python

# Para cada sección del curso| 13 | ACO+GS | 3.0 | 27,168 | ✅ 100% | 5 | ✅ |- Node.js 18+

ultimo_slot_curso = (dia_num, hora_obj)

| 14 | ACO+GS | 7.0 | 27,268 | ✅ 100% | 3 | ✅ |- MySQL 8.0

# Filtrar solo slots POSTERIORES

slots_validos = [s for s in slots if timestamp(s) > ultimo_slot_curso]- Docker (opcional)



# Asignar en el mejor slot válido**Todos los experimentos: 100% T→P→L correcto**

asignar(slot_valido)

### Instalación Manual

# Actualizar contexto

ultimo_slot_curso = nuevo_timestamp---

```

#### Backend

### Ventajas

## 🎓 Reglas Pedagógicas```bash

- ✅ **Automático**: No requiere post-procesamiento

- ✅ **Eficiente**: O(n) por cursocd backend

- ✅ **Robusto**: Maneja casos límite con fallback

- ✅ **Resultados**: 73.8% cumplimiento T→P→L### **Implementadas y Validadas**



## 📈 Resultados Actuales (Experimento 36)# Instalar dependencias



```1. **✅ Orden T→P→L** - Teorías antes que Prácticas (100% cumplido)pip install -r requirements.txt

✅ Asignaciones: 298/298 (100%)

✅ T→P→L: 45/61 cursos válidos (73.8%)2. **✅ Horarios Prime** - Teorías en Lun-Jue 8:00-12:00 (100% cumplido)

✅ Proyecciones: 60/61 cursos (98.4%)

✅ Conflictos aula: 03. **✅ Espaciado** - Separación entre sesiones (0 violaciones)# Configurar base de datos

✅ Conflictos profesor: 0

⏱️ Tiempo ejecución: ~27s4. **⚠️ Distribución** - Máximo 2 sesiones/día (área de mejora)export DATABASE_URL="mysql+pymysql://user:password@localhost:3306/upao_timetabling"

```

5. **⚠️ Conflictos** - Sin conflictos profesor/aula (0-5 encontrados)

### Interpretación

# Iniciar servidor

- **73.8% T→P→L**: Excelente para un problema NP-hard con múltiples restricciones

- **100% asignaciones**: Todas las secciones tienen horario---uvicorn app.main:app --reload

- **0 conflictos**: Sin superposiciones de recursos

- Las 16 cursos restantes (26.2%) tienen violaciones debido a limitaciones de recursos/disponibilidad```



## 🔬 Trabajo Futuro## 📁 Estructura Principal



1. **GraphSAGE Integration**: Usar embeddings de grafo para mejorar selección de slots#### Procesar datos de ejemplo

2. **Multi-objetivo**: Optimizar simultáneamente T→P→L, distancia entre sesiones, y preferencias

3. **Soft constraints**: Implementar restricciones de profesores como penalizaciones``````bash

4. **Búsqueda local mejorada**: Hill climbing dirigido a violaciones específicas

backend/cd backend

## 📚 Dependencias

├── ejecutar_aco_experimento.py          # 🔥 Script principalpython process_excel_final.py  # Procesa datos de proyecciones

```bash

pip install mysql-connector-python openpyxl pandas├── graphsage_inference.py               # Inferencia GNNpython app/algorithms/aco.py   # Ejecuta algoritmo ACO

```

├── train_graphsage_simple.py            # Entrenamiento```

## 🎓 Contexto Académico

├── reglas_pedagogicas.py                # 🆕 Reglas institucionales

**Tesis:** Optimización de Horarios Universitarios usando ACO y GraphSAGE  

**Universidad:** UPAO  ├── bitacora_experimentos_OE2.py         # 📊 Instrumento 1## 📚 Datos Procesados

**Período:** 2025-20

├── validacion_horarios_OE2.py           # 📊 Instrumento 2

## 📝 Notas Importantes

├── analisis_pedagogico_retrospectivo.py # Análisis experimentosEl sistema ha procesado exitosamente **75 cursos** de la proyección 2025:

1. **Libro1.xlsx es obligatorio**: Contiene las proyecciones de cursos (teorías, prácticas, labs)

2. **Base de datos MySQL requerida**: Debe tener tablas `courses`, `professors`, `classrooms`, etc.├── models/                              # Embeddings entrenados

3. **Experimentos se guardan automáticamente**: Tanto en BD como en JSON

4. **Local search no mejora resultados**: El context-aware ya es óptimo para este problema├── app/                                 # FastAPI- **10,746 estudiantes** proyectados total



---└── requirements.txt- **106 grupos de teoría**, **85 de práctica**, **111 de laboratorio**



**Última actualización:** 09/10/2025  ```- **61 cursos presenciales**, **14 no presenciales**

**Versión:** ACO Context-Aware v2.0  

**Estado:** Funcional - Listo para tesis- **48 cursos con laboratorio** (8 para piso F, 26 para piso G)


---

### Distribución por Ciclos

## 🎮 Uso

| Ciclo | Cursos | Estudiantes | Grupos T/P/L |

### **Ejecutar Experimento**|-------|--------|-------------|--------------|

```bash| 1     | 17     | 1,040       | 12/12/5      |

python ejecutar_aco_experimento.py| 2     | 6      | 2,018       | 17/17/9      |

```| 3     | 6      | 1,041       | 12/10/11     |

Genera horario completo con reglas pedagógicas integradas.| 4     | 6      | 1,530       | 11/7/19      |

| 5     | 6      | 725         | 9/3/14       |

### **Generar Bitácora**| 6     | 6      | 1,444       | 10/5/16      |

```bash| 7     | 6      | 866         | 10/1/19      |

python bitacora_experimentos_OE2.py| 8     | 6      | 840         | 11/7/5       |

```| 9     | 6      | 482         | 6/4/6        |

Exporta `bitacora_experimentos_OE2.xlsx` con todos los experimentos.| 10    | 10     | 760         | 8/19/7       |



### **Validar Experimento**## 🧪 Algoritmos Implementados

```bash

python validacion_horarios_OE2.py 10### ACO (Ant Colony Optimization)

```

Calcula EMR, CAS, F1 Score vs. horarios BANNER.**Estado**: ✅ Implementado y probado



### **Análisis Retrospectivo**El algoritmo ACO procesa **302 tareas de programación** (suma de todos los grupos) y optimiza asignaciones considerando todas las restricciones UPAO.

```bash

python analisis_pedagogico_retrospectivo.py**Parámetros por defecto**:

```- `α` (alpha): 1.0 - Importancia de feromonas

Evalúa experimentos 9-15 con reglas pedagógicas.- `β` (beta): 2.0 - Importancia de heurística  

- `ρ` (rho): 0.1 - Tasa de evaporación

---- Iteraciones: 50

- Hormigas: 15

## 🔬 Tecnología

### GraphSAGE

- **Python 3.13**

- **PyTorch + PyTorch Geometric** (GraphSAGE)**Estado**: 📋 Planificado para Fase 2

- **FastAPI** (API REST)

- **MySQL 8.0** (Base de datos)## 📊 Infraestructura Configurada

- **Pandas, NumPy** (Procesamiento)

### Franjas Horarias

---- **96 franjas totales** (16 por día × 6 días)

- Lunes a Sábado, 7:00 AM - 9:35 PM

## 📚 Documentación- Períodos: Mañana (7:00-11:59), Tarde (12:00-17:59), Noche (18:00-21:35)



- **[ANALISIS_EXPERIMENTOS_12-15.md](ANALISIS_EXPERIMENTOS_12-15.md)** - Análisis sensibilidad β### Aulas Disponibles

- **[INFORME_MEJORAS_ALGORITMO.md](INFORME_MEJORAS_ALGORITMO.md)** - Mejoras implementadas- **48 aulas catalogadas**

- **[RESUMEN_FINAL_OE2.md](RESUMEN_FINAL_OE2.md)** - Resumen completo- **Piso F**: 12 laboratorios (capacidad 20 c/u)

- **Pisos G6-G8**: 27 aulas teóricas + 9 laboratorios grandes

---

## 🔧 API Endpoints

## 👤 Autor

### Principales

**Seiji Amaya** - Ingeniería de Sistemas, UPAO```http

GET    /api/courses              # 75 cursos cargados

**Versión:** 2.0 (Con Reglas Pedagógicas) - Octubre 2025GET    /api/classrooms           # 48 aulas disponibles  

GET    /api/time-slots           # 96 franjas horarias
POST   /api/excel/upload         # Subir proyecciones
POST   /api/algorithms/aco/run   # Ejecutar optimización
```

## 🧪 Resultados de Pruebas

### Ejemplo de Cursos Procesados

1. **CIEN752** - ALGEBRA MATRIC Y GEOM ANALIT
   - Ciclo 1, Presencial
   - 80 estudiantes teoría/práctica, 2 grupos c/u

2. **ICSI506** - ALGORITMIA Y PROGRAMACION  
   - Ciclo 1, Presencial
   - 80 estudiantes laboratorio, 5 grupos
   - Restricción: LAB. F

3. **CIEN753** - CALCULO I
   - Ciclo 1, Presencial
   - 80 estudiantes teoría/práctica, 2 grupos c/u

## 🏗️ Próximos Pasos

### Fase 2: Completar Backend
- [ ] Integración GraphSAGE
- [ ] Optimización de parámetros ACO
- [ ] API endpoints avanzados
- [ ] Sistema de validación robusto

### Fase 3: Frontend React
- [ ] Interface de usuario completa
- [ ] Editor visual de horarios
- [ ] Drag & drop functionality
- [ ] Dashboard de métricas

### Fase 4: Integración y Testing
- [ ] Testing exhaustivo
- [ ] Optimización de performance
- [ ] Documentación de API
- [ ] Deployment

## 📞 Contacto

**Autor**: Seiji Amaya  
**Universidad**: Universidad Privada Antenor Orrego (UPAO)  
**Escuela**: Ingeniería de Sistemas e Informática

---

**Estado del Proyecto**: ✅ **Fundación Completa** | 🔄 **Algoritmos en Desarrollo** | 📋 **Frontend Planificado**