// frontend/players_config.js

import { fetchConfigData, saveConfigData, deleteConfigData } from './api/configApi.js';
import { logMessage } from './utils/logger.js';
import { getCookie } from './utils/cookie.js';

// Check if user is authenticated
const username = getCookie('username');
if (!username) {
    alert('You must be logged in to access this page.');
    window.location.href = '/login.html';
}

// DOM Elements
const playersList = document.getElementById('players-list');
const playerForm = document.getElementById('player-details-form');
const createPlayerButton = document.getElementById('create-player-button');
const teamsDropdown = document.getElementById('player-team');
const toastContainer = document.getElementById('toast-container');
let allPlayers = [];
let allTeams = [];

/**
 * Initialize the Players Configuration Page
 */
document.addEventListener('DOMContentLoaded', async () => {
    const username = getCookie('username');
    if (!username) {
        alert('User not logged in. Redirecting to login.');
        location.href = '/';
        return;
    }

    document.getElementById('current-user-display').textContent = `Logged in as: ${username}`;
    document.getElementById('logout-button').style.display = 'inline-block';

    await loadTeams();
    await loadPlayers();

    // Handle Player Form Submission
    playerForm.addEventListener('submit', handlePlayerFormSubmit);

    // Handle Create Player Button
    createPlayerButton.addEventListener('click', handleCreatePlayer);

    // Handle Logout
    document.getElementById('logout-button').addEventListener('click', handleLogout);
});


/**
 * Load Teams to Populate the Teams Dropdown
 */
async function loadTeams() {
    try {
        const data = await fetchConfigData('teams', 'get', { username: getCookie('username') });
        allTeams = data.teams;
        populateTeamsDropdown();
    } catch (error) {
        logMessage(error.message, 'error');
    }
}

/**
 * Populate Teams Dropdown with format_label
 */
function populateTeamsDropdown() {
    teamsDropdown.innerHTML = '<option value="" disabled selected>Select Team</option>';
    allTeams.forEach(team => {
        const option = document.createElement('option');
        option.value = team.id;
        option.textContent = team.display_label || team.display_name || `${team.age_group} ${team.name}`;
        teamsDropdown.appendChild(option);
    });
}

/**
 * Load Players to Populate the Players List
 */
async function loadPlayers() {
    try {
        const data = await fetchConfigData('players', 'get', { username: getCookie('username') });
        allPlayers = data.players;
        displayPlayers();
    } catch (error) {
        logMessage(error.message, 'error');
    }
}

/**
 * Display Players in the List
 */
function displayPlayers() {
    playersList.innerHTML = '';
    allPlayers.forEach(player => {
        const team = allTeams.find(t => t.id === player.team_id);
        const teamLabel = team ? team.display_label || team.display_name || `${team.age_group} ${team.name}` : 'Unknown Team';

        const listItem = document.createElement('li');
        listItem.className = 'list-group-item d-flex justify-content-between align-items-center';
        listItem.dataset.playerId = player.id;

        // Player Info
        const playerInfo = document.createElement('div');
        playerInfo.innerHTML = `<strong>${player.first_name} ${player.surname}</strong> (#${player.shirt_number}) - <em>${teamLabel}</em>`;
        listItem.appendChild(playerInfo);

        // Delete Button
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'btn btn-danger btn-sm delete-btn';
        deleteBtn.innerHTML = '<i class="bi bi-dash-lg"></i>'; // Bootstrap Icons 'dash' icon
        deleteBtn.title = 'Delete';
        deleteBtn.addEventListener('click', (e) => {
            e.stopPropagation(); // Prevent triggering the list item click
            handleDeletePlayer(player);
        });
        listItem.appendChild(deleteBtn);

        // Click Event to Populate Form
        listItem.addEventListener('click', () => {
            populatePlayerForm(player);
        });

        playersList.appendChild(listItem);
    });
}

/**
 * Populate Player Details Form
 * @param {object} player 
 */
