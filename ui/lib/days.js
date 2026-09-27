// ui/lib/days.js (L0): the P1 day picker (UX_SPEC_R2 4.3, HIST-R2 7.1). Real ERCOT evenings, simulated on our feeder.
//   dayChipHTML(index, date)   the chip: calendar icon, "Wed 22 Jul 2026 · Texas's record demand ▾", an R tag on the date
//   dayRowsHTML(index, date)   the popover rows, from p1/days/index.json ONLY (it never loads a branch file)
//   calendarStripHTML(calendar, date)   the money strip: every real evening's one-Core cycle from p1/days/calendar.json
//   mountDayPicker(el, {index, calendar, date, onPick})   the DOM half; l4 places it (the Day + scenario card)
// Every number goes through fmt with the label the index carries; the weekday is computed from the date, never typed.
// index = p1/days/index.json (docs/contracts.md A.10) or null before l2 builds it: then the chip shows the date alone.
import * as fmt from './format.js';
import { svg } from './icons.js';
import { DEFAULT_DATE } from './data.js';

const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
export const DATE_CITE = 'The evening\'s prices are ERCOT LZ_NORTH for this real date (REAL); the load is the 2018 SMART-DS weather year paired by calendar date (ASSUMPTION), which can fall on a different weekday, and the SMART-DS clock has no daylight-saving shift, so the loads may sit one hour early against the CDT prices (unverified).';

/**
 * Data-truth fix list #9 (DATA-TRUTH-inputs problem 7): prices on this date, home loads on the SMART-DS weather year's
 * same calendar date (LOAD_PAIRING, ASSUMPTION). The two weekdays can differ (23 Aug 2026 is a Sunday on a Thursday's
 * load), and the SMART-DS series has 365 x 96 values, so no daylight-saving shift (PROFILE_INDEX_RULE, unverified): its
 * clock may run one hour early against the CDT prices. The load year is read from the LOAD_PAIRING constant a data
 * file exports (p1/meta.json or p1/days/index.json `constants`); both weekdays are computed, never typed. Plain text
 * (a data-tip or a chip cite); null without a date.
 */
export function loadPairingNote(iso, consts) {
  if (!fmt.dateLabel(iso)) return null;
  const pairing = consts && consts.LOAD_PAIRING && String(consts.LOAD_PAIRING.value || '');
  const y = pairing ? /\b(\d{4})\b/.exec(pairing) : null;
  const clock = 'The SMART-DS series has no daylight-saving shift, so its clock may run one hour early against the CDT '
    + 'prices (PROFILE_INDEX_RULE, unverified).';
  if (!y) return `Home loads are the same calendar date in the SMART-DS weather year, which can fall on a different weekday (LOAD_PAIRING, ASSUMPTION). ${clock}`;
  const a = fmt.dateLabel(iso).split(' ')[0];
  const b = fmt.dateLabel(`${y[1]}${String(iso).slice(4, 10)}`).split(' ')[0];
  return `Prices are this ${a}'s (REAL); home loads are the same calendar date in the SMART-DS ${y[1]} year, a ${b}`
    + `${a === b ? '' : ', a different weekday'} (LOAD_PAIRING, ASSUMPTION). ${clock}`;
}
const rows = (index) => (index && Array.isArray(index.days) ? index.days : []);
export const dayRow = (index, date) => rows(index).find((d) => d.date === date) || null;

/** 48 prices -> a 60 x 14 sparkline (REAL; the label comes from index.series.sparkline). Pure string. */
export function sparklineSVG(values, { w = 60, h = 14 } = {}) {
  const v = (values || []).filter((x) => typeof x === 'number' && Number.isFinite(x));
  if (v.length < 2) return '';
  const lo = Math.min(...v), hi = Math.max(...v), span = hi - lo || 1;
  const pts = v.map((x, i) => `${(i * (w - 2) / (v.length - 1) + 1).toFixed(1)},${(h - 1 - (x - lo) * (h - 2) / span).toFixed(1)}`).join(' ');
  return `<svg class="hb-spark" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" aria-hidden="true"><polyline points="${pts}" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/></svg>`;
}

/** The chip (a button's inner HTML). */
export function dayChipHTML(index, date = DEFAULT_DATE) {
  const row = dayRow(index, date);
  const label = fmt.dateLabel(date) || esc(date);
  const tag = row && row.tag ? ` · <span class="hb-day-tag">${esc(row.tag)}</span>` : '';
  const caret = rows(index).length > 1 ? `<span class="hb-day-caret" aria-hidden="true">▾</span>` : '';
  const cite = (index && index.constants && loadPairingNote(date, index.constants)) || DATE_CITE;
  return `${svg('calendar', { size: 16 })}<span class="hb-day-date">${esc(label)}</span>${fmt.chip('REAL', cite === DATE_CITE ? cite : `ERCOT LZ_NORTH prices for this real date (REAL). ${cite}`)}${tag}${caret}`;
}

