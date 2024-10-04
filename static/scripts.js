// static/scripts.js

document.addEventListener('DOMContentLoaded', () => {
    populateTimeSelectors();
    loadPitches();
    loadTeams();

    document.getElementById('allocate-button').addEventListener('click', allocateTeams);
    document.getElementById('clear-pitches-button').addEventListener('click', clearPitches);
    document.getElementById('clear-teams-button').addEventListener('click', clearTeams);
});

/**
 * Populates the hour selectors with options from 00 to 23.
 */
function populateTimeSelectors() {
    const startHourSelect = document.getElementById('start-hour');
    const endHourSelect = document.getElementById('end-hour');

    for (let i = 0; i < 24; i++) {
        const hour = i.toString().padStart(2, '0');
        const optionStart = document.createElement('option');
        optionStart.value = hour;
        optionStart.text = hour;
        startHourSelect.add(optionStart);

        const optionEnd = document.createElement('option');
        optionEnd.value = hour;
        optionEnd.text = hour;
        endHourSelect.add(optionEnd);
    }

    // Set default values
    document.getElementById('start-hour').value = '10';
    document.getElementById('start-minute').value = '00';
    document.getElementById('end-hour').value = '14';
    document.getElementById('end-minute').value = '00';
}

/**
 * Fetches pitches from the backend and populates the pitches container.
 */
function loadPitches() {
    fetch('/api/pitches')  // Now served by Flask
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            const pitchesContainer = document.getElementById('pitches-container');
            pitchesContainer.innerHTML = ''; // Clear existing content
            data.pitches.forEach(pitch => {
                const div = document.createElement('div');
                div.className = 'form-check';

                const checkbox = document.createElement('input');
                checkbox.className = 'form-check-input';
                checkbox.type = 'checkbox';
                checkbox.id = `pitch-${pitch.code}`;
                checkbox.value = pitch.code;

                const label = document.createElement('label');
                label.className = 'form-check-label';
                label.htmlFor = `pitch-${pitch.code}`;
                label.innerText = `${pitch.name} (${pitch.code})`;

                div.appendChild(checkbox);
                div.appendChild(label);
                pitchesContainer.appendChild(div);
            });
        })
        .catch(error => logMessage(`Error loading pitches: ${error.message}`, 'error'));
}

/**
 * Fetches teams from the backend and populates the teams container.
 */
function loadTeams() {
    fetch('/api/teams')  // Now served by Flask
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            const teamsContainer = document.getElementById('teams-container');
            teamsContainer.innerHTML = ''; // Clear existing content
            data.teams.forEach(team => {
                const div = document.createElement('div');
                div.className = 'mb-3';

                const checkboxDiv = document.createElement('div');
                checkboxDiv.className = 'form-check';

                const checkbox = document.createElement('input');
                checkbox.className = 'form-check-input';
                checkbox.type = 'checkbox';
                checkbox.id = `team-${team.id}`;
                checkbox.value = team.id;  // Unique ID

                const label = document.createElement('label');
                label.className = 'form-check-label';
                label.htmlFor = `team-${team.id}`;
                label.innerText = team.label;  // e.g., "U7 TALYBONT (Girls)"

                checkboxDiv.appendChild(checkbox);
                checkboxDiv.appendChild(label);
                div.appendChild(checkboxDiv);

                // Preferred Time Selectors
                const timeDiv = document.createElement('div');
                timeDiv.className = 'input-group mt-2';

                const hourSelect = document.createElement('select');
                hourSelect.className = 'form-select preferred-hour';
                hourSelect.setAttribute('data-team-id', team.id);
                const defaultHourOption = document.createElement('option');
                defaultHourOption.value = '--';
                defaultHourOption.text = '--';
                hourSelect.appendChild(defaultHourOption);
                for (let i = 0; i < 24; i++) {
                    const hour = i.toString().padStart(2, '0');
                    const option = document.createElement('option');
                    option.value = hour;
                    option.text = hour;
                    hourSelect.appendChild(option);
                }

                const colonSpan = document.createElement('span');
                colonSpan.className = 'input-group-text';
                colonSpan.innerText = ':';

                const minuteSelect = document.createElement('select');
                minuteSelect.className = 'form-select preferred-minute';
                minuteSelect.setAttribute('data-team-id', team.id);
                const defaultMinuteOption = document.createElement('option');
                defaultMinuteOption.value = '--';
                defaultMinuteOption.text = '--';
                minuteSelect.appendChild(defaultMinuteOption);
                ['00', '15', '30', '45'].forEach(min => {
                    const option = document.createElement('option');
                    option.value = min;
                    option.text = min;
                    minuteSelect.appendChild(option);
                });

                timeDiv.appendChild(hourSelect);
                timeDiv.appendChild(colonSpan);
                timeDiv.appendChild(minuteSelect);
                div.appendChild(timeDiv);

                teamsContainer.appendChild(div);
            });
        })
        .catch(error => logMessage(`Error loading teams: ${error.message}`, 'error'));
}

