import random
from datetime import datetime, timedelta
import re  # Import regular expressions
from allocator.utils import get_datetime, get_pitch_type, get_duration, format_age_group
from allocator.logger import setup_logger
from models.team import Team
from models.pitch import Pitch
from models.player import Player
from models.allocation import Allocation
from models import db

logger = setup_logger(__name__)

class Allocator:
    def __init__(self, user_id, config):
        self.user_id = user_id
        self.config = config

        reference_date = datetime.today().date()
        self.start_time = get_datetime(config.get('start_time'), "10:00", reference_date)
        self.end_time = get_datetime(config.get('end_time'), "14:00", reference_date)

        # Query pitches and teams from the database
        self.pitches = Pitch.query.filter_by(user_id=self.user_id).all()
        self.teams = Team.query.filter_by(user_id=self.user_id).all()

        self.pitch_name_map = self.create_pitch_name_map()
        self.pitch_id_map = { pitch.id: pitch for pitch in self.pitches }

        # Create separate lists for free and paid pitches
        self.free_pitches = sorted([p for p in self.pitches if p.cost == 0], key=lambda p: p.capacity)
        self.paid_pitches = sorted([p for p in self.pitches if p.cost > 0], key=lambda p: (p.cost, p.capacity))

        self.allocations = []
        self.unallocated_teams = []

    def create_pitch_name_map(self):
        return {pitch.format_label(): pitch for pitch in self.pitches}

    def allocate(self):
        logger.info("Starting allocation process.")
        self.reset_allocation_state()  # Reset previous allocations
        start_time = self.start_time
        end_of_day = self.end_time

        teams_with_pref, teams_without_pref = self.prepare_teams()
        # Sort pitches by capacity ascendingly, then by cost
        self.pitches.sort(key=lambda p: (p.capacity, p.cost))

        # Sort teams with preferences by preferred time (earlier first)
        teams_with_pref.sort(key=lambda x: x[1])

        # Allocate teams with preferences first
        self.allocate_preferred_teams(teams_with_pref, start_time, end_of_day)
        # Allocate remaining teams to free pitches first
        self.allocate_remaining_teams(teams_without_pref, start_time, end_of_day, self.free_pitches)

        # If there are still unallocated teams, try to allocate them to paid pitches
        if self.unallocated_teams:
            logger.info("Attempting to allocate remaining teams to paid pitches.")
            self.allocate_remaining_teams(self.unallocated_teams, start_time, end_of_day, self.paid_pitches)

        self.log_unallocated_teams()
        logger.info("Allocation process completed.")

    def reset_allocation_state(self):
        """Reset allocations and unallocated teams."""
        self.allocations = []
        self.unallocated_teams = []
        # Remove existing allocations from the database
        Allocation.query.filter_by(user_id=self.user_id).delete()
        db.session.commit()

    def prepare_teams(self):
        teams_with_pref = []
        teams_without_pref = []
        for age, team_entries in self.config['home_teams'].items():
            if not team_entries:
                logger.info(f"No teams under age group '{age}'. Skipping allocation for this group.")
                continue
            for team_entry in team_entries:
                team = self.get_team_from_entry(team_entry)
                if not team:
                    continue
                # Safeguard the strip() method
                preferred_time = (team_entry.get('preferred_time') or "").strip()
                if preferred_time:
                    preferred_datetime = self.parse_preferred_time(preferred_time)
                    if preferred_datetime:
                        teams_with_pref.append((team, preferred_datetime))
                    else:
                        teams_without_pref.append(team)
                else:
                    teams_without_pref.append(team)
        
        return teams_with_pref, teams_without_pref

    def get_team_from_entry(self, team_entry):
        """
        Extracts the team object from team_entry using the team's 'id'.
        """
        team_id = team_entry.get('id')
        if not team_id:
            logger.error("Team ID missing in team_entry.")
            return None

        team = Team.query.filter_by(id=int(team_id), user_id=self.user_id).first()
        if not team:
            logger.warning(f"Team ID '{team_id}' not found in teams list.")
        return team
    
    def parse_preferred_time(self, preferred_time):
        try:
            return get_datetime(preferred_time, None, self.start_time.date())
        except ValueError as e:
            logger.warning(str(e))
            return None

    def allocate_preferred_teams(self, teams_with_pref, start_time, end_of_day):
        allocated_pref_teams = set()
        random.shuffle(teams_with_pref)
        for team, pref_time in teams_with_pref:
            if pref_time > end_of_day:
                logger.info(f"Cannot schedule {team.format_label()} at preferred time {pref_time.strftime('%H:%M')} as it starts after {end_of_day.strftime('%H:%M')}.")
                self.unallocated_teams.append(team)
                continue
            
            allocated = self.try_allocate_team(team, pref_time, end_of_day, preferred=True)
            logger.info(f"allocated: {allocated}")
            if allocated:
                allocated_pref_teams.add(team)
            else:
                self.unallocated_teams.append(team)

        return allocated_pref_teams
    
    def allocate_remaining_teams(self, teams, start_time, end_of_day, specific_pitches=None):
        pitches_to_use = specific_pitches if specific_pitches else self.pitches
        sorted_pitches = sorted(pitches_to_use, key=lambda p: p.cost)
        # Add unallocated teams from allocate_preferred_teams to teams_to_allocate
        teams_to_allocate = set(teams) | set(self.unallocated_teams)
        # Clear the unallocated_teams list as we're now considering all teams
        self.unallocated_teams = []
        while teams_to_allocate and start_time <= end_of_day:
            allocated_this_slot = False
            for pitch in sorted_pitches:
                if not teams_to_allocate:
                    break

                teams_list = list(teams_to_allocate)
                random.shuffle(teams_list)
                for team in teams_list:
                    if self.try_allocate_team(team, start_time, end_of_day, pitch):
                        teams_to_allocate.remove(team)
                        allocated_this_slot = True
                        break

            if not allocated_this_slot:
                logger.info(f"No allocations made at {start_time.strftime('%H:%M')}.")
            start_time += timedelta(minutes=15)

        # Update unallocated teams
        self.unallocated_teams = list(teams_to_allocate)

    def try_allocate_team(self, team, start_time, end_of_day, specific_pitch=None, preferred=False):
        pitch_type = get_pitch_type(team)
        duration = get_duration(pitch_type)

        if start_time > end_of_day:
            logger.info(f"Cannot schedule {team.format_label()} as it starts after {end_of_day.strftime('%H:%M')}.")
            return False
        
        # Sort pitches by cost ascending to prioritize cheaper pitches
        sorted_pitches = sorted(
            [specific_pitch] if specific_pitch else self.pitches,
            key=lambda p: p.cost
        )

        for pitch in sorted_pitches:
            if pitch.capacity != pitch_type:
                continue

            if not self.is_pitch_available(pitch, start_time, duration):
                continue

            # Check overlapping pitches
            overlapping = Pitch.query.filter(Pitch.id.in_(pitch.overlaps_with)).all()
            overlap_conflict = False
            for overlapping_pitch in overlapping:
                if not self.is_pitch_available(overlapping_pitch, start_time, duration):
                    overlap_conflict = True
                    logger.info(f"Cannot allocate {team.format_label()} to '{pitch.format_label()}' because overlapping pitch '{overlapping_pitch.format_label()}' is occupied at {start_time.strftime('%H:%M')}.")
                    break
            if overlap_conflict:
                continue

            # Allocate the team to the pitch
            # Create a new Allocation record
            new_allocation = Allocation(
                date=start_time.date(),
                start_time=start_time.time(),
                end_time=start_time + duration,
                user_id=self.user_id,
                pitch_id=pitch.id,
                team_id=team.id
            )
            db.session.add(new_allocation)
            db.session.commit()

            self.allocations.append({
                'start_time': start_time.strftime("%I:%M%p").lower(),
                'team': team.format_label(),
                'pitch': f"{pitch.format_label()}",
                'preferred': preferred
            })
            logger.info(f"Allocated {team.format_label()} to pitch '{pitch.format_label()}' at {start_time.strftime('%H:%M')}.")
            return True

        return False

    def is_pitch_available(self, pitch, start_time, duration):
        end_time = datetime.combine(start_time.date(), start_time.time()) + duration
        existing_allocations = Allocation.query.filter_by(pitch_id=pitch.id, date=start_time.date()).all()
        for alloc in existing_allocations:
            alloc_start = datetime.combine(alloc.date, alloc.time)
            alloc_end = alloc_start + duration
            if (start_time < alloc_end and end_time > alloc_start):
                return False
        return True

    def log_unallocated_teams(self):
        if self.unallocated_teams:
            logger.info("=== Unallocated Teams ===")
            for team in self.unallocated_teams:
                logger.info(team.format_label())
        else:
            logger.info("All teams have been successfully allocated.")

    def format_allocations(self):
        """
        Format allocations grouped and ordered by pitch capacity.
        Returns:
            str: Formatted allocation string.
        """
        # Group allocations by pitch capacity
        allocations_by_capacity = {}
        for alloc in self.allocations:
            pitch = Pitch.query.get_by_label(alloc['pitch'], self.user_id)
            if pitch:
                capacity = pitch.capacity
                if capacity not in allocations_by_capacity:
                    allocations_by_capacity[capacity] = []
                allocations_by_capacity[capacity].append(alloc)

        # Sort capacities in ascending order (younger age groups first)
        sorted_capacities = sorted(allocations_by_capacity.keys())

        formatted_allocations = ""
        for capacity in sorted_capacities:
            # Sort allocations within the same capacity by time
            sorted_allocs = sorted(
                allocations_by_capacity[capacity],
                key=lambda x: datetime.strptime(x['time'], "%I:%M%p")
            )
            for alloc in sorted_allocs:
                formatted_allocations += f"{alloc['time']} - {alloc['team']} - {alloc['pitch']} - {alloc['preferred']}\n"
            formatted_allocations += "\n"  # Line break between capacity groups

        return formatted_allocations.strip()  # Remove the trailing newline

    def save_allocations(self, filename):
        """Save allocations to a file, grouped and ordered by pitch capacity."""
        formatted_allocations = self.format_allocations()
        with open(filename, 'w') as f:
            f.write(formatted_allocations)
            f.write("\n")  # Ensure the file ends with a newline

        logger.info(f"Allocations saved to '{filename}' ordered and grouped by pitch capacity.")