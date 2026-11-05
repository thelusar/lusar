(() => {
  let version = document.documentElement.dataset.catalogRevision;
  if (!version) return;
  let checking = false;
  const protectedForm = /^\/(ai|support|order-status|account)(\/|$)/.test(location.pathname);
  async function check() {
    if (checking || document.hidden || protectedForm) return;
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
  setInterval(check, 30000);
  check();
})();
