import random
from datetime import datetime, timedelta
import re  # Import regular expressions
from allocator.utils import get_datetime, get_pitch_type, get_duration, format_age_group
from allocator.logger import setup_logger

logger = setup_logger(__name__)

class Allocator:
    def __init__(self, pitches, teams, config, start_time=None, end_time=None):
        self.pitches = pitches
        self.teams = teams
        self.config = config
        
        reference_date = datetime.today().date()
        self.start_time = get_datetime(start_time, config.get('start_time', "10:00"), reference_date)
        self.end_time = get_datetime(end_time, config.get('end_time', "14:00"), reference_date)

        self.pitch_name_map = self.create_pitch_name_map()
        self.pitch_code_map = {pitch.code: pitch for pitch in self.pitches}  # Mapping code to Pitch

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
        for pitch in self.pitches:
            pitch.reset_matches()

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
        Extracts the team object from team_entry using 'team_id'.
        Expected 'team_id' format: "TeamName-Girls" or "TeamName-Boys"
        """
        team_id = team_entry.get('team_id')
        if not team_id:
            logger.error("team_id missing in team_entry.")
            return None

        team_id = team_id.strip()  # Remove any leading/trailing spaces
        try:
            name, gender = team_id.rsplit('-', 1)
            is_girls = gender.lower() == 'girls'
        except ValueError:
            logger.error(f"Invalid team_id format: '{team_id}'. Expected format 'TeamName-Girls' or 'TeamName-Boys'.")
            return None

        team = next((t for t in self.teams if t.name == name and t.is_girls == is_girls), None)
        if not team:
            logger.warning(f"Team '{team_id}' not found in teams list.")
        return team
    
    def get_team_from_name(self, name):
        for team in self.teams:
            if team.name in name and format_age_group(team.age_group) in name:
                return team
        return None

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
            
            allocated = self.try_allocate_team(team, pref_time, end_of_day)
            logger.info(f"allocated: {allocated}")
            if allocated:
                allocated_pref_teams.add(team)
            else:
                self.unallocated_teams.append(team)

        return allocated_pref_teams
    
    def allocate_remaining_teams(self, teams, start_time, end_of_day, specific_pitches=None):
        pitches_to_use = specific_pitches if specific_pitches else self.pitches
        # Add unallocated teams from allocate_preferred_teams to teams_to_allocate
        teams_to_allocate = set(teams) | set(self.unallocated_teams)
        # Clear the unallocated_teams list as we're now considering all teams
        self.unallocated_teams = []
        while teams_to_allocate and start_time <= end_of_day:
            allocated_this_slot = False
            for pitch in pitches_to_use:
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

    def try_allocate_team(self, team, start_time, end_of_day, specific_pitch=None):
        pitch_type = get_pitch_type(team)
        duration = get_duration(pitch_type)

        if start_time > end_of_day:
            logger.info(f"Cannot schedule {team.format_label()} as it starts after {end_of_day.strftime('%H:%M')}.")
            return False

        pitches_to_check = [specific_pitch] if specific_pitch else self.pitches
        for pitch in pitches_to_check:
            if pitch.capacity != pitch_type:
                continue

            if not pitch.is_available(start_time, duration):
                continue

            # Check overlapping pitches
            overlapping = [self.pitch_code_map[code] for code in pitch.overlaps_with if code in self.pitch_code_map]
            overlap_conflict = False
            for overlapping_pitch in overlapping:
                if overlapping_pitch.is_available(start_time, duration) is False:
                    overlap_conflict = True
                    logger.info(f"Cannot allocate {team.format_label()} to '{pitch.format_label()}' because overlapping pitch '{overlapping_pitch.format_label()}' is occupied at {start_time.strftime('%H:%M')}.")
                    break
            if overlap_conflict:
                continue

            # Allocate the team to the pitch
            pitch.add_match(team, start_time, duration)
            cost_indicator = " (Paid)" if pitch.cost > 0 else ""
            self.allocations.append({
                'time': start_time.strftime("%I:%M%p").lower(),
                'team': team.format_label(),
                'pitch': f"{pitch.format_label()} ({pitch.code}){cost_indicator}"
            })
            logger.info(f"Allocated {team.format_label()} to pitch '{pitch.format_label()}' ({pitch.code}){cost_indicator} at {start_time.strftime('%H:%M')}.")
            return True

        return False

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
        # Helper function to extract capacity from pitch label
        def extract_capacity(pitch_label):
            match = re.match(r"(\d+)aside", pitch_label)
            if match:
                return int(match.group(1))
            else:
                logger.error(f"Unable to extract capacity from pitch label: '{pitch_label}'. Defaulting capacity to 0.")
                return 0

        # Group allocations by pitch capacity
        allocations_by_capacity = {}
        for alloc in self.allocations:
            # Assuming alloc['pitch'] is like "5aside - HD TL (A)"
            pitch_label = alloc['pitch'].split(" (")[0]  # Extract "5aside - HD TL"
            capacity = extract_capacity(pitch_label)
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
                formatted_allocations += f"{alloc['time']} - {alloc['team']} - {alloc['pitch']}\n"
            formatted_allocations += "\n"  # Line break between capacity groups

        return formatted_allocations.strip()  # Remove the trailing newline

    def save_allocations(self, filename):
        """Save allocations to a file, grouped and ordered by pitch capacity."""
        formatted_allocations = self.format_allocations()
        with open(filename, 'w') as f:
            f.write(formatted_allocations)
            f.write("\n")  # Ensure the file ends with a newline

        logger.info(f"Allocations saved to '{filename}' ordered and grouped by pitch capacity.")