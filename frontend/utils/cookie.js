// frontend/utils/cookie.js

/**
 * Sets a cookie with the given name, value, and expiration in days.
 * @param {string} name - Cookie name.
 * @param {string} value - Cookie value.
 * @param {number} days - Number of days until the cookie expires.
 */
export function setCookie(name, value, days) {
    const expires = days ? `; expires=${new Date(Date.now() + days * 86400000).toUTCString()}` : '';
    document.cookie = `${name}=${value || ''}${expires}; path=/`;
}

/**
 * Retrieves the value of a cookie by name.
 * @param {string} name - Cookie name.
 * @returns {string|null} - Cookie value or null if not found.
 */
export function getCookie(name) {
    const nameEQ = `${name}=`;
    const ca = document.cookie.split(';');
    for(let c of ca) {
        while (c.charAt(0) === ' ') c = c.substring(1, c.length);
        if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length);
    }
    return null;
}

/**
 * Deletes a cookie by name.
 * @param {string} name - Cookie name.
 */
export function eraseCookie(name) {   
    document.cookie = `${name}=; Max-Age=-99999999; path=/`;  
}