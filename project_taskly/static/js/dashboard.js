document.addEventListener("DOMContentLoaded", function () {
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

    fetch(setTimezoneUrl, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken
        },
        body: JSON.stringify({ timezone: timezone })
    }).catch(() => {});
});