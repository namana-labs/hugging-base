// ui/story/shell.js (UI-A): the story app's chrome (story-flow spec v2, "Shared chrome"): a 60 px header (wordmark,
// step nav 1 Configure / 2 Run / 3 Results / 4 Learnings, and per page a framing label or the run pill + continue
// button), a notice line, and a footer with the sources and the "Engine explorer" link (ui/explore.html, the old tab
// app). Also numHTML(): a labelled value + its provenance tag, the ctx.num() of app.js.
import { fmtValue, LabelError, LABELS } from '../lib/format.js';

const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
export const TAG_LABELS = [...LABELS, 'UNVERIFIED', 'SCREENING'];
export const STEPS = [['configure', '1 Configure'], ['run', '2 Run'], ['results', '3 Results'], ['learnings', '4 Learnings']];
export const FRAMING = 'Oncor-suburb stand-in · LZ_NORTH';
export const STANDIN = 'Oncor-suburb stand-in on NREL\'s synthetic feeder';
const STANDIN_CITE = 'The feeder is NREL SMART-DS 2018 AUS P1U (synthetic, CC BY 4.0), settled at ERCOT LZ_NORTH as an Oncor-suburb stand-in (ASSUMPTION). Its real buses sit in Pedernales Electric Cooperative territory.';
/** How the feeder is tagged wherever it appears (data-truth audit #1): a REAL dataset of a synthetic feeder. */
export const FEEDER_TAG = 'REAL dataset · synthetic feeder';
export const FEEDER_CITE = 'NREL SMART-DS 2018 AUS P1U (CC BY 4.0) is a REAL published dataset, but its feeder is synthetic: NREL calls SMART-DS realistic, not real.';
const NEXT = { run: ['results', 'Continue to Results →'], results: ['learnings', 'Continue to Learnings →'] };

/** A provenance tag: the label word in a 1 px tag, title = cite. SCREENING is dashed (story-flow tokens). */
export function tagHTML(label, cite) {
  if (!TAG_LABELS.includes(label)) throw new LabelError(`unknown label ${label}`);
  return `<span class="chip chip-${label}"${cite ? ` title="${esc(cite)}"` : ''}>${label}</span>`;
}

/** ctx.num(): HTML for a labelled value, `<span class="num">value</span>` + its tag (+ a dashed SCREENING tag when
 *  opts.screening, x.screening === true or x.label === 'SCREENING'). Throws LabelError on a bare number. */
export function numHTML(x, opts = {}) {
  if (x === null || typeof x !== 'object' || Array.isArray(x) || !('v' in x) || !TAG_LABELS.includes(x.label)) {
    throw new LabelError(`unlabelled number: ${JSON.stringify(x)} (want {"v": n, "label": "${TAG_LABELS.join('|')}"})`);
  }
  const std = LABELS.includes(x.label);
  const val = fmtValue(std ? x : { ...x, label: 'ASSUMPTION' }, opts);
  const screening = opts.screening || x.screening === true || x.label === 'SCREENING';
  const tags = (x.label !== 'SCREENING' ? tagHTML(x.label, x.cite) : '')
    + (screening ? tagHTML('SCREENING', `Screening estimate, not checked by OpenDSS.${x.cite ? ' ' + x.cite : ''}`) : '');
  return `<span class="num">${esc(val)}</span>${tags}`;
}

// ---- what a lever changed: the catalogue's `vsDefault` (only the headline values that differ from the default run) ----
/** Words for the catalogue's headline keys (`catalogue.headline`); money is the fleet's gross energy value (ruling 6). */
export const VS_WORDS = {
  batteryCausedNormal: ['battery-caused normal-rating events', {}],
  batteryCausedEmergency: ['battery-caused emergency events', {}],
  batteryCausedAmberMin: ['battery-caused minutes over nameplate', {}],
  energyValueUSD: ['fleet gross energy value, not Base\'s profit', { money: true, digits: 2 }],
  maxLoading: ['worst transformer', { unit: '%', digits: 1 }],
  normalEvents: ['normal-rating events', {}],
  emergencyTfs: ['transformers above emergency', {}],
  chargedPctBy0400: ['fleet charged by 04:00', { unit: '%', digits: 1 }],
  reserveBreaches: ['reserve breaches (battery-minutes)', {}],
  protectionOperated: ['protection operations', {}],
  homesDark: ['homes dark', {}],
};

