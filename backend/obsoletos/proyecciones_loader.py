"""
Módulo para cargar proyecciones de secciones desde Libro1.xlsx
Autor: Sistema ACO-GraphSAGE UPAO
Fecha: 2025
"""

import pandas as pd
import json
from pathlib import Path


class ProyeccionesLoader:
    """Carga y valida proyecciones de secciones por curso"""
    
    def __init__(self, excel_path='../inputs/Libro1.xlsx'):
        self.excel_path = excel_path
        self.proyecciones = {}
        self.cargar_proyecciones()
    
    def cargar_proyecciones(self):
        """
        Carga proyecciones desde Libro1.xlsx
        
        Columnas requeridas (por índice):
        - Col 5: ASIGNATURA
        - Col 17: N° Grupos Teoría
        - Col 18: N° Grupos Práctica
        - Col 19: N° Grupos Laboratorio
        """
        try:
            df = pd.read_excel(self.excel_path)
            
            # Acceder por índice para evitar problemas con caracteres especiales
            asignaturas = df.iloc[:, 5]  # ASIGNATURA
            grupos_t = df.iloc[:, 17]    # N° Grupos Teoría
            grupos_p = df.iloc[:, 18]    # N° Grupos Práctica
            grupos_l = df.iloc[:, 19]    # N° Grupos Laboratorio
            
            for i in range(len(df)):
                asignatura = asignaturas.iloc[i]
                
                # Filtrar filas vacías o subtotales
                if pd.isna(asignatura) or 'subtotal' in str(asignatura).lower():
                    continue
                
                # Normalizar nombre de curso (eliminar espacios múltiples)
                import re
                asignatura_norm = str(asignatura).strip().upper()
                asignatura_norm = re.sub(r'\s+', ' ', asignatura_norm)  # Múltiples espacios → 1
                
                t_count = grupos_t.iloc[i]
                p_count = grupos_p.iloc[i]
                l_count = grupos_l.iloc[i]
                
                # Convertir a enteros, manejar NaN como 0
                t_count = int(t_count) if pd.notna(t_count) else 0
                p_count = int(p_count) if pd.notna(p_count) else 0
                l_count = int(l_count) if pd.notna(l_count) else 0
                
                self.proyecciones[asignatura_norm] = {
                    'teoria': t_count,
                    'practica': p_count,
                    'laboratorio': l_count,
                    'total_secciones': t_count + p_count + l_count
                }
            
            print(f"✅ Proyecciones cargadas: {len(self.proyecciones)} cursos")
            
        except Exception as e:
            print(f"❌ Error cargando proyecciones: {e}")
            raise
    
    def obtener_proyeccion(self, nombre_curso):
        """
        Obtiene proyección para un curso específico
        
        Args:
            nombre_curso: Nombre del curso (se normaliza automáticamente)
        
        Returns:
            dict con claves: teoria, practica, laboratorio, total_secciones
            None si no existe
        """
        import re
        curso_norm = str(nombre_curso).strip().upper()
        curso_norm = re.sub(r'\s+', ' ', curso_norm)  # Normalizar espacios
        return self.proyecciones.get(curso_norm)
    
    def validar_horario_contra_proyeccion(self, horario_generado):
        """
        Valida que un horario generado respete las proyecciones
        
        Args:
            horario_generado: dict {curso: {T: count, P: count, L: count}}
        
        Returns:
            tuple (is_valid, violaciones_dict)
        """
        violaciones = {}
        
        for curso, conteos in horario_generado.items():
            curso_norm = str(curso).strip().upper()
            proyeccion = self.proyecciones.get(curso_norm)
            
            if not proyeccion:
                violaciones[curso] = {
                    'error': 'Curso no encontrado en proyecciones',
                    'generado': conteos
                }
                continue
            
            # Comparar conteos
            dif_t = conteos.get('T', 0) - proyeccion['teoria']
            dif_p = conteos.get('P', 0) - proyeccion['practica']
            dif_l = conteos.get('L', 0) - proyeccion['laboratorio']
            
            if dif_t != 0 or dif_p != 0 or dif_l != 0:
                violaciones[curso] = {
                    'esperado': proyeccion,
                    'generado': conteos,
                    'diferencias': {
                        'teoria': dif_t,
                        'practica': dif_p,
                        'laboratorio': dif_l
                    }
                }
        
        is_valid = len(violaciones) == 0
        return is_valid, violaciones
    
    def imprimir_resumen(self):
        """Imprime resumen de proyecciones cargadas"""
        print("\n" + "="*70)
        print("PROYECCIONES CARGADAS DESDE LIBRO1.XLSX")
        print("="*70)
        
        total_t = 0
        total_p = 0
        total_l = 0
        
        for curso, proyeccion in sorted(self.proyecciones.items()):
            t = proyeccion['teoria']
            p = proyeccion['practica']
            l = proyeccion['laboratorio']
            total = proyeccion['total_secciones']
            
            total_t += t
            total_p += p
            total_l += l
            
            print(f"{curso[:40]:<40} | T:{t:2} P:{p:2} L:{l:2} | Total:{total:2}")
        
        print("="*70)
        print(f"{'TOTALES:':<40} | T:{total_t:2} P:{total_p:2} L:{total_l:2} | Total:{total_t+total_p+total_l:3}")
        print("="*70 + "\n")
    
    def guardar_como_json(self, output_path='proyecciones_libro1.json'):
        """Guarda proyecciones como JSON"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.proyecciones, f, indent=2, ensure_ascii=False)
        print(f"✅ Proyecciones guardadas en: {output_path}")


def main():
    """Test del módulo"""
    print("🔍 Cargando proyecciones desde Libro1.xlsx...")
    
    loader = ProyeccionesLoader()
    loader.imprimir_resumen()
    loader.guardar_como_json()
    
    # Ejemplos de uso
    print("\n📋 Ejemplos de consulta:")
    print("-" * 50)
    
    ejemplos = ['CALCULO II', 'BASE DE DATOS', 'FISICA I']
    for curso in ejemplos:
        proy = loader.obtener_proyeccion(curso)
        if proy:
            print(f"{curso}: {proy}")
    
    # Simular validación
    print("\n✅ Ejemplo de validación:")
    print("-" * 50)
    horario_simulado = {
        'CALCULO II': {'T': 3, 'P': 3, 'L': 0},  # ✓ Correcto
        'BASE DE DATOS': {'T': 2, 'P': 1, 'L': 6},  # ✗ Error en P
    }
    
    is_valid, violaciones = loader.validar_horario_contra_proyeccion(horario_simulado)
    if is_valid:
        print("✅ Horario cumple proyecciones")
    else:
        print("❌ Horario NO cumple proyecciones:")
        for curso, detalle in violaciones.items():
            print(f"  • {curso}: {detalle}")


if __name__ == '__main__':
    main()
