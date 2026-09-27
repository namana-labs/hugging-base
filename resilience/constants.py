"""Every named constant this folder adds, registered in sim.constants' one registry (`const()`), so each exported
file carries its value, label and cite exactly as the lanes' files do. Nothing here redefines a sim constant.
"""
from sim.constants import const

# ---- physics (B1) -------------------------------------------------------------------------------------------------
POWER_BALANCE_TOL_W = const("POWER_BALANCE_TOL_W", 10.0, "ASSUMPTION",
                            "four-home-simulation/test_four_home.py test_power_balance_closes_every_step: 10 W")
SOLVER_TOLERANCE = const("SOLVER_TOLERANCE", 1e-8, "ASSUMPTION",
                         "four-home-simulation/four_home.py 'Set tolerance=1e-8' (the OpenDSS default is 1e-4)")

# ---- the controller runtime (B2; docs/design.md §5.7) ---------------------------------------------------------------
LEASE_TTL_S = const("LEASE_TTL_S", 300, "ASSUMPTION",
                    "one 5-minute interval: docs/design.md §10 'Command expiry and lease TTL'")
RUNTIME_WORKERS = const("RUNTIME_WORKERS", 3, "ASSUMPTION", "'a few worker processes' (docs/design.md §5.7)")
RUNTIME_PARTITIONS = const("RUNTIME_PARTITIONS", 3, "ASSUMPTION", "one transformer group per worker at the start")
PARTITION_RULE = const("PARTITION_RULE",
                       "fleet transformers in index order, cut into RUNTIME_PARTITIONS contiguous groups of about equal "
                       "battery count; a transformer is never split", "ASSUMPTION", "resilience/runtime/partition.py")
SHARE_RULE = const("SHARE_RULE",
                   "each group gets its own batteries' share of the fleet target (the P1 formula per battery), capped "
                   "at the group's headroom (sim.caps H per transformer); the rest goes to groups with room left, in "
                   "proportion to that room. A group whose worker missed its last heartbeat is booked at its "
                   "batteries' telemetry kW", "ASSUMPTION", "resilience/runtime/partition.py")
KILL_AFTER_MIN = const("KILL_AFTER_MIN", 20, "ASSUMPTION",
                       "the worker holding focus A's group is killed at Tc + 20 min, mid-ramp (P1 aware charges about "
                       "590 kW then)")
LATE_BATCH_RULE = const("LATE_BATCH_RULE",
                        "the killed worker's last batch (computed at the kill step, never delivered) reaches the "
                        "devices late, right after the takeover's commands: 'a dead or paused worker' moving power late",
                        "ASSUMPTION", "docs/design.md §5.7 device acceptance rules")
SEQ_SCOPE = const("SEQ_SCOPE", "seq restarts at 1 with every lease grant; devices order commands by (epoch, seq)",
                  "ASSUMPTION", "resilience/runtime/device.py (fencing token)")
RUNTIME_TRACKING_PCT = const("RUNTIME_TRACKING_PCT", 15.0, "ASSUMPTION",
                             "the percentage term of docs/design.md §4.2's max(2 MW, 15%); the 2 MW term exceeds this "
                             "96-Core fleet (1.92 MW), so only the percentage gates")
LIVE_WALL_S_PER_STEP = const("LIVE_WALL_S_PER_STEP", 0.5, "ASSUMPTION",
                             "live mode: one 60 s step plays in 0.5 s of wall clock around the kill (x120), so the "
                             "300 s lease runs out in about 2.5 s on camera")
LIVE_REPLY_DEADLINE_S = const("LIVE_REPLY_DEADLINE_S", 2.0, "ASSUMPTION",
                              "live mode: a worker that has not replied 2 s after a step starts misses that heartbeat")
LIVE_PACE_BEFORE = const("LIVE_PACE_BEFORE", 10, "ASSUMPTION", "live mode paces 10 steps before the kill")
LIVE_PACE_AFTER = const("LIVE_PACE_AFTER", 10, "ASSUMPTION", "live mode paces 10 steps after the takeover")

# ---- the covert channel and its detector (B3; docs/design.md §4.3, §5.6; milestone M6') ------------------------------
COVERT_SHARD = const("COVERT_SHARD", "the 24 dense-cohort Cores of data/fleet.json shaping.denseHomes", "ASSUMPTION",
                     "demos/grid-stories' 'Cedar' cohort: a fictional adversary's foothold on one lateral")
