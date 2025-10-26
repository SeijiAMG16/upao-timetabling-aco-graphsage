# 📦 Carpeta de Scripts Obsoletos

Esta carpeta contiene scripts que fueron utilizados durante el desarrollo y experimentación del proyecto, pero que **ya no son necesarios** para la operación actual del sistema.

## 🗂️ Categorías de Scripts Obsoletos

### 🔬 Scripts de Análisis y Debugging
- `analizar_*.py` - Análisis de datos, colores, conflictos, restricciones
- `check_*.py` - Verificaciones de aulas, modalidades, restricciones
- `debug_*.py` - Scripts de debugging de ACO, candidatos, secciones
- `diagnostico_*.py` - Diagnósticos profundos de fallos y restricciones
- `investigar_*.py` - Investigación de secciones no asignadas y problemas
- `verificar_*.py` - Verificación de cobertura, horarios, mapeos

### 🔄 Scripts de Migración y Mantenimiento
- `fix_*.py` - Correcciones de aulas, modalidades, tipos
- `migration_*.py` - Migraciones de esquema de base de datos
- `normalize_*.py` - Normalización de secciones
- `restaurar_*.py` - Restauración de datos originales
- `backup_database.py` - Backup manual de base de datos

### 📊 Scripts de Extracción y Generación
- `extraer_*.py` - Extracción de asignaciones, cursos, grupos
- `generar_*.py` - Generación de mapeos, secciones, horarios
- `asignar_*.py` - Asignación manual de profesores y cursos
- `poblar_*.py` - Población de tablas específicas

### 🧪 Scripts de Experimentación
- `aco_simple.py`, `aco_con_ligas*.py` - Versiones anteriores del ACO
- `ejecutar_aco_con_proyecciones.py` - Ejecuciones experimentales
- `ejecutar_aco_graphsage_ligas.py` - Experimentos con GraphSAGE
- `ejecutar_horario_completo.py` - Script viejo reemplazado por `ejecutar_aco_completo.py`
- `graphsage_*.py` - Scripts de inferencia y entrenamiento standalone
- `train_graphsage_simple.py` - Entrenamiento manual de GraphSAGE

### 📄 Scripts de Exportación Obsoletos
- `exportar_horarios_profesores.py` - Versión antigua del exportador
- `exportar_horario_excel.py` - Exportador obsoleto
- `export_schedules_excel.py` - Exportador antiguo
- `visualizar_horario_generado.py` - Visualizador manual

### 🧩 Scripts Misceláneos
- `app_visualizacion.py` - App de visualización standalone
- `buscar_*.py` - Búsqueda de secciones específicas
- `identificar_*.py` - Identificación de secciones problemáticas
- `mapear_*.py` - Mapeo manual de secciones virtuales
- `monitor_progreso.py` - Monitor de progreso manual
- `prueba_*.py` - Scripts de prueba diversos
- `quick_*.py` - Checks rápidos de desarrollo
- `run_pipeline_once.py` - Pipeline manual
- `slots_tiempo_upao.py` - Generador de timeslots (ahora en models)
- `temp_debug.py` - Debug temporal
- `upload_*.py` - Upload manual de datos

### 🧪 Tests Obsoletos
- `test_*.py` - Tests unitarios movidos o reemplazados

### 📁 Archivos de Datos Obsoletos
- `*.json` - Asignaciones, coberturas, experimentos, mapeos, proyecciones, restricciones antiguas
- `*.txt` - Logs, outputs, resultados de debug
- `*.md` - Documentación de fixes y diagnósticos obsoletos
- `*.sql` - Scripts SQL manuales
- `*.xlsx` - Horarios y resultados de experimentos anteriores
- `dev.db` - Base de datos SQLite de desarrollo

## ✅ Scripts Activos (NO están aquí)

Los siguientes scripts **SÍ se usan** y están en el directorio principal:

- `ejecutar_aco_completo.py` - **Script principal** para ejecutar ACO+GraphSAGE
- `exportar_horarios_un_archivo.py` - **Exportador activo** con 16 timeslots de 50 min
- `start_server.py` - Iniciar servidor FastAPI
- `run_simple.py` - Iniciar servidor sin reload
- `requirements.txt` - Dependencias del proyecto
- `app/` - Aplicación FastAPI principal
- `models/` - Modelos de datos
- `tests/` - Tests activos
- `templates/` - Templates de la aplicación

## 🗑️ ¿Puedo Borrar Esta Carpeta?

**Sí**, pero es recomendable mantenerla por un tiempo por si necesitas:
- Consultar lógica de experimentos antiguos
- Recuperar algún script de análisis específico
- Revisar historial de correcciones aplicadas

Una vez que estés seguro de que el sistema funciona correctamente en producción, puedes eliminar toda esta carpeta.

## 📅 Fecha de Limpieza

**22 de Octubre, 2025** - Limpieza masiva de scripts obsoletos después de implementar el sistema híbrido ACO + GraphSAGE en producción.
