// frontend/api/configApi.js

/**
 * Fetch Config Data
 * @param {string} configType - 'pitches' or 'teams'
 * @param {string} method - 'get', 'post', 'put', 'delete'
 * @param {object} queryParams - Additional query parameters
 * @param {object} payload - Data to send for 'post', 'put', or 'delete'
 * @returns {Promise<object>}
 */
export async function fetchConfigData(configType, method, queryParams = {}, payload = {}) {
    let url = `/api/config/${configType}`;
    
    // Append query parameters for GET and DELETE requests
    if (['get', 'delete'].includes(method.toLowerCase())) {
        const params = new URLSearchParams(queryParams);
        url += `?${params.toString()}`;
    }

    const options = {
        method: method.toUpperCase(),
        headers: {
            'Content-Type': 'application/json'
        }
    };

    if (['post', 'put', 'delete'].includes(method.toLowerCase())) {
        options.body = JSON.stringify(payload);
    }

    const response = await fetch(url, options);
    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Error ${response.status}: ${errorText}`);
    }

    return response.json();
}

/**
 * Save Config Data
 * @param {string} configType - 'pitches' or 'teams'
 * @param {string} method - 'post' or 'put'
 * @param {object} queryParams - Additional query parameters
 * @param {object} payload - Data to send
 * @returns {Promise<object>}
 */
export async function saveConfigData(configType, method, queryParams = {}, payload = {}) {
    return fetchConfigData(configType, method, queryParams, payload);
}

/**
 * Delete Config Data
 * @param {string} configType - 'pitches' or 'teams'
 * @param {string} method - 'delete'
 * @param {object} queryParams - Query parameters must include 'id' and 'username'
 * @returns {Promise<object>}
 */
export async function deleteConfigData(configType, method, queryParams = {}) {
    if (method.toLowerCase() !== 'delete') {
        throw new Error('Invalid method for deleteConfigData. Use "delete".');
    }
    return fetchConfigData(configType, method, queryParams);
}