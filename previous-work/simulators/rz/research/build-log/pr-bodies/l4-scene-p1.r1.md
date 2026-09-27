# [l4-scene-p1] Fix round 1: 3D fills visible, scale ladder, export room

Lane: **l4-scene-p1** only (`ui/lib/{scene-model,scene3d}.js`, `ui/panels/p1.js`, `ui/css/p1.css`, `ui/test/{scene-model,p1}.test.js`). No `REQUEST (lead)`.

## What changed (judge round 1)
- **F1 (5.5 cans and battery columns):** the translucent `can-ghost-*` and `battery-ghost` ColumnLayers set `parameters: { depthWriteEnabled: false }`, so the can fills below 100% and the battery SoC fills (with their colours) show. A scene-model test reads `scene3d.js` and fails if either ghost writes depth again.
- **F2 (3.4 scale ladder):** the P1 panel draws three rungs. Each rung has its name, its share with a chip (2 significant figures below 0.1%, so ERCOT reads `0.000049%`), a log-scale bar, and its own text with the base's chip. The generic tree also prints small shares to 2 significant figures. The section now sits right after the A–D gauges.
- **F6 (5.5 headroom during back-feed):** a focus can whose metered P is below 0 is labelled "room to export X kW", with `E = sqrt(kVA^2 - Q^2) + P` at alpha = 1 (DERIVED), in both the 3D labels and the gauges. D at naive 21:29 now reads "room to export 0.3 kW" (it used to read "room 99.7 kW").
- **F7 (hero half):** "its batteries discharged up to 6.9 kW (16:46)". The time is read from `batKW` at the step that equals `meta.relief.reliefKW`.

## Clause -> command -> real output
| Clause | Command | Output |
|---|---|---|
| node tests green | `node --test ui/test/*.test.js` | `ℹ tests 75` / `ℹ pass 75` / `ℹ fail 0` |
| smoke p1 on real data, fixture 0 | `scripts/smoke_ui.sh p1` | `SMOKE: 7/7 ok` (all `fixture=0`, 409-789 KB, 825-1,966 colours) |
| lane gate | `scripts/check_all.sh --lane l4-scene-p1` | `ALL CHECKS: PASS` |
| F1 on screen | street shots opened with Read | A's can at aware 22:30 shows a green fill at about 96%; naive 22:30 red fill inside the glass; battery fills coloured |
| F2 on screen | screen text of `view=p1&branch=naive&t=22:30` | `ERCOT: system demand` / `0.000049%DERIVED` / `40 kW is 0.000049% of ERCOT's 81,612 MW peak demand (2026-09-25 16:40 CT) REAL` |
| F6 on screen | screen text of `view=p1&branch=naive&t=21:29&cam=street` | `home 10.3 kW · batteries -60.0 kW SIM · room to export 0.3 kWDERIVED` |

## Acceptance output

