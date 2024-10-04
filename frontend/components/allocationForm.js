// frontend/components/allocationForm.js

import { fetchTeams, fetchPitches, submitAllocation } from '../api/api.js';
import { logMessage } from '../utils/logger.js';
import { generateTimeOptions, groupTeamsByAgeGroup } from '../utils/helpers.js';
import { getCookie } from '../utils/cookie.js';

let teamsList = [];
let pitchesList = [];
let currentUsername = '';

export function initializeFormComponents(username) {
    currentUsername = username;
    populateNextSunday();
    populateStartTime();
    populateEndTime();
    fetchTeams()
        .then(data => {
            teamsList = data;
            populateTeams();
        })
        .catch(error => logMessage(error.message, 'error'));

    fetchPitches()
        .then(data => {
            pitchesList = data;
            populatePitches();
        })
        .catch(error => logMessage(error.message, 'error'));

    document.getElementById('allocation-form').addEventListener('submit', function(event) {
        event.preventDefault();
        handleSubmitAllocation();
    });
}

function populateNextSunday() {
    const dateInput = document.getElementById('date');
    const today = new Date();
    const nextSunday = new Date(today);
    nextSunday.setDate(today.getDate() + ((7 - today.getDay()) % 7 || 7));
    const yyyy = nextSunday.getFullYear();
    const mm = String(nextSunday.getMonth() + 1).padStart(2, '0');
    const dd = String(nextSunday.getDate()).padStart(2, '0');
    dateInput.value = `${yyyy}-${mm}-${dd}`;
}

function populateStartTime() {
    const startHourSelect = document.getElementById('start-hour');
    const allowedHours = [9, 10, 11, 12];
    allowedHours.forEach(hour => {
        const option = document.createElement('option');
        option.value = String(hour).padStart(2, '0');
        option.text = String(hour).padStart(2, '0');
        startHourSelect.add(option);
    });
    startHourSelect.value = '10';
}

function populateEndTime() {
    const endHourSelect = document.getElementById('end-hour');
    const allowedHours = [14, 15, 16, 17, 18];
    allowedHours.forEach(hour => {
        const option = document.createElement('option');
        option.value = String(hour).padStart(2, '0');
        option.text = String(hour).padStart(2, '0');
        endHourSelect.add(option);
    });
    endHourSelect.value = '14';
}

function populateTeams() {
    const container = document.getElementById('teams-container');
    container.innerHTML = ''; // Clear existing content

    // Group teams by age group
    const teamsByAgeGroup = groupTeamsByAgeGroup(teamsList);

    // Create columns for each age group
    Object.entries(teamsByAgeGroup).forEach(([ageGroup, teams]) => {
        const col = document.createElement('div');
        // Adjust column classes for better mobile responsiveness
        col.className = 'col-lg-4 col-md-6 col-sm-12 mb-4';

        const ageGroupHeader = document.createElement('h5');
        ageGroupHeader.innerText = ageGroup;
        col.appendChild(ageGroupHeader);

        teams.forEach(team => {
            const div = document.createElement('div');
            div.className = 'form-check d-flex align-items-center mb-2';

            const checkbox = document.createElement('input');
            checkbox.className = 'form-check-input flex-shrink-0 me-2';
            checkbox.type = 'checkbox';
            checkbox.id = `team-${team.team_id}`;
            checkbox.value = team.team_id;

            const label = document.createElement('label');
            label.className = 'form-check-label flex-grow-1 me-2';
            label.htmlFor = `team-${team.team_id}`;
            label.innerText = team.display_name;

            const timeSelect = document.createElement('select');
            timeSelect.className = 'form-select form-select-sm flex-shrink-0';
            timeSelect.id = `time-${team.team_id}`;
            timeSelect.disabled = true;

            // Populate time options
            const times = generateTimeOptions();
            times.forEach(time => {
                const option = document.createElement('option');
                option.value = time;
                option.text = time;
                timeSelect.appendChild(option);
            });

            // Enable time select on checkbox toggle
            checkbox.addEventListener('change', function() {
                timeSelect.disabled = !this.checked;
                if (!this.checked) {
                    timeSelect.value = '';
                }
            });

            div.appendChild(checkbox);
            div.appendChild(label);
            div.appendChild(timeSelect);
            col.appendChild(div);
        });

        container.appendChild(col);
    });
}

function populatePitches() {
    const container = document.getElementById('pitches-container');
    container.innerHTML = ''; // Clear existing content

    // Create a row
    const row = document.createElement('div');
    row.className = 'row';

    // Determine the column classes based on screen size
    const colClass = 'col-lg-6 col-md-6 col-sm-12 mb-3';

    // Create a column
    const col = document.createElement('div');
    col.className = colClass;

    pitchesList.forEach((pitch) => {
        const div = document.createElement('div');
        div.className = 'form-check d-flex align-items-center mb-2';

        const checkbox = document.createElement('input');
        checkbox.className = 'form-check-input me-2';
        checkbox.type = 'checkbox';
        checkbox.id = `pitch-${pitch.code}`;
        checkbox.value = pitch.code;

        const label = document.createElement('label');
        label.className = 'form-check-label';
        label.htmlFor = `pitch-${pitch.code}`;
        label.innerText = `${pitch.format_label}`;

        div.appendChild(checkbox);
        div.appendChild(label);

        col.appendChild(div);
    });

    row.appendChild(col);
    container.appendChild(row);
}

