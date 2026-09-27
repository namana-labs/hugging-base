"""Every named constant of the root simulator, with its honesty label and a cite.

One name per value. `const()` records the value in `TAG`, and every JSON the
simulator writes exports the constants it used (see `export()`), so a number on
screen can always be traced to its label and source.

Labels (OVERNIGHT_BUILD_PROMPT.md 3.4):
  REAL        ERCOT prices; SMART-DS topology, kVA and ratings; OSM footprints; sourced programme facts
  SIM         our simulation's output
  DERIVED     arithmetic on REAL or SIM
  ASSUMPTION  a named constant we chose (four-home's UNVERIFIED maps here, with "unverified" kept in the cite)

Sign convention: positive kW = charging / consumption (as demos/grid-stories devices.py).
"""

LABELS = ("REAL", "SIM", "DERIVED", "ASSUMPTION")
TAG = {}


def const(name, value, label, cite):
    """Register a named constant. Returns the value so modules can bind it."""
    if label not in LABELS:
        raise ValueError(f"{name}: label {label!r} not in {LABELS}")
    if not cite:
        raise ValueError(f"{name}: a cite is required")
    if name in TAG and TAG[name]["value"] != value:
        raise ValueError(f"{name}: redefined with a different value")
    TAG[name] = {"value": value, "label": label, "cite": cite}
    return value


def export(*names):
    """The `constants` block of the JSON envelope: every named constant, or the ones named."""
    keys = names or sorted(TAG)
    return {k: dict(TAG[k]) for k in keys}


# ---- feeder -------------------------------------------------------------------
FEEDER_NAME = const("FEEDER_NAME", "NREL SMART-DS 2018 AUS P1U p1uhs19_1247--p1udt17263", "REAL",
                    "REAL dataset, synthetic feeder: NREL's published SMART-DS files, byte-identical to OEDI "
                    "(data/smartds, CC BY 4.0). NREL calls SMART-DS 'realistic but not real' "
                    "(https://www.nlr.gov/grid/smart-ds.html): a synthetic, statistically realistic Austin feeder, "
                    "not a utility circuit (https://data.openei.org/submissions/2981)")
STAND_IN = const("STAND_IN", "Oncor-suburb stand-in settled at LZ_NORTH (placeholder)", "ASSUMPTION",
                 "CLAUDE.md non-negotiables. The synthetic feeder is drawn on NW-Austin coordinates that fall in "
                 "Pedernales Electric Cooperative territory (PUCT service-area layers, 2023, marked 'UNOFFICIAL', "
                 "'information purposes only'; https://services6.arcgis.com/N6Lzvtb46cpxThhu/arcgis/rest/services/"
                 "COOP_DIST/FeatureServer/310): 988 of 1,010 customers, 369 of 379 transformers, 93 of 96 fleet homes, "
                 "A-D and T-240. 'Oncor suburb' is a framing label, not the real utility")
SOURCE_PU = const("SOURCE_PU", 1.03, "REAL", "SMART-DS Master.dss source pu")
FEEDER_KV = const("FEEDER_KV", 12.47, "REAL", "SMART-DS Master.dss basekV")
HEAD_LINE = const("HEAD_LINE", "l(r:p1udt17263-p1uhs19_1247)", "REAL",
                  "SMART-DS data/smartds/Lines.dss:3587: the first primary cable, linecode 3P_UG_AL_350kcmil_3")
HEAD_RATING_A = const("HEAD_RATING_A", 370.0, "REAL", "SMART-DS normamps=370.0 of the head cable (data/smartds/LineCodes.dss:19)")
HEAD_RATING_KVA = const("HEAD_RATING_KVA", round(370.0 * 3 ** 0.5 * 12.47, 1), "DERIVED",
                        "370 A x sqrt(3) x 12.47 kV, the balanced three-phase rating of the head cable (data/smartds/LineCodes.dss:19)")
