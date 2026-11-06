function initializeWorkspace() {
  const login = document.querySelector("[data-staff-login]");
  if (login && /^#LS-(?:[0-9]{6}|[A-F0-9]{12})$/.test(location.hash)) {
    const url = new URL(login.href);
    if (url.searchParams.get("return") === "/manager/orders/") {
      url.searchParams.set("return", "/manager/orders/" + location.hash);
      login.href = url.href;
    }
  }

  const main = document.querySelector("#staff-main");
  const nav = document.querySelector(".staff-section-nav");
  if (!main || !nav) return;

  const sidebar = nav.closest(".staff-sidebar");
  const profile = sidebar.querySelector(".staff-profile")?.outerHTML;
  const slot = sidebar.querySelector(".staff-team-slot");
  const links = [...nav.querySelectorAll("a")];
  const sectionPaths = new Set(links.map(link => new URL(link.href).pathname));
  const pageKey = url => url.pathname + url.search;
  let currentPage = pageKey(location);
  let pageListeners = new AbortController();
  let request;
  let teamOpen = !matchMedia("(max-width: 53rem)").matches;
  const initialTeam = slot.querySelector("#staff-team-summary");
  if (initialTeam) initialTeam.open = teamOpen;

  function updateTeam(fresh) {
    const team = slot.querySelector("#staff-team-summary");
    if (team) teamOpen = team.open;
    if (team && fresh) {
      team.replaceChildren(...fresh.children);
    } else {
      slot.replaceChildren();
      if (fresh) {
        fresh.open = teamOpen;
        slot.append(fresh);
      }
    }
  }

  async function navigate(url, fromHistory) {
    request?.abort();
    request = null;
    if (pageKey(url) === currentPage && (fromHistory || url.href === location.href)) {
      main.removeAttribute("aria-busy");
      return;
    }

    const pending = new AbortController();
    request = pending;
    main.setAttribute("aria-busy", "true");
    try {
      const response = await fetch(url, {signal: pending.signal});
      if (!response.ok || response.redirected) throw new Error("Navigation requires a page load");
      const page = new DOMParser().parseFromString(await response.text(), "text/html");
      if (pending.signal.aborted) return;
      const incoming = page.querySelector("#staff-main");
      const incomingNav = [...page.querySelectorAll(".staff-section-nav a")];
      if (!incoming || profile !== page.querySelector(".staff-profile")?.outerHTML ||
          links.length !== incomingNav.length ||
          links.some((link, index) => link.getAttribute("href") !== incomingNav[index].getAttribute("href"))) {
        throw new Error("The staff session changed");
      }

      if (!fromHistory) history.pushState(null, "", url);
      currentPage = pageKey(url);
      pageListeners.abort();
      pageListeners = new AbortController();
      main.removeAttribute("data-autosave");
      main.replaceChildren(...incoming.childNodes);
      updateTeam(page.querySelector("#staff-team-summary"));
      links.forEach((link, index) => {
        if (incomingNav[index].hasAttribute("aria-current")) link.setAttribute("aria-current", "page");
        else link.removeAttribute("aria-current");
      });
      document.title = page.title;
      window.scrollTo(0, 0);
      main.focus({preventScroll: true});
      if (typeof main.animate === "function" && !matchMedia("(prefers-reduced-motion: reduce)").matches) {
        main.getAnimations().forEach(animation => animation.cancel());
        main.animate([{opacity: .84}, {opacity: 1}], {duration: 140, easing: "ease-out"});
      }
      initializeOrders(main, slot.querySelector("#staff-team-summary"), pageListeners.signal);
    } catch (error) {
      if (pending.signal.aborted) return;
      if (fromHistory) location.reload();
      else location.assign(url);
    } finally {
      if (request === pending) {
        main.removeAttribute("aria-busy");
        request = null;
      }
    }
  }

  document.addEventListener("click", event => {
    if (event.defaultPrevented || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    const link = event.target.closest(".staff-workspace a[href]");
    if (!link || link.target || link.hasAttribute("download")) return;
    const url = new URL(link.href);
    if (url.origin !== location.origin || !sectionPaths.has(url.pathname)) return;
    if (pageKey(url) === pageKey(location) && url.hash && url.hash !== location.hash) return;
    event.preventDefault();
    void navigate(url, false);
  });
  window.addEventListener("popstate", () => void navigate(new URL(location.href), true));
  initializeOrders(main, initialTeam, pageListeners.signal);
}

function initializeOrders(main, team, signal) {
  const search = main.querySelector("#staff-order-search");
  if (!search) return;

  const orders = [...main.querySelectorAll(".staff-order")];
  const toolbar = main.querySelector(".staff-filters");
  const filters = [...toolbar.querySelectorAll("[data-filter]")];
  const result = main.querySelector("#staff-result-count");
  const reset = main.querySelector("#staff-reset");
  const empty = main.querySelector("#staff-no-match");
  const feedback = main.querySelector("#staff-save-feedback");
  const dialog = main.querySelector("#staff-cancel");
  const drawer = main.querySelector("#staff-order-drawer");
  const drawerContent = drawer.querySelector(".staff-drawer-content");
  const drawerClose = drawer.querySelector("button");
  const drawerTitle = drawer.querySelector("h2");
  const overview = main.querySelector("#staff-overview");
  const digits = text => text.replace(/\D/g, "");
  let status = filters.find(button => button.getAttribute("aria-pressed") === "true").dataset.filter;
  let drawerOrder = null;

  if (overview) {
    const switcher = overview.querySelector(".staff-period-switch");
    const days = overview.querySelector("#staff-days");
    if (typeof days.showModal === "function") {
      for (const button of overview.querySelectorAll(".staff-days-button")) {
        button.hidden = false;
        button.addEventListener("click", () => {
          days.querySelector(".staff-days-scroll").scrollTop = 0;
          days.showModal();
        });
      }
    }
    switcher.hidden = false;
    switcher.addEventListener("click", event => {
      const choice = event.target.closest("[data-period]");
      if (!choice) return;
      for (const button of switcher.querySelectorAll("button")) {
        button.setAttribute("aria-pressed", String(button === choice));
      }
      for (const chart of overview.querySelectorAll("[data-chart-period]")) {
        chart.hidden = chart.dataset.chartPeriod !== choice.dataset.period;
      }
      for (const table of days.querySelectorAll("[data-days-period]")) {
        table.hidden = table.dataset.daysPeriod !== choice.dataset.period;
      }
    });
    overview.querySelector(".staff-find-link").addEventListener("click", event => {
      if (!search.closest(".staff-filter-tools").hidden) {
        event.preventDefault();
        search.focus();
      }
    });
  }

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
      const outsidePreview = overview && !status && !query && visible >= 4;
      order.hidden = Boolean(outsidePreview || (status && order.dataset.status !== status) || !matches);
      if (!order.hidden) visible += 1;
    }
    result.textContent = visible < orders.length ? `Показано: ${visible} из ${orders.length}` : `Всего заявок: ${orders.length}`;
    for (const button of filters) {
      button.setAttribute("aria-pressed", String(button.dataset.filter === status));
      button.querySelector("strong").textContent = button.dataset.filter ? counts.get(button.dataset.filter) ?? 0 : orders.length;
    }
    reset.hidden = !status && !query;
    if (empty) empty.hidden = visible > 0;
  }

  function presentOrder(order, notice) {
    const details = order.querySelector(".staff-order-details");
    if (notice) details.prepend(notice);
    order.open = true;
    if (typeof drawer.showModal !== "function") {
      order.scrollIntoView({block: "nearest"});
      return;
    }
    drawerOrder = order;
    drawerTitle.textContent = order.id;
    drawerContent.replaceChildren(details);
    drawer.scrollTop = 0;
    if (!drawer.open) drawer.showModal();
    else (details.querySelector("select[name=target]") ?? drawerClose).focus({preventScroll: true});
  }

  function closeOrder() {
    const order = drawerOrder;
    order.append(drawerContent.firstElementChild);
    order.open = false;
    drawerOrder = null;
    drawer.close();
    if (location.hash === "#" + order.id) history.replaceState(null, "", location.pathname + location.search);
    const focus = order.hidden ? toolbar.querySelector('[aria-pressed="true"]') : order.querySelector("summary");
    focus.focus({preventScroll: true});
  }

  function openLinkedOrder() {
    const order = document.getElementById(location.hash.slice(1));
    if (!order?.matches(".staff-order") || order === drawerOrder) return;
    if (drawerOrder) closeOrder();
    const notice = main.querySelector(":scope > .staff-notice:not(#staff-save-feedback)");
    presentOrder(order, notice);
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
    const order = form.closest(".staff-order") ?? drawerOrder;
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
      if (signal.aborted) return;
      const updated = page.getElementById(order.id);
      if (!response.redirected || !updated?.matches(".staff-order")) {
        throw new Error("Не удалось подтвердить сохранение. Обновите страницу.");
      }
      const inDrawer = order === drawerOrder;
      const restoreFocus = inDrawer || document.activeElement === document.body || order.contains(document.activeElement);
      updated.open = order.open;
      orders[orders.indexOf(order)] = updated;
      order.replaceWith(updated);
      for (const selector of [".staff-metrics", ".staff-inbox"]) {
        const current = main.querySelector(selector);
        const fresh = page.querySelector(selector);
        if (current && fresh) current.replaceWith(fresh);
      }
      const freshTeam = page.querySelector("#staff-team-summary");
      if (team && freshTeam) team.replaceChildren(...freshTeam.children);
      filterOrders();
      const notice = page.querySelector(".staff-notice");
      if (inDrawer) presentOrder(updated, notice);
      if (updated.hidden || !updated.open) {
        feedback.textContent = `${updated.id} · Статус сохранён`;
        feedback.hidden = false;
        if (restoreFocus && !inDrawer) toolbar.querySelector('[aria-pressed="true"]').focus();
      } else if (!inDrawer) {
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
    main.dataset.autosave = "true";
    main.addEventListener("change", event => {
      const picker = event.target;
      if (picker.matches(".staff-status-form select")) void saveStatus(picker.form);
    }, {signal});
    main.addEventListener("submit", event => {
      if (!event.target.matches(".staff-status-form")) return;
      event.preventDefault();
      void saveStatus(event.target);
    }, {signal});
  }

  if (typeof drawer.showModal === "function") {
    main.addEventListener("click", event => {
      const summary = event.target.closest(".staff-order-row");
      const queueLink = event.target.closest(".staff-queue a");
      if (queueLink && (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey)) return;
      const order = summary?.parentElement ?? (queueLink && document.getElementById(queueLink.hash.slice(1)));
      if (!order) return;
      event.preventDefault();
      presentOrder(order);
    }, {signal});
    drawerClose.addEventListener("click", closeOrder);
    let startedOnBackdrop = false;
    function onBackdrop(event) {
      if (event.target !== drawer) return false;
      const {left, top, right, bottom} = drawer.getBoundingClientRect();
      return event.clientX < left || event.clientX > right || event.clientY < top || event.clientY > bottom;
    }
    drawer.addEventListener("pointerdown", event => {
      startedOnBackdrop = onBackdrop(event);
    });
    drawer.addEventListener("click", event => {
      if (startedOnBackdrop && onBackdrop(event)) closeOrder();
      startedOnBackdrop = false;
    });
    drawer.addEventListener("cancel", event => {
      event.preventDefault();
      closeOrder();
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
  filterOrders();
  window.addEventListener("hashchange", openLinkedOrder, {signal});
  openLinkedOrder();
}

initializeWorkspace();
