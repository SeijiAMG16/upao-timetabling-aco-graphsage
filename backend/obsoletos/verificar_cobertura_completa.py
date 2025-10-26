"""
Verificar cobertura completa del horario generado
Mostrar qué secciones NO fueron asignadas
"""
import json
import glob
from app.database import SessionLocal
from app.models import CourseSection, Course
from sqlalchemy.orm import joinedload

# Buscar el archivo JSON más reciente (ordenar por nombre completo)
json_files = glob.glob("horario_generado_*.json")
if not json_files:
    print("❌ ERROR: No se encontró ningún horario generado")
    exit(1)

# Ordenar por fecha en el nombre del archivo
latest_file = sorted(json_files)[-1]
print(f"📂 Usando archivo: {latest_file}")
print("="*80)

# Leer horario generado
with open(latest_file, 'r', encoding='utf-8') as f:
    horario_data = json.load(f)

asignaciones = horario_data.get('asignaciones', [])  # Clave correcta es 'asignaciones'

# Obtener section_ids asignados
section_ids_asignados = set()
for asig in asignaciones:
    section_ids_asignados.add(asig['section_id'])

print(f"\n📊 RESUMEN:")
print(f"   • Total asignaciones: {len(asignaciones)}")
print(f"   • Secciones únicas asignadas: {len(section_ids_asignados)}")

# Conectar a BD y obtener todas las secciones activas
db = SessionLocal()

todas_secciones = db.query(CourseSection).options(
    joinedload(CourseSection.course)
).filter(CourseSection.activa == True).all()

print(f"   • Total secciones activas en BD: {len(todas_secciones)}")

# Identificar secciones NO asignadas
secciones_no_asignadas = []
for seccion in todas_secciones:
    if seccion.id not in section_ids_asignados:
        secciones_no_asignadas.append(seccion)

print(f"   • Secciones SIN asignar: {len(secciones_no_asignadas)}")
print(f"\n📈 Cobertura: {len(section_ids_asignados)}/{len(todas_secciones)} = {(len(section_ids_asignados)/len(todas_secciones)*100):.1f}%")

if secciones_no_asignadas:
    print("\n" + "="*80)
    print("❌ SECCIONES NO ASIGNADAS:")
    print("="*80)
    
    # Agrupar por curso
    por_curso = {}
    for seccion in secciones_no_asignadas:
        curso_codigo = seccion.course.codigo if seccion.course else "SIN_CURSO"
        curso_nombre = seccion.course.nombre if seccion.course else "Sin nombre"
        
        if curso_codigo not in por_curso:
            por_curso[curso_codigo] = {
                'nombre': curso_nombre,
                'secciones': []
            }
        
        por_curso[curso_codigo]['secciones'].append({
            'id': seccion.id,
            'tipo': seccion.tipo,
            'seccion': seccion.seccion,  # Puede ser string como "T1", "P1", etc.
            'league': int(seccion.league) if seccion.league else 0,
            'nrc': seccion.nrc,
            'alumnos': seccion.alumnos_proyectados or 0
        })
    
    # Mostrar ordenado
    for curso_codigo in sorted(por_curso.keys()):
        info = por_curso[curso_codigo]
        print(f"\n📚 {curso_codigo} - {info['nombre']}")
        print(f"   Secciones no asignadas: {len(info['secciones'])}")
        
        for sec in sorted(info['secciones'], key=lambda x: (x['tipo'], x['seccion'])):
            nrc_str = str(sec['nrc']) if sec['nrc'] else 'N/A'
            print(f"      • ID:{sec['id']:4d} | {sec['tipo']:6s} | Sec:{str(sec['seccion']):3s} | Liga:{sec['league']:2d} | NRC:{nrc_str:5s} | {sec['alumnos']:3d} alumnos")
    
    print("\n" + "="*80)
    print("📊 ESTADÍSTICAS POR TIPO:")
    print("="*80)
    
    tipos_count = {}
    for seccion in secciones_no_asignadas:
        tipo = seccion.tipo
        if tipo not in tipos_count:
            tipos_count[tipo] = 0
        tipos_count[tipo] += 1
    
    for tipo, count in sorted(tipos_count.items()):
        print(f"   • {tipo:12s}: {count:3d} secciones")
    
    print("\n" + "="*80)
    print("📊 ESTADÍSTICAS POR LIGA:")
    print("="*80)
    
    ligas_count = {}
    for seccion in secciones_no_asignadas:
        liga = seccion.league
        if liga not in ligas_count:
            ligas_count[liga] = 0
        ligas_count[liga] += 1
    
    for liga, count in sorted(ligas_count.items()):
        print(f"   • Liga {liga:2d}: {count:3d} secciones")

else:
    print("\n" + "="*80)
    print("✅ ¡PERFECTO! Todas las secciones activas fueron asignadas")
    print("="*80)

db.close()
