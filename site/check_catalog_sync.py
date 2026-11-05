"""Exercise generation updates, authoritative orders and in-place browser refresh with an isolated public feed."""
import argparse
import copy
import json
import subprocess
import tempfile
import threading
import unittest
import uuid
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

import serve
from catalog_runtime import CatalogService, CatalogUnavailable
from check_checkout import EDGE
from sync_catalog import validate

SEED = json.loads(serve.CATALOG.read_text(encoding="utf-8-sig"))


class Feed:
    def __init__(self):
        self.data = copy.deepcopy(SEED)
        self.offline = False

    def __call__(self):
        if self.offline:
            raise OSError("Test feed offline")
        return copy.deepcopy(self.data)


class Quiet(serve.Handler):
    def log_message(self, *_):
        pass


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.feed = Feed()
        self.service = CatalogService(Path(self.temp.name) / "generations", fetcher=self.feed)
        self.addCleanup(self.service.close)
        previous = serve.DATABASE
        serve.DATABASE = Path(self.temp.name) / "orders.sqlite"
        self.addCleanup(setattr, serve, "DATABASE", previous)
        self.server = serve.ThreadingHTTPServer(("127.0.0.1", 0), Quiet)
        self.server.catalog_service = self.service
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.origin = f"http://127.0.0.1:{self.server.server_port}"

    def request(self, path, payload=None):
        request = Request(self.origin + path, data=json.dumps(payload).encode() if payload else None,
                          headers={"Content-Type": "application/json"} if payload else {})
        try:
            response = urlopen(request, timeout=15)
        except HTTPError as error:
            response = error
        with response:
            return response.status, response.read().decode("utf-8")

    def payload(self, price=None):
        product = SEED["products"][0]
        return {"name": "Sync test", "phone": "+37400000000", "email": "", "address": "", "promo": "",
                "cart": {product["id"]: 1}, "displayedPrices": {product["id"]: product["price"] if price is None else price},
                "requestId": str(uuid.uuid4())}

    def test_pages_and_versioned_data_change_together(self):
        self.service.refresh()
        old = self.service.active.revision
        product = self.feed.data["products"][0]
        product["name"] = "SYNC renamed light"
        product["price"] += 5000
        new = copy.deepcopy(product)
        new["id"] = "sync-new-light"
        new["sku"] = "SYNC-NEW"
        self.feed.data["products"].append(new)
        self.service.refresh()
        status, page = self.request("/catalog/product/sync-new-light")
        self.assertEqual(status, 200)
        self.assertIn("SYNC renamed light", page)
        self.assertIn('data-catalog-revision="' + self.service.active.revision + '"', page)
        self.assertIn("SYNC-NEW", self.request("/search.js")[1])
        self.assertNotIn("SYNC-NEW", self.request("/search.js?catalog=" + old)[1])
        self.assertEqual(len(json.loads(self.request("/api/catalog")[1])["products"]), len(SEED["products"]) + 1)
        self.assertEqual(self.request("/catalog/product/sync-new-light/index.html")[0], 200)

    def test_checkout_checks_live_prices_and_preserves_saved_order(self):
        product = self.feed.data["products"][0]
        stale = self.payload()
        product["price"] += 5000
        self.assertEqual(self.request("/api/orders", stale)[0], 409)
        accepted = self.payload(product["price"])
        status, body = self.request("/api/orders", accepted)
        self.assertEqual(status, 201)
        number = json.loads(body)["number"]
        product["price"] += 2000
        self.service.refresh()
        with serve.closing(serve.sqlite3.connect(serve.DATABASE)) as db:
            saved = json.loads(db.execute("SELECT payload FROM orders WHERE number = ?", (number,)).fetchone()[0])
        self.assertEqual(saved["total"], accepted["displayedPrices"][product["id"]])
        self.feed.offline = True
        self.assertEqual(self.request("/api/orders", accepted)[0], 200)
        self.assertEqual(self.request("/api/orders", self.payload())[0], 503)

    def test_unpublish_last_product_and_invalid_feed(self):
        self.service.refresh()
        previous = self.service.active
        self.feed.data = {"schemaVersion": 1, "currency": "AMD", "products": "partial", "categories": []}
        with self.assertRaises(CatalogUnavailable):
            self.service.refresh()
        self.assertIs(self.service.active, previous)
        self.assertEqual(self.request("/catalog")[0], 200)
        self.feed.data = {"schemaVersion": 1, "currency": "AMD", "products": [], "categories": []}
        self.service.refresh()
        self.assertEqual(json.loads(self.request("/api/catalog")[1])["products"], [])
        self.assertEqual(self.request("/catalog/product/" + SEED["products"][0]["id"])[0], 404)
        self.assertEqual(self.request("/api/orders", self.payload())[0], 409)

    def test_failed_build_does_not_replace_generation(self):
        previous = self.service.active
        self.feed.data["products"][0]["price"] += 1
        self.service.build = lambda _: (_ for _ in ()).throw(RuntimeError("Test build failed"))
        with self.assertRaises(CatalogUnavailable):
            self.service.refresh()
        self.assertIs(self.service.active, previous)
        self.assertEqual(self.request("/catalog")[0], 200)

    def test_reject_category_cycles(self):
        invalid = copy.deepcopy(SEED)
        invalid["categories"][0]["parentId"] = invalid["categories"][1]["id"]
        invalid["categories"][1]["parentId"] = invalid["categories"][0]["id"]
        with self.assertRaises(ValueError):
            validate(invalid)


