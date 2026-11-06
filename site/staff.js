(() => {
  const login = document.querySelector("[data-staff-login]");
  if (login && /^#LS-(?:[0-9]{6}|[A-F0-9]{12})$/.test(location.hash)) {
    const url = new URL(login.href);
    if (url.searchParams.get("return") === "/manager/orders/") {
      url.searchParams.set("return", "/manager/orders/" + location.hash);
      login.href = url.href;
    }
  }
  const search = document.querySelector("#staff-order-search");
  if (!search) return;

  const orders = [...document.querySelectorAll(".staff-order")];
  const toolbar = document.querySelector(".staff-filters");
  const filters = [...toolbar.querySelectorAll("[data-filter]")];
  const result = document.querySelector("#staff-result-count");
  const reset = document.querySelector("#staff-reset");
  const empty = document.querySelector("#staff-no-match");
  const feedback = document.querySelector("#staff-save-feedback");
  const dialog = document.querySelector("#staff-cancel");
  const digits = text => text.replace(/\D/g, "");
  let status = "";

  function filterOrders() {
    const query = search.value.trim().toLowerCase();
    const phoneQuery = /^[\d+\s().-]+$/.test(query) ? digits(query) : "";
    const counts = new Map();
    let visible = 0;
    for (const order of orders) {
      counts.set(order.dataset.status, (counts.get(order.dataset.status) ?? 0) + 1);
      const customer = order.querySelector(".staff-order-customer");
      const matches = order.id.toLowerCase().includes(query) ||
        customer.textContent.toLowerCase().includes(query) ||
        (phoneQuery && digits(customer.querySelector("small").textContent).includes(phoneQuery));
      order.hidden = Boolean((status && order.dataset.status !== status) || !matches);
      if (!order.hidden) visible += 1;
    }
    result.textContent = status || query ? `Показано: ${visible} из ${orders.length}` : `Всего заявок: ${orders.length}`;
    for (const button of filters) {
      button.setAttribute("aria-pressed", String(button.dataset.filter === status));
      button.querySelector("strong").textContent = button.dataset.filter ? counts.get(button.dataset.filter) ?? 0 : orders.length;
    }
    reset.hidden = !status && !query;
    if (empty) empty.hidden = visible > 0;
  }

  function openLinkedOrder() {
    const order = document.getElementById(location.hash.slice(1));
    if (!order?.matches(".staff-order")) return;
    if (order.hidden) {
      search.value = "";
      status = "";
      filterOrders();
    }
    order.open = true;
    const notice = document.querySelector(".staff-main > .staff-notice:not(#staff-save-feedback)");
    if (notice) order.querySelector(".staff-order-details").prepend(notice);
    order.scrollIntoView({block: "nearest"});
  }

  function confirmCancellation() {
    return new Promise(resolve => {
      const listeners = new AbortController();
      const finish = confirmed => {
        listeners.abort();
        dialog.close();
        resolve(confirmed);
      };
      dialog.addEventListener("submit", event => {
        event.preventDefault();
        finish(event.submitter?.value === "confirm");
      }, {signal: listeners.signal});
      dialog.addEventListener("cancel", event => {
        event.preventDefault();
        finish(false);
      }, {signal: listeners.signal});
      dialog.showModal();
    });
  }

  async function saveStatus(form) {
    const picker = form.elements.target;
    if (!picker.value || picker.disabled) return;
    const order = form.closest(".staff-order");
    const message = form.querySelector("[data-save-state]");
    const fields = new URLSearchParams(new FormData(form));
    picker.disabled = true;
    if (fields.get("target") === "cancelled" && !await confirmCancellation()) {
      picker.value = "";
      picker.disabled = false;
      picker.focus();
      return;
    }
    form.parentElement.querySelector(".staff-notice")?.remove();
    message.hidden = false;
    message.dataset.state = "saving";
    message.textContent = "Сохраняем…";
    feedback.hidden = true;
    try {
      const response = await fetch(form.action, {
        method: "POST",
        headers: {Accept: "application/json"},
        body: fields
      });
      if (!response.ok) {
        const problem = await response.json().catch(() => ({}));
        throw new Error(problem.error || "Не удалось сохранить статус. Обновите список и попробуйте снова.");
      }
      const page = new DOMParser().parseFromString(await response.text(), "text/html");
      const updated = page.getElementById(order.id);
      if (!response.redirected || !updated?.matches(".staff-order")) {
        throw new Error("Не удалось подтвердить сохранение. Обновите страницу.");
      }
      const restoreFocus = document.activeElement === document.body || order.contains(document.activeElement);
      updated.open = order.open;
      orders[orders.indexOf(order)] = updated;
      order.replaceWith(updated);
      filterOrders();
      const notice = page.querySelector(".staff-notice");
      if (updated.hidden || !updated.open) {
        feedback.textContent = `${updated.id} · Статус сохранён`;
        feedback.hidden = false;
        if (restoreFocus) toolbar.querySelector('[aria-pressed="true"]').focus();
      } else {
        if (notice) updated.querySelector(".staff-detail-header").append(notice);
        if (restoreFocus) (updated.querySelector("select[name=target]") ?? updated.querySelector("summary")).focus({preventScroll: true});
      }
    } catch (error) {
      picker.value = "";
      message.dataset.state = "error";
      message.textContent = error instanceof TypeError ? "Связь прервалась. Обновите страницу, чтобы проверить статус." : error.message;
    } finally {
      picker.disabled = false;
    }
  }

  if (typeof dialog?.showModal === "function") {
    document.body.dataset.autosave = "true";
    document.addEventListener("change", event => {
      const picker = event.target;
      if (picker.matches(".staff-status-form select")) void saveStatus(picker.form);
    });
    document.addEventListener("submit", event => {
      if (!event.target.matches(".staff-status-form")) return;
      event.preventDefault();
      void saveStatus(event.target);
    });
  }

  for (const button of filters) {
    button.addEventListener("click", () => {
      status = button.dataset.filter;
      filterOrders();
    });
  }
  search.addEventListener("input", filterOrders);
  reset.addEventListener("click", () => {
    search.value = "";
    status = "";
    filterOrders();
    search.focus();
  });
  if (orders.length) search.closest(".staff-filter-tools").hidden = false;
  toolbar.hidden = false;
  window.addEventListener("hashchange", openLinkedOrder);
  openLinkedOrder();
})();
