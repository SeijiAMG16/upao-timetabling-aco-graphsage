"""
Análisis T→P→L simplificado basado en el problema detectado
"""

print("="*80)
print("💡 ANÁLISIS DEL PROBLEMA T→P→L")
print("="*80)

print("""
PROBLEMA IDENTIFICADO:
======================

La validación T→P→L requiere que para CADA CURSO:
   TODAS las teorías < CUALQUIER práctica/lab
   TODAS las prácticas < CUALQUIER lab

Orden temporal: (día_número, hora)
Ejemplo:  (1=Lunes, 07:00) < (1=Lunes, 19:00) < (2=Martes, 07:00)

SITUACIÓN ACTUAL (Experimento 31: 6.6% TPL):
==========================================

Secciones ordenadas por tipo: T→P→L ✓
Slots priorizados: T=temprano, L=tardío ✓

PERO... el algoritmo procesa secciones de DIFERENTES CURSOS mezcladas:

Iteración 1:  FISICA_T1      → Lunes 07:00 ✓
Iteración 2:  QUIMICA_T1     → Lunes 09:00 ✓  
Iteración 3:  MATEMATICA_T1  → Lunes 11:00 ✓
...
Iteración 50: FISICA_P1      → Martes 07:00 ✓
...
Iteración 150: FISICA_L1     → Lunes 19:00 ❌ VIOLACIÓN!

FISICA_L1 (Lunes 19:00) es ANTES que FISICA_P1 (Martes 07:00)
   Timestamp: (1, 19:00) < (2, 07:00)
   Resultado: Lab antes que práctica → VIOLACIÓN T→P→L

¿POR QUÉ OCURRE?
================

El algoritmo ordena secciones POR TIPO (T→P→L) pero NO POR CURSO.
Entonces:
1. Todas las teorías se procesan primero (de todos los cursos mezclados)
2. Luego todas las prácticas (de todos los cursos mezclados)  
3. Finalmente todos los labs (de todos los cursos mezclados)

Las primeras teorías ocupan Lunes-Martes-Miércoles temprano.
Las últimas teorías toman Jueves-Viernes-Sábado temprano.

Cuando llegan las prácticas, los slots tempranos de Lunes ya están ocupados,
entonces van a Martes, Miércoles temprano.

Cuando llegan los labs (que priorizan horarios tardíos), 
toman Lunes 19:00, Martes 19:00, etc.

RESULTADO: Lab del curso X en Lunes tarde < Práctica del curso X en Viernes mañana


SOLUCIÓN CORRECTA:
==================

Agrupar secciones POR CURSO antes de procesar:

Por cada curso:
    1. Asignar TODAS sus teorías (T1, T2, T3...)
    2. Asignar TODAS sus prácticas (P1, P2, P3...)
    3. Asignar TODOS sus labs (L1, L2, L3...)

Ejemplo:
    Curso FISICA:
        FISICA_T1 → Lunes 07:00
        FISICA_T2 → Lunes 09:00  
        FISICA_T3 → Lunes 11:00
        FISICA_P1 → Martes 07:00  ← Después de todas las T
        FISICA_P2 → Martes 09:00
        FISICA_L1 → Miércoles 07:00  ← Después de todas las T y P
    
    Curso QUIMICA:
        QUIMICA_T1 → Martes 11:00
        QUIMICA_P1 → Miércoles 09:00
        QUIMICA_L1 → Miércoles 11:00

Ahora cada curso tiene sus secciones en orden temporal correcto.


IMPLEMENTACIÓN:
===============

En aco_simple.py, cambiar:

    # ACTUAL (MALO):
    secciones_ordenadas = sorted(secciones, key=lambda x: (
        {'T': 0, 'P': 1, 'L': 2}.get(x['session_type'][0], 3),
        x['course_name'],
        random.random()
    ))
    
    # CORRECTO (BUENO):
    secciones_ordenadas = sorted(secciones, key=lambda x: (
        x['course_name'],  # ← PRIMERO por curso
        {'T': 0, 'P': 1, 'L': 2}.get(x['session_type'][0], 3),  # ← LUEGO por tipo
        random.random()
    ))

Esto garantiza:
   FISICA_T1, FISICA_T2, FISICA_P1, FISICA_L1, QUIMICA_T1, QUIMICA_P1, ...
   
En lugar de:
   FISICA_T1, QUIMICA_T1, ..., FISICA_P1, QUIMICA_P1, ..., FISICA_L1, QUIMICA_L1
""")

print("="*80)
print("🔧 CORRECCIÓN A APLICAR:")
print("="*80)
print("""
Archivo: backend/aco_simple.py
Línea: ~72

CAMBIAR:
    secciones_ordenadas = sorted(secciones, key=lambda x: (
        {'T': 0, 'P': 1, 'L': 2}.get(x['session_type'][0], 3),  # Tipo primero
        x['course_name'],  # Curso segundo
        random.random()
    ))

POR:
    secciones_ordenadas = sorted(secciones, key=lambda x: (
        x['course_name'],  # Curso primero ← CLAVE!
        {'T': 0, 'P': 1, 'L': 2}.get(x['session_type'][0], 3),  # Tipo segundo
        random.random()
    ))
""")
print("="*80)
