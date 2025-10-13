# 📊 EXPLICACIÓN DE LAS TABLAS DEL SISTEMA

## 🎯 Flujo del Sistema: De la Gestión Manual al Horario Final

El sistema tiene **3 fases principales**:

```
FASE 1: GESTIÓN MANUAL          FASE 2: ALGORITMO ACO/GraphSAGE       FASE 3: HORARIOS FINALES
(Administrador)                 (Automático)                           (Resultado)
     ↓                                ↓                                      ↓
professor_restrictions      →    Restricciones                    →   schedule_assignments
professor_course_assignments →    Preferencias histórias         →   (Horario optimizado)
                                      ↓
                               course_sections
                               (Secciones generadas)
```

---

## 📋 TABLAS EXPLICADAS

### 1️⃣ **professor_course_assignments** (TU GESTIÓN MANUAL)
**Propósito**: Aquí TÚ defines qué profesores pueden dictar cada curso

**Ejemplo de uso**:
```
| professor_id | course_id | session_type | semestre |
|--------------|-----------|--------------|----------|
| 5 (Juan)     | 10 (POO)  | T (Teoría)   | 2025-I   |
| 5 (Juan)     | 10 (POO)  | P (Práctica) | 2025-I   |
| 8 (Maria)    | 10 (POO)  | L (Lab)      | 2025-I   |
```

**Interpretación**:
- Juan puede dictar POO: teoría Y práctica
- Maria puede dictar POO: solo laboratorio
- Cuando el ACO genere el horario, **preferirá** asignar Juan a teoría/práctica y Maria a laboratorio

---

### 2️⃣ **professor_restrictions** (TU GESTIÓN MANUAL)
**Propósito**: Aquí TÚ bloqueas horarios donde profesores NO pueden enseñar

**Ejemplo de uso**:
```
| professor_id | day       | start_time | end_time | reason              |
|--------------|-----------|------------|----------|---------------------|
| 5 (Juan)     | Monday    | 07:00      | 09:40    | Reunión semanal     |
| 5 (Juan)     | Wednesday | 14:20      | 17:00    | Clases en otra sede |
```

**Interpretación**:
- Juan NO está disponible lunes 07:00-09:40 ni miércoles 14:20-17:00
- El ACO **NUNCA** le asignará clases en esos horarios (restricción dura)

---

### 3️⃣ **course_sections** (GENERADA POR EL SISTEMA)
**Propósito**: El sistema crea secciones automáticamente según demanda

**¿Cómo funciona?**
```python
Curso: Programación Orientada a Objetos (POO)
- Tiene 3 horas teoría, 2 horas práctica, 2 horas laboratorio
- 120 alumnos proyectados

El sistema crea automáticamente:
1. POO-T-A (teoría sección A) → 60 alumnos
2. POO-T-B (teoría sección B) → 60 alumnos
3. POO-P-A (práctica sección A) → 30 alumnos
4. POO-P-B (práctica sección B) → 30 alumnos
5. POO-P-C (práctica sección C) → 30 alumnos
6. POO-P-D (práctica sección D) → 30 alumnos
7. POO-L-A (laboratorio sección A) → 20 alumnos
8. POO-L-B (laboratorio sección B) → 20 alumnos
...etc
```

**Columnas importantes**:
- `course_id`: A qué curso pertenece
- `tipo`: 'teoria', 'practica', 'laboratorio'
- `seccion`: 'A', 'B', 'C'...
- `alumnos_proyectados`: Cuántos estudiantes

---

### 4️⃣ **schedule_assignments** (RESULTADO FINAL DEL ACO)
**Propósito**: El **resultado optimizado** del algoritmo ACO

**Ejemplo de uso**:
```
| id | course_section_id  | professor_id | classroom_id | time_slot_id | semestre |
|----|--------------------|--------------|--------------|--------------| ---------|
| 1  | 1 (POO-T-A)        | 5 (Juan)     | 15 (G602)    | 48 (Lun 8:50)| 2025-I   |
| 2  | 1 (POO-T-A)        | 5 (Juan)     | 15 (G602)    | 49 (Lun 9:45)| 2025-I   |
| 3  | 1 (POO-T-A)        | 5 (Juan)     | 15 (G602)    | 50 (Lun 10:40| 2025-I   |
| 4  | 3 (POO-P-A)        | 5 (Juan)     | 22 (G705)    | 78 (Mie 8:50)| 2025-I   |
| 5  | 3 (POO-P-A)        | 5 (Juan)     | 22 (G705)    | 79 (Mie 9:45)| 2025-I   |
| 6  | 7 (POO-L-A)        | 8 (Maria)    | 30 (G809)    | 105(Vie 14:20| 2025-I   |
| 7  | 7 (POO-L-A)        | 8 (Maria)    | 30 (G809)    | 106(Vie 15:15| 2025-I   |
```

