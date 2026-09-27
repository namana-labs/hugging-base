// simulators/rz: the folder runs on its own (run.sh serves it at /ui/) and from the repo root (/simulators/rz/ui/).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { teamHref } from '../panels/more.js';

test('teammate links: from the repo root they go up to the root folders; from this folder alone they open the team repo', () => {
  assert.equal(teamHref('four-home-simulation/four-home.html', '/simulators/rz/ui/'), '/four-home-simulation/four-home.html');
  assert.equal(teamHref('demos/grid-stories/ui/dist/', '/hb/simulators/rz/ui/index.html'), '/hb/demos/grid-stories/ui/dist/');
  assert.equal(teamHref('demos/grid-stories/ui/dist/', '/ui/'),
    'https://github.com/namana-labs/hugging-base/tree/main/demos/grid-stories/ui/dist/');
});
