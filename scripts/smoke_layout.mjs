#!/usr/bin/env node
// scripts/smoke_layout.mjs (UI-A) -- the story pages' layout at the demo sizes, in one headless Chrome over CDP.
// For each size x link: the page reaches data-status=ready, nothing overflows horizontally
// (document.documentElement.scrollWidth <= innerWidth), and every primary control -- the step nav, "Start the sim ->",
// "Continue to ..." -- lies inside the viewport and is the element hit at its centre (elementFromPoint).
// Usage: node scripts/smoke_layout.mjs --base http://127.0.0.1:8801/ui/ [--sizes 1280x800,1440x900,1920x1080]
//        [--timeout 40] <query> [<query> ...]
// Prints: LAYOUT <WxH> <query> ok|FAIL <reasons>, then LAYOUT: <ok>/<total> ok. Exit 0 when all pass.
// node >= 22 (global WebSocket), or node 20 with NODE_OPTIONS=--experimental-websocket; CHROME = the Chrome binary.
import { spawn, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const CHROME = process.env.CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const argv = process.argv.slice(2);
const opt = { base: null, sizes: '1280x800,1440x900,1920x1080', timeout: 40, links: [] };
for (let i = 0; i < argv.length; i++) {
  const a = argv[i];
  if (a === '--base') opt.base = argv[++i];
  else if (a === '--sizes') opt.sizes = argv[++i];
  else if (a === '--timeout') opt.timeout = Number(argv[++i]);
  else opt.links.push(a);
}
if (!opt.base || !opt.links.length) { console.error('usage: smoke_layout.mjs --base URL [--sizes WxH,...] [--timeout S] query...'); process.exit(2); }
const sizes = opt.sizes.split(',').map((s) => s.split('x').map(Number));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const UD = fs.mkdtempSync(path.join(process.env.SMOKE_TMP || os.tmpdir(), 'chrome-layout.'));
const logFd = fs.openSync(path.join(UD, 'chrome.log'), 'w');
const chrome = spawn(CHROME, ['--headless=new', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', `--user-data-dir=${UD}`,
  '--no-first-run', '--no-default-browser-check', '--remote-debugging-port=0', '--window-size=1920,1080', 'about:blank'],
  { stdio: ['ignore', logFd, logFd] });
let done = false;
const cleanup = () => {
  if (done) return; done = true;
  if (process.platform === 'win32') spawnSync('taskkill', ['/F', '/T', '/PID', String(chrome.pid)]);
  try { chrome.kill('SIGKILL'); } catch {}
  spawnSync('pkill', ['-f', `user-data-dir=${UD}`]);
  try { fs.rmSync(UD, { recursive: true, force: true }); } catch {}
};
process.on('exit', cleanup);
process.on('SIGINT', () => { cleanup(); process.exit(130); });
process.on('SIGTERM', () => { cleanup(); process.exit(143); });

// runs in the page: the checks, as a list of failure reasons
const CHECK = `(() => {
  const why = [];
  const W = innerWidth, H = innerHeight;
  if (document.documentElement.scrollWidth > W) why.push('page scrollWidth ' + document.documentElement.scrollWidth + ' > ' + W);
  const hdr = document.querySelector('.st-header');
  if (hdr && hdr.scrollWidth > hdr.clientWidth + 1) why.push('header content ' + hdr.scrollWidth + ' > ' + hdr.clientWidth);
  const els = [...document.querySelectorAll('.st-steps > a, .st-steps > span, .st-header .st-btn, .cfg-start')];
  if (!els.length) why.push('no primary controls found');
  for (const el of els) {
    const r = el.getBoundingClientRect();
    const name = (el.textContent || el.className).trim().slice(0, 30);
    if (r.width === 0 || r.height === 0) { why.push(name + ': not displayed'); continue; }
    if (r.left < 0 || r.top < 0 || r.right > W + 0.5 || r.bottom > H + 0.5) { why.push(name + ': outside the viewport ' + [r.left, r.top, r.right, r.bottom].map(Math.round).join(',')); continue; }
    const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
    if (!hit || !(hit === el || el.contains(hit))) why.push(name + ': covered by ' + (hit ? hit.tagName + '.' + hit.className : 'nothing'));
  }
  return JSON.stringify({ status: document.body.dataset.status, why });
})()`;

async function main() {
  let portFile = null;
  for (let i = 0; i < 300 && !portFile; i++) {
    try { const t = fs.readFileSync(path.join(UD, 'DevToolsActivePort'), 'utf8').trim().split('\n'); if (t.length >= 2) portFile = t; } catch {}
    if (!portFile) await sleep(100);
  }
  if (!portFile) throw new Error('Chrome did not write DevToolsActivePort in 30 s');
  const ws = new WebSocket(`ws://127.0.0.1:${portFile[0]}${portFile[1]}`);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = () => rej(new Error('CDP websocket failed')); });
  let id = 0; const pending = new Map();
  ws.onmessage = (ev) => { const m = JSON.parse(ev.data); if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); m.error ? p.rej(new Error(m.error.message)) : p.res(m.result); } };
  const send = (method, params = {}, sessionId) => new Promise((res, rej) => {
    const i = ++id; pending.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method, params, sessionId }));
    setTimeout(() => { if (pending.has(i)) { pending.delete(i); rej(new Error(`${method} timed out`)); } }, 30000);
  });
  const { targetId } = await send('Target.createTarget', { url: 'about:blank' });
  const { sessionId: s } = await send('Target.attachToTarget', { targetId, flatten: true });
  await send('Page.enable', {}, s);
  let ok = 0, total = 0;
  for (const [w, h] of sizes) {
    await send('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: 1, mobile: false }, s);
    for (const q of opt.links) {
      total++;
      const url = new URL('?' + q, opt.base).href;
      // every page the link shows is checked when it is ready: Running is checked, then the Run page it opens by itself
      const why = [];
      try {
        await send('Page.navigate', { url }, s);
        const t0 = Date.now();
        const seen = new Set();
        let status = '', lastPage = '', quietSince = Date.now();
        while (Date.now() - t0 < opt.timeout * 1000) {
          const r = await send('Runtime.evaluate', { expression: 'document.body ? JSON.stringify([document.body.dataset.status || "", document.body.dataset.page || ""]) : "[]"', returnByValue: true }, s);
          const [st, pg] = JSON.parse(r.result.value || '[]');
          status = st;
          if (pg !== lastPage) { lastPage = pg; quietSince = Date.now(); }
          if (st === 'ready' && !seen.has(pg)) {
            seen.add(pg);
            const c = JSON.parse((await send('Runtime.evaluate', { expression: CHECK, returnByValue: true }, s)).result.value);
            why.push(...c.why.map((x) => `${pg}: ${x}`));
          }
          if (st === 'error') break;
          if (st === 'ready' && Date.now() - quietSince > 1500) break;
          await sleep(150);
        }
        if (status !== 'ready') why.push(`status=${status} (${lastPage})`);
      } catch (e) { why.push(`cdp: ${e.message}`); }
      if (!why.length) ok++;
      console.log(`LAYOUT ${w}x${h} ${q} ${why.length ? 'FAIL ' + why.join('; ') : 'ok'}`);
    }
  }
  try { await send('Browser.close'); } catch {}
  console.log(`LAYOUT: ${ok}/${total} ok`);
  return ok === total;
}

const exited = new Promise((r) => chrome.once('exit', r));
const finish = async (code) => { await Promise.race([exited, sleep(3000)]); cleanup(); process.exit(code); };
main().then((allOk) => finish(allOk ? 0 : 1)).catch((e) => { console.log(`LAYOUT: runner error: ${e.message}`); finish(1); });
