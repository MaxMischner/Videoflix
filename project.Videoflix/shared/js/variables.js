/**
 * Stores user input values during the sign-up process.
 *
 * @type {{email: string, password: string, confirmed_password: string}}
 */
let signUpValues = {
    "email": "",
    "password": "",
    "confirmed_password": "",
}

/**
 * Holds a list of video metadata or objects (fetched or cached).
 * Content structure is assumed to be dynamic or fetched later.
 *
 * @type {any}
 */
let VIDEOS

/**
 * Stores the latest videos fetched or displayed.
 *
 * @type {any[]}
 */
let LATESTVIDEOS = []

/**
 * Timestamp or indicator of the last data refresh.
 *
 * @type {any}
 */
let LASTREFRESH

/**
 * Stores the interval ID returned by setInterval,
 * used to clear the interval later with clearInterval().
 *
 * @type {number | undefined}
 */
let STARTINTERVALL

/**
 * Instance of the HLS.js player used for video streaming.
 *
 * @type {Hls | undefined}
 */
let hls

/**
 * Reference to the HTML container element for the video player.
 *
 * @type {HTMLElement | null}
 */
let videoContainer

/**
 * Reference to the HTML overlay container for the video (e.g., modals or previews).
 *
 * @type {HTMLElement | null}
 */
let overlayVideoContainer

/**
 * Stores the currently selected or playing video object.
 *
 * @type {any}
 */
let currentVideo

/**
 * Current video resolution selected by the user (default is '480p').
 *
 * @type {string}
 */
let currentResolution = '480p'

/**
 * Predefined messages for different activation states (e.g., loading, success, error).
 *
 * @type {{
 *   processing: {icon: string, title: string, text: string},
 *   success: {icon: string, title: string, text: string},
 *   error: {icon: string, title: string, text: string}
 * }}
 */
const ACTIVATION_MESSAGES = {
    processing: {
        icon: '',
        title: 'Processing...',
        text: 'Please wait while we process your request.'
    },
    success: {
        icon: '<img src="/assets/icons/check_circle.svg" alt="Success" width="28" height="28">',
        title: 'Success!',
        text: 'Operation completed successfully!'
    },
    error: {
        icon: '<img src="/assets/icons/error.svg" alt="Error" width="28" height="28">',
        title: 'Error',
        text: 'Something went wrong.'
    }
}
