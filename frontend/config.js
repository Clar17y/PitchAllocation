// frontend/config.js

import { fetchTeams, fetchPitches } from './api/api.js';
import { saveConfigData, deleteConfigData } from './api/configApi.js';
import { logMessage } from './utils/logger.js';
import { getCookie, eraseCookie } from './utils/cookie.js';

let currentUser = '';
let allPitches = [];         // Stores all available pitches
let allTeams = [];
let selectedOverlaps = [];   // Stores selected overlap pitch IDs

document.addEventListener('DOMContentLoaded', function() {
    currentUser = getCookie('username');
    if (!currentUser) {
        alert('User not logged in. Redirecting to login.');
        location.href = '/';
        return;
    }

    document.getElementById('current-user-display').textContent = `Logged in as: ${currentUser}`;
    document.getElementById('logout-button').style.display = 'inline-block';

    loadPitches();
    loadTeams();

    // Handle Pitch Form Submission
    const pitchForm = document.getElementById('pitch-details-form');
    pitchForm.addEventListener('submit', handlePitchFormSubmit);

    // Handle Team Form Submission
    const teamForm = document.getElementById('team-details-form');
    teamForm.addEventListener('submit', handleTeamFormSubmit);

    // Handle Create Buttons
    document.getElementById('create-pitch-button').addEventListener('click', handleCreatePitch);
    document.getElementById('create-team-button').addEventListener('click', handleCreateTeam);

    // Handle Logout
    document.getElementById('logout-button').addEventListener('click', handleLogout);

    // Initialize Overlaps With multi-select functionality
    initializeOverlapsWith();
});


/**
 * Load Pitches from Backend
 */
async function loadPitches() {
    try {
        const data = await fetchPitches(currentUser);
        allPitches = data.pitches; // Store all pitches

        allPitches.sort((a,b) => a.capacity - b.capacity);

        populateList('pitches-list', allPitches, displayPitchDetails, 'pitches', formatPitchLabel);
        updateOverlapsDropdown(); // Update dropdown with available pitches
    } catch (error) {
        logMessage(error.message, 'error');
    }
}


/**
 * Load Teams from Backend
 */
async function loadTeams() {
    try {
        const data = await fetchTeams(currentUser);
        allTeams = data.teams;

        // Sort teams by age_group
        allTeams.sort((a, b) => {
            const ageGroups = [
                "Under7s", "Under8s", "Under9s", "Under10s", "Under11s",
                "Under12s", "Under13s", "Under14s", "Under15s", "Under16s",
                "Under17/18s"
            ];
            return ageGroups.indexOf(a.age_group) - ageGroups.indexOf(b.age_group);
        });

        populateList('teams-list', allTeams, displayTeamDetails, 'teams', formatTeamLabel);
    } catch (error) {
        logMessage(error.message, 'error');
    }
}


/**
 * Populate List Function
 */
function populateList(listId, items, onClickCallback, type, labelFunction) {
    const list = document.getElementById(listId);
    list.innerHTML = ''; // Clear existing items

    items.forEach(item => {
        const listItem = document.createElement('li');
        listItem.className = 'list-group-item list-group-item-action d-flex justify-content-between align-items-center';
        listItem.textContent = labelFunction? labelFunction(item) : item.name;
        listItem.dataset.id = item.id; // Assuming each item has a unique 'id' field

        // Click event to display details
        listItem.addEventListener('click', () => onClickCallback(item));

        // Delete button
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'btn btn-danger btn-sm delete-btn';
        deleteBtn.innerHTML = '<i class="bi bi-dash-lg"></i>'; // Bootstrap Icons 'dash' icon
        deleteBtn.title = 'Delete';

        // Prevent triggering the list item's click when clicking the delete button
        deleteBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            handleDeleteItem(item, type);
        });


        listItem.appendChild(deleteBtn);
        list.appendChild(listItem);

        // Add swipe-to-delete functionality for mobile
        addSwipeToDelete(listItem, item.id, type);
    });
}


/**
 * Initialize Overlaps With Multi-Select Functionality
 */
