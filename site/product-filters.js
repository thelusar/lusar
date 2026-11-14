(() => {
  const form = document.querySelector("#product-filters");
  if (!form) return;
  const list = document.querySelector(".product-tiles");
  const status = document.querySelector("#product-filter-count");
  const empty = document.querySelector("#catalog-empty");
  const browser = document.querySelector(".catalog-browser");
  const sidebar = document.querySelector("#catalog-sidebar");
  const trigger = document.querySelector(".catalog-filter-trigger");
  const backdrop = document.querySelector(".catalog-filter-backdrop");
  const mobile = matchMedia("(max-width: 58rem)");
  let savedOverflow = "", returnFocus = null;
  const inertStates = new Map();
  function closeFilters() {
    if (!browser || browser.dataset.filtersOpen !== "true") return;
    browser.dataset.filtersOpen = "false";
    trigger.setAttribute("aria-expanded", "false");
    sidebar.removeAttribute("role"); sidebar.removeAttribute("aria-modal");
    backdrop.hidden = true;
    document.body.style.overflow = savedOverflow;
    for (const [node, inert] of inertStates) node.inert = inert;
    inertStates.clear();
    if (mobile.matches) returnFocus?.focus({preventScroll:true});
  }
  function openFilters() {
    if (!mobile.matches) return;
    returnFocus = trigger;
    savedOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    browser.dataset.filtersOpen = "true";
    trigger.setAttribute("aria-expanded", "true");
    sidebar.setAttribute("role", "dialog"); sidebar.setAttribute("aria-modal", "true");
    backdrop.hidden = false;
    for (const node of document.querySelectorAll(".site-header,.site-footer,.catalog-results,.catalog-heading,.category-page>h1,.category-page>p")) {
      inertStates.set(node, node.inert); node.inert = true;
    }
    sidebar.querySelector("[data-close-filters]").focus({preventScroll:true});
  }
  trigger?.addEventListener("click", openFilters);
  backdrop?.addEventListener("click", closeFilters);
  for (const button of document.querySelectorAll("[data-close-filters]")) button.addEventListener("click", closeFilters);
  const closeWideFilters = () => { if (!mobile.matches) closeFilters(); };
  mobile.addEventListener("change", closeWideFilters);
  window.addEventListener("resize", closeWideFilters, {passive:true});
  document.addEventListener("keydown", event => {
    if (browser?.dataset.filtersOpen !== "true") return;
    if (event.key === "Escape") { event.preventDefault(); closeFilters(); }
    if (event.key !== "Tab") return;
    const focusable = [...sidebar.querySelectorAll('a[href],button,input,select')].filter(node => !node.disabled && node.getClientRects().length);
    const first = focusable[0], last = focusable.at(-1);
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  });
  function setView(view) {
    if (!browser) return;
    const selected = ["grid", "compact", "list"].includes(view) ? view : "grid";
    browser.dataset.view = selected;
    for (const button of browser.querySelectorAll("[data-catalog-view]")) button.setAttribute("aria-pressed", String(button.dataset.catalogView === selected));
    // Switching layout must not leave lazy thumbnails blank in their new positions.
    for (const image of [...list.querySelectorAll('li:not([hidden]) img')].slice(0, 4)) image.loading = "eager";
  }
  if (browser) {
    try { setView(localStorage.getItem("lusar-catalog-view")); } catch { setView("grid"); }
    for (const button of browser.querySelectorAll("[data-catalog-view]")) button.addEventListener("click", () => {
      setView(button.dataset.catalogView);
      try { localStorage.setItem("lusar-catalog-view", browser.dataset.view); } catch {}
    });
  }
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
      const details = form.querySelector("details");
      if (details) details.open = true;
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
    if (sort === "name") visible.sort((a, b) => a.search.localeCompare(b.search, document.documentElement.lang));
    const selected = new Set(visible);
    for (const entry of entries) entry.element.hidden = !selected.has(entry);
    for (const entry of visible) list.append(entry.element);
    status.textContent = `Товаров: ${visible.length}`;
    empty.hidden = visible.length !== 0;
    list.hidden = visible.length === 0;
    const active = fields.filter(name => !["sort"].includes(name) && value(name).trim()).length;
    const activeCount = document.querySelector("#catalog-active-count"), clear = document.querySelector("#catalog-clear");
    if (activeCount) { activeCount.textContent = active; activeCount.hidden = !active; }
    if (clear) clear.hidden = !active;
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
  // Toolbar inputs belong to this form through the form attribute.
  document.addEventListener("input", event => { if (event.target.form === form) render(); });
  document.addEventListener("change", event => { if (event.target.form === form) render(); });
  form.addEventListener("reset", () => queueMicrotask(() => render()));
  window.addEventListener("popstate", restore);
  form.hidden = false;
  restore();
})();
