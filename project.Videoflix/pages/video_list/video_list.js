let overlayHls = null;
let NEWEST = document.getElementById('newest')

/**
 * Scrolls a video list container horizontally.
 * @param {HTMLElement} button - The button that triggered the scroll.
 * @param {number} amount - The number of pixels to scroll.
 */
function scrollHorizontally(button, amount) {
    const wrapper = button.closest('.scroll-wrapper');
    const container = wrapper.querySelector('ul');

    container.scrollBy({
        left: amount, behavior: 'smooth'
    });
}

/**
 * Initializes the video list and UI elements on page load.
 */
async function initVideoList() {
    initDOMElements();
    initEventListeners();
    setHeader();
    startRefreshIntervall();
    await loadAndSetupVideos();
    initScrollIndicators();
}

/**
 * Initializes key DOM elements used for video playback.
 */
function initDOMElements() {
    videoContainer = document.getElementById('videoPlayer');
    overlayVideoContainer = document.getElementById('overlayVideo');
    LASTREFRESH = new Date().getTime();
}

/**
 * Sets up event listeners such as resolution change.
 */
function initEventListeners() {
    document.getElementById('setResolution').addEventListener('change', handleResolutionChange);
}

/**
 * Handles video resolution changes from the dropdown.
 * @param {Event} event - The change event.
 */
function handleResolutionChange(event) {
    currentResolution = event.target.value;
    if (currentVideo && document.getElementById('overlay').style.display === 'flex') {
        loadVideoInOverlay(currentVideo, currentResolution);
    }
}

/**
 * Loads videos from the backend and sets up the UI.
 */
async function loadAndSetupVideos() {
    let response
    try {
        response = await getData();
        VIDEOS = await response.json();
        await getNewestVideos();
        setStartVideo();
        await renderVideosDynamically();
        setupInitialVideo();
    } catch (error) {
        document.getElementById('videoTitle').style.color = 'red';
        document.getElementById('category-new').style.display = 'none';
        document.getElementById('playButton').style.display = 'none';
        showToastMessage(true, ['Failed to load videos']);
    }
}

/**
 * Sets the initial video on page load.
 */
function setupInitialVideo() {
    if (VIDEOS && VIDEOS.length > 0) {
        currentVideo = VIDEOS[0].id;
        loadVideo(VIDEOS[0].id, '480p');
    }
}

/**
 * Filters the most recent videos (within the last 5 days).
 */
async function getNewestVideos() {
    let currentDate = new Date();
    let timeSpan = new Date(currentDate.getTime() - (5 * 24 * 60 * 60 * 1000));
    VIDEOS.forEach(video => {
        const videoDate = new Date(video.created_at)
        if (videoDate >= timeSpan) {
            LATESTVIDEOS.push(video)
        }
    })
}

/**
 * Sets the title and description for the first video.
 */
function setStartVideo() {
    document.getElementById('videoTitle').innerHTML = VIDEOS[0].title;
    document.getElementById('videoDescription').innerHTML = VIDEOS[0].description;
}

/**
 * Dynamically renders all video sections: first the "Newest" section, then all other categories.
 * It collects unique categories from the VIDEOS array, removes existing dynamic sections,
 * and creates new sections grouped by category.
 *
 * @async
 * @function
 */
async function renderVideosDynamically() {
    const container = document.querySelector('.list_section');

    renderNewestSection();

    const categories = new Set(VIDEOS.map(v => v.category.toLowerCase()));
    clearDynamicSections(container);

    categories.forEach(cat => {
        if (cat === 'newest') return;
        const videosInCategory = VIDEOS.filter(v => v.category.toLowerCase() === cat);
        const section = renderCategorySection(cat, videosInCategory);
        container.appendChild(section);
    });
}

/**
 * Renders the "Newest" video section.
 * Clears the existing content and appends each video from LATESTVIDEOS
 * using the `videoTemplate` function.
 *
 * @function
 */
function renderNewestSection() {
    NEWEST.innerHTML = '';
    LATESTVIDEOS.forEach(video => {
        NEWEST.append(videoTemplate(video, video.thumbnail_url));
    });
}

