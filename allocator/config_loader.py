from models import db
from models.pitch import Pitch
from models.team import Team
from models.player import Player
from allocator.logger import setup_logger
from flask_login import current_user
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

logger = setup_logger(__name__)

def load_pitches():
    """Load pitches from the PostgreSQL database."""
    user_id = current_user.id if current_user.is_authenticated else None
    if not user_id:
        logger.error("User not authenticated.")
        raise PermissionError("User not authenticated.")

    try:
        pitches = Pitch.query.filter_by(user_id=current_user.id).options(
            selectinload(Pitch.overlapping_pitches_1),
            selectinload(Pitch.overlapping_pitches_2)
        ).all()

        if not pitches:
            logger.warning(f"No pitches found for user_id {user_id}.")
        # Ensure that each Pitch instance has a 'format_label' method
        all_pitches = {pitch.format_label(): pitch for pitch in pitches}
        allowed_pitch_labels = set(all_pitches.keys())

        filtered_pitches = []
        for label in allowed_pitch_labels:
            pitch = all_pitches.get(label)
            if pitch:
                filtered_pitches.append(pitch)
            else:
                logger.warning(f"Pitch with label '{label}' not found.")

        # Sort pitches by capacity: 5-aside, 7-aside, 9-aside, then 11-aside
        filtered_pitches.sort(key=lambda pitch: {5: 0, 7: 1, 9: 2, 11: 3}.get(pitch.capacity, 4))
        logger.info(f"Loaded {len(filtered_pitches)} pitches from the database.")

        return filtered_pitches

    except SQLAlchemyError as e:
        logger.error(f"Database error while loading pitches: {e}")
        raise e

def load_teams():
    """Load teams from the PostgreSQL database."""
    user_id = current_user.id if current_user.is_authenticated else None
    if not user_id:
        logger.error("User not authenticated.")
        raise PermissionError("User not authenticated.")

    try:
        teams = Team.query.filter_by(user_id=user_id).all()
        if not teams:
            logger.warning(f"No teams found for user_id {user_id}.")

        team_list = []
        for team in teams:
            team_list.append({
                'id': team.id,
                'name': team.name,
                'age_group': team.age_group,
                'is_girls': team.is_girls,
                'display_label': team.format_label()
            })
        
        logger.info(f"Loaded {len(team_list)} teams from the database.")
        return team_list

    except SQLAlchemyError as e:
        logger.error(f"Database error while loading teams: {e}")
        raise e

def load_players():
    """Load players from the PostgreSQL database."""
    user_id = current_user.id if current_user.is_authenticated else None
    if not user_id:
        logger.error("User not authenticated.")
        raise PermissionError("User not authenticated.")

    try:
        players = Player.query.filter_by(user_id=user_id).all()
        if not players:
            logger.warning(f"No players found for user_id {user_id}.")

        player_list = []
        for player in players:
            player_list.append({
                'id': player.id,
                'first_name': player.first_name,
                'surname': player.surname,
                'team_id': player.team_id,
                'shirt_number': player.shirt_number
            })
        
        logger.info(f"Loaded {len(player_list)} players from the database.")
        return player_list

    except SQLAlchemyError as e:
        logger.error(f"Database error while loading players: {e}")
        raise e

def save_players(players):
    """Save or update players in the PostgreSQL database."""
    user_id = current_user.id if current_user.is_authenticated else None
    if not user_id:
        logger.error("User not authenticated.")
        raise PermissionError("User not authenticated.")

    try:
        for player_data in players:
            player = Player.query.filter_by(id=player_data['id'], user_id=user_id).first()
            if player:
                # Update existing player
                player.first_name = player_data['first_name']
                player.surname = player_data['surname']
                player.team_id = player_data['team_id']
                player.shirt_number = player_data['shirt_number']
                logger.info(f"Updated player ID {player.id}.")
            else:
                # Create a new player
                new_player = Player(
                    first_name=player_data['first_name'],
                    surname=player_data['surname'],
                    team_id=player_data['team_id'],
                    shirt_number=player_data['shirt_number'],
                    user_id=user_id
                )
                db.session.add(new_player)
                logger.info(f"Added new player: {new_player.first_name} {new_player.surname}.")

        db.session.commit()
        logger.info("All players have been successfully saved.")
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error while saving players: {e}")
        raise e