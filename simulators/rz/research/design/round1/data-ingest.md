# data-ingest: Round 1 design proposal

Component: **data-ingest**. Siblings: **world-sim**, **orchestrator**, **adversary** (scenario engine + observability), **ui/scenario-studio**. Citation tags: [R] is the report; [E] is `ercot_public_data_apis.md`; [D] is `simulator_public_datasets_and_tools.md`; [P] is `base_power_product_and_system.md`; [G] is `grid_physics_orchestration_and_attacks.md`. **QC** marks numbers I computed during this design from ERCOT files downloaded once with no key; the commands are in the appendix. QC numbers are preliminary, and none describes Base's own fleet.

---

## 1. Pitch

ERCOT publishes enough to replay any day since 2010. But it spreads that data across three channels, several time-labelling conventions and two market designs. data-ingest turns it into one **time-aligned, provenance-stamped stream**. That stream answers one question for any simulated moment: "what could a real controller have known right now?" LIVE and REPLAY share one contract, so the simulator cannot read a price before ERCOT published it.

The same store answers two questions that nobody publishes answers to. Both already have first-pass numbers.

**(A) The recharge rebound.** Every battery in a load-zone ADER sees the same price at the same moment. So when does a price-following fleet recharge, and how loaded is the grid then?
- Summer 2025–2026 QC: a naive rule, "recharge once the price falls below the day's median", starts around **22:45**. Zone load is then still at **0.78–0.84 of its daily peak**.
- Waiting for the cheapest 2 hours lands at **0.67–0.77 of peak** and costs **$9–11/MWh less**. That saving is a perfect-foresight upper bound.
- If it survives at feeder level with a realistic forecast, feeder-aware staggering costs no revenue and may earn some.

**(B) The grid got stiffer.** In ERCOT's own frequency-event workbook (NP12-261-M), the frequency drop per MW lost fell from about **0.21 mHz/MW (2015–2017)** to about **0.08 (2025–2026)**. No measurable event has crossed the 59.85 Hz Fast Frequency Response trigger since **2023-05-01**.
- A 1,000-Core hijack moves Texas frequency less every year.
- It moves a 25 kVA transformer just as much as ever.
- The data pushes both the fleet's value and its risk down to the feeder, which is this project's thesis.

---

## 2. Requirements

**Functional**

| # | Requirement |
|---|---|
| F1 | Adapters for every source in §3.2. Each writes an immutable raw file plus a manifest row: URL, retrieval time, sha256, license. |
| F2 | One canonical schema: UTC epoch-ms **interval start**, `interval_ms`, units, entity IDs, `available_ms`, provenance, market model. |
| F3 | **As-of reads.** `state_at(t)` returns only rows with `available_ms ≤ t`, in both modes. |
| F4 | **LIVE**: poll dashboards no faster than their CDN cache and publish behind a watermark that world-sim's realtime clock must not overtake. |
| F5 | **REPLAY**: serve pre-extracted event windows to world-sim's clock (realtime, lockstep or headless) with identical topics and schemas. |
| F6 | Bulk bundles for world-sim: SMART-DS topology, homes, transformers (SMART-DS and nameplate kVA), 15-min home load, weather, hashes. |
| F7 | Forecast channel for the orchestrator (DAM prices, zone load forecast, weather forecast, home-load forecast) with realistic error and no look-ahead. |
| F8 | A feed-path overlay hook so the adversary can spoof or blank the orchestrator's inputs while truth stays untouched. |
| F9 | Per-channel health and staleness (`age_ms`, last success, active fallback). |
| F10 | Track 1 analysis jobs over the same store, writing `insights/*.json` for the UI. |
| F11 | A recorder for every live poll. By Sunday it holds about 48 h of real 10 s frequency, inertia and PRC, a history ERCOT does not publish [E §4]. |

**Non-functional**

| Concern | Target |
|---|---|
| Freshness (LIVE) | Frequency ≤ 2.5 min behind wall clock (the source already lags 1–2 min [E §10]). PRC/EEA ≤ 70 s. 15-min SPP ≤ 3 min after the interval. Fuel mix and ESR ≤ 11 min. |
| Politeness | ≤ 1 request/s to ercot.com, and no feed polled faster than its `max-age`. ERCOT's terms bar degrading site performance [E §9]. |
| ERCOT Public API (optional) | Token bucket at 25 requests/min (the limit is 30). A ledger refuses a third download of the same doc in 12 months [E §1, §9]. Personal key, used by prefetch only, never at demo time. |
| Other APIs | Overpass: one cached bbox pull, 2 server slots [D §3]. Open-Meteo: ≤ 20 calls, cached; its free tier is non-commercial [D §6]. |
| Offline | `make demo` runs with **no network** from committed extracts. LIVE degrades to "stale" and never crashes. |
| Determinism | Replays are bit-identical given (window, dataset hashes, seed). Rows are never mutated. |
| Licensing | ERCOT raw data may be used in "compilations, charts, and analyses", but never the ERCOT logo [E §9]. CC BY attribution for SMART-DS, EAGLE-I and Open-Meteo; ODbL notice for OSM. |
| Secrets | Keys only from env. Logs record `token_present: true/false`, never values. |

---

## 3. Architecture

### 3.1 Diagram and end-to-end view

```
 SOURCES                      ADAPTERS (write-only)          STORE (immutable)            SERVE (read-only, as-of)
 ERCOT dashboards JSON ─┐     ercot_dash  (60 s)        ─┐   data/raw/**  (gitignored)    ┌─ exo.* topics (truth) ───────► world-sim, ui
 ERCOT MIS list/download┤     ercot_mis   (per report)   │   data/store/<channel>/*.pq    │
 ERCOT annual archives ─┤     ercot_archive (prefetch)   ├─► normalize ─► DuckDB views ──►├─ ctrl.exo.* = truth ⊕ overlays ──► orchestrator
 ERCOT Public API (key) ┤     ercot_api  (optional)      │   manifest.sqlite (hashes,     ├─ bundles (Parquet/GeoJSON) ────► world-sim, ui
 ADER workbooks, FME ───┤     ercot_xlsx                 │    ledger, health)             ├─ exo.health, /sources ─────────► adversary/obs, ui
 Open-Meteo/NWS/NCEI ───┤     weather                    │   data/extracts/** (committed) └─ insights/*.json (Track 1) ────► ui
 SMART-DS S3, OSM, EAGLE-I    smartds, osm, eaglei      ─┘
                                  world-sim's clock (realtime | lockstep | headless) calls state_at(t);
                                  in LIVE, t never passes the ingest watermark (wall − lag)
```

