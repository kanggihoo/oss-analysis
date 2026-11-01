// 뷰어 런타임 실행 확인용 CDP 하네스. demo.html을 headless Chrome으로 열고 키 입력/클릭/내보내기를 재현한다.
// 레포 코드는 실행하지 않는다(렌더된 산출물 demo.html만 연다). 사용: node cdp-run.mjs
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const CHROME = process.env.CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'cdp-'));
const url = 'file://' + path.join(here, 'demo.html');
const chrome = spawn(CHROME, ['--headless=new', '--disable-gpu', '--no-sandbox', `--user-data-dir=${profile}`,
  '--remote-debugging-port=0', '--window-size=1600,1000', '--autoplay-policy=no-user-gesture-required', url], { stdio: 'ignore' });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function port() {
  for (let i = 0; i < 100; i++) {
    try { return Number(fs.readFileSync(path.join(profile, 'DevToolsActivePort'), 'utf8').split('\n')[0]); } catch { await sleep(100); }
  }
  throw new Error('no devtools port');
}
const p = await port();
let target;
for (let i = 0; i < 50 && !target; i++) {
  try { target = (await (await fetch(`http://127.0.0.1:${p}/json`)).json()).find((t) => t.type === 'page'); } catch {}
  if (!target) await sleep(100);
}
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener('open', r));
let id = 0; const pending = new Map();
ws.addEventListener('message', (e) => { const m = JSON.parse(e.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } });
const send = (method, params = {}) => new Promise((r) => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async (expr) => { const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true }); if (r.result.exceptionDetails) return 'EXC ' + JSON.stringify(r.result.exceptionDetails.exception?.description || r.result.exceptionDetails.text); return r.result.result.value; };
const key = async (k, extra = {}) => { const text = k.length === 1 ? k : undefined; await send('Input.dispatchKeyEvent', { type: 'keyDown', key: k, text, ...extra }); await send('Input.dispatchKeyEvent', { type: 'keyUp', key: k, ...extra }); await sleep(250); };
const state = () => ev(`JSON.stringify({hash:location.hash,search:location.search,present:document.documentElement.dataset.present||null,guide:Archify.guide.isOpen(),finder:Archify.finder.isOpen(),exportOpen:Archify.exportMenu.isOpen(),theme:document.documentElement.dataset.theme,preset:document.documentElement.dataset.preset,motion:document.documentElement.dataset.motion,detail:document.querySelector('.diagram-container').dataset.detailLevel,focus:document.querySelector('.diagram-container svg').getAttribute('data-focus-active'),lens:document.querySelector('.diagram-container svg').getAttribute('data-lens-active'),lensOpen:Archify.semanticLens.isOpen(),radar:Archify.radar.isOpen(),route:Archify.routeProbe.active(),intent:Archify.intentTrace.active(),routeAttr:document.querySelector('.diagram-container svg').getAttribute('data-route-active')})`);
const out = [];
const log = async (label) => { const s = await state(); out.push({ step: label, state: JSON.parse(s) }); console.log(label.padEnd(34), s); };

