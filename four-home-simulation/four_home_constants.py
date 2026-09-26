"""Four home model constants. One name per value; tags and citations survive into the replay.

Tags follow the Headroom PRD: SOURCED, DERIVED, ASSUMPTION, UNVERIFIED.
Sign convention matches demos/grid-stories devices.py: battery p_kw > 0 means
charging. The Headroom PRD binding convention is the opposite; converting at any
PRD facing boundary is one negation, stated here once.
"""

TAG = {}


def const(name, value, tag, cite):
    TAG[name] = {"value": value, "tag": tag, "cite": cite}
    return value


# ---- devices: one battery per home -------------------------------------------
CORE_POWER_KW = const("CORE_POWER_KW", 20.0, "SOURCED", "Base Core spec, 20 kW continuous")
CORE_USABLE_KWH = const("CORE_USABLE_KWH", 37.0, "ASSUMPTION", "39.2 kWh nameplate; usable unpublished")
LEGACY_POWER_KW = const("LEGACY_POWER_KW", 11.4, "SOURCED", "legacy ground mount, 11.4 kW inverter")
LEGACY_USABLE_KWH = const("LEGACY_USABLE_KWH", 22.5, "UNVERIFIED", "Growatt APX inference, 90 pct of 25 kWh")
CORE_RTE = const("CORE_RTE", 0.89, "ASSUMPTION", "round trip efficiency unpublished")
LEGACY_RTE = const("LEGACY_RTE", 0.88, "ASSUMPTION", "round trip efficiency unpublished")
RESERVE_FLOOR = const("RESERVE_FLOOR", 0.20, "SOURCED", "20 pct backup reserve")
SOC0_LO = const("SOC0_LO", 0.25, "ASSUMPTION", "state of charge after the evening peak discharge")
SOC0_HI = const("SOC0_HI", 0.35, "ASSUMPTION", "state of charge after the evening peak discharge")
INVERTER_KV = const("INVERTER_KV", 0.24, "SOURCED", "inverter connects line to line on the 120/240 V service")

# ---- homes -------------------------------------------------------------------
HOME_ONSET_KW_LO = const("HOME_ONSET_KW_LO", 4.0, "UNVERIFIED", "evening home load band at onset; test R3 pending")
HOME_ONSET_KW_HI = const("HOME_ONSET_KW_HI", 6.0, "UNVERIFIED", "evening home load band at onset; test R3 pending")
HOME_KVAR_PER_KW = const("HOME_KVAR_PER_KW", round(0.5060219487390896 / 5.39943476758497, 5), "DERIVED",
                         "SMART-DS Loads.dss kvar/kW ratio, about 0.996 pf")
HOME_LEG_KV = const("HOME_LEG_KV", 0.12, "SOURCED", "SMART-DS splits each home across two 120 V legs")

# ---- service transformers, verbatim from SMART-DS Transformers.dss -------------
XFMR_KV_HV = const("XFMR_KV_HV", 7.2, "SOURCED", "SMART-DS center tap, 7.2 kV primary")
XFMR_KV_LV = const("XFMR_KV_LV", 0.12, "SOURCED", "SMART-DS center tap, 120/120 V secondary")
XFMR_XHL = const("XFMR_XHL", 2.4, "SOURCED", "SMART-DS XHL")
XFMR_XLT = const("XFMR_XLT", 2.4, "SOURCED", "SMART-DS XLT")
XFMR_XHT = const("XFMR_XHT", 1.6, "SOURCED", "SMART-DS XHT")
XFMR_R_HV_PCT = const("XFMR_R_HV_PCT", 0.266272, "SOURCED", "SMART-DS winding 1 %r")
XFMR_R_LV_PCT = const("XFMR_R_LV_PCT", 0.532544, "SOURCED", "SMART-DS winding 2 and 3 %r")
XFMR_LOADLOSS_PCT = const("XFMR_LOADLOSS_PCT", 0.798816, "SOURCED", "SMART-DS %loadloss, 25 and 50 kVA")
XFMR_NOLOAD_25_PCT = const("XFMR_NOLOAD_25_PCT", 0.472, "SOURCED", "SMART-DS %noloadloss, 25 kVA")
XFMR_NOLOAD_50_PCT = const("XFMR_NOLOAD_50_PCT", 0.37, "SOURCED", "SMART-DS %noloadloss, 50 kVA")