function naiveMeter(row) {
  const nm = row.naiveMax;
  if (!fmt.isLabelled(nm)) return '';
  const where = nm.tf != null ? ` on ${esc(typeof nm.tf === 'number' ? `T-${nm.tf}` : nm.tf)}` : '';   // T-<index>, as T-240
  const when = nm.t ? ` at ${esc(nm.t)}` : '';
  const tip = `<b>Naive: the worst transformer</b><br>${fmt.fmtHTML(nm, { unit: '%' })}${where}${when}`;
  // colour from the index's own tier code when it carries one; otherwise the emergency red the design asks for (a picture
  // of "naive overloads"); the % itself is in the tooltip and never re-derived here
  return `<span class="hb-day-naive" data-tip-html="${esc(tip)}" tabindex="0">${svg('meter', { size: 18, pct: nm.v, tier: nm.tier ?? 4 })}</span>`;
}

function awareCheck(row) {
  const n = row.awareBatteryCaused;
  if (!fmt.isLabelled(n)) return '';
  const tip = 'Feeder-aware: transformer overloads caused by batteries this evening';
  return `<span class="hb-day-aware" data-tip="${esc(tip)}" tabindex="0">${svg(n.v === 0 ? 'check' : 'warn', { size: 16 })}${fmt.fmtHTML(n)}</span>`;
}

function money(row) {
  const pb = row.perBattery && row.perBattery.aware;
  if (!fmt.isLabelled(pb)) return '';
  return `<span class="hb-day-money" data-tip="Feeder-aware: money per battery from the price difference this evening (gross, not Base's profit)" tabindex="0">${svg('money', { size: 16 })}${fmt.fmtHTML(pb, { money: true, digits: 2 })}</span>`;
}

/** The popover rows (inner HTML of the list). The current date is marked aria-current. */
export function dayRowsHTML(index, date = DEFAULT_DATE) {
  const sparkLabel = index && index.series && index.series.sparkline ? index.series.sparkline.label : null;
  return rows(index).map((row) => {
    const cur = row.date === date ? ' aria-current="true"' : '';
    const spark = sparklineSVG(row.sparkline);
    const sparkTip = sparkLabel ? ` data-tip="${esc(`ERCOT LZ_NORTH price, 16:00 to 04:00 (${sparkLabel})`)}" tabindex="0"` : '';
    return `<li><button type="button" class="hb-dayrow" data-date="${esc(row.date)}"${cur}>`
      + `<span class="hb-dayrow-d"><b>${esc(fmt.dateLabel(row.date) || row.date)}</b><span class="hb-day-tag">${esc(row.tag || '')}</span></span>`
      + `<span class="hb-dayrow-spark"${sparkTip}>${spark}</span>`
      + `${money(row)}${naiveMeter(row)}${awareCheck(row)}</button></li>`;
  }).join('');
}

// ---- the money calendar strip (HIST-R2 7.1, Should): one cell per evening from p1/days/calendar.json (A.9h) --------
const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const LOSE_RGB = [125, 147, 178], ZERO_RGB = [236, 233, 224], GAIN_RGB = [184, 134, 11];
const mix = (a, b, t) => a.map((x, i) => Math.round(x + (b[i] - x) * t));
/** A cell's colour: losing evenings a flat cool colour; earning evenings a gold ramp (sqrt of net over the year's max). */
export function netColour(net, max) {
  if (net === null || net === undefined) return null;
  if (net < 0) return LOSE_RGB;
  return mix(ZERO_RGB, GAIN_RGB, max > 0 ? Math.sqrt(Math.min(1, net / max)) : 0);
}
/** The calendar strip (pure string): a row per month, a cell per evening, ◆ on simulated evenings (clickable). Every value
 *  in a tooltip carries the label its `series` gives it; a gap says why. */
