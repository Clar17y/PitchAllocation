// frontend/utils/logger.js

export function logMessage(message, level = 'info') {
    const logsContainer = document.getElementById('console-logs');
    const p = document.createElement('p');
    p.innerText = `[${level.toUpperCase()}] ${message}`;
    p.className = `text-${level === 'error' ? 'danger' : level === 'warning' ? 'warning' : level === 'success' ? 'success' : 'secondary'}`;
    logsContainer.appendChild(p);
}