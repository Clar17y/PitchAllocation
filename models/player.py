from . import db

class Player(db.Model):
    __tablename__ = 'Player'

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    surname = db.Column(db.String(50), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('Team.id'), nullable=False)
    shirt_number = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user_login_info.id'), nullable=False)
    created = db.Column(db.DateTime(timezone=True), server_default=db.func.now())

    team = db.relationship('Team', back_populates='players')
    owner = db.relationship('User', back_populates='players')

    def __str__(self):
        return f"Player(id={self.id}, name={self.first_name} {self.surname}, team_id={self.team_id}, shirt_number={self.shirt_number})"