BROWSER = r'''<!doctype html><meta charset="utf-8"><output>WAIT</output><iframe width="390" height="950"></iframe>
<script>
const output=document.querySelector("output"), frame=document.querySelector("iframe");
const require=(ok,message)=>{if(!ok)throw Error(message);};
const tick=()=>new Promise(resolve=>setTimeout(resolve,50));
async function until(test){for(let i=0;i<100;i++){if(test())return;await tick();}throw Error("Sync UI timed out");}
function open(path){return new Promise(resolve=>{frame.onload=()=>resolve(frame.contentDocument);frame.src=path;});}
(async()=>{try{
 localStorage.clear();sessionStorage.clear();localStorage.setItem("lusar-cookie-choice-v1","essential");
 localStorage.setItem("lusar-cart",JSON.stringify({[FIRST]:1,[SECOND]:1}));
 let page=await open("/checkout");const form=page.querySelector("#checkout");
 form.elements.name.value="Sync guest";form.elements.phone.value="+37400000000";form.elements.email.value="sync@example.test";form.elements.address.value="Test address";
 await fetch("/sync-change",{method:"POST"});await frame.contentWindow.lusarCatalogCheck();
 await until(()=>!!page.querySelector(".cart-row-unavailable"));
 require(form.elements.name.value==="Sync guest"&&form.elements.email.value==="sync@example.test"&&form.elements.address.value==="Test address","Refresh lost contact fields");
 require(page.querySelector("#checkout-submit").disabled,"Removed product can be ordered");
 require(page.querySelector(".cart-row-info a").textContent.includes("SYNC changed"),"Changed product name missing");
 page.querySelector('.cart-row-unavailable [data-remove]').click();
 require(!form.hidden&&!page.querySelector("#checkout-submit").disabled,"Removing unpublished item did not unblock checkout");
 require(Number(page.querySelector("#order-total").textContent.replace(/[^0-9]/g,""))===PRICE,"Changed price missing in total");
 require(page.documentElement.scrollWidth<=page.documentElement.clientWidth+1,"Refreshed cart overflows");
 page=await open("/catalog?q=SYNC");
 require(page.querySelector('.product-tiles a[href="/catalog/product/sync-new-light"]'),"Published model missing");
 await fetch("/sync-change-again",{method:"POST"});await frame.contentWindow.lusarCatalogCheck();
 await until(()=>frame.contentDocument!==page);page=frame.contentDocument;
 await until(()=>!!page.querySelector('.product-tiles a[href="/catalog/product/sync-second-light"]'));
 require(new URL(frame.contentWindow.location.href).searchParams.get("q")==="SYNC","Refresh lost the search query");
 output.textContent="PASS";
}catch(error){output.textContent="FAIL: "+error.message;}})();
</script>'''


def check_browser(browser):
    feed = Feed()
    with tempfile.TemporaryDirectory() as temp:
        service = CatalogService(Path(temp) / "generations", fetcher=feed)

        class BrowserHandler(Quiet):
            def do_GET(self):
                if urlsplit(self.path).path != "/sync-check":
                    return super().do_GET()
                page = BROWSER.replace("FIRST", json.dumps(SEED["products"][0]["id"])).replace("SECOND", json.dumps(SEED["products"][1]["id"])).replace("PRICE", str(SEED["products"][0]["price"] + 5000)).encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(page)))
                self.end_headers()
                self.wfile.write(page)

            def do_POST(self):
                if self.path not in {"/sync-change", "/sync-change-again"}:
                    return super().do_POST()
                if self.path == "/sync-change":
                    feed.data["products"][0]["price"] += 5000
                    feed.data["products"][0]["name"] = "SYNC changed light"
                    feed.data["products"].pop(1)
                new = copy.deepcopy(feed.data["products"][0])
                new["id"] = "sync-new-light" if self.path == "/sync-change" else "sync-second-light"
                feed.data["products"].append(new)
                service.refresh()
                return self.reply(200, {"ok": True})

        with serve.ThreadingHTTPServer(("127.0.0.1", 0), BrowserHandler) as server:
            server.catalog_service = service
            threading.Thread(target=server.serve_forever, daemon=True).start()
            try:
                result = subprocess.run([str(browser), "--headless=new", "--no-first-run", "--disable-gpu", "--user-data-dir=" + str(Path(temp) / "browser"),
                                         "--window-size=510,1100", "--virtual-time-budget=18000", "--dump-dom", f"http://127.0.0.1:{server.server_port}/sync-check"],
                                        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=45)
            finally:
                server.shutdown()
                service.close()
        if "<output>PASS</output>" not in result.stdout:
            raise RuntimeError(result.stdout.partition("<output>")[2].partition("</output>")[0] or result.stderr[-500:])
    print("Browser catalog refresh, preserved checkout contacts, changed prices, unpublished items and newly published pages passed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", type=Path, default=EDGE)
    args = parser.parse_args()
    result = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(SyncTests))
    if not result.wasSuccessful():
        raise SystemExit(1)
    check_browser(args.browser)
