"""Exercise real account pages and checkout against a local signed identity provider."""
import argparse
import json
import subprocess
import tempfile
import threading
from pathlib import Path
from urllib.parse import urlencode, urlsplit

from check_accounts import Identity, Quiet, PRODUCT, accounts, serve
from check_checkout import EDGE

CHECK = r'''<!doctype html><meta charset="utf-8"><output>WAIT</output><iframe width="390" height="1050"></iframe>
<script>
const output=document.querySelector('output'), frame=document.querySelector('iframe');
const require=(value,message)=>{if(!value)throw Error(message);};
const tick=()=>new Promise(resolve=>setTimeout(resolve,40));
async function until(predicate){for(let i=0;i<150;i++){if(predicate())return;await tick();}throw Error('Timed out: '+predicate);}
async function open(path){await new Promise(resolve=>{frame.onload=resolve;frame.src=path;});const page=frame.contentDocument;await frame.contentWindow.lusarAccount.ready;await tick();return page;}
function layout(page){require(page.documentElement.scrollWidth<=page.documentElement.clientWidth+1,'Overflow: '+page.location.pathname+' '+frame.style.width+' '+page.documentElement.lang);}
async function sizes(page){for(const width of [320,390,1440]){frame.style.width=width+'px';await tick();for(const lang of ['ru','hy','en']){const picker=page.querySelector('#language');picker.value=lang;picker.dispatchEvent(new frame.contentWindow.Event('change'));await tick();layout(page);page.querySelector('#theme-toggle').click();layout(page);}}frame.style.width='390px';}
(async()=>{try{
 localStorage.clear();sessionStorage.clear();localStorage.setItem('lusar-cookie-choice-v1','essential');
 localStorage.setItem('lusar-cart',JSON.stringify({[ITEM.id]:1}));localStorage.setItem('lusar-favorites',JSON.stringify([ITEM.id]));
 let page=await open('/account');require(!page.querySelector('#account-guest').hidden,'Guest gate missing');await sizes(page);
 page=await open('/auth/start');await until(()=>!page.querySelector('#account-member').hidden);
 require(page.querySelector('#account-guest').hidden,'Guest gate visible after login');
 require(frame.contentWindow.lusarAccount.value.state.cart[ITEM.id]===1,'Guest bag not merged');
 require(frame.contentWindow.lusarAccount.value.state.favorites.includes(ITEM.id),'Guest favorites not merged');
 await sizes(page);
 page=await open('/account/settings');let form=page.querySelector('#account-profile-form');
 form.elements.name.value='Browser customer';form.elements.phone.value='+374 77 000000';form.requestSubmit();
 await until(()=>frame.contentWindow.lusarAccount.value.profile.name==='Browser customer');
 page=await open('/account/addresses');form=page.querySelector('#account-address-form');form.elements.label.value='Home';form.elements.address.value='Yerevan, Test address';form.requestSubmit();
 await until(()=>page.querySelector('.account-address'));
 require(frame.contentWindow.lusarAccount.value.profile.address==='Yerevan, Test address','Default address not saved');await sizes(page);
 page=await open('/checkout');form=page.querySelector('#checkout');
 require(form.elements.name.value==='Browser customer'&&form.elements.address.value==='Yerevan, Test address','Checkout autofill failed');
 require(!page.querySelector('#account-checkout-benefits').hidden,'Discount chooser missing');
 const mode=page.querySelector('#discount-mode');mode.value='first';mode.dispatchEvent(new frame.contentWindow.Event('change'));
 require(page.querySelector('#order-promo').disabled,'First discount allows a promo');
 require(Number(page.querySelector('#order-total').textContent.replace(/[^0-9]/g,''))===ITEM.price-Math.floor(ITEM.price/10),'First order total is wrong');
 await sizes(page);form.requestSubmit();
 await until(()=>frame.contentWindow.location.pathname==='/checkout/received');
 page=frame.contentDocument;await until(()=>page.querySelector('#receipt-number')?.textContent.includes('LS-'));
 const number=page.querySelector('#receipt-number').textContent;
 page=await open('/account/orders');await until(()=>page.querySelector('.account-order'));
 require(page.querySelector('.account-order').textContent.includes(number.match(/LS-[A-F0-9]{12}/)[0]),'Own order not shown');await sizes(page);
 require(Object.keys(frame.contentWindow.lusarAccount.value.state.cart).length===0,'Purchased bag still saved on account');
 page=await open('/account/loyalty');await until(()=>page.querySelector('#loyalty-first-order').textContent.length>0);require(frame.contentWindow.lusarAccount.value.loyalty.firstOrderReserved,'First discount not reserved');await sizes(page);
 // Remove and decrease saved shopping state, then reload; it must not reappear.
 localStorage.setItem('lusar-cart',JSON.stringify({[ITEM.id]:2}));frame.contentDocument.dispatchEvent(new frame.contentWindow.Event('lusar-shopping-change'));await frame.contentWindow.lusarAccount.flush();
 localStorage.setItem('lusar-cart',JSON.stringify({[ITEM.id]:1}));frame.contentDocument.dispatchEvent(new frame.contentWindow.Event('lusar-shopping-change'));await frame.contentWindow.lusarAccount.flush();
 page=await open('/account');require(frame.contentWindow.lusarAccount.value.state.cart[ITEM.id]===1,'Quantity decrease lost');
 await frame.contentWindow.lusarAccount.request('/api/account/logout',{});page=await open('/account');require(!page.querySelector('#account-guest').hidden,'Logout failed');require(!localStorage.getItem('lusar-cart'),'Private cached bag survived logout');
 page=await open('/auth/start');require(JSON.parse(localStorage.getItem('lusar-cart'))[ITEM.id]===1,'Saved bag not restored on next login');
 output.textContent='PASS';
}catch(error){output.textContent='FAIL: '+error.message;}})();
</script>'''


class BrowserIdentity(Identity):
    def authorization(self, state, nonce, verifier, **options):
        # Only the provider transport is replaced; callback validates a signed JWT.
        return '/auth/callback?' + urlencode({'state': state, 'code': 'local-browser-code'})


class Handler(Quiet):
    def do_GET(self):
        if urlsplit(self.path).path != '/account-ui-check':
            return super().do_GET()
        payload = CHECK.replace('ITEM', json.dumps(PRODUCT)).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', type=Path, default=EDGE)
    browser = parser.parse_args().browser
    with tempfile.TemporaryDirectory() as directory:
        serve.DATABASE = Path(directory) / 'orders.sqlite'
        with serve.ThreadingHTTPServer(('127.0.0.1', 0), Handler) as server:
            origin = 'http://127.0.0.1:' + str(server.server_port)
            config = accounts.Config('https://local-identity.example/', 'test-client', 'local-secret', origin)
            server.customer_accounts = accounts.Service(serve.DATABASE, config, BrowserIdentity(config))
            threading.Thread(target=server.serve_forever, daemon=True).start()
            try:
                result = subprocess.run([str(browser), '--headless=new', '--no-first-run', '--disable-gpu', '--user-data-dir='+directory+'/browser',
                                         '--window-size=1600,1100', '--virtual-time-budget=28000', '--dump-dom', origin+'/account-ui-check'],
                                        capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
            finally:
                server.shutdown()
        if '<output>PASS</output>' not in result.stdout:
            raise RuntimeError(result.stdout.partition('<output>')[2].partition('</output>')[0] or result.stderr[-500:])
    print('Local signed login, guest bag merge, profile, addresses, checkout discount/autofill, own history, logout and restored bag passed; account pages fit three widths, three languages and both themes.')


if __name__ == '__main__':
    main()
