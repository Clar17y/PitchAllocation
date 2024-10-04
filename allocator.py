import yaml
import logging
import argparse
import sys
import random  # Added for randomization
from datetime import datetime, timedelta
from pitch import Pitch
from team import Team

class Allocator:
    def __init__(self, pitches_file, teams_file, allocation_file, start_time=None, end_time=None):
        self.setup_logging()

        # Load and validate YAML configuration
        self.config = self.load_and_validate_config(allocation_file)

        # Initialize start and end times
        self.start_time = self.get_time(start_time, self.config.get('start_time', "10:00"))
        self.end_time = self.get_time(end_time, self.config.get('end_time', "14:00"))

        # Load pitches from pitches.yml
        with open(pitches_file) as f:
            pitches_data = yaml.safe_load(f)
        self.all_pitches = [Pitch(**p) for p in pitches_data['pitches']]
        logging.info(f"Loaded {len(self.all_pitches)} pitches.")

        # Create a mapping from descriptive name to Pitch object
        self.pitch_name_map = self.create_pitch_name_map()

        # Load teams from teams.yml
        with open(teams_file) as f:
            teams_data = yaml.safe_load(f)
        self.teams = []
        for age, names in teams_data['teams'].items():
            if not names:
                logging.info(f"No teams under age group '{age}'. Skipping.")
                continue  # Skip age groups with no teams
            for name in names:
                is_girls = '(Girls)' in name
                clean_name = name.replace(' (Girls)', '')
                self.teams.append(Team(clean_name, age, is_girls))
        logging.info(f"Loaded {len(self.teams)} teams.")

        # Filter pitches based on allocation file using descriptive names
        allocated_pitch_descriptions = self.config['pitches']
        self.pitches = []
        for desc in allocated_pitch_descriptions:
            pitch = self.pitch_name_map.get(desc)
            if pitch:
                self.pitches.append(pitch)
                logging.info(f"Allocated pitch: {desc} ({pitch.code})")
            else:
                logging.error(f"Pitch '{desc}' not found in pitches.yml.")
                sys.exit(1)

        # Load home teams
        self.home_teams = self.config['home_teams']
        self.allocations = []
        self.unallocated_teams = []  # Initialize list for unallocated teams

    def setup_logging(self):
        """Set up the logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler("allocator.log", mode='a')
            ]
        )
        logging.info("Logging is set up.")

    def create_pitch_name_map(self):
        """Create a mapping from descriptive pitch names to Pitch objects."""
        pitch_map = {}
        for pitch in self.all_pitches:
            # Format: "<Capacity>aside - <Location>"
            descriptive_name = f"{pitch.capacity}aside - {pitch.location}"
            pitch_map[descriptive_name] = pitch
        return pitch_map

    def load_and_validate_config(self, allocation_file):
        """Load and validate the YAML allocation configuration."""
        with open(allocation_file) as f:
            config = yaml.safe_load(f)

        # Validate required fields
        required_fields = ['date', 'start_time', 'end_time', 'pitches', 'home_teams']
        for field in required_fields:
            if field not in config:
                logging.error(f"Missing required field '{field}' in allocation configuration.")
                sys.exit(1)

        # Validate pitches
        if not isinstance(config['pitches'], list):
            logging.error("Field 'pitches' should be a list.")
            sys.exit(1)

        # Validate home_teams
        if not isinstance(config['home_teams'], dict):
            logging.error("Field 'home_teams' should be a dictionary.")
            sys.exit(1)

        logging.info("Allocation configuration loaded and validated.")
        return config

    def get_time(self, time_str, default):
        """Convert a time string to a datetime object."""
        if time_str:
            try:
                return datetime.strptime(time_str, "%H:%M")
            except ValueError:
                logging.error(f"Invalid time format: '{time_str}'. Expected HH:MM.")
                sys.exit(1)
        else:
            try:
                return datetime.strptime(default, "%H:%M")
            except ValueError:
                logging.error(f"Invalid default time format: '{default}'. Expected HH:MM.")
                sys.exit(1)

    def get_team_from_entry(self, team_entry):
        """Retrieve a Team object based on the team entry."""
        name = team_entry['name'].replace(' (Girls)', '')
        is_girls = '(Girls)' in team_entry['name']
        for team in self.teams:
            if team.name == name and team.is_girls == is_girls:
                return team
        return None

    def validate_time_format(self, time_str):
        """Validate the time format is HH:MM."""
        try:
            datetime.strptime(time_str, "%H:%M")
            return True
        except ValueError:
            return False

    def format_pitch_label(self, pitch):
        """
        Format the pitch label as '<Capacity>aside - <Location>'.
        For example, capacity 5 and location 'HD TL' becomes '5aside - HD TL'.
        """
        return f"{pitch.capacity}aside - {pitch.location}"

    def format_age_group(self, age_group):
        """
        Shorten 'Under7s' to 'U7', 'Under8s' to 'U8', etc.
        """
        if age_group.startswith('Under'):
            number = ''.join(filter(str.isdigit, age_group))
            return f"U{number}"
        return age_group

    def allocate(self):
        """Allocate teams to pitches based on preferences and availability."""
        logging.info("Starting allocation process.")
        start_time = self.start_time
        end_of_day = self.end_time

        # Prepare teams with and without preferred times
        teams_with_pref = []
        teams_without_pref = []
        for age, teams in self.home_teams.items():
            if not teams:
                logging.info(f"No teams under age group '{age}'. Skipping allocation for this group.")
                continue  # Skip age groups with no teams
            for team_entry in teams:
                team = self.get_team_from_entry(team_entry)
                if not team:
                    logging.warning(f"Team '{team_entry['name']}' not found in teams list.")
                    continue
                preferred_time = team_entry.get('preferred_time', "").strip()
                if preferred_time:
                    if self.validate_time_format(preferred_time):
                        preferred_datetime = start_time.replace(
                            hour=int(preferred_time.split(":")[0]),
                            minute=int(preferred_time.split(":")[1])
                        )
                        teams_with_pref.append((team, preferred_datetime))
                        logging.debug(f"Team '{team.name}' has preferred time {preferred_time}.")
                    else:
                        logging.warning(f"Invalid preferred_time format for team '{team.name}': '{preferred_time}'. Ignoring preference.")
                        teams_without_pref.append(team)
                else:
                    teams_without_pref.append(team)

        # Shuffle teams to randomize allocation order
        random.shuffle(teams_with_pref)
        random.shuffle(teams_without_pref)

        # Shuffle pitches to randomize pitch selection
        random.shuffle(self.pitches)

        # Sort teams with preferences by their preferred times
        teams_with_pref.sort(key=lambda x: x[1])

        # Allocation logic for teams with preferred times
        allocated_pref_teams = set()
        for team, pref_time in teams_with_pref:
            if pref_time > end_of_day:
                logging.info(f"Cannot schedule {team.name} at preferred time {pref_time.strftime('%H:%M')} as it starts after {end_of_day.strftime('%H:%M')}.")
                self.unallocated_teams.append(team)
                continue  # Skip this preference

            allocated = False
            # Shuffle pitches for each allocation attempt to ensure randomness
            random.shuffle(self.pitches)
            for pitch in self.pitches:
                pitch_type = self.get_pitch_type(team)
                duration = self.get_duration(pitch_type)

                if pitch.capacity != pitch_type:
                    continue  # Skip pitches that don't match the required type

                if pitch.is_available(pref_time, duration) and self.is_conflicting_pitch_available(pitch, pref_time, duration):
                    pitch.add_match(team.name, pref_time, duration)
                    self.allocations.append({
                        'time': pref_time.strftime("%I:%M%p").lower(),
                        'team': f"{self.format_age_group(team.age_group)} {team.name}",
                        'pitch': f"{self.format_pitch_label(pitch)} ({pitch.code})"
                    })
                    logging.info(f"Allocated {team.name} to pitch '{self.format_pitch_label(pitch)}' ({pitch.code}) at {pref_time.strftime('%H:%M')}.")
                    allocated_pref_teams.add(team)
                    allocated = True
                    break  # Move to the next team

            if not allocated:
                logging.info(f"Could not allocate {team.name} at preferred time {pref_time.strftime('%H:%M')}. Adding to unallocated teams.")
                self.unallocated_teams.append(team)

        # Remove allocated teams with preferences from teams_without_pref
        teams_to_allocate = [team for team in teams_without_pref if team not in allocated_pref_teams]

        # Shuffle teams_to_allocate to randomize allocation order
        random.shuffle(teams_to_allocate)

        # Allocation loop for teams without preferred times
        while start_time <= end_of_day and teams_to_allocate:
            allocated_this_slot = False
            logging.debug(f"Allocating teams at {start_time.strftime('%H:%M')}.")

            # Shuffle pitches for each time slot to ensure randomness
            random.shuffle(self.pitches)
            for pitch in self.pitches:
                if not teams_to_allocate:
                    break  # No more teams to allocate

                # Shuffle teams to allocate to randomize selection
                random.shuffle(teams_to_allocate)
                # Find the first team that can be allocated to this pitch at the current start_time
                for team in list(teams_to_allocate):  # Use a copy of the list
                    pitch_type = self.get_pitch_type(team)
                    duration = self.get_duration(pitch_type)

                    if start_time > end_of_day:
                        logging.info(f"Cannot schedule {team.name} as it starts after {end_of_day.strftime('%H:%M')}.")
                        self.unallocated_teams.append(team)
                        teams_to_allocate.remove(team)
                        continue  # Skip this team

                    if pitch.capacity != pitch_type:
                        continue  # Skip pitches that don't match the required type

                    if pitch.is_available(start_time, duration) and self.is_conflicting_pitch_available(pitch, start_time, duration):
                        # Allocate the match
                        pitch.add_match(team.name, start_time, duration)
                        self.allocations.append({
                            'time': start_time.strftime("%I:%M%p").lower(),
                            'team': f"{self.format_age_group(team.age_group)} {team.name}",
                            'pitch': f"{self.format_pitch_label(pitch)} ({pitch.code})"
                        })
                        teams_to_allocate.remove(team)
                        allocated_this_slot = True
                        logging.info(f"Allocated {team.name} to pitch '{self.format_pitch_label(pitch)}' ({pitch.code}) at {start_time.strftime('%H:%M')}.")
                        break  # Move to the next pitch

            if not allocated_this_slot:
                logging.info(f"No allocations made at {start_time.strftime('%H:%M')}.")
            # Increment start_time after checking all pitches for the current slot
            start_time += timedelta(minutes=30)

        # After all allocations, any remaining teams in teams_to_allocate are unallocated
        for team in teams_to_allocate:
            logging.info(f"Could not allocate {team.name}. Adding to unallocated teams.")
            self.unallocated_teams.append(team)

        # Log unallocated teams
        if self.unallocated_teams:
            logging.info("=== Unallocated Teams ===")
            for team in self.unallocated_teams:
                gender = "(Girls)" if team.is_girls else ""
                logging.info(f" - {self.format_age_group(team.age_group)} {team.name} {gender}")
        else:
            logging.info("All teams have been successfully allocated.")

        logging.info("Allocation process completed.")

    def is_conflicting_pitch_available(self, pitch, start_time, duration):
        """Check if conflicting pitches are available."""
        # Define conflicting codes
        conflicting_codes = {
            'E': ['E', 'F'],
            'F': ['E', 'F'],
            'D': ['D', 'G'],
            'G': ['D', 'G'],
            'H': ['H']
        }
        conflicts = conflicting_codes.get(pitch.code, [])
        for p in self.pitches:
            if p.code in conflicts and p != pitch:
                if not p.is_available(start_time, duration):
                    logging.debug(f"Conflict detected for pitch '{p.location}' during {start_time.strftime('%H:%M')}.")
                    return False
        return True

    def get_pitch_type(self, team):
        """Determine the pitch type based on team age group and gender."""
        age = team.age_group
        if age in ['Under7s', 'Under8s']:
            return 5
        elif age in ['Under9s', 'Under10s'] or (age == 'Under11s' and team.is_girls):
            return 7
        elif age in ['Under11s', 'Under12s'] or (age == 'Under13s' and team.is_girls):
            return 9
        else:
            return 11

    def get_duration(self, pitch_type):
        """Get the duration of the match based on pitch type."""
        if pitch_type in [5, 7, 9]:
            return timedelta(minutes=90)
        else:
            return timedelta(hours=2)

    def save_allocations(self, filename):
        """Save the allocation results to a file ordered by pitch capacity and time."""
        
        def sort_key(alloc):
            """
            Define the sort key for each allocation.
            - Primary Key: Pitch capacity (integer)
            - Secondary Key: Start time (datetime object)
            """
            # Extract capacity from pitch description (e.g., "5aside - HD TL (A)" -> 5)
            pitch_desc = alloc['pitch']
            try:
                capacity_part = pitch_desc.split('aside')[0].strip()
                capacity = int(capacity_part)
            except (IndexError, ValueError):
                logging.error(f"Unable to extract capacity from pitch description: '{pitch_desc}'. Defaulting capacity to 0.")
                capacity = 0  # Default capacity if parsing fails

            # Extract time and convert to datetime object for accurate sorting
            time_str = alloc['time'].lower()
            try:
                time_obj = datetime.strptime(time_str, "%I:%M%p")
            except ValueError:
                logging.error(f"Invalid time format: '{time_str}'. Defaulting time to midnight.")
                time_obj = datetime.strptime("12:00am", "%I:%M%p")  # Default time if parsing fails

            return (capacity, time_obj)

        # Sort allocations first by capacity, then by time
        sorted_allocations = sorted(self.allocations, key=sort_key)

        # Write sorted allocations to the file
        with open(filename, 'w') as f:
            for alloc in sorted_allocations:
                f.write(f"{alloc['time']} - {alloc['team']} - {alloc['pitch']}\n")
        
        logging.info(f"Allocations saved to '{filename}' ordered by pitch capacity and time.")

def parse_arguments():
    """Parse command-line arguments for dynamic configuration."""
    parser = argparse.ArgumentParser(description="Allocate teams to pitches based on preferences and availability.")
    parser.add_argument('--start_time', type=str, help="Override start time in HH:MM format.")
    parser.add_argument('--end_time', type=str, help="Override end time in HH:MM format.")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()
    allocator = Allocator(
        pitches_file='pitches.yml',
        teams_file='teams.yml',
        allocation_file='current_allocation.yml',
        start_time=args.start_time,
        end_time=args.end_time
    )
    allocator.allocate()
    allocator.save_allocations('allocations_week1.txt')