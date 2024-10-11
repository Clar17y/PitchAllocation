from . import db
from allocator.utils import format_age_group

class Team(db.Model):
    __tablename__ = 'Team'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age_group = db.Column(db.String(50), nullable=False)
    is_girls = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user_login_info.id'), nullable=False)
    created = db.Column(db.DateTime(timezone=True), server_default=db.func.now())

    players = db.relationship('Player', back_populates='team', lazy=True)
    allocations = db.relationship('Allocation', back_populates='team', lazy=True)
    owner = db.relationship('User', back_populates='teams')

    def format_label(self):
        return f"{format_age_group(self.age_group)} {self.name}" + (f" (Girls)" if self.is_girls else "")
