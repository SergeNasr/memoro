// Memoro UI - Main entry point
import { Modal } from './modal.js';
import { Toast } from './toast.js';
import { HtmxHandlers } from './htmx-handlers.js';

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    const toast = new Toast();
    new Modal();
    new HtmxHandlers(toast);
});
