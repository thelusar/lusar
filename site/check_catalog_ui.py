"""Check catalog filtering, layout choices and the mobile filter drawer."""
import html
import json
from pathlib import Path
import subprocess
import tempfile
import threading

import serve
from check_checkout import EDGE

CHECK = r'''<!doctype html><meta charset="utf-8"><output>WAIT</output><iframe width="1440" height="1000"></iframe>
<script>
(async()=>{const f=document.querySelector('iframe'),out=document.querySelector('output');
const require=(ok,message)=>{if(!ok)throw Error(message)};
const tick=()=>new Promise(r=>setTimeout(r,35));
async function waitFor(check){for(let attempt=0;attempt<30&&!check();attempt++)await tick();}
async function open(path){await new Promise(r=>{f.onload=r;f.src=path});await tick();return f.contentDocument;}
function input(d,name,value){const field=d.querySelector('#product-filters').elements.namedItem(name);field.value=value;field.dispatchEvent(new f.contentWindow.Event('input',{bubbles:true}));}
const visible=d=>[...d.querySelectorAll('.product-tiles>li:not([hidden])')];
localStorage.setItem('lusar-cookie-choice-v1','essential');sessionStorage.setItem('lusar-first-order-promo-seen','1');
localStorage.removeItem('lusar-catalog-view');localStorage.setItem('lusar-language','ru');
try{
let d=await open('/catalog'),w=f.contentWindow,root=d.querySelector('.catalog-browser'),form=d.querySelector('#product-filters');
require(root&&visible(d).length>3,'Missing catalog or products');
require(d.querySelector('.catalog-sidebar').getBoundingClientRect().right<d.querySelector('.catalog-results').getBoundingClientRect().left,'Sidebar is not left of results');
const categoryRects=[...d.querySelectorAll('.catalog-categories a')].map(e=>e.getBoundingClientRect());
require(categoryRects.every(r=>Math.abs(r.left-categoryRects[0].left)<1&&Math.abs(r.width-categoryRects[0].width)<1),'Category links are not aligned');
require(d.querySelector('.catalog-tools').getBoundingClientRect().bottom<d.querySelector('.product-tiles').getBoundingClientRect().top,'Toolbar is not above products');
const count=visible(d).length, first=visible(d)[0], term=first.dataset.search.split(' ')[0];
input(d,'q',term);require(visible(d).every(e=>e.dataset.search.toLocaleLowerCase().includes(term.toLocaleLowerCase())),'Search failed');
input(d,'q','unlikely-no-match-9876');require(visible(d).length===0&&!d.querySelector('#catalog-empty').hidden,'Empty result state missing');
form.reset();await tick();require(visible(d).length===count,'Reset did not restore products');
input(d,'minimum','20000');require(visible(d).every(e=>e.dataset.price!==''&&Number(e.dataset.price)>=20000),'Minimum price failed');
input(d,'maximum','40000');require(visible(d).every(e=>Number(e.dataset.price)<=40000),'Maximum price failed');
input(d,'sort','high');let prices=visible(d).map(e=>Number(e.dataset.price));require(prices.every((p,i)=>i===0||p<=prices[i-1]),'Descending sort failed');
form.reset();await tick();input(d,'sort','low');prices=visible(d).filter(e=>e.dataset.price!=='').map(e=>Number(e.dataset.price));require(prices.every((p,i)=>!i||p>=prices[i-1]),'Ascending sort failed');
input(d,'sort','name');require(visible(d).length===count,'Name sort lost products');
const facet=form.elements.namedItem('socket');if(facet){input(d,'socket',facet.options[1].value);require(visible(d).every(e=>e.dataset.socket===facet.value),'Socket filter failed');}
form.reset();await tick();
d.querySelector('[data-catalog-view="list"]').click();require(root.dataset.view==='list','List view failed');
const category=d.querySelector('.catalog-categories a[href^="/catalog/category/"]').getAttribute('href');
d=await open(category);require(d.querySelector('.catalog-browser').dataset.view==='list','View preference lost on category navigation');
require(d.querySelector('.catalog-categories a[aria-current="page"]').getAttribute('href')===category,'Active category missing');
d=await open('/catalog?minimum=20000&sort=high');require(visible(d).every(e=>Number(e.dataset.price)>=20000),'URL filter not restored');
d.querySelector('#product-filters').reset();await tick();
let states=0;
for(const width of [320,390,768,1024,1440,1920]){
 f.width=width;await tick();
 for(const language of ['ru','hy','en']){
  d.querySelector('#language').value=language;d.querySelector('#language').dispatchEvent(new f.contentWindow.Event('change',{bubbles:true}));
  for(const theme of ['dark','light']){
   d.documentElement.dataset.theme=theme;
   for(const view of ['grid','compact','list']){
    d.querySelector(`[data-catalog-view="${view}"]`).click();await tick();
    require(d.documentElement.scrollWidth<=Number(width)+1,'Page overflow '+width+'/'+language+'/'+view);
    const cards=visible(d).map(e=>e.getBoundingClientRect());
    require(cards.every(r=>r.width>0&&r.right<=Number(width)+1),'Card overflow '+width+'/'+language+'/'+view);
    require(visible(d).length===count,'Changing view lost products');states++;
   }
  }
 }
}
f.width=390;await tick();d.querySelector('.catalog-filter-trigger').click();await tick();
root=d.querySelector('.catalog-browser');const sidebar=d.querySelector('#catalog-sidebar');
require(root.dataset.filtersOpen==='true'&&sidebar.getAttribute('aria-modal')==='true','Mobile drawer did not open');
require(d.querySelector('.catalog-results').inert,'Background remains interactive');
input(d,'minimum','20000');require(visible(d).every(e=>Number(e.dataset.price)>=20000),'Drawer filtering failed');
d.querySelector('.catalog-filter-backdrop').click();await tick();require(root.dataset.filtersOpen==='false'&&!d.querySelector('.catalog-results').inert,'Backdrop did not close drawer');
require(d.activeElement===d.querySelector('.catalog-filter-trigger'),'Focus was not restored');
d.querySelector('.catalog-filter-trigger').click();d.dispatchEvent(new f.contentWindow.KeyboardEvent('keydown',{key:'Escape',bubbles:true}));require(root.dataset.filtersOpen==='false','Escape failed');
d.querySelector('.catalog-filter-trigger').click();f.width=1440;await tick();
// Virtual time can defer iframe resize events; dispatch after its viewport has changed.
require(!f.contentWindow.matchMedia('(max-width:58rem)').matches,'Frame did not resize');
f.contentWindow.dispatchEvent(new f.contentWindow.Event('resize'));await waitFor(()=>root.dataset.filtersOpen==='false');
require(root.dataset.filtersOpen==='false'&&d.body.style.overflow!=='hidden','Resize left page locked');
d.querySelector('#product-filters').reset();await tick();
const add=visible(d)[0].querySelector('[data-add]');add.click();require(!d.querySelector('#cart-next').hidden,'Catalog add to bag failed');
const favorite=visible(d)[0].querySelector('[data-favorite]');favorite.click();require(favorite.getAttribute('aria-pressed')==='true','Catalog wishlist failed');
out.textContent='PASS:'+states;
}catch(e){out.textContent='FAIL: '+e.message;}})();
</script>'''


class Handler(serve.Handler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path != '/catalog-ui-check':
            return super().do_GET()
        body = CHECK.encode()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        serve.DATABASE = Path(tmp) / 'orders.sqlite'
        with serve.ThreadingHTTPServer(('127.0.0.1', 0), Handler) as server:
            threading.Thread(target=server.serve_forever, daemon=True).start()
            try:
                result = subprocess.run([str(EDGE), '--headless=new', '--no-first-run', '--disable-gpu',
                    '--force-prefers-reduced-motion', '--user-data-dir='+tmp+'/browser', '--window-size=2000,1100',
                    '--virtual-time-budget=35000', '--dump-dom', f'http://127.0.0.1:{server.server_port}/catalog-ui-check'],
                    capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
                output = html.unescape(result.stdout.partition('<output>')[2].partition('</output>')[0])
                if output != 'PASS:108':
                    raise RuntimeError(output or result.stderr[-500:])
                print('PASS: catalog filters, sorting, saved views, 108 responsive states, mobile drawer, bag and wishlist.')
            finally:
                server.shutdown()