function populatePlayerForm(player) {
    document.getElementById('player-id').value = player.id;
    document.getElementById('player-first-name').value = player.first_name;
    document.getElementById('player-surname').value = player.surname;
    document.getElementById('player-shirt-number').value = player.shirt_number;
    document.getElementById('player-team').value = player.team_id;
    playerForm.dataset.editingId = player.id;
}

/**
 * Handle Player Form Submission
 * @param {Event} event 
 */
async function handlePlayerFormSubmit(event) {
    event.preventDefault();
    const username = getCookie('username');

    const playerId = playerForm.dataset.editingId ? parseInt(playerForm.dataset.editingId) : null;
    const firstName = document.getElementById('player-first-name').value.trim();
    const surname = document.getElementById('player-surname').value.trim();
    const teamId = parseInt(document.getElementById('player-team').value);
    const shirtNumber = parseInt(document.getElementById('player-shirt-number').value);

    // Frontend Validation (additional to backend)
    if (!firstName || !surname || !teamId || !shirtNumber) {
        showAlert('All fields are required.', 'warning');
        return;
    }

    const payload = {
        first_name: firstName,
        surname: surname,
        team_id: teamId,
        shirt_number: shirtNumber
    };

    try {
        if (playerId) {
            // Update existing player
            payload.id = playerId;
            const response = await saveConfigData('players', 'put', {}, payload);
            showAlert('Player updated successfully.', 'success');
        } else {
            // Create new player
            const response = await saveConfigData('players', 'post', {}, payload);
            showAlert('Player created successfully.', 'success');
        }

        // Refresh the players list
        await loadPlayers();

        // Reset the form
        playerForm.reset();
        delete playerForm.dataset.editingId;
    } catch (error) {
        logMessage(error.message, 'error');
        showAlert(`Error: ${error.message}`, 'danger');
    }
}

/**
 * Handle Create Player Button Click
 */
function handleCreatePlayer() {
    playerForm.reset();
    delete playerForm.dataset.editingId;
    showAlert('Create a new player by filling in the details and saving.', 'info');
}

/**
 * Handle Delete Player
 * @param {object} player 
 */
async function handleDeletePlayer(player) {
    const username = getCookie('username');
    if (!confirm(`Are you sure you want to delete ${player.first_name} ${player.surname}?`)) {
        return;
    }

    try {
        await deleteConfigData('players', 'delete', { username: username, id: player.id });
        showAlert('Player deleted successfully.', 'success');
        await loadPlayers();

        // If the deleted player was being edited, reset the form
        if (playerForm.dataset.editingId == player.id) {
            playerForm.reset();
            delete playerForm.dataset.editingId;
        }
    } catch (error) {
        logMessage(error.message, 'error');
        showAlert(`Error: ${error.message}`, 'danger');
    }
}

/**
 * Show Alert (Toast Notification)
 * @param {string} message 
 * @param {string} type - 'success', 'danger', 'warning', 'info'
 */
function showAlert(message, type) {
    const bgClass = {
        'success': 'bg-success',
        'danger': 'bg-danger',
        'warning': 'bg-warning text-dark',
        'info': 'bg-info'
    }[type] || 'bg-secondary';

    const toastEl = document.createElement('div');
    toastEl.className = `toast align-items-center text-white ${bgClass} border-0`;
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');

    toastEl.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;

    toastContainer.appendChild(toastEl);

    // Initialize and show the toast
    const toast = new bootstrap.Toast(toastEl, { delay: 5000 });
    toast.show();

    // Remove the toast from DOM after it's hidden
    toastEl.addEventListener('hidden.bs.toast', () => {
        toastEl.remove();
    });
}

/**
 * Handle Logout
 */
function handleLogout() {
    eraseCookie('username');
    location.reload();
}


/**
 * Get Cookie by Name
 * @param {string} name 
 * @returns {string|null}
 */
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
}

/**
 * Erase Cookie by Name
 * @param {string} name 
 */
function eraseCookie(name) {   
    document.cookie = `${name}=; Max-Age=-99999999;`;  
}