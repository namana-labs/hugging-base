#!/usr/bin/env node
// scripts/smoke_layout.mjs (UI-A) -- the story pages' layout at the demo sizes, in one headless Chrome over CDP.
// For each size x link: the page reaches data-status=ready, nothing overflows horizontally (page, header, footer)
// (document.documentElement.scrollWidth <= innerWidth), and every primary control -- the step nav, "Start the sim ->",
// "Continue to ..." -- and every header/footer link (the Engine explorer) lies inside the viewport and is the element
// hit at its centre (elementFromPoint); no provenance tag is cut by a clipping ancestor, even once scrolled into view
// (content below a scroll container's fold is not a cut); on Configure every lever group,
// evening and fixed input is in the page flow (no inner scroll) and reachable by scrolling the page.
// Usage: node scripts/smoke_layout.mjs --base http://127.0.0.1:8801/ui/ [--sizes 1280x800,1440x900,1920x1080]
//        [--timeout 40] <query> [<query> ...]
// Prints: LAYOUT <WxH> <query> ok|FAIL <reasons>, then LAYOUT: <ok>/<total> ok. Exit 0 when all pass.
// node >= 22 (global WebSocket), or node 20 with NODE_OPTIONS=--experimental-websocket; CHROME = the Chrome binary.
import { spawn, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

// Chrome: env CHROME, else the first of the usual install paths that exists (macOS, Windows, Linux)
const CHROME_PATHS = [process.env.CHROME, '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  'C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
  '/usr/bin/google-chrome', '/usr/bin/chromium'].filter(Boolean);
const CHROME = CHROME_PATHS.find((p) => fs.existsSync(p));
if (!CHROME) {
  console.error(`No Chrome found. Set CHROME to the Chrome binary; tried: ${CHROME_PATHS.join(', ')}`);
  process.exit(2);
}
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
  const ftr = document.querySelector('.st-footer');
  if (ftr && ftr.scrollWidth > ftr.clientWidth + 1) why.push('footer content ' + ftr.scrollWidth + ' > ' + ftr.clientWidth);
  // every primary control and every header/footer link (the body clips, so scrollWidth alone cannot see these)
  const els = [...new Set([...document.querySelectorAll('.st-steps > a, .st-steps > span, .st-header .st-btn, .cfg-start, .st-header a, .st-footer a, .st-explorer')])];
  if (!els.length) why.push('no primary controls found');
  if (!document.querySelector('.st-explorer')) why.push('no Engine explorer link');
  const hitOK = (el) => {
    const r = el.getBoundingClientRect();
    const name = (el.textContent || el.className).trim().slice(0, 30);
    if (r.width === 0 || r.height === 0) return name + ': not displayed';
    if (r.left < 0 || r.top < 0 || r.right > W + 0.5 || r.bottom > H + 0.5) return name + ': outside the viewport ' + [r.left, r.top, r.right, r.bottom].map(Math.round).join(',');
    const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
    return !hit || !(hit === el || el.contains(hit)) ? name + ': covered by ' + (hit ? hit.tagName + '.' + hit.className : 'nothing') : null;
  };
  for (const el of els) { const w = hitOK(el); if (w) why.push(w); }
  // a provenance tag is never cut. A tag outside a clipping ancestor (overflow not visible) is a cut only when no
  // scrolling can show it: if an ancestor scrolls (overflow auto/scroll with more content than room) or the page
  // scrolls, the tag is scrolled into view and tested again (content below a scroll container's fold is not a cut).
  const scrolls = (a) => {
    const cs = getComputedStyle(a);
    return (/auto|scroll/.test(cs.overflowY) && a.scrollHeight > a.clientHeight + 1) || (/auto|scroll/.test(cs.overflowX) && a.scrollWidth > a.clientWidth + 1);
  };
  const cutBy = (c) => {
    const r = c.getBoundingClientRect();
    if (r.right > W + 0.5 || r.left < -0.5) return 'the viewport (x ' + Math.round(r.left) + ')';
    for (let a = c.parentElement; a && a !== document.body; a = a.parentElement) {
      const cs = getComputedStyle(a);
      const cx = cs.overflowX !== 'visible', cy = cs.overflowY !== 'visible';
      if (!cx && !cy) continue;
      const ar = a.getBoundingClientRect();
      if ((cx && (r.left < ar.left - 0.5 || r.right > ar.right + 0.5)) || (cy && (r.top < ar.top - 0.5 || r.bottom > ar.bottom + 0.5))) {
        return a.tagName + '.' + String(a.className).split(' ')[0];
      }
    }
    return null;
  };
  const saved = new Map();          // scroll positions to restore after the check
  const page = document.scrollingElement;
  for (const c of document.querySelectorAll('.chip')) {
    const r = c.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    let by = cutBy(c);
    if (!by) continue;
    const chain = [];
    for (let a = c.parentElement; a; a = a.parentElement) {
      const pageScrolls = a === page && (page.scrollHeight > page.clientHeight + 1 || page.scrollWidth > page.clientWidth + 1);
      if (pageScrolls || (a !== page && scrolls(a))) chain.push(a);
    }
    if (chain.length) {
      for (const a of chain) if (!saved.has(a)) saved.set(a, [a.scrollTop, a.scrollLeft]);
      c.scrollIntoView({ block: 'nearest', inline: 'nearest' });
      by = cutBy(c);
      if (!by) continue;
    }
    why.push('tag ' + c.textContent + ' cut by ' + by + (chain.length ? ' even when scrolled into view' : '') + ' near "' + (c.parentElement.textContent || '').trim().slice(0, 40) + '"');
  }
  for (const [a, [t, l]] of saved) { a.scrollTop = t; a.scrollLeft = l; }
  // Configure: every lever group, evening and fixed input is in the page flow (no inner scroll) and reachable by
  // scrolling the page, where it is the element hit at its centre (not under the sticky start bar)
  if (document.body.dataset.page === 'configure') {
    const main = document.querySelector('main.st-main');
    const groups = [...document.querySelectorAll('.cfg-card[data-lever], .cfg-evenings > .cfg-opt, .cfg-fixed .cfg-fx')];
    if (!groups.length) why.push('configure: no lever groups found');
    for (const g of groups) {
      const name = (g.dataset.lever || g.textContent || '').trim().slice(0, 24);
      let inner = null;
      for (let a = g.parentElement; a && a !== main; a = a.parentElement) {
        const cs = getComputedStyle(a);
        if (/auto|scroll|hidden|clip/.test(cs.overflowY) && a.scrollHeight > a.clientHeight + 1) { inner = a; break; }
      }
      if (inner) { why.push('configure: ' + name + ' sits in an inner scroll (' + String(inner.className).split(' ')[0] + ')'); continue; }
      g.scrollIntoView({ block: 'center' });
      const r = g.getBoundingClientRect();
      const hit = document.elementFromPoint(r.left + Math.min(24, r.width / 2), r.top + Math.min(24, r.height / 2));
      if (!hit || !(hit === g || g.contains(hit))) why.push('configure: ' + name + ' not reachable by page scroll (hit ' + (hit ? hit.tagName + '.' + hit.className : 'nothing') + ')');
    }
    if (main) main.scrollTop = 0;
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
