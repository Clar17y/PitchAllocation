import yaml
from allocator.models.pitch import Pitch
from allocator.models.team import Team
from allocator.logger import setup_logger

logger = setup_logger(__name__)

def load_yaml(file_path):
    """Load YAML file."""
    with open(file_path, 'r') as f:
        return yaml.safe_load(f)

def load_pitches(pitches_file, allocation_config):
    """Load only the pitches specified in the allocation configuration."""
    all_pitches_data = load_yaml(pitches_file)
    all_pitches = {p['name']: Pitch(**p) for p in all_pitches_data['pitches']}

    allowed_pitch_labels = set(allocation_config['pitches'])
    filtered_pitches = []
    for pitch in all_pitches.values():
        if pitch.format_label() in allowed_pitch_labels:
            filtered_pitches.append(pitch)
        else:
            logger.debug(f"Pitch {pitch.name} ({pitch.format_label()}) not in allowed pitches.")
    
    logger.info(f"Loaded {len(filtered_pitches)} pitches as specified in the allocation configuration.")
    return filtered_pitches

def load_teams(teams_file):
    """Load teams from YAML file."""
    teams_data = load_yaml(teams_file)
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
    config = load_yaml(allocation_file)
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