HEAD_RATING_KVA_PER_PHASE = const("HEAD_RATING_KVA_PER_PHASE", round(370.0 * 12.47 / 3 ** 0.5, 1), "DERIVED",
                                  "370 A x 7.2 kV line-to-neutral (12.47 kV / sqrt(3)): one conductor of the head cable, "
                                  "not the whole feeder (the feeder head's three-phase rating is HEAD_RATING_KVA, 7,991.5 kVA); "
                                  "the 370 A limit binds per conductor (PR #19; data-truth audit 26 Sep 2026)")
WEAK_LINE_FACTOR = const("WEAK_LINE_FACTOR", 3.0, "ASSUMPTION",
                         "prototype shaping: one primary line lengthened 3x electrically (data/fleet.json shaping)")
FLEET_SEED = const("FLEET_SEED", 17263, "ASSUMPTION", "prototype fleet placement seed (demos/grid-stories/sim/constants.py)")
FLEET_SIZE = const("FLEET_SIZE", 96, "ASSUMPTION",
                   "a deliberate stress placement, frozen in data/fleet.json: 24 batteries clustered on purpose on the densest "
                   "homes near one centre (all 9 on A-D) + 72 random (demos/grid-stories/sim/build_replays.py:25-30); "
                   "96 on 1,010 customers is 9.5% penetration (DERIVED), against Base's projected 1-2% of homes a year "
                   "in CoServ territory (pv magazine, 9 Mar 2026)")

# ---- limits: three tiers, judged on OpenDSS loading (3.1) ---------------------
TIER_AMBER_PCT = const("TIER_AMBER_PCT", 100.0, "REAL", "SMART-DS kva nameplate; above it = over nameplate (amber), not a violation")
TIER_NORMAL_PCT = const("TIER_NORMAL_PCT", 110.0, "REAL", "SMART-DS normhkva = 1.1 x kva on all 379 transformers: "
                                                            "SMART-DS's modelled rating (a uniform default of the synthetic dataset), not a utility nameplate")
TIER_NORMAL_MIN = const("TIER_NORMAL_MIN", 30, "ASSUMPTION", "normal rating exceeded = above 110% for >= 30 consecutive minutes (build ruling 3.1)")
TIER_EMERGENCY_PCT = const("TIER_EMERGENCY_PCT", 150.0, "REAL", "SMART-DS EmergHKVA = 1.5 x kva on all 379 transformers: "
                                                                  "SMART-DS's modelled rating (a uniform default of the synthetic dataset), not a utility nameplate")

# ---- protection (4.5): the team's round-1 rule, never tuned --------------------
FUSE_PCT = const("FUSE_PCT", 200.0, "ASSUMPTION", "docs/headroom/design/round1/world-sim.md 'Protection' paragraph; "
                                                    "stays ASSUMPTION (RZ ruling, 26 Sep 2026): no sourced fuse curve")
FUSE_MINUTES = const("FUSE_MINUTES", 10, "ASSUMPTION", "docs/headroom/design/round1/world-sim.md 'Protection' paragraph")
FUSE_INSTANT_PCT = const("FUSE_INSTANT_PCT", 300.0, "ASSUMPTION", "docs/headroom/design/round1/world-sim.md 'Protection' paragraph")
FUSE_INSTANT_SECONDS = const("FUSE_INSTANT_SECONDS", 60, "ASSUMPTION", "docs/headroom/design/round1/world-sim.md 'Protection' paragraph")

# ---- devices ------------------------------------------------------------------
CORE_POWER_KW = const("CORE_POWER_KW", 20.0, "REAL", "Base Core '(20 kW / 39.2 kWh)': https://www.basepowercompany.com/utilities")
CORE_USABLE_KWH = const("CORE_USABLE_KWH", 37.0, "ASSUMPTION", "39.2 kWh nameplate; usable unpublished (four_home_constants.py)")
CORE_RTE = const("CORE_RTE", 0.89, "ASSUMPTION", "round-trip efficiency unpublished (four_home_constants.py)")
LEGACY_POWER_KW = const("LEGACY_POWER_KW", 11.4, "REAL", "legacy ground mount, 11.4 kW: https://www.basepowercompany.com/specs/ground-mounted "
                                                          "(docs/research-report.md:98)")