# ---- limits -------------------------------------------------------------------
TIER_N_PCT = const("TIER_N_PCT", 100.0, "SOURCED", "R-4: kva is nameplate, no de rating")
TIER_E_PCT = const("TIER_E_PCT", 110.0, "SOURCED", "110 pct normal rating; SMART-DS normhkva")
TIER_A_PCT = const("TIER_A_PCT", 150.0, "SOURCED", "150 pct emergency rating; SMART-DS EmergHKVA")
V_MIN_120 = const("V_MIN_120", 114.0, "SOURCED", "ANSI C84.1 range A lower, 120 V base")
V_MAX_120 = const("V_MAX_120", 126.0, "SOURCED", "ANSI C84.1 range A upper, 120 V base")

# ---- service drops: SMART-DS triplex, lengths inside SMART-DS spread ------------
SVC_RMATRIX = const("SVC_RMATRIX", "(0.9149 0.3744 | 0.3744 0.9149)", "SOURCED", "SMART-DS 1P_UG_AL_1/0_Brenau_2, ohm/km")
SVC_XMATRIX = const("SVC_XMATRIX", "(0.4972667 0.3969667 | 0.3969667 0.4972667)", "SOURCED", "SMART-DS 1P_UG_AL_1/0_Brenau_2, ohm/km")
SVC_LENGTH_SPREAD_M = const("SVC_LENGTH_SPREAD_M", "9.1 to 32.0", "DERIVED", "10th to 90th percentile of 810 SMART-DS service drops")

# ---- primary feeder -----------------------------------------------------------
FEEDER_KV = const("FEEDER_KV", 12.47, "SOURCED", "SMART-DS feeder base kV")
SOURCE_PU = const("SOURCE_PU", 1.03, "SOURCED", "SMART-DS Master.dss source pu")
PRI_RMATRIX = const("PRI_RMATRIX", "(0.2228 0.0592 0.0592 | 0.0592 0.2228 0.0592 | 0.0592 0.0592 0.2228)", "SOURCED", "SMART-DS 3P_UG_AL_350kcmil_3, ohm/km")
PRI_XMATRIX = const("PRI_XMATRIX", "(0.8876 0.6647 0.6647 | 0.6647 0.8876 0.6647 | 0.6647 0.6647 0.8876)", "SOURCED", "SMART-DS 3P_UG_AL_350kcmil_3, ohm/km")
PRI_LENGTH_KM = const("PRI_LENGTH_KM", 2.0, "ASSUMPTION", "substation to the street's tap")
BG_PEAK_MW = const("BG_PEAK_MW", 6.9, "SOURCED", "SMART-DS median feeder peak; rest of feeder lumped at the tap")
BG_PF = const("BG_PF", 0.95, "ASSUMPTION", "rest of feeder power factor")
LOAD_SHAPE = const("LOAD_SHAPE", "ERCOT demand / day max", "DERIVED", "background and home load follow the real ERCOT demand curve")

# ---- system frequency -----------------------------------------------------------
F_NOM_HZ = const("F_NOM_HZ", 60.0, "SOURCED", "nominal frequency")
F_RESOLUTION_MHZ = const("F_RESOLUTION_MHZ", 1.0, "SOURCED", "dashboard publishes 3 decimals")
F_SENS_LO_MHZ_PER_MW = const("F_SENS_LO_MHZ_PER_MW", 0.075, "DERIVED", "ERCOT 2026-08-07 event, 56 mHz for 757 MW")
F_SENS_HI_MHZ_PER_MW = const("F_SENS_HI_MHZ_PER_MW", 0.12, "DERIVED", "Odessa 2022, 0.3 Hz for 2,555 MW")
F_WANDER_SIGMA_MHZ = const("F_WANDER_SIGMA_MHZ", 13.7, "SOURCED", "R-5 normal frequency wander")

# ---- market and dispatch -------------------------------------------------------
ZONE = const("ZONE", "LZ_NORTH", "SOURCED", "R-3 Oncor suburb stand in, labeled placeholder")
ONSET_MEDIAN_MULT = const("ONSET_MEDIAN_MULT", 2.0, "SOURCED", "D-26 desk charge onset at or below 2x day median")
STEP_MINUTES = const("STEP_MINUTES", 5, "SOURCED", "SCED cadence")
WINDOW_STEPS = const("WINDOW_STEPS", 36, "ASSUMPTION", "three hour window after onset")
JITTER_SECONDS = const("JITTER_SECONDS", 120, "SOURCED", "0 to 120 s random start delay, device enforced")
AWARE_MARGIN = const("AWARE_MARGIN", 0.95, "ASSUMPTION", "aware controller keeps 5 pct headroom")
SEED = const("SEED", 17263, "ASSUMPTION", "matches grid-stories seed family")