The whole system, seen from the data side:
1. Prefetch fills `data/raw`, and normalization writes the Parquet store. `data/extracts` (committed) holds only what the demo needs.
2. world-sim owns the clock (its proposal says so). It reads exogenous inputs through `state_at(t)` each tick and loads the SMART-DS bundle once, at scenario start.
3. The orchestrator reads only `ctrl.exo.*` and world-sim telemetry, never truth.
4. The adversary registers overlays on `ctrl.exo.*` (price spoof, feed blackout, frozen feed) and watches `exo.health`.
5. The UI shows the real ERCOT ribbon, provenance chips, the credits panel and the Track 1 panel.
6. World-sim and the orchestrator record their outputs (feeder loading, dispatch) with the same `t_ms`, so the analyses can join them to prices.

### 3.2 Adapters (endpoints verified in the research)

| Adapter | Endpoint | Channels | Cadence |
|---|---|---|---|
| `ercot_dash` | `https://www.ercot.com/api/1/services/read/dashboards/` + [E §3]:<br>`ancillary-services.json` (10 s frequency for the last 2 h; AS capacity)<br>`dc-tie-flows.json` (10 s frequency + `currentSystemInertia` since midnight)<br>`daily-prc.json` (EEA level, PRC)<br>`system-wide-prices.json` (15-min RT SPP + DAM, hubs and LZs)<br>`fuel-mix.json` (5 min, incl. Power Storage)<br>`energy-storage-resources.json`<br>`supply-demand.json` (5 min + 6-day forecast)<br>`system-wide-demand.json`<br>`combine-wind-solar.json`<br>`generation-outages.json`<br>`weather-forecast.json`<br>`ancillary-service-capacity-monitor.json` | frequency, inertia, prc, eea, rt/dam_spp, fuel, esr, demand, load_fcst, wind, solar | 60 s. `daily-prc` returns the whole day at 8–10 s, so 60 s is enough; poll every 10 s only while EEA ≥ 1. `dc-tie-flows` (1.3 MB) every 10 min, for backfill. Each response is a trailing window, so no 10 s point is lost. |
| `ercot_rtsc` | `https://www.ercot.com/content/cdr/html/real_time_system_conditions.html` [E §3] | frequency (fallback) | 60 s, only while the JSON feeds fail |
| `ercot_mis` | `https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId=<RTID>`, then `https://www.ercot.com/misdownload/servlets/mirDownload?doclookupId=<DocID>` [E §2].<br>RTIDs:<br>NP6-905-CD 12301 · NP6-788-CD 12300 · NP6-322-CD 13114 · NP6-323-CD 13221<br>NP6-331-CD 24898 · NP6-332-CD 24891 · NP6-970-CD 13073<br>NP4-190-CD 12331 · NP4-188-CD 12329<br>NP6-345-CD 13101 · NP6-346-CD 14836 · NP3-565-CD 14837 · NP6-235-CD 12340<br>NP4-732-CD 13028 · NP4-745-CD 21809<br>NP3-233-CD 13103 · NP6-86-CD 12302 · NP12-261-M 13450 | 5-min LMP, RT AS MCPC, DAM, zonal load, forecasts, events | Poll the listing and download each new DocID once. The MIS keeps only 5–31 days, so our recorder keeps what we need. |
| `ercot_archive` | MIS annual files:<br>NP6-785-ER 13061 (`RTMLZHBSPP_YYYY`)<br>NP4-180-ER 13060<br>NP4-181-ER 13091<br>NP6-792-ER 13231<br>NP6-793-ER 13240<br>Also `https://www.ercot.com/gridinfo/load/load_hist` (`Native_Load_YYYY.zip`) and `https://www.ercot.com/gridinfo/generation` (`IntGenbyFuelYYYY.xlsx`, `FuelMixReport_PreviousYears.zip`) [E §6] | replay prices, pre-RTC+B adders, DAM AS, weather-zone load, fuel mix | prefetch |
| `ercot_xlsx` | ADER monthly report `https://www.ercot.com/files/docs/2025/04/28/ADER_Monthly_Report_202506_202606.xlsx`<br>Limits tracker `https://www.ercot.com/files/docs/2025/05/06/Limits-of-Participation-Tracking_06-01-2026.xlsx`<br>NP12-261-M via MIS 13450 [E §4, §7] | ader, fme_events | prefetch |
| `ercot_api` (ENHANCEMENT) | `https://api.ercot.com/api/public-reports` `/archive/{emilId}` and `/archive/{emilId}/download`. The B2C ROPC token lasts 1 h with no refresh; US only [E §1] | history the MIS no longer holds, e.g. NP6-331-CD and NP6-788-CD for July 2026 | prefetch; re-POST the token at 55 min |
| `weather` | Open-Meteo archive and forecast<br>NWS `api.weather.gov/points/30.2672,-97.7431` → EWX/156,91 (User-Agent required)<br>NCEI `ncei.noaa.gov/access/services/data/v1?dataset=global-hourly&stations=72254013904` (KAUS) [D §6] | temp, GHI, forecast | prefetch windows; NWS hourly in LIVE |
| `smartds` | `oedi-data-lake.s3.amazonaws.com/SMART-DS/v1.0/2018/AUS/P1U/…`: `metrics.csv`, `opendss_no_loadshapes/<sub>/`, `geojson/<feeder>.json`, `load_data/*.parquet`, `profiles/` [D §1, §5] | topology, home load, solar | prefetch |
| `osm`, `eaglei` | Overpass bbox pull (area queries return 406) [D §3]<br>EAGLE-I DOI 10.6084/m9.figshare.24237376.v4 `eaglei_outages_2021.csv`, filtered to FIPS 48453/48491/48209 [D §8] | substations, lines; Uri county outages | prefetch, ENHANCEMENT |

