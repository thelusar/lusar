(() => {
  const key = "lusar-theme";
  const root = document.documentElement;
  try {
    if (localStorage.getItem(key) === "light") root.dataset.theme = "light";
  } catch {}

  document.addEventListener("DOMContentLoaded", () => {
    const button = document.querySelector("#theme-toggle");
    if (!button) return;
    function sync() {
      button.setAttribute("aria-pressed", String(root.dataset.theme === "light"));
    }
    button.addEventListener("click", () => {
      const next = root.dataset.theme === "light" ? "dark" : "light";
      root.dataset.theme = next;
      try { localStorage.setItem(key, next); } catch {}
      sync();
    });
    sync();
    button.hidden = false;
  });
})();
