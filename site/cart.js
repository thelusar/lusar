const cartKey = "lusar-cart";
const promoDialog = document.querySelector("#first-order-promo");
if (promoDialog) {
  const promoKey = "lusar-first-order-promo-hidden-until";
  const promoSeenKey = "lusar-first-order-promo-seen";
  const sevenDays = 7 * 24 * 60 * 60 * 1000;
  function hidePromotion() {
    try { localStorage.setItem(promoKey, String(Date.now() + sevenDays)); } catch {}
  }
  promoDialog.addEventListener("close", hidePromotion);
  promoDialog.querySelector("a").addEventListener("click", hidePromotion);
  setTimeout(() => {
    try {
      if (sessionStorage.getItem(promoSeenKey) || Number(localStorage.getItem(promoKey)) > Date.now()) return;
      if (document.hidden || document.querySelector("dialog[open]")) return;
      sessionStorage.setItem(promoSeenKey, "1");
      promoDialog.showModal();
    } catch {}
  }, 15000);
}

let cart = {};
try {
  const saved = JSON.parse(localStorage.getItem(cartKey));
  if (saved && typeof saved === "object" && !Array.isArray(saved)) cart = saved;
} catch {}

function save(next) {
  localStorage.setItem(cartKey, JSON.stringify(next));
  cart = next;
}

for (const add of document.querySelectorAll("[data-add]")) {
  add.addEventListener("click", () => {
    const id = add.dataset.add;
    const status = document.querySelector("#cart-status");
    try {
      const quantity = (Number.isSafeInteger(cart[id]) && cart[id] > 0 ? cart[id] : 0) + 1;
      save({ ...cart, [id]: quantity });
      window.lusarAnalytics?.added(id);
      status.textContent = `Товар в корзине. Количество: ${quantity}.`;
      document.querySelector("#cart-next").hidden = false;
    } catch {
      status.textContent = "Не удалось сохранить корзину в этом браузере.";
    }
  });
}

const shoppingFeedback = document.querySelector(".catalog-shopping-feedback");
if (shoppingFeedback) {
  let trigger;
  document.addEventListener("click", event => {
    const action = event.target.closest("[data-add], [data-favorite]");
    if (action) trigger = action;
  });
  shoppingFeedback.querySelector("[data-dismiss-shopping]").addEventListener("click", () => {
    for (const status of shoppingFeedback.querySelectorAll('[role="status"]')) status.textContent = "";
    shoppingFeedback.querySelector("#cart-next").hidden = true;
    if (trigger?.isConnected && !trigger.closest("li[hidden]")) trigger.focus();
  });
}

const items = document.querySelector("#cart-items");
if (items) renderCart();

function renderCart() {
  items.replaceChildren();
  const money = new Intl.NumberFormat("ru-RU");
  let subtotal = 0;
  let unpriced = false;
  let unavailable = false;
  for (const [id, quantity] of Object.entries(cart)) {
    if (!Number.isSafeInteger(quantity) || quantity < 1) continue;
    const product = Object.hasOwn(products, id) ? products[id] : null;
    const row = document.createElement("p");
    if (product) {
      const link = document.createElement("a");
      link.href = product.path;
      link.textContent = product.name;
      const label = document.createElement("label");
      label.textContent = "Количество ";
      const field = document.createElement("input");
      field.type = "number";
      field.min = "1";
      field.max = "999";
      field.value = String(quantity);
      field.setAttribute("aria-label", `Количество: ${product.name}`);
      field.addEventListener("change", () => {
        if (!field.checkValidity() || !Number.isInteger(field.valueAsNumber)) {
          field.value = String(quantity);
          return;
        }
        try {
          save({ ...cart, [id]: field.valueAsNumber });
          renderCart();
        } catch {
          field.value = String(quantity);
          row.append(" Не удалось изменить количество.");
        }
      });
      label.append(field);
      row.append(link, " · ", label, " · ");
      if (product.price === null) {
        unpriced = true;
        row.append("Цена по запросу ");
      } else {
        subtotal += product.price * quantity;
        row.append(money.format(product.price * quantity) + " ֏ ");
      }
    } else {
      unavailable = true;
      row.append("Товар снят с публикации или сейчас недоступен. ");
    }
    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = "Удалить";
    remove.setAttribute("aria-label", product ? `Удалить из корзины: ${product.name}` : "Удалить недоступный товар");
    remove.addEventListener("click", () => {
      const next = { ...cart };
      delete next[id];
      try {
        save(next);
        renderCart();
      } catch {
        row.append(" Не удалось обновить корзину.");
      }
    });
    row.append(remove);
    items.append(row);
  }
  if (!items.childElementCount) items.textContent = "Корзина пока пуста.";
  document.querySelector("#cart-summary").textContent = unavailable ? "Уберите недоступные товары, чтобы оформить заявку."
    : unpriced ? "Итоговую сумму подтвердит менеджер."
    : items.childElementCount ? `Сумма товаров до скидок: ${money.format(subtotal)} ֏.` : "";
  for (const selector of ["#checkout-link", "#checkout"]) {
    const control = document.querySelector(selector);
    if (control) control.hidden = unavailable || !items.querySelector("a");
  }
  updatePromoTotal();
}

