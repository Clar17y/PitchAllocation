// frontend/components/statistics.js

import { fetchStatisticsData } from '../api/api.js';
import { logMessage } from '../utils/logger.js';
import { extractAgeGroup } from '../utils/helpers.js';

let allTeamNames = [];
let currentTeamFilter = 'All';
let lastFetchedAllocations = [];

export async function initializeStatistics() {
    try {
        const allocations = await fetchStatisticsData(); // No parameter needed
        processStatistics(allocations);
        populateTeamSelect();
    } catch (error) {
        logMessage(error.message, 'error');
    }
}

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
        processStatistics(lastFetchedAllocations);
    });
}

// Add this helper function at the top of your file
function formatTime(timeString) {
    return timeString.substring(0, 5); // This will return just the HH:MM part
}

export function processStatistics(allocations) {
    lastFetchedAllocations = allocations;

    allTeamNames = Array.from(new Set(allocations.map(alloc => alloc.team_name)))
        .sort((a, b) => {
            const ageA = extractAgeGroup(a);
            const ageB = extractAgeGroup(b);
            if (ageA === ageB) {
                return a.localeCompare(b);
            }
            return ageA - ageB;
        });

    const filteredAllocations = currentTeamFilter === 'All' 
        ? allocations 
        : allocations.filter(alloc => alloc.team_name === currentTeamFilter);

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

    const teamNames = currentTeamFilter === 'All' ? allTeamNames : [currentTeamFilter];
    const dates = Array.from(new Set(allocations.map(alloc => alloc.date))).sort();
    const startTimes = Array.from(new Set(allocations.map(alloc => formatTime(alloc.start_time)))).sort();
    const pitchNames = Array.from(new Set(allocations.map(alloc => alloc.pitch_name))).sort();

    // Structure allocations by team and date
    const allocationsByTeamDate = {};
    filteredAllocations.forEach(alloc => {
        if (!allocationsByTeamDate[alloc.team_name]) {
            allocationsByTeamDate[alloc.team_name] = {};
        }
        allocationsByTeamDate[alloc.team_name][alloc.date] = alloc;
    });

    // Populate Match Start Times Table
    const timesTableHead = timesTable.querySelector('thead tr');
    dates.forEach(date => {
        const th = document.createElement('th');
        th.innerText = date;
        timesTableHead.appendChild(th);
    });

    teamNames.forEach(team => {
        const row = document.createElement('tr');
        const teamCell = document.createElement('td');
        teamCell.innerText = team;
        row.appendChild(teamCell);

        dates.forEach(date => {
            const cell = document.createElement('td');
            if (allocationsByTeamDate[team] && allocationsByTeamDate[team][date]) {
                const alloc = allocationsByTeamDate[team][date];
                cell.innerText = formatTime(alloc.start_time);
                if (alloc.preferred) {
                    cell.classList.add('preferred-time');
                    cell.title = 'Preferred Time';
                }
            } else {
                cell.innerText = '-';
            }
            row.appendChild(cell);
        });

        timesTableBody.appendChild(row);
    });

    // Populate Allocated Pitches Table
    const pitchesTableHead = pitchesTable.querySelector('thead tr');
    dates.forEach(date => {
        const th = document.createElement('th');
        th.innerText = date;
        pitchesTableHead.appendChild(th);
    });

    teamNames.forEach(team => {
        const row = document.createElement('tr');
        const teamCell = document.createElement('td');
        teamCell.innerText = team;
        row.appendChild(teamCell);

        dates.forEach(date => {
            const cell = document.createElement('td');
            if (allocationsByTeamDate[team] && allocationsByTeamDate[team][date]) {
                const alloc = allocationsByTeamDate[team][date];
                cell.innerText = alloc.pitch_name;
            } else {
                cell.innerText = '-';
            }
            row.appendChild(cell);
        });

        pitchesTableBody.appendChild(row);
    });

    // Populate Start Time Frequency Table
    const startTimeFreqTableHead = startTimeFreqTable.querySelector('thead tr');
    startTimes.forEach(time => {
        const th = document.createElement('th');
        th.innerText = time;
        startTimeFreqTableHead.appendChild(th);
    });

    const startTimeFrequency = {};
    teamNames.forEach(team => {
        startTimeFrequency[team] = {};
        startTimes.forEach(time => {
            startTimeFrequency[team][time] = 0;
        });
    });

    filteredAllocations.forEach(alloc => {
        const formattedTime = formatTime(alloc.start_time);
        if (startTimeFrequency[alloc.team_name]) {
            startTimeFrequency[alloc.team_name][formattedTime]++;
        }
    });

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
    const pitchUsageFreqTableHead = pitchUsageFreqTable.querySelector('thead tr');
    pitchNames.forEach(pitch => {
        const th = document.createElement('th');
        th.innerText = pitch;
        pitchUsageFreqTableHead.appendChild(th);
    });

    const pitchUsageFrequency = {};
    teamNames.forEach(team => {
        pitchUsageFrequency[team] = {};
        pitchNames.forEach(pitch => {
            pitchUsageFrequency[team][pitch] = 0;
        });
    });

    filteredAllocations.forEach(alloc => {
        if (pitchUsageFrequency[alloc.team_name]) {
            pitchUsageFrequency[alloc.team_name][alloc.pitch_name]++;
        }
    });

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