export function calendarStripHTML(cal, date = DEFAULT_DATE) {
  if (!cal || !Array.isArray(cal.net) || !cal.from) return '';
  const S = cal.series || {};
  const lab = (k, v, opts) => (S[k] && fmt.LABELS.includes(S[k].label) ? fmt.fmtHTML({ v, label: S[k].label }, opts) : '');
  const peakT = String(cal.peakT || '').split(/\s+/), neg = cal.negMin || [];
  const gaps = new Map((cal.gaps || []).map((g) => [g.day, g.reason]));
  const max = Math.max(0, ...cal.net.filter((x) => typeof x === 'number'));
  const months = new Map();
  for (let i = 0; i < cal.net.length; i++) {
    const d = fmt.addDays(cal.from, i);
    if (!d) break;
    const key = d.slice(0, 7);
    if (!months.has(key)) months.set(key, []);
    const net = cal.net[i], sim = cal.sim && Object.prototype.hasOwnProperty.call(cal.sim, d);
    const rgb = netColour(net, max);
    let tip = `<b>${esc(fmt.dateLabel(d))}</b>`;
    if (gaps.has(d) || net === null || net === undefined) tip += `<br>${esc(gaps.get(d) || 'no price data for this evening')}`;
    else {
      tip += `<br>one Core, one cycle: ${lab('net', net / 100, { money: true, digits: 2 })}`;
      if (cal.peak && typeof cal.peak[i] === 'number') tip += `<br>evening peak ${lab('peak', cal.peak[i] / 100, { digits: 2, unit: ' $/MWh' })}${peakT[i] && peakT[i] !== '-' ? ` at ${esc(peakT[i].slice(0, 2))}:${esc(peakT[i].slice(2, 4))}` : ''}`;
      if (net < 0) tip += '<br>one cycle would lose money: a smart dispatcher sits out';
      if (neg[i] > 0) tip += `<br>paid to charge: ${lab('negMin', neg[i], { unit: ' min' })} of negative price`;
    }
    if (sim) tip += '<br>◆ simulated on this feeder: click to open';
    const style = rgb ? ` style="background:rgb(${rgb.join(',')})"` : '';
    const cls = `hb-cal-cell${rgb ? '' : ' gap'}${net < 0 ? ' lose' : ''}${sim ? ' sim' : ''}${d === date ? ' cur' : ''}${neg[i] > 0 ? ' paid' : ''}`;
    months.get(key).push(`<${sim ? 'button type="button"' : 'span'} class="${cls}" data-date="${d}" data-tip-html="${esc(tip)}"${style}>${sim ? '◆' : ''}</${sim ? 'button' : 'span'}>`);
  }
  const rows = [...months.entries()].map(([k, cells]) => `<div class="hb-cal-row"><span class="hb-cal-m">${MON[+k.slice(5, 7) - 1]}</span>${cells.join('')}</div>`);
  const h = cal.headline || {};
  const head = [];
  // fix list #12: the "$ per Core" sells the known priciest intervals (perfect foresight) and cycles even on losing nights
  if (fmt.isLabelled(h.perBattery2026ytd)) head.push(`${fmt.fmtHTML(h.perBattery2026ytd, { money: true, digits: 2 })} per Core this year with perfect foresight`);
  if (fmt.isLabelled(h.top10Share2026)) head.push(`${fmt.fmtHTML(h.top10Share2026, { unit: '%' })} of it on the ten best evenings`);
  if (fmt.isLabelled(h.losingNights2026)) head.push(`${fmt.fmtHTML(h.losingNights2026)} evenings would lose money`);
  return `<div class="hb-cal"><div class="hb-cal-h">${svg('money', { size: 14 })} Every real evening, one Core, one cycle (gross, not Base's profit)${head.length ? `: ${head.join(' · ')}` : ''}</div>`
    + `<div class="hb-cal-grid">${rows.join('')}</div>`
    + `<div class="hb-cal-key"><span class="hb-cal-cell lose"></span> would lose money <span class="hb-cal-cell" style="background:rgb(${GAIN_RGB.join(',')})"></span> earned most <span class="hb-cal-cell sim">◆</span> simulated</div></div>`;
}

/** Mount the chip + popover into `el`. onPick(date) runs when a different day is chosen (the caller sets &date=, keeps
 *  branch, cam, t and speed, and pauses). Returns {close(), destroy()}. */
export function mountDayPicker(el, { index = null, calendar = null, date = DEFAULT_DATE, onPick = () => {} } = {}) {
  const doc = el.ownerDocument;
  const many = rows(index).length > 1;
  el.classList.add('hb-daypick');
  el.innerHTML = `<button type="button" class="hb-daychip" aria-haspopup="${many ? 'listbox' : 'false'}" aria-expanded="false"${many ? '' : ' disabled'}>${dayChipHTML(index, date)}</button>`
    + (many ? `<div class="hb-daypop" hidden><div class="hb-daypop-h">Real ERCOT evenings, simulated on this feeder ${fmt.chip('SIM', 'OpenDSS every minute, our controller')}</div><ul class="hb-daylist">${dayRowsHTML(index, date)}</ul>${calendarStripHTML(calendar, date)}</div>` : '');
  const chipBtn = el.querySelector('.hb-daychip');
  const pop = el.querySelector('.hb-daypop');
  const close = () => { if (pop) { pop.hidden = true; chipBtn.setAttribute('aria-expanded', 'false'); } };
  const open = () => { if (pop) { pop.hidden = false; chipBtn.setAttribute('aria-expanded', 'true'); } };
  const onDoc = (e) => { if (pop && !pop.hidden && !el.contains(e.target)) close(); };
  const onKey = (e) => { if (e.key === 'Escape') close(); };
  chipBtn.addEventListener('click', () => (pop && pop.hidden ? open() : close()));
  if (pop) {
    pop.addEventListener('click', (e) => {
      const b = e.target.closest('.hb-dayrow, .hb-cal-cell.sim');
      if (!b) return;
      close();
      if (b.dataset.date !== date) onPick(b.dataset.date);
    });
  }
  doc.addEventListener('pointerdown', onDoc);
  doc.addEventListener('keydown', onKey);
  return { close, destroy: () => { doc.removeEventListener('pointerdown', onDoc); doc.removeEventListener('keydown', onKey); el.innerHTML = ''; } };
}
