# app.py
from flask import Flask, request, jsonify, render_template
from allocator.config_loader import load_pitches, load_teams, load_allocation_config
from allocator.allocator_base import Allocator
import os
from allocator.logger import setup_logger

app = Flask(__name__, static_folder='static', template_folder='templates')
logger = setup_logger(__name__)

# Load initial data
try:
    allocation_config = {'pitches': []}
    pitches = load_pitches('data/pitches.yml', allocation_config)
    teams = load_teams('data/teams.yml')
    logger.info("Initial data loaded successfully.")
except Exception as e:
    logger.error(f"Error loading initial data: {e}")
    pitches = []
    teams = []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/pitches', methods=['GET'])
def get_pitches():
    if not pitches:
        return jsonify({'pitches': []}), 500
    pitch_list = [{
        'name': pitch.name,
        'code': pitch.code,
        'location': pitch.location,
        'capacity': pitch.capacity,
        'cost': pitch.cost if hasattr(pitch, 'cost') else 0,
        'overlaps_with': pitch.overlaps_with
    } for pitch in pitches]
    return jsonify({'pitches': pitch_list})

@app.route('/api/teams', methods=['GET'])
def get_teams():
    if not teams:
        return jsonify({'teams': []}), 500
    team_list = [{
        'id': f"{team.name}-girls" if team.is_girls else f"{team.name}-boys",
        'name': team.name,
        'age_group': team.age_group,
        'is_girls': team.is_girls,
        'label': team.format_label()
    } for team in teams]
    return jsonify({'teams': team_list})

@app.route('/api/allocate', methods=['POST'])
def allocate():
    if not pitches or not teams:
        return jsonify({'allocations': [], 'logs': [{'level': 'error', 'message': 'Initialization failed. Pitches or teams data missing.'}]}), 500

    data = request.get_json()
    date = data.get('date')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    selected_pitches = data.get('pitches', [])
    selected_teams = data.get('teams', [])

    logger.info("Received allocation request.")
    logger.debug(f"Allocation data: {data}")

    # Filter pitches based on selection
    filtered_pitches = [pitch for pitch in pitches if pitch.code in selected_pitches]
    if not filtered_pitches:
        logger.error("No pitches selected or available.")
        return jsonify({
            'allocations': [],
            'logs': [{'level': 'error', 'message': 'No pitches selected or available.'}]
        }), 400

    # Map team IDs back to Team objects
    selected_team_objs = []
    for team_entry in selected_teams:
        team_id = team_entry.get('team_id')
        preferred_time = team_entry.get('preferred_time')

        if team_id:
            team_id = team_id.strip()  # Remove any leading/trailing whitespace
        else:
            logger.error("Missing 'team_id' in team_entry.")
            continue

        # Validate 'team_id' format
        if '-' not in team_id:
            logger.error(f"Invalid team_id format: '{team_id}'. Expected format 'TeamName-girls' or 'TeamName-boys'.")
            continue

        # Proceed with existing logic
        try:
            name, gender = team_id.rsplit('-', 1)
            is_girls = gender.lower() == 'girls'
            team = next((t for t in teams if t.name == name and t.is_girls == is_girls), None)
            if team:
                selected_team_objs.append(team)
            else:
                logger.warning(f"Team with ID '{team_id}' not found.")
        except ValueError:
            logger.error(f"Invalid team_id format: '{team_id}'.")

    if not selected_team_objs:
        logger.error("No valid teams selected.")
        return jsonify({
            'allocations': [],
            'logs': [{'level': 'error', 'message': 'No valid teams selected.'}]
        }), 400

    # Create allocation payload
    config = {
        'date': date,
        'start_time': start_time,
        'end_time': end_time,
        'pitches': selected_pitches,
        'home_teams': {}
    }

    for team_entry in selected_teams:
        team_id = team_entry.get('team_id')
        preferred_time = team_entry.get('preferred_time')

        if team_id:
            team_id = team_id.strip()
        else:
            logger.error("Missing 'team_id' in team_entry.")
            continue

        try:
            name, gender = team_id.rsplit('-', 1)
            is_girls = gender.lower() == 'girls'
            name = name.strip()
            team = next((t for t in teams if t.name == name and t.is_girls == is_girls), None)
            if team:
                if team.age_group not in config['home_teams']:
                    config['home_teams'][team.age_group] = []
                config['home_teams'][team.age_group].append({
                    'team_id': team_id,  # Ensure 'team_id' is passed correctly
                    'preferred_time': preferred_time
                })
            else:
                logger.error(f"Team with ID '{team_id}' not found.")
        except ValueError:
            logger.error(f"Invalid team_id format: '{team_id}'.")

    allocator = Allocator(filtered_pitches, selected_team_objs, config)
    try:
        allocator.allocate()
    except Exception as e:
        logger.error(f"Allocation process failed: {e}")
        return jsonify({
            'allocations': [],
            'logs': [{'level': 'error', 'message': 'Allocation process failed.'}]
        }), 500

    # Prepare allocations and logs for response
    allocations = allocator.allocations
    logs = [{'level': 'info', 'message': 'Allocation completed successfully.'}]

    if allocator.unallocated_teams:
        unallocated = "\n".join([team.format_label() for team in allocator.unallocated_teams])
        logs.append({'level': 'warning', 'message': f'Unallocated Teams:\n{unallocated}'})

    return jsonify({'allocations': allocations, 'logs': logs})

if __name__ == '__main__':
    # Ensure the output directory exists
    os.makedirs('output', exist_ok=True)
    app.run(debug=True)