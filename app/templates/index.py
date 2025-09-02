def get_html_template() -> str:
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
        <title>Touchscreen Photobooth</title>
        <link rel="stylesheet" href="/static/css/styles.css">
    </head>
    <body>
        <div class="fullscreen-container">
            <!-- Header -->
            <div class="header">
                <div></div>
                <div class="status" id="status">Touchscreen Photobooth Ready!</div>
                <button class="gallery-btn" onclick="showGallery()" aria-label="Open Gallery">📸</button>
            </div>

            <!-- Main Content -->
            <div class="main-content">
                <!-- Full-Screen Camera Preview -->
                <div class="preview-section">
                    <div class="preview-container">
                        <img id="preview" src="" alt="Camera Preview" />
                    </div>
                </div>

                <!-- Floating Controls Overlay -->
                <div class="controls-overlay">
                    <!-- Settings Dropdown -->
                    <div class="settings-dropdown" id="settingsDropdown">
                        <div class="settings-header" onclick="toggleSettingsDropdown()">
                            <span>Settings</span>
                            <span class="dropdown-arrow">▼</span>
                        </div>
                        <div class="settings-content">
                            <div class="setting-group">
                                <div class="setting-label">Layout</div>
                                <div class="button-group">
                                    <button class="option-btn active" data-layout="double" onclick="selectLayout('double')">
                                        Double<br><small>(4→2)</small>
                                    </button>
                                    <button class="option-btn" data-layout="quad" onclick="selectLayout('quad')">
                                        2×2<br><small>(6→4)</small>
                                    </button>
                                    <button class="option-btn" data-layout="strip" onclick="selectLayout('strip')">
                                        Strip<br><small>(12→8)</small>
                                    </button>
                                </div>
                            </div>

                            <div class="setting-group">
                                <div class="setting-label">Orientation</div>
                                <div class="button-group">
                                    <button class="option-btn active" data-orientation="portrait" onclick="selectOrientation('portrait')">
                                        <span id="portraitLabel">Portrait</span>
                                    </button>
                                    <button class="option-btn" data-orientation="landscape" onclick="selectOrientation('landscape')">
                                        <span id="landscapeLabel">Landscape</span>
                                    </button>
                                </div>
                            </div>

                            <div class="setting-group">
                                <div class="setting-label">Mode</div>
                                <div class="button-group">
                                    <button class="option-btn active" data-mode="manual" onclick="selectMode('manual')">
                                        Manual
                                    </button>
                                    <button class="option-btn" data-mode="burst" onclick="selectMode('burst')">
                                        Auto Burst
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Info Panels -->
                    <div id="captureInfo" class="floating-info info-panel">
                        <h3 id="captureInfoTitle">Capture Phase</h3>
                        <p id="captureInfoText">Ready to capture photos</p>
                        <div class="progress-bar">
                            <div class="progress-fill" id="captureProgressFill"></div>
                        </div>
                    </div>

                    <div id="autoModeInfo" class="floating-info auto-mode-panel">
                        <h3>Auto Burst Mode</h3>
                        <p id="autoModeText">Ready to start</p>
                        <div class="progress-bar">
                            <div class="progress-fill" id="progressFill"></div>
                        </div>
                    </div>

                    <!-- Action Buttons -->
                    <div class="action-buttons">
                        <button class="btn btn-primary" id="takePhotoBtn" onclick="takePhoto()">
                            📸 Take Photo
                        </button>
                        <button class="btn btn-secondary" id="startAutoBtn" onclick="startAutoMode()" style="display: none;">
                            🚀 Start Auto Burst
                        </button>
                        <button class="btn btn-warning" id="stopAutoBtn" onclick="stopAutoMode()" style="display: none;">
                            ⏹️ Stop Auto Burst
                        </button>
                        <button class="btn btn-success" id="selectPhotosBtn" onclick="showPhotoSelection()" style="display: none;" disabled>
                            🎯 Select Photos
                        </button>
                        <button class="btn btn-success" id="finishBtn" onclick="finishSession()" style="display: none;" disabled>
                            ✅ Finish Session
                        </button>
                        <button class="btn btn-secondary" id="resetBtn" onclick="resetSession()">
                            🔄 Reset
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Countdown Overlay -->
        <div class="countdown" id="countdown">3</div>

        <!-- Photo Selection Screen -->
        <div id="photoSelectionScreen" class="photo-selection-screen">
            <div class="selection-header">
                <h2>Select Your Best Photos</h2>
                <p class="selection-instruction" id="selectionInstruction">Choose your favorite photos for the final collage</p>
                <div class="selection-counter" id="selectionCounter">0 of 2 photos selected</div>
            </div>
            <div class="photos-grid" id="photosGrid">
                <!-- Photos will be inserted here dynamically -->
            </div>
            <div class="selection-controls">
                <button class="btn btn-success" id="confirmSelectionBtn" onclick="confirmSelection()" disabled>
                    ✅ Confirm Selection
                </button>
                <button class="btn btn-secondary" onclick="closePhotoSelection()">
                    ❌ Cancel
                </button>
            </div>
        </div>

        <!-- Gallery Modal -->
        <div id="galleryModal" class="modal">
            <div class="modal-content">
                <span class="close" onclick="closeGallery()">&times;</span>
                <h2>Photo Gallery</h2>
                <div id="galleryContent">
                    Loading...
                </div>
            </div>
        </div>

        <script src="/static/js/app.js"></script>
    </body>
    </html>
    """