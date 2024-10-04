// frontend/utils/helpers.js

import { logMessage } from './logger.js';

export function generateTimeOptions() {
    const times = ["--:--"];
    for (let hour = 9; hour <= 18; hour++) {
        for (let minute = 0; minute < 60; minute += 15) {
            const time = `${hour.toString().padStart(2, '0')}:${minute.toString().padStart(2, '0')}`;
            times.push(time);
        }
    }
    return times;
}

export function extractAgeGroup(teamName) {
    const match = teamName.match(/U(\d+)/);
    return match ? parseInt(match[1]) : 999; // Return a high number if no match found
}

export function groupTeamsByAgeGroup(teams) {
    return teams.reduce((groups, team) => {
        const ageGroup = team.display_name.split(' ')[0]; // Assuming the age group is the first part of the display name
        if (!groups[ageGroup]) {
            groups[ageGroup] = [];
        }
        groups[ageGroup].push(team);
        return groups;
    }, {});
}

export function copyResults() {
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