"""Verify journal content, total bag count, birthday approval and compact AI UI."""
import base64
import hashlib
import html
import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile
import threading
import xml.etree.ElementTree as ET
import serve
from check_checkout import EDGE

CHECK = r'''<!doctype html><meta charset="utf-8"><output>WAIT</output><iframe width="1440" height="900"></iframe><script>
const f=document.querySelector('iframe'),out=document.querySelector('output'),tick=()=>new Promise(r=>setTimeout(r,35));
const require=(v,m)=>{if(!v)throw Error(m)};
const open=path=>new Promise(r=>{f.onload=()=>r(f.contentDocument);f.src=path});
const until=async fn=>{for(let i=0;i<100;i++){if(fn())return;await tick()}throw Error('Timed out')};
const layout=d=>require(d.documentElement.scrollWidth<=f.contentWindow.innerWidth+1,'Overflow '+d.location.pathname);
async function card(number){const r=await fetch('/manager/orders/',{headers:{Authorization:AUTH}});require(r.ok,'Manager load');return new DOMParser().parseFromString(await r.text(),'text/html').getElementById(number)}
async function action(c,selector,values,expected=200){const form=c.querySelector(selector);require(form,'Missing manager form '+selector);const p=new URLSearchParams(new FormData(form));for(const[k,v]of Object.entries(values))p.set(k,v);const r=await fetch(form.getAttribute('action'),{method:'POST',headers:{Authorization:AUTH},body:p});require(r.status===expected,'Manager action '+r.status);return r}
(async()=>{try{
localStorage.clear();sessionStorage.setItem('lusar-first-order-promo-seen','1');localStorage.setItem('lusar-cookie-choice-v1','essential');
let d=await open('/catalog');const adds=[...d.querySelectorAll('[data-add]')];adds[0].click();adds[1].click();adds[1].click();
require(d.querySelector('[data-cart-total]').textContent==='3'&&d.querySelector('#cart-status').textContent.includes('3'),'Bag feedback counted only last SKU');
d=await open('/ai');require(d.querySelector('[data-cart-total]').textContent==='3','Global bag count missing on AI page');
for(const lang of ['ru','hy','en']){
 const picker=d.querySelector('#language');picker.value=lang;picker.dispatchEvent(new f.contentWindow.Event('change'));await tick();
 for(const selector of ['#ai-submit','.ai-telegram-action']){const r=d.querySelector(selector).getBoundingClientRect();require(r.top>=0&&r.bottom<=900,'AI action below first screen '+lang+' '+selector+' '+r.bottom)}
}
d=await open('/journal');require(d.querySelectorAll('.journal-grid>li').length===20,'Journal must have 20 articles');
for(const image of d.querySelectorAll('.journal-grid img')){
 image.scrollIntoView({block:'center'});await tick();
 // decode also waits for lazy images to reach the newly scrolled viewport.
 await until(()=>image.complete);require(image.naturalWidth>0,'Editorial image failed');
 const r=image.getBoundingClientRect();require(r.width>50&&r.height>50&&r.height<650,'Editorial image frame is empty or stretched: '+r.height);
}

d.querySelector('[data-journal-filter="outside"]').click();require([...d.querySelectorAll('[data-journal-category]:not([hidden])')].length===3,'Journal topic filter failed');
d.querySelector('[data-journal-filter="all"]').click();require(d.querySelectorAll('[data-journal-category]:not([hidden])').length===20,'Journal reset failed');
for(const path of ['/journal','/journal/yerevan-layers','/rooms','/rooms/outdoors','/offers','/ai']){
 d=await open(path);
 for(const width of [320,390,768,1440,1920]){f.width=String(width);await tick();
  for(const lang of ['ru','hy','en']){d.querySelector('#language').value=lang;d.querySelector('#language').dispatchEvent(new f.contentWindow.Event('change'));await tick();
   for(const theme of ['dark','light']){d.documentElement.dataset.theme=theme;layout(d)}
  }
 }
}
f.width='390';localStorage.setItem('lusar-language','ru');localStorage.setItem('lusar-cart',JSON.stringify({[PRODUCT_ID]:1}));
d=await open('/checkout');const form=d.querySelector('#checkout');form.elements.name.value='Birthday check';form.elements.phone.value='+37400000000';form.elements.promo.value='hApPy';form.elements.promo.dispatchEvent(new f.contentWindow.Event('input'));
require(form.elements.promo.validity.valid&&d.querySelector('#promo-total').textContent.includes('до оплаты'),'Birthday explanation missing');
form.requestSubmit();await until(()=>f.contentWindow.location.pathname==='/checkout/received');d=f.contentDocument;await until(()=>d.querySelector('#receipt-number')?.textContent.includes('LS-'));
const number=d.querySelector('#receipt-number').textContent.match(/LS-[A-F0-9]+/)[0];let c=await card(number);
const statusForm='form[action="/manager/orders/status"]', adjustForm='form[action="/manager/orders/adjust"]';
await action(c,statusForm,{target:'in_progress'});c=await card(number);
require(c.textContent.includes('ожидает подтверждения'),'Manager birthday verification is missing');
await action(c,adjustForm,{action:'payment',value:'store'},409);
await action(c,adjustForm,{action:'verify_birthday',value:'confirmed'});c=await card(number);
await action(c,adjustForm,{action:'payment',value:'store'});c=await card(number);
require(c.textContent.includes('Оплачено'),'Verified birthday could not be paid');
out.textContent='PASS';
}catch(e){out.textContent='FAIL: '+e.message}})();
</script>'''

