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
}
