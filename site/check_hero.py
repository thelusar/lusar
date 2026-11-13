"""Check independent hero lighting, presets, translations and responsive controls."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
import threading

import serve
from check_checkout import EDGE

CHECK = r'''<!doctype html><meta charset="utf-8"><output>WAIT</output><iframe width="1440" height="1000"></iframe>
<script>
const f = document.querySelector('iframe'), out = document.querySelector('output');
const tick = () => new Promise(resolve => setTimeout(resolve, 35));
const require = (value, message) => { if (!value) throw Error(message); };
localStorage.setItem('lusar-cookie-choice-v1', 'essential');
sessionStorage.setItem('lusar-first-order-promo-seen', '1');
localStorage.setItem('lusar-language', 'ru');
f.onload = async () => { try {
 const d = f.contentDocument, w = f.contentWindow, hero = d.querySelector('.home-hero');
 const deadline = Date.now() + 4000;
 while (!hero.dataset.interactive && Date.now() < deadline) await tick();
 require(hero.dataset.interactive === 'true', 'Lighting controls did not become ready');
 const layers = [...hero.querySelectorAll('[data-light]')];
 const levels = () => layers.map(layer => Number(layer.style.getPropertyValue('--level')));
 const select = key => hero.querySelector(`[data-fixture="${key}"]`).click();
 const input = (id, value) => { const slider = d.getElementById(id); slider.value = value; slider.dispatchEvent(new w.Event('input', {bubbles: true})); };
 const initial = levels();
 select('right'); input('fixture-brightness', 23);
 require(levels()[2] === .23 && levels().every((value, index) => index === 2 || value === initial[index]), 'Brightness changed an unrelated fixture');
 const filters = layers.map(layer => layer.style.filter);
 input('fixture-temperature', 6500);
 require(layers[2].style.filter !== filters[2] && layers.every((layer, index) => index === 2 || layer.style.filter === filters[index]), 'Temperature changed an unrelated fixture');
 const power = d.getElementById('fixture-power'); power.click();
 require(levels()[2] === 0 && power.getAttribute('aria-checked') === 'false', 'Power switch did not turn the selected light off');
 power.click(); require(levels()[2] === .23, 'Power switch lost the chosen brightness');
 select('left'); input('fixture-brightness', 0);
 require(levels()[1] === 0 && levels()[2] === .23, 'Wall lights are coupled');
 select('right'); require(d.getElementById('fixture-temperature').value === '6500', 'Temperature did not survive fixture selection');
 hero.querySelector('[data-scene="evening"]').click();
 require(JSON.stringify(levels()) === JSON.stringify([.25,.4,.4,.2,.65]), 'Evening preset failed');
 hero.querySelector('[data-scene="off"]').click(); require(levels().every(value => value === 0), 'All off failed');
 hero.querySelector('[data-scene="warm"]').click(); require(JSON.stringify(levels()) === JSON.stringify(initial), 'Warm preset failed');
 for (let value = 1; value <= 100; value++) input('fixture-brightness', value);
 require(levels()[2] === 1 && !hero.querySelector('[data-scene][aria-pressed="true"]'), 'Rapid adjustments lost state or left a stale preset');
 const samples = [];
 for (const width of [320,390,768,1024,1440,1920]) {
  f.width = String(width); await tick();
  for (const [language, expected] of [['ru','Правое бра'],['hy','Աջ պատի լուսատու'],['en','Right wall light']]) {
   const picker = d.querySelector('#language'); picker.value = language; picker.dispatchEvent(new w.Event('change')); await tick();
   require(d.querySelector('#fixture-name').textContent === expected, 'Selected fixture translation failed: ' + language);
   for (const theme of ['dark','light']) {
    d.documentElement.dataset.theme = theme;
    require(d.documentElement.scrollWidth <= w.innerWidth + 1, 'Horizontal overflow at ' + width + '/' + language + '/' + theme);
    for (const element of hero.querySelectorAll('button, input')) {
     const rect = element.getBoundingClientRect();
     require(rect.width >= 24 && rect.height >= 24 && rect.left >= -1 && rect.right <= w.innerWidth + 1, 'Control outside viewport or too small at ' + width);
    }
    const stage = hero.querySelector('.room-stage').getBoundingClientRect();
    require(Math.abs(stage.width / stage.height - 1672/941) < .01, 'Room frame distorted at ' + width);
    samples.push({width,language,theme});
   }
  }
 }
 require(w.getComputedStyle(layers[0]).transitionDuration === '0s', 'Reduced motion is ignored');
 require(d.querySelector('#scene-image').complete && d.querySelector('#scene-image').naturalWidth === 1672, 'Room image missing');
 out.textContent = 'PASS:' + JSON.stringify({responsiveStates:samples.length,independentLights:layers.length});
} catch (error) { out.textContent = 'FAIL:' + error.message; }};
f.src = '/';
</script>'''


class Handler(serve.Handler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path == '/hero-check':
            self.send_html(CHECK)
        elif self.path.startswith('/hero-screenshot'):
            from urllib.parse import parse_qs, urlsplit
            params = parse_qs(urlsplit(self.path).query)
            width = int(params.get('width', ['1440'])[0])
            preset = params.get('preset', ['warm'])[0]
            language = params.get('language', ['ru'])[0]
            # The iframe preserves real narrow viewports despite Edge's minimum window size.
            self.send_html('''<!doctype html><meta charset="utf-8"><style>body{margin:0;background:#080808}iframe{display:block;border:0}</style>
<iframe width="WIDTH" height="1200"></iframe><script>
localStorage.setItem('lusar-cookie-choice-v1','essential'); sessionStorage.setItem('lusar-first-order-promo-seen','1');
localStorage.setItem('lusar-language',LANGUAGE); const f=document.querySelector('iframe');f.onload=()=>{
const wait=()=>{const b=f.contentDocument.querySelector('[data-scene=PRESET]');
if(!f.contentDocument.querySelector('.home-hero').dataset.interactive)return setTimeout(wait,50);b.click();};wait();};f.src='/';</script>'''
                .replace('WIDTH', str(width)).replace('PRESET', preset).replace('LANGUAGE', json.dumps(language)))
        else:
            super().do_GET()

    def send_html(self, markup):
        body = markup.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screenshots', type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(dir=serve.ROOT, ignore_cleanup_errors=True) as temp:
        serve.DATABASE = Path(temp) / 'hero-check.sqlite'
        with serve.ThreadingHTTPServer(('127.0.0.1', 0), Handler) as server:
            threading.Thread(target=server.serve_forever, daemon=True).start()
            origin = f'http://127.0.0.1:{server.server_port}'
            common = [str(EDGE), '--headless=new', '--no-first-run', '--disable-gpu', '--force-prefers-reduced-motion']
            try:
                result = subprocess.run(common + ['--user-data-dir=' + temp + '/check', '--virtual-time-budget=16000',
                    '--dump-dom', origin + '/hero-check'], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=45)
                output = result.stdout.partition('<output>')[2].partition('</output>')[0]
                if not output.startswith('PASS:'):
                    raise RuntimeError(output or result.stderr[-1000:])
                print(output)
                if args.screenshots:
                    args.screenshots.mkdir(parents=True, exist_ok=True)
                    for name, width, height, preset, language in [('desktop',1440,1000,'warm','ru'),('day',1440,1000,'day','ru'),
                        ('evening',1440,1000,'evening','ru'),('mobile',390,1050,'warm','ru'),('mobile-hy',320,1100,'warm','hy')]:
                        subprocess.run(common + ['--user-data-dir=' + temp + '/' + name, '--window-size=' + str(max(width,600)) + ',' + str(height),
                            '--virtual-time-budget=4000', '--screenshot=' + str(args.screenshots / (name + '.png')),
                            origin + f'/hero-screenshot?width={width}&preset={preset}&language={language}'], capture_output=True, timeout=35, check=True)
                    print('Screenshots:', args.screenshots)
            finally:
                server.shutdown()


if __name__ == '__main__':
    main()
