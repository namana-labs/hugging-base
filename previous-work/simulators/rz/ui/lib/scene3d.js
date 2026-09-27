// ui/lib/scene3d.js (L4, 3D + P1 view): deck.gl 9.4.0 (vendored, global `deck`), MapView with no basemap and a flat
// --bg, lon/lat straight from topology. Draws the arrays of scene-model.js; knows nothing about the data files.
// Scene API (docs/contracts.md A.9; fallback2d.js has the same shape):
//   createScene(el, opts) -> scene        opts: {topology, theme, onError(err), viewState?}
//   scene.update(model)                   model from scene-model.js buildSceneModel()
//   scene.camera(preset, {instant}?)     'feeder' | 'street' | 't240' (fly-to; instant on first open)
//   scene.flyTo(lonlat, {zoom, pitch})    fly to a point (a click on a street column or a legend row)
//   scene.onPick(cb)                      cb({layer, object, index}) on click
//   scene.onHover(cb)                     cb({x, y, layer, object}) on hover, cb(null) on leave (UX_SPEC_R2 6.1)
//   scene.dispose()                       deck.finalize(); only ?smoke=dump calls it in the page
//   scene.whenRendered() -> Promise       resolves after the next completed render (the shell's "ready")
//   scene.kind                            'webgl'
// createScene THROWS when deck.gl or WebGL2 is unavailable; the shell then uses fallback2d.js.
//
// Layers (UX_SPEC_R2 6.1, lifted from the round-2 scene prototype): context buildings; lines; tier halos; service
// drops (near zoom); walls (extruded footprints) and hip roofs (SolidPolygonLayer, _full3d, baked shading; tinted
// only at tier >= 1); pad-mount plinths + green boxes; poles + crossarms + grey cans; white battery cabinets with a
// teal cap; one-step command pulses; billboard load meters and battery icons from one canvas atlas (icons.js, drawn at
// start-up: no network); "A".."D", "T-240"; and "worst now N%" with its label tag, the only number in the scene.
import { cameraPreset, roofColor, dropStyle, TIER_RGB } from './scene-model.js';
import { buildAtlas } from './icons.js';

export const LABEL_FULL_ZOOM = 16.2;          // the near/far bucket (UX-R2-scene 3.5)
export const PICKABLE = ['walls', 'roofs', 'pads', 'poles', 'cans', 'cabinets', 'caps', 'meters', 'battery-icons', 'badges'];
const FONT = 'Inter, "Helvetica Neue", Helvetica, Arial, sans-serif';

export function webgl2Available() {
  try {
    const c = document.createElement('canvas');
    return !!(c.getContext('webgl2'));
  } catch (e) {
    return false;
  }
}

