(() => {
  let account = {authenticated:false, available:false, loading:true};
  let saving = null, refreshing = null, queued = false, dirty = false, timer;
  const ownerKey = 'lusar-cart-owner', versionKey = 'lusar-cart-version';
  const read = (key, fallback) => {try {return JSON.parse(localStorage.getItem(key)) || fallback;} catch {return fallback;}};
  const notify = () => document.dispatchEvent(new CustomEvent('lusar-account-change', {detail:account}));
  const error = message => document.dispatchEvent(new CustomEvent('lusar-account-error', {detail:message}));
  function signalStorage() {
    for (const key of ['lusar-cart','lusar-favorites']) window.dispatchEvent(new StorageEvent('storage',{key}));
  }
  function install(data) {
    try {
      const previous = localStorage.getItem(ownerKey);
      if (data.authenticated) {
        const guest = !previous || previous === 'guest';
        const sameVersion = previous === data.profile.id && Number(localStorage.getItem(versionKey)) === data.state.version;
        const cart = {...(sameVersion?read('lusar-cart',{}):data.state.cart)}, favorites = new Set(sameVersion?read('lusar-favorites',[]):data.state.favorites);
        if (guest) {
          for (const [id,count] of Object.entries(read('lusar-cart',{}))) if (Number.isSafeInteger(count) && count > 0 && count <= 999) cart[id] = Math.max(cart[id] || 0,count);
          for (const id of read('lusar-favorites',[])) if (typeof id === 'string') favorites.add(id);
        }
        localStorage.setItem('lusar-cart',JSON.stringify(cart));
        localStorage.setItem('lusar-favorites',JSON.stringify([...favorites].slice(0,100)));
        localStorage.setItem(ownerKey,data.profile.id);
        localStorage.setItem(versionKey,String(data.state.version));
        queued = (guest || sameVersion) && (JSON.stringify(cart)!==JSON.stringify(data.state.cart) || JSON.stringify([...favorites])!==JSON.stringify(data.state.favorites));
      } else {
        if (previous && previous !== 'guest') {
          localStorage.removeItem('lusar-cart'); localStorage.removeItem('lusar-favorites');
        }
        localStorage.setItem(ownerKey,'guest'); localStorage.removeItem(versionKey);
      }
    } catch {error('Браузер не сохранил корзину. Проверьте настройки хранения данных.');}
    account = {...data, loading:false};
    for (const link of document.querySelectorAll('a[href="/account"]')) link.toggleAttribute('data-signed-in',!!data.authenticated);
    signalStorage(); notify();
  }
  async function request(path, data) {
    const response = await fetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-Lusar-CSRF':account.csrfToken || ''},body:JSON.stringify(data)});
    const result = await response.json();
    if (!response.ok) {
      if (response.status===401) install({authenticated:false,available:account.available});
      throw Object.assign(Error(result.error || 'Не удалось сохранить изменения.'),{status:response.status});
    }
    return result;
  }
  async function flush() {
    clearTimeout(timer);
    if (!account.authenticated) return;
    if (saving) {if(dirty)queued=true;return saving;}
    if (!dirty && !queued) return;
    queued=false;dirty=false;
    const state={cart:read('lusar-cart',{}),favorites:read('lusar-favorites',[]),version:account.state.version};
    saving=request('/api/account/state',state).then(data=>{
      account={...data,loading:false};
      try {localStorage.setItem(versionKey,String(data.state.version));}catch{}
      notify();
    }).catch(problem=>{error(problem.message);throw problem;}).finally(()=>{saving=null;});
    try {await saving;} finally {if(queued) {queued=false;flush().catch(()=>{});}}
  }
  async function load() {
    if (saving) await saving;
    if(dirty)await flush();
    const response=await fetch('/api/account/me',{cache:'no-store'});
    if (!response.ok) throw Error('Личный кабинет временно недоступен. Попробуйте позже.');
    install(await response.json());
    if(queued) await flush();
    return account;
  }
  function refresh() {
    if(!refreshing)refreshing=load().finally(()=>{refreshing=null;});
    return refreshing;
  }
  window.lusarAccount={get value(){return account;},request,refresh,flush,
    async logout(){try{await flush();}catch{}const result=await request('/api/account/logout',{});install({authenticated:false,available:true});location.assign(result.logoutUrl);}};
  document.addEventListener('lusar-shopping-change',()=>{if(account.authenticated){dirty=true;clearTimeout(timer);timer=setTimeout(()=>flush().catch(()=>{}),400);}});
  document.addEventListener('visibilitychange',()=>{if(document.hidden&&account.authenticated&&dirty)flush().catch(()=>{});});
  window.addEventListener('focus',()=>refresh().catch(()=>{}));
  window.lusarAccount.ready=refresh().catch(problem=>{account={...account,loading:false};notify();error(problem.message);});
})();
