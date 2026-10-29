(() => {
    const modal = document.getElementById("compareDeleteModal");
    const content = document.getElementById("compare-delete-content");
    const status = document.getElementById("compare-delete-status");
    if (!modal || !content || !status) return;

    const initialContent = content.innerHTML;
    let opener = null;
    let deleted = false;

    function requestElement(event) {
        return event.detail.requestConfig?.elt || event.detail.elt;
    }

    function isDeleteRequest(event) {
        const element = requestElement(event);
        return element instanceof Element && (
            element.matches("[data-compare-delete]") || modal.contains(element)
        );
    }

    function focusCancel() {
        if (modal.classList.contains("show")) {
            document.getElementById("compare-delete-cancel")?.focus();
        }
    }

    function showError(message) {
        const feedback = document.getElementById("compare-delete-feedback");
        if (feedback) {
            feedback.textContent = message;
            feedback.hidden = false;
        }
        const loading = document.getElementById("compare-delete-opening");
        if (loading) loading.hidden = true;
    }

    document.body.addEventListener("htmx:beforeRequest", (event) => {
        if (!isDeleteRequest(event)) return;
        const element = requestElement(event);
        if (element.matches("[data-compare-delete]")) {
            opener = element;
            deleted = false;
            // Markup awal berasal dari template halaman sendiri.
            content.innerHTML = initialContent;
            status.hidden = true;
            status.textContent = "";
        }
        const feedback = document.getElementById("compare-delete-feedback");
        if (feedback) {
            feedback.hidden = true;
            feedback.textContent = "";
        }
    });

    modal.addEventListener("shown.bs.modal", focusCancel);
    document.body.addEventListener("htmx:afterSwap", (event) => {
        if (event.detail.target.id === "compare-delete-content") focusCancel();
    });

    document.body.addEventListener("comparisonDeleted", () => {
        const confirmation = document.getElementById("compare-delete-confirmation");
        status.textContent = confirmation?.textContent.trim()
            || "Comparison deleted.";
        status.hidden = false;
        deleted = true;
        bootstrap.Modal.getOrCreateInstance(modal).hide();
    });

    modal.addEventListener("hidden.bs.modal", () => {
        if (deleted) status.focus();
        else if (opener?.isConnected) opener.focus();
    });

    document.body.addEventListener("htmx:beforeSwap", (event) => {
        if (!isDeleteRequest(event) || !event.detail.xhr.responseURL) return;
        const url = new URL(event.detail.xhr.responseURL);
        if (url.pathname === modal.dataset.loginUrl) {
            event.detail.shouldSwap = false;
            showError("Your session has expired. Reload the page to sign in.");
        }
    });

    ["htmx:responseError", "htmx:sendError", "htmx:timeout"].forEach((name) => {
        document.body.addEventListener(name, (event) => {
            if (!isDeleteRequest(event)) return;
            showError(
                "Deletion could not be confirmed. Close this dialog and " +
                "refresh Saved Comparisons to check whether it was deleted."
            );
        });
    });
})();