`gridstatus` 0.36.0 [E §8] is a **parser cross-check in tests**, not the main path. It wraps the same undocumented endpoints, so a rename breaks it as well, and we need the raw arrays.

### 3.3 Store

- **Raw.** `data/raw/<source>/<date>/…` holds every response byte for byte. `manifest.sqlite` records `(source_id, url, retrieved_ms, sha256, bytes, license)`. This is the audit trail behind "every source is real and named".
- **Canonical.** Long tables in Parquet, partitioned `channel=/year=/month=`, with DuckDB views on top:

| column | meaning |
|---|---|
| `t_ms` (int64) | UTC epoch ms, **interval start** (the instant for point samples) |
| `interval_ms` | 0 for point samples; 300000, 900000, 3600000, … |
| `channel`, `entity` | e.g. `rt_spp`/`LZ_AEN`, `frequency`/`ERCOT`, `wz_load`/`SCENT`, `temp_c`/`KAUS` |
| `value`, `unit` | `USD/MWh`, `Hz`, `MW`, `degC`, `W/m2`. Inertia's unit is carried as `UNVERIFIED` [E §3]. |
| `available_ms` | When a real-time consumer could first have known the value (§4.2) |
| `source_id` | Key into `sources.yaml` (URL, license, attribution) |
| `prov` | `observed` \| `recorded` \| `derived` \| `modeled` \| `scenario` |
| `market_model` | `pre_rtcb` \| `rtcb` |
| `quality` | `ok` \| `filled` \| `suspect`. Rejected rows go to `rejects/` with a reason. |

- **Single writer.** Only data-ingest writes. Everything else reads through the API or bus, or opens immutable Parquet bundles. This also avoids DuckDB's cross-process writer lock.

### 3.4 Clocks: two modes, one read path

The key decision: **pollers never publish**. They only write to the store, and every consumer reads through `state_at(t)`.
- **REPLAY.** world-sim's clock puts `t` anywhere inside a prefetched window, at any speed or in lockstep.
- **LIVE.** world-sim's realtime clock runs at `t = wall − lag`. `lag` defaults to 150 s so that 10 s frequency, which arrives 1–2 min late [E §10], is already stored. Ingest publishes a per-channel **watermark**, its newest `available_ms`. A channel whose watermark falls behind `t` is held at its last value with a growing `age_ms`. The clock never waits on ERCOT.
- **Instant rewind.** In LIVE, seeking backwards is simply a replay over recorded data: "rewind the last two hours of real Texas frequency", with no extra code.

The contract is identical by construction. Only `prov` (`observed` vs `recorded`) and the `mode` field differ.

---

## 4. Key transformations and analyses

### 4.1 Time normalization (conventions verified in QC)

| Source | Convention (verified) | Rule |
|---|---|---|
| `RTMLZHBSPP_*` annual SPP | `Delivery Hour` 1–24 (hour-ending) × `Delivery Interval` 1–4. **2026-03-08 (spring forward): hour 3 is absent**, leaving 92 intervals. **2025-11-02 (fall back): hour 2 appears twice**; the second copy has `Repeated Hour Flag = Y`, giving 100 intervals. | start_local = date + (hour−1) h + (interval−1)·15 min. The flag resolves the ambiguous hour: N = CDT, Y = CST. Then convert to UTC. |
| `Native_Load_YYYY.xlsx` | A single `Hour Ending` string, e.g. `03/08/2026 24:00`. Spring: `03:00` absent. Fall: `02:00` then `"02:00 DST"`. The same facts, **spelled differently**. | `24:00` means next-day 00:00. The ` DST` suffix marks the repeated hour. Subtract 1 h to get the start. |
| `system-wide-prices.json` | `intervalEnding:"20:00"`; `interval` epoch ms is the **end** | `t_ms = interval − 900000` |
| Dashboard frequency and PRC | Instantaneous `timestamp` with offset, plus `epoch` | `t_ms = epoch`, `interval_ms = 0` |
| `dstFlag` | `"N"` in most feeds, but **integer `0`** in `supply-demand.json` | Coerce both. Treat 5-min points as interval-ending (ASSUMPTION; check against NP6-235-CD). |
| MIS CSVs | `DeliveryDate, DeliveryHour, DeliveryInterval, RepeatedHourFlag` (NP6-331-CD); `…HourEnding…, DSTFlag` (NP4-188-CD) [E §2] | as above |

These DST days become unit tests. The SMART-DS load clock is UNVERIFIED. The test: the median July `cooling_kw` peak must fall between 15:00 and 20:00 local time.

### 4.2 Availability (as-of) rule

`available_ms = interval_end + latency[channel]`. The latencies were measured in [E §10]:
- SCED LMP, lambda, adders: +2 s
- 15-min SPP and RT MCPC: +2 min
- Dashboard frequency: +90 s
- PRC: +10 s
- Fuel mix and ESR: +5 min
- DAM for day D: D−1 12:40 CPT
- Actual zonal load: D+1 05:50
- Frequency-event workbook: weekly

LIVE uses the actual fetch time. REPLAY uses the model above, so a replayed orchestrator cannot buy at a price that was not yet published.

### 4.3 Market model and channel availability

`market_model = rtcb` for `t ≥ 2025-12-05 00:00 CPT` [E §2].

