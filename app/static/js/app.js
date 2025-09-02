let ws = null;
let selectedLayout = 'double';
let selectedOrientation = 'portrait';
let captureMode = 'manual';
let autoTimeout = null;
let currentSessionData = null;
let selectedPhotoIndices = [];
let isFullscreen = false;

const CAPTURE_LIMITS = { double: 4, quad: 6, strip: 12 };
const FINAL_LIMITS = { double: 2, quad: 4, strip: 8 };

function toggleSettingsDropdown() {
    const dropdown = document.getElementById('settingsDropdown');
    dropdown.classList.toggle('open');
    console.log('Dropdown toggled, open:', dropdown.classList.contains('open'));
}

function selectLayout(layout) {
    selectedLayout = layout;
    document.querySelectorAll('[data-layout]').forEach(btn => btn.classList.remove('active'));
    const btn = document.querySelector(`[data-layout="${layout}"]`);
    if (btn) btn.classList.add('active');

    updateOrientationLabels();
    updateStatus();
    console.log(`Selected layout: ${layout}`);
}

function selectOrientation(orientation) {
    selectedOrientation = orientation;
    document.querySelectorAll('[data-orientation]').forEach(btn => btn.classList.remove('active'));
    const btn = document.querySelector(`[data-orientation="${orientation}"]`);
    if (btn) btn.classList.add('active');
    updateStatus();
    console.log(`Selected orientation: ${orientation}`);
}

function selectMode(mode) {
    captureMode = mode;
    document.querySelectorAll('[data-mode]').forEach(btn => btn.classList.remove('active'));
    const btn = document.querySelector(`[data-mode="${mode}"]`);
    if (btn) btn.classList.add('active');

    const takePhotoBtn = document.getElementById('takePhotoBtn');
    const startAutoBtn = document.getElementById('startAutoBtn');
    const stopAutoBtn = document.getElementById('stopAutoBtn');
    const autoModeInfo = document.getElementById('autoModeInfo');

    if (mode === 'manual') {
        if (takePhotoBtn) takePhotoBtn.style.display = 'block';
        if (startAutoBtn) startAutoBtn.style.display = 'none';
        if (stopAutoBtn) stopAutoBtn.style.display = 'none';
        if (autoModeInfo) autoModeInfo.style.display = 'none';
        stopAutoMode();
    } else {
        if (takePhotoBtn) takePhotoBtn.style.display = 'none';
        if (startAutoBtn) startAutoBtn.style.display = 'block';
        if (stopAutoBtn) stopAutoBtn.style.display = 'none';
        if (autoModeInfo) autoModeInfo.style.display = 'none';
        stopAutoMode();
    }

    updateButtonStates();
    updateStatus();
    console.log(`Selected mode: ${mode}`);
}

