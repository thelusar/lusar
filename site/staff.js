(() => {
  const search = document.querySelector("#staff-order-search");
  if (!search) return;

  const orders = [...document.querySelectorAll(".staff-order")];
  const filters = [...document.querySelectorAll(".staff-stats [data-filter]")];
  const result = document.querySelector("#staff-result-count");
  const reset = document.querySelector("#staff-reset");
  const empty = document.querySelector("#staff-no-match");
  const digits = text => text.replace(/\D/g, "");
  let status = "";

  function filterOrders() {
    const query = search.value.trim().toLowerCase();
    const phoneQuery = /^[\d+\s().-]+$/.test(query) ? digits(query) : "";
    let visible = 0;
    for (const order of orders) {
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
    const notice = document.querySelector(".staff-notice");
    if (notice) order.querySelector(".staff-order-details").prepend(notice);
    order.scrollIntoView({block: "start"});
  }

  for (const button of filters) {
    button.addEventListener("click", () => {
      status = status === button.dataset.filter ? "" : button.dataset.filter;
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
  document.querySelector(".staff-stats").hidden = false;
  window.addEventListener("hashchange", openLinkedOrder);
  openLinkedOrder();
})();
