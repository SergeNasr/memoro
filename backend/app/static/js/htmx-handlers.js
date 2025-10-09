// HTMX event handlers
export class HtmxHandlers {
    constructor(toast) {
        this.toast = toast;
        this.init();
    }

    init() {
        document.body.addEventListener('htmx:afterSwap', (evt) => {
            this.handleSuccess(evt);
        });

        document.body.addEventListener('htmx:responseError', (evt) => {
            this.handleError(evt);
        });

        // Handle button disabling during requests
        document.body.addEventListener('htmx:beforeRequest', (evt) => {
            this.handleBeforeRequest(evt);
        });

        document.body.addEventListener('htmx:afterRequest', (evt) => {
            this.handleAfterRequest(evt);
        });
    }

    handleSuccess(evt) {
        const { xhr, target } = evt.detail;

        if (xhr.status === 200 || xhr.status === 201) {
            const message = target.getAttribute('data-success-message');
            if (message) {
                this.toast.show(message, 'info');
            }
        }
    }

    handleError(evt) {
        let message = 'Something went wrong';

        try {
            const response = JSON.parse(evt.detail.xhr.responseText);
            message = response.detail || message;
        } catch (e) {
            // Use default message
        }

        this.toast.show(message, 'error');
    }

    handleBeforeRequest(evt) {
        // Disable the analyze button during request
        const analyzeBtn = document.getElementById('analyze-btn');
        if (analyzeBtn) {
            analyzeBtn.disabled = true;
            analyzeBtn.textContent = 'Analyzing...';
        }
    }

    handleAfterRequest(evt) {
        // Re-enable the analyze button after request
        const analyzeBtn = document.getElementById('analyze-btn');
        if (analyzeBtn) {
            analyzeBtn.disabled = false;
            analyzeBtn.textContent = 'Analyze';
        }
    }
}
