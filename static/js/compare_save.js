(() => {
    const modal = document.getElementById("compareSaveModal");
    const content = document.getElementById("compare-save-content");
    const status = document.getElementById("compare-save-status");

    if (!modal || !content || !status) return;

    const initialContent = content.innerHTML;

    function isSaveRequest(event) {
        const element = event.detail.elt;

        return element instanceof Element && (
            modal.contains(element) ||
            element.id === "compare-save-open"
        );
    }

    function focusTitle() {
        if (modal.classList.contains("show")) {
            document.getElementById("compare-save-title")?.focus();
        }
    }

    function showError(message) {
        const loading = document.getElementById("compare-save-opening");
        if (loading) loading.hidden = true;

        const feedback = document.getElementById("compare-save-feedback");
        if (!feedback) return;

        const alert = document.createElement("p");
        alert.className = "compare-validation";
        alert.setAttribute("role", "alert");
        alert.textContent = message;

        feedback.replaceChildren(alert);
    }

    document.body.addEventListener("htmx:beforeRequest", (event) => {
        if (!isSaveRequest(event)) return;

        if (event.detail.elt.id === "compare-save-open") {
            // Markup awal berasal dari template halaman sendiri.
            content.innerHTML = initialContent;
            status.hidden = true;
            status.textContent = "";
        }

        document.getElementById("compare-save-feedback")
            ?.replaceChildren();
    });

    modal.addEventListener("shown.bs.modal", focusTitle);

    document.body.addEventListener("htmx:afterSwap", (event) => {
        if (event.detail.target.id === "compare-save-content") {
            focusTitle();
        }
    });

    document.body.addEventListener("comparisonSaved", () => {
        const confirmation = document.getElementById(
            "compare-save-confirmation"
        );

        status.textContent = confirmation
            ? confirmation.textContent.trim()
            : "Comparison saved.";

        status.hidden = false;

        bootstrap.Modal.getOrCreateInstance(modal).hide();
    });

    modal.addEventListener("hidden.bs.modal", () => {
        document.getElementById("compare-save-open")?.focus();
    });

    document.body.addEventListener("htmx:beforeSwap", (event) => {
        if (!isSaveRequest(event) || !event.detail.xhr.responseURL) return;

        const responsePath = new URL(event.detail.xhr.responseURL).pathname;

        if (responsePath === modal.dataset.loginUrl) {
            event.detail.shouldSwap = false;

            showError(
                "Your session has expired. Reload this page to sign in again."
            );
        }
    });

    ["htmx:responseError", "htmx:sendError", "htmx:timeout"].forEach((name) => {
        document.body.addEventListener(name, (event) => {
            if (!isSaveRequest(event)) return;

            showError(
                "The request could not be confirmed. Close this dialog " +
                "and refresh the page before trying again."
            );
        });
    });
})();