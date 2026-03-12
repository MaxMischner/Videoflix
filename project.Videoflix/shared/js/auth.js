/**
 * Handles the sign-up form submission.
 * Validates form and privacy policy checkbox before sending registration data.
 *
 * @param {Event} event - The form submission event.
 */
async function signUpSubmit(event) {
    event.preventDefault();

    const privacyCheckbox = document.getElementById('privacy_policy');
    if (privacyCheckbox && !privacyCheckbox.checked) {
        setError(true, "privacy_policy_group");
        showToastMessage(true, ["Please accept the privacy policy to continue"]);
        return;
    }

    if (!validateSignUp()) {
        showToastMessage(true, ["Please correct the errors in the form"]);
        return;
    }
    const data = getFormData(event.target);
    let response = await postData(REGISTER_URL, data);
    if (!response.ok) {
        let errorArr = extractErrorMessages(response.data);
        showToastMessage(true, errorArr);
    } else {
        localStorage.removeItem('email');
        showToastAndRedirect(false, ["Registration successful! Please check your email."], "../auth/login.html", TOAST_DURATION);
    }
}

/**
 * Handles the login form submission.
 * Submits login data and handles success or error responses.
 *
 * @param {Event} event - The form submission event.
 */
async function logInSubmit(event) {
    event.preventDefault();
    setError(false, "error_login");
    const data = getFormData(event.target);
    await logIn(data);
}

/**
 * Handles the "forgot password" form submission.
 * Sends reset email request.
 *
 * @param {Event} event - The form submission event.
 */
async function forgotEmailSubmit(event) {
    event.preventDefault();
    setError(false, "forgot_email_group");
    const data = getFormData(event.target);
    await forgetEmail(data);
}

/**
 * Sends a password reset request with the given data.
 *
 * @param {Object} data - The email or credentials for password reset.
 */
async function forgetEmail(data) {
    let response = await postData(FORGET_PASSWORD_URL, data);
    if (!response.ok) {
        setError(true, "forgot_email_group");
        let errorArr = extractErrorMessages(response.data);
        showToastMessage(true, errorArr);
    } else {
        showToastAndRedirect(false, ["Password reset email sent! Please check your inbox."], "../auth/login.html", TOAST_DURATION);
    }
}

/**
 * Logs in the user using the provided credentials.
 *
 * @param {Object} data - User login credentials.
 */
async function logIn(data) {
    let response = await postData(LOGIN_URL, data);
    if (!response.ok) {
        setError(true, "error_login");
        let errorArr = extractErrorMessages(response.data);
        showToastMessage(true, errorArr);
    } else {
        showToastAndRedirect(false, ["Login successful!"], "../video_list/index.html", TOAST_DURATION);
    }
}

/**
 * Validates the registration email field.
 * If valid, stores it in the sign-up values.
 *
 * @param {HTMLInputElement} element - The input element to validate.
 */
function validateRegistrationEmail(element) {
    let valid = validateEmail(element);
    if (valid) {
        signUpValues.email = element.value.trim();
    }
}

/**
 * Validates the password field for minimum length and updates UI.
 * Also triggers confirmation password re-validation.
 *
 * @param {HTMLInputElement} element - The password input field.
 */
function validatePW(element) {
    let valid = element.value.trim().length > 7;
    setError(!valid, element.id + "_group");
    if (valid) {
        signUpValues.password = element.value.trim();
    }
    let confirmedPwRef = document.getElementById("confirmed_password");
    if (confirmedPwRef.value.trim().length > 0) {
        validateConfirmPW(confirmedPwRef);
    }
}

/**
 * Validates that confirmation password matches original password.
 * Updates the error state in the UI.
 *
 * @param {HTMLInputElement} element - The confirmation password input.
 */
function validateConfirmPW(element) {
    let valid = document.getElementById("password").value.trim() == element.value.trim();
    setError(!valid, element.id + "_group");
    if (valid) {
        signUpValues.confirmed_password = element.value.trim();
    }
}

/**
 * Validates that the login password field is not empty.
 *
 * @param {HTMLInputElement} element - The login password input.
 */
function validateLoginPW(element) {
    let valid = element.value.trim().length > 0;
    setError(!valid, element.id + "_group");
}

/**
 * Validates if the email input is in a valid format.
 *
 * @param {HTMLInputElement} element - The email input field.
 * @returns {boolean} True if the email is valid, false otherwise.
 */
function validateEmail(element) {
    const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    let valid = emailRegex.test(element.value.trim());
    setError(!valid, element.id + "_group");
    return valid;
}

/**
 * Validates the full sign-up form, including passwords, email, and checkbox.
 *
 * @returns {boolean} True if the form is valid, false otherwise.
 */
function validateSignUp() {
    validateEmail(document.getElementById("email"));
    validatePW(document.getElementById("password"));
    validateConfirmPW(document.getElementById("confirmed_password"));

    const privacyCheckbox = document.getElementById('privacy_policy');
    if (privacyCheckbox && !privacyCheckbox.checked) {
        setError(true, "privacy_policy_group");
    } else if (privacyCheckbox) {
        setError(false, "privacy_policy_group");
    }

    const form = document.getElementById('sign_up_form');
    const elementWithErrorFalse = form.querySelector('[error="true"]');
    return elementWithErrorFalse == null;
}

