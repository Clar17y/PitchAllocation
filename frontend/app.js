// frontend/app.js

import { initializeFormComponents, clearSelections } from './components/allocationForm.js';
import { initializeStatistics } from './components/statistics.js';
import { copyResults } from './utils/helpers.js';
import { initializeLogoutButton, loadCurrentUser } from './shared.js';

document.addEventListener('DOMContentLoaded', async() => {
    loadCurrentUser();
    initializeLogoutButton();

    initializeApp();
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