**Interpretación**:
- **Sección POO-T-A** (teoría A): Juan, aula G602, lunes 08:50-11:30 (3 bloques consecutivos = 3 horas)
- **Sección POO-P-A** (práctica A): Juan, aula G705, miércoles 08:50-10:35 (2 bloques = 2 horas)
- **Sección POO-L-A** (laboratorio A): Maria, aula G809 (laboratorio), viernes 14:20-16:05 (2 horas)

**Columnas importantes**:
- `course_section_id`: Qué sección específica
- `professor_id`: Qué profesor asignado
- `classroom_id`: En qué aula
- `time_slot_id`: En qué horario (cada time_slot = 50 minutos)
- `generado_por_algoritmo`: TRUE (indica que ACO lo generó)
- `confianza_asignacion`: 0.0-1.0 (qué tan óptima es la asignación)

---

## 🔄 FLUJO COMPLETO PASO A PASO

### **PASO 1: TÚ CONFIGURAS (Frontend que creamos)**
```
1. Vas a "Restricciones de Profesores"
   → Seleccionas Juan
   → Bloqueas Lunes 07:00-09:40
   → Se guarda en: professor_restrictions

2. Vas a "Asignación Curso-Profesor"
   → Buscas "Programación Orientada a Objetos"
   → Asignas Juan → Teoría ✓
   → Asignas Juan → Práctica ✓
   → Asignas Maria → Laboratorio ✓
   → Se guarda en: professor_course_assignments
```

---

### **PASO 2: EL SISTEMA GENERA SECCIONES (Automático)**
```python
# Script: generate_sections.py (por crear)
Para cada curso:
  - Lee teoria_hours, practica_hours, laboratorio_hours
  - Lee alumnos_proyectados
  - Calcula cuántas secciones necesita:
    * Teoría: max 60 alumnos/sección
    * Práctica: max 30 alumnos/sección
    * Laboratorio: max 20 alumnos/sección
  
  - Crea registros en course_sections:
    POO-T-A, POO-T-B, POO-P-A, POO-P-B, etc.
```

---

### **PASO 3: EL ACO GENERA EL HORARIO (Tu algoritmo existente)**
```python
# Tu script: run_aco_optimized.py (ya existe, solo modificar)

Para cada course_section en course_sections:
  
  1. Buscar profesores aptos:
     - Consultar professor_course_assignments
     - Filtrar por session_type correcto
     - Ejemplo: Para POO-L-A (laboratorio), solo Maria es apta
  
  2. Verificar restricciones:
     - Consultar professor_restrictions
     - Bloquear horarios prohibidos
     - Ejemplo: Juan no puede lunes 07:00-09:40
  
  3. Usar ACO para optimizar:
     - Minimizar conflictos
     - Respetar restricciones duras (professor_restrictions)
     - Preferir asignaciones históricas (professor_course_assignments)
     - Evitar huecos en el horario
     - Agrupar bloques consecutivos
  
  4. Guardar resultado:
     - Crear registro en schedule_assignments
     - Columnas: course_section_id, professor_id, classroom_id, time_slot_id
     - Marcar generado_por_algoritmo=True
```

---

### **PASO 4: VISUALIZACIÓN DEL HORARIO FINAL**
```python
# Frontend final (por crear después)
Mostrar para cada profesor:
  Lunes:
    08:50-11:30: POO Teoría A (G602) - 60 alumnos
  Miércoles:
    08:50-10:35: POO Práctica A (G705) - 30 alumnos
  Viernes:
    (BLOQUEADO por restricción)

Mostrar para cada aula:
  G602:
    Lunes 08:50-11:30: POO-T-A (Prof. Juan)
    Martes 14:20-17:00: BD-T-B (Prof. Pedro)
```

---

## 🎨 EJEMPLO REAL COMPLETO

### **Configuración Manual (TÚ haces esto)**

#### **professor_course_assignments**:
```
Juan (id=5):
  - POO (Teoría)
  - POO (Práctica)
  - Base de Datos (Teoría)

Maria (id=8):
  - POO (Laboratorio)
  - Base de Datos (Laboratorio)
```

#### **professor_restrictions**:
```
Juan:
  - Lunes 07:00-09:40 (Reunión)
  - Viernes 18:00-22:30 (No disponible)

Maria:
  - Martes 07:00-12:25 (Clases otra sede)
```

