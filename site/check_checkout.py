"""Exercise the storefront and manager in a headless browser with an isolated database."""
import argparse
import base64
import json
import os
import secrets
import subprocess
import tempfile
import threading
from pathlib import Path

import serve

EDGE = Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "Microsoft/Edge/Application/msedge.exe"
SCRIPT = r"""<!doctype html><meta charset="utf-8"><body><output>WAIT</output><iframe width="390" height="780"></iframe>
<script>
const output = document.querySelector("output");
const frame = document.querySelector("iframe");
function openPage(path, action) {
  frame.onload = () => {
    try { action(frame.contentDocument); }
    catch (error) { output.textContent = "FAIL: " + error.message; }
  };
  frame.src = path;
}
function require(condition, message) { if (!condition) throw Error(message); }
function mobileLayout(page) {
  const root = page.documentElement;
  require(root.scrollWidth <= root.clientWidth + 1, "Horizontal overflow: " + page.location.pathname);
}
async function managerPage(number) {
  const response = await fetch("/manager/orders/", {headers: {Authorization: AUTH}});
  require(response.ok, "Manager page failed");
  const page = new DOMParser().parseFromString(await response.text(), "text/html");
  const card = page.getElementById(number);
  require(card, "Order missing in manager");
  return card;
}
async function managerAction(card, selector, values) {
  const form = card.querySelector(selector);
  require(form, "Missing manager action: " + selector);
  const fields = new URLSearchParams(new FormData(form));
  for (const [name, value] of Object.entries(values)) fields.set(name, value);
  const result = await fetch(new URL(form.getAttribute("action"), location.origin), {
    method: "POST", headers: {Authorization: AUTH}, body: fields
  });
  require(result.ok && result.redirected, "Manager action failed: " + result.status);
}
async function guestStatus(params) {
  const response = await fetch("/api/order-status", {
    method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(params)
  });
  require(response.ok, "Tracking failed");
  return response.json();
}
function startShopping() {
openPage("/catalog", page => {
  mobileLayout(page);
  require(page.querySelector('main a[href^="/catalog/category/"]'), "Missing categories");
  require(page.querySelector('.product-tiles a[href^="/catalog/product/"]'), "Missing catalog products");
  openPage(PRODUCT, page => {
    mobileLayout(page);
    page.querySelector("[data-add]").click();
    require(!page.querySelector("#cart-next").hidden, "Add confirmation missing");
    openPage("/cart", page => {
      mobileLayout(page);
      require(!page.querySelector("#checkout-link").hidden, "Cart is empty");
      frame.onload = async () => {
        try {
          const confirmation = frame.contentDocument;
          mobileLayout(confirmation);
          const text = confirmation.querySelector("#receipt-number").textContent;
          const number = text.match(/LS-[A-F0-9]{12}/)[0];
          const link = confirmation.querySelector("#receipt-tracking");
          require(!link.hidden, "Tracking link missing");
          const params = Object.fromEntries(new URLSearchParams(link.hash.slice(1)));
          require((await guestStatus(params)).number === number, "Tracking number mismatch");
          const statusForm = 'form[action="/manager/orders/status"]';
          const adjustForm = 'form[action="/manager/orders/adjust"]';
          let card = await managerPage(number);
          await managerAction(card, statusForm, {target: "in_progress"});
          card = await managerPage(number);
          await managerAction(card, adjustForm, {action: "payment", value: "store"});
          card = await managerPage(number);
          await managerAction(card, statusForm, {target: "completed"});
          require((await guestStatus(params)).status === "Выполнено", "Guest completed status missing");
          card = await managerPage(number);
          const product = card.querySelector(adjustForm + ' select[name="value"]').value;
          await managerAction(card, adjustForm, {action: "return", value: product, quantity: "1"});
          require((await guestStatus(params)).status === "Отменено", "Guest cancelled status missing");
          card = await managerPage(number);
          await managerAction(card, adjustForm, {action: "refund_paid", value: "0"});
          output.textContent = "PASS:" + number;
        } catch (error) { output.textContent = "FAIL: " + error.message; }
      };
      frame.contentDocument.querySelector("#checkout-link a").click();
      const formReady = () => {
        const form = frame.contentDocument.querySelector("#checkout");
        if (!form) return setTimeout(formReady, 25);
        mobileLayout(frame.contentDocument);
        form.elements.name.value = "Checkout test";
        form.elements.phone.value = "+37400000000";
        form.elements.promo.value = "LUSAR5000";
        form.elements.promo.dispatchEvent(new Event("input"));
        require(frame.contentDocument.querySelector("#promo-total").textContent.includes("Итог") ||
          frame.contentDocument.querySelector("#promo-total").textContent.includes("итог"), "Promo preview missing");
        frame.onload = receiptReady;
        form.requestSubmit();
      };
      const receiptReady = frame.onload;
      frame.onload = formReady;
    });
  });
});
}
openPage("/", page => {
  mobileLayout(page);
  const [catalog, rooms] = page.querySelectorAll(".nav-dropdown");
  const catalogTrigger = catalog.querySelector("summary");
  catalogTrigger.click();
  require(catalog.open && catalog.querySelector('a[href="/catalog"]'), "Catalog dropdown failed");
  mobileLayout(page);
  rooms.querySelector("summary").click();
  require(rooms.open && !catalog.open && rooms.querySelector('a[href^="/rooms/"]'), "Room dropdown failed");
  page.dispatchEvent(new frame.contentWindow.KeyboardEvent("keydown", {key: "Escape", bubbles: true}));
  require(!rooms.open && page.activeElement === rooms.querySelector("summary"), "Escape did not restore menu focus");
  catalogTrigger.click();
  page.querySelector("#home-title").click();
  require(!catalog.open, "Click outside did not close menu");
  const day = page.querySelector('[data-scene="day"]');
  day.click();
  const timeout = Date.now() + 5000;
  function waitForScene() {
    if (day.getAttribute("aria-pressed") === "true") {
      require(page.querySelector("#scene-image").src.endsWith("lusar-scene-day.webp"), "Wrong daylight frame");
      mobileLayout(page);
      startShopping();
    } else if (Date.now() < timeout) {
      setTimeout(waitForScene, 25);
    } else {
      output.textContent = "FAIL: daylight scene did not load";
    }
  }
  waitForScene();
});
</script>"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", type=Path, default=EDGE)
    browser = parser.parse_args().browser
    catalog = json.loads(serve.CATALOG.read_text(encoding="utf-8-sig"))
    product = next(item for item in catalog["products"] if item["price"] is not None)
    password = secrets.token_urlsafe(20)
    os.environ["LUSAR_LOCAL_MANAGER_PASSWORD"] = password
    auth = "Basic " + base64.b64encode(f"manager:{password}".encode()).decode()
    name = "checkout-check-" + secrets.token_hex(8) + ".html"
    page = serve.ROOT / "dist" / name
    markup = SCRIPT.replace("PRODUCT", json.dumps("/catalog/product/" + product["id"])).replace("AUTH", json.dumps(auth))
    with tempfile.TemporaryDirectory(dir=serve.ROOT, ignore_cleanup_errors=True) as temp:
        serve.DATABASE = Path(temp) / "orders.sqlite"
        page.write_text(markup, encoding="utf-8")
        try:
            with serve.ThreadingHTTPServer(("127.0.0.1", 0), serve.Handler) as server:
                threading.Thread(target=server.serve_forever, daemon=True).start()
                try:
                    result = subprocess.run([
                        str(browser), "--headless=new", "--no-first-run", "--disable-gpu",
                        "--user-data-dir=" + str(Path(temp) / "browser"), "--window-size=430,900",
                        "--virtual-time-budget=12000", "--dump-dom", f"http://127.0.0.1:{server.server_port}/{name}",
                    ], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=45)
                finally:
                    server.shutdown()
            if "<output>PASS:" not in result.stdout:
                output = result.stdout.partition("<output>")[2].partition("</output>")[0]
                raise RuntimeError(output or result.stderr[-500:])
            with serve.closing(serve.sqlite3.connect(serve.DATABASE)) as db:
                status, payload = db.execute("SELECT status, payload FROM orders").fetchone()
                history = db.execute("SELECT current FROM order_status_history ORDER BY rowid").fetchall()
            saved = json.loads(payload)
            expected = serve.order_amount([{"unitPrice": product["price"], "quantity": 1}], "LUSAR5000")
            assert saved["total"] == expected["total"] and saved["promoDiscount"] == expected["promoDiscount"]
            assert status == "cancelled" and history == [("in_progress",), ("completed",), ("cancelled",)]
            assert saved["remainingAmount"]["total"] == 0
            assert saved["returns"][0]["refundDue"] == saved["total"] and saved["returns"][0]["refundPaid"]
            print("390px mobile layout, light scene, checkout and manager workflow passed.")
        finally:
            page.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
