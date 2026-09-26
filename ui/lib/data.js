// ui/lib/data.js (L0): deep-link parsing and the data loaders, with the fixture fallback.
// Real data lives in ui/data/<path>; fixtures in ui/data/fixtures/<path>. A loader tries the real file first and
// falls back to the fixture on 404; any fixture load marks the page (body data-fixture="1" + the FIXTURE banner).
// Everything is fetched from the same origin by relative URL: no network at view time.

export const VIEWS = ['p1', 'p2', 'more'];
export const BRANCHES = ['none', 'naive', 'aware', 'aware_faults'];
export const CAMS = ['feeder', 'street', 't240'];

/** Parse a deep link (location.search). Unknown or malformed values fall back to defaults. */
export function parseLink(search) {
  const q = new URLSearchParams(search || '');
  const pick = (k, list, dflt) => (list.includes(q.get(k)) ? q.get(k) : dflt);
  const t = q.get('t');
  const n = parseInt(q.get('n'), 10);
  return {
    view: pick('view', VIEWS, 'p1'),
    branch: pick('branch', BRANCHES, 'aware'),
    t: /^\d{1,2}:\d{2}$/.test(t || '') ? t : null,
    cam: pick('cam', CAMS, null),
    combo: /^[a-z]+-[a-z]+-[a-z0-9]+-g\d+$/.test(q.get('combo') || '') ? q.get('combo') : null,
    home: q.get('home') || null,
    n: Number.isFinite(n) && n >= 1 && n <= 10 ? n : null,
    beat: q.get('beat') || null,
    nowebgl: q.get('nowebgl') === '1',
    smoke: q.get('smoke') === 'dump' ? 'dump' : null,
  };
}

/** Build a query string for a link object (the inverse of parseLink for the keys that are set). */
export function linkQuery(link) {
  const q = new URLSearchParams();
  for (const k of ['view', 'branch', 't', 'cam', 'combo', 'home', 'n', 'beat']) if (link[k] != null) q.set(k, String(link[k]));
  if (link.nowebgl) q.set('nowebgl', '1');
  return '?' + q.toString();
}

export class HttpError extends Error {
  constructor(status, path) { super(`HTTP ${status} for ${path}`); this.status = status; this.path = path; }
}

const state = { base: 'data/', fixture: false, listeners: [], cache: new Map(), fetch: (...a) => fetch(...a) };

/** For tests: swap the fetch function and base path. */
export function _configure({ base, fetchFn } = {}) {
  if (base) state.base = base;
  if (fetchFn) state.fetch = fetchFn;
  state.cache.clear();
  state.fixture = false;
}

export function isFixture() { return state.fixture; }
export function onFixture(cb) { state.listeners.push(cb); if (state.fixture) cb(); }
function markFixture() {
  if (state.fixture) return;
  state.fixture = true;
  for (const cb of state.listeners) { try { cb(); } catch (e) { /* the shell counts listener errors */ throw e; } }
}

export async function getJSON(path) {
  if (state.cache.has(path)) return state.cache.get(path);
  const p = (async () => {
    const r = await state.fetch(state.base + path);
    if (!r.ok) throw new HttpError(r.status, path);
    return r.json();
  })();
  state.cache.set(path, p);
  p.catch(() => state.cache.delete(path));
  return p;
}

/** Real file, else its fixture (marks the page as fixture). Other HTTP errors propagate. */
export async function getWithFixture(path) {
  try {
    return await getJSON(path);
  } catch (e) {
    if (!(e instanceof HttpError) || e.status !== 404) throw e;
    const doc = await getJSON('fixtures/' + path);
    markFixture();
    return doc;
  }
}

/** Optional file: null on 404 (no fixture). */
export async function getOptional(path) {
  try { return await getJSON(path); } catch (e) { if (e instanceof HttpError && e.status === 404) return null; throw e; }
}

export const loadTopology = () => getJSON('topology.json');
export const loadFootprints = () => getOptional('footprints.json');       // L4; missing homes draw as 12 m squares
export const loadBeats = () => getOptional('beats.json');                 // L5
export const loadEngine = () => getOptional('engine.json');               // L2
export const loadP1Meta = () => getWithFixture('p1/meta.json');           // L2
export const loadP1Branch = (b) => getWithFixture(`p1/${b}.json`);        // L2
export const loadP2Index = () => getWithFixture('p2/index.json');         // L3
export const loadP2Combo = (id) => getWithFixture(`p2/${id}.json`);       // L3

/** Apply a beat from beats.json over a link: the beat's `link` (a query string or object) sets every key it names. */
export function applyBeat(link, beats) {
  if (!link.beat || !beats) return link;
  const list = Array.isArray(beats) ? beats : (beats.beats || []);
  const b = list.find((x) => x.id === link.beat);
  if (!b) return link;
  const src = typeof b.link === 'string' ? parseLink(b.link) : { ...link, ...(b.link || {}) };
  const explicit = typeof b.link === 'string' ? new URLSearchParams(b.link) : null;
  const out = { ...link };
  for (const k of Object.keys(src)) {
    if (explicit ? explicit.has(k) : (b.link && k in b.link)) out[k] = src[k];
  }
  return out;
}
