function showToasts() {
  document.querySelectorAll("#toast-container .toast").forEach((el) => {
    if (el.dataset.shown) return;
    el.dataset.shown = "1";
    el.addEventListener("hidden.bs.toast", () => el.remove());
    bootstrap.Toast.getOrCreateInstance(el).show();
  });
}

document.addEventListener("DOMContentLoaded", showToasts);
document.body.addEventListener("htmx:oobAfterSwap", showToasts);