async function takePhoto() {
    if (!currentSessionData || !currentSessionData.session_id) {
        await createSession();
    }

    await showCountdown();

    try {
        const response = await fetch('/api/session/capture', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        if (response.ok) {
            const data = await response.json();

            // Flash effect
            document.body.style.background = 'white';
            setTimeout(() => {
                document.body.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
            }, 200);

            updateStatus(`Photo ${data.photo_count}/${data.max_capture_photos} captured`);
            await updateSessionStatus();
        } else {
            const error = await response.text();
            console.error('Failed to capture photo:', error);
            updateStatus('Error capturing photo');
        }
    } catch (error) {
        console.error('Error taking photo:', error);
        updateStatus('Error taking photo');
    }
}

async function startAutoMode() {
    const startAutoBtn = document.getElementById('startAutoBtn');
    const stopAutoBtn = document.getElementById('stopAutoBtn');
    const autoModeInfo = document.getElementById('autoModeInfo');

    if (startAutoBtn) startAutoBtn.style.display = 'none';
    if (stopAutoBtn) stopAutoBtn.style.display = 'block';
    if (autoModeInfo) autoModeInfo.style.display = 'block';

    await createSession();

    const maxPhotos = CAPTURE_LIMITS[selectedLayout];
    let photosTaken = 0;

    const takePhotoInBurst = async () => {
        if (photosTaken < maxPhotos) {
            const autoModeText = document.getElementById('autoModeText');
            if (autoModeText) {
                autoModeText.textContent = `Taking photo ${photosTaken + 1}/${maxPhotos}...`;
            }
            await takePhoto();
            photosTaken++;

            const progressFill = document.getElementById('progressFill');
            if (progressFill) {
                const progress = (photosTaken / maxPhotos) * 100;
                progressFill.style.width = `${progress}%`;
            }

            if (photosTaken < maxPhotos) {
                autoTimeout = setTimeout(takePhotoInBurst, 3000);
            } else {
                if (autoModeText) {
                    autoModeText.textContent = 'All photos captured! Ready for selection.';
                }
                setTimeout(() => {
                    stopAutoMode();
                    setTimeout(showPhotoSelection, 1000);
                }, 1000);
            }
        }
    };

    const autoModeText = document.getElementById('autoModeText');
    if (autoModeText) {
        autoModeText.textContent = 'Starting auto burst mode...';
    }
    autoTimeout = setTimeout(takePhotoInBurst, 2000);
}

function stopAutoMode() {
    if (autoTimeout) {
        clearTimeout(autoTimeout);
        autoTimeout = null;
    }

    const startAutoBtn = document.getElementById('startAutoBtn');
    const stopAutoBtn = document.getElementById('stopAutoBtn');
    const autoModeInfo = document.getElementById('autoModeInfo');
    const progressFill = document.getElementById('progressFill');

    if (startAutoBtn) startAutoBtn.style.display = captureMode !== 'manual' ? 'block' : 'none';
    if (stopAutoBtn) stopAutoBtn.style.display = 'none';
    if (autoModeInfo) autoModeInfo.style.display = 'none';
    if (progressFill) progressFill.style.width = '0%';
}

async function showPhotoSelection() {
    if (!currentSessionData || !currentSessionData.capture_complete) {
        updateStatus('Please complete photo capture first');
        return;
    }

    const selectionScreen = document.getElementById('photoSelectionScreen');
    const photosGrid = document.getElementById('photosGrid');
    const selectionInstruction = document.getElementById('selectionInstruction');
    const selectionCounter = document.getElementById('selectionCounter');

    if (!selectionScreen || !photosGrid) {
        console.error('Photo selection elements not found');
        return;
    }

    const finalCount = FINAL_LIMITS[currentSessionData.layout];
    if (selectionInstruction) {
        selectionInstruction.textContent = `Choose ${finalCount} photos from ${currentSessionData.photos.length} captured photos`;
    }
    if (selectionCounter) {
        selectionCounter.textContent = `0 of ${finalCount} photos selected`;
    }

    photosGrid.className = `photos-grid ${currentSessionData.layout}-selection`;
    photosGrid.innerHTML = '';
    selectedPhotoIndices = [];

    currentSessionData.photos.forEach((photo, index) => {
        const photoDiv = document.createElement('div');
        photoDiv.className = 'photo-option';
        photoDiv.onclick = () => togglePhotoSelection(index);

        photoDiv.innerHTML = `
            <img src="data:image/jpeg;base64,${photo}" alt="Photo ${index + 1}">
            <div class="selection-indicator">${index + 1}</div>
        `;

        photosGrid.appendChild(photoDiv);
    });

    selectionScreen.style.display = 'block';
    updateSelectionUI();
}

function togglePhotoSelection(index) {
    const finalCount = FINAL_LIMITS[currentSessionData.layout];
    const photoOptions = document.querySelectorAll('.photo-option');
    const photoOption = photoOptions[index];

    if (selectedPhotoIndices.includes(index)) {
        selectedPhotoIndices = selectedPhotoIndices.filter(i => i !== index);
        photoOption.classList.remove('selected');
    } else if (selectedPhotoIndices.length < finalCount) {
        selectedPhotoIndices.push(index);
        photoOption.classList.add('selected');
    }

    updateSelectionUI();
}

function closePhotoSelection() {
    const selectionScreen = document.getElementById('photoSelectionScreen');
    if (selectionScreen) {
        selectionScreen.style.display = 'none';
    }
    selectedPhotoIndices = [];
}

async function confirmSelection() {
    if (!currentSessionData || selectedPhotoIndices.length !== FINAL_LIMITS[currentSessionData.layout]) {
        updateStatus('Please select the required number of photos');
        return;
    }

    try {
        updateStatus('Processing selected photos...');

        const response = await fetch('/api/session/select-photos', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                selected_indices: selectedPhotoIndices
            })
        });

        if (response.ok) {
            closePhotoSelection();
            updateStatus('Photos selected! Creating collage...');
            await updateSessionStatus();
            setTimeout(finishSession, 1000);
        } else {
            const error = await response.text();
            console.error('Failed to select photos:', error);
            updateStatus('Error selecting photos');
        }
    } catch (error) {
        console.error('Error confirming selection:', error);
        updateStatus('Error confirming selection');
    }
}