/**
 * Removes all dynamically generated category sections from the given container.
 *
 * @param {HTMLElement} container - The parent element containing video sections.
 *
 * @function
 */
function clearDynamicSections(container) {
    [...container.querySelectorAll('.video_list.dynamic-category')].forEach(el => el.remove());
}

/**
 * Creates a section element for a specific video category, including a heading and video list.
 *
 * @param {string} cat - The category name (in lowercase).
 * @param {Object[]} videos - An array of video objects belonging to this category.
 * @returns {HTMLElement} - The constructed <section> DOM element.
 *
 * @function
 */
function renderCategorySection(cat, videos) {
    const section = document.createElement('section');
    section.classList.add('video_list', 'dynamic-category');

    const h2 = document.createElement('h2');
    h2.textContent = cat.charAt(0).toUpperCase() + cat.slice(1);
    section.appendChild(h2);

    const scrollWrapper = document.createElement('div');
    scrollWrapper.classList.add('scroll-wrapper');

    const ul = document.createElement('ul');
    ul.id = cat;

    videos.forEach(video => {
        ul.appendChild(videoTemplate(video));
    });

    scrollWrapper.appendChild(ul);
    section.appendChild(scrollWrapper);

    return section;
}

/**
 * Creates a video thumbnail element.
 * @param {Object} video - The video object.
 * @returns {HTMLElement} The list item containing the video thumbnail.
 */
function videoTemplate(video) {
    let listItem = document.createElement('li');
    let img = document.createElement('img');
    img.setAttribute("src", video.thumbnail_url)
    img.setAttribute("alt", video.title)
    img.setAttribute("onclick", `showVideo(${video.id})`)
    listItem.append(img);
    return listItem;
}

/**
 * Displays video details and loads the selected video.
 * @param {number} id - The video ID.
 */
function showVideo(id) {
    let video = VIDEOS.find(video => video.id == id);
    document.getElementById('videoTitle').innerHTML = video.title;
    document.getElementById('videoDescription').innerHTML = video.description;
    document.getElementById('playButton').setAttribute("onclick", `playVideo(${id})`)
    currentVideo = id
    loadVideo(id, '480p');
}

/**
 * Starts an interval that refreshes the JWT token every 20 minutes.
 */
function startRefreshIntervall() {
    STARTINTERVALL = setInterval(async () => {
        await doRefresh();
    }, 20 * 60 * 1000);
}

/**
 * Calls the backend to refresh the JWT token.
 */
async function doRefresh() {
    await fetch(`${API_BASE_URL}${REFRESH_URL}`, {
        method: 'POST', headers: {
            'Content-Type': 'application/json',
        }, credentials: 'include',
    })
}

/**
 * Loads and plays a video using HLS.js.
 * @param {number} id - The video ID.
 * @param {string} resolution - The desired video resolution (e.g., '480p').
 */
