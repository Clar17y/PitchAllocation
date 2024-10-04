from flask import Flask, request, jsonify, send_from_directory
from allocator.allocator_base import Allocator
from allocator.config_loader import load_pitches, load_teams
from allocator.logger import setup_logger


app = Flask(__name__)
logger = setup_logger(__name__)

# Load initial configurations
try:
    allocation_config = {'pitches': []} 
    pitches = load_pitches('data/pitches.json', allocation_config)
    teams = load_teams('data/teams.json')
except Exception as e:
    logger.error(f"Failed to load configurations: {e}")
    pitches = []
    teams = []

@app.route('/api/teams', methods=['GET'])
def get_teams():
    teams_data = []
    for team in teams:
        teams_data.append({
            'team_id': f"{team.name}-{'Girls' if team.is_girls else 'Boys'}",
            'display_name': team.format_label()
        })
    return jsonify({'teams': teams_data})

@app.route('/api/pitches', methods=['GET'])
def get_pitches():
    pitches_data = []
    for pitch in pitches:
        pitches_data.append({
            'code': pitch.code,
            'format_label': pitch.format_label()
        })
    return jsonify({'pitches': pitches_data})

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

    # Validate and process selected teams
    config = {
        'date': date,
        'start_time': start_time,
        'end_time': end_time,
        'pitches': selected_pitches,
        'home_teams': {}
    }

    for team_entry in selected_teams:
        team_id = team_entry.get('team_id', '').strip()
        preferred_time = team_entry.get('preferred_time', '').strip()

        if not team_id:
            logger.error("Missing 'team_id' in team_entry.")
            continue

        # Validate 'team_id' format
        if '-' not in team_id:
            logger.error(f"Invalid team_id format: '{team_id}'. Expected format 'TeamName-Girls' or 'TeamName-Boys'.")
            continue

        # Parse team_id
        try:
            name, gender = team_id.rsplit('-', 1)
            is_girls = gender.lower() == 'girls'
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

    # Load and validate allocation configuration
    try:
        allocator = Allocator(filtered_pitches, teams, config)
        allocator.allocate()
    except Exception as e:
        logger.error(f"Allocation process failed: {e}")
        return jsonify({
            'allocations': [],
            'logs': [{'level': 'error', 'message': 'Allocation process failed.'}]
        }), 500

    # Modify the allocations to include pitch capacity
    formatted_allocations = []
    for alloc in allocator.allocations:
        pitch = next((p for p in pitches if p.format_label() == alloc['pitch']), None)
        if pitch:
            formatted_allocations.append({
                'time': alloc['time'],
                'team': alloc['team'],
                'pitch': alloc['pitch'],
                'capacity': pitch.capacity  # Add this line
            })

    # Sort allocations by capacity and then by time
    formatted_allocations.sort(key=lambda x: (x['capacity'], x['time']))
    logger.info(f"Formatted allocations: {formatted_allocations}")
    logs = [{'level': 'info', 'message': 'Allocation completed successfully.'}]

    if allocator.unallocated_teams:
        unallocated = "\n".join([team.format_label() for team in allocator.unallocated_teams])
        logs.append({'level': 'warning', 'message': f'Unallocated Teams:\n{unallocated}'})

    return jsonify({'allocations': formatted_allocations, 'logs': logs})

@app.route('/', methods=['GET'])
def serve_index():
    return send_from_directory('frontend', 'index.html')

@app.route('/frontend/<path:filename>', methods=['GET'])
def serve_static(filename):
    return send_from_directory('frontend', filename)

if __name__ == '__main__':
    app.run(debug=True)