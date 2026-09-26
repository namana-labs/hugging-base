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
| **ERCOT RTM settlement point prices, LZ_NORTH, 15-min, 1 Jan – 19 Sep 2026** | `data/ercot/lz_north_2026.csv`, `data/ercot/SOURCE.md` (sha256 of source and extract) | ERCOT public market data; may be redistributed in analyses; ERCOT's logo may not be used | REAL | ERCOT's `hour` is hour-ending: interval start = (hour−1)·60 + (interval−1)·15 min. The feeder is an **Oncor-suburb stand-in settled at LZ_NORTH (placeholder)**; the real P1U buses sit in Austin Energy territory. |
| **NREL SMART-DS 2018 AUS P1U feeder** `p1uhs19_1247--p1udt17263` | `data/smartds/*.dss` (byte copy of the prototype's), `ui/data/topology.json` | CC BY 4.0 (NREL) | REAL | 1,010 homes, 379 service transformers with their kVA and ratings (normal 1.1 × kVA, emergency 1.5 × kVA). One primary line lengthened 3× as in the prototype (ASSUMPTION, `topology.json` `meta.shaping`). |
| **SMART-DS load profiles, August slice** (kW and kvar shapes) | `data/profiles/smartds_2018_aug.npz`, `data/profiles/SOURCE.md` (sha256 manifest) | CC BY 4.0 (NREL) | shapes REAL; the loads they drive are SIM | 2018 weather-year load paired with 2026 prices **by calendar date** (ASSUMPTION). The timestamp convention and DST are unverified. 254 shapes are reused across 2,021 load objects: A's afternoon peak and T-240's are one shared profile (`res_kw_38274_pu`), disclosed wherever either appears (`driver`). |
| **OpenStreetMap building footprints** | `ui/data/footprints.json`, `data/footprints/SOURCE.md` | ODbL 1.0, "© OpenStreetMap contributors" | REAL | Matched to homes by nearest centroid within 25 m; a home with no footprint is drawn as a 12 m square (ASSUMPTION). |
| **The 96-battery fleet** | `data/fleet.json` | from the prototype (Connor), frozen | ASSUMPTION | The prototype's placement (seed 17263). |
| **Battery and programme facts** | `sim/constants.py` (each with its cite) | cites in `docs/research-report.md` and `docs/headroom/research_notes/` | REAL where sourced, ASSUMPTION where not | Core 20 kW (REAL); 37 kWh usable and 0.89 round-trip (ASSUMPTION, unpublished); 20% backup reserve (REAL); payer programmes (REAL, `docs/research-report.md:59, 215–224`); $3.12/kW-month market benchmark (REAL, Modo April 2026); $8.50 (DERIVED from an UNVERIFIED Austin Energy figure). |
| **The team's grid findings** (voltage, feeder head) | read from `site/ems/volt-spec.md`, `flow-spec.md` | team-internal | REAL rating (head 370 A, SMART-DS NormAmps); measurements SIM | The feeder head's kVA equivalent is DERIVED. |
| **ERCOT console snapshots** (P3, if present) | `ui/data/ems/` with sha256s | as each source | per card | Snapshots of `site/ems/*.json`; each card names its source file. |
| **deck.gl 9.4.0** | `ui/vendor/deck-9.4.0.min.js`, `ui/vendor/LICENSE-deck.gl` | MIT | n/a | Vendored and served locally; sha256 checked by `ui/test/core.test.js`. |

## What we computed (SIM / DERIVED)

- **OpenDSS** (OpenDSSDirect.py 0.9.4) solves the feeder every minute of every P1 branch and refereed the P2 shortlist. Batteries run at **unity power factor** (ASSUMPTION); the prototype's batteries drew reactive power at OpenDSS's default 0.88 power factor, which overstated battery loading.
- **The surrogate** (P2 screening) sums home P and Q per transformer with losses from `Transformers.dss`, calibrated against held-out OpenDSS frames; its measured error is in `data/profiles/SOURCE.md` and on the P2 referee badge.
- **Tiers** (`sim/tiers.py`, computed once, never in the browser): over nameplate above 100% (amber, not a violation); normal rating exceeded above 110% for 30 minutes or more (the headline violation); emergency above 150%. The protection rule (fuse opens above 200% for 10 minutes or above 300% for 60 seconds) is the team's round-1 ASSUMPTION, shown with its margin and never tuned.
- **Prices:** the D-26 charge onset, the discharge plan (perfect foresight, ASSUMPTION: Base's optimizer is not public) and the price cliffs (a fall of at least half within one 15-minute interval from $60 or more) are DERIVED in `sim/prices.py`.

## Not ours, unchanged

- `demos/grid-stories/` (Connor's prototype): its prices and loads are scripted; its adversary is fictional. Linked from the More tab, never edited.
- `four-home-simulation/` (Michael's four-home model): linked from the More tab, never edited.
