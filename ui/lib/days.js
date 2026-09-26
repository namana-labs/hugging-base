// ui/lib/days.js (L0): the P1 day picker (UX_SPEC_R2 4.3, HIST-R2 7.1). Real ERCOT evenings, simulated on our feeder.
//   dayChipHTML(index, date)   the chip: calendar icon, "Wed 22 Jul 2026 · Texas's record demand ▾", an R tag on the date
//   dayRowsHTML(index, date)   the popover rows, from p1/days/index.json ONLY (it never loads a branch file)
//   mountDayPicker(el, {index, calendar, date, onPick})   the DOM half; l4 places it (the Day + scenario card)
// Every number goes through fmt with the label the index carries; the weekday is computed from the date, never typed.
// index = p1/days/index.json (docs/contracts.md A.10) or null before l2 builds it: then the chip shows the date alone.
import * as fmt from './format.js';
import { svg } from './icons.js';
import { DEFAULT_DATE } from './data.js';

const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
export const DATE_CITE = 'The evening\'s prices are ERCOT LZ_NORTH for this real date (REAL); the load is the 2018 SMART-DS weather year paired by calendar date (ASSUMPTION).';
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
  return `${svg('calendar', { size: 16 })}<span class="hb-day-date">${esc(label)}</span>${fmt.chip('REAL', DATE_CITE)}${tag}${caret}`;
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

/** Mount the chip + popover into `el`. onPick(date) runs when a different day is chosen (the caller sets &date=, keeps
 *  branch, cam, t and speed, and pauses). Returns {close(), destroy()}. */
export function mountDayPicker(el, { index = null, calendar = null, date = DEFAULT_DATE, onPick = () => {} } = {}) {
  const doc = el.ownerDocument;
  const many = rows(index).length > 1;
  el.classList.add('hb-daypick');
  el.innerHTML = `<button type="button" class="hb-daychip" aria-haspopup="${many ? 'listbox' : 'false'}" aria-expanded="false"${many ? '' : ' disabled'}>${dayChipHTML(index, date)}</button>`
    + (many ? `<div class="hb-daypop" hidden><div class="hb-daypop-h">Real ERCOT evenings, simulated on this feeder ${fmt.chip('SIM', 'OpenDSS every minute, our controller')}</div><ul class="hb-daylist">${dayRowsHTML(index, date)}</ul></div>` : '');
  const chipBtn = el.querySelector('.hb-daychip');
  const pop = el.querySelector('.hb-daypop');
  const close = () => { if (pop) { pop.hidden = true; chipBtn.setAttribute('aria-expanded', 'false'); } };
  const open = () => { if (pop) { pop.hidden = false; chipBtn.setAttribute('aria-expanded', 'true'); } };
  const onDoc = (e) => { if (pop && !pop.hidden && !el.contains(e.target)) close(); };
  const onKey = (e) => { if (e.key === 'Escape') close(); };
  chipBtn.addEventListener('click', () => (pop && pop.hidden ? open() : close()));
  if (pop) {
    pop.addEventListener('click', (e) => {
      const b = e.target.closest('.hb-dayrow');
      if (!b) return;
      close();
      if (b.dataset.date !== date) onPick(b.dataset.date);
    });
  }
  doc.addEventListener('pointerdown', onDoc);
  doc.addEventListener('keydown', onKey);
  void calendar;   // the money calendar strip (HIST 7.1, Should) is not built in this PR
  return { close, destroy: () => { doc.removeEventListener('pointerdown', onDoc); doc.removeEventListener('keydown', onKey); el.innerHTML = ''; } };
}
