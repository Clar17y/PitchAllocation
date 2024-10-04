import json  # Import JSON library alongside YAML
import os
import re
import boto3
from botocore.exceptions import ClientError
from allocator.models.pitch import Pitch
from allocator.models.team import Team
from allocator.logger import setup_logger

logger = setup_logger(__name__)

# S3 Configuration
S3_BUCKET = 'owpitchalloc'  # Ensure this matches your bucket name
s3_client = boto3.client('s3')

# Determine the absolute path to the directory containing config_loader.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def load_json_from_s3(key):
    """Load JSON data from s3."""
    try:
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
        data = response['Body'].read().decode('utf-8')
        return json.loads(data)
    except ClientError as e:
        logger.error(f"Failed to load {key} from S3: {e}")
        raise FileNotFoundError(f"File {key} not found in S3.")

def save_json_to_s3(key, data):
    """Save JSON data to S3."""
    try:
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=key,
            Body=json.dumps(data, indent=4),
            ContentType='application/json'
        )
        logger.info(f"Successfully saved {key} to S3.")
    except ClientError as e:
        logger.error(f"Failed to save {key} to S3: {e}")
        raise e

def get_config_key(config_type, username):
    """Generate S3 key for the configuration file."""
    return f"configs/{username}/{config_type}.json"

def get_default_config_key(config_type):
    """Generate S3 key for the default configuration file."""
    return f"configs/{config_type}.json"

def load_pitches(username=None):
    """Load pitches from S3."""
    if username:
        key = get_config_key('pitches', username)
    else:
        key = get_default_config_key('pitches')
    
    try:
        all_pitches_data = load_json_from_s3(key)
    except FileNotFoundError:
        logger.warning(f"{key} not found. Loading default pitches.")
        key = get_default_config_key('pitches')
        all_pitches_data = load_json_from_s3(key)
    
    all_pitches = {Pitch(**pitch).format_label(): Pitch(**pitch) for pitch in all_pitches_data['pitches']}
    allowed_pitch_labels = set(all_pitches.keys())

    filtered_pitches = []
    for label in allowed_pitch_labels:
        pitch = all_pitches.get(label)
        if pitch:
            filtered_pitches.append(pitch)
        else:
            logger.warning(f"Pitch with label '{label}' not found in {key}.")

    # Sort pitches by capacity: 5-aside, 7-aside, 9-aside, then 11-aside
    filtered_pitches.sort(key=lambda pitch: {5: 0, 7: 1, 9: 2, 11: 3}.get(pitch.capacity, 4))
    logger.info(f"Loaded {len(filtered_pitches)} pitches from S3.")

    return filtered_pitches

def load_teams(username=None):
    """Load teams from S3."""
    if username:
        key = get_config_key('teams', username)
    else:
        key = get_default_config_key('teams')
    
    try:
        teams_data = load_json_from_s3(key)
    except FileNotFoundError:
        logger.warning(f"{key} not found. Loading default teams.")
        key = get_default_config_key('teams')
        teams_data = load_json_from_s3(key)
    
    teams = []
    for team in teams_data['teams']:
        try:
            id = team['id']
            name = team['name']
            age = team['age_group']
            gender = team['gender']
            teams.append(Team(id, name, age, gender))
        except ValueError:
            logger.error(f"Invalid team format: '{team}'. Expected JSON.")
    
    logger.info(f"Loaded {len(teams)} teams from S3.")
    return teams