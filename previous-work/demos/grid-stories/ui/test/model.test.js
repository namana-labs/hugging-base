import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {rankCandidates,timeLabel,storyFor} from '../dist/model.js';
const candidates=JSON.parse(readFileSync(new URL('../dist/candidates.json',import.meta.url))).candidates;
const replays=JSON.parse(readFileSync(new URL('../dist/replays.json',import.meta.url)));
test('risk control changes an actual candidate ranking',()=>{const low=rankCandidates(candidates,0),high=rankCandidates(candidates,3);assert.notEqual(low[0].id,high[0].id);assert.equal(high.length,911);assert.ok(high.every((c,i)=>c.rank===i+1));});
test('narrative reflects physics and selected branch',()=>{assert.match(storyFor('rebound',replays.rebound.naive[7],'naive','observe').text,/29 transformers/);assert.match(storyFor('rebound',replays.rebound.aware[7],'aware','observe').text,/0 transformers/);assert.match(storyFor('covert',replays.covert.aware_quarantine[12],'aware','quarantine').title,/quarantined/);});
test('five-minute playback labels',()=>{assert.equal(timeLabel(1170),'19:30');assert.equal(timeLabel(1230),'20:30');});
