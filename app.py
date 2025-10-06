from flask import Flask, render_template, request, jsonify
from collections import defaultdict
import datetime

app = Flask(__name__)

# This will store all the results from all groups (in memory)
all_group_results = []

@app.route('/')
def index():
    """Renders the main spinner activity page for students."""
    # The name of your HTML file is assumed to be 'spinner_activity.html'
    return render_template('spinner_activity.html')

@app.route('/update_spin', methods=['POST'])
def update_spin():
    """API endpoint to add or remove a single spin."""
    data = request.get_json()
    if not data or 'color' not in data or 'group_id' not in data or 'action' not in data:
        return jsonify({'status': 'error', 'message': 'Missing data'}), 400

    group_id = data.get('group_id')
    color = data.get('color')
    action = data.get('action')

    if action == 'add':
        print(f"Group {group_id} ADDED: {color}")
        all_group_results.append({'group_id': group_id, 'color': color, 'timestamp': datetime.datetime.now()})
        return jsonify({'status': 'success', 'message': 'Spin added!'})

    elif action == 'remove':
        # To 'remove' a spin, find the last entry for that group and color and pop it.
        # Iterate backwards to efficiently find the most recent one.
        for i in range(len(all_group_results) - 1, -1, -1):
            spin = all_group_results[i]
            # Ensure group_id is compared correctly (e.g., as strings)
            if str(spin['group_id']) == str(group_id) and spin['color'] == color:
                all_group_results.pop(i)
                print(f"Group {group_id} REMOVED: {color}")
                return jsonify({'status': 'success', 'message': 'Spin removed!'})

        # If no matching spin was found to remove
        return jsonify({'status': 'error', 'message': 'No matching spin found to remove'}), 404

    else:
        return jsonify({'status': 'error', 'message': 'Invalid action specified'}), 400

def process_results():
    """Processes the raw spin data into a summary. (No changes needed here)"""
    if not all_group_results:
        return None, 0

    summary = defaultdict(lambda: {'orange': 0, 'blue': 0, 'green': 0, 'yellow': 0})
    total_spins = len(all_group_results)

    for result in all_group_results:
        group_id = result['group_id']
        color = result['color']
        if color in summary[group_id]:
            summary[group_id][color] += 1

    return summary, total_spins

@app.route('/api/results')
def api_results():
    """Provides a JSON summary of all results. (No changes needed here)"""
    summary, total_spins = process_results()
    summary_dict = {k: dict(v) for k, v in summary.items()} if summary else {}
    return jsonify({'summary': summary_dict, 'total_spins': total_spins})

@app.route('/dashboard')
def dashboard():
    """Renders the teacher dashboard. (No changes needed here)"""
    summary, total_spins = process_results()
    summary_dict = {k: dict(v) for k, v in summary.items()} if summary else {}
    return render_template('dashboard.html', summary=summary_dict, total_spins=total_spins)


if __name__ == '__main__':
    app.run(debug=True)
