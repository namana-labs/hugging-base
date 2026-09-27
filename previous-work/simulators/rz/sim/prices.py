"""REAL ERCOT RTM settlement point prices, LZ_NORTH, 15-minute (data/ercot/lz_north_2026.csv).

Clock: ERCOT's `hour` is hour-ending (1-24), so interval start = (hour-1)*60 + (interval-1)*15 minutes,
local time. Timestamps here are local strings "YYYY-MM-DDTHH:MM" (the interval START).

    price_at(ts)                     the price of the interval containing ts (a minute inside it counts)
    onset_d26(day)                   (onset_ts, price, peak_ts, threshold, mode), build prompt 4.3, exactly
    discharge_plan(day, onset_ts, usable_kwh, pmax_kw) -> [(interval_start, minutes)]
    find_cliffs(start, end)          consecutive 15-min starts with prev >= $60 and next <= 0.5 x prev

    python -m sim.prices --extract <rtm2026_lz.csv>   one time: write data/ercot/lz_north_2026.csv
    python -m sim.prices [YYYY-MM-DD]                  print the day's D-26 onset and discharge plan
"""
import csv
import hashlib
import statistics
import sys
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path

from .constants import (ONSET_MEDIAN_MULT, CLIFF_MIN_PRICE, CLIFF_DROP_FRAC, PRICES_SHA256, PRICE_ZONE)

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "data" / "ercot" / "lz_north_2026.csv"
FMT = "%Y-%m-%dT%H:%M"
STEP = timedelta(minutes=15)


def interval_start(date_mdy, hour, interval):
    d = datetime.strptime(date_mdy, "%m/%d/%Y")
    return d + timedelta(minutes=(int(hour) - 1) * 60 + (int(interval) - 1) * 15)


def extract(src, dst=CSV):
    """LZ_NORTH rows of rtm2026_lz.csv, plus interval_start_local. Verifies the source sha256."""
    src = Path(src)
    sha = hashlib.sha256(src.read_bytes()).hexdigest()
    if sha != PRICES_SHA256:
        raise SystemExit(f"source sha256 {sha} != expected {PRICES_SHA256}")
    rows = []
    with src.open() as fh:
        for r in csv.DictReader(fh):
            if r["sp"] == PRICE_ZONE:
                ts = interval_start(r["date"], r["hour"], r["interval"]).strftime(FMT)
                rows.append([r["date"], r["hour"], r["interval"], r["rep"], r["sp"], r["sptype"], r["price"], ts])
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["date", "hour", "interval", "rep", "sp", "sptype", "price", "interval_start_local"])
        w.writerows(rows)
    return len(rows), sha


@lru_cache(maxsize=None)
def load():
    """{interval_start_local: price} and the sorted list of starts."""
    table = {}
    with CSV.open() as fh:
        for r in csv.DictReader(fh):
            table[r["interval_start_local"]] = float(r["price"])
    return table, tuple(sorted(table))


def _ts(x):
    return x if isinstance(x, datetime) else datetime.strptime(x[:16], FMT)


def _s(dt):
    return dt.strftime(FMT)


def floor15(ts):
    t = _ts(ts)
    return t.replace(minute=t.minute - t.minute % 15, second=0, microsecond=0)


def price_at(ts_local):
    """Price of the 15-min interval that contains ts_local ("YYYY-MM-DDTHH:MM" or datetime)."""
    table, _ = load()
    key = _s(floor15(ts_local))
    if key not in table:
        raise KeyError(f"no LZ_NORTH price for interval starting {key}")
    return table[key]


def day_prices(day):
    """The day's 96 (start, price) pairs. `day` is "YYYY-MM-DD"."""
    t0 = datetime.strptime(day, "%Y-%m-%d")
    return [(_s(t0 + k * STEP), price_at(t0 + k * STEP)) for k in range(96)]


