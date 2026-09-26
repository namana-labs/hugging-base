// ui/panels/more.js -- OWNED BY L5. This is L0's STUB: links to the untouched prototype and four-home.
//   mount(el, ctx) -> Promise
export async function mount(el, ctx) {
  const { sceneModel, scene, topology } = ctx;
  scene.update(sceneModel.buildSceneModel({ topology, footprints: ctx.footprints, frame: null, view: 'more', theme: ctx.theme }));
  const cards = [
    ['Grid stories (prototype)', '../demos/grid-stories/ui/dist/', 'Heat wave, rebound, covert channel + quarantine, siting board. Unchanged; fictional adversary; SIM.'],
    ['Four-home simulation', '../four-home-simulation/four-home.html', "Michael's four-home model. Unchanged."],
  ];
  el.innerHTML = `<div class="hb-cards">${cards.map(([t, href, d]) =>
    `<div class="hb-card"><h3><a href="${href}">${t}</a></h3><div class="hb-sub">${d}</div></div>`).join('')}</div>`;
}
