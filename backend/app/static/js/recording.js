// Audio recording manager for voice interactions
export class RecordingManager {
    constructor(toast) {
        console.log('[RecordingManager] Constructor called');
        this.toast = toast;
        this.mediaRecorder = null;
        this.stream = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.hasRecorded = false;
        this.isStartingRecording = false;
        this.recordingTimer = null;
        this.pressStartTime = null;
        this.fabButton = null;
        this.textarea = null;

        this.init();
    }

    init() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setupListeners());
        } else {
            this.setupListeners();
        }
    }

    setupListeners() {
        console.log('[RecordingManager] setupListeners() called');
        this.fabButton = document.querySelector('.fab[data-modal-open="new-interaction-modal"]');
        console.log('[RecordingManager] FAB button found:', this.fabButton);
        if (!this.fabButton) {
            console.warn('[RecordingManager] FAB button not found!');
            return;
        }

        // Handle mouse events (desktop)
        this.fabButton.addEventListener('mousedown', (e) => this.handleStart(e));
        this.fabButton.addEventListener('mouseup', (e) => this.handleEnd(e));
        this.fabButton.addEventListener('mouseleave', (e) => this.handleEnd(e));

        // Handle touch events (mobile)
        this.fabButton.addEventListener('touchstart', (e) => {
            e.preventDefault();
            this.handleStart(e);
        });
        this.fabButton.addEventListener('touchend', (e) => {
            e.preventDefault();
            this.handleEnd(e);
        });
        this.fabButton.addEventListener('touchcancel', (e) => {
            e.preventDefault();
            this.handleEnd(e);
        });

        // Prevent default click behavior only when actively recording
        this.fabButton.addEventListener('click', (e) => {
            console.log('[RecordingManager] Click event fired', {
                isRecording: this.isRecording,
                hasRecorded: this.hasRecorded
            });
            if (this.isRecording) {
                console.log('[RecordingManager] Preventing click, currently recording');
                e.preventDefault();
                e.stopPropagation();
            } else {
                console.log('[RecordingManager] Click allowed, modal will open');
                // Reset hasRecorded on successful click (not recording)
                this.hasRecorded = false;
            }
        });
    }

    handleStart(event) {
        console.log('[RecordingManager] handleStart called', {
            isStartingRecording: this.isStartingRecording,
            isRecording: this.isRecording
        });

        // Prevent multiple simultaneous starts
        if (this.isStartingRecording || this.isRecording) {
            console.log('[RecordingManager] Already starting or recording, ignoring');
            return;
        }

        // Record when press started
        this.pressStartTime = Date.now();
        // Start recording immediately on press/hold
        console.log('[RecordingManager] Calling startRecording()');
        this.startRecording();
    }

    handleEnd(event) {
        const pressDuration = Date.now() - (this.pressStartTime || 0);

        // If recording has actually started, stop it
        if (this.isRecording) {
            // If very quick release (< 100ms), treat as click and cancel recording
            if (pressDuration < 100) {
                this.cancelRecording();
                this.hasRecorded = false; // Allow modal to open
            } else {
                this.stopRecording();
            }
        } else if (this.isStartingRecording) {
            // If we're still starting (permission dialog), mark to cancel when it completes
            this.isStartingRecording = false;
        }

        this.pressStartTime = null;
    }

    async startRecording() {
        console.log('[RecordingManager] startRecording() called');

        // Prevent multiple simultaneous starts
        if (this.isStartingRecording || this.isRecording) {
            console.log('[RecordingManager] Already starting or recording, returning early');
            return;
        }

        this.isStartingRecording = true;
        console.log('[RecordingManager] Setting isStartingRecording=true, requesting getUserMedia...');

        let stream = null;
        try {
            // Request microphone permission
            console.log('[RecordingManager] Calling navigator.mediaDevices.getUserMedia()');
            stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            console.log('[RecordingManager] getUserMedia() succeeded, stream:', stream);

            // Check if user released button while waiting for permission
            if (!this.isStartingRecording) {
                console.log('[RecordingManager] User released during permission request, cleaning up');
                // User released before permission was granted, clean up
                stream.getTracks().forEach(track => track.stop());
                return;
            }

            // Store stream reference for cleanup
            this.stream = stream;

            // Create MediaRecorder
            const options = { mimeType: 'audio/webm' };
            if (!MediaRecorder.isTypeSupported(options.mimeType)) {
                // Fallback to default
                this.mediaRecorder = new MediaRecorder(stream);
            } else {
                this.mediaRecorder = new MediaRecorder(stream, options);
            }

            this.audioChunks = [];
            this.isRecording = true;
            this.isStartingRecording = false;

            // Show visual feedback
            this.fabButton.classList.add('recording');
            this.fabButton.textContent = '🎤';

            // Set up MediaRecorder event handlers
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                }
            };

            this.mediaRecorder.onstop = () => {
                if (this.audioChunks.length > 0) {
                    this.hasRecorded = true;
                    this.uploadAudio();
                }
                if (this.stream) {
                    this.stream.getTracks().forEach(track => track.stop());
                    this.stream = null;
                }
            };

            // Start recording
            console.log('[RecordingManager] Starting MediaRecorder...');
            this.mediaRecorder.start();
            console.log('[RecordingManager] Recording started successfully');

            // Start visual timer
            this.startRecordingTimer();
        } catch (error) {
            console.error('[RecordingManager] Error in startRecording():', error);
            console.error('[RecordingManager] Error details:', {
                name: error.name,
                message: error.message,
                stack: error.stack
            });

            // Clean up stream if it was created
            if (stream) {
                console.log('[RecordingManager] Cleaning up stream');
                stream.getTracks().forEach(track => track.stop());
            }
            // Also clean up stored stream reference
            if (this.stream) {
                this.stream.getTracks().forEach(track => track.stop());
                this.stream = null;
            }

            // Reset recording state
            this.isRecording = false;
            this.isStartingRecording = false;
            this.fabButton.classList.remove('recording');
            this.fabButton.textContent = '+';

            // Handle different error types
            let errorMessage = 'Failed to start recording';
            if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
                errorMessage = 'Microphone permission denied. Please allow microphone access in your browser settings.';
            } else if (error.name === 'NotFoundError' || error.name === 'DevicesNotFoundError') {
                errorMessage = 'No microphone found. Please connect a microphone and try again.';
            } else if (error.name === 'NotReadableError' || error.name === 'TrackStartError') {
                errorMessage = 'Microphone is already in use by another application.';
            } else if (error.name === 'OverconstrainedError' || error.name === 'ConstraintNotSatisfiedError') {
                errorMessage = 'Microphone does not meet the required constraints.';
            }

            console.log('[RecordingManager] Showing error toast:', errorMessage);
            this.toast.show(errorMessage, 'error');
        }
    }

    cancelRecording() {
        if (!this.isRecording || !this.mediaRecorder) return;

        this.isRecording = false;
        this.fabButton.classList.remove('recording');
        this.fabButton.textContent = '+';

        if (this.recordingTimer) {
            clearInterval(this.recordingTimer);
            this.recordingTimer = null;
        }

        // Stop MediaRecorder without uploading
        if (this.mediaRecorder.state !== 'inactive') {
            this.mediaRecorder.stop();
            // Clear chunks so uploadAudio doesn't run
            this.audioChunks = [];
        }

        // Stop stream tracks
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
    }

    stopRecording() {
        if (!this.isRecording || !this.mediaRecorder) return;

        this.isRecording = false;
        this.fabButton.classList.remove('recording');
        this.fabButton.textContent = '+';

        if (this.recordingTimer) {
            clearInterval(this.recordingTimer);
            this.recordingTimer = null;
        }

        // Stop MediaRecorder (will trigger onstop)
        if (this.mediaRecorder.state !== 'inactive') {
            this.mediaRecorder.stop();
        }
    }

    startRecordingTimer() {
        let seconds = 0;
        this.recordingTimer = setInterval(() => {
            seconds++;
            // Visual feedback could show timer, but for now just keep pulsing
        }, 1000);
    }

    async uploadAudio() {
        if (this.audioChunks.length === 0) {
            this.toast.show('No audio recorded', 'error');
            return;
        }

        // Create blob from chunks
        const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });

        // Check file size (OpenAI limit is 25MB)
        if (audioBlob.size > 25 * 1024 * 1024) {
            this.toast.show('Recording too long. Please keep it under 25MB.', 'error');
            return;
        }

        // Show loading state
        this.toast.show('Transcribing audio...', 'info');

        // Create form data
        const formData = new FormData();
        formData.append('audio', audioBlob, 'recording.webm');

        try {
            const response = await fetch('/ui/interactions/transcribe', {
                method: 'POST',
                body: formData,
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Transcription failed');
            }

            // Fill textarea with transcribed text
            this.fillTextarea(data.text);
            this.toast.show('Audio transcribed successfully', 'success');

        } catch (error) {
            console.error('Upload error:', error);
            this.toast.show(error.message || 'Failed to transcribe audio', 'error');
        }
    }

    fillTextarea(text) {
        // Get textarea - it's in the modal
        const modal = document.getElementById('new-interaction-modal');
        if (!modal) return;

        const textarea = modal.querySelector('#interaction-text');
        if (!textarea) return;

        // Set text and trigger input event for any listeners
        textarea.value = text;
        textarea.dispatchEvent(new Event('input', { bubbles: true }));

        // Focus the textarea so user can edit
        textarea.focus();
        textarea.setSelectionRange(text.length, text.length);

        // Reset hasRecorded flag after successfully filling textarea
        this.hasRecorded = false;
    }
}

