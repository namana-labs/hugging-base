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
    <span>Feeder: NREL SMART-DS 2018 AUS P1U, CC BY 4.0</span><span>Prices: ERCOT real-time, LZ_NORTH</span>
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
        right = `<span class="st-pill" title="${esc(`A static replay of the engine's run ${scenario.id} (ui/data). No simulator runs in the page.`)}">
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
