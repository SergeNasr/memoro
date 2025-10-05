// Keyboard shortcuts for Memoro

document.addEventListener('DOMContentLoaded', function() {
    // Global keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Ctrl+K (or Cmd+K on Mac) - Focus search
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            const searchInput = document.querySelector('.search-input');
            if (searchInput) {
                searchInput.focus();
                searchInput.select();
            }
        }

        // Ctrl+N (or Cmd+N on Mac) - New interaction
        if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
            e.preventDefault();
            const fab = document.querySelector('.fab');
            if (fab) {
                fab.click();
            }
        }

        // Escape - Close modal
        if (e.key === 'Escape') {
            const modal = document.querySelector('.modal-overlay.active');
            if (modal) {
                modal.classList.remove('active');
            }
        }
    });

    // Modal controls
    const modalOverlay = document.querySelector('.modal-overlay');
    if (modalOverlay) {
        // Close modal when clicking overlay (not the modal itself)
        modalOverlay.addEventListener('click', function(e) {
            if (e.target === modalOverlay) {
                modalOverlay.classList.remove('active');
            }
        });
    }

    // FAB button to open new interaction modal
    const fab = document.querySelector('.fab');
    if (fab) {
        fab.addEventListener('click', function() {
            const modal = document.getElementById('new-interaction-modal');
            if (modal) {
                modal.classList.add('active');
                // Focus the textarea
                const textarea = modal.querySelector('textarea');
                if (textarea) {
                    textarea.focus();
                }
            }
        });
    }

    // Close button in modal
    const closeButtons = document.querySelectorAll('.modal-close');
    closeButtons.forEach(button => {
        button.addEventListener('click', function() {
            const modal = this.closest('.modal-overlay');
            if (modal) {
                modal.classList.remove('active');
            }
        });
    });

    // Toast notifications
    window.showToast = function(message, type = 'info') {
        let toast = document.querySelector('.toast');
        if (!toast) {
            toast = document.createElement('div');
            toast.className = 'toast';
            document.body.appendChild(toast);
        }

        toast.textContent = message;
        toast.className = 'toast show ' + type;

        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    };

    // HTMX event handlers
    document.body.addEventListener('htmx:afterSwap', function(evt) {
        // Show success toast if configured
        if (evt.detail.xhr.status === 201 || evt.detail.xhr.status === 200) {
            const successMessage = evt.detail.target.getAttribute('data-success-message');
            if (successMessage) {
                showToast(successMessage, 'info');
            }
        }
    });

    document.body.addEventListener('htmx:responseError', function(evt) {
        // Show error toast
        let errorMessage = 'Something went wrong';
        try {
            const response = JSON.parse(evt.detail.xhr.responseText);
            errorMessage = response.detail || errorMessage;
        } catch (e) {
            // Use default message
        }
        showToast(errorMessage, 'error');
    });
});
