# HIST-R2: real historical evenings in P1 (round 2 scout spec)

Written 26 Sep 2026, 10:20 CDT, by the historical-days scout. It answers RZ's ask 3 in `RZ_FEEDBACK_R2.md`: jump between real dates and times, and see how Base makes money during peak hours at real prices.

- **Builders:**
  - **l2-p1:** the sim side (sections 4 and 5).
  - **l0:** lead files (section 6).
  - **l4-scene-p1:** P1 UI (section 7); l5 optionally adds beats and the More row.
- **Numbers:** every number below was **measured today** on main `0335760` with the repo's own code (`sim.p1_build.build(Window(day=...))`, OpenDSS every minute). None comes from a guess.
- **Evidence:** scripts and outputs are in `overnight/evidence/hist-r2/`.
  - The scripts: `hist_build2.py`, `mk_slices.py`, `cal_money.py`, `hist_days.py`.
  - Per-day `meta/<date>.meta.json`, `days_table.json`, and `calendar.json`.

---

## 0. Decisions in one screen

| # | Decision | Why (measured) |
|---|---|---|
| D1 | Ship **5 more simulated evenings** beside 23 Aug. Must: **22 Jul 2026, 26 Aug 2026, 14 Aug 2026**. Should: **11 Jul 2025**. Could: **16 Sep 2026**. | Each day tells a different money-versus-street story (section 2). |
| D2 | History days ship **3 branches (none, naive, aware)**. `aware_faults` and `chaos` stay 23 Aug only. | `aware_faults` **crashes** on 26 Aug. `_pick_silent`: "no battery on A-D is charging at the comms-loss step". 17 Aug, 11 Jul 2025 and 29 Mar needed a fallback. The failure script is tuned to 23 Aug. |
| D3 | History branch files are **gzip** (`*.json.gz`, level 9, `mtime=0`). `meta.json` stays plain. | A raw 3-branch day is 5.9 MB against **8.7 MB** of headroom (16.31 of 25 MB used), so one day fits. Gzipped it is **0.83 to 0.92 MB**, so five days fit in about 4.7 MB. |
| D4 | **23 Aug stays exactly where it is** (`ui/data/p1/*.json`). History days go under `ui/data/p1/days/`. | No churn to beats, tests, `verify p1 --rebuild` or smoke. `ui/data/p1/**` is already l2's. |
| D5 | Deep link **`&date=YYYY-MM-DD`**. The default `2026-08-23` is omitted from generated links. `t=HH:MM` keeps its meaning (local clock, 16:00 to 04:00). | Every existing link and beat keeps working unchanged. |
| D6 | A **prices-only money calendar** covers every evening from 1 Jan 2025 to 18 Sep 2026 (626 evenings, 4 of them DST gaps; about 15 KB). Simulated days are marked on it. | Any real date can be picked: the street for the 5 or 6 simulated evenings, the money for all of them. It takes 1.4 s of CPU to build. |
| D7 | Per day, the money is shown as **sold at the peak, bought back overnight, and net**, plus a climbing **money meter** and "feeder-aware earned +$X more than naive". Local relief stays **unpriced**. | Feeder-aware earned **more** than naive on every one of the 8 evenings simulated (+$9.28 to +$39.82, DERIVED). |

---

## 1. What exists on disk (measured)

| Input | Where | Covers | Label | Notes |
|---|---|---|---|---|
| ERCOT RTM SPP, LZ_NORTH, 15 min, 2026 | `data/ercot/lz_north_2026.csv` (committed) | 1 Jan to 19 Sep 2026 (25,148 rows) | REAL | The last full evening is **18 Sep** (the window needs 04:00 the next day). |
| ERCOT RTM SPP, all zones, 2025 | `evidence/scratchpad-20260925/bp-data-ingest/rtm2025_lz.csv` (not in the app repo). sha256 `03f00c40950eba6a3cf86cada257722000718eb6218d10c53fd51780ef34730a` | All of 2025: 35,040 LZ_NORTH rows, 4 of them `rep=Y` (the repeated 01:00 hour on 2 Nov 2025) | REAL | Needs an l0 extract (6.2). |
| SMART-DS 2018 AUS P1U shapes, August slice | `data/profiles/smartds_2018_aug.npz` (committed) | 1 Aug 2018 00:00 to 1 Sep 06:00 | SIM | Covers every August 2026 day, and nothing else. |
| SMART-DS 2018 full-year raw CSVs | `~/hb-overnight/cache/smartds/` (508 files, 333 MB, never committed) | All 365 days of 2018 | SIM | Checked: its August slice equals the committed npz exactly. It is read in 2.8 s. |
| ERCOT hourly native load, 2025 and 2026 | `evidence/.../bp-data-ingest/nl2025/Native_Load_2025.xlsx` (sha `23664b0c…`) and `nl2026/Native_Load_2026.xlsx` (sha `7ce76875…`) | 2025, and 2026 to **31 Aug** | REAL | Optional context line (6.6). It has no 16 Sep. |
| Weather | only `om_aug.json` (Aug **2023**), `om_uri.json` (Feb 2021), `om_fc.json` (25 Sep 2026) | none of the candidate days | none | **No weather for any candidate day on disk.** The SMART-DS 2018 weather year is the load's hidden weather. Use the feeder-load rank as the "how hot was the street" proxy (SIM). |