| Channel | Pre-RTC+B replays (Uri 2021, Sep 2023) | RTC+B (2026 windows, LIVE) |
|---|---|---|
| RT energy price | NP6-785-ER SPP, which already includes the ORDC adder | same file, dashboard, NP6-905-CD |
| Scarcity component | NP6-792-ER / 793-ER adders (decomposition panel) | not on energy; it sits in AS prices |
| RT AS price | **did not exist**; channel absent | NP6-331-CD / 332-CD (MIS 7 days; older history via `ercot_api`) |
| DAM AS | NP4-181-ER; **no ECRS before June 2023** [G §3] | NP4-181-ER / NP4-188-CD |
| RT offer cap | pre-RTC+B values not in the research (UNVERIFIED) | $2,000 RT, $5,000 DA [R] |
| Frequency | no public history; **world-sim models it** with era-specific sensitivity (§4.6 B) and Uri's 59.302 Hz nadir [R] | observed or recorded |

### 4.4 Derived series

- **Net load** = demand − wind − solar. In LIVE it is 5-minute (`supply-demand` + `fuel-mix`). In replays it is hourly (`Native_Load` − `IntGenbyFuel`); the resolution of `IntGenbyFuel` is UNVERIFIED [E §6].
- **Weather per home cluster.** ERA5's roughly 25 km cell covers the whole P1U map [D §6]. Every cluster gets the same series, from Open-Meteo, with NCEI KAUS as station truth. We do not invent spatial variation.
- **Home-load re-weathering** (ASSUMPTION method; SMART-DS covers only 2016–2018 [D §5]):
  ```
  per home: fit cooling_kw ≈ a + b·max(0, T − 65°F); heating_kw likewise on max(0, 50°F − T)  (2018 profile × 2018 Open-Meteo)
  target day d: take the 2018 analog day (same month and weekday type, nearest mean T);
     load(d,t) = analog total_kw(t) + b·(T_d(t) − T_analog(t))⁺ + heating term;  prov = derived
  Uri (4.5 °F) extrapolates beyond 2018's range → quality = suspect, shown as a band
  ```
- **Home-load forecast.** Error drawn, seeded, from ERCOT's **real** forecast error: `currentLoadForecast` vs `systemLoad` in `system-wide-demand.json`, and NP3-565-CD vs NP6-345-CD.
- **Topology bundle.** From the SMART-DS OpenDSS and GeoJSON files: homes, transformers carrying `kva_smartds` (27.5/55/82.5) **and** `kva_nameplate` (25/50/75) [D §9], and feeders from `metrics.csv`. The price node is a config value: `LZ_AEN` (honest Austin Energy stand-in), or `LZ_NORTH`/`LZ_SOUTH` (Oncor-suburb stand-in; which applies is UNVERIFIED [R]).

### 4.5 Replay windows (pre-extracted and committed)

| Window | Dates (CPT) | Contents |
|---|---|---|
| `peak_2026_07_22` | 07-21 → 07-23 | RT SPP (2026 archive), DAM SPP/AS, Native_Load, weather. RT AS and 5-min LMP only if `ercot_api` runs. |
| `uri_2021` | 02-10 → 02-22 | RT SPP (DocID 814922832 [E §6]), DAM, adders, Native_Load, Open-Meteo + NCEI, EAGLE-I filtered |
| `eea2_2023_09_06` | 09-05 → 09-07 | 2023 archives; frequency modelled (≈59.77 Hz, partly UNVERIFIED [E §4]) |
| `heat_aug_2023` | 08-01 → 08-31 | re-weathering calibration (106.9 °F peak [D §6]) |
| `lz_prices_2025_2026` | 2025-01-01 → 2026-09-19 | all LZ and hub RT SPP for Track 1 (QC: 35,040 + 25,148 intervals) |
| `recorded_hackathon` | the event weekend | everything the LIVE recorder captured |

### 4.6 Track 1: what the data shows that most people miss

#### Insight A (primary): the recharge rebound

**Question.** When the load-zone price tells a whole zone's fleet to recharge, how loaded are the feeders, and what would waiting cost?

**Datasets**
- NP6-785-ER RT SPP 2025–2026
- NP4-180-ER DAM SPP (a policy with no hindsight)
- `Native_Load_2025/2026` by weather zone
- SMART-DS P1U residential `load_data`, re-weathered
- de-rated SMART-DS transformers
- world-sim's recorded feeder loading (final version)

Zone mapping, all ASSUMPTIONS [E §5]: LZ_HOUSTON→COAST, LZ_NORTH→NCENT, LZ_AEN→SCENT, LZ_SOUTH→SOUTH.

**Method**
```
for zone z, day d:
  D = most expensive 8 consecutive 15-min intervals (the 2-h discharge block)
  NAIVE_RT  : recharge at first interval after D with RT price ≤ median(price_d)   # reactive; whole zone in sync
  DAM_SCHED : cheapest 2 h of D−1's DAM curve after D                            # scheduled; still in sync
  ORACLE    : cheapest 2 h of RT price from end of D to next-day 12:00            # upper bound on savings
  STAGGERED : DAM_SCHED spread over the cheap window within transformer headroom  # orchestrator's policy
  record onset time, zone and feeder load as a fraction of daily peak, $/MWh paid,
         and (with world-sim) peak transformer loading at N Cores per 25 kVA transformer
hosting(policy) = Cores per feeder before the first transformer >100% or bus <0.95 pu
```

**Charts**
1. **Rebound clock.** Hour of day (CPT) against the residential feeder load band (summer median and interquartile range). Bars show the share of days each policy starts recharging in each 15-minute slot.
2. **Patience pays.** One dot per zone-day. x = load reduction from waiting; y = $/MWh saved.
3. **Headline curve.** Share of summer days with a transformer overload against Cores per transformer, one line per policy, each labelled with the dollars it gave up or gained.

**QC: summer (Jun–Aug), zone level, NAIVE_RT vs ORACLE.** Days are kept only where the price fell below the median before midnight and the load data was complete.

