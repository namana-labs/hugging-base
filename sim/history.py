"""Real historical evenings for P1 (lane L2; HIST-R2 sections 4-5, UX_SPEC_R2 5.1.3).

23 Aug 2026 stays where it is (ui/data/p1/*.json, all four branches). Other real ERCOT evenings are simulated the same
way (sim.p1_build: 16:00 -> 04:00, 720 steps of 60 s, OpenDSS every step, the same controller and D-26 plan) with three
branches (none, naive, aware; the failure script is tuned to 23 Aug, HIST-R2 D2) and written under ui/data/p1/days/:

    days/<date>/meta.json              plain JSON, the p1/meta.json contract (A.5h): branches none/naive/aware, events {}
    days/<date>/<branch>.json.gz       gzip -9, mtime 0, of the A.6 branch doc (HIST-R2 D3)
    days/index.json                    one row per simulated evening, everything the day picker needs (A.10)
    days/calendar.json                 prices-only money calendar, every evening in the price file (A.9)

    python -m sim.history                   # every day in DAYS + index + calendar (heavy: ~15 s CPU a day; take the lock)
    python -m sim.history --only 2026-07-22 # one day (+ index + calendar)
    python -m sim.history --calendar-only   # calendar + index from the metas on disk (1-2 s)
    python -m sim.history --quick           # calendar + a 60-step day into ~/hb-overnight/tmp/hist-quick (no lock)
    python -m sim.history --out DIR         # write days/ somewhere else (verify --days --rebuild uses this)

Loads: SMART-DS 2018 on the same calendar date (LOAD_PAIRING, ASSUMPTION). August 2026 evenings read the committed
August slice; any other date reads a 120-step slice cut from the SMART-DS cache into data/profiles/days/<date>.npz
(committed; rebuilt byte-identical). Prices: REAL ERCOT LZ_NORTH (data/ercot/lz_north_2026.csv).

Money (HIST-R2 5, labels): prices REAL; battery kW SIM; every $ DERIVED ("gross energy value, not Base's P&L"); the D-26
plan's perfect foresight is an ASSUMPTION (discharge_plan's cite); local relief is never priced.
"""
import argparse
import gzip
import hashlib
import json
import math
import sys
import time
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path

import numpy as np

from .constants import (const, export, P1_DAY, SOC0, RESERVE_FLOOR, CORE_USABLE_KWH, CORE_RTE, CORE_POWER_KW,
                        FLEET_SIZE)
from .contracts import ROOT, envelope, inputs_sha, labelled, dumps, write_json
from .prices import onset_d26, discharge_plan, price_at, load as load_prices

OUT = ROOT / "ui" / "data" / "p1"
DAYS_DIR = OUT / "days"
SLICES = ROOT / "data" / "profiles" / "days"
AUG_NPZ = ROOT / "data" / "profiles" / "smartds_2018_aug.npz"
CACHE = Path.home() / "hb-overnight" / "cache" / "smartds"
QUICK_OUT = Path.home() / "hb-overnight" / "tmp" / "hist-quick"
SLICE_STEPS = 120                    # 30 h of 15-min steps from <date> 00:00: covers 16:00 -> 04:00 (+ interpolation)
HIST_BRANCHES = ("none", "naive", "aware")
FMT = "%Y-%m-%dT%H:%M"

# The drawer order. Tags are editorial text with no digits (HIST-R2 5); each `why` is formatted from the day's meta
# (or cites its source when the number is not in the meta). Must: 22 Jul, 26 Aug, 14 Aug (UX_SPEC_R2 5.1.3).
DAYS = [
    {"date": "2026-08-23", "tag": "The evening we know best", "why": "peak_then_drop", "dir": ""},
    {"date": "2026-07-22", "tag": "Texas's record demand", "why": "record_demand", "dir": "days/2026-07-22"},
    {"date": "2026-08-26", "tag": "August's priciest evening", "why": "month_max", "dir": "days/2026-08-26"},
    {"date": "2026-08-14", "tag": "A quiet night", "why": "flat", "dir": "days/2026-08-14"},
]

ERCOT_RECORD_MW = const("ERCOT_RECORD_MW", 91134, "REAL",
                        "ERCOT all-time peak demand record, set 2026-07-22 (ERCOT all-time records page; "
                        "docs/research-report.md:330)")
