"""
API Flask para visualización de horarios
"""
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import mysql.connector
from datetime import datetime, time
import json

app = Flask(__name__)
CORS(app)

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'sistemas',
    'database': 'upao_timetabling'
}

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/experimentos')
def get_experimentos():
    """Lista todos los experimentos ACO"""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT 
            id,
            algoritmo,
            funcion_objetivo as fitness,
            tiempo_ejecucion,
            parametros,
            iniciado_en as created_at,
            (SELECT COUNT(*) FROM proposed_schedule_assignments 
             WHERE source = CONCAT('ACO_GEN_', algorithm_executions.id)) as total_horarios
        FROM algorithm_executions
        WHERE algoritmo LIKE 'ACO%'
        ORDER BY id DESC
        LIMIT 20
    """)
    
    experimentos = cursor.fetchall()
    
    # Convertir datetime a string
    for exp in experimentos:
        if exp['created_at']:
            exp['created_at'] = exp['created_at'].strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.close()
    conn.close()
    
    return jsonify(experimentos)

@app.route('/api/profesores')
def get_profesores():
    """Lista todos los profesores"""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT 
            id,
            nombre_completo,
            email,
            (SELECT COUNT(*) FROM proposed_schedule_assignments 
             WHERE professor_id = professors.id 
             AND source LIKE 'ACO_GEN_%') as total_asignaciones
        FROM professors
        ORDER BY nombre_completo
    """)
    
    profesores = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return jsonify(profesores)

@app.route('/api/horario/<int:experiment_id>')
def get_horario_experimento(experiment_id):
    """Obtiene todos los horarios de un experimento"""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT 
            psa.id,
            psa.nrc,
            c.nombre as curso,
            c.codigo as curso_codigo,
            p.nombre_completo as profesor,
            p.id as profesor_id,
            psa.day as dia,
            psa.start_time as hora_inicio,
            psa.end_time as hora_fin,
            psa.session_type as tipo_sesion,
            cl.codigo as aula,
            cl.tipo as tipo_aula,
            cl.capacidad
        FROM proposed_schedule_assignments psa
        JOIN professors p ON psa.professor_id = p.id
        JOIN courses c ON psa.course_id = c.id
        LEFT JOIN classrooms cl ON psa.classroom_id = cl.id
        WHERE psa.source = %s
        ORDER BY p.nombre_completo, psa.day, psa.start_time
    """, (f'ACO_GEN_{experiment_id}',))
    
    horarios = cursor.fetchall()
    
    # Convertir time objects a strings
    for h in horarios:
        if isinstance(h['hora_inicio'], time):
            h['hora_inicio'] = h['hora_inicio'].strftime('%H:%M:%S')
        if isinstance(h['hora_fin'], time):
            h['hora_fin'] = h['hora_fin'].strftime('%H:%M:%S')
    
    cursor.close()
    conn.close()
    
    return jsonify(horarios)

@app.route('/api/horario_profesor/<int:experiment_id>/<int:profesor_id>')
def get_horario_profesor(experiment_id, profesor_id):
    """Obtiene el horario de un profesor específico en un experimento"""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT 
            psa.id,
            psa.nrc,
            c.nombre as curso,
            c.codigo as curso_codigo,
            p.nombre_completo as profesor,
            psa.day as dia,
            psa.start_time as hora_inicio,
            psa.end_time as hora_fin,
            psa.session_type as tipo_sesion,
            cl.codigo as aula,
            cl.tipo as tipo_aula,
            cl.capacidad
        FROM proposed_schedule_assignments psa
        JOIN professors p ON psa.professor_id = p.id
        JOIN courses c ON psa.course_id = c.id
        LEFT JOIN classrooms cl ON psa.classroom_id = cl.id
        WHERE psa.source = %s
        AND psa.professor_id = %s
        ORDER BY psa.day, psa.start_time
    """, (f'ACO_GEN_{experiment_id}', profesor_id))
    
    horarios = cursor.fetchall()
    
    # Convertir time objects a strings
    for h in horarios:
        if isinstance(h['hora_inicio'], time):
            h['hora_inicio'] = h['hora_inicio'].strftime('%H:%M:%S')
        if isinstance(h['hora_fin'], time):
            h['hora_fin'] = h['hora_fin'].strftime('%H:%M:%S')
    
    # Obtener restricciones del profesor
    cursor.execute("""
        SELECT day, start_time, end_time
        FROM professor_restrictions
        WHERE professor_id = %s
    """, (profesor_id,))
    
    restricciones = cursor.fetchall()
    for r in restricciones:
        if isinstance(r['start_time'], time):
            r['start_time'] = r['start_time'].strftime('%H:%M:%S')
        if isinstance(r['end_time'], time):
            r['end_time'] = r['end_time'].strftime('%H:%M:%S')
    
    cursor.close()
    conn.close()
    
    return jsonify({
        'horarios': horarios,
        'restricciones': restricciones
    })

