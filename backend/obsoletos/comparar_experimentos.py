"""
Comparación completa de experimentos: Evolución del algoritmo
"""
import mysql.connector

conn = mysql.connector.connect(
    host='localhost',
    user='root',
    password='sistemas',
    database='upao_timetabling'
)
cursor = conn.cursor(dictionary=True)

# Obtener todos los experimentos con proyecciones
cursor.execute("""
    SELECT 
        e.id,
        e.timestamp,
        e.tpl_valid_courses,
        e.tpl_total_courses,
        e.tpl_violations,
        e.projections_compliance_pct,
        e.classroom_conflicts,
        e.professor_conflicts,
        e.total_assignments,
        e.total_sections,
        e.execution_time_seconds
    FROM experiments e
    WHERE e.id >= 27
    ORDER BY e.id
""")

experiments = cursor.fetchall()
conn.close()

print("="*100)
print("📊 EVOLUCIÓN COMPLETA DEL ALGORITMO")
print("="*100)
print()

print(f"{'ID':<5} {'TPL%':<8} {'Proy%':<8} {'Asign':<10} {'Conflictos':<12} {'Violac.':<10} {'Tiempo':<10}")
print("-"*100)

for exp in experiments:
    exp_id = exp['id']
    tpl_pct = (exp['tpl_valid_courses'] / exp['tpl_total_courses'] * 100) if exp['tpl_total_courses'] > 0 else 0
    proy_pct = exp['projections_compliance_pct']
    asign = f"{exp['total_assignments']}/{exp['total_sections']}"
    conflictos = f"A:{exp['classroom_conflicts']} P:{exp['professor_conflicts']}"
    violaciones = exp['tpl_violations']
    tiempo = f"{exp['execution_time_seconds']:.2f}s"
    
    print(f"{exp_id:<5} {tpl_pct:>6.1f}% {proy_pct:>6.1f}% {asign:<10} {conflictos:<12} {violaciones:<10} {tiempo:<10}")

print("="*100)
print()

# Calcular mejora
primer_exp = experiments[0]
ultimo_exp = experiments[-1]

tpl_inicial = (primer_exp['tpl_valid_courses'] / primer_exp['tpl_total_courses'] * 100)
tpl_final = (ultimo_exp['tpl_valid_courses'] / ultimo_exp['tpl_total_courses'] * 100)

print("🎯 MEJORA TOTAL:")
print(f"   T→P→L: {tpl_inicial:.1f}% → {tpl_final:.1f}% (+{tpl_final - tpl_inicial:.1f} puntos)")
print(f"   Proyecciones: {primer_exp['projections_compliance_pct']:.1f}% → {ultimo_exp['projections_compliance_pct']:.1f}%")
print(f"   Asignaciones: {primer_exp['total_assignments']}/{primer_exp['total_sections']} → {ultimo_exp['total_assignments']}/{ultimo_exp['total_sections']}")
print(f"   Violaciones T→P→L: {primer_exp['tpl_violations']} → {ultimo_exp['tpl_violations']} ({primer_exp['tpl_violations'] - ultimo_exp['tpl_violations']} menos)")

print()
print("🏆 MEJOR EXPERIMENTO:")
mejor = max(experiments, key=lambda x: (x['tpl_valid_courses'] / x['tpl_total_courses'] * 100))
mejor_tpl = (mejor['tpl_valid_courses'] / mejor['tpl_total_courses'] * 100)
print(f"   ID: {mejor['id']}")
print(f"   T→P→L: {mejor_tpl:.1f}%")
print(f"   Violaciones: {mejor['tpl_violations']}")
print(f"   Asignaciones: {mejor['total_assignments']}/{mejor['total_sections']}")

print("="*100)
