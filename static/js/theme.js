const THEME_KEY = "hef-theme";

function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  document.querySelectorAll(".hef-theme-option").forEach((btn) => {
    btn.setAttribute("aria-pressed", btn.dataset.themeValue === theme);
  });
}

document.addEventListener("click", (event) => {
  const btn = event.target.closest(".hef-theme-option");
  if (!btn) return;
  const theme = btn.dataset.themeValue;
  applyTheme(theme);
  try { localStorage.setItem(THEME_KEY, theme); } catch (e) {}
});

// Sync aria-pressed with whatever the head script chose
applyTheme(document.documentElement.getAttribute("data-theme") || "light");