function initializeOverlapsWith() {
    const overlapsInput = document.getElementById('pitch-overlaps-input');
    const overlapsDropdown = document.getElementById('overlaps-dropdown');
    const selectedOverlapsContainer = document.getElementById('selected-overlaps');

    // Show dropdown when the container is focused or clicked
    selectedOverlapsContainer.addEventListener('click', () => {
        overlapsInput.focus();
        showOverlapsDropdown();
    });


    overlapsInput.addEventListener('input', () => {
        showOverlapsDropdown();
        filterOverlapsDropdown(overlapsInput.value.trim());
    });

    overlapsInput.addEventListener('keydown', (e) => {
        if (e.key === 'Backspace' && overlapsInput.value === '' && selectedOverlaps.length > 0) {
            // Remove the last selected overlap
            removeOverlap(selectedOverlaps[selectedOverlaps.length - 1]);
        }
    });

    // Hide dropdown when clicking outside
    document.addEventListener('click', (e) => {
        if (!selectedOverlapsContainer.contains(e.target) && !overlapsDropdown.contains(e.target)) {
            hideOverlapsDropdown();
        }
    });
}


/**
 * Show Overlaps Dropdown
 */
function showOverlapsDropdown() {
    const overlapsDropdown = document.getElementById('overlaps-dropdown');
    overlapsDropdown.classList.add('show');
}


/**
 * Hide Overlaps Dropdown
 */
function hideOverlapsDropdown() {
    const overlapsDropdown = document.getElementById('overlaps-dropdown');
    overlapsDropdown.classList.remove('show');
}


/**
 * Update Overlaps Dropdown with Available Pitches
 */
function updateOverlapsDropdown() {
    const overlapsDropdown = document.getElementById('overlaps-dropdown');
    overlapsDropdown.innerHTML = ''; // Clear existing dropdown items

    // Filter available pitches (not already selected)
    const availablePitches = allPitches.filter(pitch => !selectedOverlaps.includes(pitch.id));

    if (availablePitches.length === 0) {
        const noOption = document.createElement('li');
        noOption.textContent = 'No more pitches available';
        noOption.className = 'text-muted';
        overlapsDropdown.appendChild(noOption);
        return;
    }

    availablePitches.forEach(pitch => {
        const option = document.createElement('li');
        option.textContent = pitch.name;
        option.dataset.id = pitch.id;
        option.addEventListener('click', () => {
            addOverlap(pitch.id, pitch.name);
            overlapsInput.value = '';
            overlapsInput.focus();
        });
        overlapsDropdown.appendChild(option);
    });
}


/**
 * Filter Overlaps Dropdown Based on Input
 * @param {string} filterText 
 */
function filterOverlapsDropdown(filterText) {
    const overlapsDropdown = document.getElementById('overlaps-dropdown');
    const items = overlapsDropdown.querySelectorAll('li');

    items.forEach(item => {
        if (item.textContent.toLowerCase().includes(filterText.toLowerCase())) {
            item.style.display = 'block';
        } else {
            item.style.display = 'none';
        }
    });
}


/**
 * Add Overlap to Selected Overlaps
 * @param {number} id 
 * @param {string} name 
 */
function addOverlap(id, name) {
    if (selectedOverlaps.includes(id)) return; // Prevent duplicates

    selectedOverlaps.push(id);
    renderSelectedOverlaps();
    updateOverlapsDropdown();
}


/**
 * Remove Overlap from Selected Overlaps
 * @param {number} id 
 */
function removeOverlap(id) {
    const index = selectedOverlaps.indexOf(id);
    if (index > -1) {
        selectedOverlaps.splice(index, 1);
        renderSelectedOverlaps();
        updateOverlapsDropdown();
    }
}


/**
 * Render Selected Overlaps as Tags
 */
function renderSelectedOverlaps() {
    const selectedOverlapsContainer = document.getElementById('selected-overlaps');
    // Clear existing tags except the input
    selectedOverlapsContainer.querySelectorAll('.badge').forEach(badge => badge.remove());

    selectedOverlaps.forEach(id => {
        const pitch = allPitches.find(p => p.id === id);
        if (pitch) {
            const badge = document.createElement('span');
            badge.className = 'badge bg-primary';
            badge.textContent = pitch.name;

            const removeIcon = document.createElement('span');
            removeIcon.innerHTML = '&times;';
            removeIcon.style.cursor = 'pointer';
            removeIcon.style.marginLeft = '5px';
            removeIcon.addEventListener('click', (e) => {
                e.stopPropagation();
                removeOverlap(id);
            });

            badge.appendChild(removeIcon);
            selectedOverlapsContainer.insertBefore(badge, document.getElementById('pitch-overlaps-input'));
        }
    });
}


