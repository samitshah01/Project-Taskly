document.addEventListener("DOMContentLoaded", function () {
    // Initialize Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.forEach(el => {
        try {
            new bootstrap.Tooltip(el);
        } catch (err) {
            console.warn('Tooltip init failed for element:', el, err);
        }
    });

    // Universal Loader
    const Loader = (function () {
        const overlay = document.getElementById('loaderOverlay');
        const loaderText = document.getElementById('loaderText');
        if (!overlay || !loaderText) return { show: () => {}, hide: () => {} };

        function show(text = null) {
            if (text) loaderText.textContent = text;
            else loaderText.textContent = overlay.dataset.text || 'Loading...';
            overlay.style.visibility = 'visible';
            overlay.style.opacity = '1';
        }

        function hide() {
            overlay.style.opacity = '0';
            setTimeout(() => {
                overlay.style.visibility = 'hidden';
                loaderText.textContent = overlay.dataset.text || 'Loading...';
            }, 300);
        }

        return { show, hide };
    })();

    // Show loader on page load
    Loader.show('Loading page...');
    window.addEventListener('load', () => Loader.hide());

    // Prevent form resubmission on page refresh
    if (window.history.replaceState) {
        window.history.replaceState(null, null, window.location.href);
    }

    // Navbar Toggle
    const navToggle = document.getElementById('navToggle');
    const navLinks = document.getElementById('navLinks');

    let overlay = document.querySelector('.nav-overlay');

    if (navToggle && navLinks) {

        if (!overlay) {
            overlay = document.createElement('div');
            overlay.className = 'nav-overlay';
            document.body.appendChild(overlay);
        }

        navToggle.addEventListener('click', () => {
            navLinks.classList.toggle('open');
            overlay.classList.toggle('active');

            navToggle.innerHTML = navLinks.classList.contains('open')
                ? '<i class="bi bi-x-lg"></i>'
                : '<i class="bi bi-list"></i>';
        });

        if (overlay) {
            overlay.addEventListener('click', () => {
                navLinks.classList.remove('open');
                overlay.classList.remove('active');
                navToggle.innerHTML = '<i class="bi bi-list"></i>';
            });
        }

        const navAnchors = navLinks.querySelectorAll('a');
        if (navAnchors.length > 0) {
            navAnchors.forEach(a => {
                a.addEventListener('click', () => {
                    navLinks.classList.remove('open');
                    overlay.classList.remove('active');
                    navToggle.innerHTML = '<i class="bi bi-list"></i>';
                });
            });
        }
    }

    // Scroll Reveal
    const revealElements = document.querySelectorAll('.reveal');

    if (revealElements.length > 0 && 'IntersectionObserver' in window) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(e => {
                if (e.isIntersecting) {
                    e.target.classList.add('visible');
                }
            });
        }, { threshold: 0.12 });

        revealElements.forEach(el => observer.observe(el));
    }
});