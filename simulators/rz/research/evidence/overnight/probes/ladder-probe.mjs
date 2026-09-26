import * as fmt from '/Users/rzalagbada/hb-overnight/wt/gate/ui/lib/format.js';
import { labelledTreeHTML } from '/Users/rzalagbada/hb-overnight/wt/gate/ui/panels/p1.js';
import fs from 'node:fs';
const m = JSON.parse(fs.readFileSync('/Users/rzalagbada/hb-overnight/wt/gate/ui/data/p1/meta.json'));
const h = labelledTreeHTML(fmt, m.scaleLadder);
const t = h.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
for (const s of ['0.0%', '0.000049', '0.5%', '160']) console.log(JSON.stringify(s), t.includes(s));
console.log(t.slice(t.indexOf('ERCOT'), t.indexOf('ERCOT') + 400));