PRICE_CITE = "ERCOT RTM SPP LZ_NORTH 15-min (data/ercot/lz_north_2026.csv)"
SPLIT_CITE = "REAL LZ_NORTH x SIM battery kW; gross energy value, not Base's P&L"
CAL_RULE = ("one 20 kW Core, one D-26 cycle a night: sell the plan's top-priced intervals between 16:00 and the onset "
            "(perfect foresight, ASSUMPTION), buy the energy back at full power from the onset in time order; "
            "energy only, gross, not Base's P&L")


def day_row(d):
    for r in DAYS:
        if r["date"] == d:
            return r
    return None


def day_dir(d, root=OUT):
    r = day_row(d)
    if r is None:
        raise KeyError(f"{d} is not in sim.history.DAYS")
    return Path(root) / r["dir"] if r["dir"] else Path(root)


# ---- loads ------------------------------------------------------------------------------------------------------
def _normalise_zip(path):
    """Fixed zip timestamps and order, so a rebuilt slice is byte-identical (as scripts/fetch_profiles.py)."""
    import os
    import zipfile
    tmp = path.with_suffix(".tmp.npz")
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        for item in sorted(zin.infolist(), key=lambda i: i.filename):
            data = zin.read(item.filename)
            info = zipfile.ZipInfo(item.filename, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zout.writestr(info, data, compresslevel=9)
    os.replace(tmp, path)


def slice_loads(d, cache=CACHE, out_dir=SLICES, force=False):
    """The loads npz for evening `d`. August 2026 dates read the committed August slice (nothing written). Any other
    date: a 120 x 15-min slice from <d> 00:00 of every kW and kvar shape, cut from the full-year SMART-DS 2018 CSVs in
    the cache (the same public files scripts/fetch_profiles.py fetches), with the August slice's metadata arrays;
    t0 = "<d>T00:00", source_t0 = "2018-<MM-DD>T00:00" (LOAD_PAIRING, ASSUMPTION)."""
    if d.startswith("2026-08"):
        return AUG_NPZ
    out = Path(out_dir) / f"{d}.npz"
    if out.exists() and not force:
        return out
    cache = Path(cache)
    if not cache.is_dir():
        raise SystemExit(f"no SMART-DS cache at {cache}: run `python3 scripts/fetch_profiles.py --fetch-only` "
                         "(it refetches the same public CSVs)")
    aug = np.load(AUG_NPZ)
    dd = date.fromisoformat(d)
    src = date(2018, dd.month, dd.day)
    i0 = (src - date(2018, 1, 1)).days * 96
    if i0 + SLICE_STEPS > 365 * 96:
        raise ValueError(f"{d}: the 2018 year ends before a {SLICE_STEPS}-step slice")

    def rd(name):
        v = np.array((cache / f"{name}.csv").read_text().split(), dtype=np.float64)
        if v.shape != (365 * 96,):
            raise ValueError(f"{name}.csv: {v.shape[0]} rows, expected {365 * 96}")
        return v[i0:i0 + SLICE_STEPS]

    kw_names = [str(x) for x in aug["kw_names"]]
    kvar_names = [str(x) for x in aug["kvar_names"]]
    kw = np.zeros((len(kw_names), SLICE_STEPS), dtype=np.float32)
    kvar = np.zeros((len(kvar_names), SLICE_STEPS), dtype=np.float32)
    for i, n in enumerate(kw_names):
        if not aug["kw_ok"][i]:
            raise SystemExit(f"{n}: the August slice has no kW shape for it")
        kw[i] = rd(n)
    for i, n in enumerate(kvar_names):
        if aug["kvar_ok"][i]:
            kvar[i] = rd(n)
    # the cache must reproduce the committed August slice (the same files, the same cut)
    j = (date(2018, 8, 1) - date(2018, 1, 1)).days * 96
    probe = np.array((cache / f"{kw_names[0]}.csv").read_text().split(), dtype=np.float64)[j:j + 96].astype(np.float32)
    if not np.array_equal(probe, aug["kw"][0, :96]):
        raise SystemExit(f"{cache} does not reproduce the committed August slice: refetch it")
    z = {k: aug[k] for k in aug.files}
    z.update(kw=kw, kvar=kvar, t0=np.array(f"{d}T00:00"), source_t0=np.array(f"{src.isoformat()}T00:00"))
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out, **z)
    _normalise_zip(out)
    return out


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ---- the story line -----------------------------------------------------------------------------------------------
def _window_prices(meta):
    """The meta's 1-min price series as 15-min intervals: [(HH:MM, $/MWh)] from the window start."""
    h, m = map(int, meta["start"].split(":"))
    out = []
    for k in range(0, meta["steps"], 15):
        t = (h * 60 + m + k) % 1440
        out.append((f"{t // 60:02d}:{t % 60:02d}", meta["price"][k]))
    return out


