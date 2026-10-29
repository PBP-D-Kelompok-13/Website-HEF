(() => {
    const modal = document.getElementById("compareProductPicker");
    const content = document.getElementById("compare-picker-content");

    if (!modal || !content) return;

    const initialContent = content.innerHTML;
    let productAdded = false;

    function focusSearch() {
        if (modal.classList.contains("show")) {
            document.getElementById("compare-picker-query")?.focus();
        }
    }

    function showError(message) {
        const feedback = document.getElementById("compare-picker-feedback");
        if (!feedback) return;

        const alert = document.createElement("p");
        alert.className = "compare-validation";
        alert.setAttribute("role", "alert");
        alert.textContent = message;

        feedback.replaceChildren(alert);
    }

    function isPickerRequest(event) {
        const element = event.detail.elt;
        return element instanceof Element && (
            modal.contains(element) ||
            element.matches(".compare-add-product")
        );
    }

    document.body.addEventListener("htmx:beforeRequest", (event) => {
        const element = event.detail.elt;

        if (element instanceof Element &&
            element.matches(".compare-add-product")) {
            // Reset ke markup awal milik halaman, bukan HTML dari pengguna.
            content.innerHTML = initialContent;
        }

        if (isPickerRequest(event)) {
            document.getElementById("compare-picker-feedback")
                ?.replaceChildren();
        }
    });

    modal.addEventListener("shown.bs.modal", focusSearch);

    document.body.addEventListener("htmx:afterSwap", (event) => {
        if (event.detail.target.id === "compare-picker-content") {
            focusSearch();
        }
    });

    modal.addEventListener("click", (event) => {
        if (!event.target.closest("[data-compare-clear-search]")) return;

        const input = document.getElementById("compare-picker-query");
        if (!input) return;

        input.value = "";
        input.dispatchEvent(new Event("input", { bubbles: true }));
        input.focus();
    });

    document.body.addEventListener("compareProductAdded", () => {
        productAdded = true;
        bootstrap.Modal.getOrCreateInstance(modal).hide();

        if (!modal.classList.contains("show")) {
            document.getElementById("compare-title")?.focus();
        }
    });

    modal.addEventListener("hidden.bs.modal", () => {
        if (productAdded) {
            document.getElementById("compare-title")?.focus();
            productAdded = false;
        }
    });

    document.body.addEventListener("htmx:beforeSwap", (event) => {
        if (!isPickerRequest(event) || !event.detail.xhr.responseURL) return;

        const responsePath = new URL(event.detail.xhr.responseURL).pathname;

        if (responsePath === modal.dataset.loginUrl) {
            event.detail.shouldSwap = false;
            showError("Your session has expired. Reload this page to sign in again.");
        }
    });

    ["htmx:responseError", "htmx:sendError", "htmx:timeout"].forEach((name) => {
        document.body.addEventListener(name, (event) => {
            if (!isPickerRequest(event)) return;

            showError(
                "The request could not be confirmed. Close this dialog " +
                "and refresh the page before trying again."
            );
        });
    });
})();