---

### **Generación Automática de Secciones**

El sistema detecta:
- **POO**: 3h teoría, 2h práctica, 2h lab, 120 alumnos
- **BD**: 2h teoría, 0h práctica, 2h lab, 90 alumnos

Crea en `course_sections`:
```
POO-T-A (60 alum) → necesita profesor con POO-Teoría → Juan
POO-T-B (60 alum) → necesita profesor con POO-Teoría → Juan
POO-P-A (30 alum) → necesita profesor con POO-Práctica → Juan
POO-P-B (30 alum) → necesita profesor con POO-Práctica → Juan
POO-P-C (30 alum) → necesita profesor con POO-Práctica → Juan
POO-P-D (30 alum) → necesita profesor con POO-Práctica → Juan
POO-L-A (20 alum) → necesita profesor con POO-Lab → Maria
POO-L-B (20 alum) → necesita profesor con POO-Lab → Maria
...
BD-T-A (45 alum) → Juan
BD-T-B (45 alum) → Juan
BD-L-A (20 alum) → Maria
BD-L-B (20 alum) → Maria
...
```

---

### **ACO Genera Horario Final**

En `schedule_assignments` se guarda:

**Para POO-T-A** (3 bloques consecutivos):
```sql
INSERT INTO schedule_assignments VALUES
(1, 1, 5, 15, 48, '2025-I', ...),  -- Lun 08:50 G602 Juan
(2, 1, 5, 15, 49, '2025-I', ...),  -- Lun 09:45 G602 Juan
(3, 1, 5, 15, 50, '2025-I', ...)   -- Lun 10:40 G602 Juan
```

**Para POO-L-A** (2 bloques consecutivos):
```sql
INSERT INTO schedule_assignments VALUES
(10, 7, 8, 30, 78, '2025-I', ...), -- Mie 08:50 G809 Maria
(11, 7, 8, 30, 79, '2025-I', ...)  -- Mie 09:45 G809 Maria
```

---

## 🚀 RESUMEN EJECUTIVO

| Tabla | Quién la llena | Cuándo | Para qué |
|-------|----------------|--------|----------|
| **professor_restrictions** | TÚ (Frontend) | ANTES del ACO | Bloquear horarios prohibidos |
| **professor_course_assignments** | TÚ (Frontend) | ANTES del ACO | Definir quién puede dictar qué |
| **course_sections** | Sistema automático | ANTES del ACO | Dividir cursos en secciones manejables |
| **schedule_assignments** | ACO (Algoritmo) | RESULTADO FINAL | Horario optimizado listo para usar |

---

## 📌 PRÓXIMOS PASOS

1. **Completar gestión manual** (Ya está hecho ✓):
   - Frontend para restricciones
   - Frontend para asignaciones curso-profesor

2. **Crear generador de secciones** (Por hacer):
   ```python
   # Script: backend/generate_course_sections.py
   # Lee courses → Crea course_sections según demanda
   ```

3. **Modificar ACO para usar estas tablas** (Por hacer):
   ```python
   # Archivo: backend/app/algorithms/aco_optimized.py
   # Consultar professor_course_assignments
   # Respetar professor_restrictions
   # Generar schedule_assignments
   ```

4. **Frontend de visualización** (Por hacer):
   - Ver horario por profesor
   - Ver horario por aula
   - Ver horario por sección
   - Exportar a Excel/PDF

---

## ❓ PREGUNTAS FRECUENTES

**P: ¿Por qué necesito `professor_course_assignments` SI el ACO puede asignar cualquier profesor?**  
R: Porque en la vida real no todos los profesores pueden dictar todos los cursos. Un profesor de matemáticas no puede dictar programación. Esta tabla define las **capacidades reales** de cada profesor.

**P: ¿Qué pasa si no asigno ningún profesor a un curso?**  
R: El ACO fallará o asignará aleatoriamente, lo cual es malo. Por eso debes llenar al 100% la tabla `professor_course_assignments`.

**P: ¿La tabla `schedule_assignments` guarda horarios históricos?**  
R: Sí. Cada vez que ejecutas el ACO con un nuevo semestre (ej: 2025-I, 2025-II), guarda nuevos registros. Los anteriores quedan como historial.

**P: ¿Puedo editar manualmente `schedule_assignments` después del ACO?**  
R: Sí, el administrador podría hacer ajustes manuales si el ACO genera algo subóptimo. Marca `generado_por_algoritmo=False` para esas filas.

---

**¿Necesitas más aclaraciones? Pregúntame específicamente sobre alguna tabla o flujo.**
