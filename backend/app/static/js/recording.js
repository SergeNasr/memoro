// Audio recording manager for voice interactions
export class RecordingManager {
    constructor(toast) {
        this.toast = toast;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.hasRecorded = false;
        this.recordingTimer = null;
        this.longPressTimer = null;
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
        this.fabButton = document.querySelector('.fab[data-modal-open="new-interaction-modal"]');
        if (!this.fabButton) return;

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

        // Prevent default click behavior when recording or if recording just finished
        this.fabButton.addEventListener('click', (e) => {
            if (this.isRecording || this.hasRecorded) {
                e.preventDefault();
                e.stopPropagation();
                this.hasRecorded = false; // Reset after preventing click
            }
        });
    }

    handleStart(event) {
        // Clear any existing timer
        if (this.longPressTimer) {
            clearTimeout(this.longPressTimer);
        }

        // Start long-press timer (200ms to show mic, similar to WhatsApp)
        this.longPressTimer = setTimeout(() => {
            this.startRecording();
        }, 200);
    }

    handleEnd(event) {
        // Clear long-press timer if recording hasn't started
        if (this.longPressTimer) {
            clearTimeout(this.longPressTimer);
            this.longPressTimer = null;
        }

        // If recording, stop it
        if (this.isRecording) {
            this.stopRecording();
        }
    }

    async startRecording() {
        // Request microphone permission
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

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
            this.hasRecorded = true;
            this.uploadAudio();
            stream.getTracks().forEach(track => track.stop());
        };

        // Start recording
        this.mediaRecorder.start();

        // Start visual timer
        this.startRecordingTimer();
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
    }
}

