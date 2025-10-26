# 🧹 Limpieza del Proyecto - Octubre 2025

## 📋 Resumen

Se realizó una limpieza masiva del proyecto para organizar la estructura de archivos y eliminar scripts obsoletos que estaban generando desorden.

## 📊 Estadísticas

- **Archivos movidos a `backend/obsoletos/`**: 223
- **Scripts Python activos mantenidos**: 4
- **Fecha de limpieza**: 22 de Octubre, 2025

## ✅ Scripts Activos (Mantenidos en `backend/`)

### Scripts Principales
1. **`ejecutar_aco_completo.py`** - Script principal para ejecutar ACO + GraphSAGE
   - Parámetros optimizados: 40 hormigas, 150 iteraciones
   - Usa GraphSAGE para heurísticas neuronales
   - Genera JSON con asignaciones completas

2. **`exportar_horarios_un_archivo.py`** - Exportador de horarios a Excel
   - Genera un solo archivo Excel con todos los profesores
   - Usa 16 bloques de 50 minutos (timeslots reales de UPAO)
   - Formato: `HORARIOS_PROFESORES_UPAO_YYYYMMDD_HHMMSS.xlsx`

### Scripts de Servidor
3. **`start_server.py`** - Inicia FastAPI con uvicorn y reload
4. **`run_simple.py`** - Inicia FastAPI sin reload (para debugging)

### Archivos de Configuración
- **`requirements.txt`** - Dependencias del proyecto

## 📁 Estructura Limpia del Backend

```
backend/
├── app/                    # Aplicación FastAPI principal
│   ├── api/               # Endpoints REST
│   ├── aco_graphsage/     # Motor ACO + GraphSAGE
│   ├── excel/             # Procesadores Excel
│   ├── models.py          # Modelos SQLAlchemy
│   ├── database.py        # Configuración DB
│   └── main.py            # App principal
├── models/                 # Modelos de datos adicionales
├── templates/              # Templates HTML
├── tests/                  # Tests unitarios activos
├── obsoletos/              # Scripts antiguos (223 archivos)
│   └── README.md          # Documentación de obsoletos
├── ejecutar_aco_completo.py
├── exportar_horarios_un_archivo.py
├── start_server.py
├── run_simple.py
└── requirements.txt
```

## 🗑️ Categorías de Scripts Movidos a `obsoletos/`

### Experimentación y Desarrollo
- Versiones antiguas del ACO (`aco_simple.py`, `aco_con_ligas*.py`)
- Scripts de experimentación con diferentes configuraciones
- Versiones obsoletas de ejecutores (`ejecutar_horario_completo.py`)

### Análisis y Debugging
- ~50 scripts de análisis (`analizar_*.py`)
- ~40 scripts de verificación (`check_*.py`, `verificar_*.py`)
- ~30 scripts de debugging (`debug_*.py`, `diagnostico_*.py`)
- ~20 scripts de investigación (`investigar_*.py`, `buscar_*.py`)

### Mantenimiento
- Scripts de migración de base de datos
- Scripts de restauración de datos
- Scripts de normalización
- Backups manuales

### Datos Antiguos
- ~50 archivos JSON (asignaciones, experimentos, mapeos)
- ~30 archivos Excel (horarios y resultados viejos)
- ~20 archivos TXT (logs y outputs)
- Documentación de fixes obsoletos (MD)
- Scripts SQL manuales

## 🚀 Endpoints de la API

El sistema ahora tiene una API limpia y bien organizada:

### Generación de Horarios
- `POST /api/horario/generar` - Iniciar generación ACO+GraphSAGE
- `GET /api/horario/status` - Consultar progreso
- `GET /api/horario/descargar/{filename}` - Descargar Excel
- `GET /api/horario/archivos` - Listar archivos generados

### Gestión de Datos
- `/api/projections` - Proyecciones de cursos
- `/api/professors` - Profesores
- `/api/classrooms` - Aulas
- `/api/courses` - Cursos
- `/api/assignments` - Asignaciones

## 📝 Notas Importantes

1. **La carpeta `obsoletos/` puede eliminarse en el futuro** una vez que se confirme que el sistema funciona correctamente en producción.

2. **Backup recomendado**: Antes de eliminar `obsoletos/`, hacer un backup externo por si se necesita consultar alguna lógica antigua.

3. **Scripts de test**: Los tests en `backend/obsoletos/test_*.py` fueron movidos porque eran experimentales. Los tests activos están en `backend/tests/`.

4. **requirements.txt**: Se mantiene en el directorio principal y contiene todas las dependencias necesarias.

## 🎯 Beneficios de la Limpieza

- ✅ **Estructura más clara**: Solo 4 scripts Python en el root del backend
- ✅ **Fácil navegación**: Carpetas bien organizadas por función
- ✅ **Menos confusión**: Scripts obsoletos separados con documentación
- ✅ **Mejor mantenibilidad**: Código activo claramente identificado
- ✅ **Producción lista**: Sistema limpio y profesional

## 📅 Próximos Pasos

1. Confirmar que el sistema funciona correctamente
2. Ejecutar tests de integración
3. Después de 2-3 meses sin problemas, considerar eliminar `obsoletos/`
4. Mantener solo los 4 scripts principales + carpetas app, models, templates, tests

---

**Responsable**: Sistema de limpieza automatizado  
**Fecha**: 22 de Octubre, 2025  
**Archivos afectados**: 223 movidos a obsoletos  
**Estado**: ✅ Completado exitosamente
