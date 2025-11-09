// HTMX event handlers
export class HtmxHandlers {
    constructor(toast) {
        this.toast = toast;
        this.init();
    }

    init() {
        // Handle HTMX errors
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