class Handler(serve.Handler):
    def log_message(self,*args): pass
    def do_GET(self):
        if self.path!='/storefront-check':return super().do_GET()
        body=CHECK.replace('AUTH',json.dumps(self.server.test_auth)).replace('PRODUCT_ID',json.dumps(self.server.test_product)).encode()
        self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)

def main():
    articles=json.loads((serve.ROOT/'editorial.json').read_text(encoding='utf-8'))
    assert len(articles)==len({a['slug'] for a in articles})==20
    hashes=[]
    sitemap={e.text for e in ET.parse(serve.ROOT/'dist/sitemap.xml').getroot().iter() if e.tag.endswith('loc')}
    for item in articles:
        hashes.append(hashlib.sha256((serve.ROOT/'editorial'/f"{item['slug']}.webp").read_bytes()).hexdigest())
        assert len(item['title'])==3 and len(item['body'])==3
        assert all(len(p)==3 and min(map(len,p))>90 for p in item['body'])
        assert 'https://lusar.am/journal/'+item['slug'] in sitemap
        page=(serve.ROOT/'dist/journal'/item['slug']/'index.html').read_text(encoding='utf-8')
        assert 'application/ld+json' in page and 'name="description"' in page
    assert len(set(hashes))==20
    for code in ['Happy','happy','HAPPY','hApPy']:
        amount=serve.order_amount([{'unitPrice':10000,'quantity':1}],code)
        assert amount['total']==9000
    order={'promo':'HAPPY','total':9000}
    try:serve.apply_adjustment(order,'in_progress','payment','store',0)
    except ValueError:pass
    else:raise AssertionError('Unverified birthday paid')
    serve.apply_adjustment(order,'in_progress','verify_birthday','confirmed',0)
    serve.apply_adjustment(order,'in_progress','payment','store',0)
    assert order['payment']['amount']==9000
    data=json.loads(serve.CATALOG.read_text(encoding='utf-8-sig'))
    product=next(p for p in data['products'] if p['price'] is not None)
    password=secrets.token_urlsafe(20);os.environ['LUSAR_LOCAL_MANAGER_PASSWORD']=password
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        serve.DATABASE=Path(tmp)/'orders.sqlite'
        with serve.ThreadingHTTPServer(('127.0.0.1',0),Handler) as server:
            server.test_auth='Basic '+base64.b64encode(('manager:'+password).encode()).decode()
            server.test_product=product['id'];threading.Thread(target=server.serve_forever,daemon=True).start()
            try:
                result=subprocess.run([str(EDGE),'--headless=new','--no-first-run','--disable-gpu','--force-prefers-reduced-motion','--user-data-dir='+tmp+'/browser','--window-size=2000,1100','--virtual-time-budget=35000','--dump-dom',f'http://127.0.0.1:{server.server_port}/storefront-check'],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=60)
                output=html.unescape(result.stdout.partition('<output>')[2].partition('</output>')[0])
                if output!='PASS':raise RuntimeError(output or result.stderr[-500:])
            finally:server.shutdown()
    print('20 unique illustrated trilingual articles, SEO metadata, journal filters, 180 responsive states, compact AI, total bag count and birthday approval/payment passed.')

if __name__=='__main__':main()
