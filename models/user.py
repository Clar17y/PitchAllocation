from . import db, bcrypt, login_manager
from flask_login import UserMixin
from sqlalchemy.orm import relationship

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    __tablename__ = 'user_login_info'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True)
    hash = db.Column(db.String(128), nullable=False)
    salt = db.Column(db.String(128), nullable=False)
    created = db.Column(db.DateTime(timezone=True), server_default=db.func.now())

    # Relationships with back_populates
    teams = relationship('Team', back_populates='owner', lazy=True)
    pitches = relationship('Pitch', back_populates='owner', lazy=True)
    players = relationship('Player', back_populates='owner', lazy=True)
    allocations = relationship('Allocation', back_populates='user', lazy=True)

    def set_password(self, password):
        self.salt = bcrypt.generate_password_hash(password).decode('utf-8')
        self.hash = bcrypt.generate_password_hash(password + self.salt).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.hash, password + self.salt)