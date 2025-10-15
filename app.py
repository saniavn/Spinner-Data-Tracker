import sqlite3
import io
import csv
from flask import Flask, render_template, request, jsonify, Response
from collections import defaultdict

app = Flask(__name__)
DATABASE = 'database.db'

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
    return render_template('spinner_activity.html')

@app.route('/update_spin', methods=['POST'])
def update_spin():
    data = request.get_json()
    classroom_code = data.get('classroom_code')
    group_name = data.get('group_id')
    color = data.get('color')
    action = data.get('action')

    if not all([classroom_code, group_name, color, action]):
        return jsonify({'status': 'error', 'message': 'Missing data'}), 400

    conn = get_db_connection()
    if action == 'add':
        conn.execute(
            'INSERT INTO spins (classroom_code, group_name, color) VALUES (?, ?, ?)',
            (classroom_code, group_name, color)
        )
    elif action == 'remove':
        cursor = conn.cursor()
        cursor.execute(
            'DELETE FROM spins WHERE id = (SELECT id FROM spins WHERE classroom_code = ? AND group_name = ? AND color = ? ORDER BY timestamp DESC LIMIT 1)',
            (classroom_code, group_name, color)
        )
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

@app.route('/api/results')
def api_results():
    classroom_code = request.args.get('classroom_code')
    if not classroom_code:
        return jsonify({'status': 'error', 'message': 'Classroom code is required'}), 400

    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM spins WHERE classroom_code = ?', (classroom_code,)).fetchall()
    conn.close()

    # Step 1: Create a summary of results for each group
    summary = defaultdict(lambda: defaultdict(int))
    for row in rows:
        summary[row['group_name']][row['color']] += 1
    
    # Step 2: Group the summaries by their "signature" (the set of colors used)
    grouped_experiments = defaultdict(lambda: {'colors': set(), 'results': {}})
    for group_name, results in summary.items():
        if not results: continue
        signature = ",".join(sorted(results.keys()))
        grouped_experiments[signature]['results'][group_name] = results
        grouped_experiments[signature]['colors'].update(results.keys())

    # Step 3: Format the data for the frontend
    experiments_list = []
    for signature, data in grouped_experiments.items():
        experiments_list.append({
            'signature': signature,
            'colors': sorted(list(data['colors'])),
            'results': data['results']
        })

    return jsonify({'experiments': experiments_list})

@app.route('/dashboard/<classroom_code>')
def dashboard(classroom_code):
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

if __name__ == '__main__':
    init_db()
    app.run(debug=True)