@app.route('/api/conflictos/<int:experiment_id>')
def get_conflictos(experiment_id):
    """Detecta conflictos en un experimento"""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    # Conflictos de aula (misma aula, mismo horario)
    cursor.execute("""
        SELECT 
            psa1.id as id1,
            psa2.id as id2,
            psa1.day as dia,
            psa1.start_time as hora_inicio,
            psa1.end_time as hora_fin,
            cl.codigo as aula,
            c1.nombre as curso1,
            c2.nombre as curso2,
            p1.nombre_completo as profesor1,
            p2.nombre_completo as profesor2,
            'AULA' as tipo_conflicto
        FROM proposed_schedule_assignments psa1
        JOIN proposed_schedule_assignments psa2 
            ON psa1.classroom_id = psa2.classroom_id
            AND psa1.day = psa2.day
            AND psa1.start_time = psa2.start_time
            AND psa1.id < psa2.id
        JOIN classrooms cl ON psa1.classroom_id = cl.id
        JOIN courses c1 ON psa1.course_id = c1.id
        JOIN courses c2 ON psa2.course_id = c2.id
        JOIN professors p1 ON psa1.professor_id = p1.id
        JOIN professors p2 ON psa2.professor_id = p2.id
        WHERE psa1.source = %s
        AND psa2.source = %s
    """, (f'ACO_GEN_{experiment_id}', f'ACO_GEN_{experiment_id}'))
    
    conflictos_aula = cursor.fetchall()
    
    # Conflictos de profesor (mismo profesor, mismo horario)
    cursor.execute("""
        SELECT 
            psa1.id as id1,
            psa2.id as id2,
            psa1.day as dia,
            psa1.start_time as hora_inicio,
            psa1.end_time as hora_fin,
            p1.nombre_completo as profesor,
            c1.nombre as curso1,
            c2.nombre as curso2,
            cl1.codigo as aula1,
            cl2.codigo as aula2,
            'PROFESOR' as tipo_conflicto
        FROM proposed_schedule_assignments psa1
        JOIN proposed_schedule_assignments psa2 
            ON psa1.professor_id = psa2.professor_id
            AND psa1.day = psa2.day
            AND psa1.start_time = psa2.start_time
            AND psa1.id < psa2.id
        JOIN professors p1 ON psa1.professor_id = p1.id
        JOIN courses c1 ON psa1.course_id = c1.id
        JOIN courses c2 ON psa2.course_id = c2.id
        LEFT JOIN classrooms cl1 ON psa1.classroom_id = cl1.id
        LEFT JOIN classrooms cl2 ON psa2.classroom_id = cl2.id
        WHERE psa1.source = %s
        AND psa2.source = %s
    """, (f'ACO_GEN_{experiment_id}', f'ACO_GEN_{experiment_id}'))
    
    conflictos_profesor = cursor.fetchall()
    
    # Convertir time objects
    for c in conflictos_aula + conflictos_profesor:
        if isinstance(c.get('hora_inicio'), time):
            c['hora_inicio'] = c['hora_inicio'].strftime('%H:%M:%S')
        if isinstance(c.get('hora_fin'), time):
            c['hora_fin'] = c['hora_fin'].strftime('%H:%M:%S')
    
    cursor.close()
    conn.close()
    
    return jsonify({
        'conflictos_aula': conflictos_aula,
        'conflictos_profesor': conflictos_profesor,
        'total': len(conflictos_aula) + len(conflictos_profesor)
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
