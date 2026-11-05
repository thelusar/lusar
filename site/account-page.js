(() => {
  const content=document.querySelector('#account-content'), status=document.querySelector('#account-status');
  if(!content)return;
  let renderedUser, renderedView, nextOffset=0;
  const money=value=>value===null?'Цена по запросу':new Intl.NumberFormat('ru-RU').format(value)+' ֏';
  const element=(tag,className,text)=>{const node=document.createElement(tag);if(className)node.className=className;if(text!==undefined)node.textContent=text;return node;};
  const tell=(text,focus=false)=>{status.textContent=text;if(focus)status.focus();};
  function stat(label,value){const card=element('div');card.append(element('span','',label),element('strong','',value));return card;}
  async function orders(append=false,limit=20){
    const response=await fetch('/api/account/orders?offset='+(append?nextOffset:0),{cache:'no-store'});
    const data=await response.json();if(!response.ok)throw Error(data.error);
    const root=content.querySelector('#account-orders');if(!append)root.replaceChildren();
    if(!data.orders.length&&!append)root.append(element('p','account-empty','У вас пока нет заказов.'));
    const labels={new:'Новая заявка',in_progress:'В процессе',completed:'Выполнено',cancelled:'Отменено'};
    for(const order of data.orders.slice(0,limit)){
      const card=element('article','account-order');card.id=order.number;
      const head=element('div','account-order-heading');
      head.append(element('h3','',order.number),element('span','order-status-badge',labels[order.status]));
      card.append(head);
      const date=element('time','',order.created.slice(0,10));date.dateTime=order.created;card.append(date);
      const list=element('ul');
      for(const item of order.items){const row=element('li');const name=element('span','',item.name);name.dataset.localeSource='';row.append(name,' · ',element('span','',String(item.quantity)));list.append(row);}
      card.append(list);
      const amount=element('p','account-order-total');amount.append(element('span','',order.returned?'Итог после возврата':'Сумма заказа'),' · ',element('strong','',money(order.returned?order.remainingTotal:order.total)));card.append(amount);
      if(order.paid)card.append(element('p','account-form-note','Оплата отмечена менеджером.'));
      root.append(card);
    }
    nextOffset=data.nextOffset;
    const more=content.querySelector('#account-more-orders');if(more)more.hidden=!data.hasMore;
  }
  async function update(path,data){const result=await window.lusarAccount.request(path,data);await window.lusarAccount.refresh();return result;}
  function showAddresses(){
    const root=content.querySelector('#account-addresses');root.replaceChildren();
    const form=content.querySelector('#account-address-form');
    const addresses=window.lusarAccount.value.profile.addresses;
    if(!addresses.length)root.append(element('p','account-empty','Сохранённых адресов пока нет.'));
    for(const [index,address] of addresses.entries()){
      const card=element('article','account-address'), label=element('h3','',address.label||'Адрес'), street=element('p','',address.address);
      if(address.label)label.dataset.localeSource='';street.dataset.localeSource='';card.append(label,street);
      if(index===0)card.append(element('span','address-primary','Основной адрес'));
      const actions=element('div','account-form-actions');
      const edit=element('button','text-button','Изменить');edit.type='button';edit.addEventListener('click',()=>{form.elements.id.value=address.id;form.elements.label.value=address.label;form.elements.address.value=address.address;content.querySelector('#address-form-heading').textContent='Изменить адрес';content.querySelector('#account-address-cancel').hidden=false;form.elements.label.focus();});actions.append(edit);
      for(const [operation,label] of [['primary','Сделать основным'],['delete','Удалить']]){
        if(operation==='primary'&&index===0)continue;
        const button=element('button','text-button',label);button.type='button';button.addEventListener('click',async()=>{button.disabled=true;try{await update('/api/account/address',{operation,id:address.id});showAddresses();tell('Адреса обновлены.');}catch(problem){tell(problem.message,true);button.disabled=false;}});actions.append(button);
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
  async function render(){
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
    const view=['overview','orders','addresses','settings','loyalty'].includes(content.dataset.accountView)?content.dataset.accountView:'overview';
    if(renderedUser===data.profile.id&&renderedView===view){if(view==='loyalty')showLoyalty();return;}
    renderedUser=data.profile.id;renderedView=view;
    content.replaceChildren(document.querySelector('#account-'+view+'-template').content.cloneNode(true));
    for(const link of document.querySelectorAll('.account-nav a'))if(link.pathname===location.pathname)link.setAttribute('aria-current','page');
    if(view==='overview'){
      content.querySelector('#account-greeting').textContent=data.profile.name||'Добро пожаловать';
      if(data.profile.name)content.querySelector('#account-greeting').dataset.localeSource='';
      content.querySelector('#account-stats').append(stat('Ваша скидка',data.loyalty.discountPercent+'%'),stat('Накоплено',money(data.loyalty.eligibleSpend)));
      await orders(false,3);
    }else if(view==='orders'){
      await orders();content.querySelector('#account-more-orders').addEventListener('click',async event=>{const button=event.currentTarget;button.disabled=true;try{await orders(true);}catch(problem){tell(problem.message,true);}finally{button.disabled=false;}});
    }else if(view==='addresses'){
      showAddresses();const form=content.querySelector('form');
      form.addEventListener('reset',()=>{content.querySelector('#address-form-heading').textContent='Добавить адрес';content.querySelector('#account-address-cancel').hidden=true;});
      form.addEventListener('submit',async event=>{event.preventDefault();const button=form.querySelector('[type="submit"]');button.disabled=true;try{const fields=Object.fromEntries(new FormData(form));await update('/api/account/address',{...fields,operation:fields.id?'edit':'add'});form.reset();showAddresses();tell('Адрес сохранён.');}catch(problem){tell(problem.message,true);}finally{button.disabled=false;}});
    }else if(view==='settings'){
      const form=content.querySelector('form');for(const key of ['name','phone','email'])form.elements[key].value=data.profile[key];
      form.addEventListener('submit',async event=>{event.preventDefault();const button=form.querySelector('button');button.disabled=true;try{await update('/api/account/profile',Object.fromEntries(new FormData(form)));tell('Изменения сохранены.');}catch(problem){tell(problem.message,true);}finally{button.disabled=false;}});
    }else showLoyalty();
  }
  document.addEventListener('click',event=>{const link=event.target.closest('[data-auth-link]');if(link?.getAttribute('aria-disabled')==='true')event.preventDefault();});
  document.querySelector('[data-account-logout]').addEventListener('click',async event=>{const button=event.currentTarget;button.disabled=true;try{await window.lusarAccount.logout();}catch(problem){tell(problem.message,true);button.disabled=false;}});
  document.addEventListener('lusar-account-change',()=>render().catch(problem=>tell(problem.message,true)));
  document.addEventListener('lusar-account-error',event=>tell(event.detail));
  document.addEventListener('lusar-language-change',()=>{for(const link of document.querySelectorAll('[data-auth-link]')){const url=new URL(link.href);url.searchParams.set('lang',document.documentElement.lang);link.href=url;}});
  window.lusarAccount.ready.then(()=>render()).catch(problem=>tell(problem.message,true));
})();