await sleep(1500);
await ev('document.body.focus()');
await log('initial');
await key('?', { modifiers: 8 }); await log('key ? (guide open)');
await key('?', { modifiers: 8 }); await log('key ? again (guide close via panel)');
await key('t'); await log('key t (theme toggle)');
await key('s'); await log('key s (preset cycle)');
await key('+'); await key('+'); await key('+'); await log('key + x3');
await key('0'); await log('key 0 (reset)');
await key('-'); await key('-'); await log('key - x2 (below 100% => map?)');
await key('0');
await key('/'); await log('key / (finder open)');
// finder: type "ca" and read results
await ev(`(()=>{const i=document.getElementById('node-finder-input');i.value='cac';i.dispatchEvent(new Event('input',{bubbles:true}));})()`);
console.log('finder results for "cac":', await ev(`Array.from(document.querySelectorAll('.node-finder-result')).map(b=>b.dataset.nodeId).join(',')`));
console.log('finder status:', await ev(`document.getElementById('node-finder-status').textContent`));
await ev(`(()=>{const i=document.getElementById('node-finder-input');i.value='';i.dispatchEvent(new Event('input',{bubbles:true}));})()`);
console.log('finder results for "":', await ev(`document.querySelectorAll('.node-finder-result').length`));
await ev(`(()=>{const i=document.getElementById('node-finder-input');i.value='redis';i.dispatchEvent(new Event('input',{bubbles:true}));})()`);
console.log('finder results for "redis" (sublabel/text match?):', await ev(`Array.from(document.querySelectorAll('.node-finder-result')).map(b=>b.dataset.nodeId).join(',')`));
await ev(`document.getElementById('node-finder-input').focus()`);
await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 }); await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 }); await sleep(400);
await log('Enter in finder (focus top result)');
await key('Escape'); await log('Escape (clears focus)');
await key('l'); await log('key l (lens open)');
await key('Escape'); await log('Escape (lens close)');
await key('m'); await log('key m (radar toggle)');
await key('m'); await log('key m again');
await key('r'); await log('key r (route probe start)');
await key('Escape'); await log('Escape (route clear)');
await ev(`Archify.focus.set('api')`); await sleep(300);
await log('focus.set(api)');
await ev(`document.getElementById('btn-reach-downstream').click()`); await sleep(300);
await log('click reach downstream');
await key('f'); await log('key f (present)');
await key('Escape'); await log('Escape #1 (focus first)');
await key('Escape'); await log('Escape #2 (exit present?)');
await key('Escape'); await log('Escape #3 (exit present?)');
await key('Escape'); await log('Escape #4');
await key('e'); await log('key e (export menu)');
await key('Escape', {}); await log('Escape (menu has focus?)');
// motion button
await ev(`document.getElementById('btn-motion').click()`); await sleep(300);
console.log('after motion click:', await ev(`JSON.stringify({motion:document.documentElement.dataset.motion,stored:localStorage.getItem('archify-motion')})`));
await ev(`document.getElementById('btn-motion').click()`); await sleep(300);
console.log('after 2nd click:', await ev(`JSON.stringify({motion:document.documentElement.dataset.motion,stored:localStorage.getItem('archify-motion')})`));

