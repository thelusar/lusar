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

function readCart() {
  try {
    const saved = JSON.parse(localStorage.getItem(cartKey));
    if (saved && typeof saved === "object" && !Array.isArray(saved)) return saved;
  } catch {}
  return {};
}
let cart = readCart();

const continueLinks = document.querySelectorAll("[data-continue-shopping]");
if (continueLinks.length) {
  function shoppingPath(value) {
    if (!value) return "";
    try {
      const url = new URL(value, location.origin);
      const browsingPage = /^\/(?:catalog(?:\/.*)?|search|favorites|compare)\/?$/.test(url.pathname);
      return url.origin === location.origin && browsingPage ? url.pathname + url.search + url.hash : "";
    } catch {
      return "";
    }
  }
  let previous = shoppingPath(document.referrer);
  try {
    if (previous) sessionStorage.setItem("lusar-shopping-return", previous);
    else previous = shoppingPath(sessionStorage.getItem("lusar-shopping-return"));
  } catch {}
  if (previous) for (const link of continueLinks) link.href = previous;
  if (previous && new URL(previous, location.origin).pathname === "/favorites") {
    for (const link of document.querySelectorAll(".cart-return-links a[href='/favorites'], .empty-state-actions a[href='/favorites']")) link.hidden = true;
  }
}

function save(next) {
  localStorage.setItem(cartKey, JSON.stringify(next));
  cart = next;
  document.dispatchEvent(new Event('lusar-shopping-change'));
}

document.addEventListener("click", event => {
  const add = event.target.closest("[data-add]");
  if (!add) return;
  const id = add.dataset.add;
  const status = document.querySelector("#cart-status");
  try {
    const quantity = (Number.isSafeInteger(cart[id]) && cart[id] > 0 ? cart[id] : 0) + 1;
    if (quantity > 999) { status.textContent = "Максимальное количество — 999."; return; }
    save({ ...cart, [id]: quantity });
    window.lusarAnalytics?.added(id);
    status.textContent = `Товар в корзине. Количество: ${quantity}.`;
    document.querySelector("#cart-next").hidden = false;
  } catch {
    status.textContent = "Не удалось сохранить корзину в этом браузере.";
  }
});

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

