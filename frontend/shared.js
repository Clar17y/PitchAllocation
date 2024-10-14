import { logMessage } from './utils/logger.js';

/**
 * Display Alert Messages as Toasts
 * @param {string} message - The message to display.
 * @param {string} type - The type of alert ('success', 'danger', etc.).
 */
export function showAlert(message, type) {
    const toastContainer = document.getElementById('toast-container');
    if (!toastContainer) return;

    const bgClasses = {
        success: 'bg-success',
        danger: 'bg-danger',
        warning: 'bg-warning',
        info: 'bg-info',
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
 * Handle Logout Button Click
 */
export async function handleLogout() {
    try {
        const response = await fetch('/logout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include' 
        });

        if (response.ok) {
            showAlert('Logged out successfully.', 'success');
            // Redirect to login page after a short delay
            setTimeout(() => {
                window.location.href = '/login.html';
            }, 1500);
        } else {
            const errorData = await response.json();
            showAlert(`Error: ${errorData.error || 'Logout failed.'}`, 'danger');
        }
    } catch (error) {
        logMessage(error.message, 'error');
        showAlert(`Error: ${error.message}`, 'danger');
    }
}

/**
 * Initialize Logout Button Event Listener
 */
export function initializeLogoutButton() {
    const logoutButton = document.getElementById('logout-button');
    if (logoutButton) {
        logoutButton.addEventListener('click', handleLogout);
    }
}

/**
 * Load and Display the Current User's Information
 */
export async function loadCurrentUser() {
    let currentUser = '';
    try {
        const response = await fetch('/api/current_user', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include' 
        });

        if (response.ok) {
            const data = await response.json();
            currentUser = data.name;
            const currentUserDisplay = document.getElementById('current-user-display');
            const logoutButton = document.getElementById('logout-button');
            if (data.name) {
                currentUserDisplay.textContent = `Logged in as: ${data.name}`;
                logoutButton.style.display = 'inline-block';
            } else {
                currentUserDisplay.textContent = '';
                logoutButton.style.display = 'none';
            }
        } else {
            console.error('Failed to fetch current user.');
        }
    } catch (error) {
        console.error('Error fetching current user:', error);
    }
    return currentUser;
}