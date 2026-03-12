/**
 * Logs out the user by sending a POST request to the backend logout endpoint.
 * Displays a toast message and redirects the user upon success or error.
 * Also clears the defined interval timer.
 *
 * @async
 * @function logOut
 * @returns {Promise<void>}
 */
async function logOut() {
    try {
        const csrfToken = document.cookie.split('csrftoken=')[1].split(';')[0];
        await fetch(`${API_BASE_URL}logout/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            credentials: 'include',
        });
        showToastAndRedirect(false, ["Successfully logged out!"], "../auth/login.html", TOAST_DURATION);

    } catch (error) {
        showToastAndRedirect(true, ["Logout error, redirecting..."], "../auth/login.html", TOAST_DURATION);
    }
    clearInterval(STARTINTERVALL);
}

/**
 * Initializes the header by injecting the appropriate template.
 *
 * @async
 * @function setHeader
 * @returns {Promise<void>}
 */
async function setHeader() {
    setHeaderTemplate()
}

/**
 * Injects HTML into the header element based on the current URL.
 *
 * @function setHeaderTemplate
 */
function setHeaderTemplate() {
    let headerRef = document.getElementById('head_content_right')
    if (!headerRef) {
        return
    }
    headerRef.innerHTML = getHeaderTemplate()
}

/**
 * Returns a dynamic HTML string for the header,
 * depending on the current page URL.
 *
 * @function getHeaderTemplate
 * @returns {string} - The HTML string to be rendered in the header
 */
function getHeaderTemplate() {
    const currentUrl = window.location.href;

    if (currentUrl.endsWith('login.html')) {
        return `
            <div class="d_flex_cc_gm">
                <a aria-label="register page" href="./register.html" class="std_btn btn_prime pad_s d_flex_cc_gs">
                    Sign up
                </a>
            </div>`
    } else if (currentUrl.endsWith('register.html') || currentUrl.endsWith('forgot_password.html')) {
        return `
            <div class="d_flex_cc_gm">
                <a aria-label="login page" href="./login.html" class="std_btn btn_prime pad_s d_flex_cc_gs">
                    Log in
                </a>
            </div>`
    } else if (currentUrl.includes('confirm_password.html')) {
        return `
            <div class="d_flex_cc_gm">
                <a aria-label="login page" href="./login.html" class="std_btn btn_prime pad_s d_flex_cc_gs">
                    Log in
                </a>
            </div>`
    } else if (currentUrl.endsWith('/video_list/index.html')) {
        return `
            <div class="d_flex_cc_gm">
                <a aria-label="logout" onclick="logOut()" class="std_btn btn_prime pad_s d_flex_cc_gs"> 
                    Logout 
                </a>
            </div>
        `
    }
}

/**
 * Navigates the user back to the previous page if available.
 * If not, redirects to the login page.
 *
 * @function goBackURL
 */
function goBackURL() {
    if (document.referrer && document.referrer !== window.location.href) {
        window.history.back();
    }
    else {
        window.location.href = "./pages/auth/login.html";
    }
}
