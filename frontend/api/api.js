// frontend/api/api.js

import { API_ENDPOINTS } from './endpoints.js';

/**
 * Fetch teams data specific to the current user.
 * @returns {Promise<Array>} - List of teams.
 */
export async function fetchTeams() {
    const response = await fetch(API_ENDPOINTS.TEAMS, {
        method: 'GET',
        credentials: 'same-origin' // Ensure cookies are sent
    });
    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Failed to fetch teams.');
    }
    const data = await response.json();
    return data.teams;
}

/**
 * Fetch pitches data specific to the current user.
 * @returns {Promise<Array>} - List of pitches.
 */
export async function fetchPitches() {
    const response = await fetch(API_ENDPOINTS.PITCHES, {
        method: 'GET',
        credentials: 'same-origin' // Ensure cookies are sent
    });
    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Failed to fetch pitches.');
    }
    const data = await response.json();
    return data.pitches;
}

/**
 * Submit allocation data for the current user.
 * @param {Object} payload - Allocation data including username.
 * @returns {Promise<Object>} - Response data.
 */
export async function submitAllocation(payload) {
    const response = await fetch(API_ENDPOINTS.ALLOCATE, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        credentials: 'same-origin' // Ensure cookies are sent
    });
    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Failed to submit allocation.');
    }
    return await response.json();
}

/**
 * Fetch statistics data specific to the current user.
 * Since the backend reads username from cookies, do not send username as a parameter.
 * @returns {Promise<Array>} - List of allocations.
 */
export async function fetchStatisticsData() {
    const response = await fetch(API_ENDPOINTS.STATISTICS, {
        method: 'GET',
        credentials: 'same-origin' // Ensure cookies are sent
    });
    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to fetch statistics.');
    }
    const data = await response.json();
    return data.allocations;
}