(() => {
  const hero = document.querySelector('.home-hero');
  if (!hero) return;
  const fixtures = {
    pendant: {name: 'Подвес', level: 75, temperature: 3000, last: 75},
    left: {name: 'Левое бра', level: 65, temperature: 3000, last: 65},
    right: {name: 'Правое бра', level: 65, temperature: 3000, last: 65},
    floor: {name: 'Торшер', level: 45, temperature: 3000, last: 45},
    strip: {name: 'Подсветка консоли', level: 60, temperature: 3000, last: 60}
  };
  const presets = {
    day: [0, 0, 0, 0, 0], warm: [75, 65, 65, 45, 60],
    evening: [25, 40, 40, 20, 65], off: [0, 0, 0, 0, 0]
  };
  const pins = [...hero.querySelectorAll('[data-fixture]')];
  const buttons = [...hero.querySelectorAll('[data-scene]')];
  const brightness = hero.querySelector('#fixture-brightness');
  const temperature = hero.querySelector('#fixture-temperature');
  const power = hero.querySelector('#fixture-power');
  const caption = hero.querySelector('#scene-caption');
  const name = hero.querySelector('#fixture-name');
  const translate = source => window.lusarLocale?.text(source) || source;
  let selected = 'pendant';
  function renderFixture(key) {
    const fixture = fixtures[key];
    const layer = hero.querySelector(`[data-light="${key}"]`);
    layer.style.setProperty('--level', fixture.level / 100);
    // Aligned light pools remain fixed as brightness changes. Desaturation
    // previews neutral white without casting a blue tint over the whole room.
    const warmth = (6500 - fixture.temperature) / 3800;
    layer.style.filter = `saturate(${.08 + warmth * 1.12}) brightness(${1.2 - warmth * .2})`;
    pins.find(item => item.dataset.fixture === key).dataset.lit = String(fixture.level > 0);
  }
  function renderEditor() {
    const fixture = fixtures[selected];
    name.textContent = translate(fixture.name);
    brightness.value = fixture.level;
    temperature.value = fixture.temperature;
    hero.querySelector('#brightness-value').value = fixture.level + '%';
    hero.querySelector('#temperature-value').value = fixture.temperature + ' K';
    brightness.style.setProperty('--fill', fixture.level + '%');
    power.setAttribute('aria-checked', String(fixture.level > 0));
    for (const pin of pins) pin.setAttribute('aria-pressed', String(pin.dataset.fixture === selected));
  }
  function customScene() {
    buttons.forEach(button => button.setAttribute('aria-pressed', 'false'));
    renderFixture(selected);
    renderEditor();
  }
  for (const pin of pins) pin.addEventListener('click', () => {
    selected = pin.dataset.fixture;
    renderEditor();
  });
  brightness.addEventListener('input', () => {
    const fixture = fixtures[selected];
    fixture.level = Number(brightness.value);
    if (fixture.level > 0) fixture.last = fixture.level;
    customScene();
  });
  temperature.addEventListener('input', () => {
    fixtures[selected].temperature = Number(temperature.value);
    customScene();
  });
  power.addEventListener('click', () => {
    const fixture = fixtures[selected];
    fixture.level = fixture.level > 0 ? 0 : fixture.last;
    customScene();
  });
  // Announce committed values, not every intermediate slider movement.
  for (const input of [brightness, temperature]) input.addEventListener('change', () => {
    const fixture = fixtures[selected];
    caption.textContent = `${translate(fixture.name)}: ${fixture.level}%, ${fixture.temperature} K`;
  });
  for (const button of buttons) button.addEventListener('click', () => {
    Object.keys(fixtures).forEach((key, index) => {
      const fixture = fixtures[key];
      fixture.level = presets[button.dataset.scene][index];
      fixture.temperature = button.dataset.scene === 'evening' ? 2700 : 3000;
      if (fixture.level > 0) fixture.last = fixture.level;
      renderFixture(key);
    });
    buttons.forEach(option => option.setAttribute('aria-pressed', String(option === button)));
    caption.textContent = button.dataset.scene === 'off' ? translate('Весь свет выключен') : button.textContent;
    renderEditor();
  });
  document.addEventListener('lusar-language-change', renderEditor);
  Object.keys(fixtures).forEach(renderFixture);
  renderEditor();
  // Only reveal controls when their lighting frame can actually be displayed.
  const lightImage = new Image();
  lightImage.onload = () => {
    hero.querySelector('.room-console').hidden = false;
    hero.querySelector('.room-hotspots').hidden = false;
    hero.querySelector('.room-hint').hidden = false;
    hero.dataset.interactive = 'true';
  };
  lightImage.onerror = () => hero.querySelectorAll('.room-light').forEach(layer => layer.hidden = true);
  lightImage.src = '/scenes/lusar-room-on.webp';
})();