def month_max(d):
    """The highest 15-min LZ_NORTH price of d's calendar month in the price file (REAL): ($/MWh, 'YYYY-MM-DDTHH:MM')."""
    table, starts = load_prices()
    ks = [s for s in starts if s[:7] == d[:7]]
    best = max(ks, key=lambda s: (table[s], s))
    return table[best], best


def story_for(meta):
    """meta.story = {tag, why{text, label, cite}}: the day chip's line (HIST-R2 4.3.1). The tag is editorial and holds
    no digits; `why` is formatted from this meta, or cites where its number comes from."""
    d = meta["day"]
    row = day_row(d) or {"tag": "A simulated evening", "why": "peak_then_drop"}
    ps = _window_prices(meta)
    t_pk, p_pk = max(ps, key=lambda x: x[1])
    kind = row["why"]
    if kind == "record_demand":
        why = {"text": f"ERCOT set its all-time demand record this day: {ERCOT_RECORD_MW:,} MW",
               "label": "REAL", "cite": TAG_CITE("ERCOT_RECORD_MW")}
    elif kind == "month_max":
        mx, when = month_max(d)
        if when[:10] == d and abs(mx - p_pk) < 1e-9:
            why = {"text": f"The month's highest price: ${p_pk:,.2f}/MWh at {t_pk}", "label": "REAL",
                   "cite": f"{PRICE_CITE}; the maximum 15-min price of {d[:7]} in the file"}
        else:
            why = {"text": f"Prices peaked at ${p_pk:,.2f}/MWh at {t_pk}", "label": "REAL", "cite": PRICE_CITE}
    elif kind == "flat":
        why = {"text": f"A flat, cheap evening: the highest price was ${p_pk:,.2f}/MWh", "label": "REAL", "cite": PRICE_CITE}
    else:
        onset = meta["plan"]["onset"]
        op = meta["plan"]["onsetPrice"]["v"]
        text = (f"Prices peaked at ${p_pk:,.2f}/MWh at {t_pk}, then fell to ${op:,.2f} at {onset}" if op < p_pk
                else f"Prices peaked at ${p_pk:,.2f}/MWh at {t_pk}")
        why = {"text": text, "label": "REAL", "cite": PRICE_CITE}
    return {"tag": row["tag"], "why": why}


def TAG_CITE(name):
    from .constants import TAG
    return TAG[name]["cite"]


# ---- one day ------------------------------------------------------------------------------------------------------
def write_json_gz(path, doc):
    """gzip.compress(compact JSON, 9, mtime=0): deterministic bytes. Lane L0's sim.contracts.write_json_gz is used when
    it exists (UX_SPEC_R2 4.3); this is the same recipe."""
    from . import contracts
    f = getattr(contracts, "write_json_gz", None)
    path = Path(path)
    if f is not None:
        n = f(path, doc)
        return n if isinstance(n, int) else path.stat().st_size
    path.parent.mkdir(parents=True, exist_ok=True)
    data = gzip.compress(dumps(doc).encode("utf-8"), compresslevel=9, mtime=0)
    path.write_bytes(data)
    return len(data)


def _gz_branch(path_no_suffix, doc):
    p = Path(str(path_no_suffix) + ".json.gz")
    return p.name, write_json_gz(p, doc)


def build_day(d, out_root=OUT, feeder=None, quiet=True, steps=None, start=None):
    """Simulate evening `d` (three branches) into <out_root>/days/<d>/ (or <out_root> itself for 23 Aug: the
    committed four-branch build is sim.p1_build's, never this function's). Returns build()'s result."""
    from .loads import Loads
    from .p1_build import Window, build
    if d == P1_DAY and steps is None:
        raise ValueError("23 Aug is built by sim.p1_build (four branches, p1/*.json)")
    kw = {}
    if steps is not None:
        kw["steps"] = steps
    if start is not None:
        kw["start"] = start
    win = Window(day=d, **kw)
    npz = slice_loads(d)
    loads = Loads(npz=npz)
    inputs = inputs_sha(loads_override=_sha(npz))
    out = Path(out_root) / "days" / d
    return build(win, out=out, loads=loads, feeder=feeder, quiet=quiet, branches=HIST_BRANCHES, story=story_for,
                 inputs=inputs, write_branch=_gz_branch)


