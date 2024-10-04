// frontend/app.js

document.addEventListener('DOMContentLoaded', function() {
    initializeForm();
    fetchTeams();
    fetchPitches();
});

let teamsList = [];
let pitchesList = [];

function initializeForm() {
    populateNextSunday();
    populateStartTime();
    populateEndTime();
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

function fetchTeams() {
    fetch('/api/teams')
        .then(response => response.json())
        .then(data => {
            teamsList = data.teams;
            populateTeams();
        })
        .catch(error => logMessage(`Error fetching teams: ${error}`, 'error'));
}

function fetchPitches() {
    fetch('/api/pitches')
        .then(response => response.json())
        .then(data => {
            pitchesList = data.pitches;
            populatePitches();
        })
        .catch(error => logMessage(`Error fetching pitches: ${error}`, 'error'));
}

function populatePitches() {
    const container = document.getElementById('pitches-container');
    container.innerHTML = ''; // Clear existing content

    // Create a row to hold the columns
    const row = document.createElement('div');
    row.className = 'row';

    // Create two columns
    const col1 = document.createElement('div');
    col1.className = 'col-md-6';
    const col2 = document.createElement('div');
    col2.className = 'col-md-6';

    pitchesList.forEach((pitch, index) => {
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
        label.innerText = `${pitch.format_label} (${pitch.code})`;

        div.appendChild(checkbox);
        div.appendChild(label);

        // Add to first column if index is even, second column if odd
        if (index % 2 === 0) {
            col1.appendChild(div);
        } else {
            col2.appendChild(div);
        }
    });

    // Add columns to the row
    row.appendChild(col1);
    row.appendChild(col2);

    // Add the row to the container
    container.appendChild(row);
}

function populateTeams() {
    const container = document.getElementById('teams-container');
    container.innerHTML = ''; // Clear existing content

    // Group teams by age group
    const teamsByAgeGroup = groupTeamsByAgeGroup(teamsList);

    // Create columns for each age group
    Object.entries(teamsByAgeGroup).forEach(([ageGroup, teams]) => {
        const col = document.createElement('div');
        col.className = 'col-md-4 col-sm-6 mb-3'; // Adjust column width as needed

        const ageGroupHeader = document.createElement('h5');
        ageGroupHeader.innerText = ageGroup;
        col.appendChild(ageGroupHeader);

        teams.forEach(team => {
            const div = document.createElement('div');
            div.className = 'form-check d-flex align-items-center mb-2';

            const checkbox = document.createElement('input');
            checkbox.className = 'form-check-input me-2';
            checkbox.type = 'checkbox';
            checkbox.id = `team-${team.team_id}`;
            checkbox.value = team.team_id;

            const label = document.createElement('label');
            label.className = 'form-check-label me-2';
            label.htmlFor = `team-${team.team_id}`;
            label.innerText = team.display_name;

            const timeSelect = document.createElement('select');
            timeSelect.className = 'form-select form-select-sm w-auto';
            timeSelect.id = `time-${team.team_id}`;
            
            // Populate time options
            const times = generateTimeOptions();
            times.forEach(time => {
                const option = document.createElement('option');
                option.value = time;
                option.text = time;
                timeSelect.appendChild(option);
            });

            div.appendChild(checkbox);
            div.appendChild(label);
            div.appendChild(timeSelect);
            col.appendChild(div);
        });

        container.appendChild(col);
    });
}

function generateTimeOptions() {
    const times = ["--:--"];
    for (let hour = 9; hour <= 18; hour++) {
        for (let minute = 0; minute < 60; minute += 15) {
            const time = `${hour.toString().padStart(2, '0')}:${minute.toString().padStart(2, '0')}`;
            times.push(time);
        }
    }
    return times;
}

function clearSelections() {
    // Clear pitches
    document.querySelectorAll('#pitches-container input[type="checkbox"]').forEach(checkbox => {
        checkbox.checked = false;
    });

    // Clear teams
    document.querySelectorAll('#teams-container input[type="checkbox"]').forEach(checkbox => {
        checkbox.checked = false;
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

function validatePayload(payload) {
    if (!payload.date || !payload.start_time || !payload.end_time) {
        alert('Please fill in all required fields.');
        return false;
    }

    if (payload.start_time >= payload.end_time) {
        alert('Start time must be before end time.');
        return false;
    }

    const teamIdRegex = /^[A-Za-z]+-(Girls|Boys)$/;
    for (let team of payload.teams) {
        if (!teamIdRegex.test(team.team_id)) {
            alert(`Invalid team_id format: ${team.team_id}`);
            return false;
        }
    }

    return true;
}

function submitAllocation() {
    const date = document.getElementById('date').value;
    const start_hour = document.getElementById('start-hour').value;
    const start_minute = document.getElementById('start-minute').value;
    const end_hour = document.getElementById('end-hour').value;
    const end_minute = document.getElementById('end-minute').value;

    const pitches = Array.from(document.querySelectorAll('#pitches-container input[type="checkbox"]:checked')).map(cb => cb.value);
    const teams = Array.from(document.querySelectorAll('#teams-container input[type="checkbox"]:checked')).map(cb => {
        const teamId = cb.value;
        const preferredTime = document.getElementById(`time-${teamId}`).value;
        return {
            team_id: teamId,
            preferred_time: preferredTime
        };
    });

    const payload = {
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

    fetch('/api/allocate', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
    })
    .then(response => response.json())
    .then(data => {
        displayResults(data.allocations);
        displayLogs(data.logs);
    })
    .catch(error => logMessage(`Error submitting allocation: ${error.message}`, 'error'));
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
        p.className = `text-${log.level === 'error' ? 'danger' : log.level === 'warning' ? 'warning' : 'secondary'}`;
        logsContainer.appendChild(p);
    });
}

function copyResults() {
    const resultsBox = document.getElementById('allocation-results');
    resultsBox.select();
    resultsBox.setSelectionRange(0, 99999); // For mobile devices

    navigator.clipboard.writeText(resultsBox.value)
        .then(() => {
            logMessage('Results copied to clipboard.', 'success');
        })
        .catch(err => {
            logMessage('Failed to copy results.', 'error');
        });
}

function logMessage(message, level = 'info') {
    const logsContainer = document.getElementById('console-logs');
    const p = document.createElement('p');
    p.innerText = `[${level.toUpperCase()}] ${message}`;
    p.className = `text-${level === 'error' ? 'danger' : level === 'warning' ? 'warning' : level === 'success' ? 'success' : 'secondary'}`;
    logsContainer.appendChild(p);
}

document.getElementById('allocation-form').addEventListener('submit', function(event) {
    event.preventDefault();
    submitAllocation();
});

function groupTeamsByAgeGroup(teams) {
    return teams.reduce((groups, team) => {
        const ageGroup = team.display_name.split(' ')[0]; // Assuming the age group is the first part of the display name
        if (!groups[ageGroup]) {
            groups[ageGroup] = [];
        }
        groups[ageGroup].push(team);
        return groups;
    }, {});
}