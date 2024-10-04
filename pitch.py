from datetime import timedelta

class Pitch:
    def __init__(self, name, code, location, capacity):
        self.name = name
        self.code = code
        self.location = location
        self.capacity = capacity
        self.schedule = []

    def is_available(self, start_time, duration):
        for match in self.schedule:
            if start_time < match['end'] and (start_time + duration) > match['start']:
                return False
        return True

    def add_match(self, team, start_time, duration):
        self.schedule.append({
            'team': team,
            'start': start_time,
            'end': start_time + duration
        })