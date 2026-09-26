# ERCOT Public Data and APIs as a Data Source for a Battery-Fleet Grid Simulator

Research date: 2026-09-25 (US Central). All live tests below were run with `curl` from a US IP between 2026-09-26 00:24 and 00:31 UTC (2026-09-25 19:24 to 19:31 CDT). No account was registered and no credentials were used. "Verified" means I got HTTP 200 and real data back, or I read the value in an official file. Anything I could not test or read directly is marked **UNVERIFIED**.

There are three ways to get data straight from ERCOT, and they overlap:

1. **Dashboard JSON feeds** at `https://www.ercot.com/api/1/services/read/dashboards/*.json`. No auth. Real-time, and they include system frequency every 10 seconds.
2. **MIS document listing and download** at `https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId=<RTID>` plus `https://www.ercot.com/misdownload/servlets/mirDownload?doclookupId=<DocID>`. No auth. You get the raw EMIL CSV or XML zips, usually about 7 to 31 days of recent files, plus annual historical archives going back to 2010. ERCOT does not document these endpoints, but the gridstatus library uses them.
3. **ERCOT Public Data API** at `https://api.ercot.com/api/public-reports`. You need a free account, a subscription key and an Azure B2C ID token. You can filter queries, and archives hold at least 7 years.

---

## 1. ERCOT Public API: registration, auth, token lifetime, rate limits, pagination, endpoint list

### Takeaway
Registration is free and self-service at apiexplorer.ercot.com. Every request needs two things: an `Ocp-Apim-Subscription-Key` header, and an `Authorization: Bearer <id_token>` header. You get the ID token from an Azure B2C ROPC password grant, and it lasts 1 hour with no way to refresh it. The limits are 30 requests per minute, at most 1,000 files per archive download, and no access from outside the US. The live API now exposes **249 operations across about 96 EMIL products**. The public GitHub OpenAPI spec is stale: it lists 106 paths and was last committed 2024-02-21.

