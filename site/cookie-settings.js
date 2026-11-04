(() => {
  const key = "lusar-cookie-choice-v1";
  const panel = document.querySelector("#cookie-panel");
  const settings = document.querySelector("#cookie-settings");
  const heading = document.querySelector("#cookie-heading");
  const status = document.querySelector("#cookie-status");
  let choice = null;
  try {
    const saved = localStorage.getItem(key);
    if (saved === "essential" || saved === "analytics") choice = saved;
  } catch {}

  function publishChoice() {
    document.documentElement.dataset.analyticsConsent = choice === "analytics" ? "granted" : "denied";
    window.dispatchEvent(new CustomEvent("lusar:analytics-consent", {
      detail: { granted: choice === "analytics" }
    }));
  }

  function openPanel(moveFocus) {
    status.textContent = choice === "analytics" ? "Сейчас статистика разрешена."
      : choice === "essential" ? "Сейчас выбраны только необходимые настройки." : "";
    panel.hidden = false;
    if (moveFocus) heading.focus();
  }

  for (const button of panel.querySelectorAll("[data-cookie-choice]")) {
    button.addEventListener("click", () => {
      choice = button.dataset.cookieChoice;
      try {
        localStorage.setItem(key, choice);
      } catch {
        status.textContent = "Выбор действует на этой странице. Браузер не сохранил настройки.";
        publishChoice();
        return;
      }
      publishChoice();
      panel.hidden = true;
      settings.focus();
    });
  }
  settings.hidden = false;
  settings.addEventListener("click", () => openPanel(true));
  publishChoice();
  if (!choice && !["/cart", "/checkout", "/checkout/received", "/order-status"].includes(location.pathname)) openPanel(false);
})();
