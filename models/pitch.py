from . import db
from models.allocation import Allocation
from datetime import datetime
from allocator.logger import setup_logger

logger = setup_logger(__name__)

pitch_overlaps = db.Table(
    'pitch_overlaps',
    db.metadata,
    db.Column('pitch_id_1', db.Integer, db.ForeignKey('Pitch.id'), primary_key=True),
    db.Column('pitch_id_2', db.Integer, db.ForeignKey('Pitch.id'), primary_key=True),
    schema='public'
)

class Pitch(db.Model):
    __tablename__ = 'Pitch'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    location = db.Column(db.String(150), nullable=False)
    cost = db.Column(db.Float, default=0.0)
    user_id = db.Column(db.Integer, db.ForeignKey('user_login_info.id'), nullable=False)
    created = db.Column(db.DateTime(timezone=True), server_default=db.func.now())

    allocations = db.relationship('Allocation', back_populates='pitch', lazy=True)
    owner = db.relationship('User', back_populates='pitches')
    
    # Define overlapping_pitches relationship for pitch_id_1
    overlapping_pitches_1 = db.relationship(
        'Pitch',
        secondary=pitch_overlaps,
        primaryjoin=id == pitch_overlaps.c.pitch_id_1,
        secondaryjoin=id == pitch_overlaps.c.pitch_id_2,
        backref=db.backref('overlapped_by_1', lazy='select'),
        lazy='select'
    )

    # Define overlapping_pitches relationship for pitch_id_2
    overlapping_pitches_2 = db.relationship(
        'Pitch',
        secondary=pitch_overlaps,
        primaryjoin=id == pitch_overlaps.c.pitch_id_2,
        secondaryjoin=id == pitch_overlaps.c.pitch_id_1,
        backref=db.backref('overlapped_by_2', lazy='select'),
        lazy='select'
    )

    @property
    def all_overlapping_pitches(self):
        """Combine overlapping_pitches_1 and overlapping_pitches_2."""
        return list(set(self.overlapping_pitches_1 + self.overlapping_pitches_2))

    def format_label(self):
        return f"{self.capacity}aside - {self.name}"

    def add_overlap(self, other_pitch):
        if other_pitch not in self.all_overlapping_pitches:
            self.overlapping_pitches_1.append(other_pitch)
            logger.debug(f"Added overlap between Pitch {self.id} and Pitch {other_pitch.id}")

    def remove_overlap(self, other_pitch):
        if other_pitch in self.overlapping_pitches_1:
            self.overlapping_pitches_1.remove(other_pitch)
            logger.debug(f"Removed overlap between Pitch {self.id} and Pitch {other_pitch.id}")
        elif other_pitch in self.overlapping_pitches_2:
            self.overlapping_pitches_2.remove(other_pitch)
            logger.debug(f"Removed overlap between Pitch {self.id} and Pitch {other_pitch.id}")

    def add_match(self, team, start_time, duration):
        """
        Schedule a match for a team at a specified start time and duration.

        Args:
            team (Team): The team to allocate.
            start_time (datetime): The start time of the match.
            duration (timedelta): The duration of the match.

        Returns:
            Allocation: The created allocation object if successful.
            None: If the pitch is not available.
        """
        logger.debug(f"Attempting to add match for team '{team.format_label()}' at {start_time} for duration {duration}.")

        if not isinstance(start_time, datetime):
            logger.error("start_time must be a datetime.datetime object.")
            return None

        if not self.is_available(start_time, duration):
            logger.error(f"Pitch '{self.format_label()}' is not available at {start_time}.")
            return None

        end_time = start_time + duration

        try:
            new_allocation = Allocation(
                date=start_time.date(),
                start_time=start_time,
                end_time=end_time,
                user_id=team.user_id,  # Assuming the team's user_id is the same as the pitch's
                pitch_id=self.id,
                team_id=team.id
            )
            db.session.add(new_allocation)
            db.session.commit()
            logger.debug(f"Match added: {team.format_label()} from {start_time} to {end_time}.")
            return new_allocation
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to add match: {e}")
            return None

    def is_available(self, start_time, duration):
        """
        Check if the pitch is available for a match at the given start time and duration.

        Args:
            start_time (datetime): The desired start time.
            duration (timedelta): The duration of the match.

        Returns:
            bool: True if available, False otherwise.
        """
        if not isinstance(start_time, datetime):
            logger.error("start_time must be a datetime.datetime object.")
            return False

        end_time = start_time + duration
        overlapping_allocations = Allocation.query.filter(
            Allocation.pitch_id == self.id,
            Allocation.date == start_time.date(),
            db.or_(
                db.and_(Allocation.start_time <= start_time, Allocation.end_time > start_time),
                db.and_(Allocation.start_time < end_time, Allocation.end_time >= end_time),
                db.and_(Allocation.start_time >= start_time, Allocation.end_time <= end_time)
            )
        ).all()

        if overlapping_allocations:
            logger.debug(f"Pitch '{self.format_label()}' has overlapping allocations.")
            return False

        return True

    def reset_matches(self):
        """
        Remove all allocations (matches) associated with this pitch.
        """
        try:
            Allocation.query.filter_by(pitch_id=self.id).delete()
            db.session.commit()
            logger.info(f"All matches for pitch '{self.format_label()}' have been reset.")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to reset matches for pitch '{self.format_label()}': {e}")

    def __str__(self):
        return f"Pitch(id={self.id}, name={self.name}, capacity={self.capacity}, location={self.location}, cost={self.cost})"