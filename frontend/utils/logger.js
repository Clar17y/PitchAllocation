// frontend/utils/logger.js

/**
 * Log Message to Console Logs Container
 * @param {string} message - The log message.
 * @param {string} level - Log level: 'info', 'warning', 'error', 'success'.
 */
export function logMessage(message, level = 'info') {
    const logsContainer = document.getElementById('console-logs');
    if (logsContainer) {
        const p = document.createElement('p');
        p.innerText = `[${level.toUpperCase()}] ${message}`;
        // Map 'success' to Bootstrap's 'success' text class
        p.className = `text-${
            level === 'error' ? 'danger' :
            level === 'warning' ? 'warning' :
            level === 'success' ? 'success' :
            'secondary'
        }`;
        logsContainer.appendChild(p);
    } else {
        // Define a mapping from custom levels to console methods
        const consoleLevels = {
            'info': 'info',
            'warning': 'warn',
            'error': 'error',
            'success': 'log' // Map 'success' to 'log' or 'info'
        };

        // Fallback to 'log' if the level is unrecognized
        const consoleMethod = consoleLevels[level] || 'log';

        console[consoleMethod](message);
    }
}