from flask import Flask, request, jsonify, send_from_directory, render_template, redirect, url_for, flash
from flask_login import login_user, current_user, logout_user, login_required
from models import db, bcrypt, login_manager
from allocator.allocator_base import Allocator
from allocator.config_loader import load_pitches, load_teams, load_players, save_players
from allocator.logger import setup_logger
from models.pitch import Pitch
from models.team import Team
from models.player import Player
from models.user import User
from models.allocation import Allocation
from schemas import create_player_schema, create_players_schema, create_pitch_schema, create_pitches_schema, create_team_schema, create_teams_schema, create_allocation_schema, create_allocations_schema
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import ValidationError
from datetime import datetime

application = Flask(__name__)
application.config.from_object('config.Config')
logger = setup_logger(__name__)

# Initialize extensions
db.init_app(application)
bcrypt.init_app(application)
login_manager.init_app(application)

logger = setup_logger(__name__)

# Create database tables
with application.app_context():
    db.create_all()

# Routes for Authentication
@application.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('serve_index'))
    if request.method == 'POST':
        name = request.form.get('username')
        password = request.form.get('password')
        
        if not name or not password:
            flash('Please fill out both fields.', 'warning')
            return redirect(url_for('register'))
        
        existing_user = User.query.filter_by(name=name).first()
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'danger')
            return redirect(url_for('register'))
        
        new_user = User(name=name)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@application.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('serve_index'))
    if request.method == 'POST':
        name = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(name=name).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('serve_index'))
        else:
            flash('Login Unsuccessful. Please check username and password.', 'danger')
    
    return render_template('login.html')

@application.route('/api/current_user', methods=['GET'])
@login_required
def get_current_user():
    return jsonify({
        'id': current_user.id,
        'name': current_user.name
    }), 200

@application.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@application.route('/api/teams', methods=['GET'])
@login_required
def get_teams():
    try:
        teams = load_teams()
    except Exception as e:
        logger.error(f"Failed to load teams for user '{current_user.name}': {e}")
        return jsonify({'error': 'Failed to load teams.'}), 500

    teams_data = []
    for team in teams:
        teams_data.append({
            'id': team['id'],
            'name': team['name'],
            'age_group': team['age_group'],
            'is_girls': team['is_girls'],
            'display_name': team['display_label']
        })
    return jsonify({'teams': teams_data})

@application.route('/api/pitches', methods=['GET'])
@login_required
def get_pitches():
    try:
        pitches = load_pitches()
    except Exception as e:
        logger.error(f"Failed to load pitches for user '{current_user.name}': {e}")
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

@application.route('/api/players', methods=['GET'])
@login_required
def get_players():
    try:
        players = load_players()
    except Exception as e:
        logger.error(f"Failed to load players for user '{current_user.name}': {e}")
    
    players_data = []
    for player in players:
        players_data.append({
            'id': player['id'],
            'first_name': player['first_name'],
            'surname': player['surname'],
            'team_id': player['team_id'],
            'shirt_number': player['shirt_number']
        })
    return jsonify({'players': players_data})

@application.route('/api/allocate', methods=['POST'])
@login_required
def allocate():
    pitches = load_pitches()
    teams = load_teams()
    if not pitches or not teams:
        return jsonify({'allocations': [], 'logs': [{'level': 'error', 'message': 'Initialization failed. Pitches or teams data missing.'}]}), 500

    data = request.get_json()
    date = data.get('date')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    selected_pitches = data.get('pitches', [])
    selected_teams = data.get('teams', [])

    logger.info(f"Received allocation request for {current_user.name}.")
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
            team = next((t for t in teams if t['id'] == int(id)), None)
            if team:
                if team['age_group'] not in config['home_teams']:
                    config['home_teams'][team['age_group']] = []
                config['home_teams'][team['age_group']].append({
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
                'start_time': alloc['start_time'],
                'end_time': alloc['end_time'],
                'team': alloc['team'],
                'pitch': alloc['pitch'],
                'capacity': pitch.capacity,
                'preferred': alloc['preferred']
            })

    # Sort allocations by capacity and then by time
    formatted_allocations.sort(key=lambda x: (x['capacity'], datetime.strptime(x['start_time'], "%I:%M%p")))
    logger.info(f"Formatted allocations: {formatted_allocations}")
    logs = [{'level': 'info', 'message': 'Allocation completed successfully.'}]

    if allocator.unallocated_teams:
        unallocated = "\n".join([team.format_label() for team in allocator.unallocated_teams])
        logs.append({'level': 'warning', 'message': f'Unallocated Teams:\n{unallocated}'})

    return jsonify({'allocations': formatted_allocations, 'logs': logs})

