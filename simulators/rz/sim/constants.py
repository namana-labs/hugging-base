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
                    "data/smartds (byte copy of demos/grid-stories/data/smartds @4bcca51), CC BY 4.0")
STAND_IN = const("STAND_IN", "Oncor-suburb stand-in settled at LZ_NORTH (placeholder)", "ASSUMPTION",
                 "CLAUDE.md non-negotiables; the real P1U buses sit in Pedernales Electric Cooperative territory "
                 "(PUCT service-area map, 2023, 'information purposes only'): 988 of 1,010 homes, 369 of 379 transformers, "
                 "93 of 96 fleet homes, A-D and T-240 (overnight/TEAMMATES_REVIEW.md #5)")
SOURCE_PU = const("SOURCE_PU", 1.03, "REAL", "SMART-DS Master.dss source pu")
FEEDER_KV = const("FEEDER_KV", 12.47, "REAL", "SMART-DS Master.dss basekV")
HEAD_LINE = const("HEAD_LINE", "l(r:p1udt17263-p1uhs19_1247)", "REAL",
                  "SMART-DS Lines.dss: the first primary cable (350 kcmil); site/ems/flow-spec.md")
HEAD_RATING_A = const("HEAD_RATING_A", 370.0, "REAL", "SMART-DS NormAmps of the head cable; site/ems/flow-spec.md")
HEAD_RATING_KVA = const("HEAD_RATING_KVA", round(370.0 * 3 ** 0.5 * 12.47, 1), "DERIVED",
                        "370 A x sqrt(3) x 12.47 kV; site/ems/flow-spec.md")
HEAD_RATING_KVA_PER_PHASE = const("HEAD_RATING_KVA_PER_PHASE", round(370.0 * 12.47 / 3 ** 0.5, 1), "DERIVED",
                                  "370 A x 7.2 kV line-to-neutral (12.47 kV / sqrt(3)): one conductor of the head cable; "
                                  "the 370 A limit binds per conductor (PR #19; overnight/AUDIT-R2.md L2)")
WEAK_LINE_FACTOR = const("WEAK_LINE_FACTOR", 3.0, "ASSUMPTION",
                         "prototype shaping: one primary line lengthened 3x electrically (data/fleet.json shaping)")
FLEET_SEED = const("FLEET_SEED", 17263, "ASSUMPTION", "prototype fleet placement seed (demos/grid-stories/sim/constants.py)")
FLEET_SIZE = const("FLEET_SIZE", 96, "ASSUMPTION", "prototype's 96-Core placement, frozen in data/fleet.json")

# ---- limits: three tiers, judged on OpenDSS loading (3.1) ---------------------
TIER_AMBER_PCT = const("TIER_AMBER_PCT", 100.0, "REAL", "SMART-DS kva nameplate; above it = over nameplate (amber), not a violation")
TIER_NORMAL_PCT = const("TIER_NORMAL_PCT", 110.0, "REAL", "SMART-DS normhkva = 1.1 x kva on all 379 transformers")
TIER_NORMAL_MIN = const("TIER_NORMAL_MIN", 30, "ASSUMPTION", "normal rating exceeded = above 110% for >= 30 consecutive minutes (build ruling 3.1)")
TIER_EMERGENCY_PCT = const("TIER_EMERGENCY_PCT", 150.0, "REAL", "SMART-DS EmergHKVA = 1.5 x kva on all 379 transformers")

# ---- protection (4.5): the team's round-1 rule, never tuned --------------------
FUSE_PCT = const("FUSE_PCT", 200.0, "ASSUMPTION", "docs/headroom/design/round1/world-sim.md 'Protection' paragraph")
FUSE_MINUTES = const("FUSE_MINUTES", 10, "ASSUMPTION", "docs/headroom/design/round1/world-sim.md 'Protection' paragraph")
FUSE_INSTANT_PCT = const("FUSE_INSTANT_PCT", 300.0, "ASSUMPTION", "docs/headroom/design/round1/world-sim.md 'Protection' paragraph")
FUSE_INSTANT_SECONDS = const("FUSE_INSTANT_SECONDS", 60, "ASSUMPTION", "docs/headroom/design/round1/world-sim.md 'Protection' paragraph")