**Loads pairing** (existing ASSUMPTION `LOAD_PAIRING`): the load is SMART-DS 2018 on the same calendar date, so 2025-07-11 and 2026-07-11 both use 2018-07-11.

The SMART-DS feeder's highest evening of 2018 (16:00 to 04:00) is **23 Jul** at 7,206 kW. **22 Jul is the 3rd highest** (6,506 kW), 26 Aug the 11th, 23 Aug the 18th, 11 Jul the 75th and 16 Sep the 118th (SIM, `cal_money.py`).

---

## 2. The days (measured with the real P1 build)

All rows are the full 16:00 to 04:00 window: 720 steps of 60 s, OpenDSS every step, the same controller and the same D-26 plan as 23 Aug.

- Money ("$/battery", "aware − naive") is DERIVED: REAL prices × SIM kW, divided by 96 batteries.
- Loadings and events are SIM (OpenDSS).
- ERCOT demand is REAL.

| Date | Story tag | LZ_NORTH peak (REAL) | ERCOT hourly native load peak (REAL) | no batteries: max | naive: max, events | aware: max, battery-caused | aware $/battery | aware − naive |
|---|---|---|---|---|---|---|---|---|
| **Sun 23 Aug 2026** (default; all 4 branches, failures, chaos) | "The evening we know best" | $566.42 at 21:00 | 90,472 MW at HE18 (4th highest of 2026) | 122.1% A 16:45 (one home, 17 min) | 201.2% A 22:30; 11 normal, 3 emergency | 119.5% T-240 16:45 (home load, no battery); **0** | $9.55 | +$22.73 |
| **Wed 22 Jul 2026** | "Texas's record demand" | $344.13 at 22:00 | **91,134 MW at HE18: the all-time record** | 90.9% | 186.3% B 23:15; 8 normal, 3 emergency | 98.0%; **0** | $4.33 | +$29.47 |
| **Wed 26 Aug 2026** | "August's priciest evening" | **$780.72 at 22:15** (the August maximum) | 90,272 MW | 84.1% | 182.3% B 23:15; 8 normal, 3 emergency | 98.1%; **0** | **$13.71** | +$39.82 |
| **Fri 14 Aug 2026** | "A quiet night" | **$34.23** at 18:45 (D-26 non-binding, onset 19:00) | 87,835 MW | 79.0% | **214.1% B 19:00; 9 normal, 3 emergency, 2 fuses operate**; charged only 95.8% by 04:00 | 97.6%; **0** | **−$0.21** (cycling loses) | +$9.28 |
| **Fri 11 Jul 2025** | "Fifteen minutes that paid the night" | **$1,757.28 at 21:00** (the 2025 summer maximum; one 15-min interval) | 75,298 MW | 116.8% A 17:00 (home load, 14 min) | 195.4% A 21:45; 7 normal, 3 emergency | 115.1% T-240 17:00 (home load, no battery); **0**; A relief 5.56 kW | $10.08 | +$14.69 |
| Wed 16 Sep 2026 (could) | "A spike on a mild night" | **$1,016.32 at 20:00** (the best 2026 evening in the file) | not in file (ends 31 Aug) | 83.3% | 193.8% A 22:30; 7 normal, 3 emergency | 96.9%; **0** | **$22.17** | +$16.28 |
| Mon 17 Aug 2026 (not chosen) | | $437.83 | 89,128 (records page) | 84.5% | 201.4% A; 8 normal, **4** emergency | 98.0%; 0 | $7.43 | +$18.70 |
| Sun 29 Mar 2026 (not chosen) | spring, negative prices | $23.43 | | 90.3% | 212.3% C; 9 normal, 3 emergency, 1 fuse | 97.0%; 0 | $0.09 | +$15.25 |

