# RZ feedback after testing the build (26 Sep 2026, ~09:10 CDT) — round 2 brief

RZ ran the app himself (P1 and P2, all branches). Verdict: **P1 and P2 answer the right questions.** He likes:
- seeing A–D, which transformers go red and how they go red;
- the worst transformer shown now;
- switching between no batteries / naive / feeder-aware / aware + failures;
- zooming into the 3D streets.

## What round 2 must do (his priorities, in order)

### 1. Visual clarity (P1 first, then P2)
- **Declutter the right-side panel.** The orchestrator ticker, the peak relief card and the rest carry too much at once. Rewrite them in simple terms anyone understands. Put the most important information in front. Everything else goes into **collapsible sections**, or opens a detail sub-page/drawer to read more.
- **Grab attention on first open and be self-explanatory.** A first-time viewer should know what to look at within seconds.
- **Headroom gauges (Street A–D, T-240):** show batteries as **actual battery icons** (fill level = charge), not bars going up and down.
- **Fewer raw numbers, more icons that illustrate meaning.**
  - Keep the worst transformer's % visible.
  - Most other numbers, especially the red ones, become visual states or icons.
  - Honesty labels (REAL / SIM / DERIVED / ASSUMPTION) must stay, but as compact visual markers (a small dot or badge with a hover tooltip), not text clusters.
- **Hover explanations** instead of explanation buttons. Hover any icon or 3D object to see what it is and what is happening to it right now.
- **Slower playback.** 0.5× is still too fast; he wants to watch what happens. Add 0.1× and 0.25×, and a step-one-minute control.
- **3D realism and recognisability.**
  - Houses more realistic: pitched roofs, house-like proportions and colours.
  - Transformers must look like transformers: a pad-mount green box or pole-mount can, with a recognisable icon. Their load and headroom are shown in a way that explains itself.
  - Batteries must be instantly distinguishable from transformers and houses: a distinct shape and colour, like a Base battery cabinet beside the house with a charge level.
  - A small visual legend: house, battery, transformer.
- **Tell the story visually.** Especially for naive, show step by step what happens: the price drops, every battery charges at once, the transformer overloads. Use on-screen story cues and icons. The team narrates the video, but the visuals should carry the story too.

### 2. Data correctness
- Every number and label on screen must be right. Audit P1 and P2 against OpenDSS and the sources, and fix anything wrong.

### 3. Real historical time
- Let the user **jump between real dates and times** from historical data: real ERCOT days, not only 23 Aug 2026.
- Show **how Base makes money during peak hours** with its batteries and feeders, using real prices, and how that is useful for Base.
- Be creative.

## Constraints
- **Weekly usage** is at 79% at 14:13 UTC, and the 95% weekly stop is RZ's rule. Keep round 2 lean and leave headroom for Sunday morning fixes. Submission is Sun 27 Sep 11:00 CT.
- Everything from the build prompt still stands: honesty labels, OpenDSS judges, replay/static spine, lanes + merge gate, never touch demos/ or four-home-simulation/, commits as RZ, etc.

---

## UPDATE 26 Sep ~15:05 UTC — Connor's design handoff (PR #24) and RZ's ruling (binding for every round-2 agent)

Connor merged PR #23 (`simulators/connor/`, a four-node simulator) and PR #24 into main at 14:55 UTC (main `93f448b`).
- PR #24 adds `docs/design-handoff/` (start at `docs/design-handoff/README.md`) and a `hugging-base-design` skill.
- It also edits `CLAUDE.md` to make the handoff "the authoritative design source" for UI work.
- **Fetch origin/main and read the handoff before any UI design or build.**

**RZ's ruling: merge both; RZ's round-2 asks win wherever they clash.**
- **Adopt from the handoff (its design language):**
  - the battery-shaped fleet card;
  - compact provenance tags (REAL/SIM/DERIVED/ASSUMPTION);
  - the story line;
  - the tier-count legend;
  - the rule "green never means safe" (the root app's bright green `--good` breaks it; fix it).
- **Where the handoff clashes with this file, this file wins:**
  - **Keep the worst-transformer %** visible (the handoff removes it).
  - **Slower playback:** 0.1× / 0.25× / 0.5× plus step. The handoff's 20-second day at ½×–2× is too fast for RZ.
  - **Tier rule:** the normal-rating violation stays at >110% for ≥30 minutes (team rule, root app, build prompt). The handoff's 20 minutes does not apply.
- **Never edit Connor's folders** (`simulators/connor/`, `demos/grid-stories/`) or Michael's (`four-home-simulation/`). Edit `docs/design-handoff/` only if a lane truly must; otherwise note the difference in `docs/how-base-plugs-in.md` or NOTES.

**Also adopt, from `overnight/TEAMMATES_REVIEW.md` (the judges' adopt-now list), each by its owner lane:**
1. **Territory cite is wrong** (l0 / l2):
   - 988 of 1,010 homes, 369 of 379 transformers, 93 of 96 fleet homes, and A–D and T-240 are in **Pedernales Electric Cooperative** territory (PUCT service-area map, 2023, "information purposes only"), not Austin Energy's.
   - Fix `STAND_IN` in `sim/constants.py`, `docs/data-sources.md` and any caption, and regenerate `ui/data/topology.json`.
   - The Oncor-suburb stand-in framing at LZ_NORTH (placeholder) stays.
2. **Anchor the "problem" beat on Base's real Houston charge swing:** −15.9 → −45.8 MW in 10–15 min on 22 Jul 2026 (REAL, Base blog; see `docs/research-report.md`). Add it as a constant beside the naive ASSUMPTION chip. (l0 constant, l5 caption)
3. **On the rebound-aware beat**, show the kW that feeder-aware charging defers at the price-collapse onset (about 1,326 kW at 22:00), next to "still 100% charged by 04:00" and the energy-value delta. (l2 data, l4/l5 UI)
4. **Add a power-balance test** to root `sim/tests`: head kW = Σ load kW + losses within 100 W on one snapshot with batteries. (l2)
5. **Honest copy on the More-tab teammate cards,** edited in our `ui/panels/more.js` only. (l5)
   - Connor's prototype: its battery loads run at 0.88 power factor, so its sag and trade-off figures are artefacts; it has a privileged voltage baseline and a fixed ±350 W detector wave.
   - The four-home card: its frequency figure uses the retired 3–5 mHz band.
6. **Add the TDSP-upgrade open question** to `docs/how-base-plugs-in.md`. (l5)