/** The rows of a scenario's `vsDefault` in the catalogue's `headline` order: [{key, words, opts, now, ref, refId,
 *  refTitle}], `now` and `ref` labelled from the two runs' own summaries (a row whose label is missing is dropped:
 *  never a bare number). [] for the default run, an alias, or a scenario without `vsDefault`. */
export function vsDefaultRows(cat, scenario) {
  const vs = scenario && scenario.vsDefault;
  if (!vs || typeof vs !== 'object') return [];
  const order = Array.isArray(cat.headline) ? cat.headline : Object.keys(vs);
  const keys = [...order.filter((k) => k in vs), ...Object.keys(vs).filter((k) => !order.includes(k))];
  const out = [];
  for (const key of keys) {
    const d = vs[key];
    if (!d || typeof d !== 'object' || !('v' in d)) continue;
    const refS = (cat.scenarios || []).find((x) => x.id === d.refId) || null;
    const lab = (sc) => (sc && sc.summary && sc.summary[key] && TAG_LABELS.includes(sc.summary[key].label) ? sc.summary[key] : null);
    const nowL = lab(scenario), refL0 = lab(refS);
    if (!nowL || !LABELS.includes(nowL.label)) continue;
    const refL = refL0 && LABELS.includes(refL0.label) ? refL0 : nowL;
    const [words, opts] = VS_WORDS[key] || [key, {}];
    out.push({ key, words, opts, refId: d.refId, refTitle: refS ? refS.title || refS.id : d.refId,
      now: { v: d.v, label: nowL.label, cite: nowL.cite }, ref: { v: d.ref, label: refL.label, cite: refL.cite } });
  }
  return out;
}

/** Plain text of the rows ("fleet gross energy value $1,845.39 (default run $916.56)"), for a tooltip. */
export function vsDefaultText(rows) {
  return rows.map((r) => `${r.words} ${fmtValue(r.now, r.opts)} (default run ${fmtValue(r.ref, r.opts)})`).join('; ');
}

/** HTML of the rows, each value with its tag. `max` rows at most (the rest in the title). */
export function vsDefaultHTML(rows, { max = Infinity } = {}) {
  if (!rows.length) return '';
  const shown = rows.slice(0, max);
  const more = rows.length - shown.length;
  return shown.map((r) => `<span class="vs-row" title="${esc(`vs ${r.refTitle}`)}">${esc(r.words)} ${numHTML(r.now, r.opts)} <span class="vs-was">default run ${esc(fmtValue(r.ref, r.opts))}</span></span>`).join('')
    + (more > 0 ? `<span class="vs-more" title="${esc(vsDefaultText(rows.slice(max)))}">+${more} more</span>` : '');
}

// ---- customers: every load bus is a customer; topology homes[].use says "residential" or "commercial" (DERIVED,
// topology meta.customerUse). A single customer keeps its "Home 0xxx" id; a commercial one is marked a small business.
export const SMALL_BUSINESS = 'small business';
/** "Home 0225 (small business)" for a commercial customer, else its label ("Home 0001"). `h` = index into homes. */
export function customerName(topology, h) {
  const x = topology && topology.homes && topology.homes[h];
  if (!x) return `Home ${h}`;
  return x.use === 'commercial' ? `${x.label} (${SMALL_BUSINESS})` : x.label;
}
/** The engine's own text with every commercial customer's "Home 0xxx" marked "(small business)"; nothing else changes. */
export function markCustomers(text, topology) {
  const com = new Set(((topology && topology.homes) || []).filter((x) => x.use === 'commercial').map((x) => x.label));
  if (!com.size || !text) return text;
  return String(text).replace(/Home \d{4}(?! \(small business\))/g, (m) => (com.has(m) ? `${m} (${SMALL_BUSINESS})` : m));
}

