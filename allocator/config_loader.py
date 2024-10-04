# allocator/config_loader.py
import yaml
import os
from allocator.models.pitch import Pitch
from allocator.models.team import Team
from allocator.logger import setup_logger

logger = setup_logger(__name__)

# Determine the absolute path to the directory containing config_loader.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def load_yaml(file_path):
    """Load YAML file using absolute paths."""
    absolute_path = os.path.join(BASE_DIR, file_path)
    if not os.path.exists(absolute_path):
        logger.error(f"File not found: {absolute_path}")
        raise FileNotFoundError(f"File not found: {absolute_path}")
    with open(absolute_path, 'r') as f:
        return yaml.safe_load(f)

def load_pitches(pitches_file, allocation_config):
    """Load only the pitches specified in the allocation configuration.
    If allocation_config['pitches'] is empty, load all pitches."""
    # Adjust the path to move from allocator/ to base_directory/
    pitches_path = os.path.join('..', pitches_file)
    all_pitches_data = load_yaml(pitches_path)
    all_pitches = {Pitch(**pitch).format_label(): Pitch(**pitch) for pitch in all_pitches_data['pitches']}

    if allocation_config.get('pitches'):
        allowed_pitch_labels = set(allocation_config['pitches'])
    else:
        allowed_pitch_labels = set(all_pitches.keys())

    filtered_pitches = []
    for label in allowed_pitch_labels:
        pitch = all_pitches.get(label)
        if pitch:
            filtered_pitches.append(pitch)
        else:
            logger.warning(f"Pitch with label '{label}' not found in pitches.yml.")

    # Sort pitches by capacity: 5-aside, 7-aside, 9-aside, then 11-aside
    filtered_pitches.sort(key=lambda pitch: {5: 0, 7: 1, 9: 2, 11: 3}.get(pitch.capacity, 4))
    logger.info(f"Loaded {len(filtered_pitches)} pitches as specified in the allocation configuration.")
    return filtered_pitches

def load_teams(teams_file):
    """Load teams from YAML file."""
    teams_path = os.path.join('..', teams_file)
    teams_data = load_yaml(teams_path)
    teams = []
    for age, names in teams_data['teams'].items():
        if not names:
            logger.info(f"No teams under age group '{age}'. Skipping.")
            continue
        for name in names:
            is_girls = '(Girls)' in name
            clean_name = name.replace(' (Girls)', '')
            teams.append(Team(clean_name, age, is_girls))
    logger.info(f"Loaded {len(teams)} teams.")
    return teams

def load_allocation_config(allocation_file):
    """Load and validate allocation configuration."""
    allocation_path = os.path.join('..', allocation_file)
    config = load_yaml(allocation_path)
    validate_allocation_config(config)
    return config

def validate_allocation_config(config):
    """Validate the allocation configuration."""
    required_fields = ['date', 'start_time', 'end_time', 'pitches', 'home_teams']
    for field in required_fields:
        if field not in config:
            raise ValueError(f"Missing required field '{field}' in allocation configuration.")

    if not isinstance(config['pitches'], list):
        raise ValueError("Field 'pitches' should be a list.")

    if not isinstance(config['home_teams'], dict):
        raise ValueError("Field 'home_teams' should be a dictionary.")

    logger.info("Allocation configuration loaded and validated.")