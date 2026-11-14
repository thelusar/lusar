(() => {
  const hero = document.querySelector('.home-hero');
  if (!hero) return;
  const fixtures = Object.fromEntries(['pendant','left','right','floor','strip'].map((key,index) => [key, {
    name: ['Подвес','Левое бра','Правое бра','Торшер','Подсветка консоли'][index], level: [90,40,40,30,45][index], temperature:3800, last: [90,40,40,30,45][index]
  }]));
  const presets = {morning:{levels:[65,25,25,20,35],temperature:4500},day:{levels:[90,40,40,30,45],temperature:3800},evening:{levels:[35,65,65,45,70],temperature:2700}};
  const keys=Object.keys(fixtures), selected=new Set(['pendant']);
  const $=selector=>hero.querySelector(selector), pins=[...hero.querySelectorAll('[data-fixture]')];
  const brightness=$('#fixture-brightness'),temperature=$('#fixture-temperature'),power=$('#fixture-power'),globalPower=$('#scene-power'),curtain=$('#curtain-opening');
  const layers=Object.fromEntries(keys.map(key=>[key,$('[data-light="'+key+'"]')]));
  const fixturePins=Object.fromEntries(pins.map(pin=>[pin.dataset.fixture,pin]));
  const previous=new Map(), sceneButtons=[...hero.querySelectorAll('[data-scene]')];
  const curtainLayer=$('.window-curtain'),sceneImage=$('#scene-image');
  const translate=source=>window.lusarLocale?.text(source)||source;
  let currentPreset='day', savedScene=null;
  function render() {
    for (const key of keys) {
      const fixture=fixtures[key], layer=layers[key], warmth=(6500-fixture.temperature)/3800;
      const before=previous.get(key);
      if(before?.level!==fixture.level) layer.style.setProperty('--level', fixture.level/100);
      if(before?.temperature!==fixture.temperature) layer.style.filter='saturate('+(.04+Math.pow(warmth,2.5)*1.12)+') brightness('+(1.24-warmth*.24)+')';
      previous.set(key,{level:fixture.level,temperature:fixture.temperature});
      const pin=fixturePins[key];
      pin.setAttribute('aria-pressed',String(selected.has(key)));
      pin.dataset.lit=String(fixture.level>0);
    }
    const values=[...selected].map(key=>fixtures[key]), mixed=prop=>new Set(values.map(item=>item[prop])).size>1;
    $('#fixture-name').textContent=values.length>1 ? translate('Выбрано светильников')+': '+values.length : values[0]?translate(values[0].name):translate('Выберите светильники');
    $('#fixture-name').title=values.map(item=>translate(item.name)).join(' · ');
    brightness.disabled=temperature.disabled=power.disabled=!values.length;
    brightness.value=values.length ? Math.round(values.reduce((sum,item)=>sum+item.level,0)/values.length):0;
    temperature.value=values[0]?.temperature||3800;
    $('#brightness-value').value=mixed('level')?translate('Разная'):brightness.value+'%';
    $('#temperature-value').value=mixed('temperature')?translate('Разная'):temperature.value+' K';
    brightness.style.setProperty('--fill',brightness.value+'%');
    power.setAttribute('aria-checked',String(values.some(item=>item.level>0)));
    globalPower.setAttribute('aria-checked',String(keys.some(key=>fixtures[key].level>0)));
    $('[data-select-all]').textContent=translate(selected.size===keys.length?'Снять выбор':'Выбрать все');
    sceneButtons.forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.scene===currentPreset)));
  }
  function announce(text) {$('#scene-caption').textContent=text;}
  function renderCurtain() {
    const closure=Number(curtain.value), closed=closure/100, opening=100-closure;
    const edge=28.2+closed*17.2;
    // Follow the perspective of the window's top and bottom rails.
    curtainLayer.style.clipPath=`polygon(24.1% 1.9%,${edge}% ${9.4+closed*13.9}%,${edge}% ${82-closed*10.2}%,24.1% 84%)`;
    // Unfold a dedicated full-resolution fabric asset instead of enlarging a narrow photo crop.
    curtainLayer.style.setProperty('--drape-width',`${4.1+closed*17.2}%`);
    curtainLayer.style.setProperty('--fabric-light',String(.72+opening*.0028));
    sceneImage.style.filter=`brightness(${.18+.82*opening/100})`;
    $('#curtain-value').value=closure+'%';
    curtain.style.setProperty('--fill',closure+'%');
    curtain.setAttribute('aria-valuetext',closure+'% · '+translate(closure===100?'Закрыта':closure===0?'Полностью открыта':'Закрытие шторы'));
    hero.dataset.curtainOpening=String(opening);
  }
  curtain.addEventListener('input',renderCurtain);
  curtain.addEventListener('change',()=>announce(translate('Штора')+': '+$('#curtain-value').value));
  pins.forEach(pin=>pin.addEventListener('click',()=>{
    const key=pin.dataset.fixture;
    selected.has(key)?selected.delete(key):selected.add(key);
    render();
    announce(selected.size?translate('Регулируем')+': '+$('#fixture-name').textContent:translate('Выберите светильники'));
  }));
  $('[data-select-all]').addEventListener('click',()=>{
    const all=selected.size===keys.length;selected.clear();if(!all)keys.forEach(key=>selected.add(key));render();
    announce(translate(all?'Выберите светильники':'Выбраны все светильники'));
  });
  brightness.addEventListener('input',()=>{for(const key of selected){const item=fixtures[key];item.level=Number(brightness.value);if(item.level)item.last=item.level;}currentPreset='';render();});
  temperature.addEventListener('input',()=>{for(const key of selected)fixtures[key].temperature=Number(temperature.value);currentPreset='';render();});
  function toggle(target) {
    const on=target.some(key=>fixtures[key].level>0);
    for(const key of target){const item=fixtures[key];if(on){if(item.level>0)item.last=item.level;item.level=0;}else item.level=item.last||60;}
    currentPreset='';render();announce(translate(on?'Свет выключен':'Свет включён'));
  }
  power.addEventListener('click',()=>toggle([...selected]));
  globalPower.addEventListener('click',()=>{
    const on=keys.some(key=>fixtures[key].level>0);
    if(on){savedScene={levels:keys.map(key=>fixtures[key].level),preset:currentPreset};keys.forEach(key=>{if(fixtures[key].level>0)fixtures[key].last=fixtures[key].level;fixtures[key].level=0;});currentPreset='';}
    else {keys.forEach((key,index)=>fixtures[key].level=savedScene?.levels[index]??fixtures[key].last);currentPreset=savedScene?.preset||'';}
    render();announce(translate(on?'Свет выключен':'Свет включён'));
  });
  hero.querySelectorAll('[data-scene]').forEach(button=>button.addEventListener('click',()=>{
    currentPreset=button.dataset.scene;const preset=presets[currentPreset];
    keys.forEach((key,index)=>{fixtures[key].level=fixtures[key].last=preset.levels[index];fixtures[key].temperature=preset.temperature;});
    render();announce(button.textContent+' · '+preset.temperature+' K');
  }));
  [brightness,temperature].forEach(input=>input.addEventListener('change',()=>announce($('#fixture-name').textContent+': '+$('#brightness-value').value+', '+$('#temperature-value').value)));
  document.addEventListener('lusar-language-change',()=>{render();renderCurtain();});render();renderCurtain();
  const image=new Image();image.onload=()=>{hero.querySelectorAll('.room-console,.room-hotspots,.curtain-control').forEach(item=>item.hidden=false);hero.dataset.interactive='true';};
  image.onerror=()=>hero.querySelectorAll('.room-light').forEach(item=>item.hidden=true);
  image.src='/scenes/lusar-room-ararat-on.webp';
})();
