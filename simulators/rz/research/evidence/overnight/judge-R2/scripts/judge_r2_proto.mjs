// Judge R2: prototype render check; adapted from the screen reader. Read what each deep link puts on screen (body innerText + health flags), for the screen == JSON check.
// Usage: node judge_r1_screen.mjs <base-url> <out-dir> <query>...   One headless Chrome over CDP (same launch as scripts/smoke_cdp.mjs).
import { spawn, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
const [base, outDir, ...queries] = process.argv.slice(2);
fs.mkdirSync(outDir, { recursive: true });
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const UD = fs.mkdtempSync(path.join(process.env.SMOKE_TMP || os.tmpdir(), 'chrome.'));
const logFd = fs.openSync(path.join(UD, 'chrome.log'), 'w');
const chrome = spawn(CHROME, ['--headless=new', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', `--user-data-dir=${UD}`,
  '--no-first-run', '--no-default-browser-check', '--remote-debugging-port=0', '--window-size=1920,1080', 'about:blank'],
  { stdio: ['ignore', logFd, logFd] });
const cleanup = () => { try { chrome.kill('SIGKILL'); } catch {} spawnSync('pkill', ['-f', `user-data-dir=${UD}`]); try { fs.rmSync(UD, { recursive: true, force: true }); } catch {} };
process.on('exit', cleanup);
let portFile = null;
for (let i = 0; i < 300 && !portFile; i++) { try { const t = fs.readFileSync(path.join(UD, 'DevToolsActivePort'), 'utf8').trim().split('\n'); if (t.length >= 2) portFile = t; } catch {} if (!portFile) await sleep(100); }
const ws = new WebSocket(`ws://127.0.0.1:${portFile[0]}${portFile[1]}`);
await new Promise((res, rej) => { ws.onopen = res; ws.onerror = () => rej(new Error('ws')); });
let id = 0; const pending = new Map();
ws.onmessage = (ev) => { const m = JSON.parse(ev.data); if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); m.error ? p.rej(new Error(m.error.message)) : p.res(m.result); } };
const send = (method, params = {}, sessionId) => new Promise((res, rej) => { const i = ++id; pending.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method, params, sessionId })); });
const { targetId } = await send('Target.createTarget', { url: 'about:blank' });
const { sessionId: s } = await send('Target.attachToTarget', { targetId, flatten: true });
await send('Page.enable', {}, s);
await send('Emulation.setDeviceMetricsOverride', { width: 1920, height: 1080, deviceScaleFactor: 1, mobile: false }, s);
const url = base;
await send('Page.navigate', { url }, s);
await sleep(6000);
const r = await send('Runtime.evaluate', { returnByValue: true, expression:
  `JSON.stringify({circles: document.querySelectorAll('circle').length, paths: document.querySelectorAll('path').length, title: document.title,
    offsite: performance.getEntriesByType('resource').filter(e => !e.name.startsWith(location.origin)).map(e => e.name.slice(0, 40))})` }, s);
const o = JSON.parse(r.result.value);
const shot = await send('Page.captureScreenshot', { format: 'png' }, s);
const buf = Buffer.from(shot.data, 'base64');
fs.writeFileSync(path.join(outDir, 'proto_grid_stories.png'), buf);
console.log(`PROTO ${url} circles=${o.circles} paths=${o.paths} offsite=${o.offsite.length} ${JSON.stringify(o.offsite)} title="${o.title}" shot=${Math.round(buf.length/1024)} KB`);
process.exit(0);
