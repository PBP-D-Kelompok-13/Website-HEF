(() => {
    const page = document.getElementById("saved-comparisons-page");
    const error = document.getElementById("saved-search-error");

    if (!page || !error) return;

    let focusResults = false;

    function isSavedRequest(event) {
        const element = event.detail.elt;
        return element instanceof Element && page.contains(element);
    }

    document.body.addEventListener("htmx:beforeRequest", (event) => {
        if (!isSavedRequest(event)) return;

        error.hidden = true;
        error.textContent = "";

        focusResults = event.detail.elt.matches(
            "[data-saved-pagination]"
        );
    });

    document.body.addEventListener("htmx:afterSwap", (event) => {
        if (event.detail.target.id !== "saved-comparison-results") return;

        if (focusResults) {
            document.getElementById("saved-comparison-results")?.focus();
        }

        focusResults = false;
    });

    document.body.addEventListener("htmx:beforeSwap", (event) => {
        if (!isSavedRequest(event) || !event.detail.xhr.responseURL) return;

        const responseURL = new URL(event.detail.xhr.responseURL);

        if (responseURL.pathname === page.dataset.loginUrl) {
            event.detail.shouldSwap = false;
            window.location.assign(responseURL.href);
        }
    });

    ["htmx:responseError", "htmx:sendError", "htmx:timeout"].forEach((name) => {
        document.body.addEventListener(name, (event) => {
            if (!isSavedRequest(event)) return;

            error.textContent =
                "Could not load saved comparisons. " +
                "Press Enter in the search field to try again.";

            error.hidden = false;
        });
    });
})();