/**
 * Clears all selected pitches.
 */
function clearPitches() {
    const pitchCheckboxes = document.querySelectorAll('#pitches-container input[type="checkbox"]');
    pitchCheckboxes.forEach(checkbox => checkbox.checked = false);
}

/**
 * Clears all selected teams and resets preferred times.
 */
function clearTeams() {
    const teamCheckboxes = document.querySelectorAll('#teams-container input[type="checkbox"]');
    teamCheckboxes.forEach(checkbox => checkbox.checked = false);

    const preferredHourSelects = document.querySelectorAll('.preferred-hour');
    preferredHourSelects.forEach(select => select.value = '--');

    const preferredMinuteSelects = document.querySelectorAll('.preferred-minute');
    preferredMinuteSelects.forEach(select => select.value = '--');
}

/**
 * Handles the allocation process.
 */
function allocateTeams() {
    // Gather allocation settings
    const date = document.getElementById('allocation-date').value;
    const startHour = document.getElementById('start-hour').value;
    const startMinute = document.getElementById('start-minute').value;
    const endHour = document.getElementById('end-hour').value;
    const endMinute = document.getElementById('end-minute').value;

    if (!date) {
        alert('Please select a date.');
        return;
    }

    if ((startHour === '--' || startMinute === '--') || (endHour === '--' || endMinute === '--')) {
        alert('Please select both start and end times.');
        return;
    }

    // Gather selected pitches
    const selectedPitches = Array.from(document.querySelectorAll('#pitches-container input[type="checkbox"]:checked'))
        .map(checkbox => checkbox.value);

    if (selectedPitches.length === 0) {
        alert('Please select at least one pitch.');
        return;
    }

    // Gather selected teams
    const selectedTeams = Array.from(document.querySelectorAll('#teams-container input[type="checkbox"]:checked'))
        .map(checkbox => checkbox.value);

    if (selectedTeams.length === 0) {
        alert('Please select at least one team.');
        return;
    }

    // Gather preferred times
    const teamsWithPreferences = [];
    selectedTeams.forEach(teamId => {
        const hourSelect = document.querySelector(`.preferred-hour[data-team-id="${teamId}"]`);
        const minuteSelect = document.querySelector(`.preferred-minute[data-team-id="${teamId}"]`);
        const preferredTime = `${hourSelect.value}:${minuteSelect.value}`;

        if (hourSelect.value !== '--' && minuteSelect.value !== '--') {
            teamsWithPreferences.push({
                team_id: teamId,
                preferred_time: preferredTime
            });
        } else {
            teamsWithPreferences.push({
                team_id: teamId,
                preferred_time: null
            });
        }
    });

    const payload = {
        date: date,
        start_time: `${startHour}:${startMinute}`,
        end_time: `${endHour}:${endMinute}`,
        pitches: selectedPitches,
        teams: selectedTeams.map(teamId => {
            const pref = teamsWithPreferences.find(p => p.team_id === teamId);
            return {
                team_id: teamId,
                preferred_time: pref ? pref.preferred_time : null
            };
        })
    };

    fetch('/api/allocate', {  // Now served by Flask
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        displayAllocations(data.allocations);
        displayLogs(data.logs);
    })
    .catch(error => {
        logMessage(`Allocation error: ${error.message}`, 'error');
    });
}

/**
 * Displays allocation results in the Allocation Results section.
 * @param {Array} allocations 
 */
function displayAllocations(allocations) {
    const resultsContainer = document.getElementById('allocation-results');
    resultsContainer.innerHTML = '';  // Clear previous results

    if (!allocations || allocations.length === 0) {
        resultsContainer.innerText = 'No allocations available.';
        return;
    }

    allocations.forEach(alloc => {
        const p = document.createElement('p');
        p.innerText = `${alloc.time} - ${alloc.team} - ${alloc.pitch}`;
        resultsContainer.appendChild(p);
    });
}

/**
 * Displays console logs in the Console Logs section.
 * @param {Array} logs 
 */
function displayLogs(logs) {
    const logsContainer = document.getElementById('console-logs');
    logsContainer.innerHTML = '';  // Clear previous logs

    logs.forEach(log => {
        const p = document.createElement('p');
        p.innerText = `[${log.level.toUpperCase()}] ${log.message}`;
        p.className = `text-${log.level === 'error' ? 'danger' : log.level === 'warning' ? 'warning' : 'secondary'}`;
        logsContainer.appendChild(p);
    });
}

/**
 * Logs a message to the Console Logs section.
 * @param {string} message 
 * @param {string} level - 'info', 'warning', 'error'
 */
function logMessage(message, level = 'info') {
    const logsContainer = document.getElementById('console-logs');
    const p = document.createElement('p');
    p.innerText = `[${level.toUpperCase()}] ${message}`;
    p.className = `text-${level === 'error' ? 'danger' : level === 'warning' ? 'warning' : 'secondary'}`;
    logsContainer.appendChild(p);
}