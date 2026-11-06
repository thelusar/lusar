const favoriteKey = "lusar-favorites";
const favoriteButtons = [...document.querySelectorAll("[data-favorite]")];
const favoriteList = document.querySelector("#favorite-items");
const favoriteStatus = document.querySelector("#favorite-status");
const wishlistEmpty = document.querySelector("#wishlist-empty");

if (favoriteButtons.length || favoriteList) {
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
      document.dispatchEvent(new Event('lusar-shopping-change'));
    } catch {
      favoriteStatus.textContent = "Не удалось обновить избранное в этом браузере.";
      return;
    }
    renderFavorites();
    favoriteStatus.textContent = saved ? "Товар добавлен в избранное." : "Товар удалён из избранного.";
  }

  function renderFavorites() {
    const favorites = readFavorites();
    for (const button of favoriteButtons) button.setAttribute("aria-pressed", String(favorites.has(button.dataset.favorite)));
    if (!favoriteList) return;
    favoriteList.replaceChildren();
    for (const id of favorites) {
      const item = element("li", "wishlist-item");
      const product = Object.hasOwn(products, id) ? products[id] : null;
      const body = element("div", "wishlist-item-body");
      const actions = element("div", "wishlist-item-actions");
      if (product) {
        const picture = element("a", "wishlist-photo");
        picture.href = product.path;
        picture.tabIndex = -1;
        picture.setAttribute("aria-hidden", "true");
        if (product.image) {
          const image = element("img");
          image.src = product.image;
          image.alt = "";
          image.loading = "lazy";
          picture.append(image);
        }
        item.append(picture);
        const title = element("a", "wishlist-title", product.name);
        title.href = product.path;
        title.dataset.localeSource = "";
        body.append(title);
        if (product.sku) body.append(element("p", "wishlist-sku", "Артикул " + product.sku));
        body.append(element("p", "wishlist-price", product.price === null ? "Цена по запросу" : formatMoney(product.price)));
        const add = element("button", "primary-action", "В корзину");
        add.type = "button";
        add.dataset.add = id;
        actions.append(add);
      } else {
        body.append(element("p", "", "Товар сейчас недоступен."));
      }
      const remove = element("button", "text-button wishlist-remove", "Убрать из избранного");
      remove.type = "button";
      if (product) {
        const title = body.querySelector("a");
        title.id = "wishlist-product-" + id;
        remove.setAttribute("aria-describedby", title.id);
        actions.querySelector("[data-add]").setAttribute("aria-describedby", title.id);
      }
      remove.addEventListener("click", () => {
        changeFavorite(id, false);
        if (!item.isConnected) (favoriteList.querySelector(".wishlist-remove") || wishlistEmpty.querySelector("a")).focus();
      });
      actions.append(remove);
      body.append(actions);
      item.append(body);
      favoriteList.append(item);
    }
    wishlistEmpty.hidden = !!favoriteList.children.length;
    favoriteStatus.textContent = "";
  }

  for (const button of favoriteButtons) button.addEventListener("click", () => {
    const id = button.dataset.favorite;
    changeFavorite(id, !readFavorites().has(id));
  });
  window.addEventListener("storage", event => {
    if (event.key === favoriteKey || event.key === null) renderFavorites();
  });
  renderFavorites();
}
