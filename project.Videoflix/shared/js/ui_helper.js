/**
 * Sets an "error" attribute on a given HTML element.
 *
 * @function setError
 * @param {boolean} valid - Indicates if the input is valid (true or false).
 * @param {string} id - The ID of the HTML element to modify.
 */
function setError(valid, id) {
    document.getElementById(id).setAttribute("error", valid)
}

/**
 * Toggles the visibility of a password input field and updates the icon accordingly.
 *
 * @function togglePassword
 * @param {HTMLImageElement} icon - The eye icon element that was clicked.
 */
function togglePassword(icon) {
    const container = icon.closest(".form_group_w_icon_wo_label");
    const input = container.querySelector("input[type='password'], input[type='text']");

    if (input) {
        if (input.type === "password") {
            input.type = "text";
            icon.src = "../../assets/icons/visibility_off.svg";
        } else {
            input.type = "password";
            icon.src = "../../assets/icons/visibility.svg";
        }
    }
}

/**
 * Recursively extracts all error messages from a nested error object.
 *
 * @function extractErrorMessages
 * @param {Object} errorObject - The error object returned from a server or validation.
 * @returns {string[]} - A flat array of error messages.
 */
function extractErrorMessages(errorObject) {
    let errorMessages = [];

    for (let key in errorObject) {
        if (errorObject.hasOwnProperty(key)) {
            const value = errorObject[key];
            if (typeof value === 'object' && value !== null) {
                errorMessages = errorMessages.concat(extractErrorMessages(value));
            } else if (Array.isArray(value)) {
                errorMessages = errorMessages.concat(value);
            } else {
                errorMessages.push(value);
            }
        }
    }
    return errorMessages;
}

/**
 * Displays a temporary toast message on the screen.
 *
 * @function showToastMessage
 * @param {boolean} [error=true] - Indicates whether the toast is for an error (true) or success (false).
 * @param {string[]} [msg=[]] - Array of messages to display in the toast.
 */
function showToastMessage(error = true, msg = []) {
    const toast = document.createElement('div');
    toast.className = 'toast_msg d_flex_cc_gm';
    toast.innerHTML = getToastHTML(msg, error);
    toast.setAttribute('error', error);
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 3000);
}

/**
 * Builds the HTML content for a toast message.
 *
 * @function getToastHTML
 * @param {string[]} msg - Array of messages to display.
 * @param {boolean} error - Indicates whether the toast is for an error or success.
 * @returns {string} - The HTML string for the toast content.
 */
function getToastHTML(msg, error) {
    let msglist = "";
    if (msg.length <= 0) {
        msglist = error ? "<li>An error has occurred</li>" : "<li>That worked!</li>"
    }
    for (let i = 0; i < msg.length; i++) {
        msglist += `<li>${msg[i]}</li>`
    }

    const icon = error
        ? '<img src="/assets/icons/error.svg" alt="Error" width="24" height="24">'
        : '<img src="/assets/icons/check_circle.svg" alt="Success" width="24" height="24">';

    return `<div class="toast_msg_left d_flex_cc_gm">
                ${icon}
            </div>
            <div class="toast_msg_right">
                <h3 error="false">Success</h3>
                <h3 error="true">Error</h3>
                <ul class="w_full">
                    ${msglist}
                </ul>
            </div>`
}

/**
 * Extracts `uid` and `token` parameters from the current page URL.
 *
 * @function extractParams
 * @returns {{uid: string, token: string} | null} - The extracted parameters or null if missing.
 */
function extractParams() {
    const urlParams = new URLSearchParams(window.location.search);
    const uid = urlParams.get('uid');
    const token = urlParams.get('token');

    if (uid && token) {
        return {uid, token};
    }
    return null;
}

/**
 * Shows a toast message and optionally redirects to a different URL after a delay.
 *
 * @function showToastAndRedirect
 * @param {boolean} [error=true] - Indicates if the message is an error.
 * @param {string[]} [msg=[]] - Messages to display in the toast.
 * @param {string|null} [redirectUrl=null] - The URL to redirect to after the toast.
 * @param {number} [delay=TOAST_DURATION] - Delay in milliseconds before redirecting.
 */
function showToastAndRedirect(error = true, msg = [], redirectUrl = null, delay = TOAST_DURATION) {
    showToastMessage(error, msg);

    if (redirectUrl) {
        setTimeout(() => {
            window.location.href = redirectUrl;
        }, delay);
    }
}

