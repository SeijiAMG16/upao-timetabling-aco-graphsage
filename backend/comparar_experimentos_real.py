"""
Comparación de experimentos usando los JSON guardados
"""
import json
import glob
import os

print("="*100)
print("📊 EVOLUCIÓN DEL ALGORITMO ACO CON PROYECCIONES")
print("="*100)
print()

# Buscar todos los JSONs de experimentos
json_files = sorted(glob.glob("experimento_proy_*.json"))

if not json_files:
    print("❌ No se encontraron archivos experimento_proy_*.json")
    exit()

experimentos = []
for json_file in json_files:
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        # Extraer ID del nombre del archivo
        exp_id = int(json_file.replace("experimento_proy_", "").replace(".json", ""))
        data['id'] = exp_id
        experimentos.append(data)

# Ordenar por ID
experimentos.sort(key=lambda x: x['id'])

# Filtrar solo desde el experimento 27 en adelante
experimentos = [e for e in experimentos if e['id'] >= 27]

print(f"{'ID':<5} {'TPL%':<8} {'Proy%':<8} {'Asign':<10} {'Conflictos':<12} {'Violac.':<10} {'Tiempo':<10}")
print("-"*100)

for exp in experimentos:
    exp_id = exp['id']
    
    # Métricas
    metricas = exp.get('metricas', {})
    
    tpl_pct = metricas.get('porcentaje_tpl', 0)
    proy_pct = metricas.get('porcentaje_proyecciones', 0)
    
    total_asign = exp.get('total_asignaciones', 0)
    total_secc = exp.get('total_secciones_generadas', 298)
    
    conf_aula = metricas.get('conflictos_aula', 0)
    conf_prof = metricas.get('conflictos_profesor', 0)
    
    violaciones = metricas.get('total_violaciones_tpl', 0)
    
    # Calcular tiempo aproximado (no está en el JSON)
    tiempo = 0
    
    asign = f"{total_asign}/{total_secc}"
    conflictos = f"A:{conf_aula} P:{conf_prof}"
    
    print(f"{exp_id:<5} {tpl_pct:>6.1f}% {proy_pct:>6.1f}% {asign:<10} {conflictos:<12} {violaciones:<10} {tiempo:<10.2f}s")

print("="*100)
print()

# Calcular mejora
if len(experimentos) >= 2:
    primer_exp = experimentos[0]
    ultimo_exp = experimentos[-1]
    
    tpl_inicial = primer_exp['metricas']['porcentaje_tpl']
    tpl_final = ultimo_exp['metricas']['porcentaje_tpl']
    mejora = tpl_final - tpl_inicial
    
    print(f"📈 MEJORA TOTAL:")
    print(f"   • TPL Inicial (Exp {primer_exp['id']}): {tpl_inicial:.1f}%")
    print(f"   • TPL Final (Exp {ultimo_exp['id']}): {tpl_final:.1f}%")
    print(f"   • Mejora absoluta: +{mejora:.1f} puntos porcentuales")
    if tpl_inicial > 0:
        print(f"   • Mejora relativa: +{(mejora/tpl_inicial*100):.1f}%")
    print()

# Identificar mejor experimento
mejor_exp = max(experimentos, key=lambda x: x['metricas']['porcentaje_tpl'])
print(f"🏆 MEJOR EXPERIMENTO:")
print(f"   • ID: {mejor_exp['id']}")
print(f"   • TPL: {mejor_exp['metricas']['porcentaje_tpl']:.1f}%")
print(f"   • Proyecciones: {mejor_exp['metricas']['porcentaje_proyecciones']:.1f}%")
print(f"   • Asignaciones: {mejor_exp['total_asignaciones']}/{mejor_exp['total_secciones_generadas']}")
print(f"   • Violaciones: {mejor_exp['metricas']['total_violaciones_tpl']}")
print()

print("="*100)
print()
print("🔑 HITOS IMPORTANTES:")
print(f"   • Exp 27-29: Baseline inicial (8-18% TPL)")
print(f"   • Exp 32: Ordenamiento por CURSO (34.4% TPL) - Primera mejora significativa")
print(f"   • Exp 34: Context-aware scheduling (73.8% TPL) - Breakthrough principal")
print(f"   • Exp 35: Enhanced exploration (73.8% TPL) - Confirmación de límite estructural")
print("="*100)
