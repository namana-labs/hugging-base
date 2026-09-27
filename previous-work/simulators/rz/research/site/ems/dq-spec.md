# dq: Data quality as a first-class value

Item `dq` of the EMS data list. Data file: `site/ems/dq-quality.json` (148 KB). Build scripts: `site/ems/dq-build.py` covers REAL data (stdlib only, runs offline in under 1 s from saved raw files). `site/ems/dq-sim.py` covers SIM (OpenDSS). It writes `dq-sim.json`, which the build merges in.

Raw fetches are in `evidence/live-20260925/dq-*`. They are eight dashboard feeds, fetched once each at 23:29:58–23:30:11 CDT with about 2 s between requests. The 2003 blackout report was also fetched. The build also reuses every earlier saved snapshot of the same feeds: 19:25 (research notes), 20:13 (bp-data-ingest), and 23:04–23:19 (the freq, flow, res, n1 and load items). That makes 2 to 5 observations per feed without another request.

Status tags:
- **REAL**: public data, with endpoint and retrieval time.
- **SIM**: prototype OpenDSS on SMART-DS p1uhs19_1247--p1udt17263, with scripted inputs.
- **DERIVED**: our arithmetic on REAL or SIM data, with the formula.
- **ASSUMPTION**: an input we chose.
- **UNVERIFIED**: a claim we could not source.

---

## 1. JSON shape (`dq-quality.json`)

```
{
  item:"dq", title, generated_utc, status_legend{REAL,SIM,DERIVED,ASSUMPTION},

  vocabulary: {                                   // what the words mean, with sources (section 2)
    cim:{ MeasurementValueQuality{is_a, attached_to, text, source},
          Quality61850{validity[3], source_enum[3], flags{oldData,suspect,failure,outOfRange,estimatorReplaced,...}, source},
          MeasurementValueSource{text, note, source}, "MeasurementValue.timeStamp" },
    ercot_quality_codes:{codes{Valid,Manual,Calculated,Suspect,Invalid,Com_fail}, source, se_use, sced_input, price_risk, availability},
    iccp_tase2:{validity[4], current_source[4], note, source},          // SECONDARY (vendor docs)
    team:{ mw_Provenance, dossier_quality_row, data_ingest_quality, device_belief, glossary_truth_claim_meter } },

  crosswalk: [ {our_status, meaning, cim_validity, cim_flags[], cim_source, ercot_code, data_ingest, device_belief, visual} ],  // 9 rows
  fetched_basis_legend: {client_clock, http_date, fetch_log, file_mtime},   // how each snapshot's fetch time is known
  raw_header_files: "...",                                                   // where the saved response headers are

  ribbon: [                                        // ONE ROW PER FEED: what every panel's chip shows
    { feed, label, source, status:"REAL", mode_on_page:"RECORDED", captured_cdt, as_of_cdt,
      age_at_capture_s, lastUpdated_age_at_capture_s, age_range_over_snapshots_s[2], snapshots,
      cadence_s, cache_max_age_s, fresh_s, ttl_s,
      status_at_capture ("ok"|"late"|"stale"), cim_validity, cim_flags[], ercot_quality_code_analogue,
      time_went_backwards, gaps_today, coverage_pct_today,
      primary_field_held_runs_over_180s | null, primary_field_repeated_consecutive_values | null,
      fallback_chain | null, used_by_items[],
      chip_text, chip_text_short } ],                // 10 feeds; chip_text is ready to render

  feeds: [ { id, label, url, status:"REAL", used_by_items[],
             rule{fresh_s, ttl_s, source, age_measured_on},
             age_summary{n_snapshots, min_s, median_s, max_s, statuses{}, formula},
             time_went_backwards_between_fetches[ {earlier_fetch_cdt, earlier_newest_cdt, earlier_etag, later_fetch_cdt, later_newest_cdt, later_etag, later_by} ],
             snapshots[ {fetched_by, fetched_utc, fetched_cdt, fetched_basis (code), raw, max_age_s, etag,
                         lastUpdated, newest_sample_cdt, n_samples, age_lastUpdated_s, age_newest_sample_s, status_by_rule} ],
             channels[ {channel, primary_field,
                        cadence{n, first_cdt, last_cdt, step_s_counts{}, median_step_s, mean_step_s, nominal_step_s,
                                expected_n_for_span, coverage_pct, gaps[], gap_count, duplicate_timestamps, non_monotonic},
                        fields{<field>:{longest_identical_run{samples,seconds,start_cdt,end_cdt,value}, runs_held_over_180s|null,
                                        seconds_in_held_runs, pct_of_span_in_held_runs, distinct_values, nulls, held_rule_applicable}},
                        value_change_cadence{<field>:{changes, median_s_between_changes, p90_s, max_s}}   // sub-minute channels
                        | repeated_consecutive_values{<field>:{count, examples[]}},                       // 5-min and slower
                        bins15{coverage[96], held_frac_primary[96], bin_minutes:15, first_bin_cdt} } ],
             revisions_first_vs_last_snapshot[ {channel, from_fetch_cdt, to_fetch_cdt, fields_compared, values_overlapping,
                                                values_changed, max_abs_change, examples[]} ] } ],   // per channel, all fields compared
             // system-wide-prices stores run statistics for 5 of its 15 price fields (lzNorth, lzAen, lzHouston, hbNorth, hbHubAvg); revisions cover all 15

  held_value_calibration: { status:"DERIVED", rule, rows[ {feed, channel, field, longest_identical_run_s, longest_run_value,
        longest_run_end_cdt, runs_held_over_180s, pct_of_span_in_held_runs, distinct_values,
        median_s_between_value_changes, held_rule_false_alarm_free_today} ] },

  timezone_dst: { audit{<feed>:{utc_offsets_seen{}, dstFlag_values{}, naive_timestamp_fields[]}}, notes[ {feed, status, note} ] },

  cross_checks: [ frequency_two_feeds{overlap_samples, mismatches, ancillary_services_samples_newer_than_dc_tie_flows, ...},
                  storage_two_feeds{overlap_samples, mean_diff_mw, median_abs_diff_mw, p95_abs_diff_mw, max_abs_diff_mw, ...},
                  storage_time_label_test{candidates[ {compare_fuel_mix(t)_with, n, median_abs_diff_mw, p95_abs_diff_mw} ], best_match,
                                          blend_scan{formula, rows[11]{w_esr_t, implied_esr_lag_min, n, median_abs_diff_mw, p95_abs_diff_mw, mean_abs_diff_mw},
                                                     best_w_esr_t, best_implied_esr_lag_min, lags_within_10pct_of_best_median_min[2]},
                                          label_semantics_differ, tile_label, inference},
                  publication_time_check{formula, rows[11]{feed, fetched_by, fetched_cdt, fetched_basis, raw, lastUpdated, newest_label_cdt, field, value,
                                                          fetch_minus_label_s, lastUpdated_minus_label_s, value_in_latest_snapshot, numeric_fields_at_label,
                                                          fields_changed_by_latest_snapshot, fetch_proves_not_interval_start_average,
                                                          lastUpdated_says_not_interval_start_average},
                                         summary{<feed>:{snapshots, fetch_minus_label_s_range[2], lastUpdated_minus_label_s_seen[], newest_label_final_at_first_sight,
                                                         snapshots_proving_by_fetch_time, proof_snapshot{fetched_by, fetched_cdt, newest_label_cdt, value, fetch_minus_label_s}}}},
                  prc_two_feeds{ascm_prc_mw, daily_prc_nearest_mw, seconds_apart, current_condition_matches_last_sample, ...} ],

  sim: {                                            // from dq-sim.py; status "SIM"
    status, engine, feeder, generated_utc, runtime_s,
    reproduction_check[ {scenario, policy, step, replay{maxLoading,minVoltage,feederMW}, resolved{...}, delta{}, tolerance{}, match} ],
    prototype_facts[],
    comms_loss:{ params[ {name, value, unit, status, source} ],
                 solver{status, part_a_convergence (1e-4), part_b_convergence (1e-8), why,
                        original_order_default_tolerance{aware|naive:{S0..S3:{maxLoading, maxVoltage}}},     // what the 01:15 file reported
                        range_over_warm_starts_default_1e-4{aware|naive:{S0..S3:{maxLoading[2], maxVoltage[2]}}},
                        zero_spread_at_1e-8{aware, naive}, range_formula, p2_max_abs_diff_kw_default_vs_tight{aware, naive}},
                 runs{aware|naive:{ scenario, policy, step, sim_clock, load_factor, target_kw,
                        transformer_ids[16], transformer_kva[16],          // the 16 Cedar transformers (the truth's most-loaded transformer is one of them)
                        silent_group{name, units, units_dispatched_at_loss, last_power_kw_sum, transformers, why},
                        states{S0_before_loss_and_hold_last_belief | S1_truth_after_expiry_cedar_idle |
                               S2_prd_redispatch_at_expiry | S3_double_dispatch_if_device_holds:
                               {feederMW, maxLoading, minVoltage, maxVoltage, overloaded, voltageViolations, cedar_min_voltage, fleet_kw,
                                transformers[16] (loading %, same order as transformer_ids),
                                maxLoading_at, maxLoading_4dp, maxLoading_tf_primary_kw (<0 = backfed), maxLoading_tf_backfed,
                                maxVoltage_6dp, maxVoltage_at (home bus), maxVoltage_at_is,
                                (S0: label -> notes.S0_label, max_loading_note)
                                (S2: shortfall_kw, tolerance_kw, max_voltage_delta_pu_vs_S0, max_voltage_margin_pu{to_ansi_1_05, to_splitter_acceptance_1_0495, splitter_source},
                                     max_voltage_unit_kw{unit, S0, S2, sign}, max_voltage_note)
                                (S3: over_delivery_kw, window_s[2], over_delivery_kwh, over_delivery_formula,
                                     vs_S0{max_loading_delta_pp, same_transformer, transformer, max_voltage_delta_pu},
                                     vs_S2{max_loading_delta_pp, max_voltage_delta_pu, same_max_voltage_bus}, limits_crossed{overloads, voltage_violations}, meaning)}},
                        confident_wrong_answer{status, formula, estimate_is, phantom_kw, overloads_believed|true, voltage_violations_believed|true,
                               max_loading_believed_pct, max_loading_true_pct, cedar_min_voltage_believed, cedar_min_voltage_true,
                               unmetered_transformers{why_confident, reporting_fleet_units_on_cedar_transformers, cedar_transformers,
                                     headline{id, kva, loading_believed_pct, loading_true_pct, error_pp, headroom_believed_kva, headroom_true_kva, headroom_formula},
                                     transformer_error_pp{formula, most_under_believed[3], most_over_believed[3], count_abs_error_over_20pp,
                                                          all_of_them_cedar_transformers, transformers_total},
                                     limits_crossed},                                        // WHERE the wrong answer is confident
                               head_meter_residual{feeder_mw_estimate, feeder_mw_true, residual_kw, residual_pct_of_true,
                                     of_which_silent_cohort_kw, of_which_loss_change_kw, residual_if_device_holds_kw_until_180s,
                                     formula, meaning, who_has_it, caveat},                  // the check that WOULD expose it
                               reporting_unit_voltage_residual{reporting_units, max_abs_dv_pu, max_at_unit, median_abs_dv_pu,
                                     count_abs_dv_over_0_001_pu, count_abs_dv_over_0_005_pu, formula, thresholds_note, meaning}},
                        timeline_10s{ t_s[31], device_status[31], comms_lost_label[31], cim_validity[31], cim_flags[31][],
                                      truth_kw{IDLE_ON_EXPIRY[31], HOLD_LAST[31]},
                                      belief_kw{hold_last_forever[31], base_blog_blank_after_180s[31] (null = blanked), prd_belief[31]} },
                        belief_error{formula, by_rule_and_device_policy{<rule>:{<device_policy>:{phantom_kwh_0_300s, seconds_blank}}}} }},
                 scale_note{status:"DERIVED + ASSUMPTION", is_a_restatement_of_the_tolerance, formula, value_pct, statement, mechanism,
                            assumptions[3], floor, where_it_would_surface,
                            prototype_check{capability_kw, tolerance_kw, target_kw, reported_fleet_kw_hold_last, true_fleet_kw_cedar_idle,
                                            reported_miss_kw, true_miss_kw, true_miss_pct_of_capability, true_miss_within_tolerance, meaning}, source},
                 notes{S0_label, estimate_is, why_confident, head_meter_meaning, head_meter_who_has_it, head_meter_caveat,
                       voltage_thresholds_note, voltage_meaning} },   // text shared by both runs; a run's field reads "see comms_loss.notes.<key>" 
    detector:{ params[], runs{aware|aware_quarantine:{
                 steps[13]{step, sim_clock, residual_sum_kw, flags, quarantined, fixed_1kw_threshold_flags, false_positive_rate_pct,
                           detection_seconds, channel_voltage_pu, delivered_kw, target_kw, tracking_ok,
                           groups{cedar|other:{n, states{GOOD,WATCH,SUSPECT,QUARANTINED}, rms_kw{min,median,max},
                                               abs_corr{...}, abs_voltage_delta_pu{...}}}, states_all{}},
                 unit_rms_kw{ids[96], cohort[96], rms[96][13]}   // "aware" run only
               }} } }
}
```