function validatePayload(payload) {
    if (!payload.date || !payload.start_time || !payload.end_time) {
        alert('Please fill in all required fields.');
        return false;
    }

    if (payload.start_time >= payload.end_time) {
        alert('Start time must be before end time.');
        return false;
    }

    const teamIdRegex = /^[A-Za-z0-9]+-(Girls|Boys)$/;
    for (let team of payload.teams) {
        if (!teamIdRegex.test(team.team_id)) {
            alert(`Invalid team_id format: ${team.team_id}`);
            return false;
        }
    }

    if (payload.teams.length < 1) {
        alert('Please select at least one team.');
        return false;
    }
    if (payload.pitches.length < 1) {
        alert('Please select at least one pitch.');
        return false;
    }

    return true;
}

function handleSubmitAllocation() {
    const date = document.getElementById('date').value;
    const start_hour = document.getElementById('start-hour').value;
    const start_minute = document.getElementById('start-minute').value;
    const end_hour = document.getElementById('end-hour').value;
    const end_minute = document.getElementById('end-minute').value;

    const pitches = Array.from(document.querySelectorAll('#pitches-container input[type="checkbox"]:checked')).map(cb => cb.value);
    const teams = Array.from(document.querySelectorAll('#teams-container input[type="checkbox"]:checked')).map(cb => {
        const teamId = cb.value;
        const preferredTimeInput = document.getElementById(`time-${teamId}`);
        const preferredTime = preferredTimeInput.value; // Can be empty string if not set
        return {
            team_id: teamId,
            preferred_time: preferredTime // May be empty
        };
    });

    const payload = {
        'username': currentUsername, // Include username
        'date': date,
        'start_time': `${start_hour}:${start_minute}`,
        'end_time': `${end_hour}:${end_minute}`,
        'pitches': pitches,
        'teams': teams
    };

    if (!validatePayload(payload)) {
        return;
    }

    // Check for duplicate teams
    const selectedTeamIds = payload.teams.map(team => team.team_id);
    const uniqueTeamIds = new Set(selectedTeamIds);
    if (uniqueTeamIds.size !== selectedTeamIds.length) {
        alert('Duplicate teams selected. Please ensure each team is selected only once.');
        return;
    }

    submitAllocation(payload)
        .then(data => {
            displayResults(data.allocations);
            displayLogs(data.logs);
        })
        .catch(error => logMessage(error.message, 'error'));
}

function displayResults(allocations) {
    const resultsBox = document.getElementById('allocation-results');
    if (!allocations || allocations.length === 0) {
        resultsBox.value = 'No allocations available.';
        return;
    }

    let resultText = '';
    let currentCapacity = null;

    allocations.forEach(alloc => {
        if (alloc.capacity !== currentCapacity) {
            if (currentCapacity !== null) {
                resultText += '\n';  // Add an empty line between capacity groups
            }
            currentCapacity = alloc.capacity;
        }
        resultText += `${alloc.time} - ${alloc.team} - ${alloc.pitch}\n`;
    });

    resultsBox.value = resultText.trim();
}

function displayLogs(logs) {
    const logsContainer = document.getElementById('console-logs');
    logsContainer.innerHTML = '';  // Clear previous logs

    logs.forEach(log => {
        const p = document.createElement('p');
        p.innerText = `[${log.level.toUpperCase()}] ${log.message}`;
        p.className = `text-${log.level === 'error' ? 'danger' : log.level === 'warning' ? 'warning' : log.level === 'success' ? 'success' : 'secondary'}`;
        logsContainer.appendChild(p);
    });
}

export function clearSelections() {
    // Clear pitches
    document.querySelectorAll('#pitches-container input[type="checkbox"]').forEach(checkbox => {
        checkbox.checked = false;
    });

    // Clear teams and preferred times
    document.querySelectorAll('#teams-container input[type="checkbox"]').forEach(checkbox => {
        checkbox.checked = false;
        const teamId = checkbox.value;
        const preferredTimeInput = document.getElementById(`time-${teamId}`);
        preferredTimeInput.disabled = true;
        preferredTimeInput.value = '';
    });

    // Reset date to next Sunday
    populateNextSunday();

    // Reset start and end times
    populateStartTime();
    populateEndTime();

    // Clear results and logs
    document.getElementById('allocation-results').value = '';
    document.getElementById('console-logs').innerHTML = '';
}