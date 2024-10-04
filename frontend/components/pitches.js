// frontend/components/pitches.js

import { fetchPitches } from '../api/api.js';
import { logMessage } from '../utils/logger.js';

let pitchesList = [];

export async function loadPitches() {
    try {
        const data = await fetchPitches();
        pitchesList = data;
        displayPitches();
    } catch (error) {
        logMessage(error.message, 'error');
    }
}

function displayPitches() {
    // Implement pitch display logic or reuse from allocationForm.js
}