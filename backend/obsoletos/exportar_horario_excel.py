"""
Exporta el horario generado a formato Excel
URGENTE - Para presentación de tesis
"""
import sys
sys.path.insert(0, 'c:\\Users\\amaya\\Downloads\\10mo Ciclo\\TESIS\\upao-timetabling-aco-graphsage\\backend')

import pandas as pd
from app.database import SessionLocal
from app.models import CourseSection, Course, Professor, Classroom, TimeSlot
from sqlalchemy.orm import joinedload
from datetime import datetime
import json

def exportar_ultimo_horario():
    """Exporta el último horario generado a Excel"""
    
    print("="*80)
    print("EXPORTANDO HORARIO A EXCEL")
    print("="*80)
    
    # Buscar el archivo JSON más reciente
    import os
    import glob
    
    json_files = glob.glob("horario_generado_*.json")
    if not json_files:
        print("❌ ERROR: No se encontró ningún horario generado")
        print("   Busque archivos horario_generado_*.json")
        return
    
    # Ordenar por fecha de modificación (más reciente primero)
    json_files.sort(key=os.path.getmtime, reverse=True)
    latest_file = json_files[0]
    
    print(f"📄 Archivo encontrado: {latest_file}")
    
    # Cargar el JSON
    with open(latest_file, 'r', encoding='utf-8') as f:
        horario_data = json.load(f)
    
    # FIX: El JSON usa 'asignaciones' no 'assignments'
    asignaciones = horario_data.get('asignaciones', [])
    print(f"✅ Horario cargado: {len(asignaciones)} asignaciones")
    
    if not asignaciones:
        print("❌ ERROR: El archivo JSON no contiene asignaciones")
        print(f"   Keys en JSON: {list(horario_data.keys())}")
        return
    
    # Conectar a BD para obtener nombres
    db = SessionLocal()
    
    # Preparar datos para Excel
    rows = []
    for asig in asignaciones:
        section_id = asig['section_id']
        professor_id = asig['professor_id']
        classroom_id = asig.get('classroom_id')
        timeslot_ids = asig['timeslot_ids']
        
        # Obtener información de BD
        section = db.query(CourseSection).options(
            joinedload(CourseSection.course)
        ).filter_by(id=section_id).first()
        
        if not section:
            continue
        
        professor = db.query(Professor).filter_by(id=professor_id).first()
        
        if classroom_id and classroom_id != -1:
            classroom = db.query(Classroom).filter_by(id=classroom_id).first()
            aula_codigo = classroom.codigo if classroom else "Virtual"
        else:
            classroom = None
            aula_codigo = "Virtual"
        
        # Obtener información de timeslots
        timeslots = db.query(TimeSlot).filter(TimeSlot.id.in_(timeslot_ids)).order_by(TimeSlot.dia_semana, TimeSlot.hora_inicio).all()
        
        if not timeslots:
            continue
        
        # Mapeo de días
        dias_map = {
            1: "Lunes",
            2: "Martes", 
            3: "Miércoles",
            4: "Jueves",
            5: "Viernes",
            6: "Sábado"
        }
        
        dia = dias_map.get(timeslots[0].dia_semana, f"Día {timeslots[0].dia_semana}")
        
        # FIX: hora_inicio y hora_fin ya son strings en formato HH:MM:SS
        hora_inicio = str(timeslots[0].hora_inicio)[:5]  # Tomar solo HH:MM
        hora_fin = str(timeslots[-1].hora_fin)[:5]  # Tomar solo HH:MM
        
        row = {
            'ID Sección': section_id,
            'Curso': section.course.codigo if section.course else 'N/A',
            'Nombre Curso': section.course.nombre if section.course else 'N/A',
            'Tipo': section.tipo,
            'Sección': section.seccion,
            'League': section.league,
            'NRC': section.nrc,
            'Estudiantes': section.alumnos_proyectados,
            'Profesor': professor.nombre_completo if professor else 'N/A',
            'Aula': aula_codigo,
            'Capacidad Aula': classroom.capacidad if classroom else 0,
            'Día': dia,
            'Hora Inicio': hora_inicio,
            'Hora Fin': hora_fin,
            'Duración (bloques)': len(timeslot_ids),
            'Modalidad': section.course.modalidad if section.course else 'N/A',
        }
        
        rows.append(row)
    
    db.close()
    
    # Crear DataFrame
    df = pd.DataFrame(rows)
    
    # Ordenar por día, hora, curso
    orden_dias = {"Lunes": 1, "Martes": 2, "Miércoles": 3, "Jueves": 4, "Viernes": 5, "Sábado": 6}
    df['Orden Día'] = df['Día'].map(orden_dias)
    df = df.sort_values(['Orden Día', 'Hora Inicio', 'Curso', 'Sección'])
    df = df.drop('Orden Día', axis=1)
    
    # Generar nombre de archivo
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    excel_file = f"horario_UPAO_{timestamp}.xlsx"
    
    # Exportar a Excel con formato
    with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Horario Completo', index=False)
        
        # Obtener workbook y worksheet
        workbook = writer.book
        worksheet = writer.sheets['Horario Completo']
        
        # Ajustar anchos de columna
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
        
        # Crear hoja por día
        for dia in ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]:
            df_dia = df[df['Día'] == dia].copy()
            if not df_dia.empty:
                df_dia.to_excel(writer, sheet_name=dia, index=False)
                ws_dia = writer.sheets[dia]
                
                # Ajustar anchos
                for column in ws_dia.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    ws_dia.column_dimensions[column_letter].width = adjusted_width
    
    print(f"\n✅ HORARIO EXPORTADO EXITOSAMENTE")
    print(f"📊 Archivo: {excel_file}")
    print(f"📈 Total asignaciones: {len(rows)}")
    print(f"📚 Secciones únicas: {df['ID Sección'].nunique()}")
    print(f"👨‍🏫 Profesores únicos: {df['Profesor'].nunique()}")
    print(f"🏫 Aulas únicas: {df['Aula'].nunique()}")
    
    # Estadísticas por día
    print(f"\n📅 DISTRIBUCIÓN POR DÍA:")
    for dia in ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]:
        count = len(df[df['Día'] == dia])
        if count > 0:
            print(f"  {dia}: {count} clases")
    
    return excel_file

if __name__ == '__main__':
    try:
        archivo = exportar_ultimo_horario()
        print(f"\n🎉 ÉXITO - Horario listo para presentación")
        print(f"   Abrir: {archivo}")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
