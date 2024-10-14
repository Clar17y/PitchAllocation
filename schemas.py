from marshmallow import Schema, fields, post_load, validates, ValidationError, EXCLUDE
from models.player import Player
from models.pitch import Pitch
from models.team import Team
from models.allocation import Allocation
from models.user import User
from allocator.utils import get_current_user_id
import re

def validate_name(s):
    # This regex allows letters, numbers, spaces, hyphens, and apostrophes
    return bool(re.match(r'^[a-zA-Z0-9\s\-\']+$', s))

class PlayerSchema(Schema):
    id = fields.Int(dump_only=True)
    first_name = fields.Str(required=True, validate=validate_name)
    surname = fields.Str(required=True, validate=validate_name)
    team_id = fields.Int(required=True)
    shirt_number = fields.Int(required=True)
    user_id = fields.Int(dump_only=True)
    created = fields.DateTime(dump_only=True)

    @post_load
    def make_player(self, data, **kwargs):
        user_id = self.context.get('user_id')
        if not user_id:
            raise ValidationError("User ID is required to create a Pitch.")
        data['user_id'] = user_id
        return Player(**data)

class PitchSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True)
    capacity = fields.Int(required=True)
    location = fields.Str(required=True)
    cost = fields.Float()
    overlaps_with = fields.List(fields.Int())
    user_id = fields.Int(dump_only=True)
    created = fields.DateTime(dump_only=True)

    class Meta:
        unknown = EXCLUDE

    @post_load
    def make_pitch(self, data, **kwargs):
        user_id = self.context.get('user_id')
        if not user_id:
            raise ValidationError("User ID is required to create a Pitch.")
        data['user_id'] = user_id
        return Pitch(**data)
    
    def format_label(self, data):
        return f"{data['capacity']}aside - {data['name']}"

class TeamSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True)
    age_group = fields.Str(required=True)
    is_girls = fields.Bool(required=True)
    user_id = fields.Int(dump_only=True)
    created = fields.DateTime(dump_only=True)

    class Meta:
        unknown = EXCLUDE
    
    @post_load
    def make_team(self, data, **kwargs):
        user_id = self.context.get('user_id')
        if not user_id:
            raise ValidationError("User ID is required to create a Team.")
        data['user_id'] = user_id
        return Team(**data)

class AllocationSchema(Schema):
    id = fields.Int(dump_only=True)
    date = fields.Date(required=True)
    start_time = fields.DateTime(required=True) 
    end_time = fields.DateTime(required=True)
    user_id = fields.Int(dump_only=True)
    pitch_id = fields.Int(required=True)
    team_id = fields.Int(required=True)
    created = fields.DateTime(dump_only=True)
    preferred = fields.Bool(required=True)

    class Meta:
        unknown = EXCLUDE

    @post_load
    def make_allocation(self, data, **kwargs):
        user_id = self.context.get('user_id')
        if not user_id:
            raise ValidationError("User ID is required to create an Allocation.")
        data['user_id'] = user_id
        return Allocation(**data)

class UserSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True)
    hash = fields.Str(dump_only=True)
    salt = fields.Str(dump_only=True)
    created = fields.DateTime(dump_only=True)

    @post_load
    def make_user(self, data, **kwargs):
        return User(**data)

class StatisticsSchema(Schema):
    id = fields.Int()
    date = fields.Date()
    start_time = fields.DateTime()
    end_time = fields.DateTime()
    user_name = fields.Str(attribute="user_name")
    pitch_name = fields.Str(attribute="pitch_name")
    team_name = fields.Str(attribute="team_name")
    age_group = fields.Str(attribute="age_group")
    is_girls = fields.Bool(attribute="is_girls")
    preferred = fields.Bool(attribute="preferred")

def create_player_schema():
    return PlayerSchema(context={'user_id': get_current_user_id()})

def create_players_schema():
    return PlayerSchema(many=True, context={'user_id': get_current_user_id()})

def create_pitch_schema():
    return PitchSchema(context={'user_id': get_current_user_id()})

def create_pitches_schema():
    return PitchSchema(many=True, context={'user_id': get_current_user_id()})

def create_team_schema():
    return TeamSchema(context={'user_id': get_current_user_id()})

def create_teams_schema():
    return TeamSchema(many=True, context={'user_id': get_current_user_id()})

def create_allocation_schema():
    return AllocationSchema(context={'user_id': get_current_user_id()})

def create_allocations_schema():
    return AllocationSchema(many=True, context={'user_id': get_current_user_id()})