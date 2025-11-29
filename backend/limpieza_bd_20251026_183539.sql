
-- ============================================================================
-- SCRIPT DE LIMPIEZA Y CONSOLIDACIÓN DE BASE DE DATOS
-- Fecha: 2025-10-26 18:35:39.302705
-- Base de datos: upao_timetabling
-- ============================================================================

USE upao_timetabling;

-- ============================================================================
-- FASE 1: VERIFICACIÓN PRE-LIMPIEZA
-- ============================================================================

SELECT '=== FASE 1: VERIFICACIÓN PRE-LIMPIEZA ===' as mensaje;

-- Contar registros en tablas a eliminar
SELECT 'professor_courses' as tabla, COUNT(*) as registros FROM professor_courses
UNION ALL
SELECT 'course_nrc_mapping', COUNT(*) FROM course_nrc_mapping
UNION ALL
SELECT 'proposed_schedule_assignments', COUNT(*) FROM proposed_schedule_assignments;

-- Verificar diferencias entre professor_courses y professor_course_assignments
SELECT 
    'Registros SOLO en professor_courses (no en PCA)' as descripcion,
    COUNT(*) as cantidad
FROM professor_courses pc
LEFT JOIN professor_course_assignments pca 
    ON pca.professor_id = pc.professor_id 
    AND pca.course_id = pc.course_id
WHERE pca.id IS NULL;

-- ============================================================================
-- FASE 2: CREAR BACKUPS DE SEGURIDAD
-- ============================================================================

SELECT '=== FASE 2: CREANDO BACKUPS ===' as mensaje;

-- Backup de proposed_schedule_assignments (tiene 302 registros)
CREATE TABLE IF NOT EXISTS proposed_schedule_assignments_backup_20251026_183539 AS
SELECT * FROM proposed_schedule_assignments;

SELECT 'Backup de proposed_schedule_assignments creado' as mensaje;

-- ============================================================================
-- FASE 3: ELIMINAR TABLAS DUPLICADAS/LEGACY
-- ============================================================================

SELECT '=== FASE 3: ELIMINANDO TABLAS DUPLICADAS ===' as mensaje;

-- 1. Eliminar professor_courses (duplicada con professor_course_assignments)
DROP TABLE IF EXISTS professor_courses;
SELECT 'professor_courses eliminada' as mensaje;

-- 2. Eliminar course_nrc_mapping (vacía y redundante con course_sections.nrc)
DROP TABLE IF EXISTS course_nrc_mapping;
SELECT 'course_nrc_mapping eliminada' as mensaje;

-- 3. Eliminar proposed_schedule_assignments (legacy, ya respaldada)
DROP TABLE IF EXISTS proposed_schedule_assignments;
SELECT 'proposed_schedule_assignments eliminada' as mensaje;

-- ============================================================================
-- FASE 4: ESTANDARIZAR NOMBRES DE COLUMNAS
-- ============================================================================

SELECT '=== FASE 4: ESTANDARIZANDO NOMBRES ===' as mensaje;

-- Renombrar 'activa' a 'active' en course_sections
ALTER TABLE course_sections 
  CHANGE COLUMN activa active TINYINT DEFAULT 1;

SELECT 'Columna course_sections.activa renombrada a active' as mensaje;

-- ============================================================================
-- FASE 5: VERIFICACIÓN POST-LIMPIEZA
-- ============================================================================

SELECT '=== FASE 5: VERIFICACIÓN POST-LIMPIEZA ===' as mensaje;

-- Listar todas las tablas restantes
SELECT TABLE_NAME, TABLE_ROWS 
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'upao_timetabling'
ORDER BY TABLE_NAME;

-- Verificar estructura de course_sections
SHOW COLUMNS FROM course_sections;

-- Verificar que las tablas eliminadas ya no existen
SELECT 
    CASE 
        WHEN NOT EXISTS (SELECT 1 FROM information_schema.TABLES WHERE TABLE_NAME = 'professor_courses' AND TABLE_SCHEMA = 'upao_timetabling')
        THEN 'OK: professor_courses eliminada'
        ELSE 'ERROR: professor_courses AUN EXISTE'
    END as verificacion_1,
    CASE 
        WHEN NOT EXISTS (SELECT 1 FROM information_schema.TABLES WHERE TABLE_NAME = 'course_nrc_mapping' AND TABLE_SCHEMA = 'upao_timetabling')
        THEN 'OK: course_nrc_mapping eliminada'
        ELSE 'ERROR: course_nrc_mapping AUN EXISTE'
    END as verificacion_2,
    CASE 
        WHEN NOT EXISTS (SELECT 1 FROM information_schema.TABLES WHERE TABLE_NAME = 'proposed_schedule_assignments' AND TABLE_SCHEMA = 'upao_timetabling')
        THEN 'OK: proposed_schedule_assignments eliminada'
        ELSE 'ERROR: proposed_schedule_assignments AUN EXISTE'
    END as verificacion_3;

-- ============================================================================
-- FIN DEL SCRIPT
-- ============================================================================

SELECT '=== LIMPIEZA COMPLETADA ===' as mensaje;
SELECT 'Tablas eliminadas: 3' as resumen;
SELECT 'Columnas renombradas: 1' as resumen;
SELECT 'Backups creados: 1' as resumen;