# ---- devices ------------------------------------------------------------------
CORE_POWER_KW = const("CORE_POWER_KW", 20.0, "REAL", "Base Core spec, 20 kW continuous (four-home-simulation/four_home_constants.py)")
CORE_USABLE_KWH = const("CORE_USABLE_KWH", 37.0, "ASSUMPTION", "39.2 kWh nameplate; usable unpublished (four_home_constants.py)")
CORE_RTE = const("CORE_RTE", 0.89, "ASSUMPTION", "round-trip efficiency unpublished (four_home_constants.py)")
LEGACY_POWER_KW = const("LEGACY_POWER_KW", 11.4, "REAL", "legacy ground mount, 11.4 kW inverter (four_home_constants.py)")
LEGACY_USABLE_KWH = const("LEGACY_USABLE_KWH", 22.5, "ASSUMPTION", "unverified: Growatt APX inference, 90% of 25 kWh (four_home_constants.py)")
LEGACY_RTE = const("LEGACY_RTE", 0.88, "ASSUMPTION", "round-trip efficiency unpublished (four_home_constants.py)")
RESERVE_FLOOR = const("RESERVE_FLOOR", 0.20, "REAL", "20% member backup reserve (CLAUDE.md; four_home_constants.py)")
SOC0 = const("SOC0", 0.90, "ASSUMPTION", "P1 state of charge at 16:00 (build prompt 5.4.1)")
BATTERY_PF = const("BATTERY_PF", 1.0, "ASSUMPTION", "inverter at unity power factor; fixes the prototype's default 0.88 pf (build prompt 4.4)")

# ---- controller (5.4.3) ---------------------------------------------------------
AWARE_MARGIN = const("AWARE_MARGIN", 0.95, "ASSUMPTION", "four-home-simulation/four_home_constants.py")
CHARGE_URGENCY = const("CHARGE_URGENCY", 1.2, "ASSUMPTION", "build prompt 5.4.3 step 5")
MIN_DWELL_MIN = const("MIN_DWELL_MIN", 5, "ASSUMPTION", "build prompt 5.4.3 step 5")
SOC_BUCKET = const("SOC_BUCKET", 0.02, "ASSUMPTION", "grant order: floor(SoC / 0.02), then id (build prompt 5.4.3)")
MIN_GRANT_KW = const("MIN_GRANT_KW", 0.5, "ASSUMPTION", "a grant below 0.5 kW becomes 0; 0.5 kW hysteresis (build prompt 5.4.3)")
FLIP_MIN = const("FLIP_MIN", 5, "ASSUMPTION", "at most one charge<->discharge flip per 5 minutes (build prompt 5.4.3)")
COMMAND_TTL_S = const("COMMAND_TTL_S", 300, "ASSUMPTION", "command expiry; §12 Q4")
COMMS_STALE_S = const("COMMS_STALE_S", 180, "ASSUMPTION", "silent unit marked stale; §12 Q4 (prototype COMMS_STALE_SECONDS)")
CONTROLLER_VIEW = const("CONTROLLER_VIEW", "total transformer load, 60 s lag", "ASSUMPTION",
                        "needs a utility meter-to-transformer map; §12 Q4")

# ---- P1 scenario (5.4) -------------------------------------------------------------
P1_DAY = const("P1_DAY", "2026-08-23", "ASSUMPTION", "the P1 evening; 2018 SMART-DS load paired by calendar date")
P1_START = const("P1_START", "16:00", "ASSUMPTION", "P1 window start, local")
P1_STEPS = const("P1_STEPS", 720, "ASSUMPTION", "16:00 -> 04:00 at 60 s")
P1_STEP_SECONDS = const("P1_STEP_SECONDS", 60, "ASSUMPTION", "P1 step")
P1_CHARGE_DEADLINE = const("P1_CHARGE_DEADLINE", "04:00", "ASSUMPTION", "P1 charge window end")
FAULT_COMMS_AFTER_MIN = const("FAULT_COMMS_AFTER_MIN", 15, "ASSUMPTION", "comms loss at Tc + 15 (build prompt 5.4.4)")
FAULT_HOT_AFTER_MIN = const("FAULT_HOT_AFTER_MIN", 35, "ASSUMPTION", "C runs hot at Tc + 35 (build prompt 5.4.4)")
FAULT_STALL_AFTER_MIN = const("FAULT_STALL_AFTER_MIN", 55, "ASSUMPTION", "controller stall at Tc + 55 (build prompt 5.4.4)")
EV_KW = const("EV_KW", 7.2, "ASSUMPTION", "a Level 2 EV (build prompt 5.4.4)")
HOT_MINUTES = const("HOT_MINUTES", 60, "ASSUMPTION", "C runs hot for 60 minutes (build prompt 5.4.4)")
STALL_MIN = const("STALL_MIN", 8, "ASSUMPTION", "controller stall, longer than the TTL (build prompt 5.4.4)")

# ---- prices (4.3) ---------------------------------------------------------------------
PRICE_ZONE = const("PRICE_ZONE", "LZ_NORTH", "REAL", "ERCOT RTM settlement point prices, 15-min (data/ercot/SOURCE.md)")
PRICES_SHA256 = const("PRICES_SHA256", "0487b9d106ac422beee40bd287b9f0bd3ff938b3660b91700c346bccc25cde05", "REAL",
                      "sha256 of the source rtm2026_lz.csv (data/ercot/SOURCE.md)")
