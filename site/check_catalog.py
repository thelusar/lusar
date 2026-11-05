"""Exercise catalog discovery, saved shopping actions and gallery navigation in Chrome."""
import argparse
import json
import subprocess
import tempfile
import threading
from pathlib import Path
from urllib.parse import urlsplit

import serve
from check_checkout import EDGE

CHECK = r'''<!doctype html><meta charset="utf-8"><output>WAIT</output><iframe width="390" height="850"></iframe>
<script>
const output = document.querySelector("output"), frame = document.querySelector("iframe");
const require = (condition, message) => { if (!condition) throw Error(message); };
function open(path) {
  return new Promise(resolve => { frame.onload = () => resolve(frame.contentDocument); frame.src = path; });
}
const tick = () => new Promise(resolve => setTimeout(resolve, 40));
function visible(page) { return [...page.querySelectorAll(".product-tiles > li")].filter(item => !item.hidden); }
function input(page, name, value) {
  const field = page.querySelector("#product-filters").elements.namedItem(name);
  field.value = value;
  field.dispatchEvent(new frame.contentWindow.Event("input", {bubbles:true}));
}
function layout(page) {
  require(page.documentElement.scrollWidth <= page.documentElement.clientWidth + 1, "Overflow: " + page.location.pathname);
}
(async () => {
  try {
    localStorage.clear(); sessionStorage.setItem("lusar-first-order-promo-seen", "1");
    let page = await open("/catalog");
    layout(page);
    const total = visible(page).length;
    require(total > 2, "Catalog products missing");
    input(page, "q", TEST_SKU);
    require(visible(page).length === 1, "SKU search failed");
    require(new URL(frame.contentWindow.location.href).searchParams.get("q") === TEST_SKU, "Search URL missing");
    page = await open(frame.contentWindow.location.href);
    require(visible(page).length === 1, "Search did not survive reload");
    page.querySelector("#product-filters").reset(); await tick();
    require(visible(page).length === total, "Reset failed");
    input(page, "category", "sconces");
    input(page, "maximum", "17000");
    require(visible(page).length > 0 && visible(page).every(item => item.dataset.category === "sconces" && Number(item.dataset.price) <= 17000), "Combined filters failed");
    input(page, "socket", "E27");
    require(!page.querySelector("#catalog-empty").hidden, "Empty results state missing");
    page.querySelector("#catalog-empty button").click(); await tick();
    input(page, "sort", "high");
    const prices = visible(page).map(item => Number(item.dataset.price));
    require(prices.every((price,i) => !i || prices[i-1] >= price), "Descending price sort failed");
    page.querySelector("#product-filters").reset(); await tick();
    const buttons = [...page.querySelectorAll("[data-favorite]")];
    buttons[0].click(); buttons[1].click();
    require(buttons[0].getAttribute("aria-pressed") === "true" && buttons[1].getAttribute("aria-pressed") === "true", "Multiple wishlist buttons failed");
    buttons[0].click();
    require(JSON.parse(localStorage.getItem("lusar-favorites")).length === 1, "Wishlist removal failed");
    const metrics = [], win = frame.contentWindow;
    win.addEventListener("lusar:analytics", event => metrics.push(event.detail));
    page.querySelector('[data-cookie-choice="analytics"]').click();
    require(!metrics.some(event => event.name === "view_item"), "Catalog falsely tracked a product view");
    const adds = [...page.querySelectorAll("[data-add]")];
    adds[0].click(); adds[1].click();
    require(metrics.filter(event => event.name === "add_to_cart").length === 2, "Quick adds were not tracked");
    require(Object.keys(JSON.parse(localStorage.getItem("lusar-cart"))).length === 2, "Quick add missed a product");
    page.querySelector("[data-dismiss-shopping]").click();
    require(!page.querySelector("#cart-status").textContent && page.activeElement === adds[1], "Shopping notice dismissal failed");
    page = await open("/cart");
    require(page.querySelectorAll("#cart-items > article").length === 2, "Bag did not receive quick-add products");
    page = await open("/catalog/category/sconces");
    require(page.querySelector("script[src^='/cart.js?']"), "Shopping scripts missing on category page");
    const favorite = page.querySelector("[data-favorite]"); favorite.click();
    require(favorite.getAttribute("aria-pressed") === "true", "Category wishlist action failed");
    layout(page);
    page = await open(TEST_PATH);
    const gallery = page.querySelector(".product-gallery"), photos = gallery.querySelectorAll("[data-photo]");
    require(photos.length > 1, "Gallery test needs multiple photos");
    gallery.querySelector('[data-gallery-step="1"]').click();
    require(photos[1].getAttribute("aria-pressed") === "true", "Next photo failed");
    gallery.querySelector("#product-photo-link").focus();
    gallery.querySelector("#product-photo-link").click();
    const dialog = gallery.querySelector("dialog");
    require(dialog.open && gallery.querySelector("#product-photo-large").src === photos[1].dataset.photo, "Zoom did not open selected photo");
    dialog.querySelector('[data-gallery-step="-1"]').click();
    require(photos[0].getAttribute("aria-pressed") === "true", "Modal navigation failed");
    dialog.querySelector("form button").click(); await tick();
    require(!dialog.open && page.activeElement.id === "product-photo-link", "Gallery focus did not return: open=" + dialog.open + ", focus=" + page.activeElement.outerHTML.slice(0,160));
    require(page.querySelector(".related-products a"), "Related category models missing");
    const ai = page.querySelector(".product-ai-note a");
    require(new URL(ai.href).searchParams.get("product") === TEST_ID, "AI lost product context");
    for (const width of [320,390,1440]) {
      frame.style.width = width + "px"; await tick();
      for (const lang of ["ru","hy","en"]) {
        page.querySelector("#language").value = lang;
        page.querySelector("#language").dispatchEvent(new frame.contentWindow.Event("change"));
        layout(page);
        require(page.querySelector("[data-gallery-step='1']").getAttribute("aria-label") !== "Следующее фото" || lang === "ru", "Gallery controls not translated");
        page.querySelector("#theme-toggle").click(); layout(page);
      }
    }
    page = await open("/catalog?category=pendants&minimum=6000&maximum=25000&sort=low");
    require(page.querySelector("#product-filters details").open, "Restored filters are hidden");
    require(visible(page).length > 0 && visible(page).every(item => item.dataset.category === "pendants"), "Shared filter link failed");
    for (const width of [320,390,1440]) {
      frame.style.width = width + "px"; await tick(); layout(page);
      for (const lang of ["ru","hy","en"]) {
        page.querySelector("#language").value = lang;
        page.querySelector("#language").dispatchEvent(new frame.contentWindow.Event("change")); await tick();
        layout(page);
        if (lang === "en") require(page.querySelector("#product-filter-count").textContent.startsWith("Products:"), "Result counter not translated");
      }
    }
    output.textContent = "PASS";
  } catch (error) { output.textContent = "FAIL: " + error.message; }
})();
</script>'''


