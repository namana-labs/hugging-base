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

# Four-node test topology (sim/feeder.py:four_node). All ASSUMPTION unless noted.
FOUR_NODE_TRANSFORMER_KVA = 25.0  # SOURCED: standard SMART-DS nameplate, ~2.5 homes
FOUR_NODE_NODE_LOAD_KW = 7.5  # ASSUMPTION: two homes on the transformer at ~3.75 kW each, hot evening
FOUR_NODE_POWER_FACTOR = 0.95  # ASSUMPTION
FOUR_NODE_PRIMARY_KM = (0.4, 0.6, 0.8, 1.2)  # ASSUMPTION: segment lengths sub->n1->n2->n3->n4
FOUR_NODE_SERVICE_M = (20.0, 30.0, 40.0, 90.0)  # ASSUMPTION: n4 has the long service drop
FOUR_NODE_SOURCE_PU = SOURCE_PU

SEED = 17263
