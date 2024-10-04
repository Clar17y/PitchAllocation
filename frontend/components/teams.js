// frontend/components/teams.js

import { fetchTeams, groupTeamsByAgeGroup } from '../api/api.js';
import { logMessage } from '../utils/logger.js';

let teamsList = [];

export async function loadTeams() {
    try {
        const data = await fetchTeams();
        teamsList = data;
        displayTeams();
    } catch (error) {
        logMessage(error.message, 'error');
    }
}

function displayTeams() {
    // Implement team display logic or reuse from allocationForm.js
}