import json
import os
from flask import Flask, request, jsonify, send_from_directory
from allocator.allocator_base import Allocator
from allocator.config_loader import load_pitches, load_teams
from allocator.logger import setup_logger
from allocator.models.pitch import Pitch
from allocator.models.team import Team
from datetime import datetime
import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
import re

application = Flask(__name__)
logger = setup_logger(__name__)

# Let's use S3 for storage
s3 = boto3.client('s3')
BUCKET_NAME = 'owpitchalloc'

@application.route('/api/teams', methods=['GET'])
def get_teams():
    username = request.args.get('username')
    if not username:
        logger.error("Username not provided in query parameters.")
        return jsonify({'error': 'Username is required.'}), 400
    
    try:
        teams = load_teams(username=username)
    except Exception as e:
        logger.error(f"Failed to load teams for user '{username}': {e}")
        return jsonify({'error': 'Failed to load teams.'}), 500

    teams_data = []
    for team in teams:
        teams_data.append({
            'id': team.id,
            'name': team.name,
            'age_group': team.age_group,
            'gender': team.gender,
            'display_name': team.format_label()
        })
    return jsonify({'teams': teams_data})

@application.route('/api/pitches', methods=['GET'])
def get_pitches():
    username = request.args.get('username')
    if not username:
        logger.error("Username not provided in query parameters.")
        return jsonify({'error': 'Username is required.'}), 400
    
    try:
        pitches = load_pitches(username=username)
    except Exception as e:
        logger.error(f"Failed to load pitches for user '{username}': {e}")
        return jsonify({'error': 'Failed to load pitches.'}), 500

    pitches_data = []
    for pitch in pitches:
        pitches_data.append({
            'id': pitch.id,
            'name': pitch.name,
            'capacity': pitch.capacity,
            'location': pitch.location,
            'cost': pitch.cost,
            'overlaps_with': pitch.overlaps_with,
            'format_label': pitch.format_label()
        })
    return jsonify({'pitches': pitches_data})

@application.route('/api/allocate', methods=['POST'])
def allocate():
    # Retrieve username from cookies
    username = request.cookies.get('username')
    if not username:
        logger.error("Username not found in cookies.")
        return jsonify({'allocations': [], 'logs': [{'level': 'error', 'message': 'User not authenticated.'}]}), 401

    pitches = load_pitches(username=username)
    teams = load_teams(username=username)
    if not pitches or not teams:
        return jsonify({'allocations': [], 'logs': [{'level': 'error', 'message': 'Initialization failed. Pitches or teams data missing.'}]}), 500

    data = request.get_json()
    date = data.get('date')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    selected_pitches = data.get('pitches', [])
    selected_teams = data.get('teams', [])

    logger.info(f"Received allocation request for {username}.")
    logger.debug(f"Allocation data: {data}")

    # Filter pitches based on selection
    selected_pitches = [int(pitch) for pitch in selected_pitches]
    filtered_pitches = [pitch for pitch in pitches if pitch.id in selected_pitches]
    if not filtered_pitches:
        logger.error("No pitches selected or available.")
        return jsonify({
            'allocations': [],
            'logs': [{'level': 'error', 'message': 'No pitches selected or available.'}]
        }), 400
    
    if not selected_teams:
        logger.error("No teams selected or available.")
        return jsonify({
            'allocations': [],
            'logs': [{'level': 'error', 'message': 'No teams selected or available.'}]
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
        preferred_time = team_entry.get('preferred_time', '').strip()

        try:
            id = team_entry['id']
            team = next((t for t in teams if t.id == int(id)), None)
            if team:
                if team.age_group not in config['home_teams']:
                    config['home_teams'][team.age_group] = []
                config['home_teams'][team.age_group].append({
                    'id': id,
                    'preferred_time': preferred_time
                })
            else:
                logger.error(f"Team with ID '{id}' not found.")
        except ValueError:
            logger.error(f"Invalid team id: '{id}'.")

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
                'capacity': pitch.capacity,
                'preferred': alloc['preferred']
            })

    # Sort allocations by capacity and then by time
    formatted_allocations.sort(key=lambda x: (x['capacity'], datetime.strptime(x['time'], "%I:%M%p")))
    logger.info(f"Formatted allocations: {formatted_allocations}")
    logs = [{'level': 'info', 'message': 'Allocation completed successfully.'}]

    if allocator.unallocated_teams:
        unallocated = "\n".join([team.format_label() for team in allocator.unallocated_teams])
        logs.append({'level': 'warning', 'message': f'Unallocated Teams:\n{unallocated}'})

    # Save Allocation Results to Output folder
    save_allocation_results(username, date, formatted_allocations)

    return jsonify({'allocations': formatted_allocations, 'logs': logs})


