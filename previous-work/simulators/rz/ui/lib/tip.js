// ui/lib/tip.js (L0): one floating tooltip for the whole page (UX_SPEC_R2 4.2.2, UX-R2-clarity 4.2). Hover explanations
// replace explanation buttons: every provenance tag, icon and 3D object explains itself on hover (or focus, or a tap).
//
//   mountTips(doc)          idempotent; delegated pointerover/pointerout/pointermove/focusin/focusout on the document
//   showTip(html, x, y)     for the scene's own hover (deck.gl onHover): x, y are viewport (client) pixels of the pointer
//   hideTip()
//   tipHTMLFor(el)          what an element's tip says (pure: works on any object with getAttribute + classList)
//
// What shows a tip, first match wins, walking up from the pointer's target:
//   [data-tip-html]  HTML our own code built from labelled values (never data from a file as raw HTML)
//   [data-tip]       plain text (escaped)
//   .chip            the provenance tag: LABEL_TIPS[label] in bold, then the number's cite
//   [title]          any existing title: on first hover it moves to data-cite, so the slow native tooltip never doubles
// Nothing here touches the DOM at import, so node tests can import it.

export const LABEL_TIPS = {
  REAL: 'REAL: measured or published data (ERCOT prices, NREL SMART-DS feeder, OpenStreetMap, sourced facts).',
  SIM: 'SIM: our simulation (OpenDSS power flow + our controller). Not a measurement.',
  DERIVED: 'DERIVED: arithmetic on REAL or SIM numbers (for example dollars = kW × price).',
  ASSUMPTION: 'ASSUMPTION: a value we chose because the real one is not public.',
};
export const SHOW_DELAY_MS = 80;
export const OFFSET_PX = 14;
const SELECTOR = '[data-tip-html],[data-tip],.chip,[title],[data-cite]';

const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const attr = (el, k) => (el && typeof el.getAttribute === 'function' ? el.getAttribute(k) : null);
const hasClass = (el, c) => !!(el && el.classList && typeof el.classList.contains === 'function' && el.classList.contains(c));

/** The label of a provenance tag element (from its chip-<LABEL> class, else its text). */
export function chipLabel(el) {
  const cls = String(attr(el, 'class') || '');
  const m = /\bchip-(REAL|SIM|DERIVED|ASSUMPTION)\b/.exec(cls);
  if (m) return m[1];
  const t = String((el && el.textContent) || '').trim();
  return LABEL_TIPS[t] ? t : null;
}

/** The tooltip HTML for an element, or null when it has nothing to say. */
export function tipHTMLFor(el) {
  if (!el) return null;
  const html = attr(el, 'data-tip-html');
  if (html) return html;
  const text = attr(el, 'data-tip');
  if (text) return esc(text);
  const cite = attr(el, 'data-cite') || attr(el, 'title');
  if (hasClass(el, 'chip')) {
    const label = chipLabel(el);
    const head = label ? `<div class="tip-h">${esc(LABEL_TIPS[label])}</div>` : '';
    const sub = cite ? `<div class="tip-sub">${esc(cite)}</div>` : '';
    return head + sub || null;
  }
  return cite ? esc(cite) : null;
}

/** Speed button copy (6.5): at 1x one step (a simulated minute) plays every msPerStep ms. */
export function speedTip(speed, { msPerStep = 100, steps = 720, stepSeconds = 60 } = {}) {
  const perSec = (1000 / msPerStep) * speed * (stepSeconds / 60);
  const minutes = Number.isInteger(perSec) ? String(perSec) : perSec.toFixed(1).replace(/\.0$/, '');
  const total = Math.round(steps / ((1000 / msPerStep) * speed));
  const span = total >= 120 ? `${Math.floor(total / 60)} min${total % 60 ? ` ${total % 60} s` : ''}` : `${total} s`;
  return `${speed}×: ${minutes} simulated minute${perSec === 1 ? '' : 's'} per second (the evening in ${span})`;
}

// ---- the DOM half -------------------------------------------------------------------------------------------------
const st = { doc: null, el: null, timer: null, anchor: null, x: 0, y: 0, shownFor: null };

function tipEl() {
  if (st.el && st.el.isConnected) return st.el;
  const d = st.doc || globalThis.document;
  st.el = d.createElement('div');
  st.el.className = 'hb-tip';
  st.el.setAttribute('role', 'tooltip');
  st.el.id = 'hb-tip';
  d.body.appendChild(st.el);
  return st.el;
}