const checkout = document.querySelector("#checkout");
const review = document.querySelector(".checkout-review");
if (review && matchMedia("(max-width: 40rem)").matches) review.open = false;
const promoField = document.querySelector("[name=promo]");
let submitting = false;
if (promoField) {
  try { promoField.value = sessionStorage.getItem("lusar-promo") || ""; } catch {}
  if (promoField.value) promoField.closest("details").open = true;
  promoField.addEventListener("input", () => {
    try { sessionStorage.setItem("lusar-promo", promoField.value.trim().toUpperCase()); } catch {}
    updatePromoTotal();
  });
}
const items = document.querySelector("#cart-items");

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
const formatMoney = amount => new Intl.NumberFormat("ru-RU").format(amount) + " ֏";
if (items) renderCart();
function cartLines() {
  return Object.entries(cart).filter(([,count]) => Number.isSafeInteger(count) && count > 0);
}
function cartMessage(text) {
  const status = document.querySelector("#cart-message");
  if (status) status.textContent = text;
}
function changeQuantity(id, quantity, focus) {
  if (submitting || !Number.isSafeInteger(quantity) || quantity < 1 || quantity > 999) return;
  try {
    save({...cart, [id]:quantity});
    renderCart();
    const row = items.querySelector(`[data-cart-row="${CSS.escape(id)}"]`);
    const target = row.querySelector(focus);
    (target && !target.disabled ? target : row.querySelector("input")).focus({preventScroll:true});
    cartMessage("");
  } catch { cartMessage("Не удалось изменить количество."); }
}
function renderCart() {
  items.replaceChildren();
  const lines = cartLines();
  for (const [id, quantity] of lines) {
    const product = Object.hasOwn(products, id) ? products[id] : null;
    const row = element("article", "cart-row" + (product ? "" : " cart-row-unavailable"));
    row.dataset.cartRow = id;
    const titleId = "cart-product-" + id;
    row.setAttribute("aria-labelledby", titleId);
    const picture = element(product ? "a" : "span", "cart-row-photo");
    let controls;
    if (product) {
      picture.href = product.path; picture.tabIndex = -1; picture.setAttribute("aria-hidden", "true");
      if (product.image) {
        const image = element("img"); image.src = product.image; image.alt = ""; image.loading = "lazy"; image.width = image.height = 160;
        picture.append(image);
      }
    } else picture.textContent = "—";
    const info = element("div", "cart-row-info");
    const heading = element("h2");
    const title = element(product ? "a" : "span", "", product ? product.name : "Товар сейчас недоступен.");
    title.id = titleId;
    if (product) { title.href = product.path; title.dataset.localeSource = ""; }
    heading.append(title); info.append(heading);
    if (product) {
      info.append(element("p", "cart-row-sku", "Артикул " + product.sku));
      const unit = element("p", "cart-unit-price");
      unit.append(element("span", "", "Цена за штуку"), " · ", element("span", "", product.price === null ? "Цена по запросу" : formatMoney(product.price)));
      info.append(unit);
      controls = element("div", "quantity-stepper");
      controls.setAttribute("role", "group"); controls.setAttribute("aria-label", "Количество"); controls.setAttribute("aria-describedby", titleId);
      const minus = element("button", "", "−"); minus.type = "button"; minus.dataset.quantityStep = "minus";
      minus.setAttribute("aria-label", "Уменьшить количество"); minus.disabled = quantity <= 1;
      const field = element("input"); field.type = "number"; field.min = "1"; field.max = "999"; field.step = "1"; field.value = String(quantity); field.inputMode = "numeric";
      field.setAttribute("aria-label", "Количество"); field.setAttribute("aria-describedby", titleId);
      const plus = element("button", "", "+"); plus.type = "button"; plus.dataset.quantityStep = "plus";
      plus.setAttribute("aria-label", "Увеличить количество"); plus.disabled = quantity >= 999;
      minus.addEventListener("click", () => changeQuantity(id, quantity - 1, '[data-quantity-step="minus"]'));
      plus.addEventListener("click", () => changeQuantity(id, quantity + 1, '[data-quantity-step="plus"]'));
      field.addEventListener("change", () => {
        if (!field.checkValidity() || !Number.isInteger(field.valueAsNumber)) { field.value = String(quantity); return; }
        changeQuantity(id, field.valueAsNumber, "input");
      });
      controls.append(minus,field,plus);
    } else info.append(element("p", "cart-row-warning", "Товар снят с публикации или сейчас недоступен."));
    const actions = element("div", "cart-row-end");
    if (product) actions.append(element("p", "cart-line-total", product.price === null ? "Цена по запросу" : formatMoney(product.price * quantity)));
    const remove = element("button", "cart-remove text-button", "Удалить"); remove.type = "button"; remove.dataset.remove = id;
    remove.setAttribute("aria-label", "Удалить из корзины"); remove.setAttribute("aria-describedby", titleId);
    if (!product) remove.setAttribute("aria-label", "Удалить недоступный товар");
    remove.addEventListener("click", () => {
      if (submitting) return;
      const next = {...cart}; delete next[id];
      try {
        save(next); renderCart(); cartMessage("");
        (items.querySelector("h2 a, [data-remove]") || document.querySelector("#cart-empty a")).focus();
      } catch { cartMessage("Не удалось обновить корзину."); }
    });
    actions.append(remove); row.append(picture,info);
    if (controls) row.append(controls);
    row.append(actions); items.append(row);
  }
  const unavailable = lines.some(([id]) => !Object.hasOwn(products, id));
  if (review && unavailable) review.open = true;
  document.querySelector("#order-flow").hidden = !lines.length;
  document.querySelector(".order-steps").hidden = !lines.length;
  document.querySelector("#cart-empty").hidden = !!lines.length;
  const count = document.querySelector("#cart-count"); if (count) count.textContent = lines.length ? `Товаров: ${lines.reduce((sum, [,quantity]) => sum + quantity, 0)}` : "";
  const link = document.querySelector("#checkout-link"); if (link) link.hidden = unavailable || !lines.length;
  if (checkout) checkout.hidden = unavailable || !lines.length;
  updatePromoTotal();
}

