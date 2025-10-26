# Diagnóstico: Fallo en Generación de Horario Completo

## Resumen del Problema

El algoritmo ACO completó 30 iteraciones pero **NO generó ninguna solución válida**. Ninguna hormiga pudo asignar todas las ~321 secciones.

## Secciones que Fallan Más Frecuentemente

Basado en los logs de las últimas 5 iteraciones (26-30):

### Secciones Críticas (fallan en > 50% de intentos)
- **1552**: Falla en ~12 intentos
- **1553**: Falla en ~10 intentos  
- **1554**: Falla en ~5 intentos
- **1631**: Falla en 2 intentos (CIEN769 LABORATORIO Liga 1)
- **1608, 1609**: Fallan múltiples veces
- **1607, 1613, 1616, 1617**: Fallan ocasionalmente
- **1550, 1551**: Fallan en últimas iteraciones
- **1570, 1574, 1592**: Fallan ocasionalmente

## Patrones Observados

### 1. Cascada de Fallos
Las hormigas empiezan asignando bien (15-20 secciones) pero después **fallan sistemáticamente** en ciertas secciones. Esto sugiere:
- Recursos (aulas/franjas) se agotan prematuramente
- No hay backtracking - una vez agotados, no se puede continuar

### 2. Mismo Punto de Fallo
Muchas hormigas fallan en la **misma secuencia** de secciones:
```
1546 → 1548 → 1550 → 1551 → [FALLO 1552]
```

O:

```
1547 → 1549 → [FALLO 1553] → 1554
```

Esto indica que estas secciones tienen **requisitos muy restrictivos** o dependen de recursos ya asignados a las secciones anteriores de su grupo.

### 3. Grupo CIEN769 (secciones 1629-1631)
La hormiga 9 de iteración 27 y hormiga 1 de iteración 30:
```
✅ 1629 (TEORIA)
✅ 1630 (PRACTICA)  
❌ 1631 (LABORATORIO) <-- FALLA
```

Esto confirma que **aunque priorizamos CIEN769**, sigue fallando cuando se procesa después de otros grupos.

## Hipótesis del Problema Principal

### Problema: Agotamiento Prematuro de Recursos

El algoritmo ACO está procesando secciones en un orden que agota rápidamente:

1. **Aulas grandes**: Las secciones que se asignan primero pueden estar tomando aulas de 30+ capacidad que luego se necesitan para CIEN769 y otros cursos grandes
   
2. **Franjas horarias populares**: Las franjas más deseables (mañanas, días específicos) se ocupan antes de llegar a secciones críticas

3. **Combinación profesor-franja**: Algunos profesores tienen muchas secciones y sus franjas disponibles se agotan

## Posibles Soluciones

### Opción 1: Priorizar Más Grupos Críticos ⭐ RECOMENDADO

En lugar de solo priorizar CIEN769, necesitamos identificar y priorizar **TODOS** los grupos con restricciones severas.

Los candidatos basados en fallos:
- Grupos que contienen secciones 1550-1554 (parecen ser de un mismo curso/liga)
- Grupos que contienen secciones 1608-1613
- Grupos que contienen secciones 1614-1617

**Acción**: Crear un script que identifique automáticamente grupos problemáticos basados en:
- Capacidad de aulas disponibles vs. estudiantes
- Disponibilidad de profesores
- Horas semanales requeridas

### Opción 2: Reducir el Espacio de Búsqueda

- Deshabilitar temporalmente secciones menos prioritarias
- Generar horario parcial solo con secciones críticas
- Una vez asignadas las críticas, agregar las demás

### Opción 3: Modificar Estrategia ACO

#### A. Lookahead Heurístico
Antes de asignar una sección, verificar si las secciones futuras del mismo grupo/liga podrán asignarse.

#### B. Resource Reservation
"Reservar" aulas grandes y franjas específicas para grupos conocidos como problemáticos.

#### C. Staged Assignment
1. Primera fase: Solo grupos prioritarios (CIEN769, 1550-1554, etc.)
2. Segunda fase: Grupos medianos
3. Tercera fase: Grupos pequeños flexibles

### Opción 4: Ajustes de Base de Datos ⚠️ INVASIVO

- Aumentar capacidad de más aulas (convertir más TEORICA a TEORICA_LAB)
- Reasignar profesores con menos carga
- Dividir secciones grandes en múltiples secciones más pequeñas

## Recomendación Inmediata

**Implementar Opción 1 + Opción 3C:**

1. Ejecutar script de análisis para identificar grupos críticos automáticamente
2. Modificar `priority_course_groups` para incluir TODOS los grupos críticos:
   ```python
   priority_course_groups = [
       ("CIEN769", 1),    # Ya identificado
       ("XXXX", liga),    # Cursos de secciones 1550-1554
       ("YYYY", liga),    # Cursos de secciones 1608-1617
       # ... etc
   ]
   ```
3. Implementar staged assignment: correr ACO solo con grupos prioritarios primero

## Próximos Pasos

1. **[URGENTE]** Identificar qué cursos/ligas corresponden a secciones 1550-1554 y 1608-1617
2. Analizar sus requisitos (capacidad, profesor, tipo de aula)
3. Verificar disponibilidad de recursos para esos grupos
4. Actualizar lista de `priority_course_groups`
5. Re-ejecutar con más hormigas (15-20) y menos iteraciones (15-20) para explorar más diversidad
