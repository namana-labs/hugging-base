#!/usr/bin/env node
// hover.mjs (R2 scene design prototype): load one page in headless Chrome (SwiftShader), wait for body data-status=ready,
// move the mouse to the screen point a JS expression returns, wait, and screenshot. Proves deck.gl getTooltip works.
// Usage: node hover.mjs <url> <out.png> "<js expr returning [x,y] or null>"
import { spawn, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
const [url, out, expr] = process.argv.slice(2);
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const UD = fs.mkdtempSync(path.join(process.env.SMOKE_TMP || os.tmpdir(), 'chrome.'));
const chrome = spawn(CHROME, ['--headless=new', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', `--user-data-dir=${UD}`, '--no-first-run',
  '--no-default-browser-check', '--remote-debugging-port=0', '--window-size=1920,1080', 'about:blank'], { stdio: 'ignore' });
const cleanup = () => { try { chrome.kill('SIGKILL'); } catch {} spawnSync('pkill', ['-f', `user-data-dir=${UD}`]); try { fs.rmSync(UD, { recursive: true, force: true }); } catch {} };
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
await send('Page.navigate', { url }, s);
const ev = async (e) => (await send('Runtime.evaluate', { expression: e, returnByValue: true, awaitPromise: true }, s)).result.value;
for (let i = 0; i < 900; i++) { if ((await ev('document.body && document.body.dataset.status')) === 'ready') break; await sleep(100); }
await sleep(800);
const pt = await ev(expr);
if (pt) {
  for (const [dx, dy] of [[-30, -30], [-10, -10], [0, 0]]) { await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: pt[0] + dx, y: pt[1] + dy }, s); await sleep(250); }
  await sleep(1500);
}
const shot = await send('Page.captureScreenshot', { format: 'png' }, s);
fs.writeFileSync(out, Buffer.from(shot.data, 'base64'));
console.log('HOVER', JSON.stringify(pt), await ev('(document.querySelector(".deck-tooltip")||{}).innerText || "(no tooltip)"'), '|', await ev('document.getElementById("stat") ? document.getElementById("stat").textContent : ""'));
cleanup();
process.exit(0);
