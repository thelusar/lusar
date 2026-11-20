"""Check indexable metadata, schema, links, and completed launch page layouts."""
import argparse
import json
import subprocess
import tempfile
import threading
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree as ET

import serve
from check_checkout import EDGE

PAGES = ["selection", "services", "professionals/request", "account/notifications", "legal/cookies", "legal/loyalty"]


class Metadata(HTMLParser):
    def __init__(self, markup):
        super().__init__()
        self.description = self.canonical = ""
        self.schemas = []
        self.links = []
        self.schema = None
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta" and a.get("name") == "description":
            self.description = a.get("content", "")
        if tag == "link" and a.get("rel") == "canonical":
            self.canonical = a.get("href", "")
        if tag == "a":
            self.links.append(a.get("href", ""))
        if tag == "script" and a.get("type") == "application/ld+json":
            self.schema = ""

    def handle_data(self, data):
        if self.schema is not None:
            self.schema += data

    def handle_endtag(self, tag):
        if tag == "script" and self.schema is not None:
            value = json.loads(self.schema)
            self.schemas.extend(value if isinstance(value, list) else [value])
            self.schema = None


def check_static(directory):
    urls = [e.text for e in ET.parse(directory / "sitemap.xml").getroot().iter() if e.tag.endswith("loc")]
    assert len(urls) == len(set(urls)), "Duplicate sitemap URLs"
    types = {}
    for url in urls:
        route = urlsplit(url).path.strip("/")
        page = directory / route / "index.html"
        markup = page.read_text(encoding="utf-8")
        meta = Metadata(markup)
        assert meta.description.strip(), f"Missing description: {route}"
        assert meta.canonical == url, f"Canonical mismatch: {route}"
        assert 'name="robots" content="noindex"' not in markup, f"Draft in sitemap: {route}"
        for schema in meta.schemas:
            types[schema["@type"]] = types.get(schema["@type"], 0) + 1
        if route:
            crumbs = next(s for s in meta.schemas if s.get("@type") == "BreadcrumbList")["itemListElement"]
            assert crumbs[-1]["item"] == url and crumbs[0]["item"] == "https://lusar.am/", route
        for href in meta.links:
            link = urlsplit(href)
            if not href.startswith("/") or href.startswith("//") or link.path.startswith(("/auth/", "/api/", "/manager/")):
                continue
            target = directory / unquote(link.path).strip("/")
            assert target.is_file() or (target / "index.html").is_file(), f"Broken internal link: {url} -> {href}"
    assert types.get("Store") == 2, "Missing store schema"
    assert types.get("Product") and types.get("Article") == 20, "Missing product/article schema"
    assert "Sitemap: https://lusar.am/sitemap.xml" in (directory / "robots.txt").read_text()
    print(json.dumps({"indexablePages": len(urls), "schemaTypes": types}))


CHECK = '''<!doctype html><meta charset="utf-8"><output>WAIT</output><iframe width="1440" height="1000"></iframe>
<script>
(async()=>{const f=document.querySelector('iframe'),out=document.querySelector('output');let count=0;
const tick=()=>new Promise(r=>setTimeout(r,30));
try{localStorage.setItem('lusar-cookie-choice-v1','essential');
for(const path of PAGES){await new Promise(r=>{f.onload=r;f.src='/'+path});const d=f.contentDocument;
if(d.querySelector('main').textContent.includes('Страница в разработке'))throw Error('Placeholder: '+path);
for(const width of [320,390,1440]){f.style.width=width+'px';await tick();
for(const lang of ['ru','hy','en']){const picker=d.querySelector('#language');picker.value=lang;picker.dispatchEvent(new f.contentWindow.Event('change'));
for(const theme of ['dark','light']){d.documentElement.dataset.theme=theme;await tick();
if(d.documentElement.scrollWidth>d.documentElement.clientWidth+1)throw Error('Overflow: '+path+':'+width+':'+lang);
for(const el of d.querySelectorAll('main h1,main h2,main p,main a')){const rect=el.getBoundingClientRect();
if(rect.width&&rect.right>d.documentElement.clientWidth+1)throw Error('Text overflow: '+path);}
count++;}}}}
out.textContent='PASS:'+count;
}catch(e){out.textContent='FAIL: '+e.message;}})();</script>'''.replace("PAGES", json.dumps(PAGES))


class Handler(serve.Handler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        if self.path != "/launch-check":
            return super().do_GET()
        body = CHECK.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=serve.ROOT / "dist")
    parser.add_argument("--static-only", action="store_true")
    parser.add_argument("--screenshots", type=Path)
    args = parser.parse_args()
    check_static(args.directory)
    if args.static_only:
        return
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temporary:
        serve.DATABASE = Path(temporary) / "isolated.sqlite"
        with serve.ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
            threading.Thread(target=server.serve_forever, daemon=True).start()
            common = [str(EDGE), "--headless=new", "--no-first-run", "--disable-gpu", "--force-prefers-reduced-motion"]
            origin = f"http://127.0.0.1:{server.server_port}"
            try:
                result = subprocess.run(common + ["--user-data-dir=" + temporary + "/browser", "--window-size=1700,1100", "--virtual-time-budget=25000", "--dump-dom", origin + "/launch-check"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
                output = result.stdout.partition("<output>")[2].partition("</output>")[0]
                assert output == "PASS:108", output or result.stderr[-300:]
                print(output)
                if args.screenshots:
                    args.screenshots.mkdir(parents=True, exist_ok=True)
                    target = args.screenshots.resolve() / "services.png"
                    subprocess.run(common + ["--user-data-dir=" + temporary + "/screenshot", "--window-size=1440,1000", "--virtual-time-budget=3000", "--screenshot=" + str(target), origin + "/services"], capture_output=True, timeout=30, check=True)
            finally:
                server.shutdown()


if __name__ == "__main__":
    main()
