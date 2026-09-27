# [l5-p2-story] fix round 1 (judge R1 F3, F4, F7, F8, F9) + P3 ERCOT console

Lane: **l5-p2-story** only (`ui/panels/{p2,more}.js`, `ui/css/p2.css`, `ui/data/beats.json`, `ui/data/ems/**`, `ui/test/p2.test.js`, `docs/{demo-script,data-sources,run-the-demo}.md`). Head `1799c6f` (origin/main `b866712` merged in).

| Clause | Command | Real output |
|---|---|---|
| F3 screening chip on every surrogate-only number; OpenDSS numbers where the referee ran | `node --test ui/test/*.test.js` (p2.test.js mounts all 16 combos + the 2 extra P2 links + the P2 beats in node) | `F3: every P2 link renders no "not OpenDSS-checked" number without the screening chip` ok; `F3, REAL data: the naive "where NOT to put it" card, the flip #1 line and the handoff card` ok (handoff shows OpenDSS 119.5% / 96.9%); the same tests fail on the pre-fix `p2.js` (checked in a scratch copy) |
| F4 scale ladder in the problem beat; demo script final | same | `F4: the problem caption templates every scale-ladder rung from the data, with labels` ok; caption reads "160% DERIVED of A (25 kVA REAL); 0.50% DERIVED of this feeder (7,991.5 kVA DERIVED); 0.000049% DERIVED of ERCOT (81,612 MW REAL on 2026-09-25)"; `grep 'at the time of writing' docs/demo-script.md` → nothing; script marked **final** |
| F7 relief wording as measured | same | `F7: ...` ok; caption: "its own batteries discharge up to 6.9 kW SIM (16:46 SIM)" |
| F8 handoff label overlap | same + screenshot | `F8: the P1 handoff merges into the T-240 label` ok; the scene label reads "T-240 · P1: unrelieved" |
| F9 units on the performance card | same | `F9: engine.json rows carry their unit` ok; "allocate(), 100,000 batteries 65,012 µs per call SIM" |
| P3 ERCOT console (5.7.3) | same | sha256 of the snapshot matches its manifest; every card number equals an independent recomputation; More renders 4 console cards |
| Lane gate | `scripts/check_all.sh --lane l5-p2-story` | see below |

```
STEP unit: PASS (Ran 111 tests)
STEP node: PASS (# pass 86 # fail 0 )
STEP keep: PASS (prototype 8 + 3, four-home 17)
STEP contract: PASS ((51 files, 16.13 MB, 30467 labelled numbers))
STEP verify: PASS (labels p1 p2)
STEP paths: PASS (lane l5-p2-story)
STEP smoke: PASS (SMOKE: 32/32 ok)
ALL CHECKS: PASS
```

Nothing outside the lane; `scripts/check_paths.py --lane l5-p2-story` → `PATHS: PASS (11 changed paths, all inside lane l5-p2-story; base b866712)`.

**NOT done:** the ERCOT console has no deep link of its own (it sits at the bottom of `view=more`); adding one would need a `deeplinks.txt` line (lead-only). The snapshot copies 2 of the 11 `site/ems` JSON files (the ones the cards read); the manifest lists the sha256 of all 11.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