**Why these five:**
- **22 Jul:** RZ's candidate and the record demand day (ERCOT records page and the Native Load file agree). The street is hot: the 3rd-highest SMART-DS evening. Yet the price peak is modest, because batteries flattened it (Grid Status, research report line 330).
- **26 Aug:** the August maximum-price day. It is Base's best August payday, and naive still breaks 3 transformers into emergency.
- **14 Aug:** the cheap day. **Negative prices are not available for a summer P1 evening.** In LZ_NORTH, June to September 2026 has one negative 15-minute interval in total (−$1.03, 18 Jun). The 67 evenings with a negative price inside 16:00 to 04:00 are all winter or spring, when the street is not stressed. So the cheap day is the flat summer night.
  - It carries **the sharpest insight of the scout.** On a night with nothing to earn, naive dispatch still hits **214.1%, the worst of all eight evenings**, and **2 fuses operate**, while losing $29.69.
  - Naive harm is caused by **synchronised charging**, not by price.
  - Negative prices still show on the calendar (section 7.3).
- **11 Jul 2025:** RZ's "2025 summer spike". A single 15-minute interval at $1,757.28 is about **88%** of that evening's net per battery ($8.79 of $10.04 on the price-only plan, DERIVED). The day also repeats 23 Aug's home-load spike on A, so relief shows up on a second day.
- **16 Sep (could):** the most money per battery of any 2026 evening in the file ($22.17), on a cool street (rank 118 of 365). It shows "money without street stress". It is cut first.

**Consistency check (DERIVED vs SIM, used as a verify [EXPECT] in 4.4):** the prices-only calendar's per-battery net agrees with the full sim's aware net within 3%, or within $0.05 when near zero (14 Aug: −$0.23 vs −$0.21).
- 23 Aug: calendar $9.43, sim naive $9.31, aware $9.55.
- 26 Aug: calendar $13.53, sim aware $13.71.
- 22 Jul: calendar $4.22, sim aware $4.33.

---

## 3. Data-correctness defects found on the way (l2; they matter the moment a second day exists)

1. **`relief.text` is a constant** (`sim/p1_build.py:632`): "over nameplate for about 15 minutes (amber; not a failure): one home's 15-minute spike". On 22 Jul, A never passes 51.8% (`relief.minutesOver100 = 0`), yet the text still says "over nameplate".
   - **Fix:** derive it.
     - If `minutesOver100.v == 0`: "A stays under its nameplate all evening (max {none}%)".
     - Otherwise: "over nameplate for {minutesOver100} minutes (amber; not a failure): {driver.label}'s load".
   - 23 Aug's text changes (17 min, not "about 15"), which matches UX-R2-story's `spike` caption. Rebuild, then commit the new 23 Aug `meta.json`.
2. **`markers[0].text` is a constant** (`sim/p1_build.py:677`): "A peaks at 51.8% with no batteries: one home's 15-minute spike" appears on 22 Jul. **Fix:** the same derivation. Emit the marker only when `minutesOver100 > 0`.
3. **`aware_faults` is 23-Aug-only** (D2). For history days, `build()` must accept `branches=("none", "naive", "aware")`. `assemble()` reads `runs["aware_faults"]` unconditionally (about line 656), so it must allow the branch to be absent: emit `events: {}`, `tc` as today, and `branches` listing only the three.
4. **DST spring-forward days break the D-26 search.** 2025-03-08/09 and 2026-03-07/08 have no 02:00 interval, so `price_at` raises `KeyError`. The calendar lists them in `gaps` with a reason; no P1 day may be one of them.
5. **Check, not assert: `reserveBreaches` on naive 14 Aug is 1,466.** Four homes are islanded behind 2 open fuses and run on their batteries below 20%. That is the member backup being *used*, not breached. l2 should decide whether islanded backup minutes count as a breach, and word it on screen accordingly. Today 23 Aug naive has no fuse operation, so the question never came up.
6. The `scaleLadder` ERCOT rung stays the 25 Sep demand CSV (its cite already says "not the P1 day"). The better per-day rung is the day's own hourly native load (REAL, 6.6), and it is optional.

---

## 4. Sim side: lane l2-p1

### 4.1 Files (all under paths l2 owns once l0 lands 6.1)

```
sim/history.py                      NEW   slices, day builds, calendar, index
sim/tests/test_history.py           NEW
sim/p1_build.py                     EDIT  build(win, branches=..., loads=...), assemble tolerant of 3 branches, derived relief/marker text, cash + sold/bought
sim/money.py                        EDIT  energy_split_usd(): sold (discharge revenue) and bought (charge cost) per branch
sim/verify_p1.py                    EDIT  --days: per-day invariants and rebuild
data/profiles/days/2026-07-22.npz   NEW   (and 2025-07-11, 2026-09-16); August days reuse smartds_2018_aug.npz
ui/data/p1/days/index.json          NEW
ui/data/p1/days/calendar.json       NEW
ui/data/p1/days/<date>/meta.json    NEW   plain JSON, same contract as p1/meta.json (A.5) + A.5h below
ui/data/p1/days/<date>/{none,naive,aware}.json.gz   NEW   gzip of the A.6 branch doc
```

