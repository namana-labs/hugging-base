import { spawn, spawnSync } from 'node:child_process';
import fs from 'node:fs'; import os from 'node:os'; import path from 'node:path';
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const [base, ...links] = process.argv.slice(2);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const UD = fs.mkdtempSync(path.join(os.tmpdir(), 'clarm.'));
const chrome = spawn(CHROME, ['--headless=new', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', `--user-data-dir=${UD}`, '--no-first-run', '--remote-debugging-port=0', '--window-size=1920,1080', 'about:blank'], { stdio: 'ignore' });
const cleanup = () => { try { chrome.kill('SIGKILL'); } catch {} spawnSync('pkill', ['-f', `user-data-dir=${UD}`]); };
process.on('exit', cleanup);
let pf = null;
for (let i = 0; i < 300 && !pf; i++) { try { const t = fs.readFileSync(path.join(UD, 'DevToolsActivePort'), 'utf8').trim().split('\n'); if (t.length >= 2) pf = t; } catch {} if (!pf) await sleep(100); }
const ws = new WebSocket(`ws://127.0.0.1:${pf[0]}${pf[1]}`);
await new Promise((res) => { ws.onopen = res; });
let id = 0; const pending = new Map();
ws.onmessage = (ev) => { const m = JSON.parse(ev.data); if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); m.error ? p.rej(new Error(m.error.message)) : p.res(m.result); } };
const send = (method, params = {}, sessionId) => new Promise((res, rej) => { const i = ++id; pending.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method, params, sessionId })); });
const { targetId } = await send('Target.createTarget', { url: 'about:blank' });
const { sessionId: s } = await send('Target.attachToTarget', { targetId, flatten: true });
await send('Page.enable', {}, s);
await send('Emulation.setDeviceMetricsOverride', { width: 1920, height: 1080, deviceScaleFactor: 1, mobile: false }, s);
const ev = async (expr) => (await send('Runtime.evaluate', { expression: expr, returnByValue: true }, s)).result.value;
for (const q of links) {
  const t0 = Date.now();
  await send('Page.navigate', { url: base + '?' + q }, s);
  let st = null;
  while (Date.now() - t0 < 120000) { st = await ev('document.body && document.body.dataset.status'); if (st === 'ready' || st === 'error') break; await sleep(300); }
  const m = await ev(`(()=>{const p=document.querySelector('.hb-panel');const r=p.getBoundingClientRect();
    const txt=p.innerText; const nums=(txt.match(/-?\\$?\\d[\\d,]*(\\.\\d+)?%?/g)||[]).length;
    const vis=[...p.querySelectorAll('.num')].filter(e=>{const b=e.getBoundingClientRect();return b.top<window.innerHeight&&b.bottom>r.top}).length;
    const chipsFold=[...p.querySelectorAll('.chip')].filter(e=>{const b=e.getBoundingClientRect();return b.top<window.innerHeight&&b.bottom>r.top}).length;
    return {panelH:p.scrollHeight, screens:+(p.scrollHeight/p.clientHeight).toFixed(1), chips:p.querySelectorAll('.chip').length, chipsAboveFold:chipsFold, numSpans:p.querySelectorAll('.num').length, numSpansAboveFold:vis, digitRuns:nums, words:txt.split(/\\s+/).length, sections:p.querySelectorAll('section,h2').length,
      overlayChips:document.querySelectorAll('.p1-overlay .chip').length, legendLines:(document.querySelector('.p1-legend')||{innerText:''}).innerText.split('\\n').length, stripLabels:document.querySelectorAll('.p1-strip-marks .mark > span').length,
      titles:document.querySelectorAll('[title]').length}})()`);
  console.log(q, JSON.stringify(m));
}
cleanup(); process.exit(0);