# ---- the index (A.10) ---------------------------------------------------------------------------------------------
def read_meta(d, root=OUT):
    return json.loads((day_dir(d, root) / "meta.json").read_text())


@lru_cache(maxsize=1)
def focus_names():
    """{transformer index: "A".."D"} from ui/data/topology.json (A.10: naiveMax.tf is a display name on the street)."""
    topo = json.loads((ROOT / "ui" / "data" / "topology.json").read_text())
    return {int(f["tf"]): f["key"] for f in topo["focus"]}


def naive_doc(d, root=OUT):
    """The day's naive branch doc (plain for 23 Aug, gzip for a history day): the builder reads it for naiveMax.tier."""
    base = day_dir(d, root)
    p = base / "naive.json"
    if p.exists():
        return json.loads(p.read_text())
    return json.loads(gzip.decompress((base / "naive.json.gz").read_bytes()))


def index_row(meta, row, naive=None):
    """One A.10 row from a built day's meta; `naive` (the naive branch doc) adds naiveMax.tier, the tier code at the
    worst step, so the picker never re-derives a tier from a %. The page never loads a branch file for the picker."""
    s = meta["summary"]
    d = meta["day"]
    ps = _window_prices(meta)
    t_pk, p_pk = max(ps, key=lambda x: x[1])
    split = meta["money"]["split"]
    nm = s["naive"]["maxLoading"]
    caused = s["aware"]["batteryCausedNormal"]["v"] + s["aware"]["batteryCausedEmergency"]["v"]
    cost = meta["money"]["costOfAwareness"]["v"]
    return {
        "date": d, "dow": datetime.strptime(d, "%Y-%m-%d").strftime("%a"),
        "tag": meta["story"]["tag"], "why": meta["story"]["why"], "dir": row["dir"], "branches": meta["branches"],
        "peak": labelled(p_pk, "REAL", PRICE_CITE, t=t_pk),
        "perBattery": {b: labelled(split[b]["perBattery"]["v"], "DERIVED", f"energy value / {FLEET_SIZE} batteries, "
                                                                           f"{b}; {SPLIT_CITE}")
                       for b in ("naive", "aware")},
        "awareMoreUSD": labelled(round(-cost, 2) + 0.0, "DERIVED", "fleet energy value, feeder-aware - naive (tonight); "
                                                                  f"{SPLIT_CITE}"),
        "naiveMax": labelled(nm["v"], "SIM", "OpenDSS: the worst service transformer, naive",
                             tf=focus_names().get(int(nm["tf"]), int(nm["tf"])), t=nm["t"],
                             **({"tier": _tier_at(meta, naive, nm)} if naive is not None else {})),
        "naiveEvents": labelled(s["naive"]["batteryCausedNormal"]["v"], "SIM", "battery-caused normal-tier events, naive"),
        "awareBatteryCaused": labelled(caused, "SIM", "battery-caused normal-tier events + emergency transformers, feeder-aware"),
        "reliefMinutes": labelled(meta["relief"]["minutesOver100"]["none"], "SIM",
                                  "minutes A spends above nameplate with no batteries (0: no relief card that evening)"),
        "sparkline": [p for _, p in ps],
    }


def _tier_at(meta, doc, nm):
    h, m = map(int, meta["start"].split(":"))
    th, tm = map(int, nm["t"].split(":"))
    k = ((th * 60 + tm) - (h * 60 + m)) % 1440
    return int(doc["tier"][k][int(nm["tf"])])


def build_index(root=OUT, days=None):
    days = days or [r["date"] for r in DAYS]
    rows = []
    shas = []
    for d in days:
        p = day_dir(d, root) / "meta.json"
        if not p.exists():
            continue
        shas.append(_sha(p))
        rows.append(index_row(json.loads(p.read_text()), day_row(d), naive_doc(d, root)))
    doc = envelope("p1.days", "sim.history", inputs=inputs_sha(),
                   constants=export("LOAD_PAIRING", "ERCOT_RECORD_MW", "P1_START", "P1_STEPS"),
                   sources={"price": {"label": "REAL", "text": "ERCOT RTM SPP LZ_NORTH 15-min"},
                            "load": {"label": "SIM", "text": "NREL SMART-DS 2018 AUS P1U, same calendar date (ASSUMPTION pairing)"},
                            "referee": {"label": "SIM", "text": "OpenDSSDirect.py 0.9.4 AC power flow, every step of every branch"}},
                   series={"sparkline": {"label": "REAL", "unit": "$/MWh", "by": "the 48 fifteen-minute prices, 16:00 to 04:00"}})
    doc.update({"default": P1_DAY, "metaSha256": {d: h for d, h in zip([r["date"] for r in rows], shas)}, "days": rows})
    return doc