### 4.2 `sim/history.py` API

```
DAYS = [  # order = drawer order; the tag and why are on-screen text, written from the measured table in section 2
  {"date": "2026-08-23", "tag": "The evening we know best",       "dir": None},   # the existing p1/*.json
  {"date": "2026-07-22", "tag": "Texas's record demand",          "dir": "days/2026-07-22"},
  {"date": "2026-08-26", "tag": "August's priciest evening",      "dir": "days/2026-08-26"},
  {"date": "2026-08-14", "tag": "A quiet night",                  "dir": "days/2026-08-14"},
  {"date": "2025-07-11", "tag": "Fifteen minutes that paid the night", "dir": "days/2025-07-11"},
  {"date": "2026-09-16", "tag": "A spike on a mild night",        "dir": "days/2026-09-16"},   # could; drop first
]
slice_loads(date, cache=~/hb-overnight/cache/smartds) -> Path
    # data/profiles/days/<date>.npz: 120 x 15 min from <date> 00:00 (to 06:00 the next day), every kW and kvar shape,
    # the same metadata arrays as smartds_2018_aug.npz, t0="<date>T00:00", source_t0="2018-<MM-DD>T00:00",
    # zip timestamps normalised (copy fetch_profiles._normalise_zip) so a rebuild is byte-identical.
    # August dates return data/profiles/smartds_2018_aug.npz and write nothing.
    # If the cache is missing, fail with the hint `python3 scripts/fetch_profiles.py --fetch-only`
    # (it refetches the same 508 public CSVs).
build_day(date, out=ui/data/p1/days/<date>) -> {sizes, seconds}
    # Window(day=date); Scenario(win, loads=Loads(npz=slice_loads(date))); branches none, naive, aware.
    # Writes meta.json plain (write_json) and each branch as gzip.compress(json_bytes, 9, mtime=0).
    # inputs: prices_sha256 = the price file(s) the day read (2025 file for 2025 dates);
    #         loads_sha256 = the npz used.
calendar(out=ui/data/p1/days/calendar.json)    # 4.3.2; prices only, no OpenDSS
index(out=ui/data/p1/days/index.json)          # 4.3.3; reads every built day's meta
main: python -m sim.history [--quick] [--only DATE] [--calendar-only]
    # --quick: calendar + one 60-step day into ~/hb-overnight/tmp/hist-quick, under 20 s, no lock
```

**Measured cost:**
- `build_day` takes 13 to 16 s of CPU per 4-branch day on this machine (the wall clock ran 13 to 33 s at load average 9 to 53); 3 branches take about ¾ of that.
- Five days take about **1 minute of CPU**: one heavy-lock hold.
- `calendar()` takes 1.4 s of CPU.
- Slicing reads the cache in 2.8 s. A slice measured 0.37 MB compressed at 192 steps; at 120 steps it should be about 0.25 MB (estimate).

### 4.3 Contracts (l0 copies these into `docs/contracts.md` as A.5h, A.6h, A.9, A.10)

#### 4.3.1 `p1/days/<date>/meta.json` (A.5h): A.5, with these differences

- `day`: the date; `start`, `stepSeconds` and `steps` as A.5.
- `branches: ["none", "naive", "aware"]`, `events: {}`, and no `aware_faults` keys anywhere (`summary`, `money.energyValueUSD`, `systemCapacityPerMonth`, `avoidedHarm`).
- `relief.text` and `markers` are derived (section 3, items 1 and 2).
- **New:** `story{tag, why{text, label}}`. `why` is a sentence with its numbers already formatted from this meta, for example "ERCOT's all-time demand record: 91,134 MW in the 5 to 6 pm hour (REAL)". A number from outside the meta (native load) needs `cite`.
- **New: `money.split{<branch>: {sold{v, label: "DERIVED", cite}, bought{v, ...}, net{v, ...}, perBattery{v, ...}}}`**.
  - `sold` = Σ over discharging steps of −P × price × dt: what the fleet sold, mostly at the peak.
  - `bought` = Σ over charging steps of P × price × dt.
  - `net` = sold − bought = `energyValueUSD`. This is an [INVARIANT].
  - `perBattery` = net / 96.
- **New: `cash{<branch>: [steps] int}`.** The cumulative fleet energy value in **cents** at the end of each step (DERIVED), so the UI never does money arithmetic. `cash[b][steps-1] / 100 == energyValueUSD[b]` to the cent is an [INVARIANT]. Label it once in `series.cash` as `{label: "DERIVED", unit: "USD cents, cumulative, fleet", by: "REAL LZ_NORTH x SIM battery kW"}`. It costs about 15 KB per day (estimate: 3 × 720 ints).
- **Also on 23 Aug's `p1/meta.json`:** add `money.split`, `cash` and `story` there too (a meta-only change; the branch files stay byte-identical), so the money meter works on every day.

