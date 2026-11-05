(() => {
  const scenes = {
    day: ["lusar-scene-day.webp", "Дневной свет из окна и тени на полу", "Дневной свет из окна"],
    warm: ["lusar-hero.webp", "Тёплый свет подвеса и мягкая подсветка вокруг обеденного стола", "Тёплый свет над столом"],
    evening: ["lusar-scene-evening.webp", "Локальный вечерний свет над столом в тёмном интерьере", "Мягкий свет в полутени"]
  };
  const image = document.querySelector("#scene-image");
  const controls = document.querySelector("#scene-controls");
  const caption = document.querySelector("#scene-caption");
  const buttons = [...controls.querySelectorAll("[data-scene]")];
  let requested = 0;
  let current = "warm";
  let transition;
  controls.hidden = false;
  for (const button of buttons) {
    button.addEventListener("click", () => {
      const key = button.dataset.scene;
      const request = ++requested;
      const [file, alt, description] = scenes[key];
      if (key === current) {
        caption.textContent = description;
        return;
      }
      const next = new Image();
      next.addEventListener("load", () => {
        if (request !== requested) return;
        transition?.cancel();
        if (!matchMedia("(prefers-reduced-motion: reduce)").matches) {
          const previous = image.cloneNode();
          previous.removeAttribute("id");
          previous.removeAttribute("fetchpriority");
          previous.alt = "";
          previous.setAttribute("aria-hidden", "true");
          previous.className = "scene-previous";
          image.after(previous);
          transition = previous.animate([{opacity: 1}, {opacity: 0}], {duration: 240, easing: "ease-out"});
          transition.finished.then(() => previous.remove(), () => previous.remove());
        }
        image.src = next.src;
        image.alt = alt;
        caption.textContent = description;
        current = key;
        for (const option of buttons) option.setAttribute("aria-pressed", String(option === button));
      }, { once: true });
      next.addEventListener("error", () => {
        if (request === requested) caption.textContent = "Сцена не загрузилась. Попробуйте ещё раз.";
      }, { once: true });
      next.src = "/scenes/" + file;
    });
  }
})();
