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
