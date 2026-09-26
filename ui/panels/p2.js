// ui/panels/p2.js -- OWNED BY L5 (P2 + More + story). This is L0's STUB. L5 replaces it and keeps the export:
//   mount(el, ctx) -> Promise   (same ctx as panels/p1.js)
export async function mount(el, ctx) {
  const { data, link, fmt, sceneModel, scene, topology } = ctx;
  const index = await data.loadP2Index();
  const ids = index.combos.map((c) => (typeof c === 'string' ? c : c.id));
  const combo = link.combo && ids.includes(link.combo) ? link.combo : index.default;
  const doc = await data.loadP2Combo(combo);
  scene.update(sceneModel.buildSceneModel({ topology, footprints: ctx.footprints, frame: sceneModel.frameFromP2(doc), view: 'p2', theme: ctx.theme }));
  if (link.cam) scene.camera(link.cam);
  const n = link.n || 5;
  const rows = doc.ranking.slice(0, n).map((r) => {
    const h = topology.homes[r.home];
    return `<li>${h ? h.label : r.home} on T-${r.tf}: peak with battery ${fmt.fmtHTML(r.peakWithPct, { unit: '%' })}</li>`;
  }).join('');
  el.innerHTML = `
    <h1>P2 · where the next battery goes</h1>
    <div class="hb-sub">${index.month} · combo ${combo}</div>
    <h2>Top ${n}</h2>
    <ol class="hb-list">${rows}</ol>
    <h2>Price cliffs, 2026 (REAL prices)</h2>
    <div>${fmt.fmtHTML(index.cliffs.count)} cliffs, ${fmt.fmtHTML(index.cliffs.evening)} in the evening</div>
    <p class="hb-note">Placeholder P2 panel (L0 stub). L5 builds the controls, ranking, card, strips and flip here.</p>`;
}
