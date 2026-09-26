# freq: Frequency and its trend (ERCOT, Fri 25 Sep 2026)

Item `freq` of the EMS data list. Data file: `site/ems/freq-series.json` (110 KB). Build script: `site/ems/freq-build.py`, which reruns offline from the saved raw files. Raw fetches are in `evidence/live-20260925/freq-*`.

Status tags: **REAL** means public ERCOT data (endpoint and retrieval time given). **DERIVED** means our arithmetic on REAL data (formula given). **ASSUMPTION** means an input we chose. **SIM**: this item has none. The OpenDSS prototype is a static power flow at a fixed 60 Hz, so it has no frequency, inertia or PRC.

---

## 1. JSON shape (`freq-series.json`)

```
{
  item: "freq", title, status_legend,
  provenance: { dc_tie_flows|daily_prc|ancillary_services|rtsc: {url, retrieved_utc, lastUpdated, raw, status} },
  constants: { f0_hz, design_trip_mw, critical_inertia_mws, lowest_10y_inertia_mws, ufls_hz[5], ffr_trigger_hz,
               lr_rrs_relay_hz, governor_deadband_hz, eea_clock_minute_freq_hz, eea3_steady_state_hz,
               prc_thresholds_mw{watch,eea1,eea2,eea3,offline_nsrs_deploy,vecl_nprr1238_pending},
               time_error_correction_trigger_s },
  sources: { <fact>: "url (section)" },
  stats: {
    frequency:  {n, mean_hz, sigma_mhz, min_hz, min_time_cdt, max_hz, max_time_cdt, pct_samples_outside_deadband_017,
                 clock_minutes_avg_below_59_91, clock_minute_avg_min_hz, clock_minute_avg_max_hz, largest_abs_excursion{...}},
    rocof_10s:  {method, max_fall_hz_per_s, max_fall_time_cdt, max_rise_*, p50/p99/p999_abs_hz_per_s, top5_falls[],
                 ten_s_falls_ge_15mhz_count, step_0336_understatement{...}, why_10s_understates[]},
    time_error: {formula, rtsc_anchor_1{as_of_cdt, epoch, time_error_s, frequency_hz, inertia_mws}, rtsc_anchor_2{...},
                 validation{observed_change_s, integrated_change_s, error_s}, implied_te_at_midnight_s, min_s, max_s, ...},
    inertia:    {unit, min_gws, min_time_cdt, max_gws, max_time_cdt, mean_gws, ratio_min_to_critical, ...},
    trip_2750mw:{formula, at_day_min_inertia{inertia_gws, initial_rocof_hz_per_s, no_response_s_from_60_to_59_85,
                 no_response_s_from_59_7_to_59_3}, at_day_max_inertia{...}, at_critical_100gws{...},
                 at_10yr_low_115gws{...}, sensitivity_minus_12gws_lost_with_tripped_units{...}, variant_2800mw{...}},
    prc:        {min_mw, min_time_cdt, max_mw, max_time_cdt, mean_mw, margin_to_watch_at_min_mw, samples_below_3000,
                 current_condition{eea_level, state, prc_value, ...}, thresholds_mw{...}},
    data_quality: {dc_tie_flows{points, step_s_counts, inertia_median_update_s, longest_identical_freq_run},
                   cross_check_ancillary_services{overlap_points, mismatches}, cross_check_cached_1925{...}, daily_prc{...}},
    as_capacity_monitor_last: {lastRrs, lastEcrs, lastNsrs, lastDeployedRegUp, ..., asOf},
    fleet_scale: {ader_mw_base_reported, settling_shift_mhz_range[2], formula, compare_day_sigma_mhz}
  },
  events: [ {id:"step_0336", time_cdt, kind, evidence[], pre_avg_hz, post_avg_20_52s_hz, lowest_10s_sample_hz,
             inertia_change_mws, mw_loss_estimate_derived{low,mid,high,formula}, verify},
            {id:"sag_1415", time_cdt, kind, evidence[], min_hz} ],
  reference_trips_fme: {source, status, formulas, events[{id,t0,pre_hz,post_hz,nadir_hz,mw_loss,beta_mw_per_0p1hz,
                        nadir_mhz_per_mw,nadir_below_post_mhz}], beta_min, beta_median, beta_max, ...},
  design_trip_wedge: {status, formula, lines{today_min|today_max|lowest_10y_115gws|critical_100gws:
                      {inertia_gws, rocof_hz_per_s, t_s[7], f_hz[7]}}, reference_hz{ffr_trigger, lr_rrs_relay, ufls_stage1}},
  hourly: {hour_cdt[24], f_sigma_mhz[24], f_min_hz[24], prc_mean_mw[24], prc_min_mw[24], inertia_min_gws[24],
           corr_f_sigma_vs_prc_mean, corr_f_sigma_vs_inertia_min, status},
  series_1min: { t0_epoch_ms, t0_cdt:"2026-09-25 00:00 CDT", step_s:60, n:1382,      // 00:00 to 23:01 CDT
                 f_mean_hz[], f_min_hz[], f_max_hz[],            // REAL 10-s samples aggregated per clock minute (6 each)
                 rocof10_extreme_hz_per_s[],                     // DERIVED: signed 10-s secant with the largest |value| in the minute
                 inertia_mws[],                                  // REAL, last value in the minute (feed updates ~every 50 s)
                 rocof_2750_expected_hz_per_s[],                 // DERIVED: 2750*60/(2*inertia)
                 prc_mean_mw[], prc_min_mw[],                    // REAL PRC (8/12-s samples) per minute
                 time_error_s[] },                               // DERIVED integral, anchored to REAL RTSC readings
  windows_10s: [ {label, center_cdt, half_width_s:900, t_offset_s[], f_hz[], inertia_mws[], prc_t_offset_s[], prc_mw[]} ]
                 // [0] = largest |f-60| (14:15:10, slow sag); [1] = steepest 10-s fall (03:36:50, probable trip)
}
```

