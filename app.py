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

    summary = defaultdict(lambda: defaultdict(int))
    total_spins = len(rows)
    for row in rows:
        summary[row['group_name']][row['color']] += 1

    summary_dict = {k: dict(v) for k, v in summary.items()}
    return jsonify({'summary': summary_dict, 'total_spins': total_spins})

# API Endpoint to Delete Data
@app.route('/api/delete_class_data', methods=['POST'])
def delete_class_data():
    data = request.get_json()
    classroom_code = data.get('classroom_code')
    if not classroom_code:
        return jsonify({'status': 'error', 'message': 'Classroom code is required.'}), 400

    conn = get_db_connection()
    conn.execute('DELETE FROM spins WHERE classroom_code = ?', (classroom_code,))
    conn.commit()
    conn.close()

    print(f"DELETED all data for classroom: {classroom_code}")
    return jsonify({'status': 'success', 'message': 'All data for the class has been deleted.'})

# API Endpoint to Download Data
@app.route('/api/download_class_data/<classroom_code>')
def download_class_data(classroom_code):
    conn = get_db_connection()
    rows = conn.execute('SELECT group_name, color, timestamp FROM spins WHERE classroom_code = ? ORDER BY timestamp', (classroom_code,)).fetchall()
    conn.close()

    # Use a string stream to build the CSV in memory
    si = io.StringIO()
    cw = csv.writer(si)

    # Write header and rows
    cw.writerow(['group_name', 'color', 'timestamp'])
    cw.writerows(rows)

    output = si.getvalue()

    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename={classroom_code}_results.csv"}
    )

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
