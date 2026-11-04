(() => {
  const names = new Set(["view_item", "add_to_cart", "begin_checkout", "generate_lead"]);
  const root = document.documentElement;
  let viewed = false;
  let started = false;
  let submitted = false;

  function track(name, productId) {
    if (!names.has(name) || root.dataset.analyticsConsent !== "granted") return;
    const detail = { name };
    if ((name === "view_item" || name === "add_to_cart") &&
        typeof productId === "string" && /^[a-zA-Z0-9][a-zA-Z0-9_-]{0,127}$/.test(productId)) {
      detail.productId = productId;
    }
    window.dispatchEvent(new CustomEvent("lusar:analytics", { detail }));
  }

  window.lusarAnalytics = {
    added(productId) {
      track("add_to_cart", productId);
    },
    submitted() {
      if (submitted) return;
      submitted = true;
      track("generate_lead");
    }
  };

  window.addEventListener("lusar:analytics-consent", event => {
    if (!event.detail.granted) return;
    const product = document.querySelector("[data-add]");
    if (product && !viewed) {
      viewed = true;
      track("view_item", product.dataset.add);
    }
    const checkout = document.querySelector("#checkout");
    if (checkout && !checkout.hidden && !started) {
      started = true;
      track("begin_checkout");
    }
  });
})();
