import sqlite3
import io
import csv
from flask import Flask, render_template, request, jsonify, Response
from collections import defaultdict

app = Flask(__name__)
DATABASE = 'database.db'

CURRENT_CLASSROOM = "DEFAULT_SESSION" 

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS spins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            classroom_code TEXT NOT NULL,
            group_name TEXT NOT NULL,
            color TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    # Pass the current session ID to the template if needed, or just render
    return render_template('spinner_activity.html')

@app.route('/update_spin', methods=['POST'])
def update_spin():
    data = request.get_json()
    
    # WE CHANGED THIS: We now expect 'student_id' instead of group_id/class_code
    student_id = data.get('student_id') 
    color = data.get('color')
    action = data.get('action')

    # Use the hardcoded classroom code
    classroom_code = CURRENT_CLASSROOM

    if not all([student_id, color, action]):
        return jsonify({'status': 'error', 'message': 'Missing data'}), 400

    conn = get_db_connection()
    if action == 'add':
        # specific student_id is saved into the group_name column
        conn.execute(
            'INSERT INTO spins (classroom_code, group_name, color) VALUES (?, ?, ?)',
            (classroom_code, student_id, color)
        )
    elif action == 'remove':
        cursor = conn.cursor()
        cursor.execute(
            'DELETE FROM spins WHERE id = (SELECT id FROM spins WHERE classroom_code = ? AND group_name = ? AND color = ? ORDER BY timestamp DESC LIMIT 1)',
            (classroom_code, student_id, color)
        )
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

@app.route('/api/results')
def api_results():
    # ignore the request args and use our hardcoded session
    classroom_code = CURRENT_CLASSROOM

    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM spins WHERE classroom_code = ?', (classroom_code,)).fetchall()
    conn.close()

    #Create a summary of results for each Student ID (stored in group_name)
    summary = defaultdict(lambda: defaultdict(int))
    for row in rows:
        summary[row['group_name']][row['color']] += 1
    
    #Group the summaries
    grouped_experiments = defaultdict(lambda: {'colors': set(), 'results': {}})
    for student_id, results in summary.items():
        if not results: continue
        signature = ",".join(sorted(results.keys()))
        grouped_experiments[signature]['results'][student_id] = results
        grouped_experiments[signature]['colors'].update(results.keys())

  
    experiments_list = []
    for signature, data in grouped_experiments.items():
        experiments_list.append({
            'signature': signature,
            'colors': sorted(list(data['colors'])),
            'results': data['results']
        })

    return jsonify({'experiments': experiments_list})


@app.route('/api/add_manual_group', methods=['POST'])
def add_manual_group():
    data = request.get_json()
    
    classroom_code = CURRENT_CLASSROOM
    student_id = data.get('group_name') # Frontend sends ID as group_name
    results = data.get('results')

    if not all([student_id, results]):
        return jsonify({'status': 'error', 'message': 'Missing data'}), 400

    conn = get_db_connection()
    try:
        # Check if student ID exists
        existing = conn.execute(
            'SELECT 1 FROM spins WHERE classroom_code = ? AND group_name = ? LIMIT 1',
            (classroom_code, student_id)
        ).fetchone()
        
        if existing:
            return jsonify({'status': 'error', 'message': 'Student ID already exists in database'}), 409 

        # Insert spins
        for color, count in results.items():
            if count > 0:
                for _ in range(count):
                    conn.execute(
                        'INSERT INTO spins (classroom_code, group_name, color) VALUES (?, ?, ?)',
                        (classroom_code, student_id, color)
                    )
        
        conn.commit()
        return jsonify({'status': 'success', 'message': 'Student added successfully'})
    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        conn.close()

@app.route('/dashboard')
@app.route('/dashboard/<classroom_code>')
def dashboard(classroom_code=None):
    if not classroom_code:
        classroom_code = CURRENT_CLASSROOM

    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM spins WHERE classroom_code = ?', (classroom_code,)).fetchall()
    conn.close()

    summary = defaultdict(lambda: defaultdict(int))
    total_spins = len(rows)
    for row in rows:
        summary[row['group_name']][row['color']] += 1

    summary_dict = {k: dict(v) for k, v in summary.items()}

    return render_template('dashboard.html',
                           summary=summary_dict,
                           total_spins=total_spins,
                           classroom_name=classroom_code)

@app.route('/api/clear_spins', methods=['POST'])
def clear_spins():
    data = request.get_json()
    student_id = data.get('student_id') # Changed from group_id
    classroom_code = CURRENT_CLASSROOM

    if not student_id:
        return jsonify({'status': 'error', 'message': 'Missing Student ID'}), 400

    conn = get_db_connection()
    conn.execute(
        'DELETE FROM spins WHERE classroom_code = ? AND group_name = ?',
        (classroom_code, student_id)
    )
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'success', 'message': f'Data for student {student_id} cleared.'})

if __name__ == '__main__':
    init_db()
    app.run(debug=True)