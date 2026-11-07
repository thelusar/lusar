"""Exercise real account pages and checkout against a local signed identity provider."""
import argparse
import json
import os
import subprocess
import tempfile
import threading
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from unittest.mock import patch

from check_accounts import Client, Identity, Quiet, PRODUCT, accounts, serve
from check_checkout import EDGE

CHECK = r'''<!doctype html><meta charset="utf-8"><output>WAIT</output><iframe width="390" height="1050"></iframe>
<script>
const output=document.querySelector('output'), frame=document.querySelector('iframe');
const require=(value,message)=>{if(!value)throw Error(message);};
const tick=()=>new Promise(resolve=>setTimeout(resolve,40));
async function until(predicate,attempts=150){for(let i=0;i<attempts;i++){if(predicate())return;await tick();}throw Error('Timed out: '+predicate);}
async function open(path){await new Promise(resolve=>{frame.onload=resolve;frame.src=path;});const page=frame.contentDocument;await frame.contentWindow.lusarAccount?.ready;await tick();return page;}
async function follow(link){await new Promise(resolve=>{frame.onload=resolve;link.click();});const page=frame.contentDocument;await frame.contentWindow.lusarAccount.ready;return page;}
function layout(page){require(page.documentElement.scrollWidth<=page.documentElement.clientWidth+1,'Overflow: '+page.location.pathname+' '+frame.style.width+' '+page.documentElement.lang);}
async function sizes(page){for(const width of [320,390,1440]){frame.style.width=width+'px';await tick();for(const lang of ['ru','hy','en']){const picker=page.querySelector('#language');picker.value=lang;picker.dispatchEvent(new frame.contentWindow.Event('change'));await tick();layout(page);page.querySelector('#theme-toggle').click();layout(page);}}frame.style.width='390px';}
async function staffSizes(page){for(const width of [320,390,720,1024,1440]){frame.style.width=width+'px';await tick();layout(page);page.querySelector('#theme-toggle').click();layout(page);page.querySelector('#theme-toggle').click();}frame.style.width='390px';}
async function submit(form,button){await new Promise(resolve=>{frame.onload=resolve;form.requestSubmit(button);});return frame.contentDocument;}
(async()=>{try{
 localStorage.clear();sessionStorage.clear();localStorage.setItem('lusar-cookie-choice-v1','essential');
 localStorage.setItem('lusar-cart',JSON.stringify({[ITEM.id]:1}));localStorage.setItem('lusar-favorites',JSON.stringify([ITEM.id]));
 let guestBag=await open('/cart');require(guestBag.querySelector('.account-nav').hidden,'Guest bag exposes the account menu');
 let page=await open('/account');require(!page.querySelector('#account-guest').hidden,'Guest gate missing');await sizes(page);
 page=await open('/auth/start');await until(()=>!page.querySelector('#account-member').hidden);
 require(page.querySelector('#account-guest').hidden,'Guest gate visible after login');
 require(page.querySelector('#account-avatar').textContent==='AL'&&page.querySelector('.account-nav [aria-current="page"] svg'),'Account identity or selected navigation is missing');
 require(frame.contentWindow.lusarAccount.value.state.cart[ITEM.id]===1,'Guest bag not merged');
 require(frame.contentWindow.lusarAccount.value.state.favorites.includes(ITEM.id),'Guest favorites not merged');
 await sizes(page);
 const sidebar=page.querySelector('.account-nav');
 sidebar.querySelector('[data-account-tab="settings"]').click();
 require(page.location.pathname==='/account/settings'&&page.querySelector('.account-nav')===sidebar,'Account navigation reloaded the shell');
 require(page.querySelector('#saved-addresses')&&page.querySelector('#account-profile-form'),'Profile and addresses are split');
 require(page.activeElement.id==='account-view-title','Account navigation did not move focus to the new heading');
 let form=page.querySelector('#account-profile-form');
 form.elements.name.value='Browser customer';form.elements.phone.value='+374 77 000000';form.requestSubmit();
 await until(()=>frame.contentWindow.lusarAccount.value.profile.name==='Browser customer');
 require(page.querySelector('#account-avatar').textContent==='BC'&&page.querySelector('#account-nav-name').textContent==='Browser customer','Account identity did not refresh after editing the name');
 form=page.querySelector('#account-address-form');form.elements.label.value='Home';form.elements.address.value='Yerevan, Test address';form.requestSubmit();
 await until(()=>page.querySelector('.account-address'));
 require(frame.contentWindow.lusarAccount.value.profile.address==='Yerevan, Test address','Default address not saved');await sizes(page);
 frame.contentWindow.history.back();await until(()=>page.location.pathname==='/account'&&page.querySelector('.account-benefits'));
 require(page.querySelector('.account-nav')===sidebar,'Back replaced the account navigation');
 page=await open('/account/addresses');
 require(page.querySelector('#account-profile-form')&&page.querySelector('#account-address-editor').open,'Legacy address link lost the address section');
 frame.style.width='1440px';await tick();
 const profileBounds=page.querySelector('#account-profile-form').getBoundingClientRect();
 const addressBounds=page.querySelector('#saved-addresses').getBoundingClientRect();
 require(profileBounds.top===addressBounds.top&&profileBounds.bottom===addressBounds.bottom&&Math.abs(profileBounds.width-addressBounds.width)<1,'Profile cards do not align');
 page=await follow(page.querySelector('.account-nav a[href="/cart"]'));
 require(!page.querySelector('.account-nav').hidden&&page.querySelector('.account-nav [aria-current="page"]').pathname==='/cart','Signed-in bag lost the account navigation');
 await sizes(page);
 page=await follow(page.querySelector('.account-nav a[href="/favorites"]'));
 require(page.querySelector('.account-nav [aria-current="page"]').pathname==='/favorites','Wishlist lost the account navigation');
 require(page.querySelectorAll('.wishlist-toolbar a[href="/cart"]').length===1&&page.querySelector('.wishlist-remove svg'),'Wishlist actions are duplicated or missing');
 await sizes(page);
 page=await follow(page.querySelector('.account-nav a[href="/account/settings"]'));
 require(page.querySelector('#account-profile-form'),'Cannot return from shopping to the profile');
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
 const orderId=number.match(/^LS-[0-9]{6}$/)[0];
 page=await open('/account/orders');await until(()=>page.querySelector('.account-order'));
 const customerOrder=page.querySelector('.account-order');
 require(customerOrder.querySelector('summary').textContent.includes(orderId)&&!customerOrder.open,'Order summary missing or open by default');
 customerOrder.querySelector('summary').click();
 require(customerOrder.open&&customerOrder.querySelector('.account-order-body li'),'Order details did not expand');
 await sizes(page);
 require(Object.keys(frame.contentWindow.lusarAccount.value.state.cart).length===0,'Purchased bag still saved on account');
 page=await open('/manager/orders/#'+orderId);
 const order=page.getElementById(orderId);
 const drawer=page.querySelector('#staff-order-drawer');
 require(order.open&&drawer.open&&drawer.querySelector('h2').textContent===orderId,'Telegram order link did not open the drawer');
 const detailTitles=[...drawer.querySelectorAll('section.staff-detail-card h3')].map(title=>title.textContent);
 require(detailTitles.join('|')==='Контакты клиента|Состав заказа|Оплата и возвраты','Order drawer sections are missing or out of order');
 require(drawer.querySelector('.staff-detail-header .staff-order-recap'),'Order total is missing from the drawer summary');
 await staffSizes(page);
 drawer.querySelector('button').click();
 require(!drawer.open&&!order.open,'Closing the drawer did not restore the order row');
 require(page.querySelector('.staff-profile .staff-avatar')&&page.querySelector('.staff-metric[data-tone="new"] > strong').textContent==='1','Overview or profile missing');
 require(!page.querySelector('.staff-topbar')&&page.querySelector('.staff-sidebar .staff-profile'),'Profile must be in the sidebar');
 require(page.querySelector('#staff-team-summary .staff-avatar-stack .staff-avatar'),'Admin team avatars missing');
 const days=page.querySelector('#staff-days');
 require(days.querySelector('[data-days-period="7"]').tBodies[0].rows.length===7,'Weekly data missing');
 page.querySelector('[data-period="30"]').click();
 require(!page.querySelector('[data-chart-period="30"]').hidden&&page.querySelector('[data-chart-period="7"]').hidden,'Chart period did not switch');
 const chartHeight=page.querySelector('.staff-chart').offsetHeight;
 page.querySelector('[data-chart-period="30"] .staff-days-button').click();
 require(days.open&&!days.querySelector('[data-days-period="30"]').hidden&&days.querySelector('[data-days-period="30"]').tBodies[0].rows.length===30,'Daily dialog did not use the selected period');
 require(chartHeight===page.querySelector('.staff-chart').offsetHeight,'Daily data moved the dashboard layout');
 days.querySelector('button').click();await until(()=>!days.open);
 frame.style.width='1440px';await tick();
 page.querySelector('.staff-queue a').click();
 require(drawer.open&&drawer.querySelector('h2').textContent===orderId,'Queue link did not open the drawer');
 const outside={clientX:5,clientY:50,bubbles:true}, inside={clientX:1430,clientY:50,bubbles:true};
 const pointer=(type, position)=>drawer.dispatchEvent(new frame.contentWindow.PointerEvent(type,position));
 pointer('pointerdown',inside);pointer('click',outside);
 require(drawer.open,'Dragging from the drawer onto the backdrop closed it');
 pointer('pointerdown',outside);pointer('click',outside);
 require(!drawer.open&&!order.open,'Clicking the backdrop did not close the order');
 frame.style.width='390px';await tick();
 const search=page.querySelector('#staff-order-search');
 search.value='does not exist';search.dispatchEvent(new frame.contentWindow.Event('input'));
 require(order.hidden&&!page.querySelector('#staff-no-match').hidden,'Search empty state missing');
 page.querySelector('#staff-reset').click();
 require(!order.hidden,'Reset did not restore the order');
 page.querySelector('[data-filter="completed"]').click();require(order.hidden,'Status filter failed');
 page.querySelector('[data-filter="new"]').click();require(!order.hidden,'New order filter failed');
 await staffSizes(page);
 order.querySelector('summary').click();
 const statusForm=page.querySelector('form[action="/manager/orders/status"]');
 require(statusForm&&page.querySelector('a[href="/manager/access"]'),'Administrator order controls missing');
 const selectStatus=(picker,status)=>{picker.value=status;picker.dispatchEvent(new frame.contentWindow.Event('change',{bubbles:true}));};
 const picker=statusForm.elements.target;
 selectStatus(picker,'cancelled');
 require(page.querySelector('#staff-cancel').open,'Cancellation confirmation missing');
 page.querySelector('#staff-cancel button[value="back"]').click();
 await until(()=>!picker.disabled);
 require(picker.value===''&&order.dataset.status==='new','Dismissed cancellation changed the order');
 selectStatus(picker,'in_progress');
 await until(()=>page.querySelector('#staff-save-feedback').textContent.includes(orderId));
 require(page.getElementById(orderId).hidden&&page.querySelector('[data-filter="in_progress"] strong').textContent==='1','Autosave did not update the active filter or counts');
 require(drawer.open&&page.getElementById(orderId).open&&drawer.querySelector('.staff-history').textContent.includes('Новая заявка → В процессе'),'Autosave lost the open order or audit trail');
 require(page.querySelector('.staff-metric[data-tone="in_progress"] > strong').textContent==='1'&&!page.querySelector('.staff-queue'),'Overview did not refresh after autosave');
 require(!page.querySelector('[data-chart-period="30"]').hidden,'Status save reset the chart period');
 drawer.querySelector('button').click();
 page.querySelector('[data-filter="in_progress"]').click();
 require(!page.getElementById(orderId).hidden,'Updated order missing from the next filter');
 page=await open('/manager/orders/?view=orders&status=new');
 require(!page.querySelector('#staff-overview')&&page.getElementById(orderId).hidden,'Full order list did not apply the dashboard filter');
 require(!page.querySelector('.staff-heading')&&page.querySelector('h1#orders-title'),'Orders should start with the list');
 const sectionNav=page.querySelector('.staff-section-nav');
 const themeToggle=page.querySelector('#theme-toggle');
 const workspace=page.querySelector('#staff-main');
 const navLink=label=>[...sectionNav.querySelectorAll('a')].find(link=>link.textContent===label);
 const activeSection=label=>navLink(label).getAttribute('aria-current')==='page'&&!workspace.hasAttribute('aria-busy');
 navLink('Обзор').click();
 await until(()=>activeSection('Обзор')&&page.querySelector('#staff-overview'));
 require(frame.contentDocument===page&&page.querySelector('#theme-toggle')===themeToggle,'Section navigation rebuilt the page shell');
 navLink('Сотрудники').click();
 navLink('Заказы').click();
 await until(()=>activeSection('Заказы')&&frame.contentWindow.location.search==='?view=orders');
 await tick();
 require(!page.querySelector('.staff-grant'),'An older request replaced the latest section');
 frame.contentWindow.history.back();
 await until(()=>activeSection('Обзор')&&page.querySelector('#staff-overview'));
 frame.contentWindow.history.forward();
 await until(()=>activeSection('Заказы')&&!page.querySelector('#staff-overview'));
 page.getElementById(orderId).querySelector('summary').click();
 require(page.querySelector('#staff-order-drawer').open,'Order drawer did not initialize after navigation');
 page.querySelector('#staff-order-drawer button').click();
 navLink('Импорт и экспорт').click();
 await until(()=>activeSection('Импорт и экспорт')&&page.querySelector('[data-order-export]'));
 require(frame.contentDocument===page&&page.querySelector('#theme-toggle')===themeToggle,'Order transfer rebuilt the page shell');
 const selectedExport=page.querySelector('[data-order-export] [value="selected"]');
 const format=page.querySelector('[data-order-export] select[name="format"]');
 require([...format.options].map(option=>option.value).join('|')==='xlsx|pdf|csv','Export formats are missing');
 require(selectedExport.disabled,'Empty selection can be exported');
 page.querySelector('[data-select-page]').click();
 require(!selectedExport.disabled&&selectedExport.textContent.includes('(1)'),'Selecting all orders did not enable export');
 await staffSizes(page);
 navLink('Сотрудники').click();
 await until(()=>activeSection('Сотрудники')&&page.querySelector('.staff-grant'));
 require(frame.contentDocument===page&&page.querySelector('.staff-section-nav')===sectionNav,'Staff section rebuilt the sidebar');
 require(!page.querySelector('.staff-heading'),'Staff should start with the work panels');
 require(page.querySelector('.staff-person').textContent.includes('Ваш аккаунт'),'Owner missing from staff list');
 form=page.querySelector('.staff-grant form');
 form.elements.account.value=EMPLOYEE;
 page=await submit(form);
 require(page.querySelector('.staff-role-edit')&&page.querySelector('.staff-notice'),'Staff grant failed');
 page.querySelector('.staff-role-edit').open=true;
 form=page.querySelector('.staff-role-actions form');form.elements.role.value='admin';
 page=await submit(form);
 require(page.querySelector('.staff-person:last-child .staff-badge').textContent==='Администратор','Role change failed');
 page.querySelector('.staff-role-edit').open=true;page.querySelector('.staff-revoke').open=true;
 await staffSizes(page);
 const revoke=page.querySelector('.staff-revoke button');
 page=await submit(revoke.form,revoke);
 require(page.querySelectorAll('.staff-person').length===1&&page.querySelector('.staff-notice').textContent.includes('отозван'),'Revocation failed');
 page=await open('/account/loyalty');await until(()=>page.querySelector('#loyalty-first-order').textContent.length>0);require(frame.contentWindow.lusarAccount.value.loyalty.firstOrderReserved,'First discount not reserved');await sizes(page);
 // Remove and decrease saved shopping state, then reload; it must not reappear.
 localStorage.setItem('lusar-cart',JSON.stringify({[ITEM.id]:2}));frame.contentDocument.dispatchEvent(new frame.contentWindow.Event('lusar-shopping-change'));await frame.contentWindow.lusarAccount.flush();
 localStorage.setItem('lusar-cart',JSON.stringify({[ITEM.id]:1}));frame.contentDocument.dispatchEvent(new frame.contentWindow.Event('lusar-shopping-change'));await frame.contentWindow.lusarAccount.flush();
 page=await open('/account');require(frame.contentWindow.lusarAccount.value.state.cart[ITEM.id]===1,'Quantity decrease lost');
 await frame.contentWindow.lusarAccount.request('/api/account/logout',{});page=await open('/account');require(!page.querySelector('#account-guest').hidden,'Logout failed');require(!localStorage.getItem('lusar-cart'),'Private cached bag survived logout');
 page=await open('/manager/orders/#'+orderId);
 await new Promise(resolve=>{frame.onload=resolve;page.querySelector('[data-staff-login]').click();});
 require(frame.contentDocument.getElementById(orderId)?.open,'Order link was lost through login');
 page=frame.contentDocument;
 selectStatus(page.querySelector('.staff-status-picker select'),'cancelled');
 page.querySelector('#staff-cancel button[value="confirm"]').click();
 await until(()=>{
   const error=page.querySelector('[data-save-state][data-state="error"]');
   if(error)throw Error('Cancellation failed: '+error.textContent);
   return page.getElementById(orderId)?.dataset.status==='cancelled';
 },250);
 require(page.querySelector('.staff-history').textContent.includes('В процессе → Отменено'),'Confirmed cancellation was not recorded');
 const deleteOrder=page.querySelector('#staff-order-drawer [data-delete-order]');
 require(deleteOrder&&!deleteOrder.hidden,'Delete action missing from the administrator drawer');
 deleteOrder.click();
 const deleteDialog=page.querySelector('#staff-delete');
 require(deleteDialog.open&&deleteDialog.querySelector('[data-delete-number]').textContent===orderId,'Delete confirmation missing the order number');
 deleteDialog.querySelector('[data-keep-order]').click();
 require(!deleteDialog.open&&page.getElementById(orderId),'Declining deletion removed the order');
 deleteOrder.click();
 page=await submit(deleteDialog.querySelector('form'),deleteDialog.querySelector('button[value="yes"]'));
 require(!page.getElementById(orderId)&&page.querySelector('.staff-notice').textContent.includes('Заказ удалён'),'Confirmed deletion did not remove the order');
 page=await open('/account');require(JSON.parse(localStorage.getItem('lusar-cart'))[ITEM.id]===1,'Saved bag not restored on next login');
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
        payload = CHECK.replace('ITEM', json.dumps(PRODUCT)).replace('EMPLOYEE', json.dumps(self.server.employee)).encode()
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
                server.employee = Client(server).login('employee')['profile']['id']
                owner = Client(server).login()['profile']['id']
                with patch.dict(os.environ, {'LUSAR_STAFF_ADMIN_ID': owner}):
                    result = subprocess.run([str(browser), '--headless=new', '--no-first-run', '--disable-gpu', '--user-data-dir='+directory+'/browser',
                                             '--window-size=1600,1100', '--virtual-time-budget=28000', '--dump-dom', origin+'/account-ui-check'],
                                            capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
            finally:
                server.shutdown()
        if '<output>PASS</output>' not in result.stdout:
            raise RuntimeError(result.stdout.partition('<output>')[2].partition('</output>')[0] or result.stderr[-500:])
    print('Account and staff browser flows passed, including order deep links and filters, status and audit, role changes and revocation, and responsive layouts in both themes.')


if __name__ == '__main__':
    main()
