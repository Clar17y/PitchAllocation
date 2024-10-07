from allocator.utils import format_age_group

class Team:
    def __init__(self, id, name, age_group, gender):
        self.id = id
        self.name = name
        self.age_group = age_group
        self.gender = gender

    def format_label(self):
        return f"{format_age_group(self.age_group)} {self.name}" + (f" ({self.gender})" if self.gender.lower() == 'girls' else "")
    
    def __str__(self):
        return f"Team(id={self.id}, name={self.name}, age_group={self.age_group}, gender={self.gender})"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "age_group": self.age_group,
            "gender": self.gender
        }