/**
 * Display Pitch Details
 */
function displayPitchDetails(pitch) {
    document.getElementById('pitch-id').value = pitch.id;
    document.getElementById('pitch-name').value = pitch.name;
    document.getElementById('pitch-capacity').value = pitch.capacity;
    document.getElementById('pitch-location').value = pitch.location;
    document.getElementById('pitch-cost').value = pitch.cost || 0;
    
    // Initialize selectedOverlaps based on pitch.overlaps_with
    // Assuming pitch.overlaps_with is an array of overlapping pitch IDs
    selectedOverlaps = pitch.overlaps_with;
    
    renderSelectedOverlaps();
    updateOverlapsDropdown();

    // Store current editing pitch ID
    document.getElementById('pitch-details-form').dataset.editingId = pitch.id;
}


/**
 * Display Team Details
 */
function displayTeamDetails(team) {
    document.getElementById('team-id').value = team.id;
    document.getElementById('team-name').value = team.name;
    document.getElementById('team-age-group').value = team.age_group;
    document.getElementById('team-gender').value = team.gender;
    // Store current editing team ID
    document.getElementById('team-details-form').dataset.editingId = team.id;
}


/**
 * Handle Pitch Form Submission
 */
async function handlePitchFormSubmit(event) {
    event.preventDefault();
    const pitchForm = event.target;

    const newPitchData = {
        name: document.getElementById('pitch-name').value.trim(),
        capacity: parseInt(document.getElementById('pitch-capacity').value, 10),
        location: document.getElementById('pitch-location').value.trim(),
        cost: parseFloat(document.getElementById('pitch-cost').value) || 0,
        overlaps_with: selectedOverlaps // Send array of selected overlap pitch IDs
    };

    // Frontend Validation
    const validationError = validatePitchData(newPitchData, pitchForm.dataset.editingId);
    if (validationError) {
        showAlert(validationError, 'warning');
        return;
    }

    // Generate format_label for the new pitch
    const newPitchFormatLabel = formatPitchLabel(newPitchData);

    // Check for duplicate format_label
    const duplicatePitch = allPitches.find(pitch => formatPitchLabel(pitch) === newPitchFormatLabel && (!pitchForm.dataset.editingId || pitch.id !== parseInt(pitchForm.dataset.editingId, 10)));
    if (duplicatePitch) {
        showAlert('A pitch with the same name and capacity already exists.', 'warning');
        return;
    }

    // Check if maximum number of pitches is reached
    if (!pitchForm.dataset.editingId && allPitches.length >= 40) {
        showAlert('Maximum number of pitches (40) reached. Cannot create more pitches.', 'danger');
        return;
    }

    try {
        if (pitchForm.dataset.editingId) {
            // Update existing pitch
            newPitchData.id = parseInt(pitchForm.dataset.editingId, 10);
            await saveConfigData('pitches', 'put', { username: currentUser }, newPitchData);
            showAlert('Pitch updated successfully.', 'success');
        } else {
            // Create new pitch
            const response = await saveConfigData('pitches', 'post', { username: currentUser }, newPitchData);
            showAlert('Pitch created successfully.', 'success');
            // Set the new ID in the form
            if (response.pitch && response.pitch.id) {
                document.getElementById('pitch-id').value = response.pitch.id;
            } else {
                console.warn("No pitch data returned from backend.")
            }
        }
        // Reload pitches
        await loadPitches();
        // Reset form
        pitchForm.reset();
        selectedOverlaps = [];
        renderSelectedOverlaps();
        delete pitchForm.dataset.editingId;
        // Clear the 'pitch-id' input field
        const pitchIdField = document.getElementById('pitch-id');
        if (pitchIdField) {
            pitchIdField.value = '';
        }
    } catch (error) {
        logMessage(error.message, 'error');
        showAlert(`Error: ${error.message}`, 'danger');
    }
}