#### 4.3.2 `p1/days/calendar.json` (A.9)

```json
{ "...envelope...": "producer sim.history, inputs.prices_sha256 = sha256 of the 2025 file + '+' + the 2026 file",
  "from": "2025-01-01", "to": "2026-09-18", "n": 626,
  "net":    [int, ...],   "sold": [int, ...], "bought": [int, ...],  // USD cents per 20 kW Core, one D-26 cycle; null on a gap
  "peak":   [int, ...],   // evening peak price, $/MWh x 100 (REAL); the peak searched from 17:00 as onset_d26
  "peakT":  "2100 2215 ...",           // HHMM of the peak, space-separated
  "onset":  "2200 +0215 ...",          // HHMM; "+" = after midnight
  "mode":   "bbnf...",                 // b binding, n non-binding, f fallback, - gap
  "negMin": [int, ...],                // minutes of negative price inside 16:00-04:00 (REAL)
  "sim":    {"2026-08-23": "", "2026-07-22": "days/2026-07-22", ...},   // simulated evenings: data dir ("" = p1/)
  "gaps":   [{"day": "2025-03-08", "reason": "DST: no 02:00 interval, D-26 search cannot run"}, ...],
  "headline": {
     "perBattery2025":       {"v": 329.57, "label": "DERIVED", "cite": "sum of net, 2025; one D-26 cycle a night, perfect foresight, energy only"},
     "perBattery2026ytd":    {"v": 284.68, "label": "DERIVED", "cite": "1 Jan to 18 Sep 2026"},
     "top10Share2026":       {"v": 55,     "label": "DERIVED", "cite": "share of 2026 net earned on the 10 best evenings"},
     "losingNights2026":     {"v": 85,     "label": "DERIVED", "cite": "evenings where one D-26 cycle loses money (0.89 round trip)"},
     "aug2026Top5Share":     {"v": 65,     "label": "DERIVED"} },
  "series": {"net": {"label": "DERIVED", "unit": "USD cents per 20 kW Core"}, "peak": {"label": "REAL", "unit": "$/MWh x100"}, ...},
  "constants": "export SOC0, RESERVE_FLOOR, CORE_USABLE_KWH, CORE_RTE, CORE_POWER_KW, ONSET_MEDIAN_MULT"
}
```

