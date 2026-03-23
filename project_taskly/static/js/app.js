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

    // Login Password
    const pwToggle = document.getElementById('pwToggle');
    const pwInput  = document.getElementById('password');
    const pwIcon   = document.getElementById('pwToggleIcon');

    if (pwToggle && pwInput && pwIcon) {
        pwToggle.addEventListener('click', () => {
            const show = pwInput.type === 'password';
            pwInput.type = show ? 'text' : 'password';
            pwIcon.className = show ? 'bi bi-eye-slash' : 'bi bi-eye';
        });
    }

    const loginInputs = document.querySelectorAll('.login-input');

    if (loginInputs.length) {
        loginInputs.forEach(input => {
            const wrap = input.closest('.login-input-wrap');
            if (!wrap) return;

            input.addEventListener('focus', () => wrap.classList.add('focused'));
            input.addEventListener('blur', () => wrap.classList.remove('focused'));
        });
    }

    // Register
    const regInputs = document.querySelectorAll('.reg-input');
    if (regInputs.length) {
        regInputs.forEach(input => {
            const wrap = input.closest('[data-wrap]');
            if (!wrap) return;

            input.addEventListener('focus', () => wrap.classList.add('focused'));
            input.addEventListener('blur', () => wrap.classList.remove('focused'));
        });
    }

    const pwToggles = document.querySelectorAll('.reg-pw-toggle');
    if (pwToggles.length) {
        pwToggles.forEach(btn => {
            btn.addEventListener('click', () => {
                const input = document.getElementById(btn.dataset.target);
                const icon = btn.querySelector('i');
                if (!input || !icon) return;

                const show = input.type === 'password';
                input.type = show ? 'text' : 'password';
                icon.className = show ? 'bi bi-eye-slash' : 'bi bi-eye';
            });
        });
    }

    window.checkStrength = function(val) {
        const meter = document.getElementById('strengthMeter');
        const label = document.getElementById('strengthLabel');
        const bars = [
            document.getElementById('sb1'),
            document.getElementById('sb2'),
            document.getElementById('sb3'),
            document.getElementById('sb4')
        ];

        if (!meter || !label || bars.some(bar => !bar)) return;

        if (!val) {
            meter.style.display = 'none';
            return;
        }

        meter.style.display = 'flex';

        let score = 0;
        if (val.length >= 8) score++;
        if (/[A-Z]/.test(val)) score++;
        if (/[0-9]/.test(val)) score++;
        if (/[^A-Za-z0-9]/.test(val)) score++;

        const levels = [
            { label: 'Weak', color: '#ff5470' },
            { label: 'Fair', color: '#ffb547' },
            { label: 'Good', color: '#4f7cff' },
            { label: 'Strong', color: '#30d87d' },
        ];
        const cls = ['active-weak', 'active-fair', 'active-good', 'active-strong'];

        bars.forEach((bar, i) => {
            bar.className = 'reg-strength-bar';
            if (i < score) bar.classList.add(cls[score - 1]);
        });

        label.textContent = levels[score - 1]?.label || '';
        label.style.color = levels[score - 1]?.color || 'transparent';
    };

    // Check username availability
    const usernameInput = document.getElementById('username');
    const feedback = document.getElementById('usernameFeedback');

    if (usernameInput) {
        usernameInput.addEventListener('input', () => {
            const val = usernameInput.value.trim();
            const icon = feedback.querySelector('i');
            const text = feedback.querySelector('span');

            if (!val) {
                icon.className = '';
                text.textContent = '';
                feedback.classList.remove('available', 'taken');
                return;
            }

            if (val.length < 3) {
                icon.className = 'bi bi-x-circle';
                text.textContent = 'Username too short';
                feedback.classList.add('taken');
                feedback.classList.remove('available');
                return;
            }

            const validUsernameRegex = /^[A-Za-z0-9][A-Za-z0-9_]{2,49}$/;

            if (!validUsernameRegex.test(val)) {
                feedback.classList.add('taken');
                feedback.classList.remove('available');
                icon.className = 'bi bi-x-circle';
                text.textContent = 'Invalid username';
                return;
            }

            fetch(`/check-username/?username=${encodeURIComponent(val)}`)
                .then(res => res.json())
                .then(data => {
                    if (data.available) {
                        feedback.classList.add('available');
                        feedback.classList.remove('taken');
                        icon.className = 'bi bi-check-circle';
                        text.textContent = 'Available';
                    } else {
                        feedback.classList.add('taken');
                        feedback.classList.remove('available');
                        icon.className = 'bi bi-x-circle';
                        text.textContent = 'Taken';
                    }
                })
                .catch(err => {
                    icon.className = '';
                    text.textContent = '';
                    feedback.classList.remove('available', 'taken');
                    console.error(err);
                });
        });
    }

    // Forgot Password
    const emailInput = document.getElementById('email');
    const emailWrap = document.getElementById('emailWrap');
    if (emailInput && emailWrap) {
        emailInput.addEventListener('focus', () => emailWrap.classList.add('focused'));
        emailInput.addEventListener('blur', () => emailWrap.classList.remove('focused'));
    }

    const form = document.getElementById('fp-form');
    const submitBtn = document.getElementById('fp-submit-btn');
    const formView = document.getElementById('fp-form-view');
    const successView = document.getElementById('fp-success-view');
    const sentEmail = document.getElementById('fp-sent-email');

    if (form && submitBtn && formView && successView && sentEmail && emailInput) {
        form.addEventListener('submit', (e) => {
            e.preventDefault();

            const emailVal = emailInput.value.trim();
            if (!emailVal) return;

            submitBtn.classList.add('loading');
            submitBtn.disabled = true;

            setTimeout(() => {
                sentEmail.textContent = emailVal;
                formView.style.display = 'none';
                successView.style.display = 'flex';
                submitBtn.classList.remove('loading');
                submitBtn.disabled = false;
            }, 1400);
        });
    }

    const resendBtn = document.getElementById('fp-resend-btn');
    if (resendBtn) {
        let cooldown = false;

        resendBtn.addEventListener('click', () => {
            if (cooldown) return;
            cooldown = true;
            resendBtn.disabled = true;

            let secs = 30;
            resendBtn.textContent = `Resend in ${secs}s`;

            const timer = setInterval(() => {
                secs--;
                resendBtn.textContent = secs > 0 ? `Resend in ${secs}s` : 'Resend email';
                if (secs <= 0) {
                    clearInterval(timer);
                    resendBtn.disabled = false;
                    cooldown = false;
                }
            }, 1000);
        });
    }
});