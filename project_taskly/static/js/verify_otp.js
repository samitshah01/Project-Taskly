(function () {
    'use strict';

    const digits = Array.from(document.querySelectorAll('.otp-digit'));
    const hiddenOtp = document.getElementById('otp-hidden');
    const submitBtn = document.getElementById('otp-submit-btn');
    const form = document.getElementById('otp-form');
    const resendBtn = document.getElementById('otp-resend-btn');
    const resendTimerEl = document.getElementById('otp-resend-timer');

    if (!digits.length || !hiddenOtp || !submitBtn || !form || !resendBtn) return;

    digits[0].focus();

    function getOtp() {
        return digits.map(d => d.value).join('');
    }

    function updateState() {
        digits.forEach(d => d.classList.toggle('filled', d.value.length === 1));
        const full = getOtp().length === 6;
        submitBtn.disabled = !full;
        hiddenOtp.value = getOtp();
    }

    function clearErrors() {
        digits.forEach(d => d.classList.remove('otp-error'));
    }

    digits.forEach((box, i) => {
        box.addEventListener('input', e => {
            clearErrors();
            const val = e.target.value.replace(/\D/g, '');
            box.value = val ? val[val.length - 1] : '';
            updateState();
            if (val && i < digits.length - 1) digits[i + 1].focus();
            if (getOtp().length === 6 && i === digits.length - 1) {
                setTimeout(() => submitBtn.click(), 160);
            }
        });

        box.addEventListener('keydown', e => {
            if (e.key === 'Backspace') {
                if (box.value) {
                    box.value = '';
                    updateState();
                } else if (i > 0) {
                    digits[i - 1].focus();
                    digits[i - 1].value = '';
                    updateState();
                }
            }
            if (e.key === 'ArrowLeft' && i > 0) digits[i - 1].focus();
            if (e.key === 'ArrowRight' && i < digits.length - 1) digits[i + 1].focus();
        });

        box.addEventListener('paste', e => {
            e.preventDefault();
            const pasted = (e.clipboardData || window.clipboardData).getData('text').replace(/\D/g, '').slice(0, 6);
            pasted.split('').forEach((ch, idx) => { if (digits[idx]) digits[idx].value = ch; });
            updateState();
            const next = Math.min(pasted.length, digits.length - 1);
            digits[next].focus();
            if (pasted.length === 6) setTimeout(() => submitBtn.click(), 160);
        });

        box.addEventListener('click', () => box.select());
    });

    form.addEventListener('submit', () => {
        hiddenOtp.value = getOtp();
        submitBtn.classList.add('loading');
    });

    const EXPIRY_SECS = 10 * 60;
    let remaining = EXPIRY_SECS;
    const timerVal = document.getElementById('otp-timer-val');
    const timerBadge = document.getElementById('otp-timer-badge');

    const expiryTimer = setInterval(() => {
        remaining--;
        if (remaining <= 0) {
            clearInterval(expiryTimer);
            timerVal.textContent = 'Expired';
            timerBadge.classList.add('urgent');
            submitBtn.disabled = true;
            digits.forEach(d => { d.disabled = true; d.classList.add('otp-error'); });
            return;
        }
        const m = String(Math.floor(remaining / 60)).padStart(2, '0');
        const s = String(remaining % 60).padStart(2, '0');
        timerVal.textContent = `${m}:${s}`;
        if (remaining <= 60) timerBadge.classList.add('urgent');
    }, 1000);

    let resendSecs = 60;
    let resendInterval;

    function startResendTimer() {
        resendBtn.disabled = true;
        resendSecs = 60;
        resendTimerEl.textContent = `${resendSecs}s`;

        resendInterval = setInterval(() => {
            resendSecs--;
            if (resendSecs <= 0) {
                clearInterval(resendInterval);
                resendBtn.disabled = false;
                resendBtn.innerHTML = 'Resend code';
                return;
            }
            resendTimerEl.textContent = `${resendSecs}s`;
        }, 1000);
    }

    startResendTimer();

    resendBtn.addEventListener('click', () => {
        resendBtn.disabled = true;
        resendBtn.innerHTML = 'Sending…';

        fetch("{% url 'resend_otp' %}", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": document.querySelector('[name=csrfmiddlewaretoken]').value
            }
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                if (window.showToast) showToast('success', data.message);

                clearInterval(resendInterval);
                resendBtn.innerHTML = 'Resend in <span id="otp-resend-timer">60s</span>';
                startResendTimer();
            } else {
                if (window.showToast) showToast('error', data.message);
                resendBtn.disabled = false;
                resendBtn.innerHTML = 'Resend code';
            }
        })
        .catch(() => {
            if (window.showToast) showToast('error', 'Something went wrong');
            resendBtn.disabled = false;
            resendBtn.innerHTML = 'Resend code';
        });
    });
})();