**The calendar rule** (DERIVED, the same as P1's naive market plan, on one Core):
- **Sell:** `discharge_plan(day, onset_d26(day), usable = (SOC0 − RESERVE_FLOOR) × 37 × √0.89 = 24.43 kWh, 20 kW)` sells the top-priced intervals between 16:00 and the onset.
- **Buy back:** 24.43 / 0.89 = 27.45 kWh at 20 kW from the onset, in time order.
- Measured size about 15 KB. `cal_money.py` in the evidence folder is the reference implementation, and its numbers are the ones above.

#### 4.3.3 `p1/days/index.json` (A.10)

- `days[{date, dow, tag, why{text, label}, dir, branches[], peak{v, label: "REAL", t}, perBattery{aware{v, label: "DERIVED"}}, naiveMax{v, label: "SIM", tf, t}, awareBatteryCaused{v, label: "SIM"}, sparkline[48]}]`.
- `sparkline` holds the 48 fifteen-minute prices from 16:00 to 04:00, in $/MWh (REAL, labelled in `series`).
- 23 Aug is row 0 with `dir: ""`.
- This file is all the day-chip popover needs; it must not load any branch file.

### 4.4 Verify (`sim.verify p1 --days`, in l2's `verify_p1.py`; l0 wires the flag in `sim/verify.py` if needed)

- **[INVARIANT], for every built day:**
  - aware `batteryCausedNormal == 0` and `batteryCausedEmergency == 0`;
  - `actedAfterExpiry == 0` and `nonIncreasingAccepted == 0`;
  - the reserve holds (aware);
  - every `.json.gz` decompresses to a doc that passes the A.6 shape checks;
  - `split.net == energyValueUSD`;
  - `cash` ends at `energyValueUSD`;
  - `relief.text` is consistent with `minutesOver100` ("under its nameplate" if and only if 0);
  - the `index.json` rows equal their metas;
  - `calendar.sim` names exactly the built days.
- **[EXPECT]:**
  - the calendar net per battery is within 5% (or $0.10 absolute) of the sim's aware per battery for each simulated day (measured: within 3%, or $0.02 on 14 Aug);
  - naive has battery-caused normal events on every built day (measured: 7 to 11).
- **`--rebuild`:** rebuild every day into a temp dir and byte-compare the plain and `.gz` files. That is about 1 minute of CPU inside `check_all.sh --full`'s one lock hold.

### 4.5 l2 acceptance

1. `lockf -k -t 2400 /private/tmp/claude-501/heavy-local.lock nice -n 10 $PY -m sim.history` writes the 4 or 5 days, the calendar and the index.
2. `$PY -m sim.contracts` passes, with the total at or below 25 MB (expected about 21 MB).
3. `sim.verify p1 --days --rebuild` gives `VERIFY p1: PASS` with byte-identical output.
4. `scripts/check_paths.py --lane l2-p1` passes.
5. The existing `sim.verify p1 --rebuild` still passes. 23 Aug's branch files are unchanged; its meta changes only by `split`, `cash`, `story` and the derived relief and marker text.

---

## 5. How Base makes money during peak hours: what to show, and how to label it

Per evening, on the P1 panel (l4 renders; every figure comes from `meta.json`):

1. **Money meter (DERIVED).**
   - A jar or coin icon whose fill climbs with `cash[branch][k]` as the clock plays. It jumps during the plan's discharge minutes, the peak hours, and dips slightly while charging.
   - Hover shows the fleet $ so far and the per-battery value.
   - At 04:00 it settles on `split.net`.
   - Plain mode shows only the icon plus "$9.55 per battery tonight". Numbers mode shows sold, bought and net.
2. **Sold at the peak and bought back overnight (DERIVED).** Two small icons, an up-arrow coin and a down-arrow coin, from `money.split`. 23 Aug, aware:
   - The price-only calendar gives sold $10.57, bought $1.14 and net $9.43 per battery. The build's `money.split` replaces these with the sim's exact figures (aware net $916.56 fleet, or $9.55 per battery).
   - The words: "sold at the evening peak, bought back after the price fell".
3. **"Being feeder-aware earned +$X more than naive tonight" (DERIVED).**
   - This is `−costOfAwareness`, and it is positive on all 8 measured evenings.
   - The reason is honest and belongs in the tooltip: aware charges in turn as prices keep falling; naive charges everything at the onset.
   - It tells Base that **the feeder check costs nothing in money**.
4. **Peak relief (SIM, unpriced).**
   - A shield icon on transformer A, shown only when `relief.minutesOver100 > 0` (23 Aug and 11 Jul 2025).
   - The text reads "kept A under nameplate for 17 min"; `reliefKWh` appears in numbers mode.
   - The tooltip says it is not revenue: "local relief has no sourced price (ASSUMPTION)".
   - `opportunityUpperUSD` is only ever called an upper bound.
5. **Capacity band (DERIVED, per month, not per day).** Keep the existing `systemCapacityPerMonth` line ("~1,889 kW at the peak; $3.12 to $8.50/kW-month") in the detail drawer, never beside the per-day $.
6. **The calendar insight** (in the drawer header, DERIVED, from `calendar.headline`): "Base's energy money comes from a handful of evenings: in 2026 the 10 best evenings earned 55% of it. On 85 evenings one cycle would have lost money." Pair it with the 14 Aug card: "Naive hurts the street even on nights that don't pay."

**Honesty labels:**
- Prices are REAL.
- Battery kW, loadings and events are SIM.
- Every $ is DERIVED, with the cite "REAL LZ_NORTH × SIM battery kW; gross energy value, not Base's P&L".
- The D-26 plan's perfect foresight is an ASSUMPTION (already `discharge_plan`'s cite).
- ERCOT demand figures are REAL (records page or `Native_Load_*.xlsx`).
- "Street load rank" is SIM (SMART-DS 2018).
- Story tags are editorial text with no numbers in them. Numbers in `why` come from data with their label; the l5 bare-digit test pattern applies.

**The benchmark sanity line** (for the More tab or the drawer; do not headline it):
- Energy-only arbitrage came to $329.57 per Core in 2025: one cycle a night, perfect foresight, DERIVED.
- Modo's grid-scale all-revenue benchmark is about $576 per Core-year (DERIVED, research-report line 246).
- Energy-only below all-revenue is the plausible order.

---

## 6. Lead side: l0 (small PR first; everything else depends on it)

1. **`scripts/lanes.json`:**
   - l2-p1 `owns` adds `sim/history.py`, `sim/tests/test_history*.py` and `data/profiles/days/**` (l1 is closed for round 2);
   - l0 keeps `data/ercot/**`.
   - Nothing else changes: `ui/data/p1/**` is already l2's.
