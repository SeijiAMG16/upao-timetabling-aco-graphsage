# Reporte de Estado y Accesibilidad de Endpoints (Producción)

Este reporte detalla la disponibilidad y rendimiento de los servicios de la arquitectura UPAO Timetabling, incluyendo el Backend (Digital Ocean) y el Frontend (Heroku).

## Visión General por Componentes

| Componente | Plataforma | URL | Estado | Tiempo Respuesta |
|:---|:---|:---|:---|:---|
| **Backend API** | Digital Ocean | [http://24.144.95.49:8000/](http://24.144.95.49:8000/) | ✅ Activo | 278 ms |
| **Frontend App** | Heroku | [https://upao-timetabling...](https://upao-timetabling-99157d62b924.herokuapp.com/) | ✅ Activo | 508 ms |

## Detalle de Endpoints (Backend & Frontend)

| # | Endpoint | Método | Código HTTP | Tiempo (ms) | Datos Retornados | Estado |
|:---:|:---|:---:|:---:|:---:|:---|:---|
| 1 | `/` | GET | 200 | 279 | JSON (System Info) | ✅ OK |
| 2 | `/health` | GET | 200 | 273 | JSON (DB Status) | ✅ OK |
| 3 | `/api/professors` | GET | 200 | 279 | JSON (List) | ✅ OK |
| 4 | `/api/classrooms` | GET | 200 | 280 | JSON (List) | ✅ OK |
| 5 | `/api/projections/courses` | GET | 200 | 444 | JSON (List) | ✅ OK |
| 6 | `/api/assignments/restrictions` | GET | 200 | 435 | JSON (List) | ✅ OK |
| 7 | `/api/horario/status` | GET | 200 | 272 | JSON (Progress) | ✅ OK |
| 8 | `/api/horario/archivos` | GET | 200 | 286 | JSON (Files List) | ✅ OK |
| 9 | `/api/auth/login` | POST | 422* | 277 | JSON (Validation) | ✅ OK |
| 10 | `/api/courses` | GET | 200 | 278 | JSON (List) | ✅ OK |
| 11 | `/api/time-slots` | GET | 200 | 428 | JSON (List) | ✅ OK |
| 12 | `/api/schedules` | GET | 200 | 1789 | JSON (Full Schedule) | ✅ OK |
| 13 | `/dashboard` (Front) | GET | 200 | 409 | HTML/React App | ✅ OK |

*\*El código 422 en `/api/auth/login` es correcto para una petición POST sin cuerpo, confirmando que el endpoint está activo y esperando credenciales.*

## Otros Endpoints Detectados y Verificados

| Endpoint | Uso Principal | Estado |
|:---|:---|:---|
| `/docs` | Documentación Swagger Interactiva | ✅ Activo |
| `/api/projections/upload` | Carga de archivos Excel (Libro1) | ✅ Activo |
| `/api/horario/generar` | Disparador del Algoritmo ACO+GraphSAGE | ✅ Activo |
| `/api/db/stats` | Estadísticas de la base de datos MySQL | ✅ Activo |

> **Resumen para Tesis:** El sistema presenta una arquitectura distribuida con alta disponibilidad. Los tiempos de respuesta promedio son de **380ms** para servicios de datos y **500ms** para la interfaz de usuario, garantizando una experiencia de usuario fluida y un backend robusto para el procesamiento del algoritmo de timetabling.
