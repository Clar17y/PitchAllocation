// frontend/api/api.js

import { API_ENDPOINTS } from './endpoints.js';

/**
 * Fetch data from a specified API endpoint with query parameters.
 * @param {string} endpoint - The API endpoint.
 * @param {object} queryParams - Key-value pairs for query parameters.
 * @returns {Promise<object>} - The fetched data.
 */
async function fetchData(endpoint, queryParams = {}) {
    const url = new URL(endpoint, window.location.origin);
    Object.keys(queryParams).forEach(key => url.searchParams.append(key, queryParams[key]));

    const response = await fetch(url, {
        method: 'GET',
        credentials: 'same-origin' // Ensure cookies are sent
    });

    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Failed to fetch data.');
    }

    return response.json();
}

/**
 * Fetch teams data specific to the current user.
 * @returns {Promise<Array>} - List of teams.
 */
export async function fetchTeams() {
    return fetchData(API_ENDPOINTS.TEAMS);
}

/**
 * Fetch pitches data specific to the current user.
 * @returns {Promise<Array>} - List of pitches.
 */
export async function fetchPitches() {
    return fetchData(API_ENDPOINTS.PITCHES);
}

/**
 * Fetch players data specific to the current user.
 * @returns {Promise<Array>} - List of players.
 */
export async function fetchPlayers() {
    return fetchData(API_ENDPOINTS.PLAYERS);
}

/**
 * Submit allocation data for the current user.
 * @param {Object} payload - Allocation data.
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