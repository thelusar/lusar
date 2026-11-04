(() => {
  const gallery = document.querySelector(".product-gallery");
  const image = gallery.querySelector("#product-photo");
  const link = gallery.querySelector("#product-photo-link");
  const dialog = gallery.querySelector("#product-photo-dialog");
  const large = gallery.querySelector("#product-photo-large");
  const buttons = [...gallery.querySelectorAll("[data-photo]")];
  for (const button of buttons) {
    button.addEventListener("click", () => {
      image.src = button.dataset.photo;
      link.href = button.dataset.photo;
      for (const option of buttons) option.setAttribute("aria-pressed", String(option === button));
    });
  }
  link.addEventListener("click", event => {
    if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || !dialog.showModal) return;
    event.preventDefault();
    large.src = link.href;
    dialog.showModal();
  });
  dialog.addEventListener("close", () => link.focus());
})();
