(() => {
    function clearForm(event) {
        const element =
            event.detail?.requestConfig?.elt ||
            event.detail?.elt;

        if (!(element instanceof Element)) {
            return null;
        }

        return element.closest("#compare-clear-form");
    }

    function showFailure(event) {
        if (!clearForm(event)) {
            return;
        }

        const feedback = document.getElementById("compare-clear-error");

        if (!feedback) {
            return;
        }

        feedback.textContent =
            event.detail?.xhr?.status === 403
                ? "Your session may have expired. Refresh this page and try again."
                : "Could not confirm whether the selection was cleared. Refresh this page to check before trying again.";

        feedback.hidden = false;
    }

    document.body.addEventListener("htmx:beforeRequest", (event) => {
        if (!clearForm(event)) {
            return;
        }

        const feedback = document.getElementById("compare-clear-error");

        if (feedback) {
            feedback.hidden = true;
            feedback.textContent = "";
        }
    });

    document.body.addEventListener("htmx:beforeSwap", (event) => {
        const form = clearForm(event);
        const responseUrl = event.detail?.xhr?.responseURL;

        if (!form || !responseUrl) {
            return;
        }

        const destination = new URL(responseUrl, window.location.href);
        const login = new URL(form.dataset.loginUrl, window.location.href);

        if (destination.pathname === login.pathname) {
            event.detail.shouldSwap = false;
            window.location.assign(destination.href);
        }
    });

    document.body.addEventListener("comparisonSelectionCleared", () => {
        const saveStatus = document.getElementById("compare-save-status");

        if (saveStatus) {
            saveStatus.hidden = true;
        }

        document.getElementById("compare-clear-status")?.focus({
            preventScroll: true,
        });
    });

    for (const eventName of [
        "htmx:responseError",
        "htmx:sendError",
        "htmx:timeout",
    ]) {
        document.body.addEventListener(eventName, showFailure);
    }
})();