| Zone / weather zone | Year | Days | Naive onset (median) | Load at onset, naive vs oracle (share of daily peak) | Naive onset at ≥ 90% peak (baseline: share of all hours) | 2-h charge price, naive vs oracle |
|---|---|---|---|---|---|---|
| LZ_HOUSTON / COAST | 2026 | 57 | 22:45 | 0.81 vs 0.70 | 18% (37%) | $28.03 vs $18.99 |
| LZ_NORTH / NCENT | 2026 | 37 | 22:45 | 0.78 vs 0.67 | 11% (33%) | $26.46 vs $16.89 |
| LZ_AEN / SCENT | 2026 | 44 | 22:45 | 0.82 vs 0.69 | 25% (34%) | $28.53 vs $17.89 |
| LZ_SOUTH / SOUTH | 2026 | 41 | 21:15 | 0.82 vs 0.77 | 24% (41%) | $29.26 vs $18.01 |
| LZ_HOUSTON / COAST | 2025 | 64 | 22:45 | 0.82 vs 0.75 | 20% (37%) | $28.31 vs $17.80 |
| LZ_NORTH / NCENT | 2025 | 54 | 22:45 | 0.79 vs 0.68 | 9% (33%) | $25.91 vs $16.00 |
| LZ_AEN / SCENT | 2025 | 52 | 22:45 | 0.82 vs 0.69 | 19% (34%) | $29.61 vs $18.16 |
| LZ_SOUTH / SOUTH | 2025 | 54 | 22:45 | 0.84 vs 0.72 | 26% (39%) | $28.51 vs $18.13 |

What the QC already shows:
- The 2-hour discharge block starts between 18:00 and 20:59 on 59–71 of 92 summer days, in every zone and year.
- Naive recharge follows 1–2 hours later, at about 80% of peak zone load.
- Waiting is 32–39% cheaper.
- At **zone** level, naive onset hits ≥ 90% of peak *less* often than a random hour does. The strong claim, "recharge lands on the peak", is **refuted at zone level**.

The analysis therefore has to move to the **feeder** level, where residential evening load dominates. That is why it is coupled to world-sim.

**Supporting QC: zones are not one statewide signal.** Across LZ_HOUSTON, NORTH, SOUTH and AEN:

| Measure | 2026 | 2025 |
|---|---|---|
| Median spread between zones per 15-minute interval | $4.16/MWh | $4.37/MWh |
| Intervals where all four zones are within $1 | 29.3% | 23.1% |
| Days the cheapest 2 h starts in the same interval in all four zones | 13.8% | 21.7% |
| Days the cheapest 2 h starts within 1 h across all four zones | 32.6% | 50.3% |

So synchronization is **intra-zone**, which is exactly the one-ADER-per-load-zone structure [R]. There is a side surprise too. In 2026, LZ_HOUSTON's cheapest 2 hours started between 07:00 and 09:59 on 124 of 261 days (48%), not at midday.

**What would be surprising and useful.** Two outcomes would change how Base thinks about this:
- DAM_SCHED or STAGGERED keeps most of ORACLE's saving *and* raises hosting capacity. Then feeder awareness is revenue-neutral or better, and not a cost of market position.
- NAIVE_RT overloads a de-rated 25 kVA transformer on many summer evenings at today's 1–2% annual penetration. Then the risk is present, not future.

#### Insight B (computed): the grid got about 2.6× stiffer per MW

**Source.** NP12-261-M, `ERCOT_FrequencyMeasurableEvents_AsOf_08182026.xlsx` (DocID 1263831744). Year sheets 2015–2026; the `Logs` sheet is excluded.

**Measure.** Sensitivity = (pre-perturbation average − minimum frequency) / MW lost. Nadirs are also counted against the 59.85 Hz FFR trigger [R].

| Year | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Events | 25 | 30 | 29 | 26 | 23 | 18 | 18 | 14 | 5 | 6 | 6 | 3 |
| Median mHz/MW | 0.215 | 0.209 | 0.212 | 0.192 | 0.203 | 0.209 | 0.196 | 0.172 | 0.143 | 0.154 | 0.086 | 0.081 |
| Lowest nadir (Hz) | 59.724 | 59.731 | 59.738 | 59.803 | 59.774 | 59.745 | 59.770 | 59.792 | 59.847 | 59.900 | 59.900 | 59.948 |
| Nadirs < 59.85 Hz | 8 | 9 | 6 | 5 | 4 | 7 | 6 | 4 | 1 | 0 | 0 | 0 |

The last event below the trigger was **2023-05-01 13:32**: 59.847 Hz after 851 MW lost.

ERCOT's own frequency on 2026-09-25 agrees. Of 7,251 ten-second samples between 00:00 and 20:08 CDT (range 59.966–60.022 Hz), **none** left the IEEE 1547 default deadband of ±0.036 Hz [R], and 21.9% left ±0.017 Hz.

**Caveats**
- The sheet title changes from BAL-001-TRE-1 to **BAL-001-TRE-2 in 2022**, so the event-selection criteria may have changed. Within the TRE-2 years alone the median still falls from 0.172 to 0.081.
- Recent years have few events.
- The measure is crude, and the relationship is correlation only. Batteries supplying 51% of RRS in 2025 is a plausible driver [G §3].
- Uri is not in the workbook [E §4].

**Why it matters**
- A 40 MW swing from 1,000 Cores moves frequency about **3.2 mHz** at 2026 sensitivity, against about **8.6 mHz** at 2015's (DERIVED, linear; world-sim notes that linear estimates are a lower bound for small steps).
- Replays need **era-specific calibration**: 2021 sensitivity (0.196) is about 2.4× that of 2026.

**Chart.** Per-event mHz/MW against date, with the yearly median, annotations at ECRS launch (June 2023) and RTC+B (2025-12-05), and sub-59.85 Hz events marked.

#### Insight C (ENHANCEMENT): ADER fingerprints

The June 2026 hourly sheet of the ADER monthly report (QC) shows two archetypes:
- **Energy-active.** MIDNT_ALD1, OB_ALD1 and SANSM_ALD1 were "Dispatched" in 94–100% of online SCED intervals. Median "Avg. Online Bid" was **$4,532–4,897/MWh**, and mean LMP while dispatched **$30.81–33.57**. They carried ECRS in 53–55% of intervals and Non-Spin in 33–35%.
- **Reserve-parked.** AR_ALD1 and WEBBS_ALD1 were online 100% of the time and never dispatched. They carried Non-Spin in about 91% of intervals, with $300 bids.