def save_allocation_results(username, date_str, allocations):
    """
    Saves the allocation results to a file in the Output directory.
    Each user's allocations are stored in separate files identified by their username and date.
    """
    try:
        # Sanitize the username to prevent directory traversal or injection
        if not re.match(r'^[a-zA-Z0-9]+$', username):
            logger.error(f"Invalid username format: '{username}'. Allocations not saved.")
            return

        # Parse the date string to ensure it's valid
        allocation_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        s3_filename = f"allocations/{username}/{allocation_date}.txt"

        # Format the allocations as Allocation Results
        if not allocations:
            result_text = "No allocations available."
        else:
            result_text = ""
            current_capacity = None

            for alloc in allocations:
                if alloc['capacity'] != current_capacity:
                    if current_capacity is not None:
                        result_text += '\n'  # Add an empty line between capacity groups
                    current_capacity = alloc['capacity']
                preferred_str = 'True' if alloc['preferred'] else 'False'
                result_text += f"{alloc['time']} - {alloc['team']} - {alloc['pitch']} - {preferred_str}\n"

            result_text = result_text.strip()

        try:
            s3.put_object(Bucket=BUCKET_NAME, Key=s3_filename, Body=result_text)
            logger.info(f"Allocation results saved to S3 bucket '{BUCKET_NAME}' with key '{s3_filename}'.")
        except (NoCredentialsError, PartialCredentialsError) as e:
            logger.error(f"Failed to save allocation results to S3: {e}")
    except Exception as e:
        logger.error(f"Failed to save allocation results for user '{username}': {e}")

@application.route('/', methods=['GET'])
def serve_index():
    return send_from_directory('frontend', 'index.html')

@application.route('/frontend/<path:filename>', methods=['GET'])
def serve_static(filename):
    return send_from_directory('frontend', filename)

@application.route('/api/statistics', methods=['GET'])
def get_statistics():
    """
    Fetches all allocation results for the current user from the Output directory
    and returns them as a list of allocation records.
    """
    allocations = []
    try:
        # Retrieve username from cookies
        username = request.cookies.get('username')
        if not username:
            logger.error("Username not found in cookies.")
            return jsonify({'error': 'User not authenticated.'}), 401

        logger.debug(f"Retrieved username from cookies: '{username}'")

        # Sanitize the username to prevent directory traversal or injection
        if not re.match(r'^[a-zA-Z0-9]+$', username):
            logger.error(f"Invalid username format: '{username}'.")
            return jsonify({'error': 'Invalid username format.'}), 400

        response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=f"allocations/{username}/")
        user_files = response.get('Contents', [])

        logger.debug(f"Found {len(user_files)} files for user '{username}'.")

        if not user_files:
            logger.info(f"No allocations found for user '{username}'.")
            return jsonify({'allocations': []})

        for file_path in user_files:
            date_str = file_path['Key'].split('/')[-1].split('.')[0]  # Extract date from filename
            try:
                response = s3.get_object(Bucket=BUCKET_NAME, Key=file_path['Key'])
                content = response['Body'].read().decode('utf-8')
                if content == "No allocations available.":
                    continue
                for line in content.split('\n'):
                    parts = line.split(' - ')
                    if len(parts) != 5:
                        logger.warning(f"Skipping malformed line in file '{file_path}': {line}")
                        continue
                    time, team, capacity, pitch, preferred_str = parts
                    allocations.append({
                        'date': date_str,
                        'time': time.strip(),
                        'team': team.strip(),
                        'pitch': pitch.strip(),
                        'preferred': preferred_str.lower() == 'true'
                    })
            except Exception as e:
                logger.info(f"Error getting file from s3: {e}")

        logger.info(f"Fetched statistics data successfully for user '{username}'. Total allocations: {len(allocations)}.")
    except Exception as e:
        logger.error(f"Failed to fetch statistics data: {e}")
        return jsonify({'error': 'Failed to fetch statistics data.'}), 500

    return jsonify({'allocations': allocations})

