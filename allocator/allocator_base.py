import random
from datetime import datetime, timedelta
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
        self.allocations = []
        self.unallocated_teams = []

    def create_pitch_name_map(self):
        return {pitch.format_label(): pitch for pitch in self.pitches}

    def allocate(self):
        logger.info("Starting allocation process.")
        start_time = self.start_time
        end_of_day = self.end_time

        teams_with_pref, teams_without_pref = self.prepare_teams()

        random.shuffle(teams_with_pref)
        random.shuffle(teams_without_pref)

        # Sort pitches: free pitches first, then paid pitches
        self.pitches.sort(key=lambda p: p.cost)

        teams_with_pref.sort(key=lambda x: x[1])

        self.allocate_preferred_teams(teams_with_pref, start_time, end_of_day)
        self.allocate_remaining_teams(teams_without_pref, start_time, end_of_day)

        # If there are still unallocated teams, try to allocate them to paid pitches
        if self.unallocated_teams:
            logger.info("Attempting to allocate remaining teams to paid pitches.")
            paid_pitches = [p for p in self.pitches if p.cost > 0]
            self.allocate_remaining_teams(self.unallocated_teams, start_time, end_of_day, paid_pitches)

        self.log_unallocated_teams()
        logger.info("Allocation process completed.")

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
                preferred_time = team_entry.get('preferred_time', "").strip()
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
        name = team_entry['name'].replace(' (Girls)', '')
        is_girls = '(Girls)' in team_entry['name']
        for team in self.teams:
            if team.name == name and team.is_girls == is_girls:
                return team
        logger.warning(f"Team '{team_entry['name']}' not found in teams list.")
        return None

    def parse_preferred_time(self, preferred_time):
        try:
            return get_datetime(preferred_time, None, self.start_time.date())
        except ValueError as e:
            logger.warning(str(e))
            return None

    def allocate_preferred_teams(self, teams_with_pref, start_time, end_of_day):
        allocated_pref_teams = set()
        for team, pref_time in teams_with_pref:
            if pref_time > end_of_day:
                logger.info(f"Cannot schedule {team.name} at preferred time {pref_time.strftime('%H:%M')} as it starts after {end_of_day.strftime('%H:%M')}.")
                self.unallocated_teams.append(team)
                continue

            allocated = self.try_allocate_team(team, pref_time, end_of_day)
            if allocated:
                allocated_pref_teams.add(team)

        return allocated_pref_teams

    def allocate_remaining_teams(self, teams, start_time, end_of_day, specific_pitches=None):
        pitches_to_use = specific_pitches if specific_pitches else self.pitches
        teams_to_allocate = set(teams)
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
            start_time += timedelta(minutes=30)

        # Update unallocated teams
        self.unallocated_teams = list(teams_to_allocate)

    def try_allocate_team(self, team, start_time, end_of_day, specific_pitch=None):
        pitch_type = get_pitch_type(team)
        duration = get_duration(pitch_type)

        if start_time > end_of_day:
            logger.info(f"Cannot schedule {team.name} as it starts after {end_of_day.strftime('%H:%M')}.")
            return False

        pitches_to_check = [specific_pitch] if specific_pitch else self.pitches
        for pitch in pitches_to_check:
            if pitch.capacity != pitch_type:
                continue

            if pitch.is_available(start_time, duration):
                pitch.add_match(team.name, start_time, duration)
                cost_indicator = " (Paid)" if pitch.cost > 0 else ""
                self.allocations.append({
                    'time': start_time.strftime("%I:%M%p").lower(),
                    'team': f"{format_age_group(team.age_group)} {team.name}",
                    'pitch': f"{pitch.format_label()} ({pitch.code}){cost_indicator}"
                })
                logger.info(f"Allocated {team.name} to pitch '{pitch.format_label()}' ({pitch.code}){cost_indicator} at {start_time.strftime('%H:%M')}.")
                return True

        return False

    def log_unallocated_teams(self):
        if self.unallocated_teams:
            logger.info("=== Unallocated Teams ===")
            for team in self.unallocated_teams:
                gender = "(Girls)" if team.is_girls else ""
                logger.info(f" - {format_age_group(team.age_group)} {team.name} {gender}")
        else:
            logger.info("All teams have been successfully allocated.")

    def save_allocations(self, filename):
        def sort_key(alloc):
            pitch_desc = alloc['pitch']
            try:
                capacity_part = pitch_desc.split('aside')[0].strip()
                capacity = int(capacity_part)
            except (IndexError, ValueError):
                logger.error(f"Unable to extract capacity from pitch description: '{pitch_desc}'. Defaulting capacity to 0.")
                capacity = 0

            time_str = alloc['time'].lower()
            try:
                time_obj = datetime.strptime(time_str, "%I:%M%p")
            except ValueError:
                logger.error(f"Invalid time format: '{time_str}'. Defaulting time to midnight.")
                time_obj = datetime.strptime("12:00am", "%I:%M%p")

            return (capacity, time_obj)

        sorted_allocations = sorted(self.allocations, key=sort_key)

        with open(filename, 'w') as f:
            for alloc in sorted_allocations:
                f.write(f"{alloc['time']} - {alloc['team']} - {alloc['pitch']}\n")
        
        logger.info(f"Allocations saved to '{filename}' ordered by pitch capacity and time.")