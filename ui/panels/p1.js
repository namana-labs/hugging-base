// ui/panels/p1.js -- OWNED BY L4 (3D + P1 view). This is L0's STUB: it proves the plumbing (data -> scene -> panel)
// with a placeholder panel. L4 replaces it (gauges, ticker, price strip, money, transport) and keeps the export:
//   mount(el, ctx) -> Promise   resolves after the panel's first render and ctx.scene.update(...)
//   ctx = {topology, footprints, link, scene, data, fmt, sceneModel, reportError, go(linkPatch)}
export async function mount(el, ctx) {
  const { data, link, fmt, sceneModel, scene, topology } = ctx;
  const meta = await data.loadP1Meta();
  const branch = meta.branches.includes(link.branch) ? link.branch : meta.branches[0];
  const doc = await data.loadP1Branch(branch);
  const k = link.t ? fmt.timeToStep(meta, link.t) : Math.min(meta.steps - 1, Math.floor(meta.steps / 2));
  const frame = sceneModel.frameFromP1(doc, k);
  scene.update(sceneModel.buildSceneModel({ topology, footprints: ctx.footprints, frame, view: 'p1', theme: ctx.theme }));
  if (link.cam) scene.camera(link.cam);
  const s = meta.summary[branch];
  const seg = meta.branches.map((b) => `<a href="${ctx.href({ branch: b })}" aria-current="${b === branch}">${b}</a>`).join('');
  el.innerHTML = `
    <h1>P1 · where to charge</h1>
    <div class="hb-sub">${meta.day} · ${fmt.stepToTime(meta, k)} (step ${k} of ${meta.steps}) · branch ${branch}</div>
    <div class="hb-seg">${seg}</div>
    <h2>Worst service transformer this evening</h2>
    <div class="hb-big">${fmt.fmtHTML(s.maxLoading, { unit: '%' })}</div>
    <div class="hb-sub">battery-caused normal-tier events ${fmt.fmtHTML(s.batteryCausedNormal)} · emergency ${fmt.fmtHTML(s.batteryCausedEmergency)}</div>
    <h2>Price now</h2>
    <div>${fmt.fmtHTML({ v: meta.price[k], label: 'REAL', cite: 'ERCOT RTM SPP LZ_NORTH' }, { money: true, digits: 2, unit: '/MWh' })}</div>
    <div class="hb-sub">What the controller sees: ${meta.controllerView.text} ${fmt.chip(meta.controllerView.label, meta.controllerView.cite)}</div>
    <p class="hb-note">Placeholder P1 panel (L0 stub). L4 builds the A–D gauges, ticker, price strip and transport here.</p>`;
}