@application.route('/api/config/<config_type>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def config_handler(config_type):
    if config_type not in ['pitches', 'teams']:
        logger.error(f"Invalid config type: '{config_type}'")
        return jsonify({'error': 'Invalid config type.'}), 400

    username = request.cookies.get('username')
    if not username:
        logger.error("Username not found in cookies.")
        return jsonify({'error': 'Username is required.'}), 400

    user_filename = f'{config_type}_{username}.json'
    default_filename = f'{config_type}.json'
    user_file_path = os.path.join('data', user_filename)
    default_file_path = os.path.join('data', default_filename)
    logger.info(f"User file path: {user_file_path}")
    logger.info(f"Default file path: {default_file_path}")

    if request.method == 'GET':
        if os.path.exists(user_file_path):
            with open(user_file_path, 'r') as f:
                data = json.load(f)
            return jsonify({config_type: data[config_type]}), 200
        else:
            # Return default config
            if not os.path.exists(default_file_path):
                return jsonify({'error': 'Default config not found.'}), 404
            with open(default_file_path, 'r') as f:
                data = json.load(f)
            return jsonify({config_type: data[config_type]}), 200

    elif request.method in ['POST', 'PUT', 'DELETE']:
        try:
            payload = request.get_json()
            if not payload and request.method != 'DELETE':
                logger.error("No data provided.")
                return jsonify({'error': 'No data provided.'}), 400

            # Load existing data or initialize
            if os.path.exists(user_file_path):
                with open(user_file_path, 'r') as f:
                    data = json.load(f)
            else:
                # Load default data if user file doesn't exist
                if os.path.exists(default_file_path):
                    with open(default_file_path, 'r') as f:
                        data = json.load(f)
                else:
                    data = {config_type: []}

            if config_type == 'pitches':
                items = data[config_type]
                if request.method == 'POST':
                    if len(items) >= 40:
                        logger.warning("Maximum number of pitches reached.")
                        return jsonify({'error': 'Maximum number of pitches (40) reached.'}), 400
                    # Create new pitch
                    new_pitch = {
                        'id': generate_unique_id(items),
                        'name': payload['name'],
                        'capacity': payload['capacity'],
                        'location': payload['location'],
                        'cost': payload.get('cost', 0),
                        'overlaps_with': payload.get('overlaps_with', [])
                    }

                    # Generate format_label
                    new_format_label = Pitch(**new_pitch).format_label()

                    # Check for duplicate format_label
                    if any(Pitch(**item).format_label() == new_format_label for item in items):
                        logger.warning("Duplicate pitch format_label detected.")
                        return jsonify({'error': 'A pitch with the same capacity and location already exists.'}), 400

                    # Validate input lengths
                    if len(new_pitch['name']) > 50 or len(new_pitch['location']) > 100:
                        logger.warning("Pitch name or location exceeds maximum length.")
                        return jsonify({'error': 'Pitch name or location exceeds maximum allowed length.'}), 400

                    # Validate allowed characters
                    if not all(c.isalnum() or c in [' ', '-', '_'] for c in new_pitch['name']):
                        logger.warning("Pitch name contains invalid characters.")
                        return jsonify({'error': 'Pitch name contains invalid characters.'}), 400

                    if not all(c.isalnum() or c in [' ', '-', '_'] for c in new_pitch['location']):
                        logger.warning("Pitch location contains invalid characters.")
                        return jsonify({'error': 'Pitch location contains invalid characters.'}), 400
                    data[config_type].append(new_pitch)
                elif request.method == 'PUT':
                    pitch_id = int(payload.get('id', 0))
                    # Update existing pitch
                    for pitch in items:
                        if pitch['id'] == pitch_id:
                            # Generate new format_label
                            updated_format_label = Pitch(**payload).format_label()

                            # Check for duplicate format_label excluding current pitch
                            if any(Pitch(**item).format_label() == updated_format_label and item['id'] != pitch_id for item in items):
                                logger.warning("Duplicate pitch format_label detected during update.")
                                return jsonify({'error': 'A pitch with the same capacity and location already exists.'}), 400

                            # Validate input lengths
                            if len(payload['name']) > 50 or len(payload['location']) > 100:
                                logger.warning("Pitch name or location exceeds maximum length during update.")
                                return jsonify({'error': 'Pitch name or location exceeds maximum allowed length.'}), 400

                            # Validate allowed characters
                            if not all(c.isalnum() or c in [' ', '-', '_', '(', ')'] for c in payload['name']):
                                logger.warning("Pitch name contains invalid characters during update.")
                                return jsonify({'error': 'Pitch name contains invalid characters.'}), 400

                            if not all(c.isalnum() or c in [' ', '-', '_', '(', ')'] for c in payload['location']):
                                logger.warning("Pitch location contains invalid characters during update.")
                                return jsonify({'error': 'Pitch location contains invalid characters.'}), 400
                            
                            #update pitch
                            pitch['name'] = payload['name']
                            pitch['capacity'] = payload['capacity']
                            pitch['location'] = payload['location']
                            pitch['cost'] = payload.get('cost', 0)
                            pitch['overlaps_with'] = payload.get('overlaps_with', [])
                            break
                    else:
                        logger.error("Pitch not found.")
                        return jsonify({'error': 'Pitch not found.'}), 404
                elif request.method == 'DELETE':
                    # Delete existing pitch
                    id_to_delete = int(request.args.get('id', 0))
                    for pitch in items:
                        if pitch['id'] == id_to_delete:
                            items.remove(pitch)
                            logger.info(f"Deleted pitch ID {id_to_delete}: {pitch['name']}")
                            break
                    else:
                        return jsonify({'error': 'Pitch not found.'}), 404

            elif config_type == 'teams':
                items = data[config_type]
                if request.method == 'POST':
                    if len(items) >= 100:
                        logger.warning("Maximum number of teams reached.")
                        return jsonify({'error': 'Maximum number of teams (100) reached.'}), 400
                    
                    # Create new team
                    new_team = {
                        'id': generate_unique_id(items),
                        'name': payload['name'],
                        'age_group': payload['age_group'],
                        'gender': payload['gender']
                    }

                    # Generate format_label
                    new_format_label = Team(**new_team).format_label()

                    # Check for duplicate format_label
                    if any(Team(**item).format_label() == new_format_label for item in items):
                        logger.warning("Duplicate team format_label detected.")
                        return jsonify({'error': 'A team with the same name, age group, and gender already exists.'}), 400

                    # Validate input lengths
                    if len(new_team['name']) > 50 or len(new_team['age_group']) > 20 or len(new_team['gender']) > 10:
                        logger.warning("Team name, age group, or gender exceeds maximum length.")
                        return jsonify({'error': 'Team name, age group, or gender exceeds maximum allowed length.'}), 400

                    # Validate allowed characters
                    if not all(c.isalnum() or c in [' ', '-', '_', '(', ')'] for c in new_team['name']):
                        logger.warning("Team name contains invalid characters.")
                        return jsonify({'error': 'Team name contains invalid characters.'}), 400

                    if not all(c.isalnum() or c in [' ', '-', '_', '(', ')'] for c in new_team['age_group']):
                        logger.warning("Team age group contains invalid characters.")
                        return jsonify({'error': 'Team age group contains invalid characters.'}), 400

                    if not all(c.isalnum() or c in [' ', '-', '_', '(', ')'] for c in new_team['gender']):
                        logger.warning("Team gender contains invalid characters.")
                        return jsonify({'error': 'Team gender contains invalid characters.'}), 400

                    items.append(new_team)
                    logger.info(f"Created new team: {new_team['name']} with ID {new_team['id']}")
                elif request.method == 'PUT':
                    # Update existing team
                    team_id = int(payload.get('id', 0))
                    for team in items:
                        if team['id'] == team_id:
                            # Generate new format_label
                            updated_format_label = Team(**payload).format_label()

                            # Check for duplicate format_label excluding current team
                            if any(Team(**item).format_label() == updated_format_label and item['id'] != team_id for item in items):
                                logger.warning("Duplicate team format_label detected during update.")
                                return jsonify({'error': 'A team with the same name, age group, and gender already exists.'}), 400

                            # Validate input lengths
                            if len(payload['name']) > 50 or len(payload['age_group']) > 20 or len(payload['gender']) > 10:
                                logger.warning("Team name, age group, or gender exceeds maximum length during update.")
                                return jsonify({'error': 'Team name, age group, or gender exceeds maximum allowed length.'}), 400

                            # Validate allowed characters
                            if not all(c.isalnum() or c in [' ', '-', '_' '(', ')'] for c in payload['name']):
                                logger.warning("Team name contains invalid characters during update.")
                                return jsonify({'error': 'Team name contains invalid characters.'}), 400

                            if not all(c.isalnum() or c in [' ', '-', '_' '(', ')'] for c in payload['age_group']):
                                logger.warning("Team age group contains invalid characters during update.")
                                return jsonify({'error': 'Team age group contains invalid characters.'}), 400

                            if not all(c.isalnum() or c in [' ', '-', '_' '(', ')'] for c in payload['gender']):
                                logger.warning("Team gender contains invalid characters during update.")
                                return jsonify({'error': 'Team gender contains invalid characters.'}), 400
                            
                            team['name'] = payload['name']
                            team['age_group'] = payload['age_group']
                            team['gender'] = payload['gender']
                            logger.info(f"Updated team ID {team_id}")
                            break
                    else:
                        logger.error("Team not found.")
                        return jsonify({'error': 'Team not found.'}), 404
                elif request.method == 'DELETE':
                    # Delete existing team
                    id_to_delete = int(request.args.get('id', 0))
                    for team in items:
                        if team['id'] == id_to_delete:
                            items.remove(team)
                            logger.info(f"Deleted team ID {id_to_delete}: {team['name']}")
                            break
                    else:
                        return jsonify({'error': 'Team not found.'}), 404

            # Save to user-specific file
            with open(user_file_path, 'w') as f:
                json.dump({config_type: data[config_type]}, f, indent=4)

            response_data = {'message': f'{config_type.capitalize()} saved successfully.'}
            if request.method == 'POST' and config_type == 'pitches':
                response_data['pitch'] = new_pitch
            elif request.method == 'POST' and config_type == 'teams':
                response_data['team'] = new_team

            return jsonify(response_data), 200

        except Exception as e:
            logger.error(f"Error handling {config_type} config: {str(e)}")
            return jsonify({'error': 'Internal server error.'}), 500

def generate_unique_id(items):
    """Generate a unique ID for a new item."""
    existing_ids = {item['id'] for item in items}
    new_id = 1
    while new_id in existing_ids:
        new_id += 1
    return new_id

if __name__ == '__main__':
    application.run(debug=True)