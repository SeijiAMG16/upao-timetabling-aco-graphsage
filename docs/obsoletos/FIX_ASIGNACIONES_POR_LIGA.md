# FIX CRÍTICO: Asignaciones de Profesores por Liga

## 🔴 PROBLEMA IDENTIFICADO

El sistema NO estaba respetando las asignaciones de profesores por liga correctamente.

### Ejemplo Real - TESIS II (ISIA125):

**En la Base de Datos:**
- Liga 1: Profesor Cieza (PROF_007) - Teoría + Práctica
- Liga 2: Profesor Jaime Díaz (PROF_021) - Teoría + Práctica  
- Liga 3: Profesor Cieza (PROF_007) - Teoría + Práctica
- Liga 4: Profesor Cieza (PROF_007) - Teoría + Práctica

**En el Horario Generado (ANTES DEL FIX):**
- ❌ Cieza: Solo 1 asignación (Liga 3 - Teoría)
- ❌ Jaime Díaz: Múltiples asignaciones en TODAS las ligas (1, 2, 3)

## 🐛 CAUSA RAÍZ

Archivo: `backend/app/aco_graphsage/graph_builder.py`
Función: `_candidate_professors_for_section()` (líneas 882-910)

### Código ANTES del FIX (INCORRECTO):

```python
def _candidate_professors_for_section(self, section: CourseSection) -> List[int]:
    course_id = section.course_id
    session_type = self._map_section_type(section)
    league = section.league or 1

    manual_candidates: Set[int] = set()

    # PROBLEMA: Se agregan TODOS los niveles con update()
    if (course_id, session_type, league) in self.prof_assign_by_league:
        manual_candidates.update(
            self.prof_assign_by_league[(course_id, session_type, league)]
        )  # Agrega profesores de liga específica

    if (course_id, session_type) in self.prof_assign_by_type:
        manual_candidates.update(
            self.prof_assign_by_type[(course_id, session_type)]
        )  # TAMBIÉN agrega profesores SIN importar liga

    if course_id in self.prof_assign_by_course:
        manual_candidates.update(self.prof_assign_by_course[course_id])
        # TAMBIÉN agrega profesores SIN importar tipo ni liga

    return sorted(manual_candidates)
```

**EFECTO DEL BUG:**
- Para Liga 1 (Cieza asignado):
  1. Agrega Cieza (por liga 1) ✓
  2. TAMBIÉN agrega Jaime Díaz (porque está en tipo T/P sin importar liga) ❌
  3. Resultado: AMBOS profesores son candidatos → ACO elige cualquiera

- Para Liga 2 (Jaime Díaz asignado):
  1. Agrega Jaime Díaz (por liga 2) ✓
  2. TAMBIÉN agrega Cieza (porque está en tipo T/P sin importar liga) ❌
  3. Resultado: AMBOS profesores son candidatos → ACO elige cualquiera

**CONSECUENCIA:** 
- ❌ Se rompe la especificidad por liga
- ❌ Profesores asignados a liga específica aparecen en otras ligas
- ❌ ACO elige aleatoriamente entre candidatos incorrectos

## ✅ SOLUCIÓN IMPLEMENTADA

### Código DESPUÉS del FIX (CORRECTO):

```python
def _candidate_professors_for_section(self, section: CourseSection) -> List[int]:
    """
    Obtiene profesores candidatos para una sección, respetando ESTRICTAMENTE
    las asignaciones por liga.
    
    PRIORIDADES (con fallback solo si no hay asignaciones más específicas):
    1. (curso, tipo, liga) - MÁS ESPECÍFICO
    2. (curso, tipo) - solo si NO hay asignaciones por liga
    3. (curso) - solo si NO hay asignaciones por tipo ni por liga
    
    FIX CRÍTICO (2024-10-22): 
    - ANTES: Se agregaban TODAS las asignaciones (liga + tipo + curso) con update()
    - AHORA: Se respeta SOLO el nivel más específico disponible
    - RESULTADO: Cada liga tiene su profesor correcto
    """
    course_id = section.course_id
    session_type = self._map_section_type(section)
    league = section.league or 1

    # NIVEL 1 (MÁS ESPECÍFICO): Asignaciones por (curso, tipo, liga)
    key_league = (course_id, session_type, league)
    if key_league in self.prof_assign_by_league:
        return sorted(self.prof_assign_by_league[key_league])
        # ✓ Si existe asignación por liga, SOLO devolver esos profesores
        # ✓ NO buscar en otros niveles

    # NIVEL 2: Asignaciones por (curso, tipo) - solo si NO hay asignaciones por liga
    key_type = (course_id, session_type)
    if key_type in self.prof_assign_by_type:
        return sorted(self.prof_assign_by_type[key_type])
        # ✓ Solo llega aquí si NO había asignación por liga

    # NIVEL 3: Asignaciones por curso - solo si NO hay asignaciones más específicas
    if course_id in self.prof_assign_by_course:
        return sorted(self.prof_assign_by_course[course_id])
        # ✓ Solo llega aquí si NO había asignación por liga ni por tipo

    # Sin asignaciones = sin candidatos
    return []
```