function place(x, y) {
  const el = tipEl();
  const w = el.offsetWidth, h = el.offsetHeight;
  const vw = globalThis.innerWidth || 1024, vh = globalThis.innerHeight || 768;
  let left = x + OFFSET_PX, top = y + OFFSET_PX;
  if (left + w > vw - 8) left = Math.max(8, x - OFFSET_PX - w);     // flip left at the right edge
  if (top + h > vh - 8) top = Math.max(8, y - OFFSET_PX - h);       // flip up at the bottom edge
  el.style.left = `${Math.round(left)}px`;
  el.style.top = `${Math.round(top)}px`;
}

/** Show `html` (built by our code) near viewport point (x, y). */
export function showTip(html, x, y) {
  if (!html) { hideTip(); return; }
  const el = tipEl();
  if (el.innerHTML !== html) el.innerHTML = html;
  el.classList.add('on');
  st.x = x; st.y = y;
  place(x, y);
}

export function hideTip() {
  clearTimeout(st.timer);
  st.timer = null;
  st.anchor = null;
  st.shownFor = null;
  if (st.el) st.el.classList.remove('on');
}

function anchorOf(target) {
  const el = target && typeof target.closest === 'function' ? target.closest(SELECTOR) : null;
  if (!el || el.closest('.hb-tip')) return null;
  if (el.hasAttribute('title')) {             // move the native title out of the way (instant tip, no double)
    el.setAttribute('data-cite', el.getAttribute('title'));
    el.removeAttribute('title');
  }
  return el;
}

function schedule(el, x, y) {
  clearTimeout(st.timer);
  st.anchor = el;
  st.x = x; st.y = y;
  st.timer = setTimeout(() => {
    if (st.anchor !== el) return;
    st.shownFor = el;
    showTip(tipHTMLFor(el), st.x, st.y);
  }, SHOW_DELAY_MS);
}

function focusPoint(el) {
  const r = el.getBoundingClientRect();
  return [r.left, r.bottom - OFFSET_PX + 4];
}

/** Install the delegated handlers once per document. Returns a function that removes them. */
export function mountTips(doc = globalThis.document) {
  if (!doc || doc.__hbTips) return doc && doc.__hbTips;
  st.doc = doc;
  const on = (type, fn, opts) => { doc.addEventListener(type, fn, opts); return () => doc.removeEventListener(type, fn, opts); };
  const offs = [
    on('pointerover', (e) => {
      if (e.pointerType === 'touch') return;
      const el = anchorOf(e.target);
      if (el && el !== st.anchor) schedule(el, e.clientX, e.clientY);
    }),
    on('pointermove', (e) => {
      if (!st.anchor || e.pointerType === 'touch') return;
      st.x = e.clientX; st.y = e.clientY;
      if (st.shownFor) place(st.x, st.y);
    }, { passive: true }),
    on('pointerout', (e) => {
      if (!st.anchor || e.pointerType === 'touch') return;
      if (e.relatedTarget && st.anchor.contains(e.relatedTarget)) return;
      if (e.target === st.anchor || st.anchor.contains(e.target)) hideTip();
    }),
    on('pointerdown', (e) => {                // touch: a tap toggles the tip of what was tapped
      if (e.pointerType !== 'touch') { if (st.shownFor && !anchorOf(e.target)) hideTip(); return; }
      const el = anchorOf(e.target);
      if (!el) { hideTip(); return; }
      if (st.shownFor === el) { hideTip(); return; }
      st.anchor = el; st.shownFor = el;
      showTip(tipHTMLFor(el), e.clientX, e.clientY);
    }),
    on('focusin', (e) => {
      const el = anchorOf(e.target);
      if (!el) return;
      const [x, y] = focusPoint(el);
      schedule(el, x, y);
    }),
    on('focusout', (e) => { if (st.anchor && (e.target === st.anchor || st.anchor.contains(e.target))) hideTip(); }),
    on('keydown', (e) => { if (e.key === 'Escape') hideTip(); }),
    on('scroll', () => { if (st.shownFor) hideTip(); }, { capture: true, passive: true }),
  ];
  const off = () => { offs.forEach((f) => f()); doc.__hbTips = null; hideTip(); };
  doc.__hbTips = off;
  return off;
}