class Handler(serve.Handler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        if urlsplit(self.path).path != "/catalog-check":
            return super().do_GET()
        product = json.loads(serve.CATALOG.read_text(encoding="utf-8-sig"))["products"][0]
        content = CHECK.replace("TEST_SKU", json.dumps(product["sku"])).replace("TEST_PATH", json.dumps("/catalog/product/" + product["id"])).replace("TEST_ID", json.dumps(product["id"]))
        payload = content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", type=Path, default=EDGE)
    browser = parser.parse_args().browser
    with tempfile.TemporaryDirectory() as profile:
        with serve.ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
            threading.Thread(target=server.serve_forever, daemon=True).start()
            try:
                result = subprocess.run([str(browser), "--headless=new", "--no-first-run", "--disable-gpu", "--user-data-dir=" + profile,
                                         "--window-size=1600,1000", "--virtual-time-budget=16000", "--dump-dom",
                                         f"http://127.0.0.1:{server.server_port}/catalog-check"],
                                        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=45)
            finally:
                server.shutdown()
        if "<output>PASS</output>" not in result.stdout:
            raise RuntimeError(result.stdout.partition("<output>")[2].partition("</output>")[0] or result.stderr[-500:])
    print("Catalog search, combined filters, shared URLs, quick shopping actions, gallery, related models and responsive language/theme layouts passed.")


if __name__ == "__main__":
    main()
