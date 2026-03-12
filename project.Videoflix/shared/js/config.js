/**
 * The base URL for all API requests.
 * Typically points to your backend server's API root.
 * @constant {string}
 */
const API_BASE_URL = 'http://127.0.0.1:8000/api/';

/**
 * Relative path for the login endpoint.
 * Used to authenticate users.
 * @constant {string}
 */
const LOGIN_URL = 'login/';

/**
 * Relative path for the registration endpoint.
 * Used to create new user accounts.
 * @constant {string}
 */
const REGISTER_URL = 'register/';

/**
 * Relative path for the "forgot password" endpoint.
 * Sends a password reset email to the user.
 * @constant {string}
 */
const FORGET_PASSWORD_URL = 'password_reset/';

/**
 * Relative path for refreshing JWT tokens.
 * @constant {string}
 */
const REFRESH_URL = 'token/refresh/'

/**
 * Configuration for the activation flow.
 * Contains redirect delays and the login URL after activation.
 * @constant {Object}
 * @property {number} successDelay - Delay before redirecting after successful activation (in ms).
 * @property {number} errorDelay - Delay before redirecting after failed activation (in ms).
 * @property {string} loginUrl - Path to the login page.
 */
const ACTIVATION_CONFIG = {
    successDelay: 2500,
    errorDelay: 3000,
    loginUrl: "./login.html"
};

/**
 * Default duration for toast messages (in milliseconds).
 * @constant {number}
 */
const TOAST_DURATION = 2000;

/**
 * Generates the URL path to the HLS master playlist (index.m3u8) for a given video.
 *
 * @param {number|string} id - The unique identifier of the video/movie.
 *                             Used to locate the correct video folder on the server.
 * @param {string} resolution - The desired video resolution (e.g., '480p', '720p', '1080p').
 *                              Used to select the corresponding quality folder.
 * @returns {string} The URL path to the HLS playlist file for the specified video and resolution.
 *
 * @example
 * const url = URL_TO_INDEX_M3U8(5, '720p');
 * // url is 'video/5/720p/index.m3u8'
 */
const URL_TO_INDEX_M3U8 = (id, resolution) => `video/${id}/${resolution}/index.m3u8`
