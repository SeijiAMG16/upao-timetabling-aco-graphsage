"""
Excel Processor for UPAO Course Projections
Procesa el archivo Excel con las proyecciones de cursos para extraer información estructurada
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import re
from dataclasses import dataclass, asdict
import json
from pathlib import Path

@dataclass
class CourseProjection:
    """Estructura de datos para una proyección de curso"""
    codigo_curso: str
    nombre_curso: str
    ciclo: int
    modalidad: str  # PRS/NPR (Presencial/No Presencial)
    
    # Teoría
    alumnos_teoria: int
    grupos_teoria: int
    
    # Práctica
    alumnos_practica: int
    grupos_practica: int
    
    # Laboratorio
    alumnos_laboratorio: int
    grupos_laboratorio: int
    
    # Restricciones específicas
    requiere_laboratorio: bool
    requiere_practica: bool
    restricciones_especiales: Optional[str] = None

@dataclass
class TimeSlot:
    """Franja horaria UPAO"""
    id: int
    inicio: str
    fin: str
    periodo: str  # "mañana", "tarde", "noche"

class ExcelProcessor:
    """Procesador principal para archivos Excel de UPAO"""
    
    def __init__(self):
        self.franjas_horarias = self._create_time_slots()
        self.aulas_f = self._create_aulas_f()
        self.aulas_g = self._create_aulas_g()
        
    def _create_time_slots(self) -> List[TimeSlot]:
        """Crea las 16 franjas horarias de UPAO"""
        horarios = [
            ("07:00", "07:50"), ("07:55", "08:45"), ("08:50", "09:40"), ("09:45", "10:35"),
            ("10:40", "11:30"), ("11:35", "12:25"), ("12:30", "13:20"), ("13:25", "14:15"),
            ("14:20", "15:10"), ("15:15", "16:05"), ("16:10", "17:00"), ("17:05", "17:55"),
            ("18:00", "18:50"), ("18:55", "19:45"), ("19:50", "20:40"), ("20:45", "21:35")
        ]
        
        slots = []
        for i, (inicio, fin) in enumerate(horarios, 1):
            # Determinar período
            hora_inicio = int(inicio.split(':')[0])
            if hora_inicio < 12:
                periodo = "mañana"
            elif hora_inicio < 18:
                periodo = "tarde"
            else:
                periodo = "noche"
                
            slots.append(TimeSlot(
                id=i,
                inicio=inicio,
                fin=fin,
                periodo=periodo
            ))
        return slots
    
    def _create_aulas_f(self) -> List[Dict]:
        """Crea catálogo de aulas piso F (laboratorios ≤20 alumnos)"""
        aulas = []
        for piso in ['F2', 'F3', 'F4']:
            for num in range(1, 5):  # F201-F404
                aulas.append({
                    'codigo': f"{piso}0{num}",
                    'piso': piso,
                    'capacidad': 20,
                    'tipo': 'laboratorio',
                    'edificio': 'F'
                })
        return aulas
    
    def _create_aulas_g(self) -> List[Dict]:
        """Crea catálogo de aulas pisos G (sistemas G6-G8)"""
        aulas = []
        
        # Aulas teóricas G6-G8
        for piso in [6, 7, 8]:
            for num in range(1, 10):  # G601-G809
                aulas.append({
                    'codigo': f"G{piso}0{num}",
                    'piso': f"G{piso}",
                    'capacidad': 40 if num <= 5 else 30,  # Capacidades estimadas
                    'tipo': 'teorica',
                    'edificio': 'G'
                })
        
        # Laboratorios G (>20 alumnos)
        for piso in [6, 7, 8]:
            for num in range(10, 13):  # Labs especiales G610-G812
                aulas.append({
                    'codigo': f"G{piso}{num}",
                    'piso': f"G{piso}",
                    'capacidad': 30,
                    'tipo': 'laboratorio',
                    'edificio': 'G'
                })
        
        return aulas
    
    def analyze_excel_structure(self, file_path: str) -> Dict:
        """Analiza la estructura del Excel para entender las columnas"""
        try:
            # Leer todas las hojas
            excel_data = pd.read_excel(file_path, sheet_name=None, engine='openpyxl')
            
            analysis = {
                'sheets': list(excel_data.keys()),
                'sheet_analysis': {}
            }
            
            for sheet_name, df in excel_data.items():
                analysis['sheet_analysis'][sheet_name] = {
                    'rows': len(df),
                    'columns': len(df.columns),
                    'column_names': df.columns.tolist(),
                    'sample_data': df.head(3).to_dict('records') if len(df) > 0 else [],
                    'data_types': df.dtypes.to_dict()
                }
            
            return analysis
            
        except Exception as e:
            return {'error': f"Error analizando Excel: {str(e)}"}
    
    def process_projections_excel(self, file_path: str) -> Tuple[List[CourseProjection], Dict]:
        """Procesa el Excel de proyecciones y extrae información estructurada"""
        try:
            # Primero analizar estructura
            structure = self.analyze_excel_structure(file_path)
            
            # Leer la primera hoja (asumiendo que contiene los datos principales)
            df = pd.read_excel(file_path, sheet_name=0, engine='openpyxl')
            
            # Limpiar datos
            df = self._clean_dataframe(df)
            
            # Extraer proyecciones
            projections = self._extract_course_projections(df)
            
            # Generar estadísticas
            stats = self._generate_statistics(projections)
            
            return projections, {
                'structure_analysis': structure,
                'statistics': stats,
                'processed_courses': len(projections)
            }
            
        except Exception as e:
            return [], {'error': f"Error procesando Excel: {str(e)}"}
    
    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Limpia el DataFrame eliminando filas/columnas vacías"""
        # Eliminar filas completamente vacías
        df = df.dropna(how='all')
        
        # Eliminar columnas completamente vacías
        df = df.dropna(axis=1, how='all')
        
        # Convertir a string las columnas de texto para evitar problemas
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).replace('nan', '')
        
        return df
    
    def _extract_course_projections(self, df: pd.DataFrame) -> List[CourseProjection]:
        """Extrae proyecciones de cursos del DataFrame"""
        projections = []
        
        # Mapeo inteligente de columnas (adaptable a diferentes formatos)
        column_mapping = self._map_columns(df.columns.tolist())
        
        for index, row in df.iterrows():
            try:
                # Extraer información básica
                codigo = self._safe_extract(row, column_mapping.get('codigo_curso', ''))
                nombre = self._safe_extract(row, column_mapping.get('nombre_curso', ''))
                
                if not codigo or not nombre:
                    continue
                
                # Extraer ciclo del código o nombre
                ciclo = self._extract_ciclo(codigo, nombre)
                
                # Extraer modalidad
                modalidad = self._extract_modalidad(row, column_mapping)
                
                # Extraer números de alumnos y grupos
                alumnos_teoria = self._safe_int_extract(row, column_mapping.get('alumnos_teoria', ''))
                grupos_teoria = self._safe_int_extract(row, column_mapping.get('grupos_teoria', ''))
                
                alumnos_practica = self._safe_int_extract(row, column_mapping.get('alumnos_practica', ''))
                grupos_practica = self._safe_int_extract(row, column_mapping.get('grupos_practica', ''))
                
                alumnos_lab = self._safe_int_extract(row, column_mapping.get('alumnos_laboratorio', ''))
                grupos_lab = self._safe_int_extract(row, column_mapping.get('grupos_laboratorio', ''))
                
                # Determinar si requiere laboratorio/práctica
                requiere_lab = grupos_lab > 0 or alumnos_lab > 0
                requiere_practica = grupos_practica > 0 or alumnos_practica > 0
                
                projection = CourseProjection(
                    codigo_curso=codigo,
                    nombre_curso=nombre,
                    ciclo=ciclo,
                    modalidad=modalidad,
                    alumnos_teoria=alumnos_teoria,
                    grupos_teoria=grupos_teoria,
                    alumnos_practica=alumnos_practica,
                    grupos_practica=grupos_practica,
                    alumnos_laboratorio=alumnos_lab,
                    grupos_laboratorio=grupos_lab,
                    requiere_laboratorio=requiere_lab,
                    requiere_practica=requiere_practica
                )
                
                projections.append(projection)
                
            except Exception as e:
                print(f"Error procesando fila {index}: {e}")
                continue
        
        return projections
    
    def _map_columns(self, columns: List[str]) -> Dict[str, str]:
        """Mapea columnas del Excel a campos conocidos usando patrones"""
        mapping = {}
        
        patterns = {
            'codigo_curso': [r'.*c[oó]digo.*', r'.*code.*', r'.*curso.*id.*'],
            'nombre_curso': [r'.*nombre.*curso.*', r'.*course.*name.*', r'.*asignatura.*'],
            'modalidad': [r'.*modalidad.*', r'.*mode.*', r'.*presencial.*'],
            'alumnos_teoria': [r'.*alumn.*teor.*', r'.*student.*theory.*', r'.*est.*teor.*'],
            'grupos_teoria': [r'.*grupo.*teor.*', r'.*group.*theory.*', r'.*secc.*teor.*'],
            'alumnos_practica': [r'.*alumn.*pr[aá]ct.*', r'.*student.*pract.*', r'.*est.*pr[aá]ct.*'],
            'grupos_practica': [r'.*grupo.*pr[aá]ct.*', r'.*group.*pract.*', r'.*secc.*pr[aá]ct.*'],
            'alumnos_laboratorio': [r'.*alumn.*lab.*', r'.*student.*lab.*', r'.*est.*lab.*'],
            'grupos_laboratorio': [r'.*grupo.*lab.*', r'.*group.*lab.*', r'.*secc.*lab.*']
        }
        
        for field, patterns_list in patterns.items():
            for col in columns:
                for pattern in patterns_list:
                    if re.search(pattern, col.lower()):
                        mapping[field] = col
                        break
                if field in mapping:
                    break
        
        return mapping
    
    def _safe_extract(self, row: pd.Series, column: str) -> str:
        """Extrae valor de forma segura"""
        if not column or column not in row:
            return ""
        value = row[column]
        return str(value).strip() if pd.notna(value) else ""
    
    def _safe_int_extract(self, row: pd.Series, column: str) -> int:
        """Extrae entero de forma segura"""
        value = self._safe_extract(row, column)
        try:
            return int(float(value)) if value else 0
        except:
            return 0
    
    def _extract_ciclo(self, codigo: str, nombre: str) -> int:
        """Extrae el ciclo del código o nombre del curso"""
        # Buscar patrones como "I", "II", "III", etc. o números
        text = f"{codigo} {nombre}".upper()
        
        # Patrones romanos
        roman_patterns = {
            'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5,
            'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10
        }
        
        for roman, num in roman_patterns.items():
            if f" {roman} " in text or f"-{roman}-" in text or f"_{roman}_" in text:
                return num
        
        # Buscar números directos
        numbers = re.findall(r'\b([1-9]|10)\b', text)
        if numbers:
            return int(numbers[0])
        
        return 1  # Default
    
    def _extract_modalidad(self, row: pd.Series, mapping: Dict) -> str:
        """Extrae la modalidad (PRS/NPR)"""
        modalidad_col = mapping.get('modalidad', '')
        if modalidad_col:
            value = self._safe_extract(row, modalidad_col).upper()
            if 'PRS' in value or 'PRESENCIAL' in value:
                return 'PRS'
            elif 'NPR' in value or 'NO PRESENCIAL' in value:
                return 'NPR'
        
        return 'PRS'  # Default presencial
    
    def _generate_statistics(self, projections: List[CourseProjection]) -> Dict:
        """Genera estadísticas de las proyecciones"""
        if not projections:
            return {}
        
        total_courses = len(projections)
        total_students = sum(p.alumnos_teoria + p.alumnos_practica + p.alumnos_laboratorio for p in projections)
        total_theory_groups = sum(p.grupos_teoria for p in projections)
        total_practice_groups = sum(p.grupos_practica for p in projections)
        total_lab_groups = sum(p.grupos_laboratorio for p in projections)
        
        # Estadísticas por ciclo
        cycles_stats = {}
        modality_stats = {}
        
        for p in projections:
            # Por ciclo
            if p.ciclo not in cycles_stats:
                cycles_stats[p.ciclo] = {'courses': 0, 'students': 0, 'groups': 0}
            cycles_stats[p.ciclo]['courses'] += 1
            cycles_stats[p.ciclo]['students'] += p.alumnos_teoria + p.alumnos_practica + p.alumnos_laboratorio
            cycles_stats[p.ciclo]['groups'] += p.grupos_teoria + p.grupos_practica + p.grupos_laboratorio
            
            # Por modalidad
            if p.modalidad not in modality_stats:
                modality_stats[p.modalidad] = {'courses': 0, 'students': 0}
            modality_stats[p.modalidad]['courses'] += 1
            modality_stats[p.modalidad]['students'] += p.alumnos_teoria + p.alumnos_practica + p.alumnos_laboratorio
        
        return {
            'total_courses': total_courses,
            'total_students': total_students,
            'total_theory_groups': total_theory_groups,
            'total_practice_groups': total_practice_groups,
            'total_lab_groups': total_lab_groups,
            'cycles_distribution': cycles_stats,
            'modality_distribution': modality_stats,
            'courses_with_lab': len([p for p in projections if p.requiere_laboratorio]),
            'courses_with_practice': len([p for p in projections if p.requiere_practica]),
        }
    
    def export_processed_data(self, projections: List[CourseProjection], output_path: str):
        """Exporta los datos procesados a JSON"""
        data = {
            'projections': [asdict(p) for p in projections],
            'time_slots': [asdict(slot) for slot in self.franjas_horarias],
            'aulas_f': self.aulas_f,
            'aulas_g': self.aulas_g,
            'metadata': {
                'processed_at': pd.Timestamp.now().isoformat(),
                'total_courses': len(projections)
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

def main():
    """Función principal para probar el procesador"""
    processor = ExcelProcessor()
    
    # Procesar el archivo Excel
    excel_path = "../../inputs/Libro1.xlsx"
    projections, analysis = processor.process_projections_excel(excel_path)
    
    print(f"Procesadas {len(projections)} proyecciones de cursos")
    print("\nAnálisis:", json.dumps(analysis, indent=2, ensure_ascii=False))
    
    if projections:
        # Exportar datos procesados
        processor.export_processed_data(projections, "processed_projections.json")
        print("Datos exportados a processed_projections.json")

if __name__ == "__main__":
    main()