Downsampling: the frequency feed has 8,289 10-s samples and PRC has 8,307 samples at 8 or 12 s. Both are aggregated to 1-minute bins, 1,382 bins, all populated. Frequency is kept as mean, min and max, so the chart can draw a band. Two ±15-minute windows keep the full 10-s resolution.

---

## 2. Claim verdicts

| # | Claim | Verdict | Correction / note | Sources |
|---|---|---|---|---|
| 1 | Show frequency's rate of change (RoCoF), not just the number | **holds, with a caveat** | RoCoF is the standard post-trip metric, but ERCOT publishes frequency only every 10 s. A 10-s difference **understates** the real initial RoCoF. At 03:36:50 today the 10-s slope was 0.0037 Hz/s. The theory value for the estimated trip is about 0.051 Hz/s, roughly 14 times higher (DERIVED). No public sub-10-s ERCOT frequency exists. | [dc-tie-flows.json](https://www.ercot.com/api/1/services/read/dashboards/dc-tie-flows.json); [ERCOT inertia paper 2018](https://www.ercot.com/files/docs/2018/04/04/Inertia_Basic_Concepts_Impacts_On_ERCOT_v0.pdf) |
| 2 | Show the time error | **holds, with a caveat** | ERCOT publishes "Instantaneous Time Error" on the RTSC page and still performs time-error correction. Nodal Operating Guide §2.2.9.1 says ERCOT must start correcting when \|TE\| > 30 s, using a ±0.02 Hz offset, and stops within ±0.5 s. The NERC continent-wide standard **BAL-004-0 is retired**: FERC approved the retirement by delegated letter order RD17-1-000 on 18 Jan 2017 (FERC Order 676-I, fn 17). NERC keeps only a non-binding Time Monitoring Reference Document. Time error is a clock-keeping metric, not a stability signal. Today it moved about 2.5 s, far from the 30 s trigger. | [RTSC page](https://www.ercot.com/content/cdr/html/real_time_system_conditions.html); [NOG Feb 2026 §2.2.9.1](https://www.ercot.com/files/docs/2026/01/29/February-1-2026-Nodal-Operating-Guide.pdf); [FERC Order 676-I](https://www.ferc.gov/sites/default/files/2020-08/01-23-2020-E-23.pdf) |
| 3 | In ERCOT, the operational proxy for "the reserve that can arrest a fall" is Physical Responsive Capability | **holds, with a caveat** | ERCOT's definition of PRC is "the total amount of frequency responsive Resource capability On-Line in Real-Time" (Protocols §2; formula in §6.5.7.5; published every 10 s). The Watch and EEA levels are keyed to PRC (NOG §4.5.3.3). **But PRC counts MW, not speed.** Its per-resource caps approximate deliverable response: 20% of the high limit for generators, for ESRs, the smallest of X% of MDRR (Maximum Droop Response Range, which is HSL−LSL for an ESR; X is set by the droop setting), HSL − Net MW, or the 45-min state-of-charge limit, and Load Resources on relays. Whether a fall stops above 59.3 Hz depends on PRC and inertia together. ERCOT's own 2023 finding was that at 200 GW·s, 1,500 MW of reserves is needed to avoid UFLS. The service that actually arrests the fall is RRS (FFR at 59.85 Hz within 15 cycles; Load Resources at 59.7 Hz). PRC is the broader pool. | [Protocols Mar 2026 §6.5.7.5](https://www.ercot.com/files/docs/2026/02/26/March-2-2026-Nodal-Protocols.pdf); [Grid Conditions dashboard](https://www.ercot.com/gridmktinfo/dashboards/gridconditions); [ERCOT release 2023-11-01](https://www.ercot.com/news/release/2023-11-01-ercot-updates-minimum); [NOG §2.3.1.2, §4.5.3.3](https://www.ercot.com/files/docs/2026/01/29/February-1-2026-Nodal-Operating-Guide.pdf) |
| 4 | System inertia in MW·s tells you how fast frequency will move when a unit trips | **holds** | The unit is now **verified**: ERCOT's RTSC help page labels it "Current System Inertia (MW.s)". Inertia sets the *initial* RoCoF (the first ~0.25–2 s): RoCoF0 = ΔP·f0/(2·Ek). The nadir also depends on primary response. ERCOT's value is an EMS estimate from the units online. It updates about once a minute (median 50 s in the feed) and moves in unit-sized steps. | [RTSC help](https://www.ercot.com/static-assets/data/help/v5/content/topics/wwwhelp/rtsyscondhelp.htm); [ERCOT inertia paper](https://www.ercot.com/files/docs/2018/04/04/Inertia_Basic_Concepts_Impacts_On_ERCOT_v0.pdf) |
| 5 | Frequency alone is a lagging indicator; inertia plus RoCoF is the leading one | **holds, with a caveat** | The direction is right. Frequency is the *outcome*, and today it said nothing about reserves. Hourly frequency σ correlated **positively** with PRC (r = 0.77, DERIVED, one day): frequency was noisiest at midday, when PRC was highest. **But measured RoCoF is not leading.** It exists only after an event starts, although it is the earliest post-event signal, ahead of the nadir. The pre-event (leading) pair is **inertia + PRC**, with the size of the largest contingency. Together they give an *expected* RoCoF and nadir. Frequency is also used operationally: EEA2 can be declared on a clock-minute average below 59.91 Hz for 15 min, and EEA3 on steady-state frequency below 59.8 Hz. | [NOG §4.5.3.3](https://www.ercot.com/files/docs/2026/01/29/February-1-2026-Nodal-Operating-Guide.pdf); REAL feeds above |
| 6 | Critical inertia is about 100 GW·s | **holds** | ERCOT's 2024 AS Study: "critical inertia" is 100 GW-s, the typical range is 200–400 GW-s, and the 10-year low was 115 GW-s (March 2022). ERCOT says grid-forming inverters may lower the critical level. | [ERCOT AS Study 2024, pp. 25–26](https://www.ercot.com/files/docs/2024/10/07/ERCOT-Ancillary-Services-Study-Final-White-Paper.pdf) |
| 7 | The design trip is 2,750 MW | **holds, with a caveat** | 2,750 MW is the 2018 inertia-paper figure. The **2024 AS Study states the two-largest-units loss as 2,800 MW**, used for the BAL-003 frequency-response obligation. The JSON computes both; the difference is 1.8%. | [2018 paper](https://www.ercot.com/files/docs/2018/04/04/Inertia_Basic_Concepts_Impacts_On_ERCOT_v0.pdf); [AS Study 2024 BAL-003 table](https://www.ercot.com/files/docs/2024/10/07/ERCOT-Ancillary-Services-Study-Final-White-Paper.pdf) |
| 8 | UFLS stages are 59.3 / 58.9 / 58.5 Hz | **holds, with a caveat** | The current NOG §2.6.1 Table 1 has **five** stages: 59.3 / 59.1 / 58.9 / 58.7 / 58.5 Hz, shedding at least 5 / 5 / 15 / 15 / 25% cumulative. The NOGRR247 replacement (no earlier than 1 Oct 2026) makes that 5 / 10 / 15 / 20 / 25%. | [NOG §2.6.1](https://www.ercot.com/files/docs/2026/01/29/February-1-2026-Nodal-Operating-Guide.pdf) |
| 9 | PRC thresholds are 3,000 / 2,500 / 2,000 / 1,500 MW (Watch / EEA1 / EEA2 / EEA3) | **holds** | Also relevant: offline Non-Spin deploys when PRC < 3,200 MW (AS Study). VECL deployment at < 3,100 MW is pending under NOGRR265/NPRR1238. | [NOG §4.5.3.3](https://www.ercot.com/files/docs/2026/01/29/February-1-2026-Nodal-Operating-Guide.pdf); [release 2023-11-01](https://www.ercot.com/news/release/2023-11-01-ercot-updates-minimum) |
| 10 | Governor deadband is ±0.017 Hz (UNVERIFIED in the research report) | **holds** | Now verified: NOG §2.2.7 Table 1 sets ±0.017 Hz for most units and ESRs, ±0.034 Hz for mechanical governors and ±0.036 Hz for CLRs. | [NOG §2.2.7](https://www.ercot.com/files/docs/2026/01/29/February-1-2026-Nodal-Operating-Guide.pdf) |
| 11 | dc-tie-flows.json holds 10-s frequency plus inertia since midnight; daily-prc.json holds PRC at about 10 s | **holds** | 8,289 samples at 10 s (00:00:00–23:01:20 CDT). PRC alternates 8 s and 12 s. Protocols §6.5.7.5(4) says PRC is updated every 10 s. | raw files in `evidence/live-20260925/` |

---

## 3. What the data says today (headline numbers)

| Quantity | Value | Status |
|---|---|---|
| Frequency mean / σ | 60.0004 Hz / 13.5 mHz | DERIVED on REAL |
| Frequency min / max (10-s samples) | 59.966 Hz at 14:15:10 / 60.022 Hz at 03:03:10 CDT | REAL |
| Clock-minute averages | 59.969–60.019 Hz; 0 minutes below 59.91 | DERIVED |
| Samples outside the ±17 mHz deadband | 14.5% | DERIVED |
| Steepest 10-s fall | −37 mHz (60.017 → 59.980) at 03:36:50 = −0.0037 Hz/s | DERIVED |
| 10-s falls ≥ 15 mHz | 249 in the day | DERIVED |
| Time error at 19:29:20 / 23:04:30 (ERCOT RTSC) | −2.302 s / −1.332 s | REAL |
| Our integral over the same span | +0.958 s vs +0.970 s observed (12 ms error over 3.6 h) | DERIVED (validates the method) |
| Time error day range (anchored) | −2.40 s (18:49) to +0.07 s (12:12); correction trigger ±30 s | DERIVED |
| Inertia min / max | 300.8 GW·s at 04:06:40 / 333.0 GW·s at 19:42:30; min = 3.0 × critical | REAL / DERIVED |
| Initial RoCoF, 2,750 MW trip | 0.274 Hz/s (day min inertia), 0.248 (day max), 0.825 (critical 100 GW·s) | DERIVED |
| No-response time 60 → 59.85 Hz (FFR trigger) | 0.55 s today (worst) vs 0.18 s at critical | DERIVED |
| PRC min / max | 7,124 MW at 07:44:52 / 21,929 MW at 11:20:52; closest approach to Watch was 4,124 MW above it | REAL / DERIVED |
| PRC at 23:04:24 | 8,191 MW, EEA level 0, "Normal Conditions" | REAL |
| AS awards at 23:04:24 | RRS 2,425 MW, ECRS 1,262 MW, Non-Spin 4,507 MW | REAL |
| Probable unit trip at 03:36:50 | step −37 mHz, held about 59.980 Hz for 2.5 min, inertia −3.0 GW·s; estimated 260–830 MW (mid 520) | REAL signature, DERIVED MW, **UNVERIFIED** as a trip |
| Frequency response from 2024–26 FMEs | β = 856–2,733 MW/0.1 Hz (median 1,720) | DERIVED on REAL |
| Data quality | 0 mismatches across 701 samples vs ancillary-services.json and 6,981 vs the 19:25 copy; longest identical-value run 50 s | DERIVED |

**Three stories the data tells**

1. **The largest deviation was not the event.** The day's lowest sample (59.966 Hz, 14:15) came from a slow multi-minute sag while PRC drained about 450 MW. The sharpest *event* came at 03:36:50: a step, a hold, and a matching inertia drop. That looks like a unit trip. Frequency magnitude alone would point at the wrong moment.
2. **The shock absorbers bottom out at different times.** Inertia was lowest overnight (04:06, few synchronous units online). PRC was lowest on the morning ramp before solar (07:44). Frequency looked the same through both.
3. **Scale.** A design trip right now would start falling at about 0.27 Hz/s. The day's steepest visible 10-s slope was 0.0037 Hz/s. The chart has to show both, or a viewer will think frequency is always calm.

---

## 4. REAL vs SIM

- **REAL:** 10-s frequency and inertia, PRC, AS capacity monitor, two RTSC time-error readings, and the 2024–26 FME rows (NP12-261-M file AsOf 08/18/2026, cached 25 Sep in `evidence/scratchpad-20260925/ercot/fme/`).
- **DERIVED:** everything computed: stats, the 10-s RoCoF, the time-error integral, expected RoCoF, no-response times, the design-trip wedge, β, the MW estimate for the 03:36 event, the hourly correlations, and the fleet-scale shift.
- **ASSUMPTION:** f0 = 60 Hz nominal; ΔP = 2,750 MW (plus a 2,800 MW variant); a sensitivity case in which the tripped units remove 12 GW·s of their own inertia (the 2018 paper's two-nuclear figure), raising RoCoF about 4%.
- **SIM:** none. The OpenDSS feeder prototype cannot produce frequency. A single-bus swing model calibrated to the FME β values could add a "trip now" SIM trace later. It is **not built**.
- **Not available:** sub-10-s or PMU frequency; real RoCoF; the true nadir between samples; ERCOT's own clock-minute average series; PRC broken down by resource type; public confirmation of the 03:36 trip (the next weekly NP12-261-M may or may not list it); the 23:01–24:00 CDT data (the feed resets at midnight); any historical 10-s series before today.

---

## 5. Visual spec: "Frequency is the outcome; inertia and PRC are the shock absorbers"

**Form.** Five stacked small-multiple rows share one x-axis (00:00–23:01 CDT, from `series_1min`) and one crosshair. A left-margin bracket groups the rows by role: **BEFORE an event (leading)** covers rows C–E; **DURING / AFTER (outcome)** covers row A; **SLOW drift** covers row B. Each row shows a status chip (REAL / DERIVED).

| Row | Encoding | Y domain | References |
|---|---|---|---|
| A. Frequency (REAL) | band f_min..f_max, line f_mean | 59.90–60.03 Hz | shaded ±0.017 deadband; dashed 59.91 (EEA2 if the clock-minute average stays below it for 15 min). Off-scale note: "FFR 59.85, UFLS 59.3 Hz are below this chart". Markers at 03:36:50 ("probable trip") and 14:15:10 ("largest dip: slow sag") |
| B. Time error (DERIVED, anchored) | line `time_error_s`; 2 dots at the RTSC readings labelled "ERCOT reading" | −3..+1 s | note "correction starts at ±30 s" |
| C. Inertia (REAL) | line in GW·s, light fill down to 100 | **0**–350 GW·s (do not truncate: the margin is the point) | solid 100 critical; dashed 115 (10-yr low) |
| D. "If 2,750 MW tripped now" (DERIVED from C) | line `rocof_2750_expected_hz_per_s` | 0–0.9 Hz/s | dashed 0.825 (critical-inertia RoCoF) |
| E. PRC (REAL) | line prc_mean with a faint prc_min | **0**–23,000 MW | bands < 1,500 EEA3, 1,500–2,000 EEA2, 2,000–2,500 EEA1, 2,500–3,000 Watch; label the day's min |

**Inset 1: "What a trip looks like in 10-s data"** (`windows_10s[1]`). The 10-s frequency steps over ±15 min, with inertia as a small step line underneath. Annotation: "10-s slope 0.0037 Hz/s; true initial slope ≈ 0.05 Hz/s (DERIVED, about 14× steeper)". Optional toggle to `windows_10s[0]` (the 14:15 sag) to contrast "step" with "drift".

**Inset 2: "The first 2.5 s of a design trip"** (`design_trip_wedge`). X from 0 to 2.5 s, y from 59.2 to 60.05 Hz. Four straight lines: today's min, today's max, the 10-yr low (115) and critical (100). Horizontal lines at 59.85 (FFR fires), 59.7 (load relays) and 59.3 (UFLS stage 1). Caption: "No-response bound. FFR, governors and load damping bend these lines within 0.25–2 s. The gap between the lines is the time inertia buys."

**Inset 3 (optional): "Frequency doesn't see reserves"** (`hourly`). 24 dots, hourly f σ against PRC mean, r = 0.77, labelled "one day, descriptive".

**Interactions.** One shared crosshair. The tooltip lists every row's value at that minute with its status tag. Clicking an event marker opens Inset 1. Units are always visible, and colour is never the only cue: threshold bands are text-labelled.

**Story role.** This panel is the system-level frame for the site. It shows how much shock the whole Texas grid could absorb at every minute of the day. That sets the scale against which Base's fleet is judged, and it hands off to the feeder panels, where the fleet actually matters.

---

## 6. What this means for Base

- **Markets desk (Head of Markets; ADER dispatch).** Base says its ADER resources carry Non-Spin and ECRS (company blog; UNVERIFIED against ERCOT files). ERCOT's emergency steps key off PRC. Offline Non-Spin deploys below 3,200 MW, the Watch starts below 3,000 MW, and EEA levels follow. In EEA3, ERCOT instructs **ESRs to suspend charging** (NOG §4.5.3.3(3)(a)). The PRC trend therefore tells the desk when its obligations and prices are about to change. Today PRC never came closer than 4,124 MW to the Watch threshold. Whether ADER capacity counts toward PRC is UNVERIFIED: the formula names CLRs, ESRs and FFR resources, not ADERs.
- **Fleet controls and firmware.** Frequency is the one grid signal every home battery can measure locally, with no cloud link, and it is the same everywhere in ERCOT. A local rule such as "refuse to charge below 59.91 Hz; follow droop outside ±0.017 Hz" would still work if dispatch comms were spoofed. Today's data sets the false-alarm floor: no clock-minute average went below 59.969 Hz and no 10-s sample below 59.966 Hz, so a 59.95 Hz guard would not have fired once (DERIVED, one day). Base lists IEEE 1547-2003 on its spec sheets. The 2018 edition's frequency-droop behaviour is the relevant upgrade (UNVERIFIED for Base hardware).
- **Security and integrity.** Physical state is a cross-check on market signals. A "$5,000/MWh, discharge everything" signal while PRC sits at 17–22 GW and frequency is normal is implausible and should be quarantined.
- **Members and backup.** PRC is ERCOT's public early warning of EEA risk. A falling PRC trend, not frequency, is the trigger for storm-mode pre-charging.
- **Scale honesty.** Base's reported 103 MW of ADER, swung fully, would shift settling frequency by roughly **3.8–12 mHz** (DERIVED from the FME β values; linear, and ignores the deadband). Today's normal wander had σ = 13.5 mHz. At system level, Base is not a frequency actor. Its grid risk and value sit on feeders and transformers, and this panel exists to make that contrast visible.
- **Cross-item note.** The research report's "40 MW moves frequency 3–17 mHz" is only partly supported by the FMEs. FME-linear scaling gives 1.5–4.7 mHz (settling) or 2.8–7.9 mHz (nadir) for 40 MW. The 17 mHz upper end would need the deadband argument, and that has not been measured.

---

## 7. Caveats

- The dashboard JSON feeds are undocumented website internals. ERCOT's help page says the displays "should not be relied upon". They reset at local midnight, so our day ends at 23:01:20 CDT for frequency and 23:04:24 for PRC.
- It is UNVERIFIED whether the 10-s `currentFrequency` is an instantaneous or an averaged value. Resolution is 1 mHz, so 10-s RoCoF resolution is 0.0001 Hz/s.
- `f_mean_hz` averages 6 samples per minute. That approximates, but is not, ERCOT's own clock-minute average.
- Inertia is an EMS estimate that updates about every 50 s in unit-sized steps. A +4,758 then −4,758 MW·s blip at 06:21:30–40 looks like a unit-status flicker. The same 4,758 MW·s step appears at 03:37:10.
- Time error = ∫(f−60)/60 dt holds whatever the scheduled frequency, so the integral stays valid even during a correction. The absolute level comes from the 23:04:30 RTSC reading. Validation against the 19:29:20 reading gave a 12 ms error.
- RoCoF0 = ΔP·f0/(2·Ek) is a system-average, first-instant, no-response bound. It ignores load damping and the tripped units' own inertia (+4% RoCoF in the sensitivity case). It also ignores that RoCoF is locally higher near the trip in the first second.
- The 03:36:50 "probable trip" and its 260–830 MW estimate are UNVERIFIED. The estimate extrapolates β from 700–1,300 MW FMEs. The pre-event average is noisy (60.003–60.017 Hz).
- The hourly correlation (r = 0.77) comes from 24 points on one day. It is descriptive, not causal: midday solar variability and battery headroom both rise at midday.
- The PRC formula is taken from the Protocols section version dated 5 Dec 2025, compiled 2 Mar 2026. Pending NPRRs (1029, 1238, 1244) would change the terms.