`scripts/check_all.sh --lane l4-scene-p1`
```
CHECK root=/Users/rzalagbada/hb-overnight/wt/l4-scene-p1 head=adbb420 lane=l4-scene-p1 full=0 py=/Users/rzalagbada/hb-overnight/.venv/bin/python logs=/Users/rzalagbada/hb-overnight/tmp/check-l4-scene-p1
== 1 unit
STEP unit: PASS (Ran 111 tests)
== 2 node
STEP node: PASS (# pass 75 # fail 0 )
== 3 keep (7.1)
keep: grid-stories py ok (Ran 8 tests) ; grid-stories node ok (# pass 3 # fail 0 ) ; four-home ok (Ran 17 tests)
STEP keep: PASS (prototype 8 + 3, four-home 17)
== 4 contract
contract total 48 files, 15.95 MB (budget 25.0 MB, 4.0 MB per file); 30467 labelled numbers
CONTRACTS: PASS (48 files, 15.95 MB, 30467 labelled numbers)
STEP contract: PASS ((48 files, 15.95 MB, 30467 labelled numbers))
== 5 verify
VERIFY labels: PASS (48 files, 30467 labelled numbers)
VERIFY p1: PASS (1 expectations refuted, see NOTES.md: rotation)
VERIFY p2: PASS (0 expectations refuted, see NOTES.md)
STEP verify: PASS (labels p1 p2)
== 6 paths
PATHS: PASS (6 changed paths, all inside lane l4-scene-p1; base 995cd3e)
STEP paths: PASS (lane l4-scene-p1)
== 7 smoke
SMOKE root=/Users/rzalagbada/hb-overnight/wt/l4-scene-p1 port=63508 mode=--lane links=9 shots=/Users/rzalagbada/hb-overnight/tmp/shots-l4-scene-p1
SMOKE view=p1&branch=none&t=16:45&cam=street ok | status=ready webgl=ok errors=0 fixture=0 offsite=0 | 9793 ms | 600 KB | 1966 colours
SMOKE view=p1&branch=aware&t=16:45 ok | status=ready webgl=ok errors=0 fixture=0 offsite=0 | 4759 ms | 789 KB | 1692 colours
SMOKE view=p1&branch=naive&t=22:30 ok | status=ready webgl=ok errors=0 fixture=0 offsite=0 | 4006 ms | 784 KB | 1738 colours
SMOKE view=p1&branch=aware&t=22:30 ok | status=ready webgl=ok errors=0 fixture=0 offsite=0 | 4382 ms | 783 KB | 1702 colours
SMOKE view=p1&branch=aware_faults&t=22:16 ok | status=ready webgl=ok errors=0 fixture=0 offsite=0 | 4486 ms | 778 KB | 1661 colours
SMOKE view=p1&branch=naive&t=20:00&cam=feeder ok | status=ready webgl=ok errors=0 fixture=0 offsite=0 | 4068 ms | 786 KB | 1699 colours
SMOKE view=p1&branch=aware&t=22:30&nowebgl=1 ok | status=ready webgl=fallback errors=0 fixture=0 offsite=0 | 1176 ms | 409 KB | 825 colours
SMOKE view=p2&combo=aware-core-d26-g0 ok | status=ready webgl=ok errors=0 fixture=0 offsite=0 | 4261 ms | 746 KB | 1602 colours
SMOKE view=more ok | status=ready webgl=ok errors=0 fixture=0 offsite=0 | 5620 ms | 650 KB | 833 colours
SMOKE: 9/9 ok
STEP smoke: PASS (SMOKE: 9/9 ok)
CHECK took 57 s
ALL CHECKS: PASS
```

`scripts/smoke_ui.sh p1`
```
SMOKE root=/Users/rzalagbada/hb-overnight/wt/l4-scene-p1 port=63635 mode=p1 links=7 shots=/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/shots/l4-r1
SMOKE view=p1&branch=none&t=16:45&cam=street ok | status=ready webgl=ok errors=0 fixture=0 offsite=0 | 9484 ms | 600 KB | 1966 colours
SMOKE view=p1&branch=aware&t=16:45 ok | status=ready webgl=ok errors=0 fixture=0 offsite=0 | 4918 ms | 789 KB | 1692 colours
SMOKE view=p1&branch=naive&t=22:30 ok | status=ready webgl=ok errors=0 fixture=0 offsite=0 | 4052 ms | 784 KB | 1738 colours
SMOKE view=p1&branch=aware&t=22:30 ok | status=ready webgl=ok errors=0 fixture=0 offsite=0 | 4485 ms | 783 KB | 1702 colours
SMOKE view=p1&branch=aware_faults&t=22:16 ok | status=ready webgl=ok errors=0 fixture=0 offsite=0 | 4319 ms | 778 KB | 1661 colours
SMOKE view=p1&branch=naive&t=20:00&cam=feeder ok | status=ready webgl=ok errors=0 fixture=0 offsite=0 | 4050 ms | 786 KB | 1699 colours
SMOKE view=p1&branch=aware&t=22:30&nowebgl=1 ok | status=ready webgl=fallback errors=0 fixture=0 offsite=0 | 1142 ms | 409 KB | 825 colours
SMOKE: 7/7 ok
```

`git diff --stat origin/main...HEAD`
```
 ui/css/p1.css               | 15 +++++++
 ui/lib/scene-model.js       | 30 +++++++++++---
 ui/lib/scene3d.js           |  5 ++-
 ui/panels/p1.js             | 99 +++++++++++++++++++++++++++++++++++++++------
 ui/test/p1.test.js          | 74 ++++++++++++++++++++++++++++++++-
 ui/test/scene-model.test.js | 56 +++++++++++++++++++++++--
 6 files changed, 254 insertions(+), 25 deletions(-)
```

## NOT done
- Nothing from judge R1 that belongs to this lane. L4 has no P3 item (5.7).
- The `peak-relief` caption (F7, the caption half), the `problem` caption with the ladder (F4), and the P2 pin label overlap (F8) belong to l5-p2-story.
- Playback speed in a GPU browser is UNVERIFIED; headless SwiftShader only.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
