(() => {
  const content=document.querySelector('#account-content'), status=document.querySelector('#account-status');
  if(!content)return;
  const heading=document.querySelector('#account-view-title');
  const views={
    '/account':['overview','Личный кабинет'],
    '/account/orders':['orders','Мои заказы'],
    '/account/settings':['settings','Профиль'],
    '/account/addresses':['settings','Профиль'],
    '/account/loyalty':['loyalty','Мои скидки']
  };
  let renderedUser, renderedView, nextOffset=0;
  const money=value=>value===null?'Цена по запросу':new Intl.NumberFormat('ru-RU').format(value)+' ֏';
  const element=(tag,className,text)=>{const node=document.createElement(tag);if(className)node.className=className;if(text!==undefined)node.textContent=text;return node;};
  const tell=(text,focus=false)=>{status.textContent=text;if(focus)status.focus();};
  function stat(label,value){const card=element('div');card.append(element('span','',label),element('strong','',value));return card;}
  function showIdentity(profile){
    const name=profile.name.trim();
    const words=(name||profile.email.split('@')[0]).split(/\s+/u);
    const initials=words.length>1?Array.from(words[0])[0]+Array.from(words.at(-1))[0]:Array.from(words[0]).slice(0,2).join('');
    document.querySelector('#account-avatar').textContent=initials.toUpperCase();
    document.querySelector('#account-nav-name').textContent=name||profile.email;
    const email=document.querySelector('#account-nav-email');
    email.textContent=profile.email;email.hidden=!name;
  }
  async function orders(append=false,limit=20){
    const root=content.querySelector('#account-orders');
    const more=content.querySelector('#account-more-orders');
    if(!append)root.replaceChildren(element('p','account-loading','Загружаем заказы…'));
    let response,data;
    try{
      response=await fetch('/api/account/orders?offset='+(append?nextOffset:0),{cache:'no-store'});
      data=await response.json();
    }catch(problem){
      if(!root.isConnected)return;
      if(!append)root.replaceChildren();
      throw problem;
    }
    if(!root.isConnected)return;
    if(!append)root.replaceChildren();
    if(!response.ok)throw Error(data.error);
    if(!data.orders.length&&!append)root.append(document.querySelector('#account-empty-orders-template').content.cloneNode(true));
    const labels={new:'Новая заявка',in_progress:'В процессе',completed:'Выполнено',cancelled:'Отменено'};
    for(const order of data.orders.slice(0,limit)){
      const card=element('details','account-order');card.id=order.number;
      const head=element('summary','account-order-heading');
      const date=element('time','',new Date(order.created).toLocaleDateString('ru-RU',{timeZone:'Asia/Yerevan'}));date.dateTime=order.created;
      const identity=element('span','account-order-id');identity.append(element('strong','',order.number),date);
      const badge=element('span','order-status-badge',labels[order.status]);badge.dataset.status=order.status;
      const amount=money(order.returned?order.remainingTotal:order.total);
      const marker=element('span','account-order-toggle','+');marker.setAttribute('aria-hidden','true');
      head.append(identity,badge,element('strong','account-order-price',amount),marker);
      const details=element('div','account-order-body');
      const list=element('ul');
      for(const item of order.items){
        const row=element('li'), details=element('div'), name=element('span','',item.name);
        name.dataset.localeSource='';details.append(name);
        if(item.sku)details.append(element('small','','Артикул '+item.sku));
        row.append(details,element('span','account-order-quantity','×'+item.quantity));list.append(row);
      }
      details.append(list);
      if(order.returned)details.append(element('p','account-form-note','Итог после возврата'));
      if(order.paid)details.append(element('p','account-form-note','Оплата отмечена менеджером.'));
      card.append(head,details);
      card.open=location.hash.slice(1)===order.number||(limit===3&&data.orders.length===1);
      root.append(card);
    }
    nextOffset=data.nextOffset;
    if(more)more.hidden=!data.hasMore;
  }
  async function update(path,data){const result=await window.lusarAccount.request(path,data);await window.lusarAccount.refresh();return result;}
  function showAddresses(){
    const root=content.querySelector('#account-addresses');root.replaceChildren();
    const form=content.querySelector('#account-address-form');
    const editor=content.querySelector('#account-address-editor');
    const addresses=window.lusarAccount.value.profile.addresses;
    if(!addresses.length)root.append(element('p','account-empty','Сохранённых адресов пока нет.'));
    for(const [index,address] of addresses.entries()){
      const card=element('article','account-address'), label=element('h3','',address.label||'Адрес'), street=element('p','',address.address);
      if(address.label)label.dataset.localeSource='';street.dataset.localeSource='';card.append(label,street);
      if(index===0)card.append(element('span','address-primary','Основной адрес'));
      const actions=element('div','account-form-actions');
      const edit=element('button','text-button','Изменить');edit.type='button';edit.addEventListener('click',()=>{editor.open=true;form.elements.id.value=address.id;form.elements.label.value=address.label;form.elements.address.value=address.address;content.querySelector('#address-form-heading').textContent='Изменить адрес';content.querySelector('#account-address-cancel').hidden=false;form.elements.label.focus();});actions.append(edit);
      for(const [operation,label] of [['primary','Сделать основным'],['delete','Удалить']]){
        if(operation==='primary'&&index===0)continue;
        const button=element('button','text-button',label);button.type='button';button.addEventListener('click',async()=>{button.disabled=true;try{await update('/api/account/address',{operation,id:address.id});if(form.isConnected){if(operation==='delete'&&form.elements.id.value===address.id)form.reset();showAddresses();tell('Адреса обновлены.');}}catch(problem){if(form.isConnected)tell(problem.message,true);button.disabled=false;}});actions.append(button);
      }
      card.append(actions);root.append(card);
    }
  }
  function showLoyalty(){
    const benefits=window.lusarAccount.value.loyalty;
    content.querySelector('#loyalty-summary').replaceChildren(stat('Ваша скидка',benefits.discountPercent+'%'),stat('Накоплено',money(benefits.eligibleSpend)));
    const next=content.querySelector('#loyalty-next');next.replaceChildren();
    if(benefits.nextDiscountPercent!==null)next.append(element('span','','До следующего уровня'),' '+benefits.nextDiscountPercent+'% · '+money(benefits.remainingToNext));
    else next.textContent='У вас максимальная скидка.';
    content.querySelector('#loyalty-progress').value=benefits.remainingToNext===null?1:benefits.eligibleSpend/(benefits.eligibleSpend+benefits.remainingToNext);
    content.querySelector('#loyalty-first-order').textContent=benefits.firstOrderAvailable?'Доступна при оформлении. Применяется отдельно от других скидок и промокодов.':benefits.firstOrderReserved?'Скидка закреплена за вашей текущей заявкой.':'Предложение уже использовано.';
  }
  async function render(focus=false){
    const data=window.lusarAccount.value;
    document.querySelector('#account-loading').hidden=!data.loading;
    if(data.loading)return;
    const recovery=content.dataset.accountView==='recovery';
    document.querySelector('#account-guest').hidden=!!data.authenticated&&!recovery;
    document.querySelector('#account-member').hidden=!data.authenticated||recovery;
    const params=new URLSearchParams(location.search), note=document.querySelector('#account-auth-note');
    const errors={'verify-email':'Подтвердите email в письме и повторите вход.',failed:'Вход не подтверждён. Повторите попытку.'};
    note.textContent=!data.available?'Вход пока не подключён. Страница в разработке.':errors[params.get('auth_error')]||'';
    for(const link of document.querySelectorAll('[data-auth-link]')){
      link.setAttribute('aria-disabled',String(!data.available));
      const url=new URL(link.href);url.searchParams.set('lang',document.documentElement.lang);link.href=url;
    }
    document.querySelector('#account-recovery-note').hidden=!recovery;
    if(recovery){
      const email=document.querySelector('[data-auth-link][href*="/auth/start"]:not(.account-google)');
      const url=new URL(email.href);url.searchParams.set('screen','recovery');email.href=url;
    }
    if(recovery)return;
    if(!data.authenticated){renderedUser=null;return;}
    const [view,title]=views[location.pathname]||views['/account'];
    if(renderedUser===data.profile.id&&renderedView===view){showIdentity(data.profile);if(view==='loyalty')showLoyalty();return;}
    renderedUser=data.profile.id;renderedView=view;
    heading.textContent=title;
    document.title=(window.lusarLocale?.text(title)||title)+' — LUSAR';
    content.replaceChildren(document.querySelector('#account-'+view+'-template').content.cloneNode(true));
    showIdentity(data.profile);
    for(const link of document.querySelectorAll('.account-nav [data-account-tab]')){
      if(link.dataset.accountTab===view)link.setAttribute('aria-current','page');
      else link.removeAttribute('aria-current');
    }
    if(focus)heading.focus({preventScroll:true});
    if(view==='overview'){
      content.querySelector('#account-stats').append(stat('Ваша скидка',data.loyalty.discountPercent+'%'),stat('Накоплено',money(data.loyalty.eligibleSpend)));
      await orders(false,3);
    }else if(view==='orders'){
      content.querySelector('#account-more-orders').addEventListener('click',async event=>{const button=event.currentTarget;button.disabled=true;try{await orders(true);}catch(problem){tell(problem.message,true);}finally{button.disabled=false;}});
      await orders();
    }else if(view==='settings'){
      showAddresses();
      const form=content.querySelector('#account-address-form');
      const editor=content.querySelector('#account-address-editor');
      editor.open=!data.profile.addresses.length||location.pathname==='/account/addresses';
      form.addEventListener('reset',()=>{form.elements.id.value='';content.querySelector('#address-form-heading').textContent='Добавить адрес';content.querySelector('#account-address-cancel').hidden=true;});
      form.addEventListener('submit',async event=>{event.preventDefault();const button=form.querySelector('[type="submit"]');button.disabled=true;try{const fields=Object.fromEntries(new FormData(form));await update('/api/account/address',{...fields,operation:fields.id?'edit':'add'});if(form.isConnected){form.reset();showAddresses();editor.open=false;editor.querySelector('summary').focus({preventScroll:true});tell('Адрес сохранён.');}}catch(problem){if(form.isConnected)tell(problem.message,true);}finally{button.disabled=false;}});
      const profileForm=content.querySelector('#account-profile-form');
      for(const key of ['name','phone','email'])profileForm.elements[key].value=data.profile[key];
      profileForm.addEventListener('submit',async event=>{event.preventDefault();const button=profileForm.querySelector('button');button.disabled=true;try{await update('/api/account/profile',Object.fromEntries(new FormData(profileForm)));tell('Изменения сохранены.');}catch(problem){tell(problem.message,true);}finally{button.disabled=false;}});
    }else showLoyalty();
  }
  document.addEventListener('click',event=>{const link=event.target.closest('[data-auth-link]');if(link?.getAttribute('aria-disabled')==='true')event.preventDefault();});
  document.querySelector('#account-member').addEventListener('click',event=>{
    const link=event.target.closest('a[data-account-tab]');
    if(!link||event.defaultPrevented||event.button!==0||event.metaKey||event.ctrlKey||event.shiftKey||event.altKey)return;
    if(!window.lusarAccount.value.authenticated)return;
    event.preventDefault();
    if(location.pathname===link.pathname&&!location.hash)return;
    history.pushState(null,'',link.href);
    tell('');
    render(true).catch(problem=>tell(problem.message,true));
  });
  window.addEventListener('popstate',()=>{
    if(!Object.hasOwn(views,location.pathname))return;
    tell('');
    render().catch(problem=>tell(problem.message,true));
  });
  document.querySelector('[data-account-logout]').addEventListener('click',async event=>{const button=event.currentTarget;button.disabled=true;try{await window.lusarAccount.logout();}catch(problem){tell(problem.message,true);button.disabled=false;}});
  document.addEventListener('lusar-account-change',()=>render().catch(problem=>tell(problem.message,true)));
  document.addEventListener('lusar-account-error',event=>tell(event.detail));
  document.addEventListener('lusar-language-change',()=>{for(const link of document.querySelectorAll('[data-auth-link]')){const url=new URL(link.href);url.searchParams.set('lang',document.documentElement.lang);link.href=url;}});
  window.lusarAccount.ready.then(()=>render()).catch(problem=>tell(problem.message,true));
})();
