(() => {
  const button = document.querySelector("[data-compare]");
  const tableRoot = document.querySelector("#compare-table");
  if (!button && !tableRoot) return;
  const status = document.querySelector("#compare-status");
  const key = "lusar-comparison";
  const maxItems = 4;

  function read() {
    try {
      const value = JSON.parse(localStorage.getItem(key));
      return Array.isArray(value)
        ? [...new Set(value.filter(id => typeof id === "string" && Object.hasOwn(products, id)))].slice(0, maxItems)
        : [];
    } catch {
      return [];
    }
  }

  function toggle(id) {
    const ids = read();
    const selected = ids.includes(id);
    if (!selected && ids.length >= maxItems) {
      status.textContent = "Можно сравнить до четырёх товаров. Уберите один, чтобы добавить другой.";
      return;
    }
    try {
      localStorage.setItem(key, JSON.stringify(selected ? ids.filter(item => item !== id) : [...ids, id]));
      render();
      if (button) status.textContent = selected ? "Товар убран из сравнения." : "Товар добавлен к сравнению.";
      else (tableRoot.querySelector("button") || tableRoot).focus();
    } catch {
      status.textContent = "Не удалось сохранить список в этом браузере.";
    }
  }

  function cell(row, tag, text, scope) {
    const item = document.createElement(tag);
    if (scope) item.scope = scope;
    item.textContent = text;
    row.append(item);
    return item;
  }

  function render() {
    const ids = read();
    if (button) {
      button.setAttribute("aria-pressed", String(ids.includes(button.dataset.compare)));
      return;
    }
    tableRoot.replaceChildren();
    status.textContent = ids.length ? `Товаров для сравнения: ${ids.length}.` : "Добавьте товары из каталога, чтобы сравнить их.";
    if (!ids.length) return;
    const table = document.createElement("table");
    const head = table.createTHead().insertRow();
    cell(head, "th", "Характеристика", "col");
    for (const id of ids) {
      const heading = cell(head, "th", "", "col");
      const link = document.createElement("a");
      link.href = products[id].path;
      link.textContent = products[id].name;
      const remove = document.createElement("button");
      remove.type = "button";
      remove.textContent = "Убрать";
      remove.setAttribute("aria-label", `Убрать из сравнения: ${products[id].name}`);
      remove.addEventListener("click", () => toggle(id));
      heading.append(link, document.createElement("br"), remove);
    }
    const body = table.createTBody();
    function row(label, value) {
      const entry = body.insertRow();
      cell(entry, "th", label, "row");
      for (const id of ids) cell(entry, "td", value(products[id]) || "—");
    }
    const format = new Intl.NumberFormat("ru-RU");
    row("Цена", item => item.price === null ? "Цена по запросу" : format.format(item.price) + " ֏");
    row("Артикул", item => item.sku);
    const fields = new Map();
    for (const id of ids) {
      for (const field of products[id].attributes) fields.set(field.key, field.label);
    }
    for (const [fieldKey, label] of fields) {
      row(label, item => {
        const attribute = item.attributes.find(field => field.key === fieldKey);
        return attribute ? [attribute.value, attribute.unit].filter(Boolean).join(" ") : "";
      });
    }
    tableRoot.append(table);
  }

  button?.addEventListener("click", () => toggle(button.dataset.compare));
  window.addEventListener("storage", event => {
    if (event.key === key || event.key === null) render();
  });
  render();
})();