export function createScene(el, opts = {}) {
  const D = window.deck;
  if (!D || !D.Deck) throw new Error('deck.gl not loaded');
  if (!webgl2Available()) throw new Error('WebGL2 unavailable');
  const topology = opts.topology;
  let waiters = [];
  let pick = null, hover = null;
  let model = null;
  const atlas = buildAtlas(64);
  // the off-screen pointer (UX-R2-story 4.3): when the worst transformer is outside the view, an arrow at the edge
  // points to it with its callout; a click flies there
  const ptr = document.createElement('button');
  ptr.type = 'button';
  ptr.className = 'hb-worst-ptr';
  ptr.hidden = true;
  el.appendChild(ptr);
  let ptrKey = '';
  function placePointer() {
    const w = model && model.worst && model.worst[0];
    const vp = w ? deck.getViewports()[0] : null;
    if (!w || !vp) { ptr.hidden = true; return; }
    const [x, y] = vp.project(w.position);
    const W = vp.width, H = vp.height, m = 36;
    if (x >= 0 && x <= W && y >= 0 && y <= H) { ptr.hidden = true; return; }
    const cx = W / 2, cy = H / 2, dx = x - cx, dy = y - cy;
    const k = Math.min((W / 2 - m) / Math.max(1e-9, Math.abs(dx)), (H / 2 - m) / Math.max(1e-9, Math.abs(dy)));
    ptr.hidden = false;
    const c = TIER_RGB[w.code] || TIER_RGB[0];
    const key = `${w.text}|${w.name}|${w.code}|${Math.round(Math.atan2(dy, dx) * 20)}`;
    const put = () => {   // keep the whole pill inside the scene
      const hw = ptr.offsetWidth / 2 + 8, hh = ptr.offsetHeight / 2 + 8;
      ptr.style.left = `${Math.round(Math.max(hw, Math.min(W - hw, cx + dx * k)))}px`;
      ptr.style.top = `${Math.round(Math.max(hh, Math.min(H - hh, cy + dy * k)))}px`;
    };
    if (key === ptrKey) { put(); return; }
    ptrKey = key;
    ptr.style.setProperty('--c', `rgb(${c.join(',')})`);
    ptr.innerHTML = `<span class="ar" style="transform:rotate(${(Math.atan2(dy, dx) * 180 / Math.PI).toFixed(0)}deg)">➜</span><span class="tx">${w.text.replace(/[<>&]/g, '')} · ${String(w.name).replace(/[<>&]/g, '')}</span><span class="chip chip-${w.label}">${w.label}</span>`;
    ptr.title = 'The worst transformer right now is off-screen: click to fly there';
    ptr.onclick = () => api.flyTo(w.position, { zoom: 18.3, pitch: 55 });
    put();
  }
  const initial = opts.viewState || cameraPreset(topology, 'feeder');
  let near = initial.zoom >= LABEL_FULL_ZOOM;
  const deck = new D.Deck({
    parent: el,
    views: [new D.MapView({ repeat: false })],
    initialViewState: initial,
    onViewStateChange: ({ viewState }) => {
      const b = viewState.zoom >= LABEL_FULL_ZOOM;
      if (b !== near) { near = b; if (model) deck.setProps({ layers: layers(model) }); }
    },
    controller: { dragRotate: true, touchRotate: true, scrollZoom: true, doubleClickZoom: true, keyboard: true },
    layers: [],
    useDevicePixels: true,
    pickingRadius: 3,
    onAfterRender: () => {
      if (!model) return;
      try { placePointer(); } catch (e) { /* the pointer is a nicety; never break a frame */ }
      const w = waiters; waiters = [];
      for (const f of w) f();
    },
    onError: (err) => { if (opts.onError) opts.onError(err); },
    onClick: (info) => { if (pick && info && info.object) pick({ layer: info.layer && info.layer.id, object: info.object, index: info.index }); },
    onHover: (info) => {
      if (!hover) return;
      if (info && info.object && info.layer) hover({ x: info.x, y: info.y, layer: info.layer.id, object: info.object });
      else hover(null);
    },
    getCursor: ({ isHovering, isDragging }) => (isDragging ? 'grabbing' : isHovering ? 'pointer' : 'grab'),
  });

  try { window.__hbDeck = deck; } catch (e) { /* tests project points through it (hover checks) */ }

  function layers(m) {
    const ink = m.ink;
    const trgb = (c, a = 255) => [...(TIER_RGB[c] || TIER_RGB[0]), a];
    const paperBg = m.theme === 'dark' ? [17, 24, 21, 230] : [247, 249, 245, 235];
    const out = [
      new D.PolygonLayer({ id: 'context', data: m.context, extruded: true, filled: true, stroked: false, pickable: false,
        getPolygon: (d) => d.polygon, getElevation: (d) => d.height, getFillColor: (d) => d.color }),
      new D.PathLayer({ id: 'lines', data: m.lines, getPath: (d) => d.path, getColor: (d) => d.color, widthUnits: 'pixels', getWidth: 1 }),
      new D.ScatterplotLayer({ id: 'halos', data: m.halos, getPosition: (d) => d.position, getRadius: 7, radiusUnits: 'meters', radiusMinPixels: 6,
        getFillColor: (d) => trgb(d.code, 80), getLineColor: (d) => trgb(d.code, 230), stroked: true, lineWidthUnits: 'pixels', getLineWidth: 2 }),
    ];
    if (near) {
      out.push(new D.PathLayer({ id: 'drops', data: m.drops, getPath: (d) => d.path, widthUnits: 'pixels',
        getColor: (d) => dropStyle(m.tier[d.tf] | 0, ink).color, getWidth: (d) => dropStyle(m.tier[d.tf] | 0, ink).width,
        updateTriggers: { getColor: m.tierKey, getWidth: m.tierKey } }));
    }
    out.push(
      new D.PolygonLayer({ id: 'walls', data: m.walls, extruded: true, filled: true, stroked: false, pickable: true,
        getPolygon: (d) => d.polygon, getElevation: (d) => d.height, getFillColor: (d) => m.homes[d.i].color,
        updateTriggers: { getFillColor: m.homeKey } }),
      new D.SolidPolygonLayer({ id: 'roofs', data: m.roofs, _full3d: true, extruded: false, material: false, pickable: true,
        getPolygon: (d) => d.poly, getFillColor: (d) => roofColor(d, m.tier[d.tf] | 0), updateTriggers: { getFillColor: m.tierKey } }),
      new D.PolygonLayer({ id: 'plinths', data: m.plinths, extruded: true, stroked: false, pickable: false,
        getPolygon: (d) => d.polygon, getElevation: (d) => d.height, getFillColor: m.colors.plinth }),
      new D.PolygonLayer({ id: 'pads', data: m.pads, extruded: true, stroked: false, pickable: true,
        getPolygon: (d) => d.polygon, getElevation: (d) => d.height, getFillColor: m.colors.pad }),
      new D.ColumnLayer({ id: 'poles', data: m.poles, radius: 0.3, diskResolution: 8, extruded: true, pickable: true,
        getPosition: (d) => d.position, getElevation: 10.5, getFillColor: m.colors.pole }),
      new D.PathLayer({ id: 'arms', data: m.arms, getPath: (d) => d.path, getColor: m.colors.pole, widthUnits: 'meters', getWidth: 0.3, widthMinPixels: 1 }),
      new D.ColumnLayer({ id: 'cans', data: m.cans, radius: 1.0, diskResolution: 16, extruded: true, pickable: true,
        getPosition: (d) => d.position, getElevation: 2.3, getFillColor: m.colors.can }),
      new D.PolygonLayer({ id: 'cabinets', data: m.cabinets, extruded: true, stroked: false, pickable: true,
        getPolygon: (d) => d.polygon, getElevation: (d) => d.height, getFillColor: (d) => (d.placed ? [...m.colors.cabinet.slice(0, 3), 150] : m.colors.cabinet) }),
      new D.PolygonLayer({ id: 'caps', data: m.caps, extruded: true, stroked: false, pickable: true,
        getPolygon: (d) => d.polygon, getElevation: (d) => d.height, getFillColor: (d) => (d.placed ? [...m.colors.cap, 150] : m.colors.cap) }),
      new D.ScatterplotLayer({ id: 'pulses', data: m.pulses, getPosition: (d) => d.position, getRadius: 5.5, radiusUnits: 'meters', radiusMinPixels: 5,
        filled: false, stroked: true, getLineColor: (d) => d.color, lineWidthUnits: 'pixels', getLineWidth: 2.5 }),
      new D.IconLayer({ id: 'meters', data: m.meters, iconAtlas: atlas.canvas, iconMapping: atlas.mapping, pickable: true,
        getIcon: (d) => d.icon, getPosition: (d) => d.position, getSize: near ? 44 : 30, sizeUnits: 'pixels', billboard: true,
        updateTriggers: { getSize: near } }),
      new D.IconLayer({ id: 'battery-icons', data: m.batteries, iconAtlas: atlas.canvas, iconMapping: atlas.mapping, pickable: true,
        getIcon: (d) => d.icon, getPosition: (d) => d.position, getSize: near ? 34 : 22, sizeUnits: 'pixels', billboard: true,
        updateTriggers: { getSize: near } }),
      new D.IconLayer({ id: 'badges', data: m.badges || [], iconAtlas: atlas.canvas, iconMapping: atlas.mapping, pickable: true,
        getIcon: (d) => d.icon, getPosition: (d) => d.position, getSize: near ? 26 : 20, sizeUnits: 'pixels', billboard: true,
        getPixelOffset: [near ? 16 : 11, near ? -34 : -24], updateTriggers: { getSize: near, getPixelOffset: near } }),
      new D.TextLayer({ id: 'labels', data: m.labels, getPosition: (d) => d.position, getText: (d) => d.text,
        getColor: (d) => d.color, getSize: (d) => (d.pin ? 13 : 16), fontWeight: 800, characterSet: 'auto', fontFamily: FONT,
        background: true, getBackgroundColor: paperBg, backgroundPadding: [5, 2, 5, 2],
        getPixelOffset: (d) => (d.pin ? [0, -4] : [near ? 30 : 22, near ? -30 : -22]), updateTriggers: { getPixelOffset: near }, billboard: true }),
      new D.TextLayer({ id: 'worst', data: m.worst, getPosition: (d) => d.position, getText: (d) => d.text, getSize: 15, fontWeight: 800, pickable: true,
        getColor: [255, 255, 255, 255], background: true, getBackgroundColor: (d) => trgb(d.code, 245), backgroundPadding: [6, 3, 6, 3],
        getPixelOffset: [0, near ? -62 : -46], updateTriggers: { getPixelOffset: near }, billboard: true, fontFamily: FONT, characterSet: 'auto' }),
      // the worst number's label tag (a compact letter, UX_SPEC_R2 2.5), right of the callout
      new D.TextLayer({ id: 'worst-tag', data: m.worst, getPosition: (d) => d.position, getText: (d) => d.tag, getSize: 11, fontWeight: 700,
        getColor: [85, 98, 90, 255], background: true, getBackgroundColor: [247, 249, 245, 245], backgroundPadding: [3, 1, 3, 1],
        getBorderColor: [207, 202, 189, 255], getBorderWidth: 1,
        getPixelOffset: (d) => [Math.round(d.text.length * 4.6) + 16, near ? -62 : -46], updateTriggers: { getPixelOffset: near },
        billboard: true, fontFamily: FONT, pickable: true }),
    );
    return out;
  }

  const api = {
    kind: 'webgl',
    deck,
    update(m) { model = m; deck.setProps({ layers: layers(m) }); },
    camera(preset, o = {}) {
      // {instant: true} on first open: the first frame (and every smoke screenshot) is already at the preset
      deck.setProps({ initialViewState: o.instant ? { ...cameraPreset(topology, preset) } : { ...cameraPreset(topology, preset), transitionDuration: 1400,
        transitionInterpolator: new D.FlyToInterpolator() } });
    },
    flyTo(lonlat, o = {}) {
      const base = cameraPreset(topology, 'street');
      deck.setProps({ initialViewState: { ...base, longitude: lonlat[0], latitude: lonlat[1] - 0.00025, zoom: o.zoom || 18.3, pitch: o.pitch ?? 55,
        bearing: o.bearing ?? base.bearing, transitionDuration: 1200, transitionInterpolator: new D.FlyToInterpolator() } });
    },
    onPick(cb) { pick = cb; },
    onHover(cb) { hover = cb; },
    dispose() { deck.finalize(); },
    whenRendered() { return new Promise((res) => { waiters.push(res); deck.redraw(true); }); },
  };
  return api;
}