async function finishSession() {
    try {
        updateStatus('Creating final collage...');

        const response = await fetch('/api/session/finalize', {
            method: 'POST'
        });

        if (response.ok) {
            const data = await response.json();
            showFinalPhoto(data.collage);
            updateStatus('Session completed! Photo saved.');
            console.log(`Session finalized: ${data.filename}`);

            setTimeout(() => {
                updateSessionStatus();
            }, 5000);
        } else {
            console.error('Failed to finish session');
            updateStatus('Error finishing session');
        }
    } catch (error) {
        console.error('Error finishing session:', error);
        updateStatus('Error finishing session');
    }
}

async function resetSession() {
    stopAutoMode();
    closePhotoSelection();

    try {
        await fetch('/api/session/reset', { method: 'DELETE' });
        currentSessionData = null;
        selectedPhotoIndices = [];
        await updateSessionStatus();
        updateStatus('Session reset - ready for new photos!');

        const preview = document.getElementById('preview');
        const captureInfo = document.getElementById('captureInfo');
        const captureProgressFill = document.getElementById('captureProgressFill');

        if (preview) preview.className = '';
        if (captureInfo) captureInfo.style.display = 'none';
        if (captureProgressFill) captureProgressFill.style.width = '0%';
    } catch (error) {
        console.error('Error resetting session:', error);
    }
}

async function showGallery() {
    try {
        const response = await fetch('/api/photos');
        const data = await response.json();

        const galleryContent = document.getElementById('galleryContent');
        const galleryModal = document.getElementById('galleryModal');

        if (!galleryContent || !galleryModal) {
            console.error('Gallery elements not found');
            return;
        }

        if (data.photos.length === 0) {
            galleryContent.innerHTML = '<p style="text-align: center; font-size: 1.2rem; margin: 2rem 0;">No photos yet!</p>';
        } else {
            galleryContent.innerHTML = data.photos.map(photo => `
                <div class="gallery-item">
                    <div class="gallery-item-info">
                        <h3>${photo.filename}</h3>
                        <p>Created: ${new Date(photo.created).toLocaleString()}</p>
                        <p>Size: ${(photo.size / 1024).toFixed(1)} KB</p>
                    </div>
                    <a href="${photo.download_url}" download class="btn btn-primary" style="text-decoration: none; padding: 1rem 1.5rem; margin-left: 1rem; min-width: auto;">Download</a>
                </div>
            `).join('');
        }

        galleryModal.style.display = 'block';
    } catch (error) {
        console.error('Error loading gallery:', error);
        const galleryContent = document.getElementById('galleryContent');
        const galleryModal = document.getElementById('galleryModal');

        if (galleryContent) {
            galleryContent.innerHTML = '<p style="text-align: center; font-size: 1.2rem; margin: 2rem 0; color: #ff6b6b;">Error loading gallery</p>';
        }
        if (galleryModal) {
            galleryModal.style.display = 'block';
        }
    }
}

function closeGallery() {
    const galleryModal = document.getElementById('galleryModal');
    if (galleryModal) {
        galleryModal.style.display = 'none';
    }
}

function updateOrientationLabels() {
    const portraitLabel = document.getElementById('portraitLabel');
    const landscapeLabel = document.getElementById('landscapeLabel');

    if (!portraitLabel || !landscapeLabel) return;

    if (selectedLayout === 'strip') {
        portraitLabel.textContent = 'Portrait (2×4)';
        landscapeLabel.textContent = 'Landscape (4×2)';
    } else if (selectedLayout === 'quad') {
        portraitLabel.textContent = 'Portrait (1×4)';
        landscapeLabel.textContent = 'Landscape (2×2)';
    } else {
        portraitLabel.textContent = 'Portrait';
        landscapeLabel.textContent = 'Landscape';
    }
}

async function createSession() {
    try {
        const response = await fetch('/api/session/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                layout: selectedLayout,
                orientation: selectedOrientation
            })
        });

        if (response.ok) {
            const data = await response.json();
            console.log(`Created session: ${data.layout} (capture ${data.max_capture_photos}→${data.final_photos_needed})`);
            await updateSessionStatus();
        } else {
            console.error('Failed to create session');
            updateStatus('Error creating session');
        }
    } catch (error) {
        console.error('Error creating session:', error);
        updateStatus('Error creating session');
    }
}

