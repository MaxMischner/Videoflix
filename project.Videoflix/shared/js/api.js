
/**
 * Returns a user-friendly error message based on the caught error.
 * @param {Error} error - The caught error object.
 * @returns {string} Human-readable error message.
 */
function getErrorMessage(error) {
    let errorMessage = 'Network error';
    if (error instanceof TypeError) {
        errorMessage = 'There was an issue with the request or network connection.';
    } else if (error instanceof SyntaxError) {
        errorMessage = 'Response was not valid JSON.';
    } else if (error.message.includes('Failed to fetch')) {
        errorMessage = 'Failed to connect to the server.';
    }
    return errorMessage;
}

/**
 * Extracts form data and returns it as a plain object.
 * @param {HTMLFormElement} form - The form element to extract data from.
 * @returns {Object} Object containing form field values.
 */
function getFormData(form) {
    const formData = new FormData(form);
    return Object.fromEntries(formData.entries());
}

/**
 * Sends a POST request to the API with JSON data and CSRF token (if available).
 * @param {string} endpoint - API endpoint to call (relative to API_BASE_URL).
 * @param {Object} data - Data to send in the request body.
 * @returns {Promise<{ok: boolean, status: number|string, data: any, message: string}>}
 */
async function postData(endpoint, data) {
    let csrfToken = '';
    const cookieString = document.cookie;

    if (cookieString && cookieString.includes('csrftoken=')) {
        const csrfCookie = cookieString.split('csrftoken=')[1];
        if (csrfCookie) {
            csrfToken = csrfCookie.split(';')[0];
        }
    }
    const headers = {
        'Content-Type': 'application/json',
    };

    if (csrfToken) {
        headers['X-CSRFToken'] = csrfToken;
    }

    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            method: 'POST',
            headers: headers,
            credentials: 'include',
            body: JSON.stringify(data)
        });
        const responseData = await response.json();
        return {
            ok: response.ok,
            status: response.status,
            data: responseData
        };
    } catch (error) {
        const errorMessage = getErrorMessage(error);
        return {
            ok: false,
            status: 'error',
            message: errorMessage
        };
    }
}

/**
 * Sends a GET request to the API, optionally with activation parameters.
 * @param {string} [uid] - User ID for account activation.
 * @param {string} [token] - Token for account activation.
 * @returns {Promise<Response>} Fetch response object.
 */
async function getData(uid, token) {
    const endpoint = (uid && token) ? `activate/${uid}/${token}/` : `video/`
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'include',
    });
    return response;
}

/**
 * Redirects the user to the registration page after validating the email.
 * Stores the entered email in localStorage.
 * @param {Event} event - The click event from the "Register" button/link.
 */
function goToRegister(event) {
    event.preventDefault();
    let email = document.getElementById("email").value;
    if (validateEmail(document.getElementById("email"))) {
        localStorage.setItem('email', email);
        window.location.href = "./pages/auth/register.html";
    } else {
        showToastMessage(true, ["Please enter a valid email address"]);
    }
}