LEGACY_USABLE_KWH = const("LEGACY_USABLE_KWH", 22.5, "ASSUMPTION", "unverified: Growatt APX inference, 90% of 25 kWh (four_home_constants.py)")
LEGACY_RTE = const("LEGACY_RTE", 0.88, "ASSUMPTION", "round-trip efficiency unpublished (four_home_constants.py)")
RESERVE_FLOOR = const("RESERVE_FLOOR", 0.20, "REAL", "20% member backup reserve: https://www.basepowercompany.com/blog/base-battery-guide; "
                                                      "https://www.basepowercompany.com/blog/how-base-charges-and-discharges-its-batteries "
                                                      "('aims to reserve at least 20%'); a hard constraint in every scenario (CLAUDE.md)")
SOC0 = const("SOC0", 0.90, "ASSUMPTION", "P1 state of charge at 16:00: our choice; Base says batteries rarely fall below 50% "
                                            "(how-base-charges-and-discharges-its-batteries)")
BATTERY_PF = const("BATTERY_PF", 1.0, "ASSUMPTION", "inverter at unity power factor, our choice; fixes the prototype's OpenDSS default 0.88 pf, "
                                                      "which overstated battery loading")

# ---- controller (5.4.3) ---------------------------------------------------------
AWARE_MARGIN = const("AWARE_MARGIN", 0.95, "ASSUMPTION", "four-home-simulation/four_home_constants.py")
CHARGE_URGENCY = const("CHARGE_URGENCY", 1.2, "ASSUMPTION", "controller design choice: charge at 1.2 x the rate that just meets the deadline")
MIN_DWELL_MIN = const("MIN_DWELL_MIN", 5, "ASSUMPTION", "controller design choice: a grant holds at least 5 minutes, so batteries do not chatter")
SOC_BUCKET = const("SOC_BUCKET", 0.02, "ASSUMPTION", "controller design choice: grant order floor(SoC / 0.02), then id (deterministic)")
MIN_GRANT_KW = const("MIN_GRANT_KW", 0.5, "ASSUMPTION", "controller design choice: a grant below 0.5 kW becomes 0; 0.5 kW hysteresis")
FLIP_MIN = const("FLIP_MIN", 5, "ASSUMPTION", "controller design choice: at most one charge<->discharge flip per 5 minutes")
COMMS_LOSS_BEHAVIOUR = const("COMMS_LOSS_BEHAVIOUR",
                              "a battery that loses its connection idles in backup-only mode: it does not charge, never "
                              "discharges to the grid, and only backs up its own home in an outage", "REAL",
                              "Base engineer, on site, 26 Sep 2026 (verbal). The behaviour only; the timings below stay ASSUMPTION "
                              "(sim/devices.py idles with backup armed at command expiry)")
COMMAND_TTL_S = const("COMMAND_TTL_S", 300, "ASSUMPTION", "command expiry, our timing (the idle-with-backup behaviour at expiry is REAL: "
                                                          "COMMS_LOSS_BEHAVIOUR; the 300 s is not sourced)")
COMMS_STALE_S = const("COMMS_STALE_S", 180, "ASSUMPTION", "silent unit marked stale, our timing (prototype COMMS_STALE_SECONDS); "
                                                          "Base's blog chart treats telemetry older than 180 s as stale, which is chart "
                                                          "scoring, not device behaviour")
CONTROLLER_VIEW = const("CONTROLLER_VIEW", "total transformer load, 60 s lag", "ASSUMPTION",
                        "our assumption of what the controller sees; it needs a utility meter-to-transformer map")

# ---- P1 scenario (5.4) -------------------------------------------------------------
P1_DAY = const("P1_DAY", "2026-08-23", "ASSUMPTION", "the P1 evening; 2018 SMART-DS load paired by calendar date")
P1_START = const("P1_START", "16:00", "ASSUMPTION", "P1 window start, local")
P1_STEPS = const("P1_STEPS", 720, "ASSUMPTION", "16:00 -> 04:00 at 60 s")
P1_STEP_SECONDS = const("P1_STEP_SECONDS", 60, "ASSUMPTION", "P1 step")
P1_CHARGE_DEADLINE = const("P1_CHARGE_DEADLINE", "04:00", "ASSUMPTION", "P1 charge window end")
FAULT_COMMS_AFTER_MIN = const("FAULT_COMMS_AFTER_MIN", 15, "ASSUMPTION", "scripted fault story: comms loss at Tc + 15 (the timing is ours; "
                                                                          "what the silent battery then does is REAL, COMMS_LOSS_BEHAVIOUR)")
