#!/usr/bin/env python3
"""
INTEGRADOR DE CURSOS REALES V1 - UPAO TIMETABLING
=================================================

Este script:
1. Elimina los cursos basura actuales (CURSO_001, etc.)
2. Inserta los cursos REALES extraídos del Excel
3. Crea las secciones correspondientes
4. Mantiene los profesores existentes

Autor: Sistema UPAO
Fecha: 2025-10-10
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine
from app.models import Course, CourseSection, Professor
from extraer_cursos_v2 import ExtractorCursosV2
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class IntegradorCursosReales:
    """Integrador de cursos reales al sistema UPAO"""
    
    def __init__(self):
        self.db = SessionLocal()
        self.extractor = ExtractorCursosV2()
        self.cursos_insertados = 0
        self.secciones_creadas = 0
    
    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()
    
    def limpiar_cursos_basura(self):
        """Eliminar cursos basura actuales"""
        logger.info("🗑️ Eliminando cursos basura actuales...")
        
        try:
            # Primero eliminar secciones
            secciones_eliminadas = self.db.query(CourseSection).delete()
            logger.info(f"   📋 Secciones eliminadas: {secciones_eliminadas}")
            
            # Luego eliminar cursos
            cursos_eliminados = self.db.query(Course).delete()
            logger.info(f"   📚 Cursos eliminados: {cursos_eliminados}")
            
            self.db.commit()
            logger.info("✅ Limpieza completada")
            
        except Exception as e:
            logger.error(f"❌ Error en limpieza: {e}")
            self.db.rollback()
            raise
    
    def insertar_cursos_reales(self):
        """Insertar cursos reales extraídos del Excel"""
        logger.info("📚 Extrayendo cursos del Excel...")
        
        cursos_excel = self.extractor.extraer_todos_cursos()
        if not cursos_excel:
            logger.error("❌ No se pudieron extraer cursos del Excel")
            return False
        
        logger.info(f"📖 {len(cursos_excel)} cursos extraídos. Insertando en base de datos...")
        
        try:
            for curso_data in cursos_excel:
                # Crear curso
                curso = Course(
                    codigo=curso_data['codigo'],
                    nombre=curso_data['nombre'],
                    ciclo=curso_data['ciclo'],
                    modalidad=curso_data['modalidad'],
                    creditos=curso_data['creditos'],
                    alumnos_teoria=curso_data['alumnos_teoria'],
                    alumnos_practica=curso_data['alumnos_practica'],
                    alumnos_laboratorio=curso_data['alumnos_laboratorio'],
                    grupos_teoria=curso_data['grupos_teoria'],
                    grupos_practica=curso_data['grupos_practica'],
                    grupos_laboratorio=curso_data['grupos_laboratorio'],
                    requiere_laboratorio=curso_data['requiere_laboratorio'],
                    requiere_practica=curso_data['requiere_practica'],
                    restricciones_especiales=None,
                    active=True,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                
                self.db.add(curso)
                self.db.flush()  # Para obtener el ID
                
                # Crear secciones automáticamente
                self.crear_secciones_para_curso(curso, curso_data)
                
                self.cursos_insertados += 1
                
                if self.cursos_insertados % 10 == 0:
                    logger.info(f"   📚 Insertados {self.cursos_insertados}/{len(cursos_excel)} cursos...")
            
            self.db.commit()
            logger.info(f"✅ {self.cursos_insertados} cursos insertados correctamente")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error insertando cursos: {e}")
            self.db.rollback()
            raise
    
    def crear_secciones_para_curso(self, curso: Course, curso_data: dict):
        """Crear secciones para un curso específico"""
        curso_id = curso.id
        
        # Crear secciones de teoría
        for i in range(curso_data['grupos_teoria']):
            seccion = CourseSection(
                course_id=curso_id,
                tipo='teoria',
                seccion=f"T{i+1}",
                alumnos_proyectados=curso_data['alumnos_teoria'] // curso_data['grupos_teoria'] if curso_data['grupos_teoria'] > 0 else 0,
                alumnos_reales=0,
                activa=True,
                created_at=datetime.now()
            )
            self.db.add(seccion)
            self.secciones_creadas += 1
        
        # Crear secciones de práctica
        for i in range(curso_data['grupos_practica']):
            seccion = CourseSection(
                course_id=curso_id,
                tipo='practica',
                seccion=f"P{i+1}",
                alumnos_proyectados=curso_data['alumnos_practica'] // curso_data['grupos_practica'] if curso_data['grupos_practica'] > 0 else 0,
                alumnos_reales=0,
                activa=True,
                created_at=datetime.now()
            )
            self.db.add(seccion)
            self.secciones_creadas += 1
        
        # Crear secciones de laboratorio
        for i in range(curso_data['grupos_laboratorio']):
            seccion = CourseSection(
                course_id=curso_id,
                tipo='laboratorio',
                seccion=f"L{i+1}",
                alumnos_proyectados=curso_data['alumnos_laboratorio'] // curso_data['grupos_laboratorio'] if curso_data['grupos_laboratorio'] > 0 else 0,
                alumnos_reales=0,
                activa=True,
                created_at=datetime.now()
            )
            self.db.add(seccion)
            self.secciones_creadas += 1
    
    def verificar_profesores(self):
        """Verificar que los profesores siguen intactos"""
        profesores = self.db.query(Professor).count()
        logger.info(f"👥 Profesores en sistema: {profesores}")
        return profesores > 0
    
    def mostrar_resumen_final(self):
        """Mostrar resumen de la integración"""
        cursos_total = self.db.query(Course).count()
        secciones_total = self.db.query(CourseSection).count()
        profesores_total = self.db.query(Professor).count()
        
        print("\n" + "="*60)
        print("🎯 RESUMEN DE INTEGRACIÓN COMPLETADA")
        print("="*60)
        print(f"📚 Cursos reales insertados: {self.cursos_insertados}")
        print(f"📋 Secciones creadas: {self.secciones_creadas}")
        print(f"📖 Total cursos en sistema: {cursos_total}")
        print(f"📋 Total secciones en sistema: {secciones_total}")
        print(f"👥 Total profesores: {profesores_total}")
        print()
        
        # Mostrar algunos ejemplos
        print("📚 EJEMPLOS DE CURSOS INSERTADOS:")
        cursos_sample = self.db.query(Course).limit(5).all()
        for curso in cursos_sample:
            print(f"  • {curso.codigo}: {curso.nombre} (Ciclo {curso.ciclo})")
            print(f"    💳 {curso.creditos} créditos | {curso.modalidad}")
            print(f"    👥 T:{curso.alumnos_teoria} P:{curso.alumnos_practica} L:{curso.alumnos_laboratorio}")
            print()
    
    def ejecutar_integracion_completa(self):
        """Ejecutar todo el proceso de integración"""
        logger.info("🚀 INICIANDO INTEGRACIÓN DE CURSOS REALES")
        logger.info("=" * 50)
        
        try:
            # Paso 1: Verificar profesores antes
            if not self.verificar_profesores():
                logger.error("❌ No hay profesores en el sistema. Ejecuta primero la restauración de profesores.")
                return False
            
            # Paso 2: Limpiar cursos basura
            self.limpiar_cursos_basura()
            
            # Paso 3: Insertar cursos reales
            if not self.insertar_cursos_reales():
                return False
            
            # Paso 4: Verificar resultado
            self.mostrar_resumen_final()
            
            logger.info("✅ INTEGRACIÓN COMPLETADA EXITOSAMENTE")
            return True
            
        except Exception as e:
            logger.error(f"💥 ERROR EN INTEGRACIÓN: {e}")
            return False

def main():
    """Función principal"""
    integrador = IntegradorCursosReales()
    
    print("🎯 INTEGRADOR DE CURSOS REALES - UPAO TIMETABLING")
    print("=" * 55)
    print("Este script va a:")
    print("1. 🗑️ Eliminar cursos basura actuales")
    print("2. 📚 Insertar 64 cursos REALES del Excel")
    print("3. 📋 Crear secciones automáticamente")
    print("4. 👥 Mantener profesores intactos")
    print()
    
    respuesta = input("¿Continuar? (y/N): ").strip().lower()
    if respuesta not in ['y', 'yes', 'sí', 'si']:
        print("❌ Operación cancelada")
        return
    
    exito = integrador.ejecutar_integracion_completa()
    
    if exito:
        print("\n🎉 ¡PERFECTO! Cursos reales integrados al sistema")
        print("   Ahora tienes 64 cursos reales de ISIA en lugar de cursos basura")
    else:
        print("\n💥 Hubo errores en la integración")

if __name__ == "__main__":
    main()