import os
import tkinter as tk
import random
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime
import logging
from allocator.config_loader import load_pitches, load_teams
from allocator.allocator_base import Allocator
from allocator.utils import format_age_group

class GUIHandler(logging.Handler):
    """Custom logging handler to display logs in a Tkinter Text widget."""
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        self.text_widget.configure(state='normal')
        self.text_widget.insert(tk.END, msg + '\n')
        self.text_widget.configure(state='disabled')
        self.text_widget.see(tk.END)

class AllocationUI:
    def __init__(self, master):
        self.master = master
        master.title("Pitch Allocation System")
        master.geometry("1200x700")
        master.minsize(800, 600)  # Prevent elements from collapsing

        # Initialize widget attributes
        self.log_text = None
        self.output_text = None
        self.pitches_vars = []         # List of BooleanVar for each pitch
        self.pitches_code_vars = {}    # Mapping pitch code to BooleanVar
        self.teams_vars = []
        self.preferred_time_vars = []
        self.overlap_map_ui = {}       # Mapping pitch code to set of overlapping pitch codes

        self.load_data()
        self.configure_grid()
        self.create_widgets()      # Create all widgets first
        self.setup_logging()      # Then set up logging, now log_text exists

    def configure_grid(self):
        """Configure grid weights to make the UI responsive."""
        self.master.columnconfigure(0, weight=1)  # Allocation Settings
        self.master.columnconfigure(1, weight=2)  # Pitches
        self.master.columnconfigure(2, weight=2)  # Teams
        self.master.columnconfigure(3, weight=2)  # Allocation Results and Logs

        self.master.rowconfigure(0, weight=0)    # Allocation Settings Frame
        self.master.rowconfigure(1, weight=1)    # Pitches and Teams Frames
        self.master.rowconfigure(2, weight=2)    # Allocation Results and Logs

    def create_widgets(self):
        """Create and place all UI widgets."""
        self.create_allocation_settings()
        self.create_pitches_section()
        self.create_teams_section()
        self.create_allocation_results()
        self.create_console_logs()

    def create_allocation_settings(self):
        """Create Allocation Settings frame and widgets."""
        input_frame = ttk.LabelFrame(self.master, text="Allocation Settings", padding="10")
        input_frame.grid(row=0, column=0, columnspan=4, padx=10, pady=10, sticky=(tk.W, tk.E))

        # Configure grid for input_frame
        input_frame.columnconfigure(1, weight=1)

        # Date Selector
        ttk.Label(input_frame, text="Date (YYYY-MM-DD):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.date_entry = ttk.Entry(input_frame)
        self.date_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))

        # Start Time Selector
        ttk.Label(input_frame, text="Start Time:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.start_hour, self.start_minute = self.create_time_selector(input_frame, row=1, column=1, default_hour="10", default_minute="00")

        # End Time Selector
        ttk.Label(input_frame, text="End Time:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.end_hour, self.end_minute = self.create_time_selector(input_frame, row=2, column=1, default_hour="14", default_minute="00")

        # Allocate Button
        self.allocate_button = ttk.Button(input_frame, text="Allocate", command=self.allocate)
        self.allocate_button.grid(row=3, column=0, columnspan=2, pady=10)

    def create_time_selector(self, parent, row, column, default_hour, default_minute):
        """Helper method to create hour and minute comboboxes."""
        hour_cb = ttk.Combobox(parent, values=[f"{i:02}" for i in range(0,24)], width=3, state="readonly")
        minute_cb = ttk.Combobox(parent, values=["00", "15", "30", "45"], width=3, state="readonly")
        hour_cb.grid(row=row, column=column, sticky=tk.W, padx=(5,0), pady=5)
        ttk.Label(parent, text=":").grid(row=row, column=column, sticky=tk.W, padx=(45,0), pady=5)
        minute_cb.grid(row=row, column=column, sticky=tk.W, padx=(55,5), pady=5)
        hour_cb.set(default_hour)
        minute_cb.set(default_minute)
        return hour_cb, minute_cb

    def create_pitches_section(self):
        """Create Pitches frame with scrollable checkboxes and Clear button."""
        pitches_frame = ttk.LabelFrame(self.master, text="Pitches", padding="10")
        pitches_frame.grid(row=1, column=1, padx=10, pady=10, sticky=(tk.N, tk.S, tk.E, tk.W))
        pitches_frame.columnconfigure(0, weight=1)
        pitches_frame.rowconfigure(0, weight=1)

        # Scrollable Canvas for Pitches
        self.pitches_canvas = tk.Canvas(pitches_frame)
        self.pitches_scrollbar = ttk.Scrollbar(pitches_frame, orient="vertical", command=self.pitches_canvas.yview)
        self.pitches_inner = ttk.Frame(self.pitches_canvas)

        self.pitches_inner.bind(
            "<Configure>",
            lambda e: self.pitches_canvas.configure(
                scrollregion=self.pitches_canvas.bbox("all")
            )
        )

        self.pitches_canvas.create_window((0, 0), window=self.pitches_inner, anchor="nw")
        self.pitches_canvas.configure(yscrollcommand=self.pitches_scrollbar.set)

        self.pitches_canvas.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.pitches_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # Initialize pitch variables and overlap mapping
        self.overlap_map_ui = {}  # pitch_code -> set of overlapping pitch codes
        for pitch in self.pitches:
            var = tk.BooleanVar()
            chk = ttk.Checkbutton(self.pitches_inner, text=pitch.format_label(), variable=var)
            chk.pack(anchor=tk.W, pady=2, padx=5)
            self.pitches_vars.append(var)
            self.pitches_code_vars[pitch.code] = var
            self.overlap_map_ui[pitch.code] = set(pitch.overlaps_with)

        # Clear button for Pitches
        self.clear_pitches_button = ttk.Button(pitches_frame, text="Clear Pitches", command=self.clear_pitches)
        self.clear_pitches_button.grid(row=1, column=0, pady=5, sticky=tk.E)

    def create_teams_section(self):
        """Create Teams frame with scrollable checkboxes, time selectors, and Clear button."""
        teams_frame = ttk.LabelFrame(self.master, text="Teams", padding="10")
        teams_frame.grid(row=1, column=2, padx=10, pady=10, sticky=(tk.N, tk.S, tk.E, tk.W))
        teams_frame.columnconfigure(0, weight=1)
        teams_frame.rowconfigure(0, weight=1)

        # Scrollable Canvas for Teams
        self.teams_canvas = tk.Canvas(teams_frame)
        self.teams_scrollbar = ttk.Scrollbar(teams_frame, orient="vertical", command=self.teams_canvas.yview)
        self.teams_inner = ttk.Frame(self.teams_canvas)

        self.teams_inner.bind(
            "<Configure>",
            lambda e: self.teams_canvas.configure(
                scrollregion=self.teams_canvas.bbox("all")
            )
        )

        self.teams_canvas.create_window((0, 0), window=self.teams_inner, anchor="nw")
        self.teams_canvas.configure(yscrollcommand=self.teams_scrollbar.set)

        self.teams_canvas.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.teams_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # Initialize team variables and preferred time selectors
        self.teams_vars = []
        self.preferred_time_vars = []
        for team in self.teams:
            var = tk.BooleanVar()
            chk = ttk.Checkbutton(self.teams_inner, text=team.format_label(), variable=var)
            chk.grid(row=len(self.teams_vars), column=0, sticky=tk.W, padx=5, pady=2)
            self.teams_vars.append(var)

            # Preferred Time Selectors
            hour_var = tk.StringVar()
            minute_var = tk.StringVar()
            hour_cb = ttk.Combobox(self.teams_inner, textvariable=hour_var, width=4, state="readonly")
            minute_cb = ttk.Combobox(self.teams_inner, textvariable=minute_var, width=3, state="readonly")
            hour_cb['values'] = ['--'] + [f"{i:02}" for i in range(9,19)]
            minute_cb['values'] = ['--'] + [f"{i:02}" for i in [0, 15, 30, 45]]  # Restrict to 00, 15, 30, 45
            hour_cb.grid(row=len(self.teams_vars)-1, column=1, padx=(20,0), pady=2, sticky=tk.W)
            ttk.Label(self.teams_inner, text=":").grid(row=len(self.teams_vars)-1, column=1, padx=(40,0), pady=2, sticky=tk.W)
            minute_cb.grid(row=len(self.teams_vars)-1, column=1, padx=(50,5), pady=2, sticky=tk.W)
            hour_cb.set("--")
            minute_cb.set("--")
            self.preferred_time_vars.append((hour_var, minute_var))

        # Clear button for Teams
        self.clear_teams_button = ttk.Button(teams_frame, text="Clear Teams", command=self.clear_teams)
        self.clear_teams_button.grid(row=1, column=0, pady=5, sticky=tk.E)

    def create_allocation_results(self):
        """Create Allocation Results frame with scrollable text box."""
        results_frame = ttk.LabelFrame(self.master, text="Allocation Results", padding="10")
        results_frame.grid(row=1, column=3, padx=10, pady=10, sticky=(tk.N, tk.S, tk.E, tk.W))
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)

        self.output_text = scrolledtext.ScrolledText(results_frame, wrap=tk.WORD, state='disabled')
        self.output_text.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))

    def create_console_logs(self):
        """Create Console Logs frame with scrollable text box."""
        logs_frame = ttk.LabelFrame(self.master, text="Console Logs", padding="10")
        logs_frame.grid(row=2, column=0, columnspan=4, padx=10, pady=10, sticky=(tk.N, tk.S, tk.E, tk.W))
        logs_frame.columnconfigure(0, weight=1)
        logs_frame.rowconfigure(0, weight=1)

        self.log_text = scrolledtext.ScrolledText(logs_frame, wrap=tk.WORD, state='disabled', height=10)
        self.log_text.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))

    def setup_logging(self):
        """Set up logging to the log_text widget."""
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.DEBUG)

        gui_handler = GUIHandler(self.log_text)
        gui_handler.setLevel(logging.DEBUG)

        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        gui_handler.setFormatter(formatter)

        self.logger.addHandler(gui_handler)

    def load_data(self):
        """Load data for pitches and teams."""
        allocation_config = {'pitches': []}
        self.pitches = load_pitches('data/pitches.yml', allocation_config)
        self.teams = load_teams('data/teams.yml')

    def allocate(self):
        """Perform the allocation process and update the UI."""
        # Gather selected pitches
        selected_pitches_codes = [code for code, var in self.pitches_code_vars.items() if var.get()]
        selected_pitches = [pitch for pitch in self.pitches if pitch.code in selected_pitches_codes]
        if not selected_pitches:
            messagebox.showwarning("No Pitches Selected", "Please select at least one pitch.")
            return

        # Gather selected teams and their preferred times
        selected_teams = [team for team, var in zip(self.teams, self.teams_vars) if var.get()]
        if not selected_teams:
            messagebox.showwarning("No Teams Selected", "Please select at least one team.")
            return

        home_teams = {}
        for team, (hour_var, minute_var) in zip(selected_teams, self.preferred_time_vars):
            age_group = team.age_group
            if age_group not in home_teams:
                home_teams[age_group] = []

            hour = hour_var.get()
            minute = minute_var.get()
            if hour == "--" and minute == "--":
                preferred_time_str = ""
            else:
                preferred_time_str = f"{hour}:{minute}"

            team_entry = {
                'name': f"{team.name}{' (Girls)' if team.is_girls else ''}",
                'preferred_time': preferred_time_str
            }

            home_teams[age_group].append(team_entry)

        # Default start and end times if not set
        start_time_str = f"{self.start_hour.get()}:{self.start_minute.get()}" if self.start_hour.get() != "--" else "10:00"
        end_time_str = f"{self.end_hour.get()}:{self.end_minute.get()}" if self.end_hour.get() != "--" else "14:00"

        # Create allocation configuration
        config = {
            'date': self.date_entry.get(),
            'start_time': start_time_str,
            'end_time': end_time_str,
            'pitches': [pitch.code for pitch in selected_pitches],  # Use pitch codes
            'home_teams': home_teams
        }

        # Initialize Allocator
        allocator = Allocator(selected_pitches, selected_teams, config)
        allocator.allocate()

        # Retrieve formatted allocations
        formatted_allocations = allocator.format_allocations()

        # Display Allocations in the Output Text Box
        self.output_text.configure(state='normal')
        self.output_text.delete('1.0', tk.END)
        self.output_text.insert(tk.END, formatted_allocations)
        self.output_text.configure(state='disabled')

        # Save Allocations to File
        output_dir = 'output'
        os.makedirs(output_dir, exist_ok=True)  # Ensure the output directory exists

        allocation_date = config.get('date')
        if allocation_date:
            formatted_date = allocation_date.replace('-', '')
            output_filename = f'output/allocations_{formatted_date}.txt'
        else:
            # Fallback to a default filename if date is not available
            self.logger.warning("Date not found in allocation config. Using default filename.")
            output_filename = 'output/allocations_default.txt'

        allocator.save_allocations(output_filename)

        if len(allocator.unallocated_teams) > 0:
            messagebox.showwarning("Unallocated: ", "\n".join([team.format_label() for team in allocator.unallocated_teams]))
        else:
            messagebox.showinfo("Allocation Completed", f"Allocations have been saved to '{output_filename}'.")

    def clear_pitches(self):
        """Clear all pitch checkboxes."""
        for var in self.pitches_vars:
            var.set(False)

    def clear_teams(self):
        """Clear all team checkboxes and reset preferred times."""
        for var in self.teams_vars:
            var.set(False)
        for hour_var, minute_var in self.preferred_time_vars:
            hour_var.set("--")
            minute_var.set("--")

    def reset_allocation(self):
        """Reset allocation outputs."""
        self.output_text.configure(state='normal')
        self.output_text.delete('1.0', tk.END)
        self.output_text.configure(state='disabled')

    def format_age_group(self, age_group):
        """Format the age group string."""
        return age_group.replace("Under", "U")

if __name__ == "__main__":
    root = tk.Tk()
    app = AllocationUI(root)
    root.mainloop()