// ui/lib/scene3d.js (L4, 3D + P1 view): deck.gl 9.4.0 (vendored, global `deck`), MapView with no basemap and a flat
// --bg, lon/lat straight from topology. Draws the arrays of scene-model.js; knows nothing about the data files.
// Scene API (docs/contracts.md A.9; fallback2d.js has the same shape):
//   createScene(el, opts) -> scene        opts: {topology, theme, onError(err), viewState?}
//   scene.update(model)                   model from scene-model.js buildSceneModel()
//   scene.camera(preset)                  'feeder' | 'street' | 't240' (fly-to)
//   scene.onPick(cb)                      cb({layer, object, index})
//   scene.dispose()                       deck.finalize(); only ?smoke=dump calls it in the page
//   scene.whenRendered() -> Promise       resolves after the next completed render (the shell's "ready")
//   scene.kind                            'webgl'
// createScene THROWS when deck.gl or WebGL2 is unavailable; the shell then uses fallback2d.js.
//
// Layers (build prompt 5.5): context buildings + homes (extruded real OSM footprints, PolygonLayer), lines (PathLayer),
// transformer cans (ColumnLayers: a wireframe ghost = 100% of nameplate, a fill = OpenDSS loading coloured by tier, a
// ring at 110% and a red cap at 150%; ColumnLayer's radius is per layer, so one set per kVA class keeps radius ~ sqrt(kVA)),
// batteries (ghost = full capacity, fill = SoC, a ring at the 20% reserve), a ScatterplotLayer pulse on a changed
// command, '!' on stale/expired units, and TextLayer labels.
import { cameraPreset, BAT_R_M } from './scene-model.js';

export function webgl2Available() {
  try {
    const c = document.createElement('canvas');
    return !!(c.getContext('webgl2'));
  } catch (e) {
    return false;
  }
}

function groupBy(arr, keyFn) {
  const m = new Map();
  for (const x of arr) {
    const k = keyFn(x);
    if (!m.has(k)) m.set(k, []);
    m.get(k).push(x);
  }
  return m;
}