The field semantics are **UNVERIFIED**; see question 2 in §10. We do not attribute resources to any QSE [E §7]. Once decoded, this is the only public hour-by-hour ground truth for the orchestrator's "fleet as one resource" duty cycle. Chart: an hour × resource heatmap of the share of intervals dispatched.

---

## 5. Interfaces and contracts

Conventions match world-sim's and the orchestrator's `*_ms` fields:
- Timestamps are **UTC epoch ms, interval start**.
- Units: MW (system), kW (device), USD/MWh.
- Every value carries `prov`; live values also carry `age_ms`.

**`exo.ercot.system`**: every 10 s of sim time.
```json
{"t_ms":1790384900000,"mode":"live","lag_ms":150000,"market_model":"rtcb",
 "f_hz":{"v":59.986,"prov":"observed","src":"ercot.dash.dc-tie-flows","age_ms":0},
 "inertia":{"v":332906,"unit":"UNVERIFIED","prov":"observed","age_ms":0},
 "prc_mw":{"v":10285,"prov":"observed","age_ms":8000},"eea_level":0,"grid_state":"normal",
 "reg_up_avail_mw":{"v":null},"rrs_mw":{"v":null}}
```
The values are real: frequency and inertia at 20:08:20 CDT on 2026-09-25, and PRC at 20:08:12, from feeds fetched at 01:13Z. `age_ms` follows from those times. In replays with no frequency history, `f_hz.prov` is `"modeled"` and world-sim supplies the value.

**`exo.ercot.price`**: one message per newly available interval (15-min SPP; 5-min LMP when present).
```json
{"t_ms":1790383500000,"interval_ms":900000,"kind":"rt_spp","available_ms":1790384520000,
 "unit":"USD/MWh","market_model":"rtcb","prov":"observed","src":"ercot.dash.system-wide-prices",
 "p":{"LZ_AEN":46.84,"LZ_HOUSTON":46.29,"LZ_NORTH":45.72,"LZ_SOUTH":46.95,"HB_HUBAVG":47.04}}
```
`kind` is one of `rt_spp`, `rt_lmp`, `dam_spp` or `rtd_indicative`. **`exo.ercot.as`** uses the same envelope with `"p":{"REGUP","REGDN","RRS","ECRS":0.29,"NSPIN":1.15}` [E §2]. It is **absent** before RTC+B.

**Other topics**

| Topic | Cadence | Fields |
|---|---|---|
| `exo.ercot.load` | 5 min LIVE / hourly replay | `t_ms, interval_ms, demand_mw, capacity_mw, wind_mw, solar_mw, esr_net_mw, net_load_mw, wz_load_mw{SCENT,COAST,NCENT,SOUTH}, prov` |
| `exo.weather` | hourly, interpolated on request | `t_ms, cluster_id, temp_f, temp_c, ghi_wm2, prov, src` (the fields world-sim asked for) |
| `exo.forecast` | when published | `issued_ms, kind(dam_spp\|load_fcst\|weather_fcst\|home_load_fcst), entity, horizon[{t_ms,v}], error_model, seed` |
| `exo.health` | 10 s wall | `channel, active_source, last_ok_ms, age_ms, watermark_ms, status(ok\|stale\|fallback\|down), reason` |
| `ctrl.exo.*` | as above | The orchestrator's view: truth unless an overlay is active |

**Overlay hook (adversary).**
```json
POST /ingest/overlay {"id":"inj-17","topic":"exo.ercot.price","entity":"LZ_HOUSTON",
  "op":"scale|set|hold_last|drop|delay","value":20,"from_ms":…,"to_ms":…,"label":"price_spoof"}
```
The event log tags overlaid values `prov:"scenario"` for scoring. `ctrl.exo` does not tag them, or the spoof would be obvious.

**Bulk bundles.** Parquet or GeoJSON files, with their sha256 in `bundle_manifest.json`:

| File | Key columns |
|---|---|
| `homes.parquet` | `home_id, bus, lon, lat, xfmr_id, feeder_id, substation_id, load_profile_id, price_node, cluster_id` |
| `transformers.parquet` | `xfmr_id, bus, lon, lat, feeder_id, phases, kva_smartds, kva_nameplate` |
| `feeders.parquet` | `feeder_id, substation_id, customers, peak_mw_planning, kv_nominal` |
| `home_load.parquet` | `t_ms, home_id, total_kw, cooling_kw, heating_kw, prov` (15 min) |
| `fme_events.parquet` | `event_id, t_ms, f_pre_hz, f_post_hz, f_nadir_hz, mw_loss, standard` (the calibration rows world-sim asked for) |
| `lines.geojson`, `osm_substations.geojson` | map layers; the OSM file carries an ODbL notice |

**HTTP endpoints**
- `GET /state?t_ms=&channels=`
- `GET /series?channel=&entity=&from_ms=&to_ms=&as_of_ms=`
- `GET /windows`
- `GET /sources` (feeds the UI credits panel)
- `GET /insights/{a|b|c}`

**Transport.** data-ingest needs only a `publish(topic, msg)` hook plus an in-process client. The bus itself follows whatever world-sim and the ui gateway choose. Headless hosting-capacity sweeps should read with bulk `series()` calls instead of subscribing.

---

## 6. Failure handling

