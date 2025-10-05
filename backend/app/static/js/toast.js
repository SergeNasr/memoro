// Toast notification management
export class Toast {
    constructor() {
        this.toast = null;
    }

    show(message, type = 'info') {
        if (!this.toast) {
            this.toast = document.createElement('div');
            this.toast.setAttribute('data-toast', '');
            document.body.appendChild(this.toast);
        }

        this.toast.textContent = message;
        this.toast.className = `toast show ${type}`;

        setTimeout(() => {
            this.toast.classList.remove('show');
        }, 3000);
    }
}
