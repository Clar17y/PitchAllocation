from datetime import datetime
from allocator.logger import setup_logger

logger = setup_logger(__name__)

class Pitch:
    def __init__(self, name, code, capacity, location, cost=0):
        self.name = name
        self.code = code
        self.capacity = capacity
        self.location = location
        self.cost = cost
        self.matches = []

    def add_match(self, team_name, start_time, duration):
        if not isinstance(start_time, datetime):
            logger.error("start_time must be a datetime.datetime object.")
            return

        end_time = start_time + duration
        self.matches.append({
            'team': team_name,
            'start': start_time,
            'end': end_time
        })
        logger.debug(f"Match added: {team_name} from {start_time.strftime('%H:%M')} to {end_time.strftime('%H:%M')}.")

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
        return f"{self.capacity}aside - {self.location}"