function loadVideo(id, resolution) {
    if (hls) {
        hls.destroy();
    }
    hls = new Hls({
        xhrSetup: function (xhr) {
            xhr.withCredentials = true
        },
        // BUFFER-MANAGEMENT
        maxBufferLength: 45,
        maxMaxBufferLength: 900,
        maxBufferSize: 90 * 1000 * 1000,
        maxBufferHole: 0.5,
        backBufferLength: 90,

        // STALL-DETECTION
        lowBufferWatchdogPeriod: 0.5,
        highBufferWatchdogPeriod: 2,
        nudgeOffset: 0.1,
        nudgeMaxRetry: 3,
        maxFragLookUpTolerance: 0.25,

        // PERFORMANCE
        enableWorker: true,
        startFragPrefetch: true,
        testBandwidth: true,
        enableSoftwareAES: true,

        // SEEK
        maxSeekHole: 2,
        seekHoleNudgeDuration: 0.01,

        // NETWORK-CONFIGURATION
        manifestLoadingTimeOut: 10000,
        manifestLoadingMaxRetry: 4,
        levelLoadingTimeOut: 10000,
        levelLoadingMaxRetry: 4,
        fragLoadingTimeOut: 20000,
        fragLoadingMaxRetry: 6,

        // APPEND-CONFIGURATION
        appendErrorMaxRetry: 3,
        loaderMaxRetry: 2,
        loaderMaxRetryTimeout: 64000,

        // ADVANCED SETTINGS
        lowLatencyMode: false,
        enableCEA708Captions: false,
        stretchShortVideoTrack: false,
        forceKeyFrameOnDiscontinuity: true,

        // LIVE-STREAM-CONFIGURATION
        liveSyncDurationCount: 3,
        liveMaxLatencyDurationCount: 10,
        liveDurationInfinity: false,

        // FRAGMENT-DRIFT-TOLERANCE
        maxAudioFramesDrift: 1,
        maxVideoFramesDrift: 1,

        // DEBUG
        debug: false,

        // METADATA-CONFIGURATION
        enableDateRangeMetadataCues: false,
        enableEmsgMetadataCues: false,
        enableID3MetadataCues: false
    });
    hls.loadSource(`${API_BASE_URL}${URL_TO_INDEX_M3U8(id, resolution)}`);
    hls.attachMedia(videoContainer);

    hls.on(Hls.Events.MANIFEST_PARSED, () => {
        setTimeout(() => {
            videoContainer.play().catch(() => {
                console.log("User interaction required to start playback");
            });
        }, 2000)
    });

    hls.on(Hls.Events.ERROR, (event, data) => {
        if (data.fatal) {
            console.error("HLS fatal error:", data);
        }
    });
}

/**
 * Proofs if a container is scrollable and add then the CSS class
 * @param {HTMLElement} container - container that should be proofed
 */
function updateScrollIndicator(container) {
    const scrollWrapper = container.closest('.scroll-wrapper');
    if (!scrollWrapper) return;

    const isScrollable = container.scrollWidth > container.clientWidth;

    if (isScrollable) {
        scrollWrapper.classList.add('scrollable');
    } else {
        scrollWrapper.classList.remove('scrollable');
    }
}

/**
 * Initialised scroll indicators for all video lists
 */
function initScrollIndicators() {
    const videoLists = document.querySelectorAll('.video_list ul');

    videoLists.forEach(list => {
        updateScrollIndicator(list);

        if (window.ResizeObserver) {
            const resizeObserver = new ResizeObserver(() => {
                updateScrollIndicator(list);
            });
            resizeObserver.observe(list);
            resizeObserver.observe(list.parentElement);
        }

        window.addEventListener('resize', () => {
            setTimeout(() => updateScrollIndicator(list), 100);
        });
    });
}

/**
 * Refreshes all scroll indicators
 */
function updateAllScrollIndicators() {
    const videoLists = document.querySelectorAll('.video_list ul');
    videoLists.forEach(list => {
        updateScrollIndicator(list);
    });
}

/**
 * Loads a video in the overlay using HLS.js.
 * @param {number} id - The video ID.
 * @param {string} resolution - The desired resolution.
 */
