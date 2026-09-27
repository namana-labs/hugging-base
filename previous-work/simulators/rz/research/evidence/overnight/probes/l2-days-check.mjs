import { readFileSync } from 'node:fs';
const root = process.argv[2];
const days = await import(root + '/ui/lib/days.js');
const idx = JSON.parse(readFileSync(root + '/ui/data/p1/days/index.json', 'utf8'));
for (const r of idx.days) {
  const chip = days.dayChipHTML(idx, r.date);
  console.log(r.date, 'chip', chip.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 90));
}
const rows = days.dayRowsHTML(idx, '2026-07-22');
console.log('rows html', rows.length, 'chars; rows', (rows.match(/class="hb-dayrow"/g) || []).length);
// the browser path: DecompressionStream on the committed gzip bytes (what data.getGz does)
for (const d of ['2026-07-22', '2026-08-26', '2026-08-14']) {
  const buf = readFileSync(`${root}/ui/data/p1/days/${d}/aware.json.gz`);
  const doc = await new Response(new Blob([buf]).stream().pipeThrough(new DecompressionStream('gzip'))).json();
  console.log(d, 'aware.json.gz ->', doc.schema, doc.branch, doc.steps, 'steps; first byte', buf[0].toString(16), buf[1].toString(16));
}
