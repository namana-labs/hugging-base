// Judge R0: does /demos/grid-stories/ui/dist/ still render from the root static server? (build prompt 7.5)
// Usage: node judge_r0_protocheck.mjs <url> <shot.png>. One headless Chrome over CDP (same launch as scripts/smoke_cdp.mjs).
import { spawn, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
const [url, shotPath] = process.argv.slice(2);
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
await send('Page.navigate', { url }, s);
let res = null;
const t0 = Date.now();
while (Date.now() - t0 < 20000) {
  const r = await send('Runtime.evaluate', { returnByValue: true, expression:
    `JSON.stringify({circles: document.querySelectorAll('circle').length, paths: document.querySelectorAll('path').length,
      title: document.title, offsite: performance.getEntriesByType('resource').filter(e => new URL(e.name).origin !== location.origin).length})` }, s);
  res = JSON.parse(r.result.value);
  if (res.circles > 100) break;
  await sleep(500);
}
await sleep(500);
const shot = await send('Page.captureScreenshot', { format: 'png' }, s);
fs.writeFileSync(shotPath, Buffer.from(shot.data, 'base64'));
console.log(`PROTO ${url} circles=${res.circles} paths=${res.paths} offsite=${res.offsite} title="${res.title}" shot=${Math.round(Buffer.from(shot.data, 'base64').length / 1024)} KB`);
process.exit(0);