`dq-sim.json` (64 KB) is the SIM block on its own, as written by `dq-sim.py`. It is identical to `dq-quality.json.sim`.

**Number format.** Whole-number floats are written as integers (`1.0` → `1`); a browser reads the same number. Part B SIM states are solved at OpenDSS convergence 1e-8 (see `comms_loss.solver`).

**Downsampling.** None of the REAL series are copied into the file. It carries per-feed statistics, gap lists (at most 20 per channel) and one 96-cell (15-min) coverage and held strip per channel. SIM carries a 31-point timeline (10 s steps, 0–300 s) per run and 13 steps × 96 units of detector RMS. Nothing is interpolated. Between OpenDSS solves the timeline is a step function, because the states it switches between are discrete.

---

## 2. Claim verdicts (RZ's text, not gospel)

RZ: *"Data quality itself. An EMS treats the freshness and validity of every telemetered point as a first class value, because a stale or bad measurement feeding the state estimator produces confident wrong answers. This is exactly the mw:Provenance and quality discipline and it is not decoration here, it is a stability input."*

| # | Claim | Verdict | Evidence and correction |
|---|---|---|---|
| 1 | An EMS treats the freshness and validity of every telemetered point as a first-class value | **holds** (for ERCOT's EMS and for CIM) | ERCOT Nodal Protocols §3.10.7.5.8.1 (p. 3-184): "Statuses and analogs telemetered to ERCOT shall be identified with the following quality codes": Valid, Manual, Calculated, Suspect, Invalid, Com_fail. The last is defined as "due to communications failure, the analog or status provided ERCOT is not current". CIM gives every `MeasurementValue` a `MeasurementValueQuality` (a `Quality61850`: `validity` GOOD/QUESTIONABLE/INVALID plus flags including `oldData`). **Caveat for our page:** the public dashboard JSON carries **no** per-point quality code. Everything this item says about ERCOT feed quality is DERIVED from age, cadence, repeats and cross-feed checks. |
| 2 | A stale or bad measurement feeding the state estimator produces confident wrong answers | **holds with caveat** | ERCOT §6.3 (p. 6-4): "Missing, incomplete, stale, or incorrect versions of one or more data elements input to the market applications may result in an invalid market solution and/or prices." §3.10.9 (p. 3-193) requires the SE to "detect, correct, or otherwise accommodate … stale data condition codes". §3.10.9.5(4) (p. 3-196): quality codes set the SE's confidence factors. SCED inputs flag any TSP point "stale for more than 20 seconds" (§6.5.7.1.13(1)(a), p. 6-51). **Correction on "confident":** the 2003 case is usually cited here, and there the SE was *not* confident. MISO's SE, fed a stale line status, "produced a solution with a high mismatch (outside the bounds of acceptable error)" and the SE and contingency analysis were effectively out of service from 12:15 to 16:04 EDT (U.S.-Canada Task Force Final Report, April 2004, p. 48). The *silent* failure was FirstEnergy's frozen alarm system. Operators "did not know that they were operating without alarms" and read silence as "system conditions were still safe and unchanging" (pp. 52–53). A redundant WLS estimator usually flags a single gross error. Confident wrong answers come from errors that look plausible: frozen-but-reasonable values, critical measurements with no redundancy, and topology errors that happen to fit. That last part is textbook SE theory, **UNVERIFIED** here because no primary source was fetched. Our SIM shows where it bites (section 4). The aggregator's estimate built on held values is a power flow. A power flow has no redundant measurements, so converging with 0 violations says nothing about whether it is right. It is confidently wrong only where nothing measures: on 10 of 379 service transformers, by up to 47.7 pp (p1udt23656: 18.1% believed vs 65.8% true), and no still-reporting unit sits on any of them. At the feeder head, which the utility meters, the same error would appear as a +356 kW (5.0%) residual. That is detectable, not confident. |
| 3 | "This is exactly the mw:Provenance … discipline" | **unverifiable (name)**; the discipline itself holds | The string `mw:Provenance` (or any `mw:` namespace) appears nowhere in the repo, the dossier, the PRD or the site pages (grep, 26 Sep 00:30 CDT). The dossier's own terms are the **provenance layer / provenance ribbon / provenance chips** (PRD L-07, ESSENTIAL). It maps quality to CIM `MeasurementValueQuality.validity` and source to CIM `MeasurementValueSource`. We use those names and do not invent a standard. **Correction to the dossier's table:** it lists "Data quality (good, questionable, invalid, **stale**)" as `validity` values. CIM `validity` has three values. Staleness is the separate `oldData` flag ("not been successfully updated during a specified time interval"), and validity is then usually QUESTIONABLE. |
| 4 | It is not decoration, it is a stability input | **holds with caveat** | Quality codes set the SE's confidence in each value (§3.10.9.5(4), p. 3-196). The SE feeds network security analysis (NSA: "Using the input provided by the State Estimator, ERCOT shall use the NSA processor", §6.5.7.1.10(1), p. 6-47), and NSA-identified constraints, with their Generic Transmission Limits, are activated in SCED (§6.5.7.1.11(1), p. 6-49). A GTC exists "for the purpose of managing stability, voltage, and other constraints" (§2 definition, heading p. 2-38, text p. 2-39), and GTCs stand in for "system stability limits and voltage limits" and "shall be used in the SCED application" (§3.10.7.6(1), p. 3-188). So quality is an input to how ERCOT enforces stability and security limits. It does not change the physics, which inertia and governor response set. ERCOT also issues RUC instructions for system inertia (a reporting category in §5.8(1)(e), p. 5-67). That ERCOT's inertia figure is built from telemetered unit status is plausible but not stated in the protocols we hold: **UNVERIFIED**. For Base, the PRD's belief rules decide which units count toward the dispatch envelope and the firm commitment, so a stale unit changes dispatch (SIM, section 4). **Caveat for the page:** the dashboards we show are downstream copies. They inform the viewer and control nothing. |
| 5 | (premise) Base treats telemetry older than 180 s as stale | **holds with caveat** | Base blog (fetched 04:20:41Z): "Telemetry held for more than 180 seconds is treated as stale rather than as a flat dispatch and is blanked from the realized trace". This is a rule for **held (flat) aggregate telemetry in Base's published scoring chart**. It is not a documented per-unit age rule. Our research report paraphrased it as "any unit whose telemetry is more than 180 s old". Applying it per unit is the team's design (ASSUMPTION). |
| 6 | (premise) The prototype exercises COMMS_LOST and the 180 s rule | **wrong** | `sim/constants.py` defines `COMMS_STALE_SECONDS = 180` and `COMMS_LOSS_POWER_KW = 0.0`. No replay puts a unit into COMMS_LOST, and nothing reads the 180 s constant except the `model.json` export. `docs/design.md` §5.1 says "Only GRID_DISPATCH, GRID_IDLE and COMMS_LOST are exercised in the three scenarios". `docs/reconciliation.md` correctly says it is unexercised. `dq-sim.py` runs it (section 4). |
| 7 | (vocabulary) CIM `MeasurementValueQuality` (validity GOOD/QUESTIONABLE/INVALID and flags) and `MeasurementValueSource` | **holds** | [TNO CIM ontology: MeasurementValueQuality](https://ontology.tno.nl/IEC_CIM/cim_MeasurementValueQuality.html) ("Measurement quality flags. Bits 0-10 are defined for substation automation in draft IEC 61850 part 7-3 … Bits 16-31 are reserved for EMS applications"; superclass `Quality61850`). [PyCIM Quality61850](https://pythonhosted.org/PyCIM/CIM14.IEC61970.Meas.Quality61850'.Quality61850-class.html) gives validity {GOOD, QUESTIONABLE, INVALID}, source {PROCESS, SUBSTITUTED, DEFAULTED}, and flags oldData, suspect, failure, outOfRange, estimatorReplaced ("not an IEC 61850 bit … included for convenience"), operatorBlocked, test, badReference, overFlow and oscillatory. [MeasurementValueSource](https://ontology.tno.nl/IEC_CIM/cim_MeasurementValueSource.html): "describes the alternative sources updating a MeasurementValue". Its naming conventions live in the paywalled IEC 61970-301 introduction and are **UNVERIFIED**. The ICCP/TASE.2 flags (validity VALID/HELD/SUSPECT/NOTVALID; source TELEMETERED/CALCULATED/ENTERED/ESTIMATED) come from **vendor docs** ([Ipesoft](https://doc.ipesoft.com/pages/viewpage.action?pageId=3444925), [PcVue](https://www.pcvue.com/ProductHelp/PcVue/en/Content/Extras/iccp_vtq.php)), not the IEC text. They matter because Base says its ADER telemetry reaches SCED over ICCP. |
| 8 | (premise, research notes) dashboards are CDN-cached with max-age 60, and daily-prc with 10 | **holds** | Every saved header agrees. Also `ancillary-service-capacity-monitor.json` is max-age 10, which is new. |
| 9 | (premise, research notes) the frequency feed is "about 1 to 2 minutes behind" | **holds with caveat** | `ancillary-services.json` newest sample was 19–112 s old across 4 fetches. `dc-tie-flows.json`, which carries the same frequency plus inertia, was **112–398 s** old across 5 fetches. It was STALE under the team's 5-minute TTL at 23:30. |
| 10 | (premise, data-ingest.md) treat 5-min points as interval-ending | **holds with caveat**: label semantics differ between feeds (DERIVED; INFERENCE from one day) | **Correction to our own first verdict:** fuel-mix does **not** label by interval start. Publication times rule it out (`cross_checks.publication_time_check`). Every fuel-mix snapshot has `lastUpdated` = newest label + 60 s. The 23:19:06 fetch (load item, HTTP `Date`) already carried label 23:15 at its final value, −389.59 MW, only 246 s after the label, and the 23:30 fetch had the same value. An average over [*t*, *t*+5 min] cannot exist before *t*+5 min. What the data do show is a **relative lag**: fuel-mix "Power Storage"(*t*) sits between ESR `netOutput`(*t*) and ESR(*t*+5 min). The best blend is 0.5/0.5, with a median absolute difference of 44.3 MW (n = 281) vs 103.5 MW for ESR(*t*) alone (n = 282). So ESR(*t*) lags fuel-mix(*t*) by about 2.5 min (2.0–2.5 min is within 10% of the best). Fuel-mix(*t*) is out by *t*+60 s, so ESR(*t*) must describe a time at least about 1 min before its own label. That is consistent with ESR being an interval-ending 5-min average and fuel-mix a near-instantaneous value. This is one reading; pinning down the absolute meaning needs a sub-5-min anchor these feeds do not carry. **The caveat:** the interval-ending assumption is consistent for ESR, but fuel-mix labels mean something else. Joining the two feeds on the same label mixes values about 2.5 min apart. Not documented by ERCOT. |

---

## 3. What exists (REAL) vs what we simulate (SIM)

**REAL (ERCOT public dashboards, fetched 25 Sep 2026 evening, no key)**
- Ten feeds, 2–5 snapshots each (36 observations): `dc-tie-flows`, `daily-prc`, `ancillary-services`, `ancillary-service-capacity-monitor`, `supply-demand`, `fuel-mix`, `system-wide-prices`, `energy-storage-resources`, `system-wide-demand`, `combine-wind-solar`. Each snapshot records its fetch time and says how that time is known: client clock, HTTP `Date`, fetch log, or file mtime (approximate, for the 20:13 cache).
- What the feeds carry: `lastUpdated`, full timestamps with `-0500`, `dstFlag`, epoch fields, cache headers and ETags.
- What the feeds do **not** carry: any per-point quality code, any source or estimation flag, or any revision marker. The only built-in quality signal is `supply-demand`'s `forecast` 0/1.
- ERCOT's rules for quality codes, SE confidence and stale SCED inputs come from the Nodal Protocols PDF (2 Mar 2026 edition) saved by the freq item.

**SIM (prototype, OpenDSS on SMART-DS, scripted inputs)**
- Device-level telemetry quality: the FRESH/SUSPECT/STALE belief rules, the 180 s stale threshold, the COMMS_LOST label and the command TTL. The prototype never exercised these, so `dq-sim.py` runs them on the heat-wave peak (section 4).
- The covert-scenario detector. This is the prototype's state-estimator analogue: metered minus commanded power per unit, gated by an OpenDSS voltage-corroboration test. It is read per step from `replays.json` (section 4).
- Not simulated: an actual WLS state estimator, ICCP quality bits, or any ERCOT-side processing.

---

## 4. Headline numbers

**REAL and DERIVED (ERCOT feeds)**

| What | Value | Status |
|---|---|---|
| Newest-sample age at the 23:30 capture | daily-prc 36 s; ancillary-services 47 s; AS capacity monitor 25 s; supply-demand 302 s; fuel-mix 304 s; ESR 311 s; RT prices 906 s; **dc-tie-flows 398 s (STALE by the 5-min TTL)** | DERIVED (fetch time minus newest sample timestamp) |
| Age range over all snapshots | dc-tie-flows 112–398 s; ancillary-services 19–112 s; daily-prc 23–36 s; RT prices 251–906 s; hourly wind/solar actual 4,744–5,112 s | DERIVED |
| Time went backwards | freq item's fetch at 23:04:46 got newest 23:01:20 (ETag f1f2434f). The flow item's fetch 73 s later, at 23:05:59, got **23:01:00** (ETag 798edd9e). A later request received an older file, probably from a different CDN edge (INFERENCE). | REAL |
| Completeness today | dc-tie-flows 8,421/8,421 10-s samples (00:00:00–23:23:20); daily-prc 8,457 (alternating 8/12 s); 5-min feeds 282/282; RT SPP 93/93. **0 gaps** in any feed. | DERIVED |
| Revisions | **0 of 53,115** overlapping values changed between each feed's 19:25 snapshot and its latest one (23:30; 23:19 for system-wide-demand and combine-wind-solar), across 8 feeds | DERIVED |
| Held-value rule on a normal day | frequency longest identical run 50 s, PRC 52 s: **0 false alarms**. Inertia: 104 runs > 180 s (77.6% of the day; longest 44 min, 07:24–08:08). DC ties: up to 18 h (dcR = 0). AS awards: 3–22 runs each. | DERIVED |
| Frequency in two feeds | 684 overlapping 10-s samples, **0 mismatches**. ancillary-services had 36 newer samples (6 min fresher). | DERIVED |
| Storage in two feeds | Same-label median absolute difference 103.5 MW (p95 361, max 621 at 18:20). The best blend, 0.5 × ESR(*t*) + 0.5 × ESR(*t*+5), gives 44.3 MW. **ESR lags fuel-mix by about 2.5 min** (2.0–2.5 min within 10% of the best). | DERIVED (median \|fuel-mix(*t*) − (w·ESR(*t*) + (1−w)·ESR(*t*+5))\|, w = 0…1 in steps of 0.1) |
| Publication times of 5-min labels | Label *t* appears with `lastUpdated` = *t* + 60 s (fuel-mix), *t* + 61 s (ESR) and *t* + 0 s (supply-demand), in every snapshot (3, 4 and 4 snapshots). It is already present 231–249 s after *t* in 5 snapshots (fuel-mix label 23:15 at 23:19:06, −389.59 MW). Every newest-label value was final at first sight (0 fields changed later). **So no 5-min feed here labels by interval start.** | DERIVED (fetch time − label; `lastUpdated` − label; newest-label values vs the latest snapshot) |
| PRC in two feeds | 8,630 MW (daily-prc 23:29:24) vs 8,627 MW (capacity monitor 23:29:44), 20 s apart | REAL values; the comparison is DERIVED |
| Format hazards | supply-demand `dstFlag` is integer 0 (elsewhere "N"); `hourEnding` holds the hour *beginning*; actual and forecast rows share one array; `ascapmon` timestamps have no offset; `prc_value` is the string "8,630"; epoch seconds vs milliseconds | REAL |

**SIM** (from `dq-sim.json`; OpenDSS on SMART-DS with scripted inputs)

| What | Value | Status |
|---|---|---|
| Reproduction check | 4 of 4 replay states re-solve within tolerance. Heat wave aware and naive and rebound aware are exact. Covert differs by 0.01 pp and 0.2 kW because replay powers are stored rounded to 1 W. | SIM |
| Prototype stale handling | `COMMS_LOST` is never set in any replay, and the 180 s constant is never read | code read |
| Silent group | 24 Cedar Cores on 16 transformers (10 × 25 kVA, 6 × 50 kVA). They discharge 345.5 kW (aware) or 235.2 kW (naive) at the 19:30 heat-wave peak (step 12, load factor 0.57). | SIM; the cohort choice is ASSUMPTION |
| **Confident wrong answer (aware): unmetered service transformers** | The estimate (S0) is the aggregator's model-based estimate under the hold-last belief: a power flow on the last telemetered powers, with every other load known exactly and **no feeder-head meter in the loop**. A power flow has no redundancy, so converging with 0 violations is not a confidence measure. Against the truth (S1, Cedar idle): **10 of 379 transformers are off by more than 20 pp, all of them Cedar transformers.** Under-believed by up to +47.7 pp: **p1udt23656 (25 kVA) 18.1% believed vs 65.8% true**, so headroom is 20.5 kVA believed vs 8.6 kVA true. Over-believed by up to −58.5 pp: p1udt24321 at 73.8% vs 15.3% (backfed while the batteries discharged). **0 of the 72 still-reporting units sit on any of the 16 Cedar transformers**, so no fleet measurement can contradict these numbers. We assume no transformer-level telemetry (UNVERIFIED for Oncor), and premise AMI is not real-time (Base blog). No limit is crossed in either state (0 overloads, 0 voltage violations): the error is in headroom. | DERIVED from SIM solves; metering is ASSUMPTION |
| Head-meter residual (aware): the check that would expose it | Estimate 6.824 MW vs metered head 7.180 MW: a **+356.3 kW (5.0%) residual**, made up of 345.5 kW of held Cedar discharge plus a 10.8 kW loss change. The feeder head is SCADA-metered at the substation, so an estimator using that meter would see this residual and flag the stale cohort. That makes it a detectable error, not a confident one. It is 0 while a HOLD_LAST device is still discharging, so the same residual also shows which device policy is true. The meter belongs to the utility; whether Base sees it is ASSUMPTION (we assume not). In SIM the load model is exact; a real residual also carries load-model error, and its size here is not available. | DERIVED from SIM solves |
| Reporting-unit voltages (aware) | The 72 units that still report see the feeder-wide shift. Believed vs true voltage differs by at most 0.0071 pu (median 0.00007 pu). 20 units move by more than 0.001 pu and 5 by more than 0.005 pu (illustrative cut points). Device voltage accuracy is UNVERIFIED. | DERIVED from SIM solves |
| Naive run, same checks | Transformers: 11 of 379 off by more than 20 pp (all Cedar); biggest miss **p1udt16141 at 15.6% believed vs 79.7% true** (+64.1 pp; headroom 21.1 vs 5.1 kVA). Head-meter residual +244.3 kW (3.5%): 235.2 kW cohort plus 9.1 kW losses. Voltages at most 0.0049 pu. Double dispatch (S3): +235.2 kW over the base point for 150 s (9.8 kWh); max loading equals S0's (77.72%, p1udt20273, +0.0000 pp) and max voltage equals S2's (1.04302 pu, +0.00002 pu). | DERIVED from SIM solves |
| Belief error, first 300 s (aware) | Hold-last forever: 25.9 kWh if devices idle at expiry, 11.5 kWh if they hold. Base's blank-after-180 s: 15.4 kWh plus 110 s blank if they idle, 1.0 kWh plus 110 s blank if they hold. PRD belief: **0.0 kWh if they idle, 14.4 kWh if they hold**. No rule is right under both device behaviours. | DERIVED (sum of absolute belief minus truth × 10 s) |
| Before the loss (S0, aware) | Max loading **99.49%** on p1udt9411 (25 kVA), a Cedar transformer **backfed** by its 2 discharging units (−39.3 kW of battery against 19.4 kW of home load; 19.4 kW flows back to the primary). The aware splitter accepts a dispatch only up to 99.5% loading and scales it back otherwise (`sim/splitter.py`), which is why the replay fleet sits at −923.8 kW against the −940.8 kW target. Max voltage 1.04829 pu at fleet unit p1ulv5745. This is the normal pre-loss state, not something the loss causes. | SIM |
| After expiry, Cedar idle (S1) | Max loading 81.92% (p1udt9411, now forward-fed by its home load); max voltage 1.04832 pu | SIM |
| PRD re-dispatch at expiry (S2) | Fleet back to the −940.8 kW target (0 shortfall); max loading 81.92%. **Re-dispatching onto the 72 fresh units raises the max voltage to 1.0493 pu** (1.04933; +0.00105 pu vs S0) at p1ulv5745, whose setpoint rises from −19.64 to −20.00 kW. That is 0.00017 pu under the splitter's own 1.0495 pu acceptance cap and 0.00067 pu under 1.05. | SIM; deltas DERIVED (S2 − S0) |
| If the device actually holds (S3) | The double dispatch **crosses no local limit and moves no local limit metric**: max loading +0.0011 pp vs S0 (same transformer p1udt9411, 99.49% in both), max voltage −0.00003 pu vs S2 (same bus). Its cost is tracking: **+345 kW over the base point for 150 s** (fleet −1,286 kW vs the −940.8 kW target; 14.39 kWh), a scoring error, not a network one. | SIM; deltas DERIVED (S3 − S0, S3 − S2); kWh DERIVED (345.45 kW × 150 s / 3600) |
| Solver tolerance | At OpenDSS's default 1e-4 convergence a state's result depends on the previous solve: over 5 warm starts S0 ranged 99.49–99.50% and S3 99.49–99.51%. The 01:15 file's "S3 99.51%" was that noise. Part B now solves at 1e-8: zero spread at reported precision in both runs, and identical S2 setpoints (max difference 0 kW). | SIM (`comms_loss.solver`) |
| Detector (covert) | The fictional modulation starts at 19:45. Cedar RMS median is 0.023–0.040 kW before it, 0.183 kW at 19:45 (15 of 24 WATCH) and 0.231 kW at 19:50 (24 of 24 WATCH). **All 24 are flagged SUSPECT at 20:00 (900 s).** Clean units: max RMS 0.130 kW, 0 WATCH, 0 flags. A fixed 1 kW threshold flags nothing all hour. Cedar median absolute voltage delta is 0.0005 pu vs 0.0000 for the others. Quarantine at 20:00 cuts the fleet residual from ±8.1–9.1 kW to at most 0.34 kW. | SIM |
| Scale (a restatement of Base's tolerance, not a finding) | Base's CLREDP tolerance is the greater of 2 MW or 15% of max capability (7.03 / 46.9 = 6.9 / 46 = 15%). Take a fully discharging fleet where more than 15% goes silent, the devices idle, and their last values are held in the aggregate. The reported trace still looks on target while true delivery misses by more than the tolerance. Base's aggregate held-for-180 s rule would not catch it, because the aggregate is not flat. Below 13.33 MW of capability the 2 MW floor dominates instead. Prototype check: capability 1,920 kW, tolerance 2,000 kW (floor), true miss 362.4 kW (18.9% of capability), reported miss 17.0 kW. The true miss still scores as within tolerance. | DERIVED + ASSUMPTION (full discharge; idle-on-loss is UNVERIFIED; per-unit hold inside the aggregate) |

---

## 5. Visual spec

### 5.1 The ribbon: a chip every panel carries

Every panel shows one chip per input feed, at most three, in its footer. A panel built from SIM shows a single SIM chip.

**Build on what the page already has.** `hugging-base-atlas.src.html` already has a `.provline` (a 12 px faint provenance sentence under a panel) and `.sc-badge` pills ("REPLAY · 5-MIN OPENDSS STEPS", "SCRIPTED PRICES · SOLVED PHYSICS"). The dq ribbon is an `.sc-badge` for the STATUS word plus a `.provline` holding the rest of `ribbon[].chip_text`, so it is not a new component. `chip_text` and `chip_text_short` are preformatted in the JSON.

The chip reads left to right:

`[glyph] STATUS · source · as of hh:mm:ss CDT · age · cadence · validity`

Example for the frequency panel at capture:

`◌ STALE · ERCOT dc-tie-flows.json · as of 23:23:20 CDT · 6 m 38 s at capture · every 10 s · QUESTIONABLE (oldData)`

`● OK · ERCOT ancillary-services.json · as of 23:29:20 CDT · 47 s at capture · every 10 s · GOOD`

| Field | From | Rule |
|---|---|---|
| glyph + STATUS word | `ribbon[].status_at_capture` (+ `crosswalk`) | Shape and word always; colour only reinforces. ok = filled dot; late = half dot with a clock; stale = hollow hatched dot; frozen = "‖"; invalid = triangle "!"; down = crossed circle; fallback = arrow into dot; forecast = dotted ring; SIM = diamond. |
| source | `ribbon[].source` | Links to the credits drawer (raw file, URL, fetch time, fetch basis). |
| as of | `as_of_cdt` | Newest **sample** time, not `lastUpdated`. They differ by up to 4 min on 5-min feeds. |
| age | `age_at_capture_s` | Shown as "m s". The static page labels it "at capture" and adds a `RECORDED 23:30 CDT Fri 25 Sep` tag. It must never say LIVE. |
| cadence | `cadence_s` | "every 10 s", "every 5 min", "every 15 min", "hourly". |
| validity | `cim_validity` + `cim_flags` | e.g. "QUESTIONABLE (oldData)". The tooltip adds the ERCOT analogue (`ercot_quality_code_analogue`). |

Phone width: collapse to glyph + STATUS + age. Tap to expand to the full line. No horizontal scroll.

### 5.2 What happens when a feed goes stale (live mode or scrubbing)

Thresholds: `fresh_s` and `ttl_s` per feed come from `feeds[].rule`. The team's data-ingest targets are used where they exist; other thresholds are marked ASSUMPTION.

1. **ok → late** at `fresh_s`. The chip becomes outlined with a clock badge, and the age counter keeps ticking. The plot is unchanged.
2. **late → stale** at `ttl_s`. The chip is hatched and says STALE. The plotted line **stops at the last real sample**. A dashed, muted horizontal "hold" segment runs from there to "now", labelled *held, not measured*. This follows data-ingest's fill-by-hold rule. Never interpolate, never extrapolate. The panel's headline number greys out and shows "as of 23:23:20".
3. **Propagation.** A DERIVED number takes the worst status of its inputs (our rule). The "expected RoCoF for a 2,750 MW trip" KPI goes STALE with dc-tie-flows.
4. **Fallback** (data-ingest chain). For frequency, when `dc-tie-flows` is stale and `ancillary-services` is fresh, the live number switches source. The chip names the substitute ("from ancillary-services.json"). This is exactly the 23:30 situation.
5. **Frozen.** This applies only to noisy continuous fields: frequency and PRC, where `held_rule_false_alarm_free_today` is true. An identical value for > 180 s turns the chip to "‖ FROZEN since hh:mm:ss". Schedules, awards and inertia are exempt, because the calibration table shows they hold legitimately.
6. **Time went backwards.** If a response is older than one already shown, keep the newer one. Log "older copy ignored" in the credits drawer, and never let the line step back.
7. **Down.** The chip gets a red outline and a crossed circle and reads "no data since …". Offer a one-click switch to the recorded replay.
8. **Decision panels** (fleet dispatch) drop STALE inputs from the calculation and say so in words: "24 units excluded: STALE".

### 5.3 The dq panel itself: "Feed health board"

- **A. Board table:** one row per `ribbon[]` entry, with the chip expanded into columns: STATUS, feed, as of, age at capture, age range across snapshots, cadence, max-age, gaps today, coverage, revisions, validity. Sort by status severity. The dc-tie-flows row is the only non-OK row, and its caption reads: *"The 10-s frequency history arrives in batches, 2 to 7 minutes late; the 2-hour feed is fresher. We use it for the live number."*
- **B. Age dot plot:** one row per feed with a log x-axis in seconds (10 s to 2 h). Plot each snapshot's `age_newest_sample_s` as a dot, labelled with its fetch time on hover. Draw a tick at `fresh_s` and a heavier tick at `ttl_s`. Dots beyond the TTL are hollow and hatched.
- **C. "Is 'held for 180 s' a good stale test?"** A horizontal bar chart of `held_value_calibration.rows[].longest_identical_run_s` on a log x-axis, with a vertical line at 180 s. Bars are labelled with `runs_held_over_180s`. Two groups: *noisy analog* (frequency, PRC), where the rule works, and *scheduled or slow* (DC ties, inertia, AS awards), where it would false-alarm all day. Caption: *"On a normal day, a frozen value and a calm grid look identical for scheduled quantities; for frequency they never do."*
- **D. Two feeds, one quantity:** three small tiles.
  - Frequency: 684/684 identical.
  - Storage: a small line of median absolute difference against the implied ESR lag, 0–5 min (`storage_time_label_test.blend_scan.rows`). Its minimum sits at 2.5 min, labelled with `tile_label` ("ESR lags fuel-mix by ~2.5 min"). Put a dot at 0 min for "same label: 103.5 MW". Beneath it, one line from `publication_time_check`: "fuel-mix label 23:15 was already final at 23:19:06, so not interval-start". Never label this tile "interval-start".
  - PRC: 8,630 vs 8,627.
  Caption: *"Redundancy is what lets an estimator catch a bad value. The public feeds give us three such pairs."*
- **E. 24-h coverage strip** (`bins15`): 96 cells per feed, shaded by coverage and hatched by held fraction. On 25 Sep every cell is complete, so show the strip small with the caption "a clean day". It exists so a bad day is visible.

### 5.4 SIM panels (violet SIM chip)

**F. "When 24 batteries go quiet"** (`sim.comms_loss.runs.aware.timeline_10s`, with a toggle to `naive`). X is seconds since the link dropped, 0–300. Y is the Cedar cohort in "kW discharging" (negate the values). Lines, all as steps:
- **Truth, device idles at expiry:** solid ink, 345 → 0 at 30 s.
- **Truth, device holds its setpoint:** thin dashed ink, 345 → 0 at 180 s. Label it "if the device holds instead (UNVERIFIED which is true)".
- **Belief, hold-last forever:** warning ink, flat at 345, labelled "frozen feed read as live".
- **Belief, Base blank-after-180 s:** the same line, ending at 180 s, then a gap labelled "blanked".
- **Belief, PRD rule:** violet, 345 → 0 at 30 s.

Shade the area between the selected belief and the selected truth, and label it "phantom kW". Under the axis, draw a status strip: FRESH 0–10 s, SUSPECT 10–180 s, STALE > 180 s. Add ticks at 30 s ("command expires") and 60 s ("COMMS_LOST label"). On the right, two bullet bars on 0–100% from `confident_wrong_answer.unmetered_transformers`: **p1udt23656 believed 18% vs true 66%** and p1udt24321 believed 74% vs true 15%, with the tag "no meter on this transformer". Below them, a separate, smaller readout from `head_meter_residual`: "Feeder head (utility-metered): estimate 6.82 MW, meter 7.18 MW, residual +356 kW (5.0%). This residual would flag the stale cohort if the estimate were checked against the meter." Do **not** draw the feeder head as a believed-vs-true bullet: the head is metered, so a mismatch there is a detection, not a confident error. Caption: *"The estimate is a power flow on held values. Where a meter exists the error shows up as a residual. Where none exists, on service transformers, nothing contradicts it."*

**G. "Which belief rule is right?"** (`belief_error.by_rule_and_device_policy`) A 3 × 2 grid. Rows are hold-last forever, Base's blank-after-180 s, and the PRD belief. Columns are "device idles at expiry" and "device holds until 180 s". Each cell shows phantom kWh over 300 s, plus blank seconds where they apply. No row is zero in both columns. Under the "holds" column, add a note from S3 (`states.S3…meaning`): "PRD re-dispatch plus a holding device = +345 kW over the base point for 150 s (14.4 kWh, the same number as the PRD cell). A tracking and scoring error: no local limit moves (loading +0.001 pp vs before the loss, voltage −0.00003 pu vs the re-dispatch alone)." Do not attach 1.049 pu to the double dispatch. If the page shows the near-limit voltage, it belongs to S2: "re-dispatching onto the 72 fresh units raises the max voltage to 1.0493 pu" (`states.S2…max_voltage_note`). Caption: *"A belief rule is only as good as its device-behaviour assumption. This is the one question to ask Base."*

**H. Believed vs true, per transformer** (optional; `states.S0…transformers` vs `states.S1…transformers`). The 16 Cedar transformers as paired bars on 0–100%, sorted by error. Stress moves in both directions: backfed transformers look busier than they are, and the ones the batteries were relieving look idle.

**I. "The detector is a quality flag"** (`sim.detector.runs.aware`). X is sim clock 19:30–20:30 (13 steps); Y is residual RMS in kW (0–0.4). Draw a min–max band plus median line for the 24 Cedar units and another for the 72 others. Add a threshold line at 0.18 kW and a marker at 19:45 ("fictional modulation starts"). Underneath, a stacked strip of the Cedar units' GOOD / WATCH / SUSPECT / QUARANTINED counts per step, mapped to CIM as GOOD, GOOD (watch), QUESTIONABLE + `suspect`, and excluded (a control state). Add a toggle to `aware_quarantine`; the "fleet residual" readout drops to ±0.3 kW after 20:00. Annotate: "fixed 1 kW threshold: 0 flags all hour". Per-unit spaghetti from `unit_rms_kw` is optional.

**Interactions.** One hover model everywhere: the tooltip lists value, status tag and quality chip. A "Show quality" toggle overlays hatching on every stale or suspect segment across the page. Colour is never the only cue.

**Story role.** This is the trust layer of the site. Every other panel's numbers inherit their credibility from here. It also turns "data quality" from a footnote into the thing that decides whether a battery is counted, whether a transformer looks safe, and whether a covert attack shows up.

---

## 6. How it tells part of "the full story" for Base, and who at Base cares

- **Real-time dispatch and QSE operations.** Base's ADER telemetry reaches SCED over ICCP (Base blog). Base's own scoring chart blanks telemetry held more than 180 s. ERCOT measures telemetry availability as data passing with a Valid, Manual or Calculated code at the scheduled periodicity (§3.10.7.5.4, p. 3-181; the stated targets are for TSP and QSE telemetry). A held value that looks like a "flat dispatch" is a scoring and compliance problem before it is a physics one. Scale, as a restatement of the tolerance (`sim.comms_loss.scale_note`; DERIVED + ASSUMPTION): Base's scoring tolerance is 15% of capability (7.03/46.9). Suppose more than 15% of a fully discharging fleet goes silent, the devices idle, and their last values are held in the aggregate. Then the reported trace still looks on target while true delivery misses by more than the tolerance. Base's aggregate held-for-180 s rule would not catch it, because the aggregate is not flat. The miss would surface only after the fact, at settlement on premise meters (Base blog).
- **Fleet and orchestrator engineers.** The PRD's belief rules (FRESH/SUSPECT/STALE, command TTL, same-feeder replacement) are only as good as the device's real comms-loss behaviour, which is **UNVERIFIED** (the engineer said idle). The SIM shows the error each belief rule makes under each device behaviour (section 4). The single most valuable fact to get from Base is which device policy is true. If the device holds while the PRD re-dispatches, the SIM cost is +345 kW of over-delivery for 150 s against the base point, with no local limit moved (S3).
- **Distribution and utility partners.** A stale "discharging" value hides service-transformer stress that no one meters in real time (p1udt23656: 18% believed, 66% true). The utility's feeder-head meter would see the aggregate gap (+356 kW) but cannot say where it is. Base's oldData flags can: they name the silent units (SIM, section 4).
- **Security.** The first place a covert modulation shows up is a quality flag. It surfaces as a residual that is small, correlated and physically corroborated, not a big number. A fixed 1 kW threshold never fires (SIM detector).
- **Market and analytics.** The public feeds are clean on a normal day: 0 gaps and 0 revisions. They still have traps: time-label semantics differ between two 5-min feeds, frequency history lags by up to 7 min, a CDN can hand back an older file, and forecast rows are mixed in with actuals. Any model trained on these feeds inherits those traps silently.

---

## 7. Caveats

- One normal day (25 Sep 2026, EEA 0, no scarcity) and 2–5 snapshots per feed. Age ranges are observations, not a distribution. The 20:13 snapshots' fetch time is file mtime (approximate).
- ERCOT's dashboards expose no quality codes. Every validity label for REAL feeds is ours, mapped to CIM and ERCOT vocabulary through the crosswalk. The thresholds come from the team's data-ingest design where it gives them; the others are ASSUMPTION and say so in `feeds[].rule.source`.
- The storage time-label result is an inference from one day. Publication times rule out interval-start labelling for fuel-mix, ESR and supply-demand. The relative ESR-vs-fuel-mix lag (~2.5 min) comes from a blend scan, not from any ERCOT documentation, and the absolute meaning of each label is not determinable from these feeds.
- The CDN "time went backwards" event is one observation across two different items' fetches.
- ICCP flag names come from vendor documentation, not IEC 60870-6.
- The SIM "estimate" (S0) is idealised: every non-fleet load is known exactly and no measurement is in the loop. It is a stand-in for an aggregator's model-based view, not a state estimator. The head-meter residual is therefore exact in SIM. Real load-model error on this feeder is not available, so whether a 356 kW (5%) residual stands out in practice is not shown here.
- SIM thresholds (10 s FRESH, 30 s TTL, 60 s COMMS_LOST) are dossier ASSUMPTIONS. Only 180 s is sourced, and only as a rule for held aggregate telemetry. Device power on comms loss (0 kW) is UNVERIFIED. The silent cohort (Cedar) is a scripted choice.
- SIM network states in Part B are solved at OpenDSS convergence 1e-8. At the default 1e-4, the warm start moves max loading by up to 0.02 pp (`comms_loss.solver`), so any difference that small between two default-tolerance solves is noise, not physics. The replays (and Part A) use 1e-4.
- The comms-loss timeline is a step function on a 10 s grid. The 1.0 kWh in the "Base blank / device holds" cell is one 10 s step at the 180 s boundary: Base blanks only values held *more than* 180 s, while the HOLD_LAST device stops *at* 180 s. The S2 re-dispatch is instantaneous at expiry; the dossier's device start delay, U(0, 120 s), is not modelled, so S2 is the best case.
- The prototype detector is a benchmark on fictional ±0.35 kW modulation with seeded 45 W meter noise. It is not a WLS state estimator, and its thresholds were chosen, not calibrated.
- `mw:Provenance` is not a term we could find anywhere. We did not invent a standard to match it.

## 8. Reproduce

```
python3 site/ems/dq-build.py                                   # REAL part, offline, < 1 s
nice -n 10 <venv>/bin/python site/ems/dq-sim.py                # SIM part: about 156 OpenDSS solves (incl. the warm-start noise check),
                                                               # 1.4 s wall / 1.5 s CPU (measured 26 Sep 02:43 CDT), under the 20 s
                                                               # heavy-lock threshold; runs used ulimit -t 60
python3 site/ems/dq-build.py                                   # merge into dq-quality.json
```
`<venv>` needs OpenDSSDirect.py 0.9.4 and numpy (the team scratchpad venv). The source excerpts behind the claim verdicts are saved in `evidence/live-20260925/dq-src-excerpts.txt`, next to the full PDFs (`freq-nprotocols-20260302.pdf`, `dq-src-2003-blackout-final-report.pdf`).

---

## 9. Review responses (adversarial review, 26 Sep 2026)

All three findings were checked against the saved evidence and SIM before changing anything. All three hold. The fixes, with what we added or pushed back on:

1. **Premise 10, "fuel-mix labels by interval start": accepted; our verdict was wrong.** The evidence reproduces exactly. `evidence/live-20260925/load-fuel-mix.json` (HTTP `Date` 04:19:06Z, `lastUpdated` 23:16:00) already holds label 23:15 at −389.59 MW, and the 23:30 fetch has the same value. The 19:25:14 fetch has label 19:20 with `lastUpdated` 19:21:00, never revised. Our alignment numbers also reproduce (103.53 MW same-label, n = 282; 44.26 MW for the 0.5/0.5 blend, n = 281). Changes:
   - `cross_checks.publication_time_check` is new. It covers 11 snapshots of fuel-mix, ESR and supply-demand, and 5 of them prove by fetch time alone that label *t* existed before *t*+5 min.
   - `storage_time_label_test` now has a blend scan (best lag 2.5 min; 2.0–2.5 min within 10%), a rewritten inference and a `tile_label`.
   - Row 10 is now **holds with caveat** in both the spec and the returned verdicts. "questionable" is gone.
   - Tile D is relabelled.
   
   One addition to the reviewer's reading: because fuel-mix(*t*) is out by *t*+60 s, the 2.5 min lag also means ESR(*t*) describes a time at least about 1 min before its label. So our first inference was wrong on ESR as well: it had called ESR "instantaneous at its timestamp". The absolute meaning of each label still cannot be fixed from these feeds.
2. **Feeder-head MW as the "confident wrong answer": accepted.** The feeder head is the metered point. A +356 kW (5.0%) mismatch there is a residual that exposes the stale cohort, not a confident error. S0 is now labelled as the aggregator's model-based estimate with no feeder-head meter (`states.S0…label` → `comms_loss.notes.S0_label`). The message now rests on `confident_wrong_answer.unmetered_transformers` (p1udt23656, 18.1% vs 65.8%; 10 of 379 transformers off by more than 20 pp). `head_meter_residual` reports the +356.3 kW as the check that *would* flag it. Panel F no longer draws the head as a believed-vs-true bar. Three additions:
   - (a) We checked that the transformer error really is unobservable to the fleet: 0 of the 72 still-reporting units sit on any of the 16 Cedar transformers.
   - (b) The fleet does have one more redundancy channel. Still-reporting units see a feeder-wide voltage shift of up to 0.0071 pu (`reporting_unit_voltage_residual`), so a voltage-consistency check could notice that something changed upstream.
   - (c) The same head residual is 0 while a HOLD_LAST device is still discharging, so the meter also answers the device-policy question.
   
   Two limits we state rather than hide: the SIM load model is exact, so the residual is cleaner than a real one would be; and no limit is crossed in either state, so the error is in headroom.
3. **The 15% scale note: accepted.** It is rewritten with the reviewer's wording and the mechanism the right way round: the reported trace stays on target, and it is the true delivery that misses. It is tagged DERIVED + ASSUMPTION, and its three assumptions are listed. It is no longer a headline number; it appears as a restatement of Base's tolerance. We added two DERIVED facts from the same Base text and the prototype:
   - The CLREDP tolerance has a 2 MW floor, so the 15% share applies only above 13.33 MW of capability.
   - At prototype scale (1,920 kW of capability) the floor exceeds the whole silent contribution. The true miss of 362 kW would score as within tolerance.

### Round 2 (26 Sep 2026, after the first repair)

All three findings were re-checked against the files, the SIM and the protocols PDF. All three hold; nothing here pushes back on the substance. The fixes, and what we found beyond the reviewer's reading:

4. **The S3 "double dispatch" headline was misleading: accepted.** Re-solving the heat-wave aware step 12 states reproduces the finding.
   - The 99.5% transformer is **p1udt9411** (25 kVA). Its only 2 homes are Cedar units, and in S0 they discharge 39.3 kW against 19.4 kW of home load, so it is **backfed** at 99.49% before any loss. The aware splitter accepts a dispatch only up to 99.5% loading and scales it back otherwise (`sim/splitter.py`), so S0 sits at the splitter cap by design.
   - The 0.02 pp gap was **solver warm-start noise**. At the default 1e-4 convergence, over five warm starts, S0 ranged 99.49–99.50% and S3 99.49–99.51%; the 01:15 run's solve order produced 99.51% for S3. At 1e-8 both are 99.49% (99.4894 vs 99.4905, so +0.0011 pp). The reviewer saw S0 itself land on 99.51% in one run; we saw S0 reach 99.50% and S3 99.51%. The conclusion is the same. Part B now solves at 1e-8, and `comms_loss.solver` keeps the default-tolerance numbers and their ranges so the noise stays visible.
   - Max voltage: S0 1.04829, S1 1.04832, **S2 1.04933**, S3 1.04930 pu, all at fleet unit p1ulv5745. S2 is the PRD re-dispatch with the Cedar units idle and no double dispatch, so the near-1.05 pu voltage comes from re-dispatching onto the 72 fresh units: p1ulv5745 goes from −19.64 to −20.00 kW. S2 sits 0.00017 pu under the splitter's own 1.0495 pu acceptance cap.
   - Changes: `maxVoltage`, where the max loading and max voltage sit, and a backfeed flag are now on every state (S0–S3, both runs). S2 carries `max_voltage_note` and its margins. S3 is reported as deltas (`vs_S0`, `vs_S2`) with `over_delivery_kwh` = 14.39 kWh, and its `meaning` says plainly that it crosses no local limit and that its cost is tracking. Section 4 now has S0, S1, S2 and S3 rows plus a solver row. The panel G note is reworded. The naive run tells the same story: S3 max loading equals S0's (77.72%, +0.0000 pp), and S3 max voltage equals S2's +0.00002 pu.
   - Side effect of the tighter tolerance: the naive head-meter residual moves from 244.2 to **244.3 kW** (loss change 9.0 → 9.1 kW). Every aware headline is unchanged (18.11% vs 65.80% on p1udt23656; +356.3 kW; 4.96%).
5. **The returned result was stale: accepted.** Section 9 of the first repair said row 10 was fixed "in both the spec and the returned verdicts". The spec was fixed; the returned verdicts were not. This time the returned claim verdicts and headline numbers are regenerated from `dq-quality.json` and this spec. Specifically:
   - Row 10 now says fuel-mix is NOT interval-start (publication time) and ESR lags fuel-mix by about 2.5 min (INFERENCE, one day).
   - The storage headline reads "same label 103.5 vs 0.5/0.5 blend 44.3 MW".
   - The feeder-head headline is replaced by "unmetered transformer p1udt23656 believed 18.1% vs true 65.8% (SIM)". +356.3 kW (5.0%) is listed separately as the head-meter residual that would expose it.
   - The 15% share is gone from the headlines.
6. **Claim 4 understated ERCOT practice: accepted.** We verified each citation in the saved PDF and appended the excerpts to `evidence/live-20260925/dq-src-excerpts.txt`:
   - GTC definition, "for the purpose of managing stability, voltage, and other constraints". The heading is on p. 2-38 and the text on p. 2-39.
   - §3.10.7.6(1), p. 3-188: "system stability limits … shall be used in the SCED application".
   - We added the link the reviewer asserted but did not cite, the SE → NSA → SCED chain. §6.5.7.1.10(1), p. 6-47: "Using the input provided by the State Estimator, ERCOT shall use the NSA processor". §6.5.7.1.11(1), p. 6-49: NSA constraints, including GTLs, are activated in SCED.
   - The RUC point: §5.8(1)(e), p. 5-67 lists "RUC instructions issued for system inertia" as a reporting category, so the practice is confirmed. That ERCOT's inertia figure depends on telemetered unit status is not in the protocols we hold, so that part is marked **UNVERIFIED**.
   - Row 4 is reworded to the reviewer's text plus these sources. The verdict stays holds_with_caveat.
   - Page footers in the saved PDF carry per-section revision dates: February 1, 2026 for §2–3 and December 5, 2025 for §5–6. The file is ERCOT's March 2, 2026 compilation.