def onset_d26(day):
    """Build prompt 4.3, exactly. Returns (onset_ts, price, peak_ts, threshold, mode).

    1. median of the day's 96 prices; threshold = ONSET_MEDIAN_MULT x median.
    2. peak = the highest-priced interval of that day starting at or after 17:00.
    3. price[peak] <= threshold: onset = the interval after peak, mode 'non-binding'.
    4. else search forward from peak + 15 min, across midnight, up to 06:00 next day, for the first
       interval at or below threshold: mode 'binding'.
    5. none found: onset = the interval after peak, mode 'fallback'.
    """
    table, _ = load()
    prices = day_prices(day)
    med = statistics.median(p for _, p in prices)
    threshold = ONSET_MEDIAN_MULT * med
    evening = [(t, p) for t, p in prices if t[11:16] >= "17:00"]
    peak_ts, peak_p = max(evening, key=lambda x: x[1])  # first of equal maxima
    after = _ts(peak_ts) + STEP
    if peak_p <= threshold:
        return _s(after), price_at(after), peak_ts, threshold, "non-binding"
    limit = datetime.strptime(day, "%Y-%m-%d") + timedelta(days=1, hours=6)
    t = after
    while t < limit:
        key = _s(t)
        if key in table and table[key] <= threshold:
            return key, table[key], peak_ts, threshold, "binding"
        t += STEP
    return _s(after), price_at(after), peak_ts, threshold, "fallback"


def discharge_plan(day, onset_ts, usable_kwh, pmax_kw, start="16:00"):
    """The highest-priced 15-min intervals between `start` and the onset that `usable_kwh` covers at
    `pmax_kw` (perfect foresight, ASSUMPTION). Returns [(interval_start, minutes)] in price order:
    full intervals are 15 minutes; the last is partial, floored to whole minutes."""
    t = datetime.strptime(f"{day}T{start}", FMT)
    end = _ts(onset_ts)
    cands = []
    while t < end:
        cands.append((price_at(t), _s(t)))
        t += STEP
    cands.sort(key=lambda x: (-x[0], x[1]))
    minutes_left = usable_kwh / pmax_kw * 60.0
    plan = []
    for _, ts in cands:
        if minutes_left <= 1e-9:
            break
        m = 15 if minutes_left >= 15 else int(minutes_left)
        if m <= 0:
            break
        plan.append((ts, m))
        minutes_left -= m
    return plan


def find_cliffs(start="2026-01-01T00:00", end="2026-09-20T00:00"):
    """Price cliffs (build prompt 4.3): consecutive 15-min starts with prev >= $60 and next <= 0.5 x prev.
    'evening' = the later interval starts 20:00-23:59. Returns [{t, prev, next, drop, evening}]."""
    table, starts = load()
    lo, hi = _s(_ts(start)), _s(_ts(end))
    out = []
    for a in starts:
        if not (lo <= a < hi):
            continue
        b = _s(_ts(a) + STEP)
        if b not in table or b >= hi:
            continue
        pa, pb = table[a], table[b]
        if pa >= CLIFF_MIN_PRICE and pb <= CLIFF_DROP_FRAC * pa:
            out.append({"t": b, "prev": pa, "next": pb, "drop": round(1 - pb / pa, 4),
                        "evening": "20:00" <= b[11:16] <= "23:59"})
    return out


def main(argv):
    if argv and argv[0] == "--extract":
        n, sha = extract(argv[1])
        print(f"lz_north_2026.csv: {n} rows (source sha256 {sha})")
        return 0
    day = argv[0] if argv else "2026-08-23"
    onset, p, peak, thr, mode = onset_d26(day)
    print(f"{day}: peak {peak} ${price_at(peak):.2f} | threshold ${thr:.2f} | onset {onset} ${p:.2f} ({mode})")
    from .constants import CORE_USABLE_KWH, CORE_RTE, CORE_POWER_KW, SOC0, RESERVE_FLOOR
    usable = (SOC0 - RESERVE_FLOOR) * CORE_USABLE_KWH * CORE_RTE ** 0.5
    print("discharge plan:", discharge_plan(day, onset, usable, CORE_POWER_KW), f"({usable:.2f} kWh at the meter)")
    c = find_cliffs()
    print(f"cliffs: {len(c)} total, {sum(x['evening'] for x in c)} evening")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
