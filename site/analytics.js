(() => {
  const names = new Set(["view_item", "add_to_cart", "begin_checkout", "generate_lead"]);
  const root = document.documentElement;
  const googleId = root.dataset.googleAnalytics;
  const metricaId = Number(root.dataset.yandexMetrica || 0);
  const pageUrl = location.origin + location.pathname;
  let providersStarted = false;
  let googleLoaded = false;
  let metricaLoaded = false;
  let viewed = false;
  let started = false;
  let submitted = false;

  function loadScript(url) {
    const script = document.createElement("script");
    script.async = true;
    script.src = url;
    document.head.append(script);
  }

  function enableProviders() {
    if (providersStarted || (!googleId && !metricaId)) return;
    providersStarted = true;
    if (googleId) {
      window[`ga-disable-${googleId}`] = false;
      if (!googleLoaded) {
        googleLoaded = true;
        window.dataLayer = window.dataLayer || [];
        window.gtag = function () { window.dataLayer.push(arguments); };
        window.gtag("js", new Date());
        window.gtag("consent", "default", { analytics_storage: "granted", ad_storage: "denied",
          ad_user_data: "denied", ad_personalization: "denied" });
        window.gtag("config", googleId, { send_page_view: false, allow_google_signals: false,
          allow_ad_personalization_signals: false, page_location: pageUrl });
        loadScript("https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(googleId));
      } else {
        window.gtag("consent", "update", { analytics_storage: "granted" });
      }
      window.gtag("event", "page_view", { page_location: pageUrl });
    }
    if (metricaId) {
      if (!metricaLoaded) {
        metricaLoaded = true;
        window.ym = function () { (window.ym.a = window.ym.a || []).push(arguments); };
        window.ym.l = Date.now();
        loadScript("https://mc.yandex.ru/metrika/tag.js");
      }
      window.ym(metricaId, "init", { defer: true, webvisor: false, clickmap: false, trackLinks: false });
      window.ym(metricaId, "hit", pageUrl);
    }
  }

  function disableProviders() {
    if (!providersStarted) return;
    providersStarted = false;
    if (googleId) {
      window[`ga-disable-${googleId}`] = true;
      window.gtag("consent", "update", { analytics_storage: "denied" });
    }
    if (metricaId) window.ym(metricaId, "destruct");
  }

  function track(name, productId) {
    if (!names.has(name) || root.dataset.analyticsConsent !== "granted") return;
    const detail = { name };
    if ((name === "view_item" || name === "add_to_cart") &&
        typeof productId === "string" && /^[a-zA-Z0-9][a-zA-Z0-9_-]{0,127}$/.test(productId)) {
      detail.productId = productId;
    }
    window.dispatchEvent(new CustomEvent("lusar:analytics", { detail }));
    if (!providersStarted) return;
    if (googleId) window.gtag("event", name, detail.productId ? { items: [{ item_id: detail.productId }] } : {});
    if (metricaId) window.ym(metricaId, "reachGoal", name, detail.productId ? { product_id: detail.productId } : {});
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
    if (!event.detail.granted) return disableProviders();
    enableProviders();
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