# ---- the prices-only money calendar (A.9) -------------------------------------------------------------------------
def _evening(ds, usable, recharge):
    """One evening on the calendar rule (DERIVED, per 20 kW Core). Raises KeyError on a DST gap."""
    onset, _, peak, _, mode = onset_d26(ds)
    plan = discharge_plan(ds, onset, usable, CORE_POWER_KW)
    kwh_min = CORE_POWER_KW / 60.0
    sold = sum(price_at(datetime.strptime(ts, FMT) + timedelta(minutes=j)) * kwh_min / 1000.0
               for ts, m in plan for j in range(m))
    need, t, bought = recharge, datetime.strptime(onset, FMT), 0.0
    while need > 1e-9:
        e = min(need, kwh_min)
        bought += price_at(t) * e / 1000.0
        need -= e
        t += timedelta(minutes=1)
    d0 = datetime.strptime(ds, "%Y-%m-%d")
    win = [price_at(d0 + timedelta(hours=16, minutes=15 * i)) for i in range(48)]
    return {"sold": sold, "bought": bought, "peak": price_at(peak), "peakT": peak[11:16].replace(":", ""),
            "onset": ("" if onset[:10] == ds else "+") + onset[11:16].replace(":", ""),
            "mode": {"binding": "b", "non-binding": "n", "fallback": "f"}[mode],
            "negMin": 15 * sum(1 for p in win if p < 0)}


def build_calendar(sim_days=None):
    """Every evening in the price file on the calendar rule. sim_days: {date: dir} of the simulated evenings."""
    usable = (SOC0 - RESERVE_FLOOR) * CORE_USABLE_KWH * math.sqrt(CORE_RTE)
    recharge = usable / CORE_RTE
    _, starts = load_prices()
    first = date.fromisoformat(starts[0][:10])
    last = date.fromisoformat(starts[-1][:10]) - timedelta(days=1)      # the window needs 04:00 the next day
    cols = {k: [] for k in ("net", "sold", "bought", "peak", "negMin")}
    peak_t, onset_t, mode = [], [], []
    gaps = []
    days = []
    d = first
    while d <= last:
        ds = d.isoformat()
        try:
            e = _evening(ds, usable, recharge)
        except KeyError as ex:
            e = None
            gaps.append({"day": ds, "reason": f"DST or missing interval ({ex.args[0] if ex.args else ex}): the D-26 "
                                              "search or the 16:00-04:00 window cannot run"})
        days.append(ds)
        if e is None:
            for k in cols:
                cols[k].append(None)
            peak_t.append("-")
            onset_t.append("-")
            mode.append("-")
        else:
            cols["sold"].append(int(round(e["sold"] * 100)))
            cols["bought"].append(int(round(e["bought"] * 100)))
            cols["net"].append(int(round((e["sold"] - e["bought"]) * 100)))
            cols["peak"].append(int(round(e["peak"] * 100)))
            cols["negMin"].append(e["negMin"])
            peak_t.append(e["peakT"])
            onset_t.append(e["onset"])
            mode.append(e["mode"])
        d += timedelta(days=1)
    ok = [(ds, n) for ds, n in zip(days, cols["net"]) if n is not None]
    y26 = sorted((n for ds, n in ok if ds[:4] == "2026"), reverse=True)
    aug = sorted((n for ds, n in ok if ds[:7] == "2026-08"), reverse=True)
    rng = f"{days[0]} to {days[-1]}"
    head = {
        "perBattery2026ytd": labelled(round(sum(y26) / 100, 2), "DERIVED", f"sum of net per 20 kW Core, {rng}; {CAL_RULE}"),
        "top10Share2026": labelled(round(100 * sum(y26[:10]) / sum(y26)) if sum(y26) > 0 else None, "DERIVED",
                                   "% of that sum earned on the 10 best evenings"),
        "losingNights2026": labelled(sum(1 for n in y26 if n < 0), "DERIVED",
                                     f"evenings where one D-26 cycle loses money (round trip {CORE_RTE}, ASSUMPTION)"),
        "aug2026Top5Share": labelled(round(100 * sum(aug[:5]) / sum(aug)) if aug and sum(aug) > 0 else None, "DERIVED",
                                     "% of August 2026's sum earned on its 5 best evenings"),
    }
    doc = envelope("p1.calendar", "sim.history", inputs=inputs_sha(loads=False),
                   constants=export("SOC0", "RESERVE_FLOOR", "CORE_USABLE_KWH", "CORE_RTE", "CORE_POWER_KW",
                                    "ONSET_MEDIAN_MULT"),
                   sources={"price": {"label": "REAL", "text": "ERCOT RTM SPP LZ_NORTH 15-min (every evening in the file)"},
                            "rule": {"label": "DERIVED", "text": CAL_RULE}},
                   series={"net": {"label": "DERIVED", "unit": "USD cents per 20 kW Core, one D-26 cycle (null on a gap)"},
                           "sold": {"label": "DERIVED", "unit": "USD cents per 20 kW Core"},
                           "bought": {"label": "DERIVED", "unit": "USD cents per 20 kW Core"},
                           "peak": {"label": "REAL", "unit": "$/MWh x100, the evening peak searched from 17:00 (D-26)"},
                           "peakT": {"label": "REAL", "unit": "HHMM of the peak, space-separated"},
                           "onset": {"label": "DERIVED", "unit": "HHMM of the D-26 onset; + = after midnight"},
                           "mode": {"label": "DERIVED", "unit": "b binding, n non-binding, f fallback, - gap"},
                           "negMin": {"label": "REAL", "unit": "minutes of negative price inside 16:00-04:00"}})
    doc.update({"from": days[0], "to": days[-1], "n": len(days), **cols,
                "peakT": " ".join(peak_t), "onset": " ".join(onset_t), "mode": "".join(mode),
                "sim": dict(sim_days or {}), "gaps": gaps, "headline": head})
    return doc