2. **2025 prices:**
   - `python -m sim.prices --extract-year 2025 <rtm2025_lz.csv>` writes `data/ercot/lz_north_2025.csv`:
     - it verifies sha `03f00c40…730a`;
     - it keeps LZ_NORTH and **drops the 4 `rep=Y` rows**, the second 01:00 hour of 2 Nov 2025.
   - Add a constant `PRICES_2025_SHA256`.
   - `sim.prices.load()` reads both files. `prices_sha256()` stays the 2026 file's hash, so **no existing artifact changes**.
   - `inputs_sha()` gets `prices_path=`/`loads_path=` overrides; `loads_override` already exists.
   - Update `data/ercot/SOURCE.md`.
3. **`sim/contracts.py`:**
   - check `*.json.gz` by decompressing, then applying the same label and shape rules;
   - count the size on disk;
   - add shape checks for A.5h, A.9 and A.10;
   - add `write_json_gz(path, doc)` = `gzip.compress(bytes, 9, mtime=0)`, so the output is deterministic.
4. **`ui/lib/data.js`:**
   - `parseLink` adds `date` (`/^\d{4}-\d{2}-\d{2}$/`, default `'2026-08-23'`). `linkQuery` emits it **only when it is not the default**.
   - Add `loadP1Days()` → `getOptional('p1/days/index.json')`, and `loadCalendar()` → `getOptional('p1/days/calendar.json')`.
   - Add `loadP1MetaFor(date)`: the default date reads `p1/meta.json` (with its fixture fallback, as today); otherwise `p1/days/<date>/meta.json` with **no fixture fallback**.
   - Add `loadP1BranchFor(date, b)`: the default reads `p1/<b>.json`; otherwise it calls `getGz('p1/days/<date>/<b>.json.gz')`.
   - **`getGz`:** `arrayBuffer()`.
     - If the bytes start with `1f 8b`, it runs `new Response(new Blob([buf]).stream().pipeThrough(new DecompressionStream('gzip'))).json()`.
     - Otherwise it runs `JSON.parse(new TextDecoder().decode(buf))`, because a host that sets `Content-Encoding: gzip` hands back plain JSON.
     - It is cached like `getJSON`.
     - `DecompressionStream` works in Chrome 80+, Safari 16.4+, Firefox 113+ and Node 18+.
   - A date not in the index is a visible notice plus the 23 Aug evening (no silent fallback). It is **not** counted in `data-errors`.
5. **`scripts/deeplinks.txt`** (P1 group) adds:
   - `view=p1&date=2026-07-22&branch=naive&t=23:15`
   - `view=p1&date=2026-08-14&branch=naive&t=19:00`
   - `view=p1&date=2026-08-26&branch=aware&t=22:15`
   - `view=p1&date=2025-07-11&branch=aware&t=21:00`
   - `view=p1&date=2026-08-14&branch=aware_faults`: it must reach `ready` on aware with the "failures: 23 Aug only" notice, not an error.
   - `view=p1&date=2026-01-01`: not simulated, so it shows the notice.
   - `scripts/build_all.sh`: a new heavy target `history` (lockf + nice), plus `sim.verify p1 --days --rebuild` in `check_all.sh --full`.
6. **Optional (cut first):** `data/ercot/ercot_native_load_hourly.csv`, the ERCOT total column only, from the two `Native_Load_*.xlsx` files (REAL, sha-verified). It gives each day's "Texas demand tonight" line and the 22 Jul record rung. It needs `openpyxl`, which is in the system python but **not in the venv**, so either extract once and commit the CSV, or add openpyxl to requirements.
7. `docs/contracts.md`: A.5h, A.6h (A.6 gzipped), A.9 and A.10 from 4.3.

---

## 7. UI side: l4-scene-p1 (placement follows UX-R2-clarity §10; the popover component is l0's `tip.js`)

1. **Day chip (top-left of P1):** a calendar icon, then "Wed 22 Jul 2026 · Texas's record demand ▾", with a REAL dot on the date. Clicking opens the popover:
   - **Simulated evenings:** one row per `index.days`, showing:
     - the date and weekday, and the tag;
     - a 60×14 price sparkline (REAL);
     - the per-battery $ (aware, DERIVED) with a coin icon;
     - two tiny transformer icons: naive's worst in red with its % on hover, and aware's battery-caused count, a green 0.
     - Clicking a row sets `&date=`, **keeps branch, cam, t and speed, and pauses**.
   - **Money calendar strip:** 21 months × about 30 cells, where cell colour is `calendar.net` on a diverging scale.
     - **Losing nights** are a muted cool colour with a small moon icon: "one cycle would lose money: a smart dispatcher sits out".
     - **Spike nights** are the hot colour.
     - **Negative-price evenings** get a tiny "paid to charge" dot (`negMin > 0`).
     - ◆ marks the simulated days.
     - Hover shows the date, the peak price and time, and $ per battery.
     - Clicking ◆ loads that evening. Clicking any other day shows, **inside the popover**, a prices-only card: the 48-interval price curve, the plan's discharge bands, the onset line, sold, bought and net per battery, and "the street was not simulated for this day → nearest simulated evening". It never pretends to have loaded that day.
   - A native `<input type="date" min="2025-01-01" max="2026-09-18">` jumps the strip to a day.
