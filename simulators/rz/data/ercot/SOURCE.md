# ERCOT LZ_NORTH real-time prices, 2026 (REAL)

- **What:** ERCOT Real-Time Market settlement point prices (RTM SPP), load zone **LZ_NORTH**, 15-minute intervals, 1 Jan 2026 00:00 to 19 Sep 2026 23:45 local time: 25,148 rows (262 days x 96, less the 4 intervals of the March DST change). No `rep=Y` rows.
- **Source file:** `evidence/scratchpad-20260925/bp-data-ingest/rtm2026_lz.csv` (all load zones and hubs), sha256 `0487b9d106ac422beee40bd287b9f0bd3ff938b3660b91700c346bccc25cde05`. Extracted with `python -m sim.prices --extract <that file>`, which refuses a source with another sha256.
- **This file:** `data/ercot/lz_north_2026.csv`, sha256 `8fbbb2a5e193ef8ec3f881d01ad840a5e4bc1d2df2001c0f86991b9fd9bdb313`. Columns: the source's `date,hour,interval,rep,sp,sptype,price` plus `interval_start_local`.
- **Clock (hour-ending):** ERCOT's `hour` is hour-ending 1-24, so **interval start = (hour-1)*60 + (interval-1)*15 minutes** after local midnight of `date`. Unit test: 08/23 hour 22 interval 1 = 21:00-21:15 = $566.42 (`sim/tests/test_prices.py`). This matches four-home's `price_for_step()`.
- **Use:** replayed from this file only. **No live ERCOT calls anywhere** in the app. ERCOT data may be redistributed in analyses; ERCOT's logo may not be used.
- **Label:** REAL. Derived quantities (the D-26 onset, the discharge plan, cliffs) are DERIVED and computed in `sim/prices.py`.

# ERCOT system demand, 25 Sep 2026 (REAL): `demand_2026-09-25.csv`

- **What:** ERCOT's 5-minute system demand for 25 Sep 2026 (the supply-demand dashboard, published 2026-09-25 22:45 -05:00), the only ERCOT demand series in the repo. It is the ERCOT rung of P1's scale ladder (`sim/money.py` `ercot_demand()`: the day's peak 5-min demand).
- **This file** is a byte copy of `four-home-simulation/data/demand_2026-09-25.csv` (Michael's folder, commit 4bcca51; provenance in `four-home-simulation/data/four_home_provenance.json`), sha256 `cfc8eece0d96552847b473137300f53e56d7e4d9c80bb1fe439caa4b3af0df7f`. It was copied into `simulators/rz` so this folder never reads another team member's folder. The committed data still names the original path as its source.
- **Label:** REAL (ERCOT). The ladder's shares built from it are DERIVED.
