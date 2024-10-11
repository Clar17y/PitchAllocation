from datetime import datetime, timedelta
from flask_login import current_user

def get_current_user_id():
    return current_user.id if current_user.is_authenticated else None

def get_datetime(time_str_override, default_time_str, reference_date):
    """Convert a time string to a datetime.datetime object with the given reference_date."""
    time_str = time_str_override if time_str_override else default_time_str
    if time_str != "--:--":
        try:
            time_obj = datetime.strptime(time_str, "%H:%M").time()
            return datetime.combine(reference_date, time_obj)
        except ValueError:
            raise ValueError(f"Invalid time format: '{time_str}'. Expected format: HH:MM")
    else:
        return None

def validate_time_format(time_str):
    """Validate if the provided time string is in the correct format HH:MM."""
    try:
        datetime.strptime(time_str, "%H:%M")
        return True
    except ValueError:
        return False

def get_pitch_type(team):
    """Determine the pitch type based on team age group and gender."""
    age = team.age_group
    if age in ['Under7s', 'Under8s']:
        return 5
    elif age in ['Under9s', 'Under10s'] or (age == 'Under11s' and team.gender == 'Girls'):
        return 7
    elif age in ['Under11s', 'Under12s'] or (age == 'Under13s' and team.gender == 'Girls'):
        return 9
    else:
        return 11

def get_duration(pitch_type):
    """Get the duration of the match based on pitch type."""
    if pitch_type in [5, 7, 9]:
        return timedelta(minutes=90)
    else:
        return timedelta(hours=2)

def format_age_group(age_group):
    """Shorten 'Under7s' to 'U7', 'Under8s' to 'U8', etc."""
    if age_group.startswith('Under'):
        number = ''.join(filter(str.isdigit, age_group))
        return f"U{number}"
    return age_group