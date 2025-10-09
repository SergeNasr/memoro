// Modal management
export class Modal {
    constructor() {
        this.init();
    }

    init() {
        // Event delegation for all modal interactions
        document.addEventListener('click', (e) => {
            // Open modal via data-modal-open
            if (e.target.hasAttribute('data-modal-open')) {
                const modalId = e.target.getAttribute('data-modal-open');
                this.open(modalId);
            }

            // Close modal via data-modal-close
            if (e.target.hasAttribute('data-modal-close')) {
                const modal = e.target.closest('[data-modal]');
                if (modal) this.close(modal);
            }

            // Close modal on overlay click
            if (e.target.hasAttribute('data-modal')) {
                this.close(e.target);
            }
        });

        // Escape key to close all modals
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeAll();
            }
        });
    }

    open(modalId) {
        const modal = document.getElementById(modalId);
        if (!modal) return;

        modal.classList.add('active');

        // Auto-focus first input/textarea
        const focusable = modal.querySelector('[autofocus], textarea, input');
        if (focusable) focusable.focus();
    }

    close(modal) {
        modal.classList.remove('active');

        // Reset the new interaction modal to initial state
        if (modal.id === 'new-interaction-modal') {
            this.resetNewInteractionModal();
        }
    }

    closeAll() {
        document.querySelectorAll('[data-modal].active').forEach(modal => {
            this.close(modal);
        });
    }

    resetNewInteractionModal() {
        // Reset the form (clears textarea and resets button state)
        const form = document.querySelector('#new-interaction-modal form');
        if (form) form.reset();

        // Clear the review form content
        const reviewForm = document.getElementById('review-form');
        if (reviewForm) reviewForm.innerHTML = '';
    }
}
