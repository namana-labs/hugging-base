# Data sources, licences and labels

Every number on screen carries one of four labels. This page lists where each input comes from, its licence, and how it is labelled. The app replays committed files only: **no live data calls at view time**.

| Label | Covers |
|---|---|
| **REAL** | ERCOT prices; SMART-DS topology, kVA and transformer ratings; OSM footprints; sourced programme facts |
| **SIM** | our simulation's output (OpenDSS AC power flow, the per-transformer surrogate, the month model) |
| **DERIVED** | arithmetic on REAL or SIM: dollars, interpolated 1-minute load, the discharge plan, the D-26 onset, cliffs |
| **ASSUMPTION** | a named constant we chose: margins, the fuse rule, SoC at 16:00, growth, the 2018-load / 2026-price pairing, the fleet placement |

Four-home's `SOURCED` maps to REAL; `UNVERIFIED` maps to ASSUMPTION with "unverified" kept in the cite. Every constant is registered once in `sim/constants.py` with its label and cite, and exported into every JSON file's envelope.

## Inputs

| Input | Where in the repo | Licence / terms | Label | Notes |
|---|---|---|---|---|
| **ERCOT RTM settlement point prices, LZ_NORTH, 15-min, 1 Jan – 19 Sep 2026** | `data/ercot/lz_north_2026.csv`, `data/ercot/SOURCE.md` (sha256 of source and extract) | ERCOT public market data; may be redistributed in analyses; ERCOT's logo may not be used | REAL | ERCOT's `hour` is hour-ending: interval start = (hour−1)·60 + (interval−1)·15 min. The feeder is an **Oncor-suburb stand-in settled at LZ_NORTH (placeholder)**; the real P1U buses sit in **Pedernales Electric Cooperative** territory (PUCT service-area map, 2023, "information purposes only": 988 of 1,010 homes, 369 of 379 transformers, 93 of 96 fleet homes, A–D and T-240; corrected 26 Sep from "Austin Energy", TEAMMATES_REVIEW adopt #1). |
| **NREL SMART-DS 2018 AUS P1U feeder** `p1uhs19_1247--p1udt17263` | `data/smartds/*.dss` (byte copy of the prototype's), `ui/data/topology.json` | CC BY 4.0 (NREL) | REAL | 1,010 homes, 379 service transformers with their kVA and ratings (normal 1.1 × kVA, emergency 1.5 × kVA). One primary line lengthened 3× as in the prototype (ASSUMPTION, `topology.json` `meta.shaping`). |
| **SMART-DS load profiles, August slice** (kW and kvar shapes) | `data/profiles/smartds_2018_aug.npz`, `data/profiles/SOURCE.md` (sha256 manifest) | CC BY 4.0 (NREL) | shapes REAL; the loads they drive are SIM | 2018 weather-year load paired with 2026 prices **by calendar date** (ASSUMPTION). The timestamp convention and DST are unverified. 254 shapes are reused across 2,021 load objects: A's afternoon peak and T-240's are one shared profile (`res_kw_38274_pu`), disclosed wherever either appears (`driver`). |
| **OpenStreetMap building footprints** | `ui/data/footprints.json`, `data/footprints/SOURCE.md` | ODbL 1.0, "© OpenStreetMap contributors" | REAL | Matched to homes by nearest centroid within 25 m; a home with no footprint is drawn as a 12 m square (ASSUMPTION). |
| **The 96-battery fleet** | `data/fleet.json` | from the prototype (Connor), frozen | ASSUMPTION | The prototype's placement (seed 17263). |
| **Battery and programme facts** | `sim/constants.py` (each with its cite) | cites in `docs/research-report.md` and `docs/headroom/research_notes/` | REAL where sourced, ASSUMPTION where not | Core 20 kW (REAL); 37 kWh usable and 0.89 round-trip (ASSUMPTION, unpublished); 20% backup reserve (REAL); payer programmes (REAL, `docs/research-report.md:59, 215–224`); $3.12/kW-month grid-scale storage **revenue** benchmark (REAL, Modo April 2026, one month; it includes arbitrage and is not a capacity payment); $8.50 (DERIVED from an UNVERIFIED Austin Energy figure); Base's Houston charge block, −45.8 MW within 15 minutes on 22 Jul 2026 (REAL, Base blog "Aggregated DERs and the capacity crunch", `docs/research-report.md:207-212, 297`; `BASE_HOUSTON_CHARGE_BLOCK_MW`). |
| **Real ERCOT evenings (round 2): 22 Jul, 14 Aug, 23 Aug and 26 Aug 2026** | `ui/data/p1/days/index.json`, `p1/days/<date>/meta.json` and gzipped branch files (`sim.history`) | the ERCOT prices above; SMART-DS loads | prices REAL; each evening's OpenDSS run SIM; money DERIVED | Each evening is the real LZ_NORTH price for that date on our feeder, with the 2018 SMART-DS load of the same calendar date (ASSUMPTION). `aware_faults` is scripted for 23 Aug only. The P1 day chip and the More tab's "Real Texas evenings" card read the index. |
| **The money calendar (round 2)** | `ui/data/p1/days/calendar.json` (`sim.history`) | the ERCOT prices above | DERIVED | Prices only, no OpenDSS: one 20 kW Core, one D-26 cycle each evening from 1 Jan 2026 (sell the plan's top-priced intervals, buy back from the onset; perfect foresight, ASSUMPTION). Gross energy value, not Base's P&L. |
| **The team's grid findings** (voltage, feeder head) | read from `site/ems/volt-spec.md`, `flow-spec.md` | team-internal | REAL rating (head 370 A **per conductor**, SMART-DS NormAmps of `3P_UG_AL_350kcmil_3`); measurements SIM | The feeder head's kVA equivalents are DERIVED: 2,663.8 kVA per phase (370 A × 7.2 kV) is the one that binds; the balanced three-phase 7,991.5 kVA reads low when phases are unequal. |
| **ERCOT console: one recorded system day, 25 Sep 2026** (P3, the More tab) | `ui/data/ems/synth-console.json` and `freq-series.json`: byte copies of the team's `site/ems/` files; `ui/data/ems/index.json` lists their sha256 and the sha256 of every `site/ems/*.json` at snapshot time | ERCOT public dashboards and MIS reports (the EMS workflow recorded them; each item's spec in `site/ems/` gives the endpoint and retrieval time) | each number carries its field's status from the bundle (`real5.fields`): frequency and PRC samples, demand, price REAL; net load, ramp, SCED counts, σ DERIVED; the fleet-scale thread DERIVED from Base-published fleet MW (REAL) | Recorded, not live, and a **different day** from P1 (23 Aug). `site/ems/SYNTHESIS.md` picks the four panels (frequency, PRC, net load and ramp, SCED congestion). The cards are computed in `ui/panels/more.js` (`emsModel`) at view time; `ui/test/p2.test.js` recomputes every card number from the snapshot. |
| **deck.gl 9.4.0** | `ui/vendor/deck-9.4.0.min.js`, `ui/vendor/LICENSE-deck.gl` | MIT | n/a | Vendored and served locally; sha256 checked by `ui/test/core.test.js`. |

## What we computed (SIM / DERIVED)

- **OpenDSS** (OpenDSSDirect.py 0.9.4) solves the feeder every minute of every P1 branch and refereed the P2 shortlist. Batteries run at **unity power factor** (ASSUMPTION); the prototype's batteries drew reactive power at OpenDSS's default 0.88 power factor, which overstated battery loading.
- **The surrogate** (P2 screening) sums home P and Q per transformer with losses from `Transformers.dss`, calibrated against held-out OpenDSS frames; its measured error is in `data/profiles/SOURCE.md` and on the P2 referee badge.
- **Tiers** (`sim/tiers.py`, computed once, never in the browser): over nameplate above 100% (amber, not a violation); normal rating exceeded above 110% for 30 minutes or more (the headline violation); emergency above 150%. The protection rule (fuse opens above 200% for 10 minutes or above 300% for 60 seconds) is the team's round-1 ASSUMPTION, shown with its margin and never tuned.
- **Prices:** the D-26 charge onset, the discharge plan (perfect foresight, ASSUMPTION: Base's optimizer is not public) and the price cliffs (a fall of at least half within one 15-minute interval from $60 or more) are DERIVED in `sim/prices.py`.

## Not ours, unchanged

- `demos/grid-stories/` (Connor's prototype): its prices and loads are scripted; its adversary is fictional. Linked from the More tab, never edited.
- `four-home-simulation/` (Michael's four-home model): linked from the More tab, never edited.