| Failure | Detection | Response |
|---|---|---|
| Dashboard renamed, 404, or a 302 alias (it has happened before [E §3]) | HTTP status or schema validation | Follow redirects, then fall back per channel and emit `status=fallback`.<br>**Frequency**: `ancillary-services` → `dc-tie-flows` → RTSC HTML → recorded → modelled.<br>**Prices**: dashboard → MIS NP6-905-CD → API → hold.<br>**PRC/EEA**: `daily-prc` → hold, with a banner. |
| Schema drift (moved field, type change) | A pydantic model per feed | The row goes to `rejects/` with a reason. Never guess silently. |
| Rate limit (429) or slow responses | Status code, latency | Exponential backoff with jitter; the per-host bucket halves its rate. Overpass is never looped; use the cache. |
| API token expiry (1 h, no refresh) | 55-minute timer, or a 401 | Re-POST for a new token. Credentials come only from env and are never logged. |
| Duplicate API download | Ledger shows ≥ 2 downloads in 12 months | Refuse and serve the cached file. |
| Venue Wi-Fi loss | All channels stale beyond their TTL (frequency 5 min, prices 20 min) | Hold last values while `age_ms` grows. The UI shows "LIVE feed stale", and one click switches to the recorded replay. The demo default is REPLAY from committed extracts, so the video never depends on Wi-Fi. |
| Bad values | f outside [59, 61] Hz; PRC < 0. Prices get **no** hard bound, because LMPs can legitimately exceed the $2,000 offer cap [G §3] | Keep the row, flagged `suspect`; RT prices above $2,000 are flagged. |
| Gaps and DST | Expected-interval generator (92 / 96 / 100 intervals per day) | Fill by hold only (`filled`). Never interpolate prices. |
| Dashboard and MIS disagree | SPP differs by more than $0.01 for the same interval | Prefer MIS and log the difference. Price corrections (NP4-196-M / NP4-197-M [E §10]) are out of scope. |
| Slow xlsx parsing | QC: openpyxl read-only took **14.7 s** (2026 archive, 16 MB) and **17.8 s** (2025 archive, 22.5 MB) | Parse once in prefetch and serve Parquet. |

---

## 7. Stack

| | **A: Python + Parquet + DuckDB** (recommended) | **B: Postgres + TimescaleDB** |
|---|---|---|
| Venue setup | `uv sync`; no server | Docker, migrations, and a server that can die mid-demo |
| Offline and committed extracts | Parquet files go straight into git (a few MB) | Dump and restore scripts |
| Concurrency | One writer; readers via the API or immutable files | Multi-writer, which we do not need |
| Siblings | world-sim and the ui gateway both proposed Python | Adds a second runtime |

**Recommendation: A.**
- Python 3.12 pinned with uv (gridstatus needs Python < 3.15 [E §8]).
- Libraries: `httpx`, `pydantic`, `openpyxl` (measured above), `pyarrow`/`polars`, `duckdb`, `fastapi`.
- The volumes are small. The 2025 extract of 9 load-zone and hub price points is 315,360 rows (QC), and one day of 10 s frequency is 8,640 points. DuckDB should handle these sizes in under a second, but that has not been measured, so measure it before promising it.
- Spend the 48-hour risk budget on getting time and availability right, not on a database.

---

## 8. Build order (by dependency; staffing and schedule are the team's call)

| # | Item | Needs | Class |
|---|---|---|---|
| 1 | `sources.yaml`, `ATTRIBUTION.md`, data layout, `.env` handling | — | ESSENTIAL |
| 2 | Canonical schema, time module, DST tests (the §4.1 days), as-of rule | 1 | ESSENTIAL |
| 3 | §5 contracts agreed with world-sim, the orchestrator and the ui | 2 | ESSENTIAL |
| 4 | Prefetch: RTM SPP annual files, Native_Load, and the `peak_2026_07_22` extract | 2 | ESSENTIAL |
| 5 | SMART-DS bundle for one ~1,000-customer feeder (e.g. `p1uhs19_1247--p1udt17263`, 1,012 customers [D §1]), both kVA columns, with hashes | 1 | ESSENTIAL |
| 6 | `state_at` / `series` service, plus replay serving for world-sim's clock | 3, 4 | ESSENTIAL |
| 7 | Provenance fields and `/sources` for the UI credits panel | 6 | ESSENTIAL |
| 8 | LIVE recorder and pollers. Start early: recording only works going forward. | 2 | ENHANCEMENT |
| 9 | Watermark LIVE mode, instant rewind, fallback chains, `exo.health` | 6, 8 | ENHANCEMENT |
| 10 | Uri and Sep 2023 windows, pre-RTC+B adders, DAM and AS prices | 4 | ENHANCEMENT |
| 11 | Weather windows, re-weathering, home-load forecast | 5 | ENHANCEMENT |
| 12 | `ctrl.exo` overlay hook | 6 | ENHANCEMENT |
| 13 | Insight B (already computed): chart and JSON | 2 | ENHANCEMENT (needed for Track 1) |
| 14 | Insight A at zone level, adding DAM_SCHED | 4, 10 | ENHANCEMENT (needed for Track 1) |
| 15 | Insight A at feeder level, joined to world-sim's recorded loading | 14, world-sim | ENHANCEMENT (the Track 1 headline) |
| 16 | Insight C, OSM layer, EAGLE-I, `ercot_api` pulls | 1 | ENHANCEMENT |

---

## 9. How this angle scores

| Rubric line | Contribution |
|---|---|
| Completeness (15) | The demo runs offline from committed extracts. LIVE loss degrades rather than crashes. DST, gap and schema tests. |
| Technical depth (15) | An availability-aware as-of store; LIVE and REPLAY identical by construction; per-channel fallback chains; two market designs handled explicitly; raw EMIL files parsed, not an API wrapper. |
| Track fit: problem (15) | **Track 1**: two findings from ERCOT's own files. B is computed; A answers the Base engineer's question. **Track 2**: the feed is itself a failing dependency (stale, spoofed, down) that the orchestrator must survive. |
| Track fit: why (15) | ERCOT dispatches by load zone and does not enforce distribution limits [R]. A shows the timing consequence of that. B shows that system frequency is the wrong place to look for fleet risk. |
| Insight quality (10) | A decade-long trend nobody quotes: sensitivity down about 60%, and no event below the FFR trigger since May 2023. A naive hypothesis honestly refuted at zone level and replaced by a sharper feeder-level one. |
| Usability (10) | Base analysts could use `/series` and the Parquet extracts tomorrow. The per-zone-day rebound metric could run on their own dispatch logs. |
| Creativity (10) | ERCOT prices, the frequency-event workbook, NREL feeders and weather, joined in one place. Plus a self-recorded 48 h of 10 s frequency that exists nowhere publicly. |
| Performance (10) | Each file is parsed once into Parquet. Polling at the cache interval still recovers full 10 s resolution. |

