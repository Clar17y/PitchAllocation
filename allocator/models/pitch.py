from datetime import datetime
from allocator.logger import setup_logger

logger = setup_logger(__name__)

class Pitch:
    def __init__(self, id, name, capacity, location, cost=0, overlaps_with=None):
        self.id = id
        self.name = name
        self.capacity = capacity
        self.location = location
        self.cost = cost
        self.matches = []
        self.overlaps_with = overlaps_with if overlaps_with else []

    def add_match(self, team, start_time, duration):
        if not isinstance(start_time, datetime):
            logger.error("start_time must be a datetime.datetime object.")
            return

        end_time = start_time + duration
        self.matches.append({
            'team': team.format_label(),
            'start': start_time,
            'end': end_time
        })
        logger.debug(f"Match added: {team.format_label()} from {start_time.strftime('%H:%M')} to {end_time.strftime('%H:%M')}.")

    def is_available(self, start_time, duration):
        if not isinstance(start_time, datetime):
            logger.error("start_time must be a datetime.datetime object.")
            return False

        end_time = start_time + duration
        for match in self.matches:
            if (match['start'] <= start_time < match['end']) or (start_time <= match['start'] < end_time):
                return False
        return True

    def format_label(self):
        return f"{self.capacity}aside - {self.name}"
    
    def reset_matches(self):
        """Reset all scheduled matches."""
        self.matches = []

    def to_dict(self):
        """Serialize Pitch object to a dictionary excluding 'matches'."""
        return {
            'id': self.id,
            'name': self.name,
            'capacity': self.capacity,
            'location': self.location,
            'cost': self.cost,
            'overlaps_with': self.overlaps_with
        }
    
    def __str__(self):
        return f"Pitch(id={self.id}, name={self.name}, capacity={self.capacity}, location={self.location}, cost={self.cost})"