function showCountdown() {
    return new Promise((resolve) => {
        const countdownEl = document.getElementById('countdown');
        if (!countdownEl) {
            resolve();
            return;
        }

        countdownEl.style.display = 'block';
        let count = 3;
        countdownEl.textContent = count;

        const interval = setInterval(() => {
            count--;
            if (count > 0) {
                countdownEl.textContent = count;
            } else {
                countdownEl.textContent = 'SMILE!';
                setTimeout(() => {
                    countdownEl.style.display = 'none';
                    clearInterval(interval);
                    resolve();
                }, 500);
            }
        }, 1000);
    });
}

function updateCaptureProgress(current, total) {
    const progressFill = document.getElementById('captureProgressFill');
    const captureInfo = document.getElementById('captureInfo');
    const captureInfoText = document.getElementById('captureInfoText');

    if (current > 0) {
        if (captureInfo) captureInfo.style.display = 'block';
        if (progressFill) {
            const progress = (current / total) * 100;
            progressFill.style.width = `${progress}%`;
        }
        if (captureInfoText) {
            captureInfoText.textContent = `Captured ${current} of ${total} photos`;
            if (current >= total) {
                captureInfoText.textContent = `All ${total} photos captured! Ready to select favorites.`;
            }
        }
    } else {
        if (captureInfo) captureInfo.style.display = 'none';
    }
}

async function updateSessionStatus() {
    try {
        const response = await fetch('/api/session/status');
        const data = await response.json();
        currentSessionData = data;
        updateButtonStates();
        updateStatus();
    } catch (error) {
        console.error('Error updating session status:', error);
    }
}

function updateButtonStates() {
    const takePhotoBtn = document.getElementById('takePhotoBtn');
    const selectPhotosBtn = document.getElementById('selectPhotosBtn');
    const finishBtn = document.getElementById('finishBtn');

    if (currentSessionData && currentSessionData.session_id) {
        const maxCapturePhotos = currentSessionData.max_capture_photos || CAPTURE_LIMITS[currentSessionData.layout];
        const currentCount = currentSessionData.photo_count || 0;
        const captureComplete = currentSessionData.capture_complete;
        const selectionComplete = currentSessionData.selection_complete;

        if (captureMode === 'manual') {
            if (!captureComplete) {
                if (takePhotoBtn) takePhotoBtn.disabled = false;
                if (selectPhotosBtn) selectPhotosBtn.style.display = 'none';
                if (finishBtn) finishBtn.style.display = 'none';
            } else if (!selectionComplete) {
                if (takePhotoBtn) takePhotoBtn.disabled = true;
                if (selectPhotosBtn) {
                    selectPhotosBtn.style.display = 'block';
                    selectPhotosBtn.disabled = false;
                }
                if (finishBtn) finishBtn.style.display = 'none';
            } else {
                if (takePhotoBtn) takePhotoBtn.disabled = true;
                if (selectPhotosBtn) selectPhotosBtn.style.display = 'none';
                if (finishBtn) {
                    finishBtn.style.display = 'block';
                    finishBtn.disabled = false;
                }
            }
        }
    } else {
        if (takePhotoBtn) takePhotoBtn.disabled = false;
        if (selectPhotosBtn) selectPhotosBtn.style.display = 'none';
        if (finishBtn) finishBtn.style.display = 'none';
    }
}

function showFinalPhoto(imageData) {
    const preview = document.getElementById('preview');
    if (preview) {
        preview.src = `data:image/jpeg;base64,${imageData}`;
        preview.className = 'final-photo';
    }
}

