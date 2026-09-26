"""Single source of truth for every assumption (docs/design.md §10).

Every value carries its label from the research report: SOURCED, DERIVED,
ASSUMPTION or UNVERIFIED. Keep the labels; an on-site answer changes one line.
"""

STEP_MINUTES = 5  # SOURCED: one SCED interval

# Devices (design.md §5.1). Only the Core class is exercised.
CORE_POWER_KW = 20.0  # SOURCED
CORE_USABLE_KWH = 37.0  # ASSUMPTION
CORE_ROUND_TRIP_EFFICIENCY = 0.89  # ASSUMPTION
RESERVE_FLOOR = 0.20  # SOURCED: 20 % member reserve, hard constraint
COMMS_STALE_SECONDS = 180  # UNVERIFIED
COMMS_LOSS_POWER_KW = 0.0  # UNVERIFIED: power = 0, backup armed
COMMAND_EXPIRY_STEPS = 1  # ASSUMPTION: one 5-minute interval
BACKUP_SOC_FLOOR = 0.05  # ASSUMPTION: inverter cut-off while islanded; the 20 % reserve is spent on backup

# Feeder referee (design.md §5.2). Transformer limit is nameplate kVA, three tiers.
VOLTAGE_MIN_PU = 0.95  # SOURCED: ANSI C84.1 Range A
VOLTAGE_MAX_PU = 1.05  # SOURCED: ANSI C84.1 Range A
TIER_NAMEPLATE_PCT = 100.0  # SOURCED: SMART-DS kva
TIER_NORMAL_PCT = 110.0  # SOURCED: SMART-DS normhkva
TIER_EMERGENCY_PCT = 150.0  # SOURCED: SMART-DS emerghkva
SUSTAINED_WINDOW_MINUTES = 30  # ASSUMPTION: >110 % for this long is the headline violation
SOURCE_PU = 1.03  # SOURCED: SMART-DS circuit source setting

# Controller view (design.md §5.5). Conservative on purpose; OpenDSS decides.
CONTROLLER_HEADROOM_MARGIN = 0.98  # ASSUMPTION: fill transformers to 98 % of nameplate
SPLITTER_START_JITTER_SECONDS = 120  # ASSUMPTION; not yet exercised

# Market (design.md §5.3)
MARKET_TOLERANCE_KW = 2000.0  # SOURCED: max(2 MW, 15 %)
MARKET_TOLERANCE_FRACTION = 0.15  # SOURCED
MARKET_BENCHMARK_DOLLARS_DAY = 1.58  # DERIVED, flat within the load zone

# Lateral topology (sim/feeder.py:lateral). The city size is `n_nodes`; four is the
# instance we run today. All ASSUMPTION unless noted.
FOUR_NODE_TRANSFORMER_KVA = 25.0  # SOURCED: standard SMART-DS nameplate, ~2.5 homes
FOUR_NODE_NODE_LOAD_KW = 7.5  # ASSUMPTION: two homes on the transformer at ~3.75 kW each, hot evening peak
FOUR_NODE_POWER_FACTOR = 0.95  # ASSUMPTION
FOUR_NODE_PRIMARY_KM = (0.4, 0.6, 0.8, 1.2)  # ASSUMPTION: segment lengths sub->n1->n2->n3->n4
FOUR_NODE_SERVICE_M = (20.0, 30.0, 40.0, 90.0)  # ASSUMPTION: n4 has the long service drop
FOUR_NODE_SOURCE_PU = SOURCE_PU
LATERAL_SEGMENT_KM = 0.6  # ASSUMPTION: primary segment for nodes beyond the four-node pattern
LATERAL_SERVICE_M = 30.0  # ASSUMPTION: service drop for nodes beyond the four-node pattern
DEFAULT_NODES = 4  # the city size we run today; raise it when the lateral is proven

# Rooftop solar (one aggregate PV per node, same bus as the home load)
PV_KW_PER_NODE = 7.5  # ASSUMPTION: ~2.5 homes at ~40 % rooftop penetration of ~7 kW systems

# Reactive power (design-handoff README, Reactive power card)
CAP_BANK_KVAR_PER_NODE = 1.5  # ASSUMPTION: one switched bank mid-lateral, sized to the nodes it serves
CAP_BANK_ON_KVAR_PER_NODE = 1.75  # ASSUMPTION: close the bank when feeder-head demand passes this
CAP_BANK_OFF_KVAR_PER_NODE = 1.0  # ASSUMPTION: open it again below this (hysteresis)
INVERTER_KVAR_FRACTION = 0.44  # SOURCED: IEEE 1547-2018 Category B, 44 % of nameplate injection/absorption
VOLT_VAR_INJECT_START_PU = 0.98  # SOURCED: IEEE 1547-2018 Cat B default volt-var V2
VOLT_VAR_INJECT_FULL_PU = 0.92  # SOURCED: IEEE 1547-2018 Cat B default volt-var V1
VOLT_VAR_ABSORB_START_PU = 1.02  # SOURCED: IEEE 1547-2018 Cat B default volt-var V3
VOLT_VAR_ABSORB_FULL_PU = 1.08  # SOURCED: IEEE 1547-2018 Cat B default volt-var V4

# Day scenario (sim/scenarios/day.py). Every curve is scripted; none is ERCOT or AMI data.
DAY_STEPS = 24 * 60 // STEP_MINUTES  # 288
DAY_INITIAL_SOC = 0.40  # ASSUMPTION: "the fleet holds about 40 % at night" (handoff story line)
DAY_CHEAP_PRICE = 20.0  # $/MWh ASSUMPTION: at or below this the fleet tops up slowly
DAY_DISCHARGE_PRICE = 100.0  # $/MWh ASSUMPTION: at or above this the fleet discharges
DAY_OVERNIGHT_CHARGE_FRACTION = 0.05  # ASSUMPTION: "batteries top up slowly" overnight, ~+13 % of fleet energy by 06:00
DAY_PEAK_DISCHARGE_FRACTION = 0.35  # ASSUMPTION: spread the stored energy across the 17:00-21:00 price window
DAY_PEAK_LOAD_FACTOR = 1.0  # ASSUMPTION: the evening peak equals FOUR_NODE_NODE_LOAD_KW; raise for a hotter day
# Hourly price, $/MWh, index = hour. ASSUMPTION: illustrative LZ_NORTH-like shape, not ERCOT data.
DAY_PRICE_BY_HOUR = (18, 18, 18, 18, 18, 18, 28, 40, 40, 12, 12, 12, 12, 12, 12, 12, 45, 145, 145, 145, 145, 60, 25, 25)

SEED = 17263
