function normalize(text) {
  return text.normalize("NFKC").toLocaleLowerCase("ru").replaceAll("ё", "е").trim();
}

function findCatalogEntries(entries, query) {
  const words = normalize(query).split(/\s+/).filter(Boolean);
  if (!words.length) return [];
  const exact = normalize(query);
  return entries.filter(entry => {
    const searchable = normalize([entry.name, entry.sku, entry.keywords].join(" "));
    return words.every(word => searchable.includes(word));
  }).sort((a, b) => Number(normalize(b.sku) === exact) - Number(normalize(a.sku) === exact));
}

const form = document.querySelector("#catalog-search");
const input = form.elements.q;
const status = document.querySelector("#search-status");
const results = document.querySelector("#search-results");
input.value = (new URLSearchParams(location.search).get("q") || "").slice(0, 120);

function renderSearch() {
  const query = input.value.trim();
  results.replaceChildren();
  if (!query) {
    status.textContent = "Введите название, артикул или характеристику.";
    return;
  }
  const matches = findCatalogEntries(searchIndex, query);
  status.textContent = matches.length ? `Найдено: ${matches.length}` : "Совпадений нет. Проверьте артикул или откройте каталог.";
  for (const match of matches) {
    const item = document.createElement("li");
    const link = document.createElement("a");
    link.href = match.path;
    link.textContent = match.sku ? `${match.name} · ${match.sku}` : match.name;
    item.append(link);
    results.append(item);
  }
  if (!matches.length) {
    const item = document.createElement("li");
    const link = document.createElement("a");
    link.href = "/catalog";
    link.textContent = "Открыть каталог";
    item.append(link);
    results.append(item);
  }
}

form.addEventListener("submit", event => {
  event.preventDefault();
  const query = input.value.trim();
  history.replaceState(null, "", query ? "/search?" + new URLSearchParams({ q: query }) : "/search");
  renderSearch();
});
renderSearch();