function updatePromoTotal() {
  if (!promoField) return true;
  const lines = cartLines();
  const unavailable = lines.some(([id]) => !Object.hasOwn(products,id));
  const unpriced = lines.some(([id]) => Object.hasOwn(products,id) && products[id].price === null);
  const priced = !unavailable && !unpriced;
  const subtotal = priced ? lines.reduce((sum,[id,count]) => sum + products[id].price * count, 0) : 0;
  const code = promoField.value.trim().toUpperCase();
  const account=window.lusarAccount?.value;
  const mode=document.querySelector('#discount-mode')?.value||'none';
  const first=account?.authenticated && mode==='first' && priced;
  const accountPercent=account?.authenticated && mode==='loyalty' ? account.loyalty.discountPercent : 0;
  const accountDiscount=priced?Math.floor(subtotal*accountPercent/100):0;
  const firstDiscount=first?Math.floor(subtotal/10):0;
  const valid = first || !code || Object.hasOwn(promotions,code);
  const nominal = valid && code && priced && !first ? promotions[code] : 0;
  const afterAccount=subtotal-accountDiscount;
  const discount = nominal === "10%" ? Math.floor(afterAccount / 10) : Math.min(nominal,Math.floor(afterAccount / 5));
  document.querySelector('#order-account-discount').textContent='−'+formatMoney(accountDiscount);
  document.querySelector('#order-account-discount-row').hidden=!accountDiscount;
  document.querySelector('#order-first-discount').textContent='−'+formatMoney(firstDiscount);
  document.querySelector('#order-first-discount-row').hidden=!firstDiscount;
  document.querySelector("#order-subtotal").textContent = priced ? formatMoney(subtotal) : "—";
  document.querySelector("#order-total").textContent = priced ? formatMoney(subtotal - discount-accountDiscount-firstDiscount) : "Цена по запросу";
  document.querySelector("#order-discount").textContent = "−" + formatMoney(discount);
  document.querySelector("#order-discount-row").hidden = !discount;
  document.querySelector("#cart-summary").textContent = unavailable ? "Уберите недоступные товары, чтобы оформить заявку." : "";
  const promoStatus = document.querySelector("#promo-total");
  promoStatus.textContent = unpriced ? "Менеджер подтвердит цену и скидку по этой заявке." : !valid ? "Промокод не найден." : first ? "Скидка на первый заказ применяется отдельно." : code ? "Промокод применён." : "";
  promoField.disabled = submitting || unpriced || unavailable || first;
  promoField.setAttribute("aria-invalid", String(priced && !valid));
  promoField.setCustomValidity(priced && !valid ? (window.lusarLocale?.text("Промокод не найден.") || "Промокод не найден.") : "");
  const submit = document.querySelector("#checkout-submit"); if (submit) submit.disabled = submitting || unavailable || !lines.length || !!window.lusarAccount?.value.loading;
  const modeField=document.querySelector('#discount-mode');if(modeField)modeField.disabled=submitting||unpriced||unavailable;
  return !priced || valid;
}

window.addEventListener("storage", event => {
  if (submitting || !items || (event.key !== cartKey && event.key !== null)) return;
  cart = readCart(); renderCart();
});
if (items) window.lusarCartRefresh = data => {
  if (submitting) return false;
  const current = {};
  for (const product of data.products) {
    current[product.id] = {name:product.name, price:product.price, sku:product.sku, attributes:product.attributes,
      path:"/catalog/product/" + encodeURIComponent(product.id),
      image:product.images[Math.min(1, product.images.length - 1)]?.url || ""};
  }
  for (const id of Object.keys(products)) delete products[id];
  Object.assign(products,current);
  cart = readCart(); renderCart();
  cartMessage("Каталог обновлён. Проверьте состав и сумму заявки.");
  return true;
};
document.addEventListener("lusar-language-change", () => { if (items) updatePromoTotal(); });
function accountCheckout(){
  const data=window.lusarAccount?.value, panel=document.querySelector('#account-checkout-benefits');
  if(!panel||!checkout)return;
  panel.hidden=!data?.authenticated;
  const signIn=document.querySelector('#checkout-sign-in');if(signIn)signIn.hidden=!data?.available||!!data?.authenticated;
  if(!data?.authenticated){document.querySelector('#discount-mode').value='none';updatePromoTotal();return;}
  const mode=document.querySelector('#discount-mode'), first=mode.querySelector('[value="first"]');
  first.disabled=!data.loyalty.firstOrderAvailable;
  if(!mode.dataset.chosen){mode.value=data.loyalty.firstOrderAvailable&&!promoField.value?'first':'loyalty';mode.dataset.chosen='true';}
  if(mode.value==='first'&&!data.loyalty.firstOrderAvailable)mode.value='loyalty';
  document.querySelector('#account-checkout-level').textContent=window.lusarLocale?.text('Ваша скидка')+' · '+data.loyalty.discountPercent+'%';
  document.querySelector('#checkout-account-mode').textContent='Из личного кабинета';
  for(const key of ['name','phone','email','address'])if(!checkout.elements[key].value)checkout.elements[key].value=data.profile[key]||'';
  updatePromoTotal();
}
document.querySelector('#discount-mode')?.addEventListener('change',event=>{event.target.dataset.chosen='true';updatePromoTotal();});
document.addEventListener('lusar-account-change',accountCheckout);
document.addEventListener('lusar-account-error',event=>{if(items)cartMessage(event.detail);});
accountCheckout();