function updatePromoTotal() {
  const output = document.querySelector("#promo-total");
  if (!output) return;
  const code = document.querySelector("[name=promo]").value.trim().toUpperCase();
  const lines = Object.entries(cart).filter(([id, count]) => Object.hasOwn(products, id) && Number.isSafeInteger(count) && count > 0);
  if (!lines.length || lines.some(([id]) => products[id].price === null)) {
    output.textContent = "Итоговую сумму подтвердит менеджер.";
    return;
  }
  const subtotal = lines.reduce((sum, [id, count]) => sum + products[id].price * count, 0);
  const valid = !code || Object.hasOwn(promotions, code);
  const nominal = valid && code ? promotions[code] : 0;
  const discount = nominal === "10%" ? Math.floor(subtotal / 10) : Math.min(nominal, Math.floor(subtotal / 5));
  const format = amount => new Intl.NumberFormat("ru-RU").format(amount) + " ֏";
  output.textContent = valid
    ? `Скидка: ${format(discount)}. Предварительный итог: ${format(subtotal - discount)}.`
    : "Промокод не найден.";
}

const checkout = document.querySelector("#checkout");
checkout?.querySelector("[name=promo]").addEventListener("input", updatePromoTotal);
let request;
checkout?.addEventListener("submit", async event => {
  event.preventDefault();
  const status = document.querySelector("#checkout-status");
  const submit = checkout.querySelector("button");
  submit.disabled = true;
  try {
    const displayedPrices = Object.fromEntries(
      Object.keys(cart).filter(id => Object.hasOwn(products, id)).map(id => [id, products[id].price])
    );
    const payload = { ...Object.fromEntries(new FormData(checkout)), cart, displayedPrices };
    const signature = JSON.stringify(payload);
    if (request?.signature !== signature) request = { signature, id: crypto.randomUUID() };
    const response = await fetch("/api/orders", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...payload, requestId: request.id })
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error);
    checkout.hidden = true;
    items.hidden = true;
    document.querySelector("#cart-summary").hidden = true;
    status.textContent = `Заявка №${result.number} получена. Менеджер свяжется с вами в ближайшее время. Часы связи ${serviceHours}.`;
    if (result.trackingToken) {
      const trackingLink = document.querySelector("#order-status-link");
      trackingLink.href = "/order-status#" + new URLSearchParams({ number: result.number, key: result.trackingToken });
      trackingLink.hidden = false;
    }
    try { save({}); } catch {}
    try {
      sessionStorage.setItem("lusar-order-receipt", JSON.stringify({
        number: result.number, trackingToken: result.trackingToken,
        leadPending: response.status === 201 && document.documentElement.dataset.analyticsConsent === "granted"
      }));
      location.replace("/checkout/received");
    } catch {
      if (response.status === 201) window.lusarAnalytics?.submitted();
    }
  } catch (error) {
    status.textContent = error.message || "Не удалось отправить заявку. Попробуйте ещё раз.";
    submit.disabled = false;
  }
});
