## [l4-scene-p1] 3D scene + P1 view (lane L4)

Scope (build prompt section 6, row L4). Owns only `scripts/fetch_footprints.py`, `data/footprints/**`, `ui/data/footprints.json`, `ui/lib/{scene-model,scene3d,fallback2d}.js`, `ui/panels/p1.js`, `ui/css/p1.css`, `ui/test/{scene-model,p1}.test.js`. Head `0520ded`, with origin/main `2f5b87d` merged in (L2's real P1 data and L3's real P2 data are on this branch through main).

### NOT done (first)
1. **Scale ladder is not on screen**: `p1/meta.json` has no `scaleLadder` (not in the contract; judge R0 assigns it to l2-p1 plus a lead contract PR). The panel renders `meta.scaleLadder` generically once it exists.
2. **Playback speed on a GPU browser is UNVERIFIED.** Headless SwiftShader draws about 1 frame/s with 2,400 extruded footprints; the transport keeps time by skipping steps (JS per step about 1 ms).
3. **Not merged**: this lane does not merge its own PR; the lead's merge gate does.
4. P1 beat captions come from L5's caption bar (lead PR #10 mounts it); they appear once L5 (#9) merges.

### Fix round 0 (judge R0, clause C1)
- Synced with origin/main `2f5b87d` (clean merge `3d939ce`): the P1 view now plays **L2's real `ui/data/p1/*`** (fixture=0 on all 7 P1 links).
- `ui/data/footprints.json` producer is now `scripts.fetch_footprints` (PR #11 admits `scripts.<name>`); rebuilt offline from the cache, the rest of the file is identical.
- The hero now names the 15-minute spike's `driver` above the fold whenever that spike is the worst service transformer (within 15 min of its interval): home, SMART-DS profile, kW at the peak, and the other homes sharing the profile ("not independent evidence"); on the feeder-aware branch it also shows A's relief at its true size (122.1% -> 97.8%, 6.9 kW, amber not a failure). Numbers read from `meta.relief` / `meta.unrelieved`; tests added.

### What is in it
- **Footprints** (`scripts/fetch_footprints.py`, `data/footprints/SOURCE.md`, `ui/data/footprints.json` 638 KB): Overpass `way["building"]` in the feeder bbox (2,406 buildings, ODbL 1.0, © OpenStreetMap contributors); nearest area centroid within 25 m, greedy by distance, one home per footprint: **985 of 1,010 homes matched** (median 11.6 m), 25 drawn as 12 m squares (ASSUMPTION). The prompt's 1,007 counted homes with *a* footprint within 25 m, before the one-home-per-footprint rule (see NOTES). The 1,421 unmatched buildings are drawn as neutral context. Deterministic from the cache.
- **`scene-model.js`** (pure, node-tested): homes are extruded real footprints tinted by their transformer's tier code (dark / battery-backup states from `homeState`); cans are a wireframe ghost (100% of nameplate), a fill (OpenDSS loading, pokes out when over), a ring at 110% and a red cap at 150% (named cans and cans over nameplate), radius ~ sqrt(kVA); battery columns sit beside their homes (ghost = full, fill = SoC, 20% reserve ring, colour by state, a pulse on a changed command, "!" when stale or expired); A-D labels carry kVA and room to nameplate (DERIVED) or "over by x kVA"; T-240 labelled. Static geometry keeps its identity across frames, so deck.gl never re-tessellates. `pins`/`placed` for L5's P2 view. Camera presets: whole feeder, street A-D (zoom 18, pitch 55), Northbank T-240.
- **`scene3d.js`** (deck.gl 9.4.0 vendored; MapView, orbit + zoom, fly-to presets; labels shorten when zoomed out) and **`fallback2d.js`** (the same model on a canvas; pan + wheel zoom), same Scene API.
- **`panels/p1.js`**: branch toggle (naive carries its ASSUMPTION framing from `meta.naiveLabel`), the big number (worst service transformer now, OpenDSS, with its tier), tier and battery-state counts, "Pieces fail" events with the silent unit's live state, A-D + T-240 headroom gauges (home kW grey, battery kW accent, relief hatched, ticks 100/110/150 REAL and 200 fuse ASSUMPTION, evening max, minutes above 110/150%, the fuse margin), the orchestrator ticker, peak relief with its `driver` (shared profile disclosed), unrelieved -> P2 link, grid checks (voltage measured: "stays in range at unity pf" only when no home is below 0.95 pu; feeder head % of 370 A), the branch summary with the scoped claim, the money card (5.4.6: energy value per branch, cost of awareness, the capacity band only on fleet kW at the price peak, local relief unpriced, who pays, avoided harm), what the controller sees, sources. Over the scene: camera buttons, legend (three tiers + protection, homes, batteries, cans), ODbL + SMART-DS credits, and the transport (play, 0.5x-8x, 1 simulated minute per 100 ms at 1x, REAL price strip with the plan's discharge intervals, a tier-count ribbon, grouped data markers with their labels, click/drag scrub, arrow keys, `t` and `branch` kept in the URL).

