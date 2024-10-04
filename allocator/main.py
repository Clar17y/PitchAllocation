import argparse
from allocator.config_loader import load_pitches, load_teams, load_allocation_config
from allocator.allocator_base import Allocator
from allocator.logger import setup_logger

logger = setup_logger(__name__)

def parse_arguments():
    parser = argparse.ArgumentParser(description="Allocate teams to pitches based on preferences and availability.")
    parser.add_argument('--start_time', type=str, help="Override start time in HH:MM format.")
    parser.add_argument('--end_time', type=str, help="Override end time in HH:MM format.")
    return parser.parse_args()

def main():
    args = parse_arguments()
    
    allocation_config = load_allocation_config('data/current_allocation.yml')
    pitches = load_pitches('data/pitches.yml', allocation_config)
    teams = load_teams('data/teams.yml')
    
    allocator = Allocator(pitches, teams, allocation_config, args.start_time, args.end_time)
    allocator.allocate()
    # Get the date from the allocation_config
    allocation_date = allocation_config.get('date')
    
    if allocation_date:
        # Format the date to be used in the filename
        formatted_date = allocation_date.replace('-', '')
        output_filename = f'output/allocations_{formatted_date}.txt'
    else:
        # Fallback to a default filename if date is not available
        logger.warning("Date not found in allocation config. Using default filename.")
        output_filename = 'output/allocations_default.txt'
    
    # Save the allocations using the new filename
    allocator.save_allocations(output_filename)

if __name__ == "__main__":
    main()