// frontend/app.js
let allTeamNames = [];
let currentTeamFilter = 'All';
let lastFetchedAllocations = []; 

document.addEventListener('DOMContentLoaded', function() {
    if (!window.location.pathname.endsWith('statistics.html')) {
        initializeForm();
        fetchTeams();
        fetchPitches();

        document.getElementById('allocation-form').addEventListener('submit', function(event) {
            event.preventDefault();
            submitAllocation();
        });
    }

    // Check if we're on the statistics page
    if (window.location.pathname.endsWith('statistics.html')) {
        console.log('Fetching statistics');
        fetchStatistics();
    }
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


function clearSelections() {
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
        const preferredTimeInput = document.getElementById(`time-${teamId}`);
        const preferredTime = preferredTimeInput.value; // Can be empty string if not set
        return {
            team_id: teamId,
            preferred_time: preferredTime // May be empty
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
        p.className = `text-${log.level === 'error' ? 'danger' : log.level === 'warning' ? 'warning' : log.level === 'success' ? 'success' : 'secondary'}`;
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

// New functions for Statistics Page

/**
 * Fetches allocation data from the backend and processes it.
 */
function fetchStatistics() {
    fetch('/api/statistics')
        .then(response => response.json())
        .then(data => {
            if (data.allocations) {
                allTeamNames = Array.from(new Set(data.allocations.map(alloc => alloc.team)))
                    .sort((a, b) => {
                        const ageA = extractAgeGroup(a);
                        const ageB = extractAgeGroup(b);
                        if (ageA === ageB) {
                            return a.localeCompare(b);
                        }
                        return ageA - ageB;
                    });
                populateTeamSelect();
                processStatistics(data.allocations);
            } else {
                logMessage('No allocation data available for statistics.', 'warning');
            }
        })
        .catch(error => {
            logMessage(`Error fetching statistics: ${error.message}`, 'error');
        });
}

// Add this new function to populate the team select dropdown
function populateTeamSelect() {
    const teamSelect = document.getElementById('team-select');
    teamSelect.innerHTML = '<option value="All" selected>All Teams</option>';
    allTeamNames.forEach(team => {
        const option = document.createElement('option');
        option.value = team;
        option.textContent = team;
        teamSelect.appendChild(option);
    });

    teamSelect.addEventListener('change', function() {
        currentTeamFilter = this.value;
        processStatistics(lastFetchedAllocations); // We'll define this variable later
    });
}

/**
 * Processes the allocation data to structure it for table population.
 * @param {Array} allocations - List of allocation records.
 */
function processStatistics(allocations) {
    lastFetchedAllocations = allocations; 

    const filteredAllocations = currentTeamFilter === 'All' 
        ? allocations 
        : allocations.filter(alloc => alloc.team === currentTeamFilter);
    const timesTable = document.getElementById('times-table');
    const pitchesTable = document.getElementById('pitches-table');
    const startTimeFreqTable = document.getElementById('start-time-frequency-table');
    const pitchUsageFreqTable = document.getElementById('pitch-usage-frequency-table');

    // Clear existing table contents, including headers
    [timesTable, pitchesTable, startTimeFreqTable, pitchUsageFreqTable].forEach(table => {
        table.innerHTML = '<thead><tr><th>Team Name</th></tr></thead><tbody></tbody>';
    });

    // Re-select table bodies after clearing
    const timesTableBody = timesTable.querySelector('tbody');
    const pitchesTableBody = pitchesTable.querySelector('tbody');
    const startTimeFreqTableBody = startTimeFreqTable.querySelector('tbody');
    const pitchUsageFreqTableBody = pitchUsageFreqTable.querySelector('tbody');

    // Use filteredAllocations instead of allocations
    const teamNames = currentTeamFilter === 'All' ? allTeamNames : [currentTeamFilter];
    const dates = Array.from(new Set(allocations.map(alloc => alloc.date))).sort();
    const startTimes = Array.from(new Set(allocations.map(alloc => alloc.time))).sort();
    const pitchNames = Array.from(new Set(allocations.map(alloc => alloc.pitch))).sort();

    // Structure allocations by team and date
    const allocationsByTeamDate = {};
    filteredAllocations.forEach(alloc => {
        if (!allocationsByTeamDate[alloc.team]) {
            allocationsByTeamDate[alloc.team] = {};
        }
        allocationsByTeamDate[alloc.team][alloc.date] = alloc;
    });

    // Populate Match Start Times Table
    // Create table headers with dates
    const timesTableHead = document.querySelector('#times-table thead tr');
    dates.forEach(date => {
        const th = document.createElement('th');
        th.innerText = date;
        timesTableHead.appendChild(th);
    });

    // Populate table rows
    teamNames.forEach(team => {
        const row = document.createElement('tr');

        const teamCell = document.createElement('td');
        teamCell.innerText = team;
        row.appendChild(teamCell);

        dates.forEach(date => {
            const cell = document.createElement('td');
            if (allocationsByTeamDate[team] && allocationsByTeamDate[team][date]) {
                const alloc = allocationsByTeamDate[team][date];
                if (alloc.preferred) {
                    cell.innerText = alloc.time;
                    cell.classList.add('preferred-time');
                    cell.title = 'Preferred Time';
                } else {
                    cell.innerText = alloc.time;
                }
            } else {
                cell.innerText = '-';
            }
            row.appendChild(cell);
        });

        timesTableBody.appendChild(row);
    });

    // Structure allocations by team and date for Pitches
    // Populate Allocated Pitches Table
    const allocationsByTeamDateForPitch = allocationsByTeamDate; // Same structure

    // Create table headers with dates
    const pitchesTableHead = document.querySelector('#pitches-table thead tr');
    // Reuse existing dates, no need to recreate headers

    dates.forEach(date => {
        const th = document.createElement('th');
        th.innerText = date;
        pitchesTableHead.appendChild(th);
    });

    // Populate table rows
    teamNames.forEach(team => {
        const row = document.createElement('tr');

        const teamCell = document.createElement('td');
        teamCell.innerText = team;
        row.appendChild(teamCell);

        dates.forEach(date => {
            const cell = document.createElement('td');
            if (allocationsByTeamDateForPitch[team] && allocationsByTeamDateForPitch[team][date]) {
                const alloc = allocationsByTeamDateForPitch[team][date];
                cell.innerText = alloc.pitch;
            } else {
                cell.innerText = '-';
            }
            row.appendChild(cell);
        });

        pitchesTableBody.appendChild(row);
    });

    // Populate Start Time Frequency Table
    // Create headers with start times
    const startTimeFreqTableHead = document.querySelector('#start-time-frequency-table thead tr');
    startTimes.forEach(time => {
        const th = document.createElement('th');
        th.innerText = time;
        startTimeFreqTableHead.appendChild(th);
    });

    // Structure data for frequency
    const startTimeFrequency = {};
    teamNames.forEach(team => {
        startTimeFrequency[team] = {};
        startTimes.forEach(time => {
            startTimeFrequency[team][time] = 0;
        });
    });

    allocations.forEach(alloc => {
        if (startTimeFrequency[alloc.team] && startTimeFrequency[alloc.team][alloc.time] !== undefined) {
            startTimeFrequency[alloc.team][alloc.time]++;
        }
    });

    // Populate Start Time Frequency Table
    teamNames.forEach(team => {
        const row = document.createElement('tr');

        const teamCell = document.createElement('td');
        teamCell.innerText = team;
        row.appendChild(teamCell);

        startTimes.forEach(time => {
            const cell = document.createElement('td');
            cell.innerText = startTimeFrequency[team][time];
            row.appendChild(cell);
        });

        startTimeFreqTableBody.appendChild(row);
    });

    // Populate Pitch Usage Frequency Table
    // Create headers with pitch names
    const pitchUsageFreqTableHead = document.querySelector('#pitch-usage-frequency-table thead tr');
    pitchNames.forEach(pitch => {
        const th = document.createElement('th');
        th.innerText = pitch;
        pitchUsageFreqTableHead.appendChild(th);
    });

    // Structure data for frequency
    const pitchUsageFrequency = {};
    teamNames.forEach(team => {
        pitchUsageFrequency[team] = {};
        pitchNames.forEach(pitch => {
            pitchUsageFrequency[team][pitch] = 0;
        });
    });

    allocations.forEach(alloc => {
        if (pitchUsageFrequency[alloc.team] && pitchUsageFrequency[alloc.team][alloc.pitch] !== undefined) {
            pitchUsageFrequency[alloc.team][alloc.pitch]++;
        }
    });

    // Populate Pitch Usage Frequency Table
    teamNames.forEach(team => {
        const row = document.createElement('tr');

        const teamCell = document.createElement('td');
        teamCell.innerText = team;
        row.appendChild(teamCell);

        pitchNames.forEach(pitch => {
            const cell = document.createElement('td');
            cell.innerText = pitchUsageFrequency[team][pitch];
            row.appendChild(cell);
        });

        pitchUsageFreqTableBody.appendChild(row);
    });
}

function extractAgeGroup(teamName) {
    const match = teamName.match(/U(\d+)/);
    return match ? parseInt(match[1]) : 999; // Return a high number if no match found
}