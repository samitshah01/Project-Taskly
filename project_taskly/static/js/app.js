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

    // Login Form
    try {
        const loginForm = document.getElementById('loginForm');
        const loginPasswordInput = document.querySelector('#loginForm #password');
        const loginTogglePassword = document.querySelector('#loginForm #togglePassword');

        if (loginForm) {
            loginForm.addEventListener('submit', () => Loader.show('Signing in...'));
        }

        if (loginPasswordInput && loginTogglePassword) {
            loginTogglePassword.addEventListener('click', function () {
                const type = loginPasswordInput.getAttribute('type') === 'password' ? 'text' : 'password';
                loginPasswordInput.setAttribute('type', type);
                const icon = this.querySelector('i');
                if (icon) {
                    icon.classList.toggle('bi-eye');
                    icon.classList.toggle('bi-eye-slash');
                }
            });
        }
    } catch (err) {
        console.error('Login script error:', err);
    }

    // Register Form
    try {
        const registerForm = document.getElementById('registerForm');
        const registerPasswordInput = document.querySelector('#registerForm #password');
        const confirmInput = document.querySelector('#registerForm #confirmPassword');
        const registerTogglePassword = document.querySelector('#registerForm #togglePassword');
        const registerButton = document.querySelector('#registerForm #registerButton');
        const passwordMatchText = document.querySelector('#registerForm #passwordMatch');
        const strengthText = document.querySelector('#registerForm #passwordStrength');
        const termsCheck = document.querySelector('#registerForm #termsCheck');

        if (registerForm && registerPasswordInput && confirmInput && registerTogglePassword && registerButton) {
            let agreed = termsCheck ? termsCheck.checked : true;

            if (termsCheck) {
                termsCheck.addEventListener('change', function () {
                    agreed = termsCheck.checked;
                    checkFormValidity();
                });
            }

            registerTogglePassword.addEventListener('click', () => {
                const isPasswordType = registerPasswordInput.getAttribute('type') === 'password';
                registerPasswordInput.setAttribute('type', isPasswordType ? 'text' : 'password');
                confirmInput.setAttribute('type', isPasswordType ? 'text' : 'password');
                registerTogglePassword.innerHTML = isPasswordType
                    ? '<i class="bi bi-eye-slash"></i>'
                    : '<i class="bi bi-eye"></i>';
            });

            registerPasswordInput.addEventListener('input', () => {
                const val = registerPasswordInput.value;
                let strength = 0;
                if (val.length >= 8) strength++;
                if (/[A-Z]/.test(val)) strength++;
                if (/[a-z]/.test(val)) strength++;
                if (/\d/.test(val)) strength++;
                if (/[!@#$%^&*(),.?":{}|<>]/.test(val)) strength++;

                if (val.length === 0) strengthText.textContent = '';
                else if (strength <= 2) {
                    strengthText.textContent = 'Weak password';
                    strengthText.className = 'form-text text-danger mt-1 d-block';
                } else if (strength <= 4) {
                    strengthText.textContent = 'Medium password';
                    strengthText.className = 'form-text text-warning mt-1 d-block';
                } else {
                    strengthText.textContent = 'Strong password';
                    strengthText.className = 'form-text text-success mt-1 d-block';
                }

                checkFormValidity();
            });

            confirmInput.addEventListener('input', () => {
                if (confirmInput.value !== registerPasswordInput.value && confirmInput.value !== '') {
                    passwordMatchText.classList.remove('d-none');
                } else {
                    passwordMatchText.classList.add('d-none');
                }
                checkFormValidity();
            });

            function checkFormValidity() {
                const strong = strengthText.textContent === 'Strong password';
                const match = registerPasswordInput.value === confirmInput.value && registerPasswordInput.value !== '';
                registerButton.disabled = !(strong && match && agreed);
            }

            checkFormValidity();

            registerForm.addEventListener('submit', () => Loader.show('Creating account...'));
        }
    } catch (err) {
        console.error('Register script error:', err);
    }
});