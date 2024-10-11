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
    const groupedTeams = teams.reduce((groups, team) => {
        const ageGroup = team.display_name.split(' ')[0]; // Assuming the age group is the first part of the display name
        if (!groups[ageGroup]) {
            groups[ageGroup] = [];
        }
        groups[ageGroup].push(team);
        return groups;
    }, {});

    // Define a custom sorting function for age groups
    const sortAgeGroups = (a, b) => {
        const getAge = (group) => parseInt(group.substring(1)); // Extract the number from 'U7', 'U8', etc.
        return getAge(a) - getAge(b);
    };

    // Create a new object with sorted keys
    const sortedGroups = Object.keys(groupedTeams)
        .sort(sortAgeGroups)
        .reduce((sorted, key) => {
            sorted[key] = groupedTeams[key];
            return sorted;
        }, {});

    return sortedGroups
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