### Cited Findings
**Registration and subscription key**
- To register, go to https://apiexplorer.ercot.com/ and click Sign In/Sign Up. Enter your email, then the verification code, then set a password and your name. To get a key, open Products, pick "Public API", enter a subscription name and click Subscribe. The primary key then appears on the Profile page under "Show". Page last updated 2026-09-17. — [ERCOT Developer Portal: Registration and Authentication](https://developer.ercot.com/applications/pubapi/user-guide/registration-and-authentication/)
- The live developer-portal metadata lists two products. The first is "Public API" (`apim-product-public`): subscriptionRequired true, approvalRequired false, subscriptionsLimit 1. The second is "Energy Storage Resource (ESR) API" (`esrapi-apim-api`), described as "ERCOT Energy Storage Resource (ESR) four second data". Verified by an unauthenticated GET on 2026-09-26. — [apiexplorer products JSON](https://apiexplorer.ercot.com/developer/products?api-version=2022-04-01-preview)
- There are two APIs. The first is `pubapi-apim-api`, at path `api/public-reports`. The second is `esrapi-apim-api`, at path `api/public-data`. Both have subscriptionRequired true and use an OpenID provider "aadb2c". The subscription key is read from the header `Ocp-Apim-Subscription-Key` or from the query parameter `subscription-key`. — [apiexplorer APIs JSON](https://apiexplorer.ercot.com/developer/apis?api-version=2022-04-01-preview)

**Token (Azure AD B2C ROPC flow)**
- The token URL is `https://ercotb2c.b2clogin.com/ercotb2c.onmicrosoft.com/B2C_1_PUBAPI-ROPC-FLOW/oauth2/v2.0/token` and the method is POST. The parameters are:
  - `username`, `password`
  - `grant_type=password`
  - `scope=openid+fec253ea-0d06-4272-a5e6-b478baeecd70+offline_access`
  - `client_id=fec253ea-0d06-4272-a5e6-b478baeecd70`
  - `response_type=id_token`

  — [ERCOT Developer Portal: Registration and Authentication](https://developer.ercot.com/applications/pubapi/user-guide/registration-and-authentication/)
- The docs say: "ID tokens are valid for one hour. There is no way to refresh an ID token. A new ID token may be acquired by sending another POST request." — [same page](https://developer.ercot.com/applications/pubapi/user-guide/registration-and-authentication/)
- ERCOT's own Python sample puts username and password in the **query string** of the POST URL, and it reads `access_token` from the response. That contradicts the docs, which say to use the `id_token`. The gridstatus client sends the same fields as a form body and reads `id_token` (`TOKEN_EXPIRATION_SECONDS = 3600`). — [ERCOT docs](https://developer.ercot.com/applications/pubapi/user-guide/registration-and-authentication/); [gridstatus ercot_api.py](https://github.com/gridstatus/gridstatus/blob/main/gridstatus/ercot_api/ercot_api.py)
- The live OpenID configuration for this B2C policy lists `grant_types_supported: ["password"]` and `response_types_supported` including `id_token`. The token endpoint is `.../b2c_1_pubapi-ropc-flow/oauth2/v2.0/token` (the path is case-insensitive). Verified with HTTP 200. — [OpenID config](https://ercotb2c.b2clogin.com/ercotb2c.onmicrosoft.com/B2C_1_PUBAPI-ROPC-FLOW/v2.0/.well-known/openid-configuration)
- Without a key, `GET https://api.ercot.com/api/public-reports` returns HTTP 401 with `{"statusCode": 401, "message": "Access denied due to missing subscription key..."}`. Verified. — [api.ercot.com](https://api.ercot.com/api/public-reports)

**Limits**
- The rate limit is "up to 30 requests per minute", and going over it returns `429 Too Many Requests`. Historic file downloads are limited to "1,000 files at a time". "Regions outside the United States of America are restricted." Historic files are "retained for at least 7 years". Data starts on each product's "initial activation date within the Public Data API system". Page updated 2026-09-17. — [ERCOT Developer Portal: Known limits](https://developer.ercot.com/applications/pubapi/known-limits/)
- gridstatus retries 429 errors with exponential backoff. It uses a page size of 100,000 (its code comment says "It's not clear what the max is (1_000_000 works)"), fetches 1,000 historical links per call, and switches to the archive method for dates more than 90 days old, noting that this "seems to vary per dataset". — [gridstatus ercot_api.py](https://github.com/gridstatus/gridstatus/blob/main/gridstatus/ercot_api/ercot_api.py)

**Pagination and response shape**
- The spec for `/np6-905-cd/spp_node_zone_hub` defines these query parameters:
  - date and hour filters: `deliveryDateFrom/To` (yyyy-MM-dd), `deliveryHourFrom/To`, `deliveryIntervalFrom/To`
  - location filters: `settlementPoint`, `settlementPointType`
  - price filter: `settlementPointPriceFrom/To`
  - `DSTFlag`
  - paging and sorting: `page`, `size`, `sort`, `dir`

  Responses include `_meta` (`totalRecords`, `pageSize`, `totalPages`, `currentPage`, `query`), `report`, `fields` (a column list), `data` and `links`. — [ercot/api-specs pubapi-apim-api.json](https://github.com/ercot/api-specs/blob/main/pubapi/pubapi-apim-api.json)
- The root `GET /` returns `"_embedded": {"products": [...]}` with `emilId`, `name`, `description`, an `artifacts` array of endpoint links, and `_links` for paging. — [ERCOT Developer Portal: Using the API](https://developer.ercot.com/applications/pubapi/user-guide/using-api/)
- These generic operations appear in the live list:
  - `GET /` (all products)
  - `GET /version`
  - `GET /{emilId}` (artifacts)
  - `GET /archive/{emilId}`
  - `POST /archive/{emilId}/download` ("a JSON request with a single 'docIds' element")
  - `GET /bundle/{emilId}` ("historical report archives")
  - `POST /bundle/{emilId}/download`

  — [apiexplorer operations JSON](https://apiexplorer.ercot.com/developer/apis/pubapi-apim-api/operations?api-version=2022-04-01-preview&$top=500)
- gridstatus calls `/archive/{emil_id}` with `postDatetimeFrom`, `postDatetimeTo`, `size`, `page`, reads `archives[]._links.endpoint.href`, and posts `{"docIds": batch}` to `/archive/{emil_id}/download`. — [gridstatus ercot_api.py](https://github.com/gridstatus/gridstatus/blob/main/gridstatus/ercot_api/ercot_api.py)

**Endpoint list (live, 2026-09-26)**
- The live operations list has 249 operations. That is 143 more than the GitHub spec, whose `pubapi/pubapi-apim-api.json` was last committed 2024-02-21 ("Public API OpenAPI Spec"). — [apiexplorer operations JSON](https://apiexplorer.ercot.com/developer/apis/pubapi-apim-api/operations?api-version=2022-04-01-preview&$top=500); [ercot/api-specs](https://github.com/ercot/api-specs)
- These are the live EMIL IDs in the Public API. Paths are lower-case:
  - np1-301, np1-302
  - np3-161-cd, np3-162-cd, np3-233-cd, np3-257-ex, np3-560-cd, np3-561-cd, np3-562-cd, np3-565-cd, np3-566-cd, np3-763-cd, np3-764-cd, np3-765-cd
  - np3-906-ex, np3-907-ex, np3-908-er, np3-909-er, np3-910-er, np3-911-er, np3-914-ex, np3-915-ex, np3-916-ex, np3-965-er, np3-966-er, np3-987-ex, np3-990-ex, np3-991-ex
  - np4-158-sg, np4-159-cd, np4-179-cd, np4-183-cd, np4-188-cd, np4-19-cd, np4-190-cd, np4-191-cd, np4-192-cd, np4-193-cd, np4-194-cd, np4-196-m, np4-197-m, np4-200-cd
  - np4-212-cd, np4-213-cd, np4-214-cd, np4-215-cd, np4-231-cd, np4-33-cd, np4-412-cd, np4-442-cd, np4-443-cd, np4-523-cd, np4-532-cd, np4-722-cd
  - np4-732-cd, np4-733-cd, np4-737-cd, np4-738-cd, np4-742-cd, np4-743-cd, np4-745-cd, np4-746-cd, np4-751-cd, np4-752-cd, np4-790-cd, np4-791-cd
  - np5-108-cd, np5-525-cd, np5-526-cd, np5-527-cd, np5-528-cd, np5-754-cd, np5-755-cd
  - np6-235-cd, np6-322-cd, np6-323-cd, np6-324-cd, np6-325-cd, np6-326-cd, np6-327-cd, np6-328-cd, np6-329-cd, np6-331-cd, np6-332-cd, np6-344-cd, np6-345-cd, np6-346-cd
  - np6-625-cd, np6-626-cd, np6-787-cd, np6-788-cd, np6-86-cd, np6-905-cd, np6-915-cd, np6-970-cd, np7-464-cd
  - one non-NP product: `gen-55-cd/hrly_rt_load_fcast_actual`

  — [apiexplorer operations JSON](https://apiexplorer.ercot.com/developer/apis/pubapi-apim-api/operations?api-version=2022-04-01-preview&$top=500)
- The **ESR API** (`https://api.ercot.com/api/public-data`) has one data endpoint: `GET /rptesr-m/4_sec_esr_charging_mw`, "Energy Storage Resource Four Second Data". It also has `/`, `/archive/{productId}`, `/bundle/{productId}`, the download POSTs and `/version`. It launched in release 2025-R5 on 2025-05-29. — [apiexplorer ESR ops JSON](https://apiexplorer.ercot.com/developer/apis/esrapi-apim-api/operations?api-version=2022-04-01-preview&$top=500); [ERCOT Developer Portal: Release notes](https://developer.ercot.com/applications/pubapi/relnotes/)
- The release history:
  - Beta on 2023-12-11 with 30 products.
  - GA on 2024-02-16, with "historic files from public data products spanning at least seven years".
  - Release 2024-R11 (2024-12-11): "Monthly Archives are now available for products with a daily or higher frequency."
  - 2025-R2: added historic file-only products.
  - 2025-R4 (2025-04-24): added NP6-792-ER and NP6-793-ER, the historical real-time price adders.
  - 2025-R11 (2025-12-05): RTC+B, with 22 new products.

  — [ERCOT Developer Portal: Release notes](https://developer.ercot.com/applications/pubapi/relnotes/)

### Inferences
- Getting a key should take minutes, because the product has `approvalRequired: false`. Each person can hold only one Public API subscription (`subscriptionsLimit: 1`). At 30 requests per minute, one shared key across 5 people and a live demo will get throttled. Two better options: each teammate registers their own account, or one backend process caches responses and the simulator reads from that cache.
- Use the archive and bundle endpoints for history. They return whole zips, so one request covers a day or a month instead of many paged queries.
- Cloud runners outside the US (for example a non-US region) will be blocked. Run fetchers from US regions or from laptops.

### Gaps
- I could not test the token flow or any authenticated call, because I registered no account and used no credentials, as instructed. The exact JSON of `data` rows (arrays vs objects) and the maximum `size` are **UNVERIFIED** by me. gridstatus says 1,000,000 works.
- The date format `postDatetimeFrom` expects (e.g. `2024-07-08T00:00:00`) is **UNVERIFIED**.
- The bundle endpoint's date coverage (how far back bundles go per product) is **UNVERIFIED**.

---

## 2. EMIL report IDs relevant to a battery-fleet simulator (verified names and corrections)

### Takeaway
Most of the IDs in the brief are right. Four need correcting:
- **NP3-233-CD is Hourly Resource Outage Capacity**, not ancillary service prices.
- **NP3-911-ER is the 2-Day Ancillary Service Reports** (cleared, self-arranged and aggregated AS offers, released with a 2-day lag), not ORDC adders.
- Since RTC+B went live on 2025-12-05, **NP6-331-CD is Real-Time Clearing Prices for Capacity for the 15-minute Settlement Interval** (the real-time AS MCPC). Its per-SCED companion is NP6-332-CD.
- The former ORDC adders live in **NP6-323-CD**, now named "Real-Time Price Adders by SCED Interval". Their history is in NP6-792-ER and NP6-793-ER.

### Cited Findings
Names below come from the live API operation list. Report Type ID (RTID), cadence, first run date and MIS display days come from each ERCOT "Data Product Details" page, fetched 2026-09-26. The URL pattern is `https://www.ercot.com/mp/data-products/data-product-details?id=<EMIL>`, for example [NP6-905-CD](https://www.ercot.com/mp/data-products/data-product-details?id=NP6-905-CD). The live API list is [here](https://apiexplorer.ercot.com/developer/apis/pubapi-apim-api/operations?api-version=2022-04-01-preview&$top=500).

| EMIL ID | Official name | API path | RTID (MIS) | Cadence | First run | MIS display (days) |
|---|---|---|---|---|---|---|
| NP6-905-CD | Settlement Point Prices at Resource Nodes, Hubs and Load Zones | `/np6-905-cd/spp_node_zone_hub` | 12301 | 15 min | 2010-11-30 | 7 |
| NP6-788-CD | LMPs by Resource Nodes, Load Zones and Trading Hubs | `/np6-788-cd/lmp_node_zone_hub` | 12300 | per SCED run (about 5 min) | 2010-11-30 | 5 |
| NP6-970-CD | RTD Indicative LMPs by Resource Nodes, Load Zones and Hubs | `/np6-970-cd/rtd_lmp_node_zone_hub` | 13073 | 5 min | 2012-06-27 | 5 |
| NP6-322-CD | SCED System Lambda | `/np6-322-cd/sced_system_lambda` | 13114 | per SCED | 2013-12-11 | 5 |
| NP4-190-CD | DAM Settlement Point Prices | `/np4-190-cd/dam_stlmnt_pnt_prices` | 12331 | per DAM run (daily) | 2010-11-29 | 31 |
| NP4-183-CD | DAM Hourly LMPs | `/np4-183-cd/dam_hourly_lmp` | 12328 | per DAM run | 2010-11-29 | 31 |
| NP4-188-CD | DAM Clearing Prices for Capacity (DAM AS MCPC) | `/np4-188-cd/dam_clear_price_for_cap` | 12329 | per DAM run | 2010-11-29 | 31 |
| NP6-331-CD | Real-Time Clearing Prices for Capacity for 15-Minute Settlement Interval | `/np6-331-cd/rt_clear_price_cap` | 24898 | 15 min | **2025-12-05** | 7 |
| NP6-332-CD | Real-Time Clearing Prices for Capacity by SCED Interval | `/np6-332-cd/rt_clear_price_cap_sced` | 24891 | per SCED | 2025-07-07 | 7 |
| NP6-329-CD | RTD Indicative MCPC | `/np6-329-cd/rtd_ind_mcpc` | not scraped | not scraped | not scraped | not scraped |
| NP6-323-CD | Real-Time Price Adders by SCED Interval (formerly ORDC and Reliability Deployment adders) | `/np6-323-cd/rt_price_adder_sced` | 13221 | per SCED | 2014-05-31 | 5 |
| NP6-324-CD | RT 15-min price adders | `/np6-324-cd/rt_15min_price_adders` | not scraped | not scraped | not scraped | not scraped |
| NP6-328-CD | Total Capability of Resources Available to Provide Ancillary Service | `/np6-328-cd/tot_as_res_cap` | 24887 | per SCED | 2025-12-05 | 7 |
| NP4-212-CD | DAM and SCED AS Demand Curves | `/np4-212-cd/dam_sced_as_demand_curves` | not scraped | not scraped | not scraped | not scraped |
| NP4-33-CD | DAM Ancillary Service Plan | `/np4-33-cd/dam_as_plan` | 12316 | daily | 2010-11-29 | 31 |
| NP3-911-ER | 2-Day Ancillary Service Reports (cleared DAM AS, self-arranged AS, aggregated AS offers) | `/np3-911-er/2d_*` | 13057 | daily (2-day lag) | 2011-01-29 | 31 |
| NP6-346-CD | Actual System Load by Forecast Zone | `/np6-346-cd/act_sys_load_by_fzn` | 14836 | daily (hourly values) | 2017-06-29 | 31 |
| NP6-345-CD | Actual System Load by Weather Zone | `/np6-345-cd/act_sys_load_by_wzn` | 13101 | daily (hourly values) | 2013-06-13 | 31 |
| NP6-235-CD | System-Wide Demand | `/np6-235-cd/system_wide_demand` | 12340 | hourly (15-min values) | 2010-11-30 | 7 |
| NP3-565-CD | Seven-Day Load Forecast by Model and Weather Zone | `/np3-565-cd/lf_by_model_weather_zone` | 14837 | hourly | 2017-06-28 | 7 |
| NP3-560-CD | Seven-Day Load Forecast by Forecast Zone | `/np3-560-cd/7d_load_fcast_by_fzn` | 12311 | hourly | 2010-11-30 | 7 |
| NP4-732-CD | Wind Power Production: Hourly Averaged Actual and Forecasted Values | `/np4-732-cd/wpp_hrly_avrg_actl_fcast` | 13028 | hourly | 2010-11-28 | 7 |
| NP4-742-CD | Wind: same, by Geographical Region | `/np4-742-cd/wpp_hrly_actual_fcast_geo` | not scraped | hourly | not scraped | not scraped |
| NP4-737-CD | Solar Power Production: Hourly Averaged Actual and Forecasted Values | `/np4-737-cd/spp_hrly_avrg_actl_fcast` | 13483 | hourly | 2016-02-09 | 7 |
| NP4-745-CD | Solar: same, by Geographical Region | `/np4-745-cd/spp_hrly_actual_fcast_geo` | 21809 | hourly | 2022-06-30 | 7 |
| NP4-733-CD / NP4-738-CD | Wind / Solar actual 5-minute averaged values | `/np4-733-cd/...`, `/np4-738-cd/...` | not scraped | 5 min | not scraped | not scraped |
| NP3-233-CD | **Hourly Resource Outage Capacity** (NOT AS prices) | `/np3-233-cd/hourly_res_outage_cap` | 13103 | hourly | 2013-10-20 | 31 |
| NP3-763-CD | Short-Term System Adequacy | `/np3-763-cd/st_sys_adequacy` | 12315 | hourly | 2010-11-23 | 31 |
| NP6-86-CD | SCED Shadow Prices and Binding Transmission Constraints (congestion) | `/np6-86-cd/shdw_prices_bnd_trns_const` | 12302 | hourly | 2010-11-30 | 7 |
| NP4-191-CD | DAM Shadow Prices | `/np4-191-cd/dam_shadow_prices` | not scraped | per DAM | not scraped | not scraped |
| NP3-965-ER | 60-Day SCED Disclosure Reports | `/np3-965-er/60_*` | 13052 | daily (60-day lag) | 2011-01-29 | 1462 |
| NP3-966-ER | 60-Day DAM Disclosure Reports | `/np3-966-er/60_*` | 13051 | daily (60-day lag) | 2011-01-29 | 1462 |
| NP3-910-ER | 2-Day Real Time Gen and Load Data Reports | `/np3-910-er/2d_agg_*` | 13056 | daily | 2011-01-29 | 31 |
| NP6-785-ER | Historical RTM Load Zone and Hub Prices (annual) | archive only | 13061 | weekly | 2011-09-30 | N/A |
| NP4-180-ER | Historical DAM Load Zone and Hub Prices (annual) | archive only | 13060 | weekly | 2011-10-01 | N/A |
| NP4-181-ER | Historical DAM Clearing Prices for Capacity (annual) | archive only | 13091 | weekly | 2012-10-23 | N/A |
| NP6-792-ER | Historical Real-Time Price Adders by SCED Interval (annual; ORDC-era files 2014-2025) | archive only | 13231 | weekly | 2014-06-07 | N/A |
| NP6-793-ER | Historical Real-Time Price Adders for 15-Minute Settlement Interval | archive only | 13240 | weekly | 2014-08-02 | N/A |
| NP12-261-M | Frequency Measurable Events in ERCOT Interconnection | MIS only | 13450 | weekly | 2015-03-02 | 730 |

- RTC+B went live on 2025-12-05. ERCOT moved to the new systems "at midnight between December 4, 2025, and December 5, 2025". — [ERCOT news release 2025-12-05](https://www.ercot.com/news/release/12052025-ercot-goes-live) (via search summary; also consistent with NP6-331-CD's first run date of 12-5-2025 on its [product page](https://www.ercot.com/mp/data-products/data-product-details?id=NP6-331-CD))
- Under RTC+B, the ORDC adder on energy prices is removed. Scarcity is now priced through Ancillary Service Demand Curves (ASDCs) inside real-time co-optimization. — [GridStatus insight](https://www.gridstatus.io/insights/27932035194) and [Yes Energy RTC+B hub](https://www.yesenergy.com/ercot-rtcb-market-changes) (secondary sources, via search summary)
- The live NP6-331-CD CSV header is `DeliveryDate,DeliveryHour,DeliveryInterval,RepeatedHourFlag,ASType,MCPC`. Sample rows: `09/25/2026,20,1,N,ECRS,0.29` and `NSPIN,1.15`. Verified by MIS download. — [MIS list RTID 24898](https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId=24898)
- The live NP6-323-CD header is `SCEDTimestamp,RepeatedHourFlag,SystemLambda,RTRDPA,RTRDPARUS,RTRDPARDS,RTRDPARRS,RTRDPAECRS,RTRDPANSS,RTRRUC,RTRRMR,RTDNCLR,RTDERS,...,RTOLLSL,RTOLHSL,RTDLL`. The per-AS reliability deployment adders are at the start of that list. Verified. — [MIS list RTID 13221](https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId=13221)
- The live NP4-188-CD header is `DeliveryDate,HourEnding,AncillaryType,MCPC,DSTFlag`: 121 lines, which is 24 hours × 5 AS types plus the header. Sample row: `09/26/2026,01:00,RRS,0.19,N`. Verified. — [MIS list RTID 12329](https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId=12329)
- NP6-792-ER file names change in 2025. The earlier files are `RTM_ORDC_REL_DPLY_PRC_ADDR_RSRV_2014..2025`, and 2025 and 2026 also have `HIST_RT_SCED_PRC_ADDR_*`. That matches the RTC+B transition. Verified. — [MIS list RTID 13231](https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId=13231)

### Inferences
- Price signals for the orchestrator after RTC+B:
  - energy: NP6-905-CD (15-minute SPP) and NP6-788-CD (5-minute LMP)
  - AS capacity: NP6-331-CD and NP6-332-CD (real time), NP4-188-CD (day ahead)
  - forward look: NP6-970-CD and NP6-329-CD (RTD indicative, about 1 hour ahead)
- A Uri or 2023 replay needs the pre-RTC+B price model. In that model the ORDC adder was added onto energy prices, and you can get it from NP6-792-ER and NP6-793-ER.

### Gaps
- For products marked "not scraped" I did not open the product page, so their RTID, first run date and display duration are **UNVERIFIED**. Their names are verified from the live API list.
- I found no EMIL product for "NP3-911 ORDC adders". That ID is the 2-day AS report, as shown above.

---

## 3. Real-time dashboard JSON feeds (no auth): exact URLs, shapes, cadence

### Takeaway
Twelve JSON feeds under `https://www.ercot.com/api/1/services/read/dashboards/` returned HTTP 200 with no auth and no special headers. A plain `curl` with no User-Agent also got 200. They are CDN-cached, mostly with `max-age=60`; `daily-prc.json` uses `max-age=10`. Together they give live system frequency (10 s), inertia, PRC and EEA state (about 8 to 10 s), 5-minute fuel mix, 5-minute ESR charge and discharge, 15-minute hub and load-zone prices, hourly load and forecasts, AS capacity, outages and a weather forecast. That is enough to drive a live simulator with no API key.

### Cited Findings
The dashboard index is https://www.ercot.com/gridmktinfo/dashboards. Each dashboard page references its JSON: ancillaryservices→`ancillary-services.json`, combinedwindandsolar→`combine-wind-solar.json`, dctieflows→`dc-tie-flows.json`, energystorageresources→`energy-storage-resources.json`, fuelmix→`fuel-mix.json`, generationoutages→`generation-outages.json`, gridconditions→`daily-prc.json`, supplyanddemand→`supply-demand.json`, systemwidedemand→`system-wide-demand.json`, systemwideprices→`system-wide-prices.json`, weatherforecast→`weather-forecast.json`. — [ERCOT dashboards](https://www.ercot.com/gridmktinfo/dashboards)

All results below are from tests run 2026-09-26 00:24 to 00:31 UTC. Times shown are CDT.

| URL (prefix `https://www.ercot.com/api/1/services/read/dashboards/`) | HTTP | Size | Shape and fields (trimmed) | Cadence and freshness observed |
|---|---|---|---|---|
| `ancillary-services.json` | 200 | 217 KB | `{lastUpdated, data:[{timestamp, interval(epoch ms), dstFlag, currentFrequency}] (720 pts), ascapmon:[{deployedRegUp, undeployedRegUp, deployedRegDown, undeployedRegDown, rrs, nsrs, ecrs}] (720 pts), lastRrs, lastEcrs, lastNsrs, ...}` | Frequency every **10 s** over the last 2 hours. The last point was 19:23:20 at `60.015` Hz while lastUpdated was 19:23:12, so about 1 to 2 minutes behind wall clock. AS capacity every about 8 s. |
| `dc-tie-flows.json` | 200 | 1.3 MB | `data:[{currentFrequency, currentSystemInertia, dcE, dcN, dcL, dcR, timestamp, epoch}]` (6,981 pts since midnight) | **10 s** since 00:00. Last: freq 60.015, inertia 330,942 (MW·s, UNVERIFIED unit) |
| `daily-prc.json` (Grid Conditions) | 200 | 774 KB | `current_condition:{eea_level:0, state:"normal", title:"Normal Conditions", prc_value:"10,418", condition_note, energy_level_value}`, `data:[{timestamp, epoch, prc}]` (6,990 pts) | About 8 to 10 s. Last point 19:24:52, fetched 19:24:52. **max-age=10** |
| `supply-demand.json` | 200 | 81 KB | `data:[{timestamp, demand, capacity, available, forecast(0/1)}]` (289 = 5-min today), `forecast:[{deliveryDate, hourEnding, forecastedDemand, availCapGen}]` (144 = 6 days hourly) | 5 min. lastUpdated 19:20 |
| `fuel-mix.json` | 200 | 160 KB | `monthlyCapacity:{Natural Gas:69599, Solar:40957, Wind:40405, Power Storage:22376, Coal and Lignite:13705, Nuclear:5268, Hydro:579, Other:663}`, `data:{<date>:{<ts>:{<fuel>:{gen}}}}` for yesterday and today | 5 min. At 19:20: Power Storage **+10,497 MW**, Gas 41,077, Wind 8,593 |
| `energy-storage-resources.json` | 200 | 98 KB | `previousDay/currentDay:{data:[{timestamp, totalCharging, totalDischarging, netOutput}]}` | 5 min. At 19:20: discharging 10,521.7 MW, net +10,482.6 MW |
| `system-wide-prices.json` | 200 | 34 KB | `rtSppData:[{intervalEnding, hbBusAvg, hbHubAvg, hbHouston, hbNorth, hbPan, hbSouth, hbWest, lzAen, lzCps, lzHouston, lzLcra, lzNorth, lzRaybn, lzSouth, lzWest, timestamp}]` (15-min, today), `damSppData:[{hourEnding, same keys}]` (24) | 15-min SPP. The 19:15 interval was present at 19:17, e.g. `lzAen 52.86`, `hbHouston 52.73` |
| `system-wide-demand.json` | 200 | 15 KB | `previousDay/currentDay/nextDay:{data:[{hourEnding, systemLoad, currentLoadForecast, dayAheadForecast, currentDayHsl, dayAheadHsl}]}` | hourly |
| `combine-wind-solar.json` | 200 | 17 KB | `currentDay/nextDay:{data:{<epoch>:{hourEnding, actualWind, stwpf, wgrpp, copHslWind, ...DayAhead, actualSolar, stppf, pvgrpp, copHslSolar}}}` | hourly |
| `generation-outages.json` | 200 | 502 KB | `currentOutages`, `current:{<epoch>:{deliveryTime, Combined/Dispatchable/Renewable:{planned, unplanned, total}}}`, `previous` | 5 min |
| `weather-forecast.json` | 200 | 2 KB | `[{lastUpdated, data:{DFW, Austin, San Antonio, Houston, Tyler, Wichita Falls, Lubbock, Abilene, Midland, Corpus Christi, ...}:{high, low, high15yr, low15yr, icon}}]` | daily; `no-store` |
| `ancillary-service-capacity-monitor.json` | 200 | 2 KB | `{lastUpdated, data:{responsiveReserveCapabilityGroup:[["key","value"],["rrcCapPfrGenEsr",1377],...], responsiveReserveAwardsGroup, ercotContingencyReserveCapabilityGroup:[...,["ecrsCapEsr",1269]], ...}}` | snapshot (19:29:52) |
| `todays-outlook.json` | **403** | 0.8 KB HTML | n/a | blocked or not public |
| `systemWidePrices.json`, `loadForecastVsActual.json`, `rtSyscond.json` | 302 | n/a | redirect to `system-wide-prices.json`, `system-wide-demand.json`, `dc-tie-flows.json` | legacy aliases |

- There is also a legacy HTML page with no auth, https://www.ercot.com/content/cdr/html/real_time_system_conditions.html, which returned HTTP 200 and auto-refreshes every 60 s. At "Last Updated: Sep 25, 2026 19:29:20" it showed "Current Frequency 59.994", "Instantaneous Time Error -2.302", "Actual System Demand 74368", "Total System Capacity 86496", "Total Wind Output 8465", "Total PVGR Output 113", "Current System Inertia 330942" and DC tie flows. gridstatus scrapes this page in `get_real_time_system_conditions()`. — [ERCOT RTSC page](https://www.ercot.com/content/cdr/html/real_time_system_conditions.html); [gridstatus ercot.py](https://github.com/gridstatus/gridstatus/blob/main/gridstatus/ercot.py)
- gridstatus's `Ercot()` class (no key) calls `ancillary-service-capacity-monitor.json` and `generation-outages.json`, as well as the MIS listing `IceDocListJsonWS` and `mirDownload`. — [gridstatus ercot.py](https://github.com/gridstatus/gridstatus/blob/main/gridstatus/ercot.py)

Example calls, all tested:
```bash
curl -s https://www.ercot.com/api/1/services/read/dashboards/daily-prc.json | jq '.current_condition'
# -> {"condition_note":"There is enough power for current demand.","eea_level":0,"state":"normal","title":"Normal Conditions","prc_value":"10,418",...}
curl -s https://www.ercot.com/api/1/services/read/dashboards/ancillary-services.json | jq '.data[-1]'
# -> {"timestamp":"2026-09-25 19:23:20-0500","interval":1790382200000,"dstFlag":"N","currentFrequency":60.015}
curl -s https://www.ercot.com/api/1/services/read/dashboards/system-wide-prices.json | jq '.rtSppData[-1] | {timestamp, lzAen, lzHouston, lzNorth, hbHubAvg}'
curl -s https://www.ercot.com/api/1/services/read/dashboards/energy-storage-resources.json | jq '.currentDay.data[-1]'
```

Minimal Python poller (requests only):
```python
import requests, time, json
BASE = "https://www.ercot.com/api/1/services/read/dashboards/"
FEEDS = ["daily-prc", "ancillary-services", "dc-tie-flows", "fuel-mix", "system-wide-prices",
         "supply-demand", "energy-storage-resources", "system-wide-demand", "combine-wind-solar"]
def snapshot():
    return {f: requests.get(BASE + f + ".json", timeout=20).json() for f in FEEDS}
while True:
    s = snapshot()
    cc = s["daily-prc"]["current_condition"]
    f = s["ancillary-services"]["data"][-1]
    print(cc["eea_level"], cc["prc_value"], f["timestamp"], f["currentFrequency"])
    json.dump(s, open(f"snap_{int(time.time())}.json", "w"))   # archive for replay
    time.sleep(60)   # matches CDN max-age=60; be polite (ERCOT ToU bars degrading site performance)
```

### Inferences
- These feeds are undocumented website internals. ERCOT can rename them at any time; the 302 legacy aliases show that renames have happened before. For a 48-hour hackathon they are the fastest path. Keep an MIS or API fallback ready.
- Polling faster than once every 60 s gains nothing for most feeds, because of the CDN `max-age`. `daily-prc.json` (max-age 10) is the exception.

### Gaps
- I found no official documentation or stability guarantee for the dashboard JSON API.
- The units of `currentSystemInertia` (presumably MW·s) are **UNVERIFIED**.
- The history depth of each feed beyond "today and yesterday" is **UNVERIFIED**. As observed, `ancillary-services.json` holds the last 2 hours and `dc-tie-flows.json` holds since midnight.

---

## 4. Is ERCOT system frequency public? Granularity and history

### Takeaway
Yes, for real time only. Frequency at **10-second** resolution is public with no auth in `ancillary-services.json` (the last 2 hours) and `dc-tie-flows.json` (since local midnight, with inertia). An instantaneous value is on the legacy RTSC HTML page, which refreshes every 60 s. I found **no public historical frequency time series**. The best public proxy is the weekly **NP12-261-M "Frequency Measurable Events"** workbook: one row per event from 2015 to 2026, with pre- and post-disturbance average frequency, the nadir and the MW lost. Detailed PDCWG frequency data appears to be restricted to members.

### Cited Findings
- 10-second `currentFrequency` points were verified in `ancillary-services.json` (720 points, 10,000 ms step) and `dc-tie-flows.json` (6,981 points, 10,000 ms step, with `currentSystemInertia`). — [ancillary-services.json](https://www.ercot.com/api/1/services/read/dashboards/ancillary-services.json); [dc-tie-flows.json](https://www.ercot.com/api/1/services/read/dashboards/dc-tie-flows.json)
- The RTSC page shows "Current Frequency", "Instantaneous Time Error" and "Consecutive BAAL Clock-Minute Exceedances", and refreshes every 60 s (`setTimeout(... 60000)`). — [RTSC page](https://www.ercot.com/content/cdr/html/real_time_system_conditions.html)
- NP12-261-M, "Frequency Measurable Events in ERCOT Interconnection": RTID 13450, weekly, first run 2015-03-02, public. The latest file is `ERCOT_FrequencyMeasurableEvents_AsOf_08182026.xlsx`, with sheets 2015 to 2026. Its columns are `ID, Time of FME (t(0)), Pre-perturbation Average Frequency (Hz), Post-perturbation Average Frequency (Hz), Minimum/Maximum Frequency (Hz), MW Loss (MW), Date Posted`. Sample row: `211, 2026-08-07 13:16:28, 60.0174, 59.9741, 59.961, 757 MW`. Verified by download. — [NP12-261-M product page](https://www.ercot.com/mp/data-products/data-product-details?id=NP12-261-M); [MIS list RTID 13450](https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId=13450)
- The FME list does **not** include the Uri load-shed frequency excursion of 2021-02-15. The 2021 sheet goes straight from 2021-01-28 to 2021-02-22, event 158: nadir 59.885 Hz, 714 MW. Verified in the file above.
- Uri: frequency hit a low of 59.302 Hz at about 1:55 a.m. on 2021-02-15 and stayed below 59.4 Hz for about 4 minutes 23 seconds. Some outlets report "4 minutes and 37 seconds" from collapse. These figures come from a search-result summary; I did not open the PDFs, so treat them as partially verified. — [ERCOT Feb 24 2021 presentation](https://www.ercot.com/files/docs/2021/02/24/2.2_REVISED_ERCOT_Presentation.pdf); [UT Austin timeline report](https://energy.utexas.edu/sites/default/files/UTAustin%20(2021)%20EventsFebruary2021TexasBlackout%2020210714.pdf); [Community Impact](https://communityimpact.com/austin/central-austin/government/2021/02/24/ercot-texas-power-system-was-less-than-5-minutes-from-collapse-during-winter-storm/)
- 2023-09-06: frequency fell to about 59.77 Hz between about 7:10 and 7:25 p.m. EEA2 was declared at 7:25 p.m., frequency was back at 60 Hz at 7:37 p.m., and operations were normal at 8:37 p.m. This is from a search summary citing ERCOT's 2023 Q3 report, which I did not open, so it is **partially UNVERIFIED**. — [ERCOT 2023 Q3 report](https://www.ercot.com/files/docs/2024/01/12/2023-10-13%20ERM%202023%20Q3%20Report.pdf); [ERCOT news: EEA2 initiated](https://www.ercot.com/news/release/2023-09-06-ercot-has-initiated)
- PDCWG reports are "only accessible to PDCWG members with specific Digital Certificates" and require an NDA. This comes from a search summary. — [PDCWG page](https://www.ercot.com/committees/ros/pdcwg)

### Inferences
- For the simulator, poll `dc-tie-flows.json` about every 10 minutes. It returns the whole day at 10-second resolution, so a 48-hour run can build its own frequency history.
- To script a generator-trip scenario, use NP12-261-M rows (MW lost, then nadir and settling frequency) as calibration points for a simple swing-equation or droop model.

### Gaps
- I found no public sub-10-second (PMU or 1-second) frequency data, and no public multi-year time series.

---

## 5. Load zones, hubs, weather zones and forecast zones (Austin, Houston, DFW)

### Takeaway
There is **no `LZ_AUSTIN`**. Austin Energy's zone is **`LZ_AEN`**. The eight settlement load zones are LZ_AEN, LZ_CPS, LZ_HOUSTON, LZ_LCRA, LZ_NORTH, LZ_RAYBN, LZ_SOUTH and LZ_WEST. The seven hubs are HB_BUSAVG, HB_HOUSTON, HB_HUBAVG, HB_NORTH, HB_PAN, HB_SOUTH and HB_WEST. There are eight weather zones (COAST, EAST, FAR_WEST, NORTH, NORTH_C, SOUTHERN, SOUTH_C, WEST) and four forecast zones (NORTH, SOUTH, WEST, HOUSTON).

### Cited Findings
- The live NP6-905-CD file (09/25/2026 HE20 interval 1) lists:
  - hubs, each with its type: `HB_BUSAVG` (SH), `HB_HUBAVG` (AH), and `HB_HOUSTON`, `HB_NORTH`, `HB_PAN`, `HB_SOUTH`, `HB_WEST` (HU)
  - load zones `LZ_AEN, LZ_CPS, LZ_HOUSTON, LZ_LCRA, LZ_NORTH, LZ_RAYBN, LZ_SOUTH, LZ_WEST`, each twice, as type `LZ` and as type `LZEW` (energy-weighted)
  - DC tie zones `LZ_DC` and `LZ_DCEW` for DC_E, DC_L, DC_N and DC_R
  - about 1,000 or more resource nodes (`RN`)

  Verified. — [MIS list RTID 12301](https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId=12301)
- The 2021 annual RTM archive covers exactly the 7 hubs and 8 load zones listed above. Verified. — [NP6-785-ER](https://www.ercot.com/mp/data-products/data-product-details?id=NP6-785-ER)
- The NP6-345-CD header is `OperDay,HourEnding,COAST,EAST,FAR_WEST,NORTH,NORTH_C,SOUTHERN,SOUTH_C,WEST,TOTAL,DSTFlag`. The NP6-346-CD header is `OperDay,HourEnding,NORTH,SOUTH,WEST,HOUSTON,TOTAL,DSTFlag`. The NP3-565-CD columns are `Coast,East,FarWest,North,NorthCentral,SouthCentral,Southern,West,SystemTotal,Model,InUseFlag`, with multiple forecast models (e.g., A3, A6). All verified. — [MIS RTID 13101](https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId=13101); [MIS RTID 14836](https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId=14836); [MIS RTID 14837](https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId=14837)
- LZ_AEN (Austin Energy), LZ_CPS (CPS Energy, San Antonio), LZ_LCRA (Lower Colorado River Authority) and LZ_RAYBN (Rayburn Country co-op) are the four NOIE (non-opt-in entity) load zones. AEN, CPS and LCRA sit geographically within the South area and RAYBN within the North. This comes from a search summary of Potomac and PUCT documents. — [Potomac Economics nodal monthly report](https://www.potomaceconomics.com/wp-content/uploads/2024/12/2024-11_Nodal_Monthly_Report.pdf); [PUCT filing 53911](https://interchange.puc.texas.gov/Documents/53911_121_1443773.PDF)
- The ERCOT weather-forecast dashboard lists representative cities including DFW, Austin, San Antonio, Houston, Tyler, Wichita Falls, Lubbock, Abilene, Midland and Corpus Christi. Verified. — [weather-forecast.json](https://www.ercot.com/api/1/services/read/dashboards/weather-forecast.json)
- ERCOT's official weather zone map is on its media-kit maps page. — [ERCOT Maps](https://www.ercot.com/news/mediakit/maps)
- ERCOT publishes a county mapping for wind and solar regions. — [Wind and Solar Regions to County Mapping.xlsx](https://www.ercot.com/files/docs/2024/05/31/Wind%20and%20Solar%20Regions%20to%20County%20Mapping.xlsx)

### Inferences
- **Austin members.** Inside the City of Austin, use **LZ_AEN** prices, **SOUTH_C** weather zone load and forecast, and the **SOUTH** forecast zone. HB_SOUTH or HB_HUBAVG are reasonable hub proxies.
- **Houston members.** Use **LZ_HOUSTON / HB_HOUSTON**, the **COAST** weather zone and the **HOUSTON** forecast zone.
- **DFW members.** Use **LZ_NORTH / HB_NORTH**, the **NORTH_C** weather zone and the **NORTH** forecast zone.
- **Base Power customers.** They are retail customers in competitive (opt-in) areas, so they would mostly settle in LZ_HOUSTON, LZ_NORTH, LZ_SOUTH or LZ_WEST rather than the NOIE zones. The city-to-zone mapping and this retail inference are **UNVERIFIED** against an official ERCOT map table.

### Gaps
- I did not open ERCOT's official weather zone map or a county-to-weather-zone table. The Austin→SOUTH_C, Houston→COAST and DFW→NORTH_C assignments are **UNVERIFIED**. They are consistent with ERCOT's zone naming and the dashboard city list, but I have not confirmed them against an official table.
- The settlement point to electrical bus mapping (NP4-160-SG) was not examined.

---

## 6. Historical data for scenario replay (Uri 2021, Elliott 2022, Sep 2023 EEA2, Heather Jan 2024, Beryl Jul 2024)

### Takeaway
You can get every event date with **no auth** from ERCOT's annual archive files through the MIS listing:
- RTM and DAM hub and load-zone prices, 2010 to 2026 (NP6-785-ER, NP4-180-ER)
- DAM AS clearing prices, 2010 to 2026 (NP4-181-ER)
- ORDC and real-time adders, 2014 to 2026 (NP6-792-ER, NP6-793-ER)
- hourly native load by weather zone (annual `Native_Load_YYYY.zip`, back to 2002)
- the annual fuel-mix workbooks (`IntGenbyFuelYYYY.xlsx`, plus a previous-years zip)

The Public API's filterable query endpoints only cover dates from each product's API activation, which is Dec 2023 for the original products. So Heather and Beryl can be queried directly. For Uri, Elliott and Sep 2023, use the API's `/archive` files (retained at least 7 years) or the MIS annual files.

### Cited Findings
- Historical RTM Load Zone and Hub Prices (NP6-785-ER, RTID 13061) has files `RTMLZHBSPP_2010` through `RTMLZHBSPP_2026`, about 13 to 14 MB zips each. The 2026 file was last published 2026-09-20. Verified with an unauthenticated listing. — [MIS list RTID 13061](https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId=13061)
- Historical DAM Load Zone and Hub Prices (NP4-180-ER, RTID 13060) has files `DAMLZHBSPP_2010` through `DAMLZHBSPP_2026`. Verified. — [MIS list RTID 13060](https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId=13060)
- Historical DAM Clearing Prices for Capacity (NP4-181-ER, RTID 13091) has files `DAMASMCPC_2010` through `DAMASMCPC_2026`. Historical adders (NP6-792-ER, RTID 13231; NP6-793-ER, RTID 13240) cover 2014 to 2026. Verified. — [NP4-181-ER](https://www.ercot.com/mp/data-products/data-product-details?id=NP4-181-ER); [NP6-792-ER](https://www.ercot.com/mp/data-products/data-product-details?id=NP6-792-ER); [NP6-793-ER](https://www.ercot.com/mp/data-products/data-product-details?id=NP6-793-ER)
- **Uri replay check.** I downloaded `RTMLZHBSPP_2021` with no auth (DocID 814922832, 13.3 MB). It unzips to one xlsx with month sheets `Jan` to `Dec` and columns `Delivery Date, Delivery Hour, Delivery Interval, Repeated Hour Flag, Settlement Point Name, Settlement Point Type, Settlement Point Price`. The Feb sheet has 61,824 rows. The maximum 15-minute RT SPP on 2021-02-15 was 9,794.02 $/MWh at LZ_AEN, 9,117.83 at HB_NORTH and 9,004.59 at LZ_HOUSTON. Feb 18 reached 9,875.33 at LZ_AEN. Verified. — [mirDownload DocID 814922832](https://www.ercot.com/misdownload/servlets/mirDownload?doclookupId=814922832)
- The Hourly Load Data Archives page lists `Native_Load_2016.zip` to `Native_Load_2026.zip` and `20xx_ercot_hourly_load_data.xls` for 2002 to 2015. Examples: `https://www.ercot.com/files/docs/2021/11/12/Native_Load_2021.zip`, `https://www.ercot.com/files/docs/2024/02/06/Native_Load_2024.zip`. Verified by listing the links. — [ERCOT Hourly Load Data Archives](https://www.ercot.com/gridinfo/load/load_hist)
- The generation page lists `IntGenbyFuel2026-1-.xlsx`, `IntGenbyFuel2025.xlsx` and `FuelMixReport_PreviousYears.zip` (https://www.ercot.com/files/docs/2021/03/10/FuelMixReport_PreviousYears.zip). Verified by listing the links. — [ERCOT Generation page](https://www.ercot.com/gridinfo/generation)
- For the Public API: the Data Access Portal search goes back as far as 2023-11-30, and older archives come as file packages. That is from a search summary of GitHub discussion #39. The API holds data from the product's activation date, and historic files are retained at least 7 years. — [ercot/api-specs Discussion #39](https://github.com/ercot/api-specs/discussions/39); [Known limits](https://developer.ercot.com/applications/pubapi/known-limits/); [Release notes](https://developer.ercot.com/applications/pubapi/relnotes/)
- The Data Access Portal (https://data.ercot.com) is for browsing current and expired data, the API Explorer is https://apiexplorer.ercot.com, and the gateway is https://api.ercot.com. — [ERCOT Public API Applications](https://www.ercot.com/services/mdt/data-portal) (via search summary)
- The 60-day SCED and DAM disclosures (NP3-965-ER and NP3-966-ER) have an MIS display duration of 1,462 days. The MIS listing for NP3-965-ER returned 923 files, the oldest published 2024-03-24. Verified. — [NP3-965-ER](https://www.ercot.com/mp/data-products/data-product-details?id=NP3-965-ER); [MIS list RTID 13052](https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId=13052)
- Sep 6 2023: ERCOT declared EEA2 and exited it the same evening with no rotating outages. — [ERCOT news: EEA2 initiated](https://www.ercot.com/news/release/2023-09-06-ercot-has-initiated); [ERCOT news: exited](https://www.ercot.com/news/release/2023-09-06-ercot-has-exited)

Recipe for each event (inference, built from the verified files above):

| Event | Prices (15-min RT, hourly DAM) | AS prices | Scarcity adders | Load | Fuel mix | Frequency |
|---|---|---|---|---|---|---|
| Uri, Feb 13-20 2021 | RTMLZHBSPP_2021 / DAMLZHBSPP_2021 | DAMASMCPC_2021 | RTM_ORDC_REL_DPLY_PRC_ADDR_RSRV_2021 | Native_Load_2021 | FuelMixReport_PreviousYears | event reports only (59.302 Hz nadir) |
| Elliott, Dec 22-24 2022 | *_2022 | DAMASMCPC_2022 | *_2022 | Native_Load_2022 | FuelMixReport_PreviousYears (UNVERIFIED coverage) | NP12-261-M 2022 sheet |
| Sep 6 2023 EEA2 | *_2023 | DAMASMCPC_2023 | *_2023 | Native_Load_2023 | as above | about 59.77 Hz (Q3 report) |
| Heather, Jan 13-17 2024 | *_2024, or the Public API query endpoints (after Dec 2023) | DAMASMCPC_2024 | *_2024 | Native_Load_2024 | as above | NP12-261-M 2024 sheet |
| Beryl, Jul 8 2024 | *_2024, or the Public API | DAMASMCPC_2024 | *_2024 | Native_Load_2024 (COAST zone) | as above | NP12-261-M 2024 sheet |

### Inferences
- The annual xlsx files are 14 to 22 MB unzipped. Pre-extract each event window into small CSVs, e.g. `scenarios/uri_2021/rt_spp.csv`, and commit those to the repo. Then the demo never has to hit ERCOT live.
- Beryl was mostly a distribution-level (CenterPoint) outage. It shows up as a drop in LZ_HOUSTON and COAST load rather than as scarcity pricing. This is my own background knowledge and is **UNVERIFIED** here. It fits the "feeder outage" scenario better than "generation scarcity".

### Gaps
- I did not verify the resolution of `FuelMixReport_PreviousYears.zip` or which years it covers, nor the 2021 Native_Load columns. I believe they are hourly by weather zone, but I did not open them, so this is **UNVERIFIED**.
- Whether the Public API `/bundle/{emilId}` covers 2021 and 2022 for NP6-905-CD is **UNVERIFIED** without a key.
- I did not open the official ERCOT, PUCT or FERC event reports for Elliott, Heather or Beryl.

---

## 7. ERCOT ADER (Aggregate Distributed Energy Resource) pilot: public data

### Takeaway
ERCOT publishes a monthly ADER workbook with no auth. It has a summary by month, monthly participation per resource and hourly participation per resource. There is also a limits-of-participation tracker broken down by settlement load zone. By 2026-08 there were **9 commercial ADERs** with **292.9 MW** qualified for energy. The pilot limits are 500 MW capacity, 100 MW Non-Spin and 100 MW ECRS, with no QSE allowed more than 90%.

### Cited Findings
- The ADER pilot page lists Governing Document Phase 3.3 (Jun 3 2026) and the "ADER Monthly Report" covering Jun 2025 to Jun 2026, published Sep 2 2026, at https://www.ercot.com/files/docs/2025/04/28/ADER_Monthly_Report_202506_202606.xlsx. It also lists the "Limits of Participation Tracking" file at https://www.ercot.com/files/docs/2025/05/06/Limits-of-Participation-Tracking_06-01-2026.xlsx, and earlier monthly reports back to early 2024. — [ERCOT ADER Pilot page](https://www.ercot.com/mktrules/pilots/ader)
- I downloaded the monthly report with no auth (HTTP 200, 34.6 KB). It has three sheets: `Summary of Commercial ADERs`, `Monthly Participation` and `Hourly Participation (06_2026)`.
  - Summary columns are `Month, No. of Commercial ADERs, Qualified Amt. for Energy (MW), Non-Spin (MW), ECRS (MW)`. Rows run from `2025-05: 3, 15.537, 8.6, 8.84` to `2026-08: 9, 292.941, 64.5, 97.3`.
  - Monthly and hourly sheets carry, per resource: `Total SCED Intervals, Online SCED Intervals, Intervals Carrying Non-Spin/ECRS, Dispatched, Avg. Online Bid, Avg. LMP While Dispatched`. Resource IDs are visible, e.g. `AR_ALD1`, `BOERNE_ALD1`, `MARION_ALD1`, `MIDNT_ALD1`.

  Verified. — [ADER Monthly Report xlsx](https://www.ercot.com/files/docs/2025/04/28/ADER_Monthly_Report_202506_202606.xlsx)
- The limits tracker is dated 06-01-26. It shows "500 MW Capacity, 100 MW Non-Spin, 100 MW ECRS" and "No QSE will be allowed to register more than 90% of these system-wide limits". Approved totals are 248.7 MW energy, 66.8 MW Non-Spin and 100 MW ECRS. By zone:

  | Zone | Energy (MW) | Non-Spin (MW) | ECRS (MW) |
  |---|---|---|---|
  | LZ_HOUSTON | 142 | 38.3 | 59.9 |
  | LZ_NORTH | 69.9 | 18.8 | 31.8 |
  | LZ_SOUTH | 24.9 | 5.7 | 7.5 |
  | LZ_LCRA | 1.6 | 0 | 0.8 |
  | LZ_AEN, LZ_CPS, LZ_RAYBN, LZ_WEST | 0 | 0 | 0 |

  DSP and QSE names are masked. Verified. — [Limits tracking xlsx](https://www.ercot.com/files/docs/2025/05/06/Limits-of-Participation-Tracking_06-01-2026.xlsx)
- Market notice M-A030226-01 (March 2026) raised the Registered Capacity Limit to 500 MW and the QSE limit from 50% to 90%. This is from a search summary. — [ERCOT M-A030226-01](https://www.ercot.com/services/comm/mkt_notices/M-A030226-01)
- A Phase 3 board item from June 2025 includes a Phase 2 report covering 2023-08-22 to 2025-05-01. This is from a search summary; the PDF was not opened. — [ERCOT ADER Phase 3 PDF](https://www.ercot.com/files/docs/2025/06/16/4.3-Aggregate-Distributed-Energy-Resource-ADER-Pilot-Project-Phase-3.pdf)

### Inferences
- The hourly participation sheet is realistic ground truth for how an aggregated home-battery VPP behaves in SCED: how many intervals it is online, how often it carries Non-Spin or ECRS, and its average bid. Use it to calibrate the orchestration layer's "fleet as one resource" abstraction.

### Gaps
- Which ADER resource IDs belong to which aggregator is masked or unstated. I did not attempt to identify Base Power's resources.

---

## 8. Third-party routes (gridstatus, GridStatus.io, EIA-930, others)

### Takeaway
The fastest route is the open-source **`gridstatus`** Python library. Its `Ercot()` class needs no key, because it wraps the dashboards, MIS listings and annual archives. Its `ErcotAPI()` class needs ERCOT Public API credentials. **GridStatus.io**'s hosted API needs a free key, capped at 500,000 rows per month. **EIA API v2** (EIA-930 hourly ERCOT demand, forecast, net generation and fuel mix) needs a free key and returns at most 5,000 rows per JSON response.

### Cited Findings
- gridstatus is at v0.36.0 (released 2026-04-21), BSD-3-Clause, Python `>=3.10,<3.15`. — [PyPI gridstatus](https://pypi.org/project/gridstatus/); [GitHub releases](https://github.com/gridstatus/gridstatus/releases)
- `Ercot()` (no key) methods include `get_fuel_mix(date)`, `get_load(date)`, `get_spp(date, market=..., location_type=...)`, `get_as_prices(date)`, `get_real_time_system_conditions()`, `get_rtm_spp(year)` (NP6-785-ER), `get_dam_spp(year)`, `get_load_forecast(date)`, `get_energy_storage_resources()`, `get_system_as_capacity_monitor()`, `get_mcpc_real_time_15_min`, `get_real_time_adders`, `get_as_demand_curves_dam_and_sced` and others. — [gridstatus ercot.py](https://github.com/gridstatus/gridstatus/blob/main/gridstatus/ercot.py)
- `ErcotAPI()` requires the environment variables `ERCOT_API_USERNAME`, `ERCOT_API_PASSWORD` and `ERCOT_PUBLIC_API_SUBSCRIPTION_KEY`, plus `ERCOT_ESR_API_SUBSCRIPTION_KEY` for ESR data. Its methods include `get_spp_real_time_15_min`, `get_spp_day_ahead_hourly`, `get_lmp_by_settlement_point`, `get_as_prices`, `get_load_by_weather_zone`, `get_60_day_sced_disclosure`, `get_system_load_charging_4_seconds` and `get_historical_data`. — [gridstatus ercot_api.py](https://github.com/gridstatus/gridstatus/blob/main/gridstatus/ercot_api/ercot_api.py)
- GridStatus.io client: install with `uv pip install gridstatusio`, set `GRIDSTATUS_API_KEY`, then call `GridStatusClient().get_dataset("ercot_fuel_mix", ..., limit=1000)`. "The free plan allows 500,000 rows per month." — [gridstatusio README](https://github.com/gridstatus/gridstatusio/blob/main/README.md)
- The GridStatus `/v1/api_usage` example response shows fields such as `api_rows_returned_limit`, `api_requests_limit`, `api_rows_per_response_limit`, `per_second_api_rate_limit` and `per_minute_api_rate_limit`. The values shown are examples, not free-tier values. — [GridStatus docs: API Usage](https://docs.gridstatus.io/developers/api-reference/api-usage)
- EIA: an unauthenticated call to `https://api.eia.gov/v2/electricity/rto/region-data/data/?frequency=hourly&data[0]=value&facets[respondent][]=ERCO` returned HTTP 403, `{"error":{"code":"API_KEY_MISSING", ... "register for one at https://www.eia.gov/opendata/register.php"}}`. Verified. — [EIA API](https://api.eia.gov/v2/electricity/rto/region-data/data/)
- EIA keys are free and emailed automatically. JSON responses return at most 5,000 rows (XML 300). Heavy users "must throttle ... per second and per hour", with automatic temporary suspension, but no numeric limit is stated. — [EIA API documentation](https://www.eia.gov/opendata/documentation.php)
- EIA's hourly grid monitor covers demand and generation by source for 64 balancing authorities, including ERCOT. — [EIA electricity (ERCOT)](https://www.eia.gov/electricity/?rto=ercot); [EIA API browser region-data](https://www.eia.gov/opendata/browser/electricity/rto/region-data)

Snippets (install commands are standard; code is based on the verified signatures above but not executed here, because pandas was not installed in my test shell):
```bash
pip install gridstatus        # no key needed for Ercot()
pip install gridstatusio      # needs GRIDSTATUS_API_KEY (free, 500k rows/month)
```
```python
import gridstatus
ercot = gridstatus.Ercot()                      # no credentials
fm   = ercot.get_fuel_mix("today")              # 5-min fuel mix (dashboard)
spp  = ercot.get_spp("today", market="REAL_TIME_15_MIN", location_type="Load Zone")  # market enum string UNVERIFIED
uri  = ercot.get_rtm_spp(2021)                  # NP6-785-ER annual archive (verified source file)
rtsc = ercot.get_real_time_system_conditions()  # frequency, inertia, demand

from gridstatus.ercot_api.ercot_api import ErcotAPI   # needs ERCOT_API_USERNAME / _PASSWORD / _PUBLIC_API_SUBSCRIPTION_KEY
api = ErcotAPI()
rt  = api.get_spp_real_time_15_min(date="2024-07-08", end="2024-07-09")
```
```bash
# EIA-930 ERCOT hourly demand (D), day-ahead forecast (DF), net generation (NG); key via env var
curl -s "https://api.eia.gov/v2/electricity/rto/region-data/data/?api_key=$EIA_API_KEY&frequency=hourly&data[0]=value&facets[respondent][]=ERCO&facets[type][]=D&sort[0][column]=period&sort[0][direction]=desc&length=48"
# fuel mix: /v2/electricity/rto/fuel-type-data/data/ with facets[respondent][]=ERCO  (route name UNVERIFIED by test)
```

### Inferences
- For the hackathon, `gridstatus.Ercot()` with no key, plus direct dashboard polling, covers about 90% of needs in minutes. Keep `ErcotAPI` for filtered historical pulls if someone registers.
- EIA-930 adds nothing beyond ERCOT's own data at hourly resolution, and it lags. Its main value is a cross-check, or comparing ERCOT with other ISOs.

### Gaps
- **pyiso**: not researched. I believe it is largely unmaintained, but that is **UNVERIFIED**.
- **Modo Energy / Ascend Analytics free data**: not researched, so there are no verified free-tier terms. **UNVERIFIED.**
- The exact enum strings for `get_spp(market=...)` and the EIA `fuel-type-data` route were not execution-tested.
- The EIA-930 publication lag for ERCOT is **UNVERIFIED**.

---

## 9. Licensing and terms of use (can the team redistribute in a public GitHub repo or demo?)

### Takeaway
Yes, raw ERCOT public data may be redistributed in compilations, charts and analyses without keeping ERCOT's notices. Four limits apply:
- Don't present modified ERCOT *content* (documents, pages) as unmodified.
- Don't use the ERCOT logo or trademarks.
- Don't hammer the site.
- For API and Data Access Portal downloads, don't re-download the same report more than 3 times in 12 months. Cache locally.

### Cited Findings
- Website terms, last updated 07/20/2023: "The publicly available contents of this website may be used, reproduced, and redistributed, provided that the contents are not modified and that you maintain all copyright and other notices..." and "raw data provided in public portions of this website may be used, reproduced, and redistributed in compilations, charts, and analyses without maintaining such notices." "ERCOT does not guarantee the accuracy of any such compilations, charts, or analyses." The terms also prohibit "use of this website in a manner that negatively affects the performance of this website or other ERCOT systems". The ERCOT logo and "ERCOT" are trademarks, which "may not be used without the prior written permission of ERCOT." — [ERCOT Terms of Use](https://www.ercot.com/help/terms)
- API terms: "You may not download the same report from the Data Access Portal more than three times within a 12-month period." Rate limits are enforced "in ERCOT's sole discretion". Everything is provided "As Is". I found no explicit redistribution clause and no attribution requirement. — [Terms of Use for ERCOT API](https://www.ercot.com/help/terms/data-portal)
- GridStatus.io and EIA terms were not reviewed. **Gap.**

### Inferences
- Committing extracted CSVs (e.g. scenario windows) to a public repo is consistent with the "raw data ... compilations" clause. Add a README line along the lines of "Source: ERCOT public data; ERCOT does not guarantee accuracy of this compilation", and don't use ERCOT branding in the demo UI.
- Never commit API subscription keys or passwords. Use environment variables or a `.env` listed in `.gitignore`.

### Gaps
- There is no explicit statement on whether data pulled through the API, as opposed to the website, falls under the website's "raw data" redistribution clause. I infer that it does, but it is **UNVERIFIED**.

---

## 10. Update latency by channel

### Takeaway
Measured on 2026-09-25 around 19:25 to 19:31 CDT:
- SCED-based reports (LMPs, lambda, adders) post about **2 seconds** after each SCED run.
- 15-minute SPPs and RT AS MCPCs post about **2 minutes** after the interval ends.
- Dashboard frequency and PRC lag about 1 to 2 minutes (frequency) and less than 10 s (PRC).
- The fuel mix and ESR dashboards run about 5 to 10 minutes behind.
- Hourly forecasts post near the top of each hour.
- Actual load by zone posts once a day, at about 05:50 for the prior day.
- DAM results post about 12:40 the day before the operating day.
- 60-day disclosures lag by 60 days.

### Cited Findings
The MIS listing (no auth) was fetched at 2026-09-26 00:30:38 UTC (19:30:38 CDT). "Latest" is the newest file's friendly name and publish time. — `https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId=<RTID>`
- NP6-788-CD (12300): `LMPSROSNODENP6788_20260925_192522` published **19:25:24**, 2 s after the SCED timestamp 19:25:22. 3,406 files kept, the oldest from 2026-09-20.
- NP6-322-CD (13114) and NP6-323-CD (13221): the SCED run at 19:25:22 was published at 19:25:24.
- NP6-905-CD (12301): the interval ending 19:15 (`SPPHLZNP6905_20260925_1915`) was published **19:17:01**. Files expire after 7 days (`ExpiredDate` 2026-10-02 on the 09-25 file). 1,500 files were listed.
- NP6-331-CD (24898): the latest 15-minute RT MCPC was published 19:17:00. NP6-332-CD (24891): the latest was published 19:30:22.
- NP4-190-CD and NP4-188-CD (DAM): published **12:41:14** on 09-25 for operating day 09-26.
- NP6-345-CD and NP6-346-CD (actual load): published **05:50:00** on 09-25 for 09-24.
- NP3-565-CD: 18:30:00. NP4-732-CD and NP4-745-CD: 18:55. NP6-86-CD: 19:05. NP3-233-CD: 19:00:47. NP3-763-CD: 19:00:52. NP6-235-CD: 19:05.
- NP3-965-ER (60-day SCED): published 05:13:54 daily. 923 files listed, the oldest published 2024-03-24.
- Dashboards, per the Section 3 tests:
  - `daily-prc.json`: last point 19:24:52, fetched 19:24:52.
  - `ancillary-services.json`: frequency last point 19:23:20, fetched about 19:24.
  - `system-wide-prices.json`: the 19:15 interval was present, lastUpdated 19:17.
  - `fuel-mix.json` and `energy-storage-resources.json`: last point 19:20, fetched about 19:25.
  - `supply-demand.json`: lastUpdated 19:20.
  - Cache headers: `max-age=60` on all of these except `daily-prc` (`max-age=10`) and `weather-forecast` (`no-store`).
- The Public API serves the same EMIL files. I did not measure its lag, because I had no key (**UNVERIFIED**; it is presumably the same or seconds later).

### Inferences
- Live mode: tick the simulator every 5 minutes on NP6-788 LMPs, or the dashboard fuel mix and ESR feeds. Settle every 15 minutes on NP6-905 SPP. Stream frequency and PRC every 10 s from the dashboards.
- Use NP6-970-CD (RTD indicative LMPs) or NP3-565-CD, NP4-732-CD and NP4-745-CD as the orchestrator's forward look.

### Gaps
- I measured each report once. Latency percentiles and outage behaviour, such as delayed or corrected prices, are not characterized. NP4-196-M and NP4-197-M record price corrections.

---

## Consolidated catalog

### Takeaway
You can start building now with no credentials:
- **Live mode:** dashboard JSON feeds, plus MIS EMIL files for LMPs and RT MCPC.
- **History:** the MIS annual archives, plus the Native_Load and IntGenbyFuel files.

Register for the ERCOT Public API only if you need filtered queries or `/archive` bulk pulls. If you do, one key per person.

### Cited Findings
- Every row below is sourced in Sections 1 to 10.

### Inferences
- For a public repo, commit extracted event-window CSVs and fetch live data at runtime.

### Gaps
- Anything marked N in the Verified column.

### Catalog table

| Dataset | Endpoint/URL | Auth | Granularity | Latency (observed) | History depth | Simulator use | Verified (Y/N) |
|---|---|---|---|---|---|---|---|
| System frequency (live) | `https://www.ercot.com/api/1/services/read/dashboards/ancillary-services.json` (`data[].currentFrequency`) | None | 10 s | about 1-2 min | last 2 h | Frequency state, triggers for fast frequency response / FFR dispatch | Y |
| Frequency + inertia + DC ties | `.../dashboards/dc-tie-flows.json` | None | 10 s | about 1-2 min | since local midnight | Frequency/inertia model; poll to build history | Y |
| Instantaneous RT conditions (freq, time error, demand, capacity, wind, PV, inertia) | `https://www.ercot.com/content/cdr/html/real_time_system_conditions.html` | None | snapshot, 60 s refresh | about 1 min | none | Live HUD | Y |
| Grid condition / EEA level / PRC | `.../dashboards/daily-prc.json` | None | about 8-10 s | <10 s | today | Emergency state machine (EEA0-3), reserve margin | Y |
| AS capacity monitor (RegUp/Dn, RRS, NSRS, ECRS deployed/undeployed) | `.../dashboards/ancillary-services.json` (`ascapmon`) and `.../ancillary-service-capacity-monitor.json` | None | about 8 s / snapshot | <1-2 min | 2 h / snapshot | AS headroom; when the fleet's AS matters | Y |
| Fuel mix (incl. Power Storage) | `.../dashboards/fuel-mix.json` | None | 5 min | about 5 min | yesterday + today | Generation stack, carbon intensity, storage share | Y |
| ESR fleet charge/discharge (system) | `.../dashboards/energy-storage-resources.json` | None | 5 min | about 5 min | yesterday + today | Benchmark the fleet vs grid-scale batteries | Y |
| Supply/demand + 6-day forecast | `.../dashboards/supply-demand.json` | None | 5 min actual; hourly forecast | about 5 min | today + 6 days ahead | Load driver, capacity margin | Y |
| Hub/LZ prices RT 15-min + DAM | `.../dashboards/system-wide-prices.json` | None | 15 min / hourly | about 2 min after interval | today | Price signal for charge/discharge | Y |
| Hourly load vs forecast + HSL | `.../dashboards/system-wide-demand.json` | None | hourly | hourly | prev/cur/next day | Forecast error scenarios | Y |
| Wind/solar actual + STWPF/STPPF | `.../dashboards/combine-wind-solar.json` | None | hourly | hourly | today + tomorrow | Renewable variability, net load | Y |
| Generation outages (planned/unplanned) | `.../dashboards/generation-outages.json` | None | 5 min | about 5 min | about 7 days | Generator-trip scenario baseline | Y |
| Weather forecast (12 cities) | `.../dashboards/weather-forecast.json` | None | daily hi/lo | daily | forecast only | Heat wave / cold snap triggers | Y |
| SPP (nodes, hubs, LZs) NP6-905-CD | MIS RTID 12301; API `/np6-905-cd/spp_node_zone_hub` | None (MIS) / key+token (API) | 15 min | about 2 min | MIS 7 days; API since Dec 2023 + archives ≥7 yr | Settlement prices per member zone (LZ_AEN, LZ_HOUSTON, LZ_NORTH) | Y (MIS); N (API call) |
| LMPs per SCED NP6-788-CD | MIS RTID 12300; API `/np6-788-cd/lmp_node_zone_hub` | None / key+token | 5 min (per SCED) | about 2 s after SCED | MIS 5 days | 5-min dispatch price | Y (MIS) |
| RTD indicative LMPs NP6-970-CD | API `/np6-970-cd/rtd_lmp_node_zone_hub`; MIS RTID 13073 | key+token / None | 5 min, look-ahead | not measured | 5 days (MIS) | Orchestrator short-horizon forecast | N (not downloaded) |
| SCED system lambda NP6-322-CD | MIS 13114; API `/np6-322-cd/sced_system_lambda` | None / key+token | per SCED | about 2 s | 5 days | System marginal energy price | Y (MIS listing) |
| RT price adders NP6-323-CD (post-RTC+B) | MIS 13221; API `/np6-323-cd/rt_price_adder_sced` | None / key+token | per SCED | about 2 s | 5 days | Scarcity adder component | Y |
| RT AS MCPC 15-min NP6-331-CD (RTC+B) | MIS 24898; API `/np6-331-cd/rt_clear_price_cap` | None / key+token | 15 min, 5 AS types | about 2 min | since 2025-12-05 | AS revenue for fleet (RegUp/Dn, RRS, ECRS, NSPIN) | Y |
| RT AS MCPC per SCED NP6-332-CD | MIS 24891; API `/np6-332-cd/rt_clear_price_cap_sced` | None / key+token | per SCED | <1 min | 7 days (MIS) | Same, 5-min | Y (listing) |
| DAM SPP NP4-190-CD | MIS 12331; API `/np4-190-cd/dam_stlmnt_pnt_prices` | None / key+token | hourly | about 12:40 day-ahead | MIS 31 days | Day-ahead schedule for fleet | Y (listing) |
| DAM hourly LMP NP4-183-CD | MIS 12328; API `/np4-183-cd/dam_hourly_lmp` | None / key+token | hourly | day-ahead | MIS 31 days | Day-ahead nodal | Y (page) |
| DAM AS MCPC NP4-188-CD | MIS 12329; API `/np4-188-cd/dam_clear_price_for_cap` | None / key+token | hourly × 5 AS | about 12:40 day-ahead | MIS 31 days | Day-ahead AS co-optimization | Y |
| AS demand curves NP4-212-CD | API `/np4-212-cd/dam_sced_as_demand_curves` | key+token | per run | not measured | since RTC+B | Scarcity modelling post-RTC+B | N |
| Actual load by weather zone NP6-345-CD | MIS 13101; API `/np6-345-cd/act_sys_load_by_wzn` | None / key+token | hourly | daily about 05:50 for prior day | MIS 31 days | Zonal load (SOUTH_C for Austin, COAST, NORTH_C) | Y |
| Actual load by forecast zone NP6-346-CD | MIS 14836; API `/np6-346-cd/act_sys_load_by_fzn` | None / key+token | hourly | daily about 05:50 | MIS 31 days | Zonal load (NORTH/SOUTH/WEST/HOUSTON) | Y |
| System-wide demand NP6-235-CD | MIS 12340; API `/np6-235-cd/system_wide_demand` | None / key+token | 15 min | hourly posting | MIS 7 days | System load | Y |
| 7-day load forecast by model & weather zone NP3-565-CD | MIS 14837; API `/np3-565-cd/lf_by_model_weather_zone` | None / key+token | hourly × 7 days × models | hourly | MIS 7 days | Orchestrator load forecast | Y |
| 7-day load forecast by forecast zone NP3-560-CD | MIS 12311; API `/np3-560-cd/7d_load_fcast_by_fzn` | None / key+token | hourly | hourly | MIS 7 days | Same | Y (page) |
| Wind hourly actual+forecast NP4-732-CD (geo: NP4-742-CD) | MIS 13028; API `/np4-732-cd/wpp_hrly_avrg_actl_fcast` | None / key+token | hourly (5-min actuals: NP4-733-CD) | hourly (:55) | MIS 7 days | Net load, renewable dip scenarios | Y (listing) |
| Solar hourly actual+forecast NP4-745-CD (system: NP4-737-CD) | MIS 21809; API `/np4-745-cd/spp_hrly_actual_fcast_geo` | None / key+token | hourly (5-min: NP4-738/746) | hourly (:55) | MIS 7 days | Solar ramp / duck curve | Y (listing) |
| Hourly resource outage capacity NP3-233-CD | MIS 13103; API `/np3-233-cd/hourly_res_outage_cap` | None / key+token | hourly | hourly | MIS 31 days | Generator-trip / outage scenarios | Y (listing) |
| Short-term system adequacy NP3-763-CD | MIS 12315; API `/np3-763-cd/st_sys_adequacy` | None / key+token | hourly | hourly | MIS 31 days | Forward capacity tightness | Y (listing) |
| SCED shadow prices / binding constraints NP6-86-CD | MIS 12302; API `/np6-86-cd/shdw_prices_bnd_trns_const` | None / key+token | per SCED, hourly posting | hourly | MIS 7 days | Congestion on synthetic feeders | Y (listing) |
| 2-Day AS reports NP3-911-ER | MIS 13057; API `/np3-911-er/2d_*` | None / key+token | hourly | 2-day lag | MIS 31 days | AS market depth | Y (page) |
| 60-day SCED / DAM disclosure NP3-965-ER / NP3-966-ER | MIS 13052 / 13051; API `/np3-965-er/...`, `/np3-966-er/...` | None / key+token | per SCED / hourly | 60-day lag | MIS 1,462-day display (oldest listed 2024-03-24) | Unit-level ESR bids/dispatch behaviour | Y (listing) |
| ESR 4-second data | `https://api.ercot.com/api/public-data/rptesr-m/4_sec_esr_charging_mw` | key (ESR product)+token | 4 s | not measured (monthly "-M"?) | since 2025-05-29 | High-res storage behaviour for fast dispatch | N |
| Historical RTM hub/LZ SPP NP6-785-ER | MIS 13061 (`RTMLZHBSPP_YYYY`), `mirDownload?doclookupId=` | None | 15 min | weekly update | 2010-2026 | Uri/Elliott/2023/Heather/Beryl replays | Y (2021 parsed) |
| Historical DAM hub/LZ SPP NP4-180-ER | MIS 13060 (`DAMLZHBSPP_YYYY`) | None | hourly | weekly | 2010-2026 | Replays | Y (listing) |
| Historical DAM AS MCPC NP4-181-ER | MIS 13091 (`DAMASMCPC_YYYY`) | None | hourly | weekly | 2010-2026 | Replays with AS revenue | Y (listing) |
| Historical RT adders (ORDC era) NP6-792-ER / NP6-793-ER | MIS 13231 / 13240 | None | per SCED / 15 min | weekly | 2014-2026 | Pre-RTC+B scarcity pricing in replays | Y (listing) |
| Native load archives | `https://www.ercot.com/gridinfo/load/load_hist` (e.g. `files/docs/2021/11/12/Native_Load_2021.zip`) | None | hourly (by weather zone, UNVERIFIED) | annual/periodic | 2002-2026 | Load replay | Y (links); N (contents) |
| Fuel mix archives | `https://www.ercot.com/gridinfo/generation` (`IntGenbyFuel2025.xlsx`, `FuelMixReport_PreviousYears.zip`) | None | 15 min (UNVERIFIED) | annual | multi-year (UNVERIFIED) | Generation mix replay | Y (links); N (contents) |
| Frequency measurable events NP12-261-M | MIS 13450 (`ERCOT_FrequencyMeasurableEvents_AsOf_*.xlsx`) | None | per event | weekly | 2015-2026 | Calibrate generator-trip scenario (MW loss → nadir) | Y |
| ADER pilot monthly report + limits tracker | `https://www.ercot.com/files/docs/2025/04/28/ADER_Monthly_Report_202506_202606.xlsx`; `.../2025/05/06/Limits-of-Participation-Tracking_06-01-2026.xlsx` | None | monthly + hourly-by-resource | monthly | 2024-2026 | Calibrate aggregated-DER (VPP) behaviour | Y |
| ERCOT Public API catalog | `GET https://api.ercot.com/api/public-reports/` (+ `/archive/{emilId}`, `/bundle/{emilId}`) | Subscription key + B2C id_token | per product | per product | query: from activation (Dec 2023+); files ≥7 yr | Filtered/bulk historical pulls | N (401 without key, as expected) |
| gridstatus (OSS) | `pip install gridstatus`; `gridstatus.Ercot()` | None (Ercot) / ERCOT creds (ErcotAPI) | wraps above | wraps above | wraps above | Fastest Python path | Y (source read); N (not executed) |
| GridStatus.io hosted API | `api.gridstatus.io/v1`, `pip install gridstatusio` | Free API key | per dataset | not measured | per dataset | Clean, normalized pulls | N |
| EIA-930 (API v2) | `https://api.eia.gov/v2/electricity/rto/region-data/data/?facets[respondent][]=ERCO` | Free API key | hourly | not measured (UNVERIFIED) | multi-year | Cross-check demand/fuel mix | Y (403 without key); N (data) |