@application.route('/', methods=['GET'])
@login_required
def serve_index():
    return send_from_directory('frontend', 'index.html')

@application.route('/frontend/<path:filename>', methods=['GET'])
@login_required
def serve_static(filename):
    return send_from_directory('frontend', filename)

@application.route('/api/statistics', methods=['GET'])
@login_required
def get_statistics():
    """
    Fetches all allocation results for the current user directly from the Allocation table
    and returns them as a list of allocation records.
    """
    try:
        username = current_user.name
        if not username:
            return jsonify({'error': 'User not authenticated.'}), 401

        # Fetch allocations directly from the Allocation table
        allocations = Allocation.query.join(User).filter(User.name == username).all()

        if not allocations:
            logger.info(f"No allocations found for user '{username}'.")
            return jsonify({'allocations': []}), 200

        # Serialize allocations using Marshmallow
        allocations_schema = create_allocations_schema()
        result = allocations_schema.dump(allocations)
        logger.info(f"Fetched {len(result)} allocation records for user '{username}'.")
        return jsonify({'allocations': result}), 200

    except Exception as e:
        logger.error(f"Failed to fetch statistics data: {e}")
        return jsonify({'error': 'Failed to fetch statistics data.'}), 500

@application.route('/api/config/pitches', methods=['GET', 'POST', 'PUT', 'DELETE'])
@login_required
def config_pitches():
    config_type = 'pitches'
    return handle_config(config_type)

@application.route('/api/config/teams', methods=['GET', 'POST', 'PUT', 'DELETE'])
@login_required
def config_teams():
    config_type = 'teams'
    return handle_config(config_type)

@application.route('/api/config/players', methods=['GET', 'POST', 'PUT', 'DELETE'])
@login_required
def config_players():
    config_type = 'players'
    return handle_config(config_type)

