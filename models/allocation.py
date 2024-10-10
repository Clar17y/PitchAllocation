from . import db

class Allocation(db.Model):
    __tablename__ = 'Allocation'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.DateTime(timezone=True), nullable=False)  # Changed to DateTime for precise scheduling
    user_id = db.Column(db.Integer, db.ForeignKey('user_login_info.id'), nullable=False)
    pitch_id = db.Column(db.Integer, db.ForeignKey('Pitch.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('Team.id'), nullable=False)
    created = db.Column(db.DateTime(timezone=True), server_default=db.func.now())

    # Relationships with back_populates
    user = db.relationship('User', back_populates='allocations')
    pitch = db.relationship('Pitch', back_populates='allocations')
    team = db.relationship('Team', back_populates='allocations')

    def to_dict(self):
        """Serialize Allocation object to a dictionary."""
        return {
            'id': self.id,
            'date': self.date.isoformat(),
            'time': self.time.isoformat(),
            'user_id': self.user_id,
            'pitch_id': self.pitch_id,
            'team_id': self.team_id
        }

    def __str__(self):
        return f"Allocation(id={self.id}, date={self.date}, time={self.time}, user_id={self.user_id}, pitch_id={self.pitch_id}, team_id={self.team_id})"