---

## 10. Risks, unknowns, and questions for Base engineers

**Risks and unknowns**
- **Dashboard renames mid-event** [E §3]. Mitigated by fallback chains and the committed extracts.
- **Insight A's zone-level proxy.** It uses weather-zone load, not residential feeder load, and the LZ-to-weather-zone mapping is an ASSUMPTION. Only the feeder-level version answers the Base engineer, and that version depends on world-sim and on SMART-DS profiles built on 2018 weather.
- **Insight B's causal limits.** The standard changed in 2022 and recent years have few events, so we present a trend with caveats, not a cause.
- **Frequency in replays.** Every replay's frequency is modelled, because no public history exists before our own recording. It must be labelled as such.
- **SMART-DS time convention** is unknown; the §4.1 test checks it.
- **Weather licensing.** Open-Meteo's free tier is non-commercial [D §6]. Prefer NCEI (public domain) for committed weather and use Open-Meteo only for gaps, with attribution.
- **API-only history.** RT AS prices and 5-min LMP for July 2026 need someone's personal API key. Registering is the team's call. Without it, the July replay uses 15-min SPP and DAM AS only.

**Questions for Base engineers on site**
1. After an evening discharge block, how does the fleet recharge: SCED base points, a DAM schedule, or a local rule? Is there a stagger or random delay? Would a per-zone "rebound risk" score help the Markets desk?
2. In ERCOT's ADER workbook, what do "Dispatched" and "Avg. Online Bid" mean for an ADER? Is a bid around $4,700 a "keep consuming unless scarce" bid?
3. Which ERCOT signals feed your dispatch model: RTD indicative LMPs (NP6-970-CD), DAM, PRC, weather? Do you use the dashboard feeds at all, or only ICCP and MIS?
4. Do you see the per-MW frequency-sensitivity decline in your own data? Does the fleet respond to frequency at all, given that ADER offers no Regulation and PFR is optional [P §5]?
5. Which load zone do Oncor Austin-suburb members settle in? That decides whether our feeder is priced at LZ_NORTH or LZ_SOUTH.
6. Do TDSPs give you feeder IDs or transformer maps, so the rebound metric could run on real topology?
7. How do you normalize ERCOT's DST days and interval-ending labels internally?

---

## 11. What I need the other designers to get right

- **world-sim**
  - Own the clock, but never let the realtime clock pass the ingest watermark.
  - Treat `prov:"modeled"` frequency as yours in replays, with **era-specific sensitivity** (§4.6 B). The 2026-08-07 fit is right for 2026 and about 2.4× too stiff for Uri.
  - Record per-step feeder and transformer loading and voltages so Insight A can join them.
  - Say explicitly whether a run uses `kva_smartds` or `kva_nameplate`.
- **orchestrator**
  - Read only `ctrl.exo.*`.
  - Honour `available_ms` and `age_ms`; no look-ahead.
  - Handle absent channels: no RT AS before 2025-12-05, no ECRS before June 2023, no 5-min LMP in replays without the API pull.
  - Record every dispatch with its `t_ms`.
- **adversary / observability**
  - Inject feed attacks only through `POST /ingest/overlay`, never by mutating the store.
  - Use `exo.health` for "ERCOT feed goes dark".
  - Score against overlay labels.
- **ui / scenario-studio**
  - Show a provenance chip on every exogenous number, the LIVE lag, and a credits panel from `/sources`.
  - Use no ERCOT logo [E §9].
  - The natural-language creator must compile to a named window, overlays and injections, and never invent "real" data.
  - Plan an offline basemap fallback [D §10].
  - Build the three §4.6 charts.

---

## Appendix: QC provenance

Each file was downloaded once, with no key, on 2026-09-26 between about 01:13 and 01:20 UTC. The DocIDs come from the MIS listings for `reportTypeId=13061` and `13450`, fetched at the same time.

```
curl -o rtm2026.zip "https://www.ercot.com/misdownload/servlets/mirDownload?doclookupId=1276781176"  # RTMLZHBSPP_2026, data to 2026-09-19
curl -o rtm2025.zip "https://www.ercot.com/misdownload/servlets/mirDownload?doclookupId=1177737535"  # RTMLZHBSPP_2025
curl -o fme.zip     "https://www.ercot.com/misdownload/servlets/mirDownload?doclookupId=1263831744"  # NP12-261-M AsOf 08182026
curl -O https://www.ercot.com/files/docs/2026/02/10/Native_Load_2026.zip   # hourly by weather zone, to 2026-08-31
curl -O https://www.ercot.com/files/docs/2025/02/11/Native_Load_2025.zip
curl -O https://www.ercot.com/files/docs/2025/04/28/ADER_Monthly_Report_202506_202606.xlsx
curl -O https://www.ercot.com/api/1/services/read/dashboards/{dc-tie-flows,system-wide-prices,daily-prc,energy-storage-resources,supply-demand}.json
```

**Method.** Python 3.14 standard library plus openpyxl in read-only mode:
1. Extract the load-zone and hub rows.
2. Map each row to its interval start. For this QC only, rows flagged `Repeated Hour Flag = Y` were dropped; the ingest code resolves them properly.
3. Join each load zone to its weather zone by hour-beginning.

**Scripts.** `extract_rtm.py`, `a1_zones.py`, `a3_rebound.py` and `a4_flip.py` are in `/private/tmp/claude-501/-Users-rzalagbada-Desktop-projects-REDACTED/db7213a8-6bab-44d3-b22b-9fe4a11f46ca/scratchpad/bp-data-ingest/`. That folder is ephemeral and a reboot empties it; the method above is enough to rebuild them. The FME and ADER numbers came from inline scripts run over the same files.
