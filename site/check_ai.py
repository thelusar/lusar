"""Check the AI workspace in Chrome with a local simulated API."""
import argparse
import json
import subprocess
import tempfile
import threading
from pathlib import Path
from urllib.parse import urlsplit

import serve
from check_checkout import EDGE

TEST_PRODUCT = json.loads(serve.CATALOG.read_text(encoding="utf-8-sig"))["products"][0]

MOCK = """
<script>
window.aiRequests = [];
const realFetch = window.fetch;
window.fetch = (url, options = {}) => {
  if (url !== "/api/ai") return realFetch(url, options);
  if (options.method !== "POST") return Promise.resolve(new Response('{"available":true}'));
  window.aiRequests.push(JSON.parse(options.body));
  if (window.aiRequests.length > 1) {
    return new Promise(resolve => setTimeout(() => resolve(new Response(
      '{"error":"Test service unavailable"}', {status:503})), 100));
  }
  return new Promise(resolve => setTimeout(() => resolve(new Response(JSON.stringify({
    image: "/scenes/ai-interior.jpg",
    advice: "Local test result.",
    products: [{id:"TEST_PRODUCT_ID",name:"Test light",path:"/catalog",reason:"Test recommendation.",inMockup:true}]
  }))), 400));
};
</script>
"""

CHECK = """
<!doctype html><meta charset="utf-8"><body><output>WAIT</output>
<iframe width="390" height="850" src="/ai"></iframe><script>
const frame = document.querySelector("iframe");
const output = document.querySelector("output");
function require(condition, message) { if (!condition) throw Error(message); }
async function waitFor(condition) {
  const deadline = Date.now() + 5000;
  while (!condition()) {
    if (Date.now() > deadline) throw Error("Timed out waiting for AI state");
    await new Promise(resolve => setTimeout(resolve, 25));
  }
}
frame.onload = async () => {
  try {
    const page = frame.contentDocument, win = frame.contentWindow;
    const input = page.querySelector("#ai-photo");
    await waitFor(() => !page.querySelector("#ai-submit").disabled);
    const invalid = new win.DataTransfer();
    invalid.items.add(new win.File(["invalid"], "test.txt", {type:"text/plain"}));
    input.files = invalid.files;
    input.dispatchEvent(new win.Event("change"));
    require(input.files.length === 0 && !page.querySelector("#ai-empty").hidden, "Invalid upload did not reset");
    const canvas = page.createElement("canvas");
    canvas.width = canvas.height = 16;
    canvas.getContext("2d").fillRect(0, 0, 16, 16);
    const photo = await new Promise(resolve => canvas.toBlob(resolve, "image/png"));
    const transfer = new win.DataTransfer();
    transfer.items.add(new win.File([photo], "room.png", {type:"image/png"}));
    const dropzone = page.querySelector("#ai-dropzone");
    dropzone.dispatchEvent(new win.DragEvent("drop", {dataTransfer:transfer,bubbles:true,cancelable:true}));
    await waitFor(() => !page.querySelector("#ai-photo-preview").hidden);
    require(page.querySelector("#ai-empty").hidden, "Example image remained after upload");
    require(page.querySelector("#ai-file-label").textContent === "room.png", "Filename is missing");
    const preset = page.querySelector("[data-ai-wish]");
    preset.click();
    const wishes = page.querySelector("#ai-wishes");
    const submittedWishes = wishes.value;
    require(submittedWishes && preset.getAttribute("aria-pressed") === "true", "Quick preference failed");
    page.querySelector("#ai-consent").checked = true;
    page.querySelector("#ai-form").requestSubmit();
    require(!page.querySelector("#ai-progress").hidden && input.disabled, "Loading state failed");
    wishes.value = "Changed while processing";
    page.querySelector("#ai-form").requestSubmit();
    await waitFor(() => !page.querySelector("#ai-visualization").hidden);
    require(win.aiRequests.length === 1, "Duplicate AI request");
    require(win.aiRequests[0].wishes === submittedWishes && win.aiRequests[0].photo, "Submitted input changed");
    require(page.querySelector("#ai-before").src.startsWith("blob:"), "Original photo is missing");
    require(page.querySelector("#ai-progress").hidden && !input.disabled, "Loading did not end");
    const slider = page.querySelector("#ai-compare");
    slider.value = "75";
    slider.dispatchEvent(new win.Event("input"));
    require(win.getComputedStyle(page.querySelector("#ai-render")).clipPath.includes("75%"), "Comparison slider failed");
    require(page.querySelector("#ai-results a") && !page.querySelector("#ai-results").hidden, "Product suggestions are missing");
    require(page.querySelector("#ai-results img") && !page.querySelector("#ai-advice").hidden, "Product photo or explanation is missing");
    page.querySelector("#ai-form").requestSubmit();
    await waitFor(() => page.querySelector("#ai-result-status").textContent === "Test service unavailable");
    require(!page.querySelector("#ai-photo-preview").hidden && page.querySelector("#ai-visualization").hidden, "Original photo disappeared after an API error");
    require(page.querySelector("#ai-progress").hidden && !page.querySelector("#ai-submit").disabled, "Cannot retry after an API error");
    require(page.documentElement.scrollWidth <= page.documentElement.clientWidth + 1, "AI workspace overflows on mobile");
    output.textContent = "PASS";
  } catch (error) {
    output.textContent = "FAIL: " + error.message;
  }
};
</script>
"""


class Handler(serve.Handler):
    def do_GET(self):
        route = urlsplit(self.path).path
        if route == "/ai":
            content = (serve.ROOT / "dist/ai/index.html").read_text(encoding="utf-8")
            content = content.replace("<head>", "<head>" + MOCK.replace("TEST_PRODUCT_ID", TEST_PRODUCT["id"]), 1)
        elif route == "/ai-check":
            content = CHECK
        else:
            return super().do_GET()
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
                result = subprocess.run([
                    str(browser), "--headless=new", "--no-first-run", "--disable-gpu",
                    "--user-data-dir=" + profile, "--window-size=430,930",
                    "--virtual-time-budget=12000", "--dump-dom",
                    f"http://127.0.0.1:{server.server_port}/ai-check",
                ], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=45)
            finally:
                server.shutdown()
        if "<output>PASS</output>" not in result.stdout:
            message = result.stdout.partition("<output>")[2].partition("</output>")[0]
            raise RuntimeError(message or result.stderr[-500:])
    print("AI upload, validation, preferences, progress, input consistency, comparison and recommendations passed with a simulated API.")


if __name__ == "__main__":
    main()
