(() => {
  let version = document.documentElement.dataset.catalogRevision;
  if (!version) return;
  let checking = false;
  // Only pages that display catalog data need background freshness checks.
  const commercePage = location.pathname === "/" || /^\/(catalog|cart|checkout|favorites|compare|search)(\/|$)/.test(location.pathname);
  async function check() {
    if (checking || document.hidden || !commercePage) return;
    checking = true;
    try {
      const response = await fetch("/api/catalog", {cache:"no-store"});
      if (!response.ok) return;
      const data = await response.json();
      if (data.schemaVersion !== 1 || !Array.isArray(data.products) || typeof data.revision !== "string" || data.revision === version) return;
      if (window.lusarCartRefresh) {
        if (window.lusarCartRefresh(data)) version = data.revision;
      } else {
        // Catalog filters are in the URL; customer photo/contact forms are excluded above.
        location.reload();
      }
    } catch {
      // Preserve the rendered catalog on a transient connection failure.
    } finally {
      checking = false;
    }
  }
  window.lusarCatalogCheck = check;
  window.addEventListener("focus", check);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) check(); });
  if (commercePage) {
    setInterval(check, 60000);
    // Let the first screen and its controls become usable before polling.
    window.addEventListener("load", () => setTimeout(check, 1500), {once:true});
  }
})();
