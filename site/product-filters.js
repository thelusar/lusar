(() => {
  const form = document.querySelector("#product-filters");
  if (!form) return;
  const list = document.querySelector(".product-tiles");
  const status = document.querySelector("#product-filter-count");
  const empty = document.querySelector("#catalog-empty");
  const fields = ["q", "category", "minimum", "maximum", "socket", "temperature", "sort"];
  const normalize = value => value.normalize("NFKC").toLocaleLowerCase().replaceAll("ё", "е");
  const entries = [...list.children].map(element => ({
    element, price: element.dataset.price === "" ? null : Number(element.dataset.price),
    search: normalize(element.dataset.search), category: element.dataset.category,
    socket: element.dataset.socket, temperature: element.dataset.temperature
  }));

  function restore() {
    form.reset();
    const params = new URLSearchParams(location.search);
    for (const name of fields) {
      const field = form.elements.namedItem(name);
      if (!field || !params.has(name)) continue;
      field.value = params.get(name);
      if (field.tagName === "SELECT" && !field.value) field.value = name === "sort" ? "default" : "";
    }
    if (["category", "minimum", "maximum", "socket", "temperature"].some(name => form.elements.namedItem(name)?.value)) {
      form.querySelector("details").open = true;
    }
    render(false);
  }

  function render(updateURL = true) {
    const value = name => form.elements.namedItem(name)?.value || "";
    const minimum = value("minimum") && form.elements.minimum.validity.valid ? form.elements.minimum.valueAsNumber : null;
    const maximum = value("maximum") && form.elements.maximum.validity.valid ? form.elements.maximum.valueAsNumber : null;
    const terms = normalize(value("q").trim()).split(/\s+/u).filter(Boolean);
    const visible = entries.filter(entry =>
      terms.every(term => entry.search.includes(term)) &&
      ["category", "socket", "temperature"].every(name => !value(name) || value(name) === entry[name]) &&
      (minimum === null || (entry.price !== null && entry.price >= minimum)) &&
      (maximum === null || (entry.price !== null && entry.price <= maximum))
    );
    const sort = value("sort");
    if (sort === "low" || sort === "high") {
      visible.sort((a, b) => a.price === null ? b.price === null ? 0 : 1 : b.price === null ? -1 : (sort === "low" ? 1 : -1) * (a.price - b.price));
    }
    const selected = new Set(visible);
    for (const entry of entries) entry.element.hidden = !selected.has(entry);
    for (const entry of visible) list.append(entry.element);
    status.textContent = `Товаров: ${visible.length}`;
    empty.hidden = visible.length !== 0;
    list.hidden = visible.length === 0;
    if (updateURL) {
      const url = new URL(location.href);
      for (const name of fields) {
        const current = value(name).trim();
        if (current && !(name === "sort" && current === "default")) url.searchParams.set(name, current);
        else url.searchParams.delete(name);
      }
      history.replaceState(null, "", url);
    }
  }

  form.addEventListener("submit", event => event.preventDefault());
  form.addEventListener("input", () => render());
  form.addEventListener("change", () => render());
  form.addEventListener("reset", () => queueMicrotask(() => render()));
  window.addEventListener("popstate", restore);
  form.hidden = false;
  restore();
})();