2. **Clock:** the real calendar date, the weekday and "CDT". After 00:00 it shows the **next day's** date ("Thu 23 Jul · 00:15"). The price ticker shows the REAL price of the current 15 minutes, with its plan state (selling, waiting, charging) as an icon.
3. **Money meter** and the sold/bought/aware-extra lines as in section 5, fed from `meta.cash` and `meta.money.split`. Peak relief appears only when `relief.minutesOver100 > 0`.
4. **Branch toggle:** "aware + failures" is disabled on history days, with the tooltip "Failures are scripted for 23 Aug 2026 only". A deep link with `branch=aware_faults` on a history day opens aware with that notice.
5. **Story cues (UX-R2-story §7.6):** they read only meta and the branch doc, so they work per day unchanged. The `spike` cue must key off `relief.minutesOver100 > 0`, not `markers[0]`.
6. **Tests (`ui/test/p1.test.js`):**
   - the date parse and default-omission round trip;
   - the gz loader on a gzipped fixture;
   - the disabled faults branch on a history meta;
   - a non-simulated date showing the notice and never a fixture;
   - a clock rollover past midnight.
7. **Smoke:** the six new `deeplinks.txt` lines, with screenshots of 22 Jul naive 23:15 and 14 Aug naive 19:00 (the fuse night).

**l5 (optional):**
- Two beats: `hist-record` (`view=p1&date=2026-07-22&branch=naive&t=23:15`) and `hist-quiet` (`view=p1&date=2026-08-14&branch=naive&t=19:00`). Captions are templated from `p1/days/<date>/meta.json` with labels.
- A More-tab row, "sold vs bought vs net" per simulated day, from `index.json` (UX-R2-story §7.6).

---

## 8. Size budget (measured)

| Item | Size |
|---|---|
| `ui/data` today (`sim.contracts`) | **16.31 MB** / 25 MB |
| One history day: 3 branches gzipped + plain meta | 0.83 to 0.92 MB + about 33 KB (+about 15 KB `cash`) |
| 4 days (must + should) | about 3.8 MB → **about 20.1 MB** |
| + 16 Sep (could) | about 0.9 MB → **about 21.0 MB** |
| `calendar.json` + `index.json` | about 15 KB + about 10 KB |
| For comparison: one raw 4-branch day | 7.5 to 7.9 MB (it does not fit twice) |

No file comes near the 4 MB per-file cap: the largest gzipped branch file is about 0.35 MB.

---

## 9. Cut order (if behind)

1. Cut 16 Sep.
2. Cut the native-load context line (6.6).
3. Cut the calendar's prices-only day card; ◆ days and colours stay.
4. Cut 11 Jul 2025, which also saves l0's 2025 extract.
5. Cut the strip itself. Keep the day list and the money meter.

**Never cut:**
- the `&date=` link;
- 22 Jul, 26 Aug and 14 Aug;
- the derived relief and marker text (section 3, items 1 and 2), which is a correctness fix.

---

## 10. Decisions RZ should check (also logged in NOTES.md)

1. **The cheap day is 14 Aug (flat, max $34.23), not a negative-price day.** Summer evenings in LZ_NORTH have essentially no negative prices; the negative-price evenings are winter and spring, when nothing on this street is stressed. Negative prices still appear on the calendar. Conservative alternative: simulate 29 Mar 2026 (38 negative intervals in the day, window minimum −$4.59, naive 212.3% and 1 fuse), which is already measured in the evidence folder.
2. **History days drop `aware_faults` (and chaos).** Keeping them needs a re-tuned fault script per day. The script crashes on 26 Aug as written.
3. **The money is shown as the fleet's gross energy value at real prices** (sold − bought), labelled DERIVED and "not Base's P&L", plus an unpriced relief line and the monthly capacity band. The calendar uses perfect foresight on the D-26 plan (an existing ASSUMPTION). It does **not** apply a "sit out losing nights" rule to the P1 sims. The calendar only marks those nights.
4. **gzip for history branch files** through `DecompressionStream` in the page. Alternative: raise `DATA_BUDGET_MB` (an ASSUMPTION constant) to about 50 MB and ship raw JSON. Rejected: it is slower to load, and a budget change is RZ's call.
5. **23 Aug's relief text changes** from "about 15 minutes" to the measured 17 minutes when it becomes derived. Its branch files do not change.
6. **The `reserveBreaches` question** (section 3, item 5): whether islanded backup minutes under an open fuse count as a breach. l2 decides and labels it; this does not block anything.
