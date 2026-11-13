(() => {
  function basketCount() {
    let total=0;
    try {
      const cart=JSON.parse(localStorage.getItem('lusar-cart'));
      if(cart && typeof cart==='object' && !Array.isArray(cart)) total=Object.values(cart).reduce((sum,q)=>sum+(Number.isSafeInteger(q)&&q>0&&q<=999?q:0),0);
    } catch {}
    document.querySelectorAll('[data-cart-total]').forEach(badge=>{badge.textContent=String(total);badge.hidden=total===0;});
  }
  basketCount();
  ['lusar-shopping-change','lusar-account-change','lusar-shopping-ready'].forEach(name=>document.addEventListener(name,basketCount));
  window.addEventListener('storage',event=>{if(event.key==='lusar-cart')basketCount();});
  window.addEventListener('pageshow',basketCount);
  document.querySelectorAll('[data-journal-filter]').forEach(button=>button.addEventListener('click',()=>{
    document.querySelectorAll('[data-journal-filter]').forEach(item=>item.setAttribute('aria-pressed',String(item===button)));
    document.querySelectorAll('[data-journal-category]').forEach(item=>item.hidden=button.dataset.journalFilter!=='all'&&item.dataset.journalCategory!==button.dataset.journalFilter);
  }));
  document.querySelectorAll('[data-copy-promo]').forEach(button=>button.addEventListener('click',async()=>{
    const status=document.querySelector('#copy-promo-status'),tr=value=>window.lusarLocale?.text(value)||value;
    try {await navigator.clipboard.writeText(button.dataset.copyPromo);status.textContent=tr('Промокод Happy скопирован.');}
    catch {status.textContent=tr('Промокод: Happy. Введите его в корзине.');}
  }));
})();
