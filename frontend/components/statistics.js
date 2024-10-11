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

export function processStatistics(allocations) {
    lastFetchedAllocations = allocations; 

    allTeamNames = Array.from(new Set(allocations.map(alloc => alloc.team)))
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