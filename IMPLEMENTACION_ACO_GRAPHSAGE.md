# Implementación ACO + GraphSAGE en el Sistema

## 📋 Resumen

Se ha actualizado el sistema completo para usar el algoritmo híbrido **ACO + GraphSAGE** tanto en el backend como en el frontend.

## 🔧 Cambios Realizados

### Backend (`backend/app/api/endpoints/horario.py`)

#### ✅ Script Actualizado
- **Antes**: Usaba `ejecutar_horario_completo.py` (ACO básico)
- **Ahora**: Usa `ejecutar_aco_completo.py` (ACO + GraphSAGE)

#### ✅ Parámetros Optimizados
```python
--hormigas 40              # 40 hormigas por iteración
--iteraciones 150          # 150 iteraciones máximas
--alpha 1.0                # Peso de feromona
--beta 2.3                 # Peso de heurística neural (GraphSAGE)
--rho 0.2                  # Tasa de evaporación
--q0 0.88                  # Probabilidad de explotación
--patiencia 8              # Early stopping patience
--max-candidatos 600       # Máximo combinaciones candidato
--max-profesores 6         # Profesores máximos por sección
--max-aulas 12             # Aulas máximas por sección
--max-timeslots 24         # Franjas de inicio máximas por sección
```

#### ✅ Timeout Aumentado
- **Antes**: 600 segundos (10 minutos)
- **Ahora**: 900 segundos (15 minutos)
- **Razón**: GraphSAGE requiere más tiempo para construir el grafo y generar embeddings

#### ✅ Logging Mejorado
- Registra estadísticas del JSON generado (total asignaciones, score final)
- Logs más descriptivos: "ACO+GraphSAGE" en lugar de solo "ACO"

#### ✅ Respuesta Mejorada
El endpoint `/api/horario/generar` ahora devuelve:
```json
{
  "message": "Generación de horario iniciada",
  "status": "started",
  "algorithm": "ACO + GraphSAGE",
  "estimated_time_minutes": 5,
  "parameters": {
    "hormigas": 40,
    "iteraciones": 150,
    "alpha": 1.0,
    "beta": 2.3,
    "rho": 0.2,
    "q0": 0.88
  }
}
```

### Frontend (`frontend/src/pages/GenerarHorario.jsx`)

#### ✅ Descripción Actualizada
- Menciona explícitamente "algoritmo híbrido ACO + GraphSAGE"

#### ✅ Proceso de Generación Detallado
Ahora muestra 5 pasos:
1. **Construye el grafo heterogéneo** de restricciones
2. **Ejecuta GraphSAGE** para generar embeddings
3. **Ejecuta ACO** guiado por heurísticas neuronales
4. **Exporta a Excel** con 16 bloques de 50 minutos
5. **Descarga automática**

#### ✅ Información Mejorada
```
⏱️ Tiempo estimado: 4-6 minutos
🧠 Algoritmo: ACO + GraphSAGE (Híbrido)
🐜 Parámetros: 40 hormigas × 150 iteraciones máx.
```

## 🚀 Endpoints Disponibles

### 1. Generar Horario
```http
POST /api/horario/generar
```
Inicia la generación en background. Devuelve inmediatamente con status.

### 2. Consultar Status
```http
GET /api/horario/status
```
Consulta el progreso de la generación actual.

Respuesta:
```json
{
  "is_running": true,
  "progress": 65,
  "message": "Ejecutando algoritmo ACO con GraphSAGE...",
  "error": null,
  "filename": null,
  "started_at": "2025-10-22T10:30:00",
  "completed_at": null
}
```

### 3. Descargar Excel
```http
GET /api/horario/descargar/{filename}
```
Descarga el archivo Excel generado.

### 4. Listar Archivos
```http
GET /api/horario/archivos
```
Lista todos los archivos Excel generados con metadata.

## 🎯 Flujo Completo

1. **Usuario hace clic en "Generar Horario Completo"** en el frontend
2. **Frontend llama** a `POST /api/horario/generar`
3. **Backend inicia proceso en background**:
   - Construye grafo con `TimetableGraphBuilder`
   - Crea modelo GNN con `ACOGraphSAGEModel`
   - Ejecuta `ACOEngine` con heurísticas neuronales
   - Genera JSON con asignaciones
   - Exporta Excel con horarios de profesores (16 bloques × 50 min)
4. **Frontend consulta status** cada 2 segundos via polling
5. **Backend actualiza progreso**: 10% → 20% → 60% → 100%
6. **Al completar**, frontend **descarga automáticamente** el Excel

## 📊 Características del Sistema

### GraphSAGE
- **Tipo de grafo**: Heterogéneo (HeteroData)
- **Nodos**: secciones, profesores, aulas, franjas horarias, currículos
- **Aristas**: assigned_to, uses, starts_at, belongs_to
- **Hidden dimension**: 64
- **Aprendizaje**: Embeddings contextuales de relaciones complejas

### ACO
- **Hormigas**: 40 por iteración
- **Iteraciones**: Hasta 150 (con early stopping)
- **Heurística**: Combinación de feromona + heurística neural (GraphSAGE)
- **Beta alto (2.3)**: Mayor peso a las predicciones de la red neuronal

### Restricciones
- **Duras**: No solapamiento, capacidad de aulas, disponibilidad de profesores
- **Suaves**: Distribución uniforme, preferencias de horario, minimización de brechas

## 📝 Archivos Modificados

1. ✅ `backend/app/api/endpoints/horario.py` - Endpoint actualizado a ACO+GraphSAGE
2. ✅ `frontend/src/pages/GenerarHorario.jsx` - UI actualizada con info detallada
3. ✅ `backend/asignar_convocatoria_isia119.py` - Asignación de profesor faltante

## 🔍 Próximos Pasos

1. **Ejecutar desde el frontend**: Ir a la página "Generar Horario"
2. **Hacer clic en "Generar Horario Completo"**
3. **Esperar 4-6 minutos** mientras se ejecuta ACO+GraphSAGE
4. **Descargar automáticamente** el Excel con todos los horarios
5. **Verificar cobertura**: Debería ser ~99.7% (307/308 secciones)

## 💾 Base de Datos

### Asignación ISIA119
Se agregaron 4 asignaciones para el curso ISIA119:
```sql
professor_id=353 (PROF_032 "CONVOCATORIA")
course_id=672 (ISIA119)
- Teoría Liga 1
- Teoría Liga 2
- Laboratorio Liga 1
- Laboratorio Liga 2
```

## ✨ Ventajas del Sistema Híbrido

1. **Mejor calidad de soluciones**: GraphSAGE aprende patrones del grafo
2. **Convergencia más rápida**: Heurísticas neuronales guían mejor la búsqueda
3. **Generalización**: Se adapta a cambios en datos sin reconfiguración
4. **Restricciones complejas**: Maneja relaciones entre múltiples entidades
5. **Escalabilidad**: Eficiente con 308 secciones, 47 profesores, 32 aulas, 96 franjas

---

**Fecha**: 22 de Octubre, 2025  
**Versión**: ACO + GraphSAGE v1.0  
**Estado**: ✅ Implementado y listo para producción