function updateStatus(message) {
    const statusEl = document.getElementById('status');
    if (!statusEl) return;

    if (message) {
        statusEl.textContent = message;
    } else if (currentSessionData && currentSessionData.session_id) {
        const captureLimit = CAPTURE_LIMITS[selectedLayout];
        const finalLimit = FINAL_LIMITS[selectedLayout];
        const currentCount = currentSessionData.photo_count || 0;

        if (currentSessionData.capture_complete && !currentSessionData.selection_complete) {
            statusEl.textContent = `${captureLimit} photos captured • Ready to select ${finalLimit} favorites`;
        } else if (currentSessionData.selection_complete) {
            statusEl.textContent = `Photos selected • Creating ${selectedLayout.toUpperCase()} ${selectedOrientation} collage`;
        } else {
            statusEl.textContent = `${currentCount}/${captureLimit} photos • Select ${finalLimit} • ${selectedLayout.toUpperCase()} ${selectedOrientation}`;
        }
    } else {
        const captureLimit = CAPTURE_LIMITS[selectedLayout];
        const finalLimit = FINAL_LIMITS[selectedLayout];
        statusEl.textContent = `Ready: ${selectedLayout.toUpperCase()} ${selectedOrientation} • Capture ${captureLimit}→Select ${finalLimit}`;
    }
}

function updateSelectionUI() {
    if (!currentSessionData) return;

    const finalCount = FINAL_LIMITS[currentSessionData.layout];
    const selectionCounter = document.getElementById('selectionCounter');
    const confirmBtn = document.getElementById('confirmSelectionBtn');

    if (selectionCounter) {
        selectionCounter.textContent = `${selectedPhotoIndices.length} of ${finalCount} photos selected`;
    }

    document.querySelectorAll('.photo-option').forEach((photoOption, index) => {
        const indicator = photoOption.querySelector('.selection-indicator');
        if (indicator) {
            if (selectedPhotoIndices.includes(index)) {
                const selectionOrder = selectedPhotoIndices.indexOf(index) + 1;
                indicator.textContent = selectionOrder;
            } else {
                indicator.textContent = index + 1;
            }
        }
    });

    if (confirmBtn) {
        confirmBtn.disabled = selectedPhotoIndices.length !== finalCount;
    }
}

// WebSocket and initialization
function initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    ws = new WebSocket(wsUrl);

    ws.onmessage = function(event) {
        const data = JSON.parse(event.data);

        if (data.type === 'preview') {
            const preview = document.getElementById('preview');
            if (preview) {
                preview.src = `data:image/jpeg;base64,${data.data}`;
            }
        } else if (data.type === 'photo_captured') {
            updateSessionStatus();
            updateCaptureProgress(data.photo_count, data.max_capture_photos);

            if (data.capture_complete) {
                console.log('Capture phase complete - ready for selection');
            }
        } else if (data.type === 'selection_complete') {
            console.log('Photo selection completed');
        } else if (data.type === 'session_complete') {
            showFinalPhoto(data.collage);
            stopAutoMode();
            updateSessionStatus();
        }
    };

    ws.onerror = function(error) {
        console.error('WebSocket error:', error);
        updateStatus('Camera connection failed');
    };

    ws.onclose = function() {
        console.log('WebSocket connection closed');
        setTimeout(initWebSocket, 3000);
    };
}

function initFullscreen() {
    const elem = document.documentElement;
    if (elem.requestFullscreen) {
        elem.requestFullscreen().catch(e => console.log('Fullscreen request failed:', e));
    } else if (elem.webkitRequestFullscreen) {
        elem.webkitRequestFullscreen();
    } else if (elem.msRequestFullscreen) {
        elem.msRequestFullscreen();
    }

    document.addEventListener('contextmenu', e => e.preventDefault());
    document.addEventListener('selectstart', e => e.preventDefault());
}

function closeDropdownOnClickOutside(event) {
    const dropdown = document.getElementById('settingsDropdown');
    if (dropdown && !dropdown.contains(event.target) && dropdown.classList.contains('open')) {
        dropdown.classList.remove('open');
    }
}

function init() {
    console.log('Initializing Touchscreen Photobooth...');
    initWebSocket();
    setTimeout(initFullscreen, 1000);

    updateSessionStatus();
    updateOrientationLabels();
    updateButtonStates();

    document.addEventListener('click', closeDropdownOnClickOutside);
    window.addEventListener('click', (event) => {
        const modal = document.getElementById('galleryModal');
        if (event.target === modal) {
            closeGallery();
        }

        const selectionScreen = document.getElementById('photoSelectionScreen');
        if (event.target === selectionScreen) {
            closePhotoSelection();
        }
    });
    let lastTouchEnd = 0;
    document.addEventListener('touchend', (e) => {
        const now = Date.now();
        if (now - lastTouchEnd <= 300) {
            e.preventDefault();
        }
        lastTouchEnd = now;
    }, { passive: false });
    setInterval(updateSessionStatus, 10000);

    console.log('Touchscreen Photobooth initialized successfully');
}
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}