// hashchange 동기화, 경로 해시
await ev("location.hash='#focus=db'"); await sleep(500); await log('hash set to #focus=db after load');
await ev("location.hash='#route=users~worker'"); await sleep(800); await log('hash set to #route=users~worker');
console.log('route nodes:', await ev("Array.from(document.querySelectorAll('[data-route-match=\"true\"][data-node-id]')).map(n=>n.dataset.nodeId).join('>')"));
console.log('route steps:', await ev("Array.from(document.querySelectorAll('[data-node-id][data-route-step]')).sort((a,b)=>a.dataset.routeStep-b.dataset.routeStep).map(n=>n.dataset.nodeId+':'+n.dataset.routeStep).join(' ')"));
console.log('share items hidden/disabled (route):', await ev("(()=>{const b=document.querySelector('[data-action=route-share-card]');return JSON.stringify({hidden:b.hidden,disabled:b.disabled})})()"));
// exports: capture downloads
await ev(`window.__dl=[];const oc=HTMLAnchorElement.prototype.click;HTMLAnchorElement.prototype.click=function(){ if(this.download){ const name=this.download, href=this.href; window.__dl.push(fetch(href).then(r=>r.blob()).then(async b=>{const buf=new Uint8Array(await b.slice(0,32).arrayBuffer());const head=Array.from(buf).map(x=>x.toString(16).padStart(2,'0')).join('');let text='';if(b.type.indexOf('svg')>=0)text=await b.text();if(text)(window.__svgText=window.__svgText||{})[name]=text;const dv=new DataView(buf.buffer);const png=head.startsWith('89504e47')?{w:dv.getUint32(16),h:dv.getUint32(20)}:undefined;return {name,type:b.type,size:b.size,head:head.slice(0,16),png,svgThemes:text?{lightVars:/\\[data-theme="light"\\]|data-theme=.light./.test(text),darkVars:/data-theme=.dark./.test(text),prefers:/prefers-color-scheme/.test(text),len:text.length}:undefined}})); return;} return oc.apply(this,arguments)}; 'patched'`);
for (const f of ['png', 'jpeg', 'webp', 'svg', 'svg-light', 'svg-dark']) {
  await ev(`Archify.exportMenu.run('${f}')`); await sleep(1500);
}
console.log('can record webm:', await ev(`Archify.motion.canRecord()`));
await ev(`Archify.exportMenu.run('webm')`); await sleep(9000);
const downloads = await ev(`Promise.all(window.__dl).then(a=>JSON.stringify(a))`);
console.log('downloads:\n' + JSON.parse(downloads).map((d) => '  ' + JSON.stringify(d)).join('\n'));
console.log('export receipt attrs:', await ev(`JSON.stringify(Array.from(document.documentElement.attributes).filter(a=>/export|motion-bytes/.test(a.name)).map(a=>[a.name,a.value]))`));
await ev("Archify.exportMenu.downloadRouteShareCard()"); await sleep(2500);
await ev("Archify.focus.set('api'); Archify.focus.reach('downstream',{})"); await sleep(600);
await ev("Archify.exportMenu.downloadReachShareCard()"); await sleep(2500);
const dl2 = JSON.parse(await ev("Promise.all(window.__dl).then(a=>JSON.stringify(a))"));
console.log('share cards:', JSON.stringify(dl2.slice(7)));
// canonical export 청결성: 포커스·Reach가 활성인 상태로 SVG를 내보내고 뷰어 상태 마커가 남는지 본다
await ev("Archify.focus.set('api',{toggle:false}); Archify.focus.reach('downstream',{toggle:false}); Archify.motionGovernor.resume()"); await sleep(600);
await ev("Archify.exportMenu.run('svg-dark')"); await sleep(1500);
console.log('live state before clean export:', await ev("JSON.stringify({focus:Archify.focus.active(),reach:!!Archify.focus.reachability(),hash:location.hash})"));
console.log('clean-export markers in svg-dark (export clone count; live DOM count in parens):', await ev(`(() => {
  const t = Object.values(window.__svgText || {}).pop() || '';
  const d = new DOMParser().parseFromString(t, 'image/svg+xml');
  const live = document.querySelector('.diagram-container svg');
  const root = ['data-focus-active', 'data-reach-active', 'data-lens-active', 'data-route-active'].map((a) => a + ':' + d.documentElement.hasAttribute(a) + ' (live ' + live.hasAttribute(a) + ')');
  const sels = ['[data-reach-match]', '[data-reach-origin]', '[data-route-match]', '[data-intent-trace-overlay]', '[data-ambient-flow-overlay]', '[data-node-id]', '[data-edge-from]'];
  const counts = {};
  sels.forEach((k) => { counts[k] = d.querySelectorAll(k).length + ' (' + live.querySelectorAll(k).length + ')'; });
  return JSON.stringify({ root, counts });
})()`));
console.log('live state after export (selection preserved?):', await ev("JSON.stringify({focus:Archify.focus.active(),reach:!!Archify.focus.reachability()})"));
console.log('unsupported format:', await ev(`Archify.exportMenu.run('gif').then(()=>'resolved',e=>'rejected: '+e.message)`));
console.log('route/reach share without state:', await ev(`Archify.exportMenu.shareCard('route').then(()=>'resolved',e=>'rejected: '+e.message)`));
fs.writeFileSync(path.join(here, 'cdp-run.json'), JSON.stringify({ steps: out, downloads: JSON.parse(downloads) }, null, 1));
ws.close(); chrome.kill(); await sleep(800); try { fs.rmSync(profile, { recursive: true, force: true, maxRetries: 5 }); } catch {}
