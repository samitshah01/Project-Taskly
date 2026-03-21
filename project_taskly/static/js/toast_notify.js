document.addEventListener("DOMContentLoaded", function () {
    const container = document.getElementById('toast-container');

    if (!container) return;

    const duration = 5000;
    const speed = 360;

    function createToast(type, message) {
        const el = document.createElement('div');
        el.className = `toast-item toast-${type}`;

        el.innerHTML = `
            <div class="toast-body">
                <div class="toast-title">${type.toUpperCase()}</div>
                <div class="toast-message">${escapeHtml(message)}</div>
            </div>
            <button class="toast-close">&times;</button>
            <div class="toast-progress"></div>
        `;

        const progress = el.querySelector('.toast-progress');

        if (progress) {
            progress.style.transition = `transform ${duration}ms linear`;

            requestAnimationFrame(() => {
                progress.style.transform = 'scaleX(0)';
            });
        }

        let timer = setTimeout(() => close(el), duration);

        const closeBtn = el.querySelector('.toast-close');
        if (closeBtn) {
            closeBtn.onclick = () => close(el);
        }

        el.onmouseenter = () => clearTimeout(timer);
        el.onmouseleave = () => {
            timer = setTimeout(() => close(el), 1500);
        };

        return el;
    }

    function close(el) {
        if (!el) return;

        el.classList.add('closing');
        setTimeout(() => {
            if (el && el.parentNode) {
                el.remove();
            }
        }, speed);
    }

    function show(type, message) {
        if (!container) return;

        const toast = createToast(type, message);
        container.appendChild(toast);

        const items = container.querySelectorAll('.toast-item');
        if (items.length > 5) {
            close(items[0]);
        }
    }

    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    const el = document.getElementById('django-messages');
    if (!el) return;

    let list = [];

    try {
        list = JSON.parse(el.textContent);
    } catch (e) {
        console.warn('Invalid Django messages JSON');
        list = [];
    }

    list.forEach((m, i) => {
        setTimeout(() => {
            const t = m.type || '';

            const type =
                t.includes('success') ? 'success' :
                t.includes('error') ? 'error' :
                t.includes('warning') ? 'warning' :
                'info';

            show(type, m.text || '');
        }, i * 120);
    });

});