MODULATION_KW = const("MODULATION_KW", 0.35, "ASSUMPTION", "demos/grid-stories/sim/constants.py: fictional compromised devices")
COVERT_SYMBOL_MIN = const("COVERT_SYMBOL_MIN", 5, "ASSUMPTION", "one symbol per 5-minute telemetry sample (docs/design.md §5.6)")
COVERT_CARRIER = const("COVERT_CARRIER",
                       "the hidden offset alternates sign every minute; each 5-minute symbol's phase carries one bit of "
                       "a seeded fictional message; only while the unit acts on a live command", "ASSUMPTION",
                       "demos/grid-stories/sim/build_replays.py (alternating +-350 W), keyed per docs/design.md §5.6")
COVERT_AFTER_MIN = const("COVERT_AFTER_MIN", 30, "ASSUMPTION", "the channel opens at Tc + 30 min, inside legitimate charging")
COVERT_SEED = const("COVERT_SEED", 20260926, "ASSUMPTION", "seeds the fictional message and the telemetry and voltage noise")
TELEMETRY_NOISE_KW = const("TELEMETRY_NOISE_KW", 0.045, "ASSUMPTION", "demos/grid-stories/sim/constants.py: seeded Gaussian meter noise")
VOLTAGE_NOISE_PU = const("VOLTAGE_NOISE_PU", 0.00002, "ASSUMPTION",
                         "demos/grid-stories/sim/constants.py: not a measured noise floor")
DETECT_WINDOW_MIN = const("DETECT_WINDOW_MIN", 10, "ASSUMPTION", "the detector judges the last 10 one-minute samples")
DETECTION_RMS_KW = const("DETECTION_RMS_KW", 0.18, "ASSUMPTION", "demos/grid-stories/sim/constants.py")
DETECTION_CORRELATION = const("DETECTION_CORRELATION", 0.75, "ASSUMPTION",
                              "demos/grid-stories/sim/constants.py; here sign-aware: the residual's lag-1 autocorrelation "
                              "must be below -0.75 (it oscillates), so a smooth shortfall such as the charge taper never "
                              "qualifies")
VOLTAGE_CARRIER_PU = const("VOLTAGE_CARRIER_PU", 0.0001, "ASSUMPTION",
                           "voltage corroboration: the home's own AMI voltage must carry the carrier (median amplitude at "
                           "the carrier frequency over quiet windows) above 1e-4 pu, 5 x VOLTAGE_NOISE_PU; measured on the "
                           "quick and fixture windows, compromised homes under attack read 1.35e-4 (p5) to 2.5e-4 (p50) pu, "
                           "the same homes without the attack about 1e-5 (p50)")
PEER_MIN_HOMES = const("PEER_MIN_HOMES", 5, "ASSUMPTION",
                       "peer set, reported and never gating: the other homes on the unit's transformer, widened to the "
                       "nearest transformers until there are at least 5; docs/design.md §5.6 'same transformer, lateral'")
CHANNEL_SPAN_MIN = const("CHANNEL_SPAN_MIN", 60, "ASSUMPTION",
                         "the channel's strength is measured over the attack's first hour (a reporting choice, never gating)")
FIXED_THRESHOLD_KW = const("FIXED_THRESHOLD_KW", 1.0, "ASSUMPTION",
                           "the naive comparison: flag any |reported - setpoint| above 1 kW (demos/grid-stories fixedThresholdFlags)")

COVERT_CONSTANTS = ("COVERT_SHARD", "MODULATION_KW", "COVERT_SYMBOL_MIN", "COVERT_CARRIER", "COVERT_AFTER_MIN",
                    "COVERT_SEED", "TELEMETRY_NOISE_KW", "VOLTAGE_NOISE_PU", "DETECT_WINDOW_MIN", "DETECTION_RMS_KW",
                    "DETECTION_CORRELATION", "VOLTAGE_CARRIER_PU", "PEER_MIN_HOMES", "CHANNEL_SPAN_MIN",
                    "FIXED_THRESHOLD_KW")

RUNTIME_CONSTANTS = ("LEASE_TTL_S", "RUNTIME_WORKERS", "RUNTIME_PARTITIONS", "PARTITION_RULE", "SHARE_RULE",
                     "KILL_AFTER_MIN", "LATE_BATCH_RULE", "SEQ_SCOPE", "RUNTIME_TRACKING_PCT")
LIVE_CONSTANTS = ("LIVE_WALL_S_PER_STEP", "LIVE_REPLY_DEADLINE_S", "LIVE_PACE_BEFORE", "LIVE_PACE_AFTER")
