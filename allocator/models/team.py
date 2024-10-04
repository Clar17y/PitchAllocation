from allocator.utils import format_age_group

class Team:
    def __init__(self, name, age_group, is_girls):
        self.name = name
        self.age_group = age_group
        self.is_girls = is_girls

    def format_label(self):
        return f"{format_age_group(self.age_group)} {self.name}" + (" (Girls)" if self.is_girls else "")