ONSET_MEDIAN_MULT = const("ONSET_MEDIAN_MULT", 2.0, "ASSUMPTION", "D-26: charge onset at or below 2 x day median (four_home_constants.py)")
ONSET_EVENING_FROM = const("ONSET_EVENING_FROM", "17:00", "ASSUMPTION", "D-26 evening peak searched from 17:00 (build prompt 4.3)")
ONSET_SEARCH_UNTIL = const("ONSET_SEARCH_UNTIL", "06:00", "ASSUMPTION", "D-26 search runs across midnight to 06:00 next day (build prompt 4.3)")
CLIFF_MIN_PRICE = const("CLIFF_MIN_PRICE", 60.0, "ASSUMPTION", "price cliff: prev >= $60 (build prompt 4.3)")
CLIFF_DROP_FRAC = const("CLIFF_DROP_FRAC", 0.5, "ASSUMPTION", "price cliff: next <= 0.5 x prev (build prompt 4.3)")
CLIFF_EVENING_FROM = const("CLIFF_EVENING_FROM", "20:00", "ASSUMPTION", "evening cliff: later interval starts 20:00-23:59 (build prompt 4.3)")

# ---- loads ------------------------------------------------------------------------------
LOAD_PAIRING = const("LOAD_PAIRING", "2018 SMART-DS weather-year load paired with 2026 prices by calendar date", "ASSUMPTION",
                     "build prompt 4.2; §12 Q9")
PROFILE_INDEX_RULE = const("PROFILE_INDEX_RULE", "profile index k = interval starting k x 15 min local time; DST unverified", "ASSUMPTION",
                           "build prompt 4.2; §12 Q8")

# ---- money (5.4.6): cites only, never invented ------------------------------------------
CAPACITY_BENCHMARK_USD_KW_MONTH = const("CAPACITY_BENCHMARK_USD_KW_MONTH", 3.12, "REAL",
                                        "Modo Apr 2026 ERCOT storage market benchmark (third party); docs/headroom/research_notes/grid_physics_orchestration_and_attacks.md:229")
CAPACITY_HIGH_USD_KW_MONTH = const("CAPACITY_HIGH_USD_KW_MONTH", 8.50, "DERIVED",
                                   "implied from an UNVERIFIED Austin Energy figure; docs/research-report.md:246, docs/design.md:160-161")
MARKET_BENCHMARK_USD_DAY = const("MARKET_BENCHMARK_USD_DAY", 1.58, "DERIVED", "docs/research-report.md:246")
BASE_HOUSTON_CHARGE_BLOCK_MW = const("BASE_HOUSTON_CHARGE_BLOCK_MW", -45.8, "REAL",
                                     "Base's Houston charge block reached -45.8 MW within 15 minutes on 22 Jul 2026 "
                                     "(Base blog 'aggregated-ders-and-the-capacity-crunch'; docs/research-report.md:207-212, 297). "
                                     "Zone level, ERCOT's base point; wording limited to what both readings of the blog agree on")
TRANSFORMER_REPLACEMENT_USD = const("TRANSFORMER_REPLACEMENT_USD", None, "ASSUMPTION", "not sourced; never invent one (§12 Q7)")

# ---- P2 (5.6) -------------------------------------------------------------------------------
P2_MONTH = const("P2_MONTH", "2026-08", "ASSUMPTION", "the P2 month")
P2_STEPS = const("P2_STEPS", 2976, "ASSUMPTION", "August at 15 min; the npz carries 3,000 steps so the 31 Aug night charges to 06:00")
CURTAIL_CAP = const("CURTAIL_CAP", 0.10, "ASSUMPTION", "useful capacity stops above 10% curtailment under aware (build prompt 5.6)")
GROWTH = const("GROWTH", 0.20, "ASSUMPTION", "+20% load growth: EVs and heat pumps (build prompt 5.6)")
FOOTPRINT_MISSING_M = const("FOOTPRINT_MISSING_M", 12.0, "ASSUMPTION", "a home with no OSM footprint is drawn as a 12 m square")

# ---- budget of ui/data (5.3) ----------------------------------------------------------------
DATA_BUDGET_MB = const("DATA_BUDGET_MB", 25.0, "ASSUMPTION", "all of ui/data (build prompt 5.3)")
DATA_FILE_CAP_MB = const("DATA_FILE_CAP_MB", 4.0, "ASSUMPTION", "per file in ui/data (build prompt 5.3)")

# ---- the focus street and the P2 bridge (4.1): keyed by id, never by index ------------
FOCUS_TFS = const("FOCUS_TFS", {"A": "tr(r:p1udt9411-p1udt9411lv)", "B": "tr(r:p1udt23656-p1udt23656lv)",
                                "C": "tr(r:p1udt16141-p1udt16141lv)", "D": "tr(r:p1udt9796-p1udt9796lv)"},
                  "ASSUMPTION", "focus street A-D chosen by the planning round (ids REAL, SMART-DS); build prompt 4.1")
BRIDGE_TF = const("BRIDGE_TF", "tr(r:p1udt15649-p1udt15649lv)", "ASSUMPTION",
                  "the P2 bridge transformer (id REAL, SMART-DS; 25 kVA, no battery); build prompt 4.1")
