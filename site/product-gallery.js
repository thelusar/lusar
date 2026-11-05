(() => {
  const gallery = document.querySelector(".product-gallery");
  if (!gallery) return;
  const image = gallery.querySelector("#product-photo");
  const link = gallery.querySelector("#product-photo-link");
  const dialog = gallery.querySelector("#product-photo-dialog");
  const large = gallery.querySelector("#product-photo-large");
  const buttons = [...gallery.querySelectorAll("[data-photo]")];
  let current = 0;
  function select(index) {
    if (!buttons.length) return;
    current = (index + buttons.length) % buttons.length;
    const url = buttons[current].dataset.photo;
    image.src = url;
    link.href = url;
    if (dialog.open) large.src = url;
    for (const [i, button] of buttons.entries()) button.setAttribute("aria-pressed", String(i === current));
    for (const counter of gallery.querySelectorAll("#gallery-counter, .gallery-modal-counter")) counter.textContent = `${current + 1} / ${buttons.length}`;
  }
  for (const [index, button] of buttons.entries()) button.addEventListener("click", () => select(index));
  if (buttons.length > 1) {
    for (const controls of gallery.querySelectorAll(".gallery-navigation, .gallery-modal-navigation")) controls.hidden = false;
    for (const button of gallery.querySelectorAll("[data-gallery-step]")) {
      button.addEventListener("click", () => select(current + Number(button.dataset.galleryStep)));
    }
    gallery.addEventListener("keydown", event => {
      if (!["ArrowLeft", "ArrowRight"].includes(event.key)) return;
      event.preventDefault();
      select(current + (event.key === "ArrowRight" ? 1 : -1));
    });
  }
  link.addEventListener("click", event => {
    if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || !dialog.showModal) return;
    event.preventDefault();
    large.src = link.href;
    dialog.showModal();
  });
  dialog.addEventListener("click", event => {
    if (event.target !== dialog) return;
    const box = dialog.getBoundingClientRect();
    if (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) dialog.close();
  });
  dialog.addEventListener("close", () => link.focus());
  select(0);
})();