**LÓGICA DEL FIX:**
- ✅ Si existe asignación por (curso + tipo + liga) → devolver SOLO esos profesores
- ✅ Si NO existe por liga, buscar por (curso + tipo)
- ✅ Si NO existe por tipo, buscar por curso
- ✅ Cada nivel hace `return` inmediatamente (no agrega y continúa)

## 🧪 VERIFICACIÓN DEL FIX

Script: `backend/verificar_fix_ligas.py`

### Resultados de la Verificación:

```
[ASIGNACIONES] Cargadas por liga (course_id, session_type, league):
--------------------------------------------------------------------
  Liga 1 - Tipo T: PROF_007 (CIEZA MOSTACERO SEGUNDO EDWIN)
  Liga 1 - Tipo P: PROF_007 (CIEZA MOSTACERO SEGUNDO EDWIN)
  Liga 2 - Tipo T: PROF_021 (Jaime Diaz Sanchez)
  Liga 2 - Tipo P: PROF_021 (Jaime Diaz Sanchez)
  Liga 3 - Tipo T: PROF_007 (CIEZA MOSTACERO SEGUNDO EDWIN)
  Liga 3 - Tipo P: PROF_007 (CIEZA MOSTACERO SEGUNDO EDWIN)
  Liga 4 - Tipo T: PROF_007 (CIEZA MOSTACERO SEGUNDO EDWIN)
  Liga 4 - Tipo P: PROF_007 (CIEZA MOSTACERO SEGUNDO EDWIN)

[SIMULACION] Seleccion de candidatos POR SECCION:
--------------------------------------------------------------------
Sección P1         | Liga 1 | Tipo practica -> Candidatos: PROF_007 (Cieza)
Sección T1         | Liga 1 | Tipo teoria   -> Candidatos: PROF_007 (Cieza)
Sección P2         | Liga 2 | Tipo practica -> Candidatos: PROF_021 (Jaime Diaz)
Sección T2         | Liga 2 | Tipo teoria   -> Candidatos: PROF_021 (Jaime Diaz)
Sección P3         | Liga 3 | Tipo practica -> Candidatos: PROF_007 (Cieza)
Sección T3         | Liga 3 | Tipo teoria   -> Candidatos: PROF_007 (Cieza)
Sección P4         | Liga 4 | Tipo practica -> Candidatos: PROF_007 (Cieza)
Sección T4         | Liga 4 | Tipo teoria   -> Candidatos: PROF_007 (Cieza)
```

✅ **PERFECTO:** Cada sección tiene EXACTAMENTE el profesor correcto según su liga.

## 📊 IMPACTO DEL FIX

### ANTES:
- ❌ Profesor Cieza: 1 sección (solo Liga 3)
- ❌ Profesor Jaime Díaz: 7 secciones (Ligas 1, 2, 3 mezcladas)
- ❌ 75% de asignaciones incorrectas en TESIS II

### DESPUÉS (ESPERADO):
- ✅ Profesor Cieza: 6 secciones (Ligas 1, 3, 4 - Teoría + Práctica cada una)
- ✅ Profesor Jaime Díaz: 2 secciones (Liga 2 - Teoría + Práctica)
- ✅ 100% de asignaciones correctas

## 🔍 CURSOS AFECTADOS

Este bug afectaba a **TODOS los cursos con múltiples profesores asignados a diferentes ligas**, incluyendo:

1. TESIS II (ISIA125) - 4 ligas
2. TESIS I (ISIA124) - 4 ligas
3. Cualquier curso con asignaciones diferenciadas por liga

**Estimado:** ~30-40% del total de secciones tenían asignaciones incorrectas.

## ✅ ESTADO ACTUAL

- [x] Bug identificado y documentado
- [x] Solución implementada en `graph_builder.py`
- [x] Script de verificación creado y ejecutado con éxito
- [x] Regeneración de horario EN PROGRESO
- [ ] Exportación a Excel pendiente
- [ ] Validación final de todas las asignaciones

## 📝 PRÓXIMOS PASOS

1. ✅ Esperar a que termine la regeneración del horario completo
2. ✅ Ejecutar `exportar_horarios_un_archivo.py`
3. ✅ Verificar manualmente que TESIS II tiene las asignaciones correctas:
   - Liga 1: Solo Cieza (T1 + P1)
   - Liga 2: Solo Jaime Díaz (T2 + P2)
   - Liga 3: Solo Cieza (T3 + P3)
   - Liga 4: Solo Cieza (T4 + P4)
4. ✅ Verificar otros cursos con múltiples profesores

## 🎯 CRITERIOS DE ÉXITO

El fix se considera exitoso si:
1. ✅ Cada sección de TESIS II tiene el profesor correcto según su liga
2. ✅ No hay "cruces" entre profesores de diferentes ligas
3. ✅ La cobertura sigue siendo 100% (315/315 secciones)
4. ✅ Todos los demás cursos también respetan sus asignaciones por liga

---

**Archivo modificado:** `backend/app/aco_graphsage/graph_builder.py`  
**Líneas:** 882-918  
**Fecha:** 2024-10-22  
**Estado:** ✅ IMPLEMENTADO - EN PRUEBA
