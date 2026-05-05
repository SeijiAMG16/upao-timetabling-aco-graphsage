# REPORTE_EVOLUCION_ACO

## 1) Telemetria Historica (Linea Base)

Fuentes revisadas:

- `backend/logs/aco_diag_20251129_114310.log`
- `resultados/diag_verbose_20251129.log`
- `resultados/diag_verbose_relax_20251129.log`
- `resultados/diag_verbose_relax_20251129_10x10.log`
- `backend/logs/entrenamiento_graphsage_estable_20260421_112135.json`
- `backend/logs/inventario_conflictos_mapeo_20260421_090026.json`
- `backend/logs/inventario_conflictos_mapeo_20260421_090924.json`
- `backend/logs/reparar_conflictos_prioridad_20260421_094913.json`
- `backend/logs/reparar_todas_duras_20260421_100008.json`

Resumen extraido:

- Diagnostico 2025-11-29:
  - Parametros observados: `alpha=1.0`, `beta=2.3`, `rho=0.2`, `q0=0.88`, con corridas entre `1x1` y `12x12`.
  - Cobertura observada: entre `87.8%` y `93.9%` (promedio `90.97%` en lote `10x10`).
- Telemetria hibrida 2026-04-21:
  - `best_metrics.coverage ~= 89.71%`
  - `generated_solution.total_cost = 4753.56`
  - `generated_solution.tiempo_ejecucion = 1786.08 s (~29.77 min)`
  - `hard_violations = 0`

## 2) Configuracion Usada En Corridas Locales (2026-05-03)

Parametros solicitados para entorno local:

- `n_hormigas = 15`
- `n_iteraciones = 30`
- `early_stopping_patience = 5`
- `alpha = 1.0`
- `beta = 2.0`
- `rho = 0.1`
- `q0 = 0.9`

Comando base ejecutado:

```powershell
python backend/ejecutar_aco_completo.py --hormigas 15 --iteraciones 30 --patiencia 5 --alpha 1.0 --beta 2.0 --rho 0.1 --q0 0.9
```

Ajustes tecnicos aplicados antes de medir variacion:

1. `constraints.py`: `_parse_ciclo_number` ahora acepta `int/float/str` (evita fallo al parsear ciclo).
2. `constraints.py`: se elimino la sobreescritura interna que forzaba pesos a `1.0` para varias penalizaciones (`preferencia_laboratorio`, `dispersion_teoria_practica`, `fatiga_bloques_largos`, `profesor_baja_prioridad`).
3. `ejecutar_aco_completo.py`: `SoftConstraintEvaluator` recibe `professor_restrictions`.

## 3) Corridas Reales (Con Costos Calibrados)

Artefactos:

- `backend/logs/run_v2_calibrado_fixpesos_1_20260503.log`
- `backend/logs/run_v2_calibrado_fixpesos_2_20260503.log`
- `horario_generado_20260503_182230.json`
- `horario_generado_20260503_184622.json`

| Run | Fecha local | Iteraciones completadas | Secciones asignadas | Cobertura | Costo soft total | Latencia |
|---|---|---:|---:|---:|---:|---:|
| V2-R1 | 2026-05-03 18:22 | 8 | 280/311 | 90.03% | 95774.11 | 1753.19 s (29.22 min) |
| V2-R2 | 2026-05-03 18:46 | 6 | 281/311 | 90.35% | 85642.22 | 1416.54 s (23.61 min) |

### Desglose dominante de costo (V2-R1 y V2-R2)

Contribuciones ponderadas mas altas:

- `preferencia_franja` (peso 25): `71625.00` (R1) vs `65375.00` (R2)
- `dispersion_teoria_practica` (peso 25): `19500.00` (R1) vs `16500.00` (R2)
- `alineacion_franja` (peso 8): `1830.67` (R1) vs `1586.00` (R2)
- `huecos_estudiantes` (peso 10): `1430.00` (R1) vs `980.00` (R2)

Observacion:

- `profesor_baja_prioridad = 0.0` en ambas corridas. Esto indica que, con los datos actuales, no se registraron franjas marcadas como baja prioridad para activar esa multa.

## 4) Variacion Observada

Variacion entre las dos corridas calibradas:

- Cobertura: `90.03%` a `90.35%` (variacion baja de `0.32` puntos porcentuales).
- Costo soft total: `95774.11` a `85642.22` (diferencia `10131.89`, aprox. `10.58%`).
- Latencia: `29.22 min` a `23.61 min`.

Interpretacion:

- La cobertura se mantiene estable cerca de `90%`.
- La mayor variabilidad aparece en el costo blando, dominado por reglas de turno (`preferencia_franja`) y dispersion T/P (`dispersion_teoria_practica`), precisamente las que recibieron peso de negocio alto.

## 5) Comparativa Evolutiva (Tesis)

| Version | Evidencia | Parametros | Cobertura | Costo blando | Latencia | Lectura |
|---|---|---|---:|---:|---:|---|
| 1.0 Baseline | Logs 2025-11-29 (`diag_verbose*`, `aco_diag*`) | Escenarios de diagnostico (1x1 a 12x12), `beta=2.3` | 87.8%-93.9% | No consolidado en esos logs | No consolidada | Foco en factibilidad/cobertura |
| 2.0 Calibrada | Corridas locales 2026-05-03 (`run_v2_calibrado_fixpesos_*`) | `15/30`, `patience=5`, `alpha=1.0`, `beta=2.0`, `rho=0.1`, `q0=0.9` | 90.03%-90.35% | 85642-95774 | 23.6-29.2 min | Mayor presion por cumplimiento de turnos y regla pedagogica T/P |
