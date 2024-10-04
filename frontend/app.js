// frontend/app.js

import { initializeFormComponents, clearSelections } from './components/allocationForm.js';
import { initializeStatistics } from './components/statistics.js';
import { copyResults } from './utils/helpers.js';
import { setCookie, getCookie, eraseCookie } from './utils/cookie.js';

document.addEventListener('DOMContentLoaded', function() {
    const username = getCookie('username');
    if (!username) {
        // Show login modal if username is not set
        const loginModal = new bootstrap.Modal(document.getElementById('loginModal'), {
            backdrop: 'static',
            keyboard: false
        });
        loginModal.show();
    } else {
        // Initialize the app for the logged-in user
        initializeApp(username);
    }

    // Handle login form submission
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', function(event) {
            event.preventDefault();
            const usernameInput = document.getElementById('username-input').value.trim();
            const sanitizedUsername = sanitizeUsername(usernameInput);
            if (sanitizedUsername) {
                setCookie('username', sanitizedUsername, 7); // Expires in 7 days
                document.getElementById('current-user-display').textContent = `Logged in as: ${sanitizedUsername}`;
                const loginModalInstance = bootstrap.Modal.getInstance(document.getElementById('loginModal'));
                loginModalInstance.hide();
                initializeApp(sanitizedUsername);
            } else {
                alert('Invalid username. Please use alphanumeric characters only.');
            }
        });
    } else {
        console.error('Login form element not found!');
    }

    // Handle logout
    const logoutButton = document.getElementById('logout-button');
    logoutButton.addEventListener('click', function() {
        eraseCookie('username');
        location.reload();
    });
});

/**
 * Initializes the application after successful login.
 * @param {string} username - The logged-in user's name.
 */
function initializeApp(username) {
    document.getElementById('current-user-display').textContent = `Logged in as: ${username}`;
    document.getElementById('logout-button').style.display = 'inline-block';

    if (!window.location.pathname.endsWith('statistics.html')) {
        initializeFormComponents(username);
        
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
        initializeStatistics(username);
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