def handle_config(config_type):
    """
    Generic handler for configurations. Refactored into separate functions for clarity.
    """
    nonPluralConfigType = config_type[:-2] if config_type == "pitches" else config_type[:-1]
    # Sanitize config_type to prevent directory traversal or injection
    if config_type not in ['pitches', 'teams', 'players']:
        logger.error(f"Invalid config type: '{config_type}'")
        return jsonify({'error': 'Invalid config type.'}), 400

    player_schema = create_player_schema()
    players_schema = create_players_schema()
    pitch_schema = create_pitch_schema()
    pitches_schema = create_pitches_schema()
    team_schema = create_team_schema()
    teams_schema = create_teams_schema()
    if request.method == 'GET':
        if config_type == 'players':
            config_data = load_players()
            result = players_schema.dump(config_data)
        elif config_type == 'pitches':
            config_data = load_pitches()
            result = pitches_schema.dump(config_data)
        elif config_type == 'teams':
            config_data = load_teams()
            result = teams_schema.dump(config_data)
        return jsonify({config_type: result}), 200

    elif request.method in ['POST', 'PUT', 'DELETE']:
        payload = request.get_json()
        logger.info(f"Received payload: {payload}")
        if not payload and request.method != 'DELETE':
            logger.error("No data provided.")
            return jsonify({'error': 'No data provided.'}), 400

        # Load existing data
        try:
            if config_type == 'players':
                config_data = load_players()
            elif config_type == 'pitches':
                config_data = load_pitches()
            elif config_type == 'teams':
                config_data = load_teams()
        except Exception as e:
            logger.error(f"Failed to load {config_type}: {e}")
            config_data = []

        # Serialize existing data
        if config_type == 'players':
            config_list = players_schema.dump(config_data)
        elif config_type == 'pitches':
            config_list = pitches_schema.dump(config_data)
        elif config_type == 'teams':
            config_list = teams_schema.dump(config_data)

        # Define maximum items and unique fields based on config_type
        if config_type == 'pitches':
            max_items = 40
        elif config_type == 'teams':
            max_items = 100
        elif config_type == 'players':
            max_items = 1000 

        if request.method == 'POST':
            if len(config_list) >= max_items:
                logger.warning(f"Maximum number of {config_type} reached.")
                return jsonify({'error': f'Maximum number of {config_type} ({max_items}) reached.'}), 400

            # Deserialize new item
            if config_type == 'players':
                try:
                    new_item = player_schema.load(payload)
                except ValidationError as err:
                    return jsonify(err.messages), 400
            elif config_type == 'pitches':
                try:
                    new_item = pitch_schema.load(payload)
                except ValidationError as err:
                    return jsonify(err.messages), 400
            elif config_type == 'teams':
                try:
                    new_item = team_schema.load(payload)
                except ValidationError as err:
                    return jsonify(err.messages), 400

            # Additional unique constraints and validations can be added here

            # Save to DB
            try:
                db.session.add(new_item)
                db.session.commit()
                logger.info(f"Created new {nonPluralConfigType} with ID {new_item.id}.")
                result = pitch_schema.dump(new_item) if config_type == 'pitches' else (
                            team_schema.dump(new_item) if config_type == 'teams' else
                            player_schema.dump(new_item))
                return jsonify({nonPluralConfigType: result}), 201
            except SQLAlchemyError as e:
                db.session.rollback()
                logger.error(f"Database error while creating {config_type}: {e}")
                return jsonify({'error': 'Database error occurred.'}), 500

        elif request.method == 'PUT':
            item_id = payload.get('id')
            if not item_id:
                logger.error("ID not provided for update.")
                return jsonify({'error': 'ID is required for update.'}), 400

            # Find the item
            item = None
            if config_type == 'players':
                item = Player.query.filter_by(id=item_id, user_id=current_user.id).first()
            elif config_type == 'pitches':
                item = Pitch.query.filter_by(id=item_id, user_id=current_user.id).first()
            elif config_type == 'teams':
                item = Team.query.filter_by(id=item_id, user_id=current_user.id).first()

            if not item:
                logger.error(f"{nonPluralConfigType.capitalize()} not found.")
                return jsonify({'error': f'{nonPluralConfigType.capitalize()} not found.'}), 404

            # Update the item
            try:
                payload_without_id = {k: v for k, v in payload.items() if k != 'id'}
                if config_type == 'players':
                    updated_item = player_schema.load(payload_without_id, partial=True)
                elif config_type == 'pitches':
                    updated_item = pitch_schema.load(payload_without_id, partial=True)
                elif config_type == 'teams':
                    updated_item = team_schema.load(payload_without_id, partial=True)

                # Update the existing item with new data
                for attr, value in updated_item.__dict__.items():
                    if attr != '_sa_instance_state':  # Skip SQLAlchemy internal attribute
                        setattr(item, attr, value)

                db.session.commit()
                logger.info(f"Updated {nonPluralConfigType} with ID {item_id}.")
                result = pitch_schema.dump(updated_item) if config_type == 'pitches' else (
                            team_schema.dump(updated_item) if config_type == 'teams' else
                            player_schema.dump(updated_item))
                return jsonify({nonPluralConfigType: result}), 200
            except ValidationError as err:
                return jsonify(err.messages), 400
            except SQLAlchemyError as e:
                db.session.rollback()
                logger.error(f"Database error while updating {config_type}: {e}")
                return jsonify({'error': 'Database error occurred.'}), 500

        elif request.method == 'DELETE':
            item_id = request.args.get('id')
            if not item_id:
                logger.error("ID not provided for deletion.")
                return jsonify({'error': 'ID is required for deletion.'}), 400

            # Find and delete the item
            try:
                if config_type == 'players':
                    item = Player.query.filter_by(id=item_id, user_id=current_user.id).first()
                elif config_type == 'pitches':
                    item = Pitch.query.filter_by(id=item_id, user_id=current_user.id).first()
                elif config_type == 'teams':
                    item = Team.query.filter_by(id=item_id, user_id=current_user.id).first()

                logger.info(f"Item to delete: {item}")
                if not item:
                    logger.error(f"{nonPluralConfigType.capitalize()} not found for deletion.")
                    return jsonify({'error': f'{nonPluralConfigType.capitalize()} not found.'}), 404

                db.session.delete(item)
                db.session.commit()
                logger.info(f"Deleted {nonPluralConfigType} with ID {item_id}.")
                return jsonify({'message': f'{nonPluralConfigType.capitalize()} deleted successfully.'}), 200
            except SQLAlchemyError as e:
                db.session.rollback()
                logger.error(f"Database error while deleting {config_type}: {e}")
                return jsonify({'error': 'Database error occurred.'}), 500

@application.route('/register.html')
def register_page():
    return render_template('register.html')

@application.route('/login.html')
def login_page():
    return render_template('login.html')

def generate_unique_id(items):
    """Generate a unique ID for a new item."""
    existing_ids = {item['id'] for item in items}
    new_id = 1
    while new_id in existing_ids:
        new_id += 1
    return new_id

if __name__ == '__main__':
    application.run(debug=True)