### Acceptance (build prompt 7.5 and the L4 row), real output on this head
| Clause | Command | Output |
|---|---|---|
| node tests green | `node --test ui/test/*.test.js` | `pass 33, fail 0` on real P1 data |
| lane gate | `scripts/check_all.sh --lane l4-scene-p1` | `ALL CHECKS: PASS` (unit 102, node 33, keep 8+3+17, contracts 47 files 15.94 MB, `VERIFY p1: PASS (1 refuted: rotation)`, `VERIFY p2: PASS (0 refuted)`, paths 10 in lane, smoke 9/9) |
| `smoke_ui.sh p1` all ok on real data (fixture 0) | the gate's smoke step (`--lane` = p1 links + 3 canaries) | 9/9 ok, every P1 link `fixture=0` |
| screenshots >= 50 KB / >= 16 colours, two opened with Read | smoke shots | 406-789 KB, 823-1,750 colours; opened naive 22:30 (A 201.2%, footprints, gauges, transport), aware 16:45 (T-240 119.5% with driver Home 0409 `res_kw_38274_pu`; A relief 122.1% -> 97.8%), none 16:45 street (A 122.1%, driver Home 0212): scene present, numbers equal `p1/meta.json` |

Gate (head 0520ded):
```
CHECK root=/Users/rzalagbada/hb-overnight/wt/l4-scene-p1 head=0520ded lane=l4-scene-p1 full=0 py=/Users/rzalagbada/hb-overnight/.venv/bin/python logs=/Users/rzalagbada/hb-overnight/tmp/check-l4-scene-p1
STEP unit: PASS (Ran 102 tests)
STEP node: PASS (# pass 33 # fail 0 )
STEP keep: PASS (prototype 8 + 3, four-home 17)
CONTRACTS: PASS (47 files, 15.94 MB, 30460 labelled numbers)
STEP contract: PASS ((47 files, 15.94 MB, 30460 labelled numbers))
VERIFY labels: PASS (47 files, 30460 labelled numbers)
VERIFY p1: PASS (1 expectations refuted, see NOTES.md: rotation)
VERIFY p2: PASS (0 expectations refuted, see NOTES.md)
STEP verify: PASS (labels p1 p2)
PATHS: PASS (10 changed paths, all inside lane l4-scene-p1; base 2f5b87d)
STEP paths: PASS (lane l4-scene-p1)
SMOKE root=/Users/rzalagbada/hb-overnight/wt/l4-scene-p1 port=58189 mode=--lane links=9 shots=/Users/rzalagbada/hb-overnight/tmp/l4/shots-fr0c
SMOKE view=p1&branch=none&t=16:45&cam=street ok | status=ready webgl=ok errors=0 fixture=0 offsite=0 | 9351 ms | 615 KB | 1750 colours
SMOKE view=p1&branch=aware&t=16:45 ok | status=ready webgl=ok errors=0 fixture=0 offsite=0 | 4969 ms | 789 KB | 1656 colours
SMOKE view=p1&branch=naive&t=22:30 ok | status=ready webgl=ok errors=0 fixture=0 offsite=0 | 3956 ms | 785 KB | 1701 colours
SMOKE view=p1&branch=aware&t=22:30 ok | status=ready webgl=ok errors=0 fixture=0 offsite=0 | 4231 ms | 783 KB | 1663 colours
SMOKE view=p1&branch=aware_faults&t=22:16 ok | status=ready webgl=ok errors=0 fixture=0 offsite=0 | 4337 ms | 778 KB | 1625 colours
SMOKE view=p1&branch=naive&t=20:00&cam=feeder ok | status=ready webgl=ok errors=0 fixture=0 offsite=0 | 4010 ms | 786 KB | 1658 colours
SMOKE view=p1&branch=aware&t=22:30&nowebgl=1 ok | status=ready webgl=fallback errors=0 fixture=0 offsite=0 | 1459 ms | 406 KB | 823 colours
SMOKE view=p2&combo=aware-core-d26-g0 ok | status=ready webgl=ok errors=0 fixture=0 offsite=0 | 3858 ms | 627 KB | 1320 colours
SMOKE view=more ok | status=ready webgl=ok errors=0 fixture=0 offsite=0 | 3807 ms | 522 KB | 871 colours
SMOKE: 9/9 ok
STEP smoke: PASS (SMOKE: 9/9 ok)
CHECK took 53 s
ALL CHECKS: PASS
```

`git diff --stat origin/main...HEAD`:
```
 data/footprints/SOURCE.md   |  23 ++
 scripts/fetch_footprints.py | 238 ++++++++++++++
 ui/css/p1.css               | 119 ++++++-
 ui/data/footprints.json     |   1 +
 ui/lib/fallback2d.js        | 137 ++++++--
 ui/lib/scene-model.js       | 301 ++++++++++++++---
 ui/lib/scene3d.js           | 104 ++++--
 ui/panels/p1.js             | 776 ++++++++++++++++++++++++++++++++++++++++++--
 ui/test/p1.test.js          | 213 ++++++++++++
 ui/test/scene-model.test.js | 236 ++++++++++++++
 10 files changed, 2031 insertions(+), 117 deletions(-)
```

No REQUEST (lead) open (the earlier one landed as PR #11).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