/**
 * Handle Team Form Submission
 */
async function handleTeamFormSubmit(event) {
    event.preventDefault();
    const teamForm = event.target;

    const newTeamData = {
        name: document.getElementById('team-name').value.trim().toUpperCase(),
        age_group: document.getElementById('team-age-group').value.trim(),
        gender: document.getElementById('team-gender').value
    };

    // Frontend Validation
    const validationError = validateTeamData(newTeamData, teamForm.dataset.editingId);
    if (validationError) {
        showAlert(validationError, 'warning');
        return;
    }

    // Generate format_label for the new team
    const newTeamFormatLabel = formatTeamLabel(newTeamData);
    // Check for duplicate format_label
    const duplicateTeam = allTeams.find(team => formatTeamLabel(team) === newTeamFormatLabel && (!teamForm.dataset.editingId || team.id !== parseInt(teamForm.dataset.editingId, 10)));
    if (duplicateTeam) {
        showAlert('A team with the same name, age group, and gender already exists.', 'warning');
        return;
    }

    // Check if maximum number of teams is reached
    if (!teamForm.dataset.editingId && allTeams.length >= 100) {
        showAlert('Maximum number of teams (100) reached. Cannot create more teams.', 'danger');
        return;
    }

    try {
        if (teamForm.dataset.editingId) {
            // Update existing team
            newTeamData.id = parseInt(teamForm.dataset.editingId, 10);
            await saveConfigData('teams', 'put', { username: currentUser }, newTeamData);
            showAlert('Team updated successfully.', 'success');
        } else {
            // Create new team
            await saveConfigData('teams', 'post', { username: currentUser }, newTeamData);
            showAlert('Team created successfully.', 'success');
        }
        // Reload teams
        await loadTeams();
        // Reset form
        teamForm.reset();
        delete teamForm.dataset.editingId;
    } catch (error) {
        logMessage(error.message, 'error');
        showAlert(`Error: ${error.message}`, 'danger');
    }
}


/**
 * Handle Create Pitch Button
 */
function handleCreatePitch() {
    const pitchForm = document.getElementById('pitch-details-form');
    pitchForm.reset();
    selectedOverlaps = [];
    renderSelectedOverlaps();
    updateOverlapsDropdown();
    delete pitchForm.dataset.editingId;
    showAlert('Create a new pitch by filling in the details and saving.', 'info');
}


/**
 * Handle Create Team Button
 */
function handleCreateTeam() {
    const teamForm = document.getElementById('team-details-form');
    teamForm.reset();
    delete teamForm.dataset.editingId;
    showAlert('Create a new team by filling in the details and saving.', 'info');
}


/**
 * Handle Logout
 */
function handleLogout() {
    eraseCookie('username');
    location.reload();
}


/**
 * Display Alert Messages as Toasts
 * @param {string} message - The message to display.
 * @param {string} type - Bootstrap toast background class: 'bg-success', 'bg-danger', 'bg-warning', 'bg-info'.
 */
