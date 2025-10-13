"""
GENERADOR DE SLOTS DE TIEMPO CORRECTOS PARA UPAO
=================================================

Genera slots de 50 minutos según los bloques oficiales de UPAO
"""

# Bloques de tiempo oficiales UPAO (50 minutos cada uno)
BLOQUES_UPAO = [
    ("07:00:00", "07:50:00"),
    ("07:55:00", "08:45:00"),
    ("08:50:00", "09:40:00"),
    ("09:45:00", "10:35:00"),
    ("10:40:00", "11:30:00"),
    ("11:35:00", "12:25:00"),
    ("12:30:00", "01:20:00"),
    ("01:25:00", "02:15:00"),
    ("02:20:00", "03:10:00"),
    ("03:15:00", "04:05:00"),
    ("04:10:00", "05:00:00"),
    ("05:05:00", "05:55:00"),
    ("06:00:00", "06:50:00"),
    ("06:55:00", "07:45:00"),
    ("07:50:00", "08:40:00"),
    ("08:45:00", "09:35:00"),  # ← Límite presencial
    ("09:40:00", "10:30:00"),  # ← Solo cursos virtuales/NPR
]

DIAS_SEMANA = ['LUNES', 'MARTES', 'MIÉRCOLES', 'JUEVES', 'VIERNES', 'SÁBADO']

def generar_slots_upao(incluir_virtual=True):
    """
    Genera todos los slots de tiempo válidos según bloques UPAO
    
    Args:
        incluir_virtual: Si True, incluye bloque 9:40-10:30pm (solo NPR/virtual)
    
    Returns:
        Lista de tuplas (dia, hora_inicio, hora_fin)
    """
    slots = []
    
    limite_bloques = len(BLOQUES_UPAO) if incluir_virtual else len(BLOQUES_UPAO) - 1
    
    for dia in DIAS_SEMANA:
        for i in range(limite_bloques):
            h_inicio, h_fin = BLOQUES_UPAO[i]
            slots.append((dia, h_inicio, h_fin))
    
    return slots

def es_slot_virtual(hora_inicio):
    """Verifica si un slot es solo para cursos virtuales/NPR"""
    return hora_inicio >= "09:40:00"

def obtener_slots_para_sesion(duracion_horas=2, incluir_virtual=True):
    """
    Genera slots válidos para sesiones de N horas (bloques consecutivos)
    
    Args:
        duracion_horas: Duración en horas (2, 3, o 4)
        incluir_virtual: Si incluye bloques nocturnos tardíos
    
    Returns:
        Lista de tuplas (dia, hora_inicio, hora_fin_real)
    """
    # Calcular cuántos bloques necesitamos
    bloques_necesarios = int(duracion_horas * 60 / 50)  # 50 min por bloque
    
    slots_sesion = []
    limite = len(BLOQUES_UPAO) if incluir_virtual else len(BLOQUES_UPAO) - 1
    
    for dia in DIAS_SEMANA:
        # Intentar cada bloque como inicio
        for i in range(limite - bloques_necesarios + 1):
            h_inicio = BLOQUES_UPAO[i][0]
            h_fin = BLOQUES_UPAO[i + bloques_necesarios - 1][1]
            
            # Verificar que los bloques sean consecutivos (diferencia < 10 min)
            es_consecutivo = True
            for j in range(i, i + bloques_necesarios - 1):
                fin_actual = BLOQUES_UPAO[j][1]
                inicio_siguiente = BLOQUES_UPAO[j + 1][0]
                
                # Convertir a minutos para comparar
                from datetime import datetime
                t1 = datetime.strptime(fin_actual, "%H:%M:%S")
                t2 = datetime.strptime(inicio_siguiente, "%H:%M:%S")
                
                diff_minutos = (t2.hour * 60 + t2.minute) - (t1.hour * 60 + t1.minute)
                
                if diff_minutos > 10:  # No consecutivo
                    es_consecutivo = False
                    break
            
            if es_consecutivo:
                slots_sesion.append((dia, h_inicio, h_fin))
    
    return slots_sesion

# Generar slots estándar (2 horas = ~2 bloques)
SLOTS_2_HORAS = obtener_slots_para_sesion(2, incluir_virtual=False)
SLOTS_2_HORAS_VIRTUAL = obtener_slots_para_sesion(2, incluir_virtual=True)

if __name__ == '__main__':
    print("="*80)
    print("🕐 BLOQUES DE TIEMPO UPAO")
    print("="*80)
    
    print(f"\n📊 Total de bloques por día: {len(BLOQUES_UPAO)}")
    print(f"   • Presenciales (hasta 9:35pm): {len(BLOQUES_UPAO) - 1}")
    print(f"   • Virtual/NPR (hasta 10:30pm): {len(BLOQUES_UPAO)}")
    
    print(f"\n⏰ BLOQUES OFICIALES:")
    for i, (inicio, fin) in enumerate(BLOQUES_UPAO, 1):
        virtual = " (SOLO NPR/VIRTUAL)" if i == len(BLOQUES_UPAO) else ""
        print(f"   Bloque {i:2d}: {inicio} - {fin}{virtual}")
    
    print(f"\n📅 SLOTS DISPONIBLES PARA SESIONES DE 2 HORAS (presencial):")
    print(f"   • Total slots: {len(SLOTS_2_HORAS)}")
    print(f"   • Por día: {len(SLOTS_2_HORAS) // 6}")
    
    print(f"\n📋 Ejemplo - Slots del LUNES (2 horas):")
    slots_lunes = [s for s in SLOTS_2_HORAS if s[0] == 'LUNES']
    for slot in slots_lunes[:10]:
        dia, h_ini, h_fin = slot
        print(f"   {dia} {h_ini} - {h_fin}")
    
    print("\n" + "="*80)