function loadVideoInOverlay(id, resolution) {
    if (overlayHls) {
        overlayHls.destroy();
    }

    overlayHls = new Hls({
        xhrSetup: function (xhr) {
            xhr.withCredentials = true
        },
        // BUFFER-MANAGEMENT
        maxBufferLength: 45,
        maxMaxBufferLength: 900,
        maxBufferSize: 90 * 1000 * 1000,
        maxBufferHole: 0.5,
        backBufferLength: 90,

        // STALL-DETECTION
        lowBufferWatchdogPeriod: 0.5,
        highBufferWatchdogPeriod: 2,
        nudgeOffset: 0.1,
        nudgeMaxRetry: 3,
        maxFragLookUpTolerance: 0.25,

        // PERFORMANCE
        enableWorker: true,
        startFragPrefetch: true,
        testBandwidth: true,
        enableSoftwareAES: true,

        // SEEK
        maxSeekHole: 2,
        seekHoleNudgeDuration: 0.01,

        // NETWORK-CONFIGURATION
        manifestLoadingTimeOut: 10000,
        manifestLoadingMaxRetry: 4,
        levelLoadingTimeOut: 10000,
        levelLoadingMaxRetry: 4,
        fragLoadingTimeOut: 20000,
        fragLoadingMaxRetry: 6,

        // APPEND-CONFIGURATION
        appendErrorMaxRetry: 3,
        loaderMaxRetry: 2,
        loaderMaxRetryTimeout: 64000,

        // ADVANCED SETTINGS
        lowLatencyMode: false,
        enableCEA708Captions: false,
        stretchShortVideoTrack: false,
        forceKeyFrameOnDiscontinuity: true,

        // LIVE-STREAM-CONFIGURATION
        liveSyncDurationCount: 3,
        liveMaxLatencyDurationCount: 10,
        liveDurationInfinity: false,

        // FRAGMENT-DRIFT-TOLERANCE
        maxAudioFramesDrift: 1,
        maxVideoFramesDrift: 1,

        // DEBUG
        debug: false,

        // METADATA-CONFIGURATION
        enableDateRangeMetadataCues: false,
        enableEmsgMetadataCues: false,
        enableID3MetadataCues: false
    });

    overlayHls.loadSource(`${API_BASE_URL}${URL_TO_INDEX_M3U8(id, resolution)}`);
    overlayHls.attachMedia(overlayVideoContainer);

    overlayHls.on(Hls.Events.MANIFEST_PARSED, () => {
        setTimeout(() => {
            overlayVideoContainer.play().catch(() => {
            console.log("User interaction required to start overlay playback");
        });
        }, 2000)
    });

    overlayHls.on(Hls.Events.ERROR, (event, data) => {
        if (data.fatal) {
            console.error("HLS fatal error:", data);
        }
    });
}

/**
 * Opens the overlay player and starts playback.
 * @param {number} videoId - The video ID.
 * @param {string} resolution - The resolution to play.
 */
function openVideoOverlay(videoId, resolution) {
    const video = VIDEOS.find(video => video.id == videoId);
    if (!video) return;

    hideHeader();
    const overlay = document.getElementById('overlay');
    overlay.style.display = 'flex';
    document.body.classList.add('overlay-open');
    document.getElementById('overlayTitle').innerHTML = video.title;
    document.getElementById('setResolution').value = resolution;
    currentResolution = resolution;
    loadVideoInOverlay(videoId, resolution);
    document.body.style.overflow = 'hidden';

}

/**
 * Closes the overlay video player and resets the UI.
 */
function closeVideoOverlay() {
    const overlay = document.getElementById('overlay');
    overlay.style.display = 'none';

    document.body.classList.remove('overlay-open');

    showHeader();

    if (overlayHls) {
        overlayHls.destroy();
        overlayHls = null;
    }

    overlayVideoContainer.pause();
    overlayVideoContainer.src = '';

    document.body.style.overflow = 'auto';
}

/**
 * Opens the video overlay for the given video.
 * @param {number} id - The video ID.
 */
function playVideo(id) {
    if (!id) {
        id = currentVideo;
    }
    openVideoOverlay(id, currentResolution);
}

/**
 * Hides the main header (e.g., when playing video fullscreen).
 */
function hideHeader() {
    const header = document.querySelector('.main_header');
    if (header) {
        header.style.transform = 'translateY(-100%)';
        header.style.opacity = '0';
        header.style.transition = 'transform 0.3s ease-in-out, opacity 0.3s ease-in-out';
    }
}

/**
 * Shows the main header again.
 */
function showHeader() {
    const header = document.querySelector('.main_header');
    if (header) {
        header.style.transform = 'translateY(0)';
        header.style.opacity = '1';
        header.style.transition = 'transform 0.3s ease-in-out, opacity 0.3s ease-in-out';
    }
}

/**
 * Closes the overlay when the Escape key is pressed.
 */
document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
        closeVideoOverlay();
    }
});