/** Lever words for the run pill, from the catalogue's own option labels. */
export function leverSummary(catalogue, levers) {
  const L = (catalogue && catalogue.levers) || {};
  // the option's label up to its first ":" or " (" ("Controller crash: a worker is ..." -> "Controller crash")
  const lab = (key) => {
    const o = ((L[key] && L[key].options) || []).find((x) => String(x.id) === String(levers[key]));
    return o ? String(o.label).split(/: | \(/)[0].trim() : String(levers[key]);
  };
  if (!levers) return '';
  const parts = [lab('policy')];
  if (levers.failure && levers.failure !== 'none') parts.push(lab('failure'));
  if (levers.policy !== 'none') parts.push(`${lab('fleet')}, ${lab('cls')}`, lab('reserve'), lab('soc0'));
  if (levers.growth !== undefined && String(levers.growth) !== String(L.growth && L.growth.default)) parts.push(lab('growth'));
  return parts.join(' · ');
}

export function createShell(body) {
  const header = document.createElement('header');
  header.className = 'st-header';
  const notice = document.createElement('div');
  notice.className = 'st-notice';
  notice.hidden = true;
  notice.setAttribute('role', 'status');
  const banner = document.createElement('div');
  banner.className = 'st-banner';
  banner.hidden = true;
  const main = document.createElement('main');
  main.className = 'st-main';
  const footer = document.createElement('footer');
  footer.className = 'st-footer';
  footer.innerHTML = `<span class="st-standin" title="${esc(STANDIN_CITE)}">${STANDIN}</span>
    <span title="${esc(FEEDER_CITE)}">Feeder: NREL SMART-DS 2018 AUS P1U, CC BY 4.0 (${FEEDER_TAG})</span><span>Prices: ERCOT real-time, LZ_NORTH</span>
    <span>Buildings: © OpenStreetMap contributors, ODbL</span><span>Power flow: OpenDSS</span>
    <span>Every number carries its tag: REAL, SIM, DERIVED, ASSUMPTION</span>
    <a class="st-explorer" href="explore.html">Engine explorer</a>`;
  body.append(header, banner, notice, main, footer);

  const api = {
    main,
    update({ page, scenario, catalogue, link, nav }) {
      notice.hidden = true;
      notice.textContent = '';
      const running = page === 'running';
      const active = running ? 'run' : page;
      const steps = STEPS.map(([id, text]) => {
        if (running && (id === 'results' || id === 'learnings')) return `<span class="st-step off" aria-disabled="true">${text}</span>`;
        const on = id === active;
        return `<a class="st-step${on ? ' on' : ''}" href="${esc(link(id, {}))}" data-page="${id}"${on ? ' aria-current="page"' : ''}>${text}</a>`;
      }).join('');
      let right = '';
      if (page === 'configure') right = `<span class="st-framing">${FRAMING}</span>`;
      else if (page === 'learnings') right = '<span class="st-framing">Core batteries · D-26 onset · today\'s load</span>';
      else if (NEXT[page] && scenario) {
        const idx = (catalogue.scenarios || []).indexOf(scenario) + 1;
        const vs = vsDefaultText(vsDefaultRows(catalogue, scenario));
        right = `<span class="st-pill" title="${esc(`A static replay of the engine's run ${scenario.id} (ui/data). No simulator runs in the page.${vs ? ` Versus the default run: ${vs}.` : ''}`)}">
            <span class="dot"></span><b>Run #${idx}</b><span class="sum">${esc(leverSummary(catalogue, scenario.levers))}</span></span>
          <a class="st-btn" href="${esc(link(NEXT[page][0], {}))}" data-next="${NEXT[page][0]}">${NEXT[page][1]}</a>`;
      }
      header.innerHTML = `<div class="st-wordmark">Hugging Base</div><nav class="st-steps" aria-label="Story steps">${steps}</nav>
        <div class="st-spacer"></div>${right}`;
      // in-app navigation (the hrefs still work with a middle click)
      for (const a of header.querySelectorAll('a[data-page], a[data-next]')) {
        a.addEventListener('click', (ev) => {
          if (ev.button !== 0 || ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey) return;
          ev.preventDefault();
          nav(a.dataset.page || a.dataset.next, {});
        });
      }
    },
    notice(msg) {
      notice.textContent = notice.textContent ? `${notice.textContent} ${msg}` : msg;
      notice.hidden = false;
      document.body.dataset.notice = String((Number(document.body.dataset.notice) || 0) + 1);
    },
    banner(msg) { banner.textContent = msg; banner.hidden = false; },
    error(msg) {
      let el = document.querySelector('.st-error');
      if (!el) { el = document.createElement('div'); el.className = 'st-error'; el.setAttribute('role', 'alert'); (document.querySelector('main.st-main') || footer).before(el); }
      el.textContent = msg;
    },
  };
  return api;
}
