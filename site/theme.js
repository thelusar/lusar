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
      const light = root.dataset.theme === "light";
      const source = light ? "Тёмная тема" : "Светлая тема";
      const label = window.lusarLocale?.text(source) ?? source;
      button.setAttribute("aria-pressed", String(light));
      button.setAttribute("aria-label", label);
      button.title = label;
    }
    button.addEventListener("click", () => {
      const next = root.dataset.theme === "light" ? "dark" : "light";
      root.dataset.theme = next;
      try { localStorage.setItem(key, next); } catch {}
      sync();
    });
    sync();
    document.addEventListener("lusar-language-change", sync);
    button.hidden = false;
  });
})();