export function createScene(el, opts = {}) {
  const D = window.deck;
  if (!D || !D.Deck) throw new Error('deck.gl not loaded');
  if (!webgl2Available()) throw new Error('WebGL2 unavailable');
  const topology = opts.topology;
  let waiters = [];
  let pick = null;
  let model = null;
  let version = 0;
  const deck = new D.Deck({
    parent: el,
    views: [new D.MapView({ repeat: false })],
    initialViewState: opts.viewState || cameraPreset(topology, 'feeder'),
    controller: { dragRotate: true, touchRotate: true, scrollZoom: true, doubleClickZoom: true, keyboard: true },
    layers: [],
    useDevicePixels: true,
    onAfterRender: () => {
      if (!model) return;
      const w = waiters; waiters = [];
      for (const f of w) f();
    },
    onError: (err) => { if (opts.onError) opts.onError(err); },
    onClick: (info) => { if (pick && info && info.object) pick({ layer: info.layer && info.layer.id, object: info.object, index: info.index }); },
  });

  function layers(m, ver) {
    const ink = m.ink;
    const out = [
      new D.PolygonLayer({ id: 'context', data: m.context, extruded: true, filled: true, stroked: false, pickable: false,
        getPolygon: (d) => d.polygon, getElevation: (d) => d.height, getFillColor: (d) => d.color }),
      new D.PathLayer({ id: 'lines', data: m.lines, getPath: (d) => d.path, getColor: (d) => d.color, widthUnits: 'pixels', getWidth: 1.4 }),
      new D.PolygonLayer({ id: 'homes', data: m.homeGeom, extruded: true, filled: true, stroked: false, pickable: true,
        getPolygon: (d) => d.polygon, getElevation: (d) => d.height,
        getFillColor: (d) => m.homes[d.i].color,
        updateTriggers: { getFillColor: ver } }),
    ];
    // transformer cans, one set of ColumnLayers per radius (kVA class)
    const ghostsBy = groupBy(m.canGhosts, (d) => d.radius);
    for (const [r, g] of ghostsBy) {
      out.push(new D.ColumnLayer({ id: `can-ghost-${r.toFixed(3)}`, data: g, radius: r, diskResolution: 24, extruded: true,
        filled: true, wireframe: true, getPosition: (d) => d.position, getElevation: (d) => d.height,
        getFillColor: [ink[0], ink[1], ink[2], 18], getLineColor: [ink[0], ink[1], ink[2], 90], pickable: false }));
    }
    for (const [r, g] of groupBy(m.cans, (d) => d.radius)) {
      out.push(new D.ColumnLayer({ id: `can-fill-${r.toFixed(3)}`, data: g, radius: r * 0.8, diskResolution: 24, extruded: true,
        getPosition: (d) => d.position, getElevation: (d) => d.height, getFillColor: (d) => d.color, pickable: true }));
    }
    for (const [r, g] of groupBy(m.canRings, (d) => d.radius)) {
      out.push(new D.ColumnLayer({ id: `can-ring110-${r.toFixed(3)}`, data: g, radius: r, diskResolution: 24, extruded: true,
        getPosition: (d) => d.position, getElevation: 0.5, getFillColor: [ink[0], ink[1], ink[2], 150], pickable: false }));
    }
    for (const [r, g] of groupBy(m.canCaps, (d) => d.radius)) {
      out.push(new D.ColumnLayer({ id: `can-cap150-${r.toFixed(3)}`, data: g, radius: r, diskResolution: 24, extruded: true,
        getPosition: (d) => d.position, getElevation: 0.6, getFillColor: [208, 59, 59, 210], pickable: false }));
    }
    out.push(
      new D.ColumnLayer({ id: 'battery-ghost', data: m.batteryGhosts, radius: BAT_R_M, diskResolution: 12, extruded: true,
        filled: true, wireframe: true, getPosition: (d) => d.position, getElevation: (d) => d.height,
        getFillColor: [ink[0], ink[1], ink[2], 16], getLineColor: [ink[0], ink[1], ink[2], 110] }),
      new D.ColumnLayer({ id: 'batteries', data: m.batteries, radius: BAT_R_M * 0.8, diskResolution: 12, extruded: true, pickable: true,
        getPosition: (d) => d.position, getElevation: (d) => d.height, getFillColor: (d) => d.color }),
      new D.ColumnLayer({ id: 'battery-reserve', data: m.reserveRings, radius: BAT_R_M * 1.3, diskResolution: 12, extruded: true,
        getPosition: (d) => d.position, getElevation: 0.3, getFillColor: [ink[0], ink[1], ink[2], 170] }),
      new D.ScatterplotLayer({ id: 'pulses', data: m.pulses, getPosition: (d) => d.position, getRadius: 5.5, radiusUnits: 'meters',
        filled: false, stroked: true, getLineColor: (d) => d.color, lineWidthUnits: 'pixels', getLineWidth: 2.5 }),
      new D.TextLayer({ id: 'alerts', data: m.alerts, getPosition: (d) => d.position, getText: (d) => d.text, getSize: 20,
        getColor: [255, 255, 255, 255], fontWeight: 800, background: true, getBackgroundColor: [110, 114, 111, 235],
        backgroundPadding: [5, 1, 5, 1], billboard: true }),
      new D.TextLayer({ id: 'labels', data: m.labels, getPosition: (d) => d.position, getText: (d) => d.text,
        getColor: (d) => d.color, getSize: (d) => (d.pin ? 13 : 15), fontWeight: 700, characterSet: 'auto',
        fontFamily: 'Inter, "Helvetica Neue", Helvetica, Arial, sans-serif',
        background: true, getBackgroundColor: m.theme === 'dark' ? [17, 24, 21, 225] : [247, 249, 245, 230],
        backgroundPadding: [6, 3, 6, 3], getPixelOffset: [0, -4], billboard: true }),
    );
    return out;
  }

  return {
    kind: 'webgl',
    deck,
    update(m) { model = m; version += 1; deck.setProps({ layers: layers(m, version) }); },
    camera(preset) {
      deck.setProps({ initialViewState: { ...cameraPreset(topology, preset), transitionDuration: 1400,
        transitionInterpolator: new D.FlyToInterpolator() } });
    },
    onPick(cb) { pick = cb; },
    dispose() { deck.finalize(); },
    whenRendered() { return new Promise((res) => { waiters.push(res); deck.redraw(true); }); },
  };
}