const shoppingReady = document.querySelector("#shopping-ready");
if (shoppingReady) {
  const loading = document.querySelector("#shopping-loading");
  loading.hidden = false;
  function reveal() {
    loading.hidden = true;
    shoppingReady.hidden = false;
  }
  document.addEventListener("DOMContentLoaded", () => {
    if (window.lusarAccount?.value.loading) document.addEventListener("lusar-account-change", reveal, {once:true});
    else reveal();
  }, {once:true});
}

let request;
checkout?.addEventListener("submit", async event => {
  event.preventDefault();
  if (submitting || window.lusarAccount?.value.loading || !updatePromoTotal()) return;
  const status = document.querySelector("#checkout-status");
  const submit = document.querySelector("#checkout-submit");
  const fields = Object.fromEntries(new FormData(checkout));
  if(!window.lusarAccount?.value.authenticated)fields.discountMode='none';
  fields.name = fields.name.trim(); fields.phone = fields.phone.trim();
  if (!fields.name || !/^[+0-9() .-]+$/.test(fields.phone) || fields.phone.replace(/\D/g, "").length < 7 || fields.phone.replace(/\D/g, "").length > 15) {
    status.textContent = "Проверьте имя и номер телефона."; status.focus(); return;
  }
  const displayedPrices = Object.fromEntries(Object.keys(cart).filter(id => Object.hasOwn(products,id)).map(id => [id,products[id].price]));
  const payload = {...fields, cart:{...cart}, displayedPrices, numberFormat:"short"};
  const signature = JSON.stringify(payload);
  if (request?.signature !== signature) request = {signature, id:crypto.randomUUID()};
  submitting = true; checkout.setAttribute("aria-busy", "true");
  status.classList.add("visually-hidden"); status.textContent = "Отправляем заявку…";
  const controls = [...document.querySelectorAll("#checkout input, #cart-items button, #cart-items input, #order-promo, #discount-mode, #checkout-submit")].map(control => [control,control.disabled]);
  for (const [control] of controls) control.disabled = true;
  submit.textContent = "Отправляем заявку…";
  try {
    const response = await fetch("/api/orders", {method:"POST", headers:{"Content-Type":"application/json",...(window.lusarAccount?.value.authenticated?{'X-Lusar-CSRF':window.lusarAccount.value.csrfToken}:{})}, body:JSON.stringify({...payload,requestId:request.id})});
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.error || "Не удалось отправить заявку. Попробуйте ещё раз.");
    if (!/^LS-(?:[0-9]{6}|[A-F0-9]{12})$/.test(result.number)) throw new Error("Не удалось отправить заявку. Попробуйте ещё раз.");
    // Leave items added in another tab while this request was in flight.
    const remaining = readCart();
    for (const [id,count] of Object.entries(payload.cart)) {
      if (Number.isSafeInteger(remaining[id]) && remaining[id] > count) remaining[id] -= count;
      else delete remaining[id];
    }
    try { save(remaining); } catch {}
    try {
      sessionStorage.removeItem("lusar-promo");
      sessionStorage.setItem("lusar-order-receipt",JSON.stringify({number:result.number,trackingToken:result.trackingToken,
        leadPending:response.status === 201 && document.documentElement.dataset.analyticsConsent === "granted"}));
      location.replace("/checkout/received");
    } catch {
      if (response.status === 201) window.lusarAnalytics?.submitted();
      document.querySelector("#order-flow").hidden = true;
      document.querySelector("#checkout-success").hidden = false;
      document.querySelector("#checkout-success-number").textContent = `Заявка №${result.number} получена.`;
      status.textContent = "";
      const trackingLink = document.querySelector("#order-status-link");
      if (typeof result.trackingToken === "string" && /^[A-Za-z0-9_-]{43}$/.test(result.trackingToken)) {
        trackingLink.href = "/order-status#" + new URLSearchParams({number:result.number,key:result.trackingToken});
        trackingLink.hidden = false;
      }
      const heading = document.querySelector("#checkout-success h2"); heading.tabIndex = -1; heading.focus();
    }
  } catch (error) {
    status.classList.remove("visually-hidden");
    status.textContent = error instanceof TypeError ? "Не удалось отправить заявку. Попробуйте ещё раз." : error.message;
    submitting = false; checkout.removeAttribute("aria-busy");
    for (const [control,disabled] of controls) control.disabled = disabled;
    submit.textContent = "Отправить заявку"; status.focus();
  }
});