FAULT_HOT_AFTER_MIN = const("FAULT_HOT_AFTER_MIN", 35, "ASSUMPTION", "scripted fault story: C runs hot at Tc + 35")
FAULT_STALL_AFTER_MIN = const("FAULT_STALL_AFTER_MIN", 55, "ASSUMPTION", "scripted fault story: controller stall at Tc + 55")
EV_KW = const("EV_KW", 7.2, "ASSUMPTION", "scripted fault story: a Level 2 EV")
HOT_MINUTES = const("HOT_MINUTES", 60, "ASSUMPTION", "scripted fault story: C runs hot for 60 minutes")
STALL_MIN = const("STALL_MIN", 8, "ASSUMPTION", "scripted fault story: controller stall, longer than the command TTL")

# ---- prices (4.3) ---------------------------------------------------------------------
PRICE_ZONE = const("PRICE_ZONE", "LZ_NORTH", "ASSUMPTION", "placeholder zone for an Oncor-suburb stand-in; the prices of that zone are REAL "
                                                            "(ERCOT RTM settlement point prices, 15-min, settlement point type LZ; data/ercot/SOURCE.md)")
PRICES_SHA256 = const("PRICES_SHA256", "0487b9d106ac422beee40bd287b9f0bd3ff938b3660b91700c346bccc25cde05", "REAL",
                      "sha256 of the source rtm2026_lz.csv (data/ercot/SOURCE.md)")
ONSET_MEDIAN_MULT = const("ONSET_MEDIAN_MULT", 2.0, "ASSUMPTION", "D-26: charge onset at or below 2 x day median (four_home_constants.py)")
ONSET_EVENING_FROM = const("ONSET_EVENING_FROM", "17:00", "ASSUMPTION", "rule parameter: D-26 evening peak searched from 17:00")
ONSET_SEARCH_UNTIL = const("ONSET_SEARCH_UNTIL", "06:00", "ASSUMPTION", "rule parameter: D-26 search runs across midnight to 06:00 next day")
CLIFF_MIN_PRICE = const("CLIFF_MIN_PRICE", 60.0, "ASSUMPTION", "rule parameter: price cliff when prev >= $60")
CLIFF_DROP_FRAC = const("CLIFF_DROP_FRAC", 0.5, "ASSUMPTION", "rule parameter: price cliff when next <= 0.5 x prev")
CLIFF_EVENING_FROM = const("CLIFF_EVENING_FROM", "20:00", "ASSUMPTION", "rule parameter: evening cliff when the later interval starts 20:00-23:59")

# ---- loads ------------------------------------------------------------------------------
LOAD_PAIRING = const("LOAD_PAIRING", "2018 SMART-DS weather-year load paired with 2026 prices by calendar date", "ASSUMPTION",
                     "our pairing; it mixes weekdays: 22 Jul 2026 (Wed) uses Sun 22 Jul 2018, 14 Aug (Fri) uses Tue, "
                     "23 Aug (Sun) uses Thu, 26 Aug (Wed) uses Sun (docs/data-sources.md)")
PROFILE_INDEX_RULE = const("PROFILE_INDEX_RULE", "profile index k = interval starting k x 15 min local time; DST unverified", "ASSUMPTION",
                           "our reading of the index; the SMART-DS series has 35,040 values (365 x 96), so no DST shifts: if it is "
                           "standard time, August loads sit one hour early against the CDT prices (unverified)")

# ---- money (5.4.6): cites only, never invented ------------------------------------------
CAPACITY_BENCHMARK_USD_KW_MONTH = const("CAPACITY_BENCHMARK_USD_KW_MONTH", 3.12, "REAL",
                                        "Modo Apr 2026 ERCOT grid-scale storage revenue benchmark (energy + ancillary), "
                                        "not a capacity price (third party; "
                                        "https://modoenergy.com/research/en/ercot-battery-storage-2026-things-to-watch)")
