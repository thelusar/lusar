(() => {
  "use strict";
  const API = "https://lusar-catalog-studio.sovazones.chatgpt.site/api/storefront";
  const IMAGE_ORIGIN = new URL(API).origin;
  const REFRESH_MS = 30000;
  const $ = id => document.getElementById(id);
  const state = { catalog: null, category: "all", query: "", sort: "new", loading: false, signature: "", activeProduct: null, activeImage: null };
  const el = (tag, className, text) => { const node = document.createElement(tag); if (className) node.className = className; if (text !== undefined) node.textContent = String(text); return node; };
  const text = value => typeof value === "string" ? value : "";
  const categoryById = id => state.catalog?.categories.find(c => c.id === id);
  function imageURL(value) {
    try { const url = new URL(value); return url.origin === IMAGE_ORIGIN && /^\/api\/storefront\/photo\/[a-f0-9-]{36}$/.test(url.pathname) ? url.href : ""; } catch { return ""; }
  }
  const money = product => product.price !== null && Number.isFinite(product.price) ? new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 2 }).format(product.price) + " ֏" : "Цена по запросу";
  const attributeValue = a => [text(a.value), text(a.unit)].filter(Boolean).join(" ");
  function idsWithin(id) {
    const ids = new Set([id]); let changed = true;
    while (changed) { changed = false; for (const category of state.catalog?.categories || []) if (category.parentId && ids.has(category.parentId) && !ids.has(category.id)) { ids.add(category.id); changed = true; } }
    return ids;
  }
  function filteredProducts() {
    const ids = state.category === "all" ? null : idsWithin(state.category);
    const query = state.query.trim().toLocaleLowerCase("ru");
    return [...(state.catalog?.products || [])].filter(p => (!ids || ids.has(p.categoryId)) && (!query || [p.name, p.sku, p.brand, p.description, ...(p.attributes || []).map(a => a.label + " " + attributeValue(a))].join(" ").toLocaleLowerCase("ru").includes(query))).sort((a, b) => {
      if (state.sort === "name") return a.name.localeCompare(b.name, "ru");
      if (state.sort.startsWith("price-")) { if (a.price === null) return b.price === null ? 0 : 1; if (b.price === null) return -1; return state.sort === "price-asc" ? a.price - b.price : b.price - a.price; }
      return b.createdAt.localeCompare(a.createdAt) || a.id.localeCompare(b.id);
    });
  }
  function renderCategories() {
    const root = $("categories"); const fragment = document.createDocumentFragment();
    const add = (id, name, count) => {
      const button = el("button", "category-pill" + (state.category === id ? " selected" : ""), name);
      button.type = "button"; button.setAttribute("aria-pressed", String(state.category === id));
      button.append(el("span", "", count)); button.addEventListener("click", () => { state.category = id; renderCategories(); renderProducts(); }); fragment.append(button);
    };
    add("all", "Все товары", state.catalog.products.length);
    for (const category of state.catalog.categories) { const ids = idsWithin(category.id); const count = state.catalog.products.filter(p => ids.has(p.categoryId)).length; add(category.id, category.parentId ? category.path : category.name, count); }
    root.replaceChildren(fragment);
  }
  function renderProducts() {
    const products = filteredProducts(); const root = $("products"); const fragment = document.createDocumentFragment();
    $("collection-count").textContent = "Товаров: " + products.length;
    for (const product of products) {
      const card = el("article", "product-card"); const link = el("a", "product-card-link");
      const href = new URL(location.href); href.searchParams.set("product", product.id); link.href = href.pathname + href.search;
      link.addEventListener("click", event => { if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return; event.preventDefault(); openProduct(product.id, true); });
      const media = el("div", "product-image"); media.append(el("span", "image-fallback", "L"));
      const src = imageURL(product.images[0]?.url);
      if (src) { const img = el("img"); img.src = src; img.alt = product.name; img.loading = "lazy"; img.decoding = "async"; img.addEventListener("load", () => img.classList.add("loaded")); img.addEventListener("error", () => img.remove()); media.append(img); }
      const body = el("div", "product-card-body"); body.append(el("p", "product-category", categoryById(product.categoryId)?.name || "LUSAR"), el("h2", "product-name", product.name), el("p", "product-sku", product.sku));
      const price = el("p", "product-price", money(product)); if (product.price !== null) price.append(el("small", "", " / " + product.unit)); body.append(price);
      const specs = el("div", "card-specs");
      const keys = ["power", "power_per_m", "temperature", "cri", "voltage", "ip"];
      for (const key of keys) { const a = product.attributes.find(a => a.key === key); if (!a || specs.children.length >= 3) continue; specs.append(el("span", "", key === "cri" ? "Ra " + a.value : key === "voltage" ? a.value + " В" : attributeValue(a))); }
      body.append(specs); link.append(media, body); card.append(link); fragment.append(card);
    }
    root.replaceChildren(fragment); root.setAttribute("aria-busy", "false");
    $("empty").hidden = products.length !== 0;
    const hasFilters = !!state.query.trim() || state.category !== "all";
    $("empty-title").textContent = hasFilters ? "Ничего не найдено" : "Коллекция готовится";
    $("empty-text").textContent = hasFilters ? "Попробуйте другое название, артикул или категорию." : "Скоро здесь появятся товары LUSAR.";
    $("reset-filters").hidden = !hasFilters;
  }
  function setImage(product, id) {
    state.activeImage = id; const photo = product.images.find(p => p.id === id) || product.images[0]; const main = document.querySelector(".detail-main-photo"); if (!main) return;
    const img = el("img"); const src = imageURL(photo?.url); if (src) { img.src = src; img.alt = product.name; img.decoding = "async"; img.addEventListener("error", () => main.replaceChildren(el("span", "image-fallback", "L"))); main.replaceChildren(img); } else main.replaceChildren(el("span", "image-fallback", "L"));
    document.querySelectorAll(".detail-thumbnail").forEach(button => button.setAttribute("aria-pressed", String(button.dataset.photo === photo?.id)));
  }
  function renderProduct(product) {
    const root = $("product-detail"); const gallery = el("div", "detail-gallery"); const main = el("div", "detail-main-photo"); gallery.append(main);
    const thumbs = el("div", "detail-thumbnails"); thumbs.setAttribute("aria-label", "Фотографии товара");
    if (product.images.length > 1) product.images.forEach((photo, index) => { const button = el("button", "detail-thumbnail"); button.type = "button"; button.dataset.photo = photo.id; button.setAttribute("aria-label", "Фото " + (index + 1)); const img = el("img"); img.src = imageURL(photo.url); img.alt = ""; img.loading = "lazy"; button.append(img); button.addEventListener("click", () => setImage(product, photo.id)); thumbs.append(button); });
    gallery.append(thumbs); const info = el("div", "detail-info"); info.append(el("p", "product-category", categoryById(product.categoryId)?.path || "LUSAR"));
    if (product.brand) info.append(el("p", "detail-brand", product.brand));
    const title = el("h2", "", product.name); title.id = "detail-title"; info.append(title, el("p", "product-sku", "Артикул: " + product.sku));
    const price = el("p", "detail-price", money(product)); if (product.price !== null) price.append(el("small", "", " / " + product.unit)); info.append(price);
    if (product.description) info.append(el("p", "detail-description", product.description));
    const groups = new Map(); for (const a of product.attributes) { if (!groups.has(a.group)) groups.set(a.group, []); groups.get(a.group).push(a); }
    for (const [name, attributes] of groups) { const section = el("section", "spec-group"); section.append(el("h3", "", name)); const list = el("dl", "spec-list"); for (const a of attributes) { const row = el("div", "spec-line"); row.append(el("dt", "", a.label), el("dd", "", attributeValue(a))); list.append(row); } section.append(list); info.append(section); }
    const share = el("button", "share-button", "Скопировать ссылку на товар"); share.type = "button"; const result = el("p", "share-result"); result.setAttribute("role", "status");
    share.addEventListener("click", async () => { const url = new URL(location.href); url.searchParams.set("product", product.id); try { await navigator.clipboard.writeText(url.href); result.textContent = "Ссылка скопирована"; } catch { result.textContent = "Ссылка на этот товар находится в адресной строке браузера."; } });
    info.append(share, result); root.replaceChildren(gallery, info); setImage(product, state.activeImage || product.images[0]?.id);
  }
  function openProduct(id, writeHistory) {
    const product = state.catalog?.products.find(p => p.id === id); const dialog = $("product-dialog");
    if (!product) { state.activeProduct = id; const unavailable = el("div", "dialog-unavailable"); const h = el("h2", "", "Товар сейчас недоступен"); h.id = "detail-title"; unavailable.append(h, el("p", "", "Выберите другой товар в каталоге.")); $("product-detail").replaceChildren(unavailable); }
    else { if (state.activeProduct !== id) state.activeImage = null; state.activeProduct = id; renderProduct(product); }
    if (!dialog.open) dialog.showModal();
    if (writeHistory) { const url = new URL(location.href); url.searchParams.set("product", id); history.pushState({ product: id }, "", url.pathname + url.search); }
  }
  function closeProduct() { $("product-dialog").close(); state.activeProduct = null; state.activeImage = null; const url = new URL(location.href); url.searchParams.delete("product"); history.replaceState(null, "", url.pathname + url.search); }
  function syncURL() { const id = new URL(location.href).searchParams.get("product"); if (id) openProduct(id, false); else { $("product-dialog").close(); state.activeProduct = null; } }
  async function refresh() {
    if (state.loading) return; state.loading = true; const controller = new AbortController(); const timeout = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(API, { credentials: "omit", mode: "cors", cache: "no-store", signal: controller.signal }); if (!response.ok) throw new Error("Catalog unavailable");
      const data = await response.json(); if (data.schemaVersion !== 1 || !Array.isArray(data.products) || !Array.isArray(data.categories)) throw new Error("Invalid catalog");
      const signature = JSON.stringify(data); $("connection-notice").hidden = true;
      if (state.signature !== signature) { state.catalog = data; state.signature = signature; if (state.category !== "all" && !categoryById(state.category)) state.category = "all"; renderCategories(); renderProducts(); syncURL(); }
    } catch { $("connection-notice").hidden = false; if (!state.catalog) { $("products").replaceChildren(); $("products").setAttribute("aria-busy", "false"); $("empty").hidden = false; $("empty-title").textContent = "Каталог временно недоступен"; $("empty-text").textContent = "Попробуйте обновить страницу немного позже."; $("collection-count").textContent = ""; } }
    finally { clearTimeout(timeout); state.loading = false; }
  }
  $("year").textContent = String(new Date().getFullYear());
  $("search").addEventListener("input", event => { state.query = event.target.value; if (state.catalog) renderProducts(); });
  $("sort").addEventListener("change", event => { state.sort = event.target.value; if (state.catalog) renderProducts(); });
  $("retry").addEventListener("click", refresh);
  $("reset-filters").addEventListener("click", () => { state.category = "all"; state.query = ""; $("search").value = ""; renderCategories(); renderProducts(); });
  $("close-detail").addEventListener("click", closeProduct);
  $("product-dialog").addEventListener("cancel", event => { event.preventDefault(); closeProduct(); });
  $("product-dialog").addEventListener("click", event => { if (event.target === $("product-dialog")) { const rect = event.target.getBoundingClientRect(); if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) closeProduct(); } });
  addEventListener("popstate", () => { if (state.catalog) syncURL(); });
  document.addEventListener("visibilitychange", () => { if (!document.hidden) void refresh(); });
  setInterval(() => { if (!document.hidden) void refresh(); }, REFRESH_MS);
  void refresh();
})();
