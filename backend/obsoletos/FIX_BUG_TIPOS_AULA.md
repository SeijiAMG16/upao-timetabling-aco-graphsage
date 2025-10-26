# PROBLEMA CRÍTICO ENCONTRADO Y CORREGIDO

## Fecha: 2025-10-18

## Resumen Ejecutivo

Se identificó y corregió un **BUG CRÍTICO** que impedía la generación de horarios: el código ACO/GraphSAGE buscaba tipos de aula `'laboratorio'`, `'teorica'`, `'practica'` pero la base de datos almacena `'LAB'` y `'NOLAB'`.

## Problema Detectado

### Síntomas
- NINGUNA iteración del ACO generaba soluciones válidas (0/30 iteraciones exitosas)
- Las secciones 1550-1554, 1605-1613, 1631-1632 **SIEMPRE fallaban** en asignación
- Error recurrente: "No se pudo asignar sección XXXX"

### Causa Raíz

El validador de restricciones duras (`constraints.py`) comparaba directamente:

```python
if classroom.tipo != "laboratorio":  # ❌ SIEMPRE FALSO
    return False
```

Pero en la base de datos:
- Laboratorios tienen `tipo = 'LAB'` (NO 'laboratorio')
- Aulas normales tienen `tipo = 'NOLAB'` (NO 'teorica')

**Resultado**: TODAS las validaciones de tipo de aula fallaban, haciendo IMPOSIBLE asignar laboratorios.

### Impacto

Afectaba a **TODAS** las secciones de tipo laboratorio:
- ICSI506 (Algoritmia y Programación) - 5 secciones lab
- ICSI509 (POO) - 6 secciones lab  
- CIEN769 (Física II) - 3 secciones lab
- ADMI779 - Múltiples secciones lab

~25-30% de todas las secciones NO podían asignarse por este bug.

## Solución Implementada

### 1. Función de Normalización

Ya existía en `graph_builder.py` pero NO se usaba en validación:

```python
def _normalize_classroom_type(self, raw_type: Optional[str]) -> str:
    value = (raw_type or "").strip().upper()
    if value in {"LAB", "LABORATORIO", "LABORATORY"}:
        return "laboratorio"
    if value in {"PRACTICA", "PRÁCTICA", "PRACTICE"}:
        return "practica"
    if value in {"NOLAB", "AULA", "TEORICA", "TEÓRICA", "GENERAL"}:
        return "teorica"
    return "teorica"
```

### 2. Correcciones Aplicadas

#### A. `constraints.py` - Clase `HardConstraintValidator`

**Agregado método de normalización** (línea ~141):
```python
def _normalize_classroom_type(self, raw_type: Optional[str]) -> str:
    """Normaliza tipos de aula de la BD a formato estándar"""
    value = (raw_type or "").strip().upper()
    if value in {"LAB", "LABORATORIO", "LABORATORY"}:
        return "laboratorio"
    if value in {"PRACTICA", "PRÁCTICA", "PRACTICE"}:
        return "practica"
    if value in {"NOLAB", "AULA", "TEORICA", "TEÓRICA", "GENERAL"}:
        return "teorica"
    return "teorica"
```

**Modificado `_validate_classroom_type()`** (línea ~530):
```python
def _validate_classroom_type(self, assignment: Assignment) -> Tuple[bool, Dict[str, Any]]:
    classroom = self.classrooms[assignment.classroom_id]
    
    # ✅ NORMALIZAR el tipo ANTES de comparar
    tipo_normalizado = self._normalize_classroom_type(classroom.tipo)
    
    if assignment.session_type == "L":
        if tipo_normalizado != "laboratorio":  # ✅ Ahora funciona
            return False, detail
```

#### B. `graph_builder.py` - Construcción del grafo

**Modificada creación de aristas section→classroom** (línea ~666):
```python
for classroom in classrooms:
    # ✅ Normalizar tipo de aula
    tipo_aula_normalizado = self._normalize_classroom_type(classroom.tipo)
    
    # Filtrar por tipo compatible
    if tipo_section == 'L' and tipo_aula_normalizado != 'laboratorio':  # ✅ Correcto
        continue
```

### 3. Archivos Modificados

```
backend/app/aco_graphsage/constraints.py
  - Agregado: _normalize_classroom_type() método
  - Modificado: _validate_classroom_type() usa normalización

backend/app/aco_graphsage/graph_builder.py
  - Modificado: línea 666, usa normalización en construcción de grafo
```

## Verificación

### Datos de Aulas en BD

```sql
SELECT DISTINCT tipo, COUNT(*) as total
FROM classrooms
GROUP BY tipo;
```

Resultado:
- `'LAB'`: 15 aulas (capacidad 20)
- `'NOLAB'`: 24 aulas (capacidad 60)

### Estado de Secciones Problemáticas

Antes del fix:
- Sección 1550-1554: ❌ 0% asignadas (0/5)
- Sección 1608-1613: ❌ 0% asignadas (0/6)
- Sección 1631: ❌ 0% asignada

Después del fix:
- **PENDIENTE**: Ejecutando test de validación

## Próximos Pasos

1. ✅ **COMPLETADO**: Corrección del bug de tipos
2. ⏳ **EN CURSO**: Test de validación con 5 hormigas × 3 iteraciones
3. ⏳ **PENDIENTE**: Ejecución completa con 15 hormigas × 25 iteraciones
4. ⏳ **PENDIENTE**: Validación de horario generado

## Lecciones Aprendidas

### Error de Diseño
- **Falta de validación de esquema**: El código asumió nombres de tipos sin verificar contra la BD
- **Normalización inconsistente**: Existía la función pero no se usaba consistentemente

### Mejoras Aplicadas
- Centralizar normalización de tipos
- Aplicar normalización en TODAS las comparaciones
- Documentar valores esperados vs. valores reales de BD

### Recomendaciones Futuras
1. Agregar tests unitarios que validen tipos de aula
2. Documentar esquema de BD explícitamente en código
3. Agregar validación al inicio: "¿existen aulas tipo LAB? ✓"
4. Logging más detallado en validaciones

## Impacto Esperado

Con esta corrección, se espera:
- ✅ Asignación exitosa de TODAS las secciones de laboratorio
- ✅ Tasa de éxito del ACO > 50% (antes: 0%)
- ✅ Cobertura de ~95%+ de secciones (antes: ~70%)
- ✅ Soluciones válidas en <10 iteraciones (antes: nunca)

---

**Autor**: AI Assistant (GitHub Copilot)  
**Revisión**: Pendiente  
**Estado**: Fix implementado, validación en curso