function showAlert(message, type) {
    const toastContainer = document.getElementById('toast-container');
    // Map alert types to Bootstrap background classes
    const bgClasses = {
        'success': 'bg-success',
        'danger': 'bg-danger',
        'warning': 'bg-warning',
        'info': 'bg-info'
    };

    const bgClass = bgClasses[type] || 'bg-primary'; // Default to primary if type not found

    // Create toast element
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
 * Handle Delete Item (Pitch or Team)
 * @param {number} id - The ID of the item to delete.
 * @param {string} type - 'pitches' or 'teams'.
 */
async function handleDeleteItem(item, type) {
    let nonPluralType = (type === "teams") ? "team" : "pitch";
    if (!confirm(`Are you sure you want to delete ${item.name}?`)) {
        return;
    }

    try {
        await deleteConfigData(type, 'delete', { username: currentUser, id: item.id });
        showAlert(`${capitalizeFirstLetter(nonPluralType)}` + ` deleted successfully.`, 'success');
        // Reload the list
        if (type === 'pitches') {
            loadPitches();
            const pitchForm = document.getElementById('pitch-details-form');
            pitchForm.reset();
            delete pitchForm.dataset.editingId;
            // Clear the 'pitch-id' input field
            const pitchIdField = document.getElementById('pitch-id');
            if (pitchIdField) {
                pitchIdField.value = '';
            }
        } else if (type === 'teams') {
            loadTeams();
            const teamForm = document.getElementById('team-details-form');
            teamForm.reset();
            delete teamForm.dataset.editingId;
            // Clear the 'pitch-id' input field
            const teamIdField = document.getElementById('team-id');
            if (teamIdField) {
                teamIdField.value = '';
            }
        }
    } catch (error) {
        logMessage(error.message, 'error');
        showAlert(`Error: ${error.message}`, 'danger');
    }
}


/**
 * Add Swipe-to-Delete Functionality
 * @param {HTMLElement} listItem - The list item element.
 * @param {number} id - The ID of the item.
 * @param {string} type - 'pitches' or 'teams'.
 */
function addSwipeToDelete(listItem, id, type) {
    let touchStartX = 0;
    let touchEndX = 0;

    listItem.addEventListener('touchstart', function(event) {
        touchStartX = event.changedTouches[0].screenX;
    }, false);

    listItem.addEventListener('touchend', function(event) {
        touchEndX = event.changedTouches[0].screenX;
        handleGesture();
    }, false);

    function handleGesture() {
        if (touchEndX < touchStartX - 50) { // Swipe left by at least 50px
            listItem.classList.add('show-delete');
            // Optionally, you can add a timeout to hide the delete button
            setTimeout(() => {
                listItem.classList.remove('show-delete');
            }, 3000);
        }
    }
}

/**
 * Generate format_label for Pitch
 * @param {object} pitch 
 * @returns {string}
 */
function formatPitchLabel(pitch) {
    // Assuming format_label follows the model's format_label method
    return `${pitch.capacity}aside - ${pitch.name}`;
}

/**
 * Generate format_label for Team
 * @param {object} team 
 * @returns {string}
 */
function formatTeamLabel(team) {
    return `${team.age_group} ${team.name}` + (team.gender === 'Girls' ? ` (Girls)` : ``)
}

/**
 * Validate Pitch Data
 * @param {object} data 
 * @param {number|string} editingId
 * @returns {string|null} - Returns error message or null if valid
 */
function validatePitchData(data, editingId) {
    // Limit lengths
    if (data.name.length > 50) return 'Pitch name must be 50 characters or fewer.';
    if (data.location.length > 100) return 'Pitch location must be 100 characters or fewer.';
    if (data.cost < 0 || data.cost > 10000) return 'Pitch cost must be between £0 and £10,000.';

    // Alphanumeric checks (allowing spaces, hyphens, underscores and brackets)
    const alphaNumRegex = /^[a-zA-Z0-9\s()_-]+$/;
    if (!alphaNumRegex.test(data.name)) return 'Pitch name contains invalid characters.';
    if (!alphaNumRegex.test(data.location)) return 'Pitch location contains invalid characters.';

    return null; // No errors
}

/**
 * Validate Team Data
 * @param {object} data 
 * @param {number|string} editingId
 * @returns {string|null} - Returns error message or null if valid
 */
function validateTeamData(data, editingId) {
    // Limit lengths
    if (data.name.length > 50) return 'Team name must be 50 characters or fewer.';
    if (data.age_group.length > 20) return 'Age group must be 20 characters or fewer.';
    if (data.gender.length > 10) return 'Gender must be 10 characters or fewer.';

    // Alphanumeric checks (allowing spaces, hyphens, underscores and brackets)
    const alphaNumRegex = /^[a-zA-Z0-9\s()_-]+$/;
    if (!alphaNumRegex.test(data.name)) return 'Team name contains invalid characters.';
    if (!alphaNumRegex.test(data.age_group)) return 'Age group contains invalid characters.';
    if (!alphaNumRegex.test(data.gender)) return 'Gender contains invalid characters.';

    return null; // No errors
}

/**
 * Capitalize the first letter of a string
 * @param {string} string 
 * @returns {string}
 */
function capitalizeFirstLetter(string) {
    return string.charAt(0).toUpperCase() + string.slice(1);
}