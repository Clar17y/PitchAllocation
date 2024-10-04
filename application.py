import json
import os
from flask import Flask, request, jsonify, send_from_directory
from allocator.allocator_base import Allocator
from allocator.config_loader import load_pitches, load_teams, save_json_to_s3, get_config_key, get_default_config_key
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
                        logger.warning(f"Skipping malformed line in file '{file_path['Key']}': {line}")
                        continue
                    time, team, capacity,pitch, preferred_str = parts
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
    nonPluralConfigType = "pitch" if config_type == "pitches" else "team"
    # Sanitize config_type to prevent directory traversal or injection
    if config_type not in ['pitches', 'teams']:
        logger.error(f"Invalid config type: '{config_type}'")
        return jsonify({'error': 'Invalid config type.'}), 400

    username = request.cookies.get('username')
    if not username:
        logger.error("Username not found in cookies.")
        return jsonify({'error': 'Username is required.'}), 400

    user_key = get_config_key(config_type, username)
    default_key = get_default_config_key(config_type)
    logger.info(f"User config key: {user_key}")
    logger.info(f"Default config key: {default_key}")

    if request.method == 'GET':
        try:
            config_data = load_pitches(username=username) if config_type == 'pitches' else load_teams(username=username)
            # Serialize using to_dict to exclude 'matches'
            serialized_data = [item.to_dict() for item in config_data] if config_type == 'pitches' else [item.__dict__ for item in config_data]
            return jsonify({config_type: serialized_data}), 200
        except FileNotFoundError:
            return jsonify({'error': f'Default {config_type} config not found.'}), 404
        except Exception as e:
            logger.error(f"Error loading {config_type}: {e}")
            return jsonify({'error': 'Failed to load configuration.'}), 500

    elif request.method in ['POST', 'PUT', 'DELETE']:
        try:
            payload = request.get_json()
            logger.info(f"Received payload: {payload}")
            if not payload and request.method != 'DELETE':
                logger.error("No data provided.")
                return jsonify({'error': 'No data provided.'}), 400

            # Load existing data
            try:
                config_data = load_pitches(username=username) if config_type == 'pitches' else load_teams(username=username)
            except FileNotFoundError:
                # Load default config if user config doesn't exist
                try:
                    config_data = load_pitches() if config_type == 'pitches' else load_teams()
                except FileNotFoundError:
                    config_data = [] if config_type == 'pitches' else []

            # Convert to a mutable type (list of dicts)
            config_list = [item.to_dict() for item in config_data] if config_type == 'pitches' else [item.__dict__ for item in config_data]

            if config_type == 'pitches':
                max_items = 40
                unique_fields = ['capacity', 'name']
            else:
                max_items = 100
                unique_fields = ['name', 'age_group', 'gender']

            if request.method == 'POST':
                if len(config_list) >= max_items:
                    logger.warning(f"Maximum number of {config_type} reached.")
                    return jsonify({'error': f'Maximum number of {config_type} ({max_items}) reached.'}), 400

                # Create new item
                new_id = generate_unique_id(config_list)
                new_item = {**payload, 'id': new_id}

                # Validate uniqueness
                if any(all(item[field] == new_item[field] for field in unique_fields) for item in config_list):
                    logger.warning(f"Duplicate {nonPluralConfigType} detected.")
                    return jsonify({'error': f'A {nonPluralConfigType} with the same {", ".join(unique_fields)} already exists.'}), 400

                # Additional validations can be added here (e.g., input lengths, allowed characters)

                config_list.append(new_item)
                logger.info(f"Created new {nonPluralConfigType} with ID {new_id}.")

            elif request.method == 'PUT':
                item_id = payload.get('id')
                if not item_id:
                    logger.error("ID not provided for update.")
                    return jsonify({'error': 'ID is required for update.'}), 400

                for item in config_list:
                    if item['id'] == item_id:
                        # Update fields, excluding 'matches' if present
                        updated_item = {**item, **payload}
                        # Remove 'matches' if it's part of the payload mistakenly
                        updated_item.pop('matches', None)
                        item.update(updated_item)
                        logger.info(f"Updated {nonPluralConfigType} with ID {item_id}.")
                        break
                else:
                    logger.error(f"{nonPluralConfigType.capitalize()} not found.")
                    return jsonify({'error': f'{nonPluralConfigType.capitalize()} not found.'}), 404

            elif request.method == 'DELETE':
                item_id = request.args.get('id')
                if not item_id:
                    logger.error("ID not provided for deletion.")
                    return jsonify({'error': 'ID is required for deletion.'}), 400

                original_length = len(config_list)
                config_list = [item for item in config_list if item['id'] != int(item_id)]
                if len(config_list) < original_length:
                    logger.info(f"Deleted {nonPluralConfigType} with ID {item_id}.")
                else:
                    logger.error(f"{nonPluralConfigType.capitalize()} not found for deletion.")
                    return jsonify({'error': f'{nonPluralConfigType.capitalize()} not found.'}), 404

            # Save updated config back to S3
            # Use to_dict to exclude 'matches' for pitches
            if config_type == 'pitches':
                serializable_config = [Pitch(**item).to_dict() for item in config_list]
            else:
                serializable_config = config_list

            save_json_to_s3(user_key, {config_type: serializable_config})
            response_msg = f'{config_type.capitalize()} saved successfully.'
            response_data = {'message': response_msg}

            if request.method == 'POST':
                response_data[nonPluralConfigType] = new_item

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