/**
 * Initializes the password reset process by extracting reset parameters.
 * Redirects if parameters are invalid.
 */
function initPasswordReset() {
    const params = extractParams();
    if (!params) {
        showToastAndRedirect(true, ["Invalid reset link"], "./login.html", TOAST_DURATION);
        return;
    }
    window.resetParams = params;
}

/**
 * Handles submission of the confirm password form.
 * Validates and sends new password to the server.
 *
 * @param {Event} event - The form submission event.
 */
async function confirmPasswordSubmit(event) {
    event.preventDefault();
    const form = event.target;
    const formData = getFormData(form);
    const apiEndpoint = `password_confirm/${window.resetParams.uid}/${window.resetParams.token}/`;
    const data = {
        new_password: formData.password,
        confirm_password: formData.repeated_password,
    };
    const result = await postData(apiEndpoint, data);
    if (result.ok) {
        showToastAndRedirect(false, ["Password successfully reset!"], "./login.html", TOAST_DURATION);
        window.resetParams = null;
        form.reset();
    } else {
        const errorMessages = extractErrorMessages(result.data);
        showToastMessage(true, errorMessages);
    }
}

/**
 * Initializes the account activation view and triggers activation request.
 */
async function initActivation() {
    setHeader()
    await activateAccount();
}

/**
 * Sends the activation request using URL parameters (uid, token).
 */
async function activateAccount() {
    const params = extractActivationParams();
    if (!params) return;
    updateActivationContent('processing');
    try {
        const result = await processActivation(params);
        handleActivationSuccess(result);
    } catch (error) {
        handleActivationError(error);
    }
}

/**
 * Extracts activation parameters (uid and token) from URL.
 * Calls error handler if missing.
 *
 * @returns {{uid: string, token: string} | null}
 */
function extractActivationParams() {
    const {uid, token} = extractParams() || {};
    if (!uid || !token) {
        handleActivationError('Invalid activation link');
        return null;
    }
    return {uid, token};
}

/**
 * Sends a GET request to activate the account.
 *
 * @param {{uid: string, token: string}} params - Activation parameters.
 * @returns {Promise<Object>} The parsed server response.
 */
async function processActivation({uid, token}) {
    const response = await getData(uid, token);
    const result = await response.json();

    if (!response.ok) {
        throw new Error(result.message || "Activation failed");
    }
    return result;
}

/**
 * Handles a successful account activation.
 *
 * @param {Object} result - The success response from the server.
 */
function handleActivationSuccess(result) {
    const message = result.message || "Account successfully activated!";
    updateActivationContent('success', message);
    showToastAndRedirect(false, [message], ACTIVATION_CONFIG.loginUrl, ACTIVATION_CONFIG.successDelay);
}

/**
 * Handles an activation error, including display and redirect.
 *
 * @param {string | Error} error - The error object or message.
 */
function handleActivationError(error) {
    const message = typeof error === 'string' ? error : 'Network error occurred';
    updateActivationContent('error', message);
    showToastAndRedirect(true, [message], ACTIVATION_CONFIG.loginUrl, ACTIVATION_CONFIG.errorDelay);
}

/**
 * Updates the DOM with content corresponding to the activation status.
 *
 * @param {"processing" | "success" | "error"} status - Activation status.
 * @param {string} [customMessage] - Optional custom message to display.
 */
function updateActivationContent(status, customMessage = '') {
    const activationContent = document.getElementById('activation_content');
    if (!activationContent) return;

    const content = getActivationContent(status, customMessage);
    activationContent.innerHTML = buildActivationHTML(content, status);
}

/**
 * Returns the content object (icon, title, text) based on activation status.
 *
 * @param {"processing" | "success" | "error"} status - Activation status.
 * @param {string} customMessage - Optional override for text message.
 * @returns {{icon: string, title: string, text: string}}
 */
function getActivationContent(status, customMessage) {
    const baseContent = ACTIVATION_MESSAGES[status];
    return {
        ...baseContent,
        text: customMessage || baseContent.text
    };
}

/**
 * Builds the HTML string for the activation content section.
 *
 * @param {{icon: string, title: string, text: string}} content - Activation content data.
 * @param {"processing" | "success" | "error"} status - Activation status.
 * @returns {string} HTML string to inject.
 */
function buildActivationHTML({icon, title, text}, status) {
    const redirectMessage = status !== 'processing'
        ? '<p class="text_a_c font_prime_color">Redirecting to login...</p>'
        : '';

    const titleClass = status === 'success' ? 'activation-success-text' :
        status === 'error' ? 'activation-error-text' : 'font_prime_color';

    return `
        <h1 class="${titleClass} d_flex_cs_gl w_full">${icon} ${title}</h1>
        <p class="text_a_c font_prime_color">${text}</p>
        ${redirectMessage}
    `;
}

/**
 * Initializes the registration form by pre-filling the email if stored in localStorage.
 */
function initRegister() {
    const email = localStorage.getItem('email');
    if (email && email.length > 0) {
        document.getElementById('email').value = email;
    }

}
