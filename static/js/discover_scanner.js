(function () {
    const modal = document.getElementById("scannerModal");
    if (!modal) return;

    let scanner = null;
    const status = document.getElementById("scannerStatus");
    const urlTemplate = modal.dataset.lookupUrl || "/products/lookup/__CODE__/";

    function stopScanner() {
        if (!scanner) return Promise.resolve();
        const active = scanner;
        scanner = null;
        return active.stop().catch(function () {}).then(function () {
            try { active.clear(); } catch (e) {}
        });
    }

    modal.addEventListener("shown.bs.modal", function () {
        if (typeof Html5Qrcode === "undefined") {
            status.textContent = "Barcode library failed to load.";
            return;
        }
        status.textContent = "Starting camera...";
        scanner = new Html5Qrcode("reader");
        scanner.start(
            { facingMode: "environment" },
            { fps: 10, qrbox: { width: 250, height: 150 } },
            function (decodedText) {
                const code = (decodedText || "").trim();
                if (!/^\d{8,14}$/.test(code)) return;
                status.textContent = "Found barcode " + code + ". Loading product...";
                stopScanner().then(function () {
                    window.location.href = urlTemplate.replace("__CODE__", encodeURIComponent(code));
                });
            },
            function () {}
        ).then(function () {
            status.textContent = "Point your camera at a food product barcode.";
        }).catch(function () {
            status.textContent = "Could not access camera. Please allow camera permission or type the barcode in the search box.";
        });
    });

    modal.addEventListener("hide.bs.modal", stopScanner);
})();
