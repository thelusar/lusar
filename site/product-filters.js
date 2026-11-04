function filterProducts(entries, maximum, sort) {
  const visible = entries.filter(entry => maximum === null || (entry.price !== null && entry.price <= maximum));
  if (sort === "low" || sort === "high") {
    const direction = sort === "low" ? 1 : -1;
    visible.sort((a, b) => {
      if (a.price === null) return b.price === null ? 0 : 1;
      if (b.price === null) return -1;
      return direction * (a.price - b.price);
    });
  }
  return visible;
}

(() => {
  const form = document.querySelector("#product-filters");
  if (!form) return;
  const list = document.querySelector(".product-tiles");
  const status = document.querySelector("#product-filter-count");
  const entries = [...list.children].map(element => ({
    element,
    price: element.dataset.price === "" ? null : Number(element.dataset.price)
  }));

  function render() {
    const field = form.elements.maximum;
    const maximum = field.value && field.validity.valid ? field.valueAsNumber : null;
    const visible = filterProducts(entries, maximum, form.elements.sort.value);
    const selected = new Set(visible);
    for (const entry of entries) entry.element.hidden = !selected.has(entry);
    for (const entry of visible) list.append(entry.element);
    status.textContent = visible.length ? `Товаров: ${visible.length}` : "По выбранной цене товаров нет.";
  }

  form.addEventListener("submit", event => event.preventDefault());
  form.addEventListener("input", render);
  form.addEventListener("reset", () => queueMicrotask(render));
  form.hidden = false;
  render();
})();
