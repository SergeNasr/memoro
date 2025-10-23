// Memoro UI - Main entry point
import { Modal } from './modal.js';
import { Toast } from './toast.js';
import { HtmxHandlers } from './htmx-handlers.js';

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    const toast = new Toast();
    const modal = new Modal();
    new HtmxHandlers(toast);

    // Wait for tinykeys to be available
    const initShortcuts = () => {
        if (!window.tinykeys) {
            setTimeout(initShortcuts, 50);
            return;
        }

        window.tinykeys(window, {
            '$mod+k': (e) => {
                e.preventDefault();
                const searchInput = document.querySelector('.search-input');
                if (searchInput) {
                    searchInput.focus();
                    searchInput.select();
                }
            },
            '$mod+.': (e) => {
                e.preventDefault();
                modal.open('new-interaction-modal');
            }
        });
    };

    initShortcuts();
});
