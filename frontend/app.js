// frontend/app.js

import { initializeFormComponents, clearSelections } from './components/allocationForm.js';
import { initializeStatistics } from './components/statistics.js';
import { copyResults } from './utils/helpers.js';
import { setCookie, getCookie, eraseCookie } from './utils/cookie.js';

let currentUser = '';

document.addEventListener('DOMContentLoaded', async() => {
    try {
        const response = await fetch('/api/current_user', {
            method: 'GET',
            credentials: 'include'  
        });

        if (response.status === 200) {
            const data = await response.json();
            currentUser = data.name;
            document.getElementById('current-user-display').textContent = `Logged in as: ${currentUser}`;
            document.getElementById('logout-button').style.display = 'inline-block';
            initializeApp();
        } else {
            // Redirect to login if not authenticated
            window.location.href = '/login.html';
        }
    } catch (error) {
        console.error('Error fetching current user:', error);
        window.location.href = '/login.html';
    }

    // Handle logout
    const logoutButton = document.getElementById('logout-button');
    logoutButton.addEventListener('click', function() {
        eraseCookie('username');
        location.reload();
    });
});


function initializeApp() {
    if (!window.location.pathname.endsWith('statistics.html')) {
        initializeFormComponents();
        
        // Attach clearSelections to the clear button
        const clearButton = document.getElementById('clear-button');
        if (clearButton) {
            clearButton.addEventListener('click', clearSelections);
        }

        // Attach copyResults to the copy button
        const copyButton = document.getElementById('copy-button');
        if (copyButton) {
            copyButton.addEventListener('click', copyResults);
        }
    } else {
        console.log('Fetching statistics');
        initializeStatistics();
    }
}

/**
 * Sanitizes the username to allow only alphanumeric characters.
 * @param {string} username - The input username.
 * @returns {string|null} - Sanitized username or null if invalid.
 */
function sanitizeUsername(username) {
    const regex = /^[a-zA-Z0-9]+$/;
    return regex.test(username) ? username : null;
}