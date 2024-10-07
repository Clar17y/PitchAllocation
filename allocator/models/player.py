from allocator.logger import setup_logger

logger = setup_logger(__name__)

class Player:
    def __init__(self, id, first_name, surname, team_id, shirt_number):
        self.id = id
        self.first_name = first_name
        self.surname = surname
        self.team_id = team_id
        self.shirt_number = shirt_number

    def format_label(self):
        return f"{self.first_name} {self.surname} (#{self.shirt_number})"

    def to_dict(self):
        """Serialize Player object to a dictionary."""
        return {
            'id': self.id,
            'first_name': self.first_name,
            'surname': self.surname,
            'team_id': self.team_id,
            'shirt_number': self.shirt_number
        }
    
    def __str__(self):
        return f"Player(id={self.id}, first_name={self.first_name}, surname={self.surname}, team_id={self.team_id}, shirt_number={self.shirt_number})"