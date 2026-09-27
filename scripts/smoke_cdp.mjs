#!/usr/bin/env node
// scripts/smoke_cdp.mjs -- one headless Chrome per run, driven over CDP (node >= 22: global WebSocket + fetch).
// Verified 26 Sep 2026 on node v26.0.0 + Chrome at load ~140 against a deck.gl 9.4.0 page (see OVERNIGHT_BUILD_PROMPT.md 7.5).
// Usage: node scripts/smoke_cdp.mjs --base http://127.0.0.1:<port>/ui/ --shots <dir> [--timeout 20] <query> [<query> ...]
//   each <query> is a deep-link query string without the leading "?", e.g. "view=p1&branch=aware&t=22:30"
// Prints one line per link:  SMOKE <query> ok|FAIL <reasons> | <flags> | <ms> ms | <KB> KB | <colours> colours
// and a final line:          SMOKE: <ok>/<total> ok
// Exit code: 0 if all ok, 1 otherwise (gate on the SMOKE: line, not on this code).
import { spawn, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import zlib from 'node:zlib';

const CHROME = process.env.CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const argv = process.argv.slice(2);
const opt = { base: null, shots: null, timeout: 20, links: [] };
for (let i = 0; i < argv.length; i++) {
  const a = argv[i];
  if (a === '--base') opt.base = argv[++i];
  else if (a === '--shots') opt.shots = argv[++i];
  else if (a === '--timeout') opt.timeout = Number(argv[++i]);
  else opt.links.push(a);
}
if (!opt.base || !opt.shots || !opt.links.length) { console.error('usage: smoke_cdp.mjs --base URL --shots DIR [--timeout S] query...'); process.exit(2); }
fs.mkdirSync(opt.shots, { recursive: true });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const slug = (q) => q.replace(/[^A-Za-z0-9]+/g, '_').replace(/^_|_$/g, '').slice(0, 120) || 'root';

// ---- minimal PNG decode (8-bit RGB/RGBA, non-interlaced: what Page.captureScreenshot returns) ----
function pngColours(buf) {
  let off = 8, w = 0, h = 0, ct = 0; const idat = [];
  while (off < buf.length) {
    const len = buf.readUInt32BE(off), type = buf.toString('ascii', off + 4, off + 8), data = buf.subarray(off + 8, off + 8 + len);
    if (type === 'IHDR') { w = data.readUInt32BE(0); h = data.readUInt32BE(4); ct = data[9]; if (data[8] !== 8 || data[12] !== 0) return -1; }
    if (type === 'IDAT') idat.push(data);
    off += 12 + len;
  }
  const bpp = ct === 6 ? 4 : ct === 2 ? 3 : 0; if (!bpp) return -1;
  const raw = zlib.inflateSync(Buffer.concat(idat)), stride = w * bpp, px = Buffer.alloc(h * stride);
  for (let y = 0; y < h; y++) {
    const f = raw[y * (stride + 1)], src = raw.subarray(y * (stride + 1) + 1, (y + 1) * (stride + 1)), row = y * stride;
    for (let x = 0; x < stride; x++) {
      const a = x >= bpp ? px[row + x - bpp] : 0, b = y ? px[row - stride + x] : 0, c = (y && x >= bpp) ? px[row - stride + x - bpp] : 0;
      let v = src[x];
      if (f === 1) v += a; else if (f === 2) v += b; else if (f === 3) v += (a + b) >> 1;
      else if (f === 4) { const p = a + b - c, pa = Math.abs(p - a), pb = Math.abs(p - b), pc = Math.abs(p - c); v += (pa <= pb && pa <= pc) ? a : (pb <= pc ? b : c); }
      px[row + x] = v & 255;
    }
  }
  const seen = new Set();
  for (let y = 0; y < h; y += 8) for (let x = 0; x < w; x += 8) { const i = y * stride + x * bpp; seen.add((px[i] << 16) | (px[i + 1] << 8) | px[i + 2]); }
  return seen.size;
}

// ---- launch one Chrome; its output goes to a file, never a pipe ----
const UD = fs.mkdtempSync(path.join(process.env.SMOKE_TMP || os.tmpdir(), 'chrome.'));
const logFd = fs.openSync(path.join(UD, 'chrome.log'), 'w');
const chrome = spawn(CHROME, ['--headless=new', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', `--user-data-dir=${UD}`,
  '--no-first-run', '--no-default-browser-check', '--remote-debugging-port=0', '--window-size=1920,1080', 'about:blank'],
  { stdio: ['ignore', logFd, logFd] });
let done = false;
const cleanup = () => {
  if (done) return; done = true;
  try { chrome.kill('SIGKILL'); } catch {}
  spawnSync('pkill', ['-f', `user-data-dir=${UD}`]);        // orphaned helpers (NetworkService) outlive the main process
  try { fs.rmSync(UD, { recursive: true, force: true }); } catch {}
};
process.on('exit', cleanup);
process.on('SIGINT', () => { cleanup(); process.exit(130); });
process.on('SIGTERM', () => { cleanup(); process.exit(143); });

async function main() {
  let portFile = null;
  for (let i = 0; i < 300 && !portFile; i++) {            // up to 30 s for Chrome to start under load
    try { const t = fs.readFileSync(path.join(UD, 'DevToolsActivePort'), 'utf8').trim().split('\n'); if (t.length >= 2) portFile = t; } catch {}
    if (!portFile) await sleep(100);
  }
  if (!portFile) throw new Error('Chrome did not write DevToolsActivePort in 30 s (see ' + path.join(UD, 'chrome.log') + ')');
  const ws = new WebSocket(`ws://127.0.0.1:${portFile[0]}${portFile[1]}`);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = () => rej(new Error('CDP websocket failed')); });
  let id = 0; const pending = new Map();
  // console errors of the page under test (console.error, uncaught exceptions, failed loads such as a 404)
  const consoleErrors = [];
  ws.onmessage = (ev) => {
    const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); m.error ? p.rej(new Error(m.error.message)) : p.res(m.result); return; }
    if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') consoleErrors.push((m.params.args || []).map((a) => a.value ?? a.description ?? '').join(' '));
    else if (m.method === 'Runtime.exceptionThrown') consoleErrors.push((m.params.exceptionDetails && (m.params.exceptionDetails.exception || {}).description) || 'exception');
    else if (m.method === 'Log.entryAdded' && m.params.entry.level === 'error') consoleErrors.push(`${m.params.entry.text}${m.params.entry.url ? ' ' + m.params.entry.url : ''}`);
  };
  const send = (method, params = {}, sessionId) => new Promise((res, rej) => { const i = ++id; pending.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method, params, sessionId })); });

  // wait for the static server (the caller started it)
  for (let i = 0; i < 100; i++) { try { const r = await fetch(opt.base); if (r.ok) break; } catch {} await sleep(100); }
  const has = async (p) => { try { return (await fetch(new URL(p, opt.base))).ok; } catch { return false; } };
  const realP1 = await has('data/p1/meta.json'), realP2 = await has('data/p2/index.json');

  const { targetId } = await send('Target.createTarget', { url: 'about:blank' });
  const { sessionId: s } = await send('Target.attachToTarget', { targetId, flatten: true });
  await send('Page.enable', {}, s);
  await send('Runtime.enable', {}, s);
  await send('Log.enable', {}, s);
  await send('Emulation.setDeviceMetricsOverride', { width: 1920, height: 1080, deviceScaleFactor: 1, mobile: false }, s);

  let ok = 0;
  for (const q of opt.links) {
    // page= links open the story app (ui/index.html); view=/beat= links the engine explorer (ui/explore.html)
    const story = /(^|&)page=/.test(q) || !/(^|&)(view|beat)=/.test(q);
    const t0 = Date.now(), url = new URL((story ? '' : 'explore.html') + '?' + q, opt.base).href, why = [];
    let flags = null;
    // one retry at twice the timeout if the page never settles (machine load, not a verdict)
    for (let attempt = 0, lim = opt.timeout; attempt < 2; attempt++, lim *= 2) {
      try {
        const ta = Date.now();
        consoleErrors.length = 0;
        await send('Page.navigate', { url }, s);
        while (Date.now() - ta < lim * 1000) {
          const r = await send('Runtime.evaluate', { expression: 'document.body ? JSON.stringify(Object.assign({}, document.body.dataset)) : "null"', returnByValue: true }, s);
          flags = JSON.parse(r.result.value || 'null');
          if (flags && (flags.status === 'ready' || flags.status === 'error')) break;
          await sleep(250);
        }
      } catch (e) { why.push('cdp:' + e.message); break; }
      if (flags && (flags.status === 'ready' || flags.status === 'error')) break;
    }
    const f = flags || {};
    // the story app draws a scene on Run only (Running hands over to Run by itself: either flag is fine there)
    const page = story ? ((q.match(/(^|&)page=([a-z]+)/) || [])[2] || 'configure') : null;
    const scene = !story || page === 'run';
    const wantWebgl = !scene ? (page === 'running' ? /^(none|ok)$/ : /^none$/) : /(^|&)nowebgl=1(&|$)/.test(q) ? /^fallback$/ : /^ok$/;
    const view = (q.match(/(^|&)view=([a-z0-9]+)/) || [])[2];
    if (f.status !== 'ready') why.push(`status=${f.status ?? 'none'}`);
    if (f.errors !== '0') why.push(`errors=${f.errors ?? 'none'}`);
    if (f.offsite !== '0') why.push(`offsite=${f.offsite ?? 'none'}`);
    if (!wantWebgl.test(f.webgl ?? '')) why.push(`webgl=${f.webgl ?? 'none'}(want ${wantWebgl.source})`);
    if ((view === 'p1' && realP1) || (view === 'p2' && realP2)) { if (f.fixture !== '0') why.push(`fixture=${f.fixture ?? 'none'}(real data exists)`); }
    let kb = 0, colours = 0;
    if (f.status === 'ready') {
      try {
        await sleep(400);                                    // let one more frame land after "ready"
        const shot = await send('Page.captureScreenshot', { format: 'png' }, s);
        const buf = Buffer.from(shot.data, 'base64');
        fs.writeFileSync(path.join(opt.shots, slug(q) + '.png'), buf);
        kb = Math.round(buf.length / 1024); colours = pngColours(buf);
        // a story page not merged yet (UI-B) is a mostly empty placeholder by design: its size says nothing
        if (!f.placeholder && buf.length < 50 * 1024) why.push(`shot ${kb} KB < 50 KB`);
        if (!f.placeholder && colours >= 0 && colours < 16) why.push(`shot has ${colours} colours (blank?)`);
      } catch (e) { why.push('shot:' + e.message); }
    }
    if (consoleErrors.length) why.push(`console=${consoleErrors.length} (${consoleErrors[0].slice(0, 160)})`);
    const pass = why.length === 0; if (pass) ok++;
    const fl = ['status', 'webgl', 'errors', 'fixture', 'offsite'].map((k) => `${k}=${f[k] ?? '-'}`).join(' ') + (f.placeholder ? ` placeholder=${f.placeholder}` : '');
    console.log(`SMOKE ${q} ${pass ? 'ok' : 'FAIL ' + why.join(',')} | ${fl} | ${Date.now() - t0} ms | ${kb} KB | ${colours} colours`);
  }
  try { await send('Browser.close'); } catch {}
  console.log(`SMOKE: ${ok}/${opt.links.length} ok`);
  return ok === opt.links.length;
}

const exited = new Promise((r) => chrome.once('exit', r));
const finish = async (code) => { await Promise.race([exited, sleep(3000)]); cleanup(); process.exit(code); };
main().then((allOk) => finish(allOk ? 0 : 1))
  .catch((e) => { console.log(`SMOKE: 0/${opt.links.length} ok (runner error: ${e.message})`); finish(1); });