CAPACITY_HIGH_USD_KW_MONTH = const("CAPACITY_HIGH_USD_KW_MONTH", 8.50, "DERIVED",
                                   "City of Austin Recommendation for Action, 23 Apr 2026: up to 40 MW 'in an estimated amount of "
                                   "up to $4,080,000 per year' (https://services.austintexas.gov/edims/document.cfm?id=471637); "
                                   "4,080,000 / (40,000 kW x 12) = $8.50/kW-month. An upper bound ('up to'), the city's estimate, "
                                   "not a published contract price")
MARKET_BENCHMARK_USD_DAY = const("MARKET_BENCHMARK_USD_DAY", 1.58, "DERIVED",
                                 "Modo trailing-year ERCOT storage revenue about $28,800/MW-yr x 0.020 MW / 365 = $1.58 a day for one Core "
                                 "(https://modoenergy.com/research/en/ercot-battery-storage-2026-things-to-watch)")
BASE_HOUSTON_CHARGE_BLOCK_MW = const("BASE_HOUSTON_CHARGE_BLOCK_MW", -45.8, "REAL",
                                     "the set point Base dispatched to its Houston partition (lz-houston-ader) went from 0 to -45.8 MW "
                                     "within 15 minutes (23:30-23:45 CT) on 22 Jul 2026; the fleet realized -44.7 MW. The blog table's "
                                     "column is 'Set point', not ERCOT's base point (Base blog "
                                     "https://www.basepowercompany.com/blog/aggregated-ders-and-the-capacity-crunch). Zone level")
TRANSFORMER_REPLACEMENT_USD = const("TRANSFORMER_REPLACEMENT_USD", None, "ASSUMPTION", "not sourced; never invent one")

# ---- P2 (5.6) -------------------------------------------------------------------------------
P2_MONTH = const("P2_MONTH", "2026-08", "ASSUMPTION", "the P2 month")
P2_STEPS = const("P2_STEPS", 2976, "ASSUMPTION", "August at 15 min; the npz carries 3,000 steps so the 31 Aug night charges to 06:00")
CURTAIL_CAP = const("CURTAIL_CAP", 0.10, "ASSUMPTION", "our rule: useful capacity stops above 10% curtailment under feeder-aware")
GROWTH = const("GROWTH", 0.20, "ASSUMPTION", "our scenario: +20% home-load growth (EVs and heat pumps)")
FOOTPRINT_MISSING_M = const("FOOTPRINT_MISSING_M", 12.0, "ASSUMPTION", "a home with no OSM footprint is drawn as a 12 m square")

# ---- budget of ui/data (5.3) ----------------------------------------------------------------
DATA_BUDGET_MB = const("DATA_BUDGET_MB", 40.0, "ASSUMPTION", "all of ui/data, an engineering budget; raised from 25 for the story "
                                                              "catalogue (26 Sep 2026 sprint ruling)")
DATA_FILE_CAP_MB = const("DATA_FILE_CAP_MB", 4.0, "ASSUMPTION", "per file in ui/data, an engineering budget")

# ---- the focus street and the P2 bridge (4.1): keyed by id, never by index ------------
FOCUS_TFS = const("FOCUS_TFS", {"A": "tr(r:p1udt9411-p1udt9411lv)", "B": "tr(r:p1udt23656-p1udt23656lv)",
                                "C": "tr(r:p1udt16141-p1udt16141lv)", "D": "tr(r:p1udt9796-p1udt9796lv)"},
                  "ASSUMPTION", "focus street A-D chosen by the planning round (ids REAL, SMART-DS); it is where the stress "
                                "placement is densest (FLEET_SIZE)")
BRIDGE_TF = const("BRIDGE_TF", "tr(r:p1udt15649-p1udt15649lv)", "ASSUMPTION",
                  "the P2 bridge transformer, chosen by the planning round (id REAL, SMART-DS; 25 kVA, no battery)")
