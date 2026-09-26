// ui/lib/charts.js -- OWNED BY L5. L0's STUB: exports the chart names the panels will call; each draws a
// placeholder box. L5 replaces the bodies (plain SVG/canvas, no libraries) and may add exports.
//   priceStrip(el, {price[], markers[], label})   heatStrip(el, {values[31*24], label})
//   lineChart(el, {series[], label})              barChart(el, {bars[], label})
function placeholder(el, name) {
  if (!el) return null;
  el.textContent = `[${name}: chart pending (L5)]`;
  return el;
}
export const priceStrip = (el) => placeholder(el, 'price strip');
export const heatStrip = (el) => placeholder(el, 'heat strip');
export const lineChart = (el) => placeholder(el, 'line chart');
export const barChart = (el) => placeholder(el, 'bar chart');
