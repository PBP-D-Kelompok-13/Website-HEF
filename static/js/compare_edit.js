(() => {
    const modal = document.getElementById("compareEditModal");
    const content = document.getElementById("compare-edit-content");
    const status = document.getElementById("compare-edit-status");
    if (!modal || !content || !status) return;

    const initialContent = content.innerHTML;
    let opener = null;
    let updated = false;

    function requestElement(event) {
        return event.detail.requestConfig?.elt || event.detail.elt;
    }

    function isEditRequest(event) {
        const element = requestElement(event);
        return element instanceof Element && (
            element.matches("[data-compare-edit]") ||
            modal.contains(element)
        );
    }

    function syncRows() {
        const rows = [...content.querySelectorAll("[data-edit-row]")];
        rows.forEach((row, index) => {
            const number = index + 1;
            const select = row.querySelector("select");
            const label = row.querySelector("label");
            const remove = row.querySelector("[data-edit-remove]");
            select.id = "compare-edit-product-" + number;
            label.htmlFor = select.id;
            label.textContent = "Product " + number;
            remove.disabled = rows.length <= 2;
            remove.setAttribute("aria-label", "Remove product " + number);
        });
        const add = content.querySelector("[data-edit-add]");
        if (add) add.disabled = rows.length >= 3;
    }

    function focusTitle() {
        if (modal.classList.contains("show")) {
            document.getElementById("compare-edit-title")?.focus();
        }
    }

    function showError(message) {
        const feedback = document.getElementById("compare-edit-feedback");
        if (feedback) {
            feedback.textContent = message;
            feedback.hidden = false;
        }
        const loading = document.getElementById("compare-edit-opening");
        if (loading) loading.hidden = true;
    }

    content.addEventListener("click", (event) => {
        const add = event.target.closest("[data-edit-add]");
        const remove = event.target.closest("[data-edit-remove]");
        const rows = [...content.querySelectorAll("[data-edit-row]")];

        if (add && rows.length < 3) {
            const row = rows[0].cloneNode(true);
            row.querySelectorAll("[data-unavailable]").forEach(
                (option) => option.remove()
            );
            row.querySelector("select").value = "";
            document.getElementById("compare-edit-products").append(row);
            syncRows();
            row.querySelector("select").focus();
        } else if (remove && rows.length > 2) {
            remove.closest("[data-edit-row]").remove();
            syncRows();
            content.querySelector("[data-edit-add]")?.focus();
        }
    });

    document.body.addEventListener("htmx:beforeRequest", (event) => {
        if (!isEditRequest(event)) return;
        const element = requestElement(event);

        if (element.matches("[data-compare-edit]")) {
            opener = element;
            updated = false;
            // Hanya mengembalikan markup awal dari template sendiri.
            content.innerHTML = initialContent;
            status.hidden = true;
            status.textContent = "";
        }
        const feedback = document.getElementById("compare-edit-feedback");
        if (feedback) {
            feedback.hidden = true;
            feedback.textContent = "";
        }
    });

    modal.addEventListener("shown.bs.modal", focusTitle);

    document.body.addEventListener("htmx:afterSwap", (event) => {
        if (event.detail.target.id !== "compare-edit-content") return;
        syncRows();
        focusTitle();
    });

    document.body.addEventListener("comparisonUpdated", () => {
        const confirmation = document.getElementById(
            "compare-edit-confirmation"
        );
        status.textContent = confirmation?.textContent.trim()
            || "Comparison updated.";
        status.hidden = false;
        updated = true;
        bootstrap.Modal.getOrCreateInstance(modal).hide();
    });

    modal.addEventListener("hidden.bs.modal", () => {
        if (updated) status.focus();
        else if (opener?.isConnected) opener.focus();
    });

    document.body.addEventListener("htmx:beforeSwap", (event) => {
        if (!isEditRequest(event) || !event.detail.xhr.responseURL) return;
        const url = new URL(event.detail.xhr.responseURL);
        if (url.pathname === modal.dataset.loginUrl) {
            event.detail.shouldSwap = false;
            showError("Your session has expired. Reload the page to sign in.");
        }
    });

    ["htmx:responseError", "htmx:sendError", "htmx:timeout"].forEach((name) => {
        document.body.addEventListener(name, (event) => {
            if (!isEditRequest(event)) return;
            showError(
                "The request could not be confirmed. Close this dialog " +
                "and refresh Saved Comparisons before trying again."
            );
        });
    });
})();
