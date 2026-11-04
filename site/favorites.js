const favoriteKey = "lusar-favorites";
const favoriteButton = document.querySelector("[data-favorite]");
const favoriteList = document.querySelector("#favorite-items");
const favoriteStatus = document.querySelector("#favorite-status");

if (favoriteButton || favoriteList) {
  function readFavorites() {
    try {
      const saved = JSON.parse(localStorage.getItem(favoriteKey));
      return new Set(Array.isArray(saved) ? saved.filter(id => typeof id === "string") : []);
    } catch {
      return new Set();
    }
  }

  function changeFavorite(id, saved) {
    const favorites = readFavorites();
    if (saved) favorites.add(id);
    else favorites.delete(id);
    try {
      localStorage.setItem(favoriteKey, JSON.stringify([...favorites]));
    } catch {
      favoriteStatus.textContent = "Не удалось обновить избранное в этом браузере.";
      return;
    }
    renderFavorites();
    if (favoriteButton || favoriteList.children.length) {
      favoriteStatus.textContent = saved ? "Товар добавлен в избранное." : "Товар удалён из избранного.";
    }
  }

  function renderFavorites() {
    const favorites = readFavorites();
    if (favoriteButton) {
      const saved = favorites.has(favoriteButton.dataset.favorite);
      favoriteButton.setAttribute("aria-pressed", String(saved));
      return;
    }
    favoriteList.replaceChildren();
    for (const id of favorites) {
      const item = document.createElement("li");
      const product = Object.hasOwn(products, id) ? products[id] : null;
      if (product) {
        const link = document.createElement("a");
        link.href = product.path;
        link.textContent = product.name;
        item.append(link);
      } else {
        const unavailable = document.createElement("p");
        unavailable.textContent = "Товар сейчас недоступен.";
        item.append(unavailable);
      }
      const remove = document.createElement("button");
      remove.type = "button";
      remove.textContent = "Убрать из избранного";
      if (product) remove.setAttribute("aria-label", `Убрать из избранного: ${product.name}`);
      remove.addEventListener("click", () => {
        changeFavorite(id, false);
        if (!item.isConnected) (favoriteList.querySelector("button") || favoriteList.nextElementSibling).focus();
      });
      item.append(remove);
      favoriteList.append(item);
    }
    favoriteStatus.textContent = favoriteList.children.length ? "" : "В избранном пока нет товаров.";
    favoriteStatus.tabIndex = -1;
  }

  favoriteButton?.addEventListener("click", () => {
    const id = favoriteButton.dataset.favorite;
    changeFavorite(id, !readFavorites().has(id));
  });
  window.addEventListener("storage", event => {
    if (event.key === favoriteKey || event.key === null) renderFavorites();
  });
  renderFavorites();
}
