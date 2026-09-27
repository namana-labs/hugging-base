// clarity designer: viewport shot + panel pages for each link (read-only on the repo)
import { spawn, spawnSync } from 'node:child_process';
import fs from 'node:fs'; import os from 'node:os'; import path from 'node:path';
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const [base, shots, linksFile] = process.argv.slice(2);
const links = fs.readFileSync(linksFile, 'utf8').split('\n').filter((l) => l && !l.startsWith('#')).map((l) => l.split(/\s+/)[1]);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const slug = (q) => q.replace(/[^A-Za-z0-9]+/g, '_').replace(/^_|_$/g, '').slice(0, 120);
const UD = fs.mkdtempSync(path.join(os.tmpdir(), 'clar.'));
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
const shot = async (file, clip) => { const r = await send('Page.captureScreenshot', { format: 'png', ...(clip ? { clip: { ...clip, scale: 1 } } : {}) }, s); fs.writeFileSync(path.join(shots, file), Buffer.from(r.data, 'base64')); };
for (const q of links) {
  const t0 = Date.now();
  await send('Page.navigate', { url: base + '?' + q }, s);
  let st = null;
  while (Date.now() - t0 < 90000) { st = await ev('document.body && document.body.dataset.status'); if (st === 'ready' || st === 'error') break; await sleep(300); }
  await sleep(600);
  const n = slug(q);
  await shot(n + '.png');
  const info = await ev(`(()=>{const p=document.querySelector('.hb-panel');return p?{sh:p.scrollHeight,ch:p.clientHeight,top:p.getBoundingClientRect().top,left:p.getBoundingClientRect().left,w:p.clientWidth}:null})()`);
  let pages = 0;
  if (info && info.sh > info.ch + 20) {
    for (let y = info.ch - 60, i = 1; y < info.sh && i <= 6; y += info.ch - 60, i++) {
      await ev(`document.querySelector('.hb-panel').scrollTop=${y}`); await sleep(250);
      await shot(`${n}__panel${i}.png`, { x: info.left, y: info.top, width: info.w + 2, height: info.ch }); pages++;
    }
    await ev(`document.querySelector('.hb-panel').scrollTop=0`);
  }
  const txt = await ev(`document.body.dataset.errors`);
  console.log(`${q} status=${st} errors=${txt} panelH=${info && info.sh} pages=${pages} ${Date.now() - t0}ms`);
}
cleanup(); process.exit(0);
