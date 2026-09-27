# ERCOT LZ_NORTH real-time prices, 2026 (REAL)

- **What:** ERCOT Real-Time Market settlement point prices (RTM SPP), load zone **LZ_NORTH**, 15-minute intervals, 1 Jan 2026 00:00 to 19 Sep 2026 23:45 local time: 25,148 rows (262 days x 96, less the 4 intervals of the March DST change). No `rep=Y` rows.
- **Source file:** `evidence/scratchpad-20260925/bp-data-ingest/rtm2026_lz.csv` (all load zones and hubs), sha256 `0487b9d106ac422beee40bd287b9f0bd3ff938b3660b91700c346bccc25cde05`. Extracted with `python -m sim.prices --extract <that file>`, which refuses a source with another sha256.
- **This file:** `data/ercot/lz_north_2026.csv`, sha256 `8fbbb2a5e193ef8ec3f881d01ad840a5e4bc1d2df2001c0f86991b9fd9bdb313`. Columns: the source's `date,hour,interval,rep,sp,sptype,price` plus `interval_start_local`.
- **Clock (hour-ending):** ERCOT's `hour` is hour-ending 1-24, so **interval start = (hour-1)*60 + (interval-1)*15 minutes** after local midnight of `date`. Unit test: 08/23 hour 22 interval 1 = 21:00-21:15 = $566.42 (`sim/tests/test_prices.py`). This matches four-home's `price_for_step()`.
- **Use:** replayed from this file only. **No live ERCOT calls anywhere** in the app. ERCOT data may be redistributed in analyses; ERCOT's logo may not be used.
- **Label:** REAL. Derived quantities (the D-26 onset, the discharge plan, cliffs) are DERIVED and computed in `sim/prices.py`.

## Provenance manifest (data-truth fix list #15; audit `simulators/rz/judges/DATA-TRUTH-inputs.md` problem 8)

A judge can follow this chain from ERCOT's public site to the committed bytes. The audit re-checked every link and hash below on 26 Sep 2026.

| Step | What | Where / how | Check |
|---|---|---|---|
| 1. ERCOT product | NP6-785-ER "Historical RTM Load Zone and Hub Prices", report type 13061 | https://www.ercot.com/mp/data-products/data-product-details?id=NP6-785-ER | HTTP 200 on 26 Sep 2026 (audit) |
| 2. MIS listing | the 2026 year-to-date file of report 13061 | https://www.ercot.com/misapp/GetReports.do?reportTypeId=13061 | HTTP 200 on 26 Sep 2026 (audit) |
| 3. Downloaded file | `rpt.00013061.0000000000000000.20260920.080732945.RTMLZHBSPP_2026.zip`, 9,802,030 bytes, published by ERCOT 2026-09-20 08:07:30 CDT; MIS doclookupId 1276781176 (the download link on the listing in step 2) | retrieved after its 20 Sep publication into a local evidence folder dated 25 Sep 2026 (`evidence/scratchpad-20260925/.../rtm2026/`, not in the repo); the exact retrieval time was not recorded | the doclookupId link returned HEAD 200 with this file name on 26 Sep 2026 (audit) |
| 4. Spreadsheet inside | `RTMLZHBSPP_2026.xlsx`, 12 monthly sheets; its columns include `Delivery Hour`, `Delivery Interval` (hour-ending), `Settlement Point Name` and `Settlement Point Type` | unzip of step 3 | sha256 `b7ad7234a5e5d8699dc13488eeb8ab32da845f9c96d88186b5f6a65cdcb87632` |
| 5. Intermediate CSV | `rtm2026_lz.csv`: every load zone and hub, columns `date,hour,interval,rep,sp,sptype,price` | written from step 4 by the ingest script `extract_rtm.py` (openpyxl over the monthly sheets). **That script is not committed and is not on the build machine**: this is the one step a judge cannot re-run from the repo | sha256 `0487b9d106ac422beee40bd287b9f0bd3ff938b3660b91700c346bccc25cde05` (`PRICES_SHA256` in `sim/constants.py`) |
| 6. This file | `data/ercot/lz_north_2026.csv`: the 25,148 LZ_NORTH rows (all `sptype` = `LZ`, all `rep` = `N`) plus `interval_start_local` | `python -m sim.prices --extract rtm2026_lz.csv` (refuses any source whose sha256 is not step 5's) | sha256 `8fbbb2a5e193ef8ec3f881d01ad840a5e4bc1d2df2001c0f86991b9fd9bdb313`, 1,320,648 bytes (computed from the committed blob, `git show HEAD:data/ercot/lz_north_2026.csv \| sha256sum`) |

- **Independent check of step 5 to 6 (audit):** all 25,148 LZ_NORTH rows of `lz_north_2026.csv` equal the xlsx values key by key (openpyxl, `Settlement Point Name == LZ_NORTH` and `Settlement Point Type == LZ`): 0 missing, 0 extra, 0 differing. So the uncommitted step 5 does not change a value; it only reshapes.
- **Settlement point type:** the extract uses type `LZ`. ERCOT's file also carries `LZEW` rows for LZ_NORTH, which differ from `LZ` in 5,870 of 25,148 intervals by at most $1.36 (median $0.01), e.g. 23 Aug 21:00 is $566.42 `LZ` against $566.68 `LZEW` (audit figures). The choice does not change any result on screen; it is disclosed here.
- **Zone choice:** LZ_NORTH is our placeholder zone for the Oncor-suburb stand-in (`PRICE_ZONE`, ASSUMPTION); the prices of that zone are REAL.
- **Licence and terms:** ERCOT data may be redistributed in compilations and analyses; the ERCOT logo may not be used without permission (https://www.ercot.com/help/terms). The same report may not be re-downloaded through the API more than three times in twelve months, so the demo never fetches it: it replays this file.