# ---- main -----------------------------------------------------------------------------------------------------------
def built_days(root=OUT):
    return [r["date"] for r in DAYS if (day_dir(r["date"], root) / "meta.json").exists()]


def write_index_and_calendar(root=OUT):
    days = built_days(root)
    idx = build_index(root, days)
    sizes = {"index.json": write_json(Path(root) / "days" / "index.json", idx)}
    cal = build_calendar({d: day_row(d)["dir"] for d in days})
    sizes["calendar.json"] = write_json(Path(root) / "days" / "calendar.json", cal)
    return sizes, idx, cal


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--quick", action="store_true", help="calendar + one 60-step day into ~/hb-overnight/tmp/hist-quick")
    ap.add_argument("--only", default=None, help="build one day (YYYY-MM-DD)")
    ap.add_argument("--calendar-only", action="store_true", help="index + calendar from the metas on disk")
    ap.add_argument("--out", default=None, help="the p1 data root to write into (default ui/data/p1)")
    a = ap.parse_args(argv)
    t0 = time.time()
    if a.quick:
        root = Path(a.out) if a.out else QUICK_OUT
        d = a.only or "2026-07-22"
        r = build_day(d, root, steps=60, start="22:00")
        print(f"quick: {d} 22:00 + 60 steps -> {root / 'days' / d} ({r['seconds']:.1f} s)")
        cal = build_calendar({d: f"days/{d}"})
        write_json(root / "days" / "calendar.json", cal)
        print(f"quick: calendar {cal['from']} to {cal['to']} ({cal['n']} evenings, {len(cal['gaps'])} gaps) ; "
              f"{time.time() - t0:.1f} s")
        return 0
    root = Path(a.out) if a.out else OUT
    if not a.calendar_only:
        from .feeder import Feeder
        feeder = Feeder()
        todo = [a.only] if a.only else [r["date"] for r in DAYS if r["date"] != P1_DAY]
        for d in todo:
            t1 = time.time()
            r = build_day(d, root, feeder=feeder)
            m = r["meta"]
            s = m["summary"]
            print(f"  {d}: naive max {s['naive']['maxLoading']['v']}% ; aware battery-caused "
                  f"{s['aware']['batteryCausedNormal']['v']} ; aware ${m['money']['split']['aware']['perBattery']['v']}"
                  f"/battery ; {sum(r['sizes'].values()) / 1048576:.2f} MB ; {time.time() - t1:.1f} s", flush=True)
    sizes, idx, cal = write_index_and_calendar(root)
    print(f"history: {len(idx['days'])} evenings in index.json ; calendar {cal['from']} to {cal['to']} "
          f"({cal['n']} evenings, {len(cal['gaps'])} gaps) ; {time.time() - t0:.1f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
