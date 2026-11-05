"""Check cart editing, promo limits, guest form and safe retries with a simulated order API."""
import argparse
import json
import subprocess
import tempfile
import threading
from pathlib import Path
from urllib.parse import urlsplit

import serve
from check_checkout import EDGE

CHECK = r'''<!doctype html><meta charset="utf-8"><output>WAIT</output><iframe width="390" height="950"></iframe>
<script>
const output = document.querySelector("output"), frame = document.querySelector("iframe");
const require = (condition, message) => { if (!condition) throw Error(message); };
const tick = () => new Promise(resolve => setTimeout(resolve,40));
async function until(condition) { for (let i=0;i<80;i++) { if (condition()) return; await tick(); } throw Error("Timed out waiting for order state"); }
function open(path) { return new Promise(resolve => { frame.onload = () => resolve(frame.contentDocument); frame.src = path; }); }
function input(page, field, value) { field.value = value; field.dispatchEvent(new frame.contentWindow.Event("input", {bubbles:true})); }
function total(page) { return Number(page.querySelector("#order-total").textContent.replace(/[^0-9]/g,"")); }
function layout(page) { require(page.documentElement.scrollWidth <= page.documentElement.clientWidth + 1, "Overflow: " + page.location.pathname); }
(async () => {
 try {
  localStorage.clear(); sessionStorage.clear(); localStorage.setItem("lusar-cookie-choice-v1","essential");
  let page = await open("/checkout");
  require(!page.querySelector("#cart-empty").hidden && page.querySelector("#order-flow").hidden, "Empty checkout is orderable");
  page = await open("/checkout/received");
  require(page.querySelector(".receipt-symbol").hidden && page.querySelector("#receipt-details").hidden, "Receipt claimed an order without a receipt");
  localStorage.setItem("lusar-cart",JSON.stringify({[ITEM.id]:1}));
  page = await open("/cart");
  require(page.querySelector(".cart-row img") && total(page)===ITEM.price, "Cart photo or starting total missing");
  page.querySelector('[data-quantity-step="plus"]').click();
  require(total(page)===ITEM.price*2 && page.activeElement.dataset.quantityStep==="plus", "Quantity increment or focus failed");
  page.querySelector('[data-quantity-step="minus"]').click();
  require(total(page)===ITEM.price && page.querySelector('[data-quantity-step="minus"]').disabled, "Quantity decrement or lower boundary failed");
  let quantity = page.querySelector(".quantity-stepper input"); quantity.value="0"; quantity.dispatchEvent(new frame.contentWindow.Event("change"));
  require(quantity.value==="1" && JSON.parse(localStorage.getItem("lusar-cart"))[ITEM.id]===1, "Invalid quantity was saved");
  input(page,page.querySelector("#order-promo"),"LUSAR5000");
  require(total(page)===ITEM.price-Math.min(5000,Math.floor(ITEM.price/5)), "Fixed promo exceeded 20 percent");
  const changed = {[ITEM.id]:4}; localStorage.setItem("lusar-cart",JSON.stringify(changed));
  frame.contentWindow.dispatchEvent(new frame.contentWindow.StorageEvent("storage",{key:"lusar-cart"}));
  require(total(page)===ITEM.price*4-Math.min(5000,Math.floor(ITEM.price*4/5)), "Another tab did not update the total");
  page = await open("/checkout");
  require(page.querySelector("#order-promo").value==="LUSAR5000", "Promo lost between bag and checkout");
  const form = page.querySelector("#checkout");
  require(!form.elements.email.required && !form.elements.address.required, "Optional contacts are mandatory");
  for (const width of [320,390,1440]) {
   frame.style.width=width+"px"; await tick();
   for (const lang of ["ru","hy","en"]) {
    page.querySelector("#language").value=lang;page.querySelector("#language").dispatchEvent(new frame.contentWindow.Event("change"));await tick();
    layout(page);page.querySelector("#theme-toggle").click();layout(page);
   }
  }
  page.querySelector("#language").value="ru";page.querySelector("#language").dispatchEvent(new frame.contentWindow.Event("change"));
  frame.style.width="390px";
  input(page,form.elements.name,"Guest test");input(page,form.elements.phone,"123");
  const win=frame.contentWindow, sent=[]; let finish;
  win.fetch=async (url,options) => {
   if (url!=="/api/orders") throw Error("Unexpected API call");
   sent.push(JSON.parse(options.body));
   if (sent.length===1) return {ok:false,status:503,json:async()=>({error:"Test service unavailable"})};
   return new Promise(resolve=>{finish=()=>resolve({ok:true,status:201,json:async()=>({number:"LS-ABCDEF123456",trackingToken:"a".repeat(43)})});});
  };
  form.requestSubmit();require(sent.length===0,"Invalid phone reached API");
  input(page,form.elements.phone,"+374 77 123451");
  input(page,form.elements.promo,"INVALID");
  require(!form.elements.promo.validity.valid,"Invalid promo remained valid");
  input(page,form.elements.promo,"LUSAR10");
  require(total(page)===ITEM.price*4-Math.floor(ITEM.price*4/10), "Percentage promo calculated incorrectly");
  // Use a real fixed code for the retry payload.
  input(page,form.elements.promo,"LUSAR5000");
  form.requestSubmit();await until(()=>page.querySelector("#checkout-status").textContent==="Test service unavailable");
  require(!page.querySelector("#checkout-submit").disabled && form.elements.name.value==="Guest test", "Failure lost contacts or blocked retry");
  require(JSON.parse(localStorage.getItem("lusar-cart"))[ITEM.id]===4,"Failed request cleared the bag");
  form.requestSubmit();
  require(sent.length===2 && page.querySelector("#checkout-submit").disabled,"Pending request is not locked");
  form.dispatchEvent(new win.Event("submit",{bubbles:true,cancelable:true}));
  require(sent.length===2,"Duplicate request sent");
  require(sent[0].requestId===sent[1].requestId && sent[1].promo==="LUSAR5000", "Retry lost idempotency or associated promo field");
  require(sent[1].email==="" && sent[1].address==="","Guest request omitted optional empty contacts");
  localStorage.setItem("lusar-cart",JSON.stringify({[ITEM.id]:5,[SECOND]:1}));
  finish();await until(()=>frame.contentWindow.location.pathname==="/checkout/received");
  page=frame.contentDocument;await until(()=>!page.querySelector("#receipt-details").hidden);
  require(page.querySelector("#receipt-number").textContent.includes("LS-ABCDEF123456") && !page.querySelector("#receipt-tracking").hidden,"Receipt or tracking missing");
  const remaining=JSON.parse(localStorage.getItem("lusar-cart"));
  require(remaining[ITEM.id]===1 && remaining[SECOND]===1,"Success erased items added while request was pending");
  for (const width of [320,390,1440]) {frame.style.width=width+"px";await tick();layout(page);}
  localStorage.setItem("lusar-cart",JSON.stringify({[ITEM.id]:1}));
  page=await open("/cart");
  frame.contentWindow.eval('products['+JSON.stringify(ITEM.id)+'].price=null; renderCart();');
  require(page.querySelector("#order-promo").disabled && page.querySelector("#order-total").textContent==="Цена по запросу", "Unpriced item got a fabricated total");
  page.querySelector("[data-remove]").click();
  require(!page.querySelector("#cart-empty").hidden && page.querySelector("#order-flow").hidden,"Removing last item failed");
  output.textContent="PASS";
 } catch(error) {output.textContent="FAIL: "+error.message;}
})();
</script>'''


class Handler(serve.Handler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        if urlsplit(self.path).path != "/cart-check":
            return super().do_GET()
        products = json.loads(serve.CATALOG.read_text(encoding="utf-8-sig"))["products"]
        payload = CHECK.replace("ITEM", json.dumps(products[0])).replace("SECOND", json.dumps(products[1]["id"])).encode("utf-8")
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
                result = subprocess.run([str(browser), "--headless=new", "--no-first-run", "--disable-gpu", "--user-data-dir="+profile,
                                         "--window-size=1600,1100", "--virtual-time-budget=16000", "--dump-dom",
                                         f"http://127.0.0.1:{server.server_port}/cart-check"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=45)
            finally:
                server.shutdown()
        if "<output>PASS</output>" not in result.stdout:
            raise RuntimeError(result.stdout.partition("<output>")[2].partition("</output>")[0] or result.stderr[-500:])
    print("Cart editing, promo cap, shared state, guest contacts, failed retry, duplicate prevention, receipt and pending cart preservation passed with a simulated order API.")


if __name__ == "__main__":
    main()
