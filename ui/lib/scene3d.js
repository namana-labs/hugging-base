// ui/lib/scene3d.js -- OWNED BY L4 (3D + P1 view). This is L0's STUB: deck.gl 9.4.0 (vendored, global `deck`),
// plain ColumnLayers, no footprints. L4 replaces the body and keeps the Scene API (docs/contracts.md):
//   createScene(el, opts) -> scene        opts: {topology, theme, onError(err), viewState?}
//   scene.update(model)                   model from scene-model.js buildSceneModel()
//   scene.camera(preset)                  'feeder' | 'street' | 't240' (fly-to)
//   scene.onPick(cb)                      cb({layer, object, index})
//   scene.dispose()                       deck.finalize(); only ?smoke=dump calls it in the page
//   scene.whenRendered() -> Promise       resolves after the next completed render (the shell's "ready")
//   scene.kind                            'webgl'
// createScene THROWS when deck.gl or WebGL2 is unavailable; the shell then uses fallback2d.js (same API).
import { cameraPreset } from './scene-model.js';

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
  let pick = null;
  let model = null;
  const deck = new D.Deck({
    parent: el,
    views: [new D.MapView({ repeat: false })],
    initialViewState: opts.viewState || cameraPreset(topology, 'feeder'),
    controller: true,
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

  function layers(m) {
    return [
      new D.PathLayer({ id: 'lines', data: m.lines, getPath: (d) => d.path, getColor: (d) => d.color, widthUnits: 'pixels', getWidth: 1.5 }),
      new D.ColumnLayer({ id: 'homes', data: m.homes, diskResolution: 8, radius: 7, extruded: true, pickable: true,
        getPosition: (d) => d.position, getElevation: (d) => d.height, getFillColor: (d) => d.color }),
      new D.ColumnLayer({ id: 'batteries', data: m.batteries, diskResolution: 12, radius: 4, extruded: true, pickable: true,
        getPosition: (d) => d.position, getElevation: (d) => d.height, getFillColor: (d) => d.color }),
      new D.ColumnLayer({ id: 'cans', data: m.cans, diskResolution: 16, extruded: true, pickable: true, radiusUnits: 'meters',
        getPosition: (d) => d.position, getElevation: (d) => d.height, getFillColor: (d) => d.color, radius: 1,
        getRadius: (d) => d.radius }),
      new D.TextLayer({ id: 'labels', data: m.labels, getPosition: (d) => d.position, getText: (d) => d.text, getColor: (d) => d.color,
        getSize: 16, getPixelOffset: [0, -18], fontWeight: 700 }),
    ];
  }

  return {
    kind: 'webgl',
    deck,
    update(m) { model = m; deck.setProps({ layers: layers(m) }); },
    camera(preset) {
      deck.setProps({ initialViewState: { ...cameraPreset(topology, preset), transitionDuration: 1200,
        transitionInterpolator: new D.FlyToInterpolator() } });
    },
    onPick(cb) { pick = cb; },
    dispose() { deck.finalize(); },
    whenRendered() { return new Promise((res) => { waiters.push(res); deck.redraw(true); }); },
  };
}
