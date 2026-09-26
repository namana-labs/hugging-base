# Public (non-ERCOT) datasets and open-source tools for a synthetic Austin distribution grid and battery-fleet simulator

_Research date 2026-09-25 (Austin time). I ran all live access tests from a Mac on 2026-09-26 between 00:25 and 00:50 UTC. "Tested" means I fetched the URL with curl or Python myself; HTTP status and a trimmed sample are recorded. No accounts were created and no credentials were used. The only key used was NREL/NLR's public `DEMO_KEY`. Anything not confirmed by a test or a primary page is marked UNVERIFIED._

---

## 1. Synthetic distribution feeders: SMART-DS, IEEE, GridLAB-D taxonomy, Texas synthetic grids. Which is quickest to adapt for ~1,000 homes?

### Takeaway
NREL SMART-DS has a real **Austin (AUS)** region: six sub-regions of synthetic 12.47 kV feeders built on real Austin building locations. Each ships in OpenDSS, CYME and per-feeder GeoJSON, with **WGS84 lon/lat bus coordinates in north Austin** and 15-minute ResStock-derived load profiles for 2016–2018. It is public on S3 with no key, licensed CC BY 4.0, and includes pre-built solar and battery placement scenarios.

A single SMART-DS feeder with ~1,000 customers is the fastest route to "1,000 homes on a real-looking Austin feeder." Several exist (for example `p1uhs19_1247--p1udt17263`, with 1,012 customers and a 7.0 MW peak). A single substation is only about 6 MB of OpenDSS files. The alternatives fall short:
- **IEEE test feeders** are tiny and abstract.
- **GridLAB-D taxonomy feeders** are generic US prototypes with no geography.
- **Texas A&M ACTIVSg** grids are transmission-level, not distribution.

### Cited Findings
- **Catalog entry.** SMART-DS OEDI submission 2981: "SMART-DS Synthetic Electrical Network Data OpenDSS Models for SFO, GSO, and AUS". License **CC BY 4.0**, total **5.32 TB**, location `s3://oedi-data-lake/SMART-DS/`, published 2020-12-18, citation Palmintier et al. — [OEDI 2981](https://data.openei.org/submissions/2981)
- **Tested S3 layout** (anonymous S3 listing, HTTP 200, no key):
  - `SMART-DS/v1.0/` contains `2016/`, `2017/`, `2018/`, `GIS/`, `User_Guide/`, `peak/` and `placements/`.
  - `SMART-DS/v1.0/2018/AUS/` contains `P1R/`, `P1U/`, `P2U/`, `P3U/`, `P4U/`, `P5U/` and `full_dataset_analysis/`.
  - Source: [S3 listing AUS](https://oedi-data-lake.s3.amazonaws.com/?list-type=2&prefix=SMART-DS/v1.0/2018/AUS/&delimiter=/)
- **User guide, Austin region.** "The Austin dataset contains six sub-regions... five urban regions P1U-P5U and one rural region P1R. The Austin dataset also contains a small Powerworld transmission model" — [SMART-DS User Guide Readme.md](https://oedi-data-lake.s3.amazonaws.com/SMART-DS/v1.0/User_Guide/Readme.md)
- **User guide, model content** (same source):
  - Models were produced in CYME and OpenDSS. They "capture electrical connections at all levels... sub-transmission lines, substations, distribution feeders and secondaries from distribution transformers to customers."
  - They "connect to real buildings which have synthetic load patterns attached," while "the networks themselves are entirely synthetic."
  - Protection equipment is included (fuses, reclosers, GOABs, open tie switches), as are regulators and capacitors.
  - Equipment was sized by RNM-US and validated statistically against real utility feeders.
  - Each sub-region has a 230 kV source node `st_mat` and a 69 kV subtransmission network.
- **User guide, loads** (same source):
  - Timeseries loads cover 365 days of 2016, 2017 and 2018 at **15-minute resolution**.
  - Residential and commercial profiles come from ResStock and ComStock.
  - `load_data/*.parquet` files carry end-use columns (`total_site_electricity_kw`, `heating_kw`, `cooling_kw`, `lighting_kw`, `fans_kw`, and more).
  - Profile CSVs are expressed as a fraction of the annual maximum.
- **User guide, known caveats** (same source):
  - Post-processing included "Increase line and transformer capacity to prevent overloads for timeseries scenarios."
  - "Timeseries dispatch of batteries is not presently included."
  - "Sizing of grid-related features does not presently consider the network topology, which may cause line and transformer overloads as well as voltage violations in the integrated scenarios."
- **Tested scenario folders.** `AUS/P1U/scenarios/` contains `base_timeseries` plus `solar_{none,low,medium,high,extreme}_batteries_{none,low,high}_timeseries`. Each has `cyme/`, `geojson/`, `opendss/`, `opendss_no_loadshapes/` and a `metrics.csv`. — [S3 listing](https://oedi-data-lake.s3.amazonaws.com/?list-type=2&prefix=SMART-DS/v1.0/2018/AUS/P1U/scenarios/&delimiter=/)
- **Tested feeder statistics** (AUS P1U `metrics.csv`, parsed):
  - 96 feeder rows (95 non-empty) under 26 substations, **65,529 customers** in total.
  - **Median 663.5 customers per feeder** (max 1,872).
  - **Median peak planning load 6.9 MW** (max 17.0 MW).
  - Median 238.5 service transformers per feeder.
  - **Median 2.5 loads per service transformer** (max 4.4).
  - Nominal source 12.47 kV; the county column reads "Travis".
  - Source: [metrics.csv](https://oedi-data-lake.s3.amazonaws.com/SMART-DS/v1.0/2018/AUS/P1U/scenarios/base_timeseries/metrics.csv)
- **Tested feeders closest to 1,000 customers** (same file):

  | Feeder | Customers | Peak | Service transformers | Transformer capacity | Residential |
  |---|---|---|---|---|---|
  | `p1uhs19_1247--p1udt17263` | 1,012 | 7.02 MW | 379 | 17.6 MVA | 98.2% |
  | `p1uhs23_1247--p1udt25139` | 1,014 | 6.21 MW | 342 | 15.8 MVA | 97.9% |
  | `p1uhs9_1247--p1udt21819` | 981 | 5.95 MW | 260 | 13.7 MVA | 99.8% |
  | `p1uhs21_1247--p1udt11662` | 1,021 | 7.05 MW | 356 | 17.8 MVA | 96.1% |
  | `p1uhs16_1247--p1udt16473` | 1,037 | 6.80 MW | 373 | 17.3 MVA | 99.1% |

  Substation `p1uhs0` has three feeders with 878, 776 and 1,872 customers.
- **Tested download size.** The substation folder `.../base_timeseries/opendss/p1uhs0_1247/` holds 78 files totaling **6.13 MB**. That excludes the shared `profiles/` folder its LoadShapes reference. OpenDSS fails to compile the `opendss/` variant without `profiles/`, but the `opendss_no_loadshapes/` variant compiles standalone. — [S3 listing p1uhs0](https://oedi-data-lake.s3.amazonaws.com/?list-type=2&prefix=SMART-DS/v1.0/2018/AUS/P1U/scenarios/base_timeseries/opendss/p1uhs0_1247/)
- **Tested map-readiness.** `Buscoords.dss` holds lon/lat, for example `sb2_p1uhs0_1247_node_2_11 -97.7123312 30.4196007`. The 9,819 buses of `p1uhs0` span lon −97.731 to −97.696 and lat 30.402 to 30.437, which is north Austin. — [Buscoords.dss](https://oedi-data-lake.s3.amazonaws.com/SMART-DS/v1.0/2018/AUS/P1U/scenarios/base_timeseries/opendss/p1uhs0_1247/Buscoords.dss)
- **Tested GeoJSON.** Per-feeder files range from 0.22 to 8.75 MB (for example `p1uhs0_1247--p1udt12703.json` is 8.75 MB). — [geojson listing](https://oedi-data-lake.s3.amazonaws.com/?list-type=2&prefix=SMART-DS/v1.0/2018/AUS/P1U/scenarios/base_timeseries/geojson/)
- **GIS layers.** GIS shapefiles plus `AUS_QGIS.qgs` are provided. The layers cover transmission substations (230–69 kV), distribution substations (69 kV to 4/12.47/25 kV), feeders and distribution transformers. They carry a warning: the shapefiles "were produced before post-processing... may differ from the OpenDSS and CYME models." — [GIS warning.md](https://oedi-data-lake.s3.amazonaws.com/SMART-DS/v1.0/GIS/warning.md); [Readme](https://oedi-data-lake.s3.amazonaws.com/SMART-DS/v1.0/User_Guide/Readme.md)
- **IEEE test feeders.** The IEEE PES test feeder resource page returned HTTP 403 to curl, so details are UNVERIFIED from a primary source. The commonly cited specs are 13-bus at 4.16 kV, 34-bus at 24.9 kV and 123-bus at 4.16 kV. OpenDSS versions of the IEEE cases live in the dss-extensions test repository (verified to exist via the GitHub API; last push 2024-06-24). — [IEEE PES Test Feeders](https://cmte.ieee.org/pes-testfeeders/resources/); [dss-extensions/electricdss-tst](https://github.com/dss-extensions/electricdss-tst)
- **GridLAB-D taxonomy feeders.** The repository `gridlab-d/Taxonomy_Feeders` exists (11 stars, last push 2024-01-30, verified via the GitHub API). The underlying PNNL report (PNNL-18035) returned HTTP 403, so the "24 prototypical feeders" description is UNVERIFIED. — [GitHub Taxonomy_Feeders](https://github.com/gridlab-d/Taxonomy_Feeders); [PNNL-18035](https://www.pnnl.gov/main/publications/external/technical_reports/PNNL-18035.pdf)
- **ACTIVSg2000** is a 2,000-bus, entirely synthetic Texas **transmission** case. Formats: PowerWorld, Matpower, PSS/E raw and PSLF. It is "free for commercial or non-commercial use"; users are asked to fill in a form and cite the papers. This is from a search snippet of the TAMU page, not fetched. — [TAMU ACTIVSg2000](https://electricgrids.engr.tamu.edu/electric-grid-test-cases/activsg2000); [GitHub mirror caseformat/ACTIVSg2000](https://github.com/caseformat/ACTIVSg2000/). TAMU also lists a Texas2k "series25" page and ACTIVSg10k (contents UNVERIFIED). — [TAMU texas2k-series25](https://electricgrids.engr.tamu.edu/texas2k-series25/)

### Inferences
- **SMART-DS AUS is the clear pick.** It already gives exactly the object the team described: homes grouped on feeders under substations, with transformer ratings, 15-minute AC-heavy load, solar and battery placement files, and map coordinates. No other free source combines distribution topology with Austin geography.
- **Which slice to use.** For "~1,000 homes on a few feeders," use one ~1,000-customer feeder and treat its laterals as zones. Alternatively take a whole substation with 2–3 feeders (for example `p1uhs0`, 3,526 customers) and sub-sample homes for the UI.
- **The feeders are not stressed as shipped.** Service transformers are upsized about 10% (27.5/55/82.5 kVA, see §9), and the README says capacity was increased to avoid overloads. To create a stressed feeder for the "each additional battery" question, de-rate transformers back to 25/50/75 kVA nameplate, or scale load or battery export.
- **Label it synthetic.** The networks are synthetic even though they sit on real Austin buildings. `p1uhs0` falls in north Austin, which in reality is Austin Energy territory (see §3). Label it a "synthetic Austin-area grid" in the demo.
- **Everything else is second-tier.** IEEE 13/34/123 are too small (under 200 buses) and have no geography. ACTIVSg is only useful for a transmission "generator trip" backdrop, and the ERCOT researcher covers that more directly.

### Gaps
- I did not measure the total size of one AUS sub-region's `profiles/` and `load_data/` folders because the listings paginate. Individual solar profile CSVs are about 261 KB each.
- IEEE feeder parameters and the PNNL taxonomy report contents were not fetched (HTTP 403).
- I did not check whether the 2016 and 2017 AUS networks differ from 2018.

---

## 2. Power-flow and grid-simulation libraries: speed at 1,000 nodes and 1–5 minute steps, the hackathon pick, and whether a "feeder capacity bucket" model is defensible

### Takeaway
Speed is not a constraint. I measured both candidates on this Mac:
- **OpenDSSDirect.py** solved a real SMART-DS Austin substation (9,820 buses, 6,817 loads, 1,302 transformers) in **41 ms per snapshot**. 288 successive solves, one day at 5-minute steps, took **1.1 s**.
- **pandapower** solved a 1,000-home, 1,411-bus synthetic radial feeder in **14 ms per power flow**, even without numba. That is about 4 s per simulated day at 5-minute steps.

Use OpenDSSDirect.py if the team adopts SMART-DS, since it is the native format and handles unbalanced single-phase secondaries. Use pandapower if they generate their own network. Skip GridLAB-D, HELICS and PyPSA for a 48-hour build.

A capacity-bucket model is defensible as the **controller's internal model**, with power flow as ground truth. It should not replace the physics: voltage limits bind as well as thermal limits, as the 0.907 pu minimum voltage below shows.

### Cited Findings
- **Tested pandapower speed** (pandapower 3.5.5, Python 3.14, numba not installed):
  - Network: one 12.47 kV external grid, 10 laterals × 20 service transformers of 50 kVA × 5 homes = **1,000 homes, 1,411 buses, 200 transformers**.
  - Result: **14 ms per balanced Newton-Raphson power flow** with randomized loads, warm start. 288 steps ≈ **4.0 s**.
  - pandapower warned that "numba cannot be imported... Please install numba to gain a massive speedup."
  - Source: [pandapower on PyPI](https://pypi.org/project/pandapower/)
- **Tested OpenDSS speed** (OpenDSSDirect.py 0.9.4 on dss-python 0.15.7, SMART-DS AUS `p1uhs0` `opendss_no_loadshapes`):
  - Compile 0.21 s: 9,820 buses, 18,805 nodes, 6,817 loads, 1,302 transformers.
  - Snapshot solve **41 ms**, converged.
  - **288 snapshot solves with varying LoadMult: 1.11 s**.
  - Bus voltages at the last step ranged **0.907–1.026 pu**.
  - Sources: [OpenDSSDirect.py on PyPI](https://pypi.org/project/OpenDSSDirect.py/); [S3 feeder folder](https://oedi-data-lake.s3.amazonaws.com/?list-type=2&prefix=SMART-DS/v1.0/2018/AUS/P1U/scenarios/base_timeseries/opendss_no_loadshapes/p1uhs0_1247/)
- **Versions and licenses** (PyPI and npm JSON APIs, tested):

  | Package | Version | License |
  |---|---|---|
  | pandapower | 3.5.5 | PyPI field blank; GitHub `e2nIEE/pandapower` reports "NOASSERTION". Commonly described as BSD-3 (UNVERIFIED). |
  | OpenDSSDirect.py | 0.9.4 | BSD-style, Alliance for Sustainable Energy |
  | dss-python | 0.15.7 | BSD-3-Clause |
  | py-dss-interface | 2.3.0 | MIT |
  | PyPSA | 1.3.0 | MIT |
  | HELICS | 3.6.1 | BSD |
  | pvlib | 0.15.2 | BSD-3-Clause |
  | gridstatus | 0.36.0 | BSD-3-style |

  Sources: [PyPI pandapower](https://pypi.org/project/pandapower/), [PyPI py-dss-interface](https://pypi.org/project/py-dss-interface/), [PyPI pypsa](https://pypi.org/project/pypsa/), [PyPI helics](https://pypi.org/project/helics/)
- **Active repositories.** GridLAB-D (last push 2026-09-25) and HELICS (BSD-3-Clause, last push 2026-09-09) are both active. — [gridlab-d/gridlab-d](https://github.com/gridlab-d/gridlab-d); [GMLC-TDC/HELICS](https://github.com/GMLC-TDC/HELICS)
- **Solver modeling differences.** pandapower uses an ideal slack bus, while OpenDSS models source impedance; results align when the OpenDSS short-circuit power is set very high. pandapower uses Newton-Raphson; OpenDSS uses a fixed-point method by default. This is a secondary source. — [Electrisim: pandapower vs OpenDSS](https://electrisim.com/pandapower-opendss-load-flow-comparison); [PowerGridModel benchmark](https://github.com/PowerGridModel/power-grid-model-benchmark/blob/main/Power%20Grid%20Model%20Benchmark.ipynb)
- **Reference paper.** pandapower paper — [arXiv 1709.06743](https://arxiv.org/abs/1709.06743)

### Inferences
- **Runtime is trivial.** A full AC power flow for 1,000 homes at 5-minute steps costs about 1–4 s per simulated day, so a week-long heat-wave replay runs in well under a minute. The team does not need a simplified model for speed.
- **Hidden cost.** The real per-step cost will be pushing 1,000 per-home kW values from Python into the solver each step; the LoadMult test above does not include this. Use OpenDSS LoadShapes or batch property setting, or vectorized pandapower `net.load.p_mw` assignment. This overhead is UNVERIFIED.
- **OpenDSSDirect.py** is the right pick with SMART-DS: native `.dss` files, unbalanced three-phase with single-phase service transformers, and `Transformers`/`Lines` APIs that report loading directly.
- **pandapower** fits better if the team builds its own network from OSM and buildings: pandas tables and easy programmatic creation. Its `runpp` is balanced, and `runpp_3ph` exists for unbalanced cases.
- **Tools to skip:**
  - GridLAB-D needs a C++ build and GLM authoring.
  - HELICS is co-simulation plumbing, only useful if coupling a transmission model.
  - PyPSA is aimed at optimisation and capacity expansion rather than unbalanced distribution power flow.
- **The bucket model as a demo feature.** A "capacity-aware controller" that tracks each service transformer's kVA headroom and the feeder-head MW headroom is exactly the Base engineer's question. Show "naive fleet dispatch" against "capacity-aware dispatch" with OpenDSS as the referee. A kW-only bucket misses voltage: 0.907 pu is below the ANSI C84.1 Range A floor of 0.95 pu (the threshold is general knowledge; UNVERIFIED here). The referee should report both transformer overloads and voltage violations.

### Gaps
- There is no published head-to-head timing at exactly 1,000 homes; the numbers above are my own single-machine measurements, possibly with other processes running.
- pandapower's license is not confirmed from a primary page.

---

## 3. Real grid infrastructure for the map, and utility territories (Austin Energy vs Oncor, PEC, TNMP)

### Takeaway
OpenStreetMap through Overpass works with no key and is the best free source of real Austin substations and lines. A metro bounding box returned **200 substations**, tagged by operator: Austin Energy 70, LCRA 37, PEC 28, Oncor 15, Bluebonnet 8. The core bbox holds **856 `power=line` ways**. Use **bounding-box** queries: the county-area query returned HTTP 406.

**HIFLD Open was shut down in August 2025.** Copies survive at HSDL and data-rescue mirrors.

Territories:
- **Austin Energy** covers about 437 sq mi, including parts of Pflugerville and Cedar Park.
- **Oncor** serves Round Rock, parts of Pflugerville, and Hutto.
- **PEC** covers the western Hill Country.

**Premise correction:** Base's own pricing page, fetched today, lists **Austin Energy** (municipal) as a territory with plans, alongside Oncor. PEC is not listed.

### Cited Findings
- **Tested Overpass access:**
  - `overpass-api.de` POST with bounding-box queries returned **HTTP 200 in 3–7 s**.
  - The area query `area["name"="Travis County"]["admin_level"="6"]` returned **HTTP 406** by POST and by GET.
  - Mirrors `overpass.private.coffee`, `maps.mail.ru` and `overpass.kumi.systems` returned **504** on the area query.
  - `private.coffee` answered the bbox query but its data timestamp was **2026-07-28**, stale compared with overpass-api.de at 2026-09-26.
  - The status endpoint reported "Rate limit: 2" slots.
  - Source: [Overpass status](https://overpass-api.de/api/status)
- **Tested metro substations.** Bbox 29.85,−98.2 to 30.95,−97.25 (approximately Travis, Williamson and Hays) returned 200 `power=substation` features:
  - Operators: Austin Energy 70; Lower Colorado River Authority 37; untagged 31; Pedernales Electric Cooperative 28; Oncor 15; Bluebonnet Electric Cooperative 8; San Marcos Electric Utilities 4; Brazos Electric 3.
  - Examples: "Summit Substation" (Austin Energy, 138 kV, distribution) at 30.3981, −97.7238, and "Dessau Substation" (Austin Energy, 138 kV).
  - The response states "The data is made available under ODbL."
  - Source: [Overpass API](https://overpass-api.de/api/interpreter)
- **Tested north Austin / Pflugerville / Round Rock.** Bbox 30.35,−97.75 to 30.60,−97.55 returned 29 substations: Austin Energy 14, Oncor 7, LCRA 5. — [Overpass API](https://overpass-api.de/api/interpreter)
- **Tested transmission lines.** `way["power"="line"]` in the Austin core bbox (30.1,−97.95 to 30.55,−97.55) returned a count of 856 ways. — [Overpass API](https://overpass-api.de/api/interpreter)
- **HIFLD shutdown.** "In August 2025, HIFLD Open, a public data portal managed by the U.S. Department of Homeland Security (DHS), was shut down. An aggregation of those open data sources was preserved in the Homeland Security Digital Library (HSDL)." — [HSDL HIFLD](https://www.hsdl.org/hifld/) (fetched, HTTP 200). The deactivation date was August 26, 2025 per the search summary, UNVERIFIED on a primary page. `hifld-geoplatform.hub.arcgis.com` returned **HTTP 404** (tested).
- **HIFLD copies.** Transmission-line mirrors exist at the Data Rescue Project and DataLumos, and ArcGIS hubs such as US FWS still host copies (not tested). — [Data Rescue Project](https://portal.datarescueproject.org/datasets/hifld-open-transmission-lines/); [DataLumos](https://www.datalumos.org/datalumos/project/240591/version/V1/view); [US FWS hub](https://gis-fws.opendata.arcgis.com/datasets/fws::us-electric-power-transmission-lines/about)
- **Austin Energy territory.** About 437 sq mi, mostly in Travis County with the rest in Williamson; about half is inside Austin city limits. It serves the City of Austin plus "all or portions of" Bee Cave, Village of the Hills, Lakeway, Rollingwood, Westlake Hills, Sunset Valley, Creedmoor, Del Valle, Pflugerville and Cedar Park. The page offers no GIS download. — [Austin Energy service area](https://austinenergy.com/about/company-profile/electric-system/service-area-map)
- **Oncor in the Austin area.** Oncor serves Round Rock, and Oncor outage reports come from Round Rock and Pflugerville; Oncor has a service center in Hutto (search snippets). — [Round Rock Chamber: Oncor](https://web.roundrockchamber.org/Public-Utilities,-Waste,-and-Recycle/Oncor-Electric-Delivery-60); [Oncor communities](https://www.oncor.com/communityprofiles/communities.html); [Oncor service area map](https://www.oncor.com/content/oncorwww/us/en/home/about-us/service-area-map.html)
- **Oncor's regional footprint.** "Oncor serves eastern Williamson County, northeastern Travis County and northwest Bastrop County." This comes from a broker blog, so it is a secondary source and UNVERIFIED. — [energybrokertx](https://energybrokertx.com/blog/austin-central-texas-commercial-electricity-broker)
- **PEC footprint.** PEC serves the Hill Country west of Austin and parts of western Williamson, Travis and Hays counties (secondary source). — [Wikipedia: PEC](https://en.wikipedia.org/wiki/Pedernales_Electric_Cooperative)
- **Base Power territories** (tested; pricing page fetched 2026-09-26 about 00:45 UTC, HTTP 200). The page shows "Texas & Illinois · plans by area... 11 areas":
  - CenterPoint (Energy + backup, Energy only)
  - Oncor, Central & North Texas (Energy + backup, Energy only)
  - AEP Texas Central
  - AEP Texas North
  - Texas–New Mexico Power
  - ComEd (Chicago)
  - Guadalupe Valley EC
  - CoServ
  - Farmers EC
  - **"Austin Energy, Austin (municipal utility), See plans"** (link `/austinenergy#pricing`)
  - El Paso Electric

  PEC and Bluebonnet are not listed. — [Base pricing](https://www.basepowercompany.com/pricing)
- **Base cities in Oncor territory.** A search snippet says Base's Oncor coverage includes Georgetown, Round Rock and Pflugerville. These city names were not in the static HTML I fetched, so this is UNVERIFIED. — [Base pricing (filtered)](https://www.basepowercompany.com/pricing?offering_equal=Energy+%2B+Backup)

### Inferences
- **Premise correction.** "Austin Energy is outside the market, so Base can't operate there" appears out of date as of 2026-09. Base lists Austin Energy with plans. The plan type (probably backup-only, as with its co-op areas) is not visible in static HTML, so it is UNVERIFIED. Hand this to the Base/ERCOT researcher to confirm.
- **Safest map framing.** The Oncor pocket (Round Rock, parts of Pflugerville, Hutto) is where Base's full "Energy + backup" offering is confirmed. SMART-DS AUS feeders sit in north Austin, which in reality is Austin Energy territory. Either keep them labeled as synthetic, or draw real Oncor substations from OSM as context.
- **Overpass usage.** Pull once and save as static GeoJSON; there are only 2 concurrent slots and mirrors can be stale. OSM operator tags are incomplete (31 of 200 untagged), and LCRA entries are mostly transmission.

### Gaps
- No official, downloadable territory polygons were verified. The PUCT CCN service-area maps and the EIA/HIFLD "Electric Retail Service Territories" layer were not tested.
- An EIA U.S. Energy Atlas hub search via its API returned no results, so its layers are UNVERIFIED.

---

## 4. Houses and buildings for the map: Overture, Microsoft, OSM, TCAD

### Takeaway
**Overture Maps buildings** (ODbL; conflates OSM, Microsoft ML, Google and Esri) is the best single building layer. Its release `2026-09-23.1` is on public S3, with an MIT Python CLI. The legacy **Microsoft US Building Footprints** URL is dead (HTTP 409); the global Microsoft set still works. Parcel attributes such as year built or size are available via TxGIO StratMap parcels (unverified for Travis).

For a 48-hour build, the simplest move is to **use the SMART-DS load bus coordinates as the homes**: they already sit on real Austin building locations, so no separate buildings dataset is needed.

### Cited Findings
- **Tested Overture releases.** `s3://overturemaps-us-west-2/release/` lists `2026-08-19.0`, `2026-09-23.0` and `2026-09-23.1`. — [S3 listing](https://overturemaps-us-west-2.s3.amazonaws.com/?list-type=2&prefix=release/&delimiter=/)
- **Overture license and sources.** The buildings theme is ODbL, with attribution "© OpenStreetMap contributors." Sources are OpenStreetMap (ODbL), Esri Community Maps (CC BY 4.0), Microsoft Global ML Building Footprints (ODbL), Google Open Buildings (CC BY 4.0) and USGS 3DEP; the page was updated 2026-05-15. — [Overture attribution](https://docs.overturemaps.org/attribution/)
- **Overture building attributes.** Buildings carry height and levels for 2.5D/3D extrusion. ML-derived footprints need at least 10 m² of area, and features at 900 m or taller are excluded. — [Overture buildings guide](https://docs.overturemaps.org/guides/buildings/)
- **Overture CLI.** `overturemaps` 1.0.2, MIT (PyPI, tested). Exact CLI flags are UNVERIFIED. — [PyPI overturemaps](https://pypi.org/project/overturemaps/)
- **Tested dead Microsoft US URL.** `https://usbuildingdata.blob.core.windows.net/usbuildings-v2/Texas.geojson.zip` returned **HTTP 409 "Public access is not permitted on this storage account."** — [MS US Building Footprints (dead)](https://usbuildingdata.blob.core.windows.net/usbuildings-v2/Texas.geojson.zip)
- **Tested Microsoft global footprints.** The Global ML Building Footprints index returned HTTP 200, with 2,415 United States quadkey rows. File paths point at release folder `2026-02-03`, with upload dates such as 2026-02-23. — [dataset-links.csv](https://minedbuildings.z5.web.core.windows.net/global-buildings/dataset-links.csv)
- **TxGIO StratMap Land Parcels** translates county appraisal-district data into a common schema, offered as shapefile or geodatabase. "Not all counties are available." Whether Travis carries year built or living area is UNVERIFIED (search snippet). — [TxGIO Land Parcels](https://tnris.org/stratmap/land-parcels.html)
- **SMART-DS placement.** SMART-DS models "connect to real buildings which have synthetic load patterns attached." — [SMART-DS Readme](https://oedi-data-lake.s3.amazonaws.com/SMART-DS/v1.0/User_Guide/Readme.md)

### Inferences
- **Fastest path.** Draw SMART-DS load buses from `Buscoords.dss` or the GeoJSON as home dots, then optionally overlay Overture footprints for visual realism. Overture GeoParquet for a small bbox is quick to pull with DuckDB or the CLI.
- **Don't use the dead Microsoft URL.** Many tutorials still reference the legacy US-v2 link; point the team at Overture instead.
- **Skip TCAD and parcel attributes.** Home size can be inferred from footprint area and Overture levels, or taken from ResStock metadata.

### Gaps
- I did not find or test a Travis Central Appraisal District open-data export URL.
- The TxGIO Travis parcel attributes were not inspected.

---

## 5. Residential load profiles: ResStock / End-Use Load Profiles, Pecan Street, Smart Meter Texas

### Takeaway
Use **SMART-DS's own `load_data` parquet**. It is ResStock-derived, 15-minute, covers 2016–2018, includes a `cooling_kw` end-use column, and is already assigned to each Austin home. Alternatively use **ResStock** from OEDI: 2024 release individual-building parquet files for Texas, or 2021 release **Travis County (FIPS 48453, code `g4804530`)** aggregates.

**Pecan Street** is real Austin data, but the only free-for-anyone piece is a 10-home, 3-day Kaggle sample. Its university tier requires academic verification (review within 3 business days) and non-commercial use, so it is not realistic in 48 hours.

### Cited Findings
- **SMART-DS load data.** `load_data/<res|com>_<id>.parquet` holds 15-minute data with `total_site_electricity_kw`, `heating_kw`, `cooling_kw`, `lighting_kw`, `fans_kw`, `pumps_kw` and more, derived from ResStock/ComStock. — [SMART-DS Readme](https://oedi-data-lake.s3.amazonaws.com/SMART-DS/v1.0/User_Guide/Readme.md)
- **Tested ResStock 2024 (AMY2018, release 2) layout.**
  - `timeseries_individual_buildings/by_state/upgrade=0/state=TX/` contains per-building parquet files of 2.7–5.7 MB each (for example `100025-0.parquet`, 5.68 MB, dated 2024-09-13).
  - `timeseries_aggregates/` offers only `by_state`, `by_iso_rto_region`, `by_building_america_climate_zone` and `by_ashrae_iecc_climate_zone_2004`. There is **no by_county** in this release.
  - Source: [S3 listing](https://oedi-data-lake.s3.amazonaws.com/?list-type=2&prefix=nrel-pds-building-stock/end-use-load-profiles-for-us-building-stock/2024/resstock_amy2018_release_2/&delimiter=/)
- **Tested ResStock 2021 (AMY2018, release 1) Travis aggregates.** `timeseries_aggregates/by_county/state=TX/` includes Travis `g4804530-*.csv` by building type: mobile home 23.1 MB, multifamily 2–4 units 24.1 MB, multifamily 5+ 26.5 MB, single-family attached 23.0 MB. Single-family detached files exist for other counties (for example `g4800010-single-family_detached.csv`, 25.0 MB). — [S3 listing](https://oedi-data-lake.s3.amazonaws.com/?list-type=2&prefix=nrel-pds-building-stock/end-use-load-profiles-for-us-building-stock/2021/resstock_amy2018_release_1/timeseries_aggregates/by_county/state=TX/)
- **ResStock 2024.2 documentation.** Each building model yields one year of consumption in **15-minute intervals**, separated by end use. — [ResStock 2024.2 documentation (PDF)](https://oedi-data-lake.s3.amazonaws.com/nrel-pds-building-stock/end-use-load-profiles-for-us-building-stock/2024/resstock_tmy3_release_2/resstock_documentation_2024_release_2.pdf); [OEDI EULP 4520](https://data.openei.org/submissions/4520); [AWS Open Data registry](https://registry.opendata.aws/nrel-pds-building-stock/)
- **Pecan Street free sample.** A Kaggle sample of **10 Austin homes**, 1-minute circuit-level, over three consecutive August days in 2018. It includes whole-home, HVAC (air handler and condenser) and rooftop solar circuits. — [Pecan Street: free datasets (2025-07)](https://www.pecanstreet.org/2025/07/public-data/)
- **Pecan Street university tier.** Up to 75 homes in Austin, New York and California at 1-minute and 1-second resolution, "only for non-commercial educational and research purposes." It is limited to current faculty, staff or students at a 4-year institution. Applicants submit an ID photo or bio link, and review takes about 3 business days. — [Pecan Street: free datasets](https://www.pecanstreet.org/2025/07/public-data/); [Pecan Street access and pricing](https://www.pecanstreet.org/access/)
- **Kaggle URL.** My guessed Kaggle URL (`kaggle.com/datasets/pecanstreet/pecan-street-dataport-sample`) returned HTTP 404, so the exact Kaggle location is UNVERIFIED. Kaggle downloads typically require login.

### Inferences
- **Pecan Street is effectively out.** The Base-sponsored hackathon is arguably commercial, it needs a university-affiliated member, and approval can take up to 3 business days. The Kaggle 10-home sample is useful only to sanity-check the AC load shape.
- **Weather-driven AC for events outside 2018.** Neither SMART-DS nor ResStock AMY2018 covers Winter Storm Uri (2021) or the Aug 2023 heat wave. A simple approach is to fit per-home `cooling_kw` (and `heating_kw`) against outdoor temperature from the profile year, then drive it with Open-Meteo historical temperatures (§6).

### Gaps
- Smart Meter Texas was not verified. My understanding, UNVERIFIED, is that it offers only a customer's own meter data after account registration, and only in competitive TDU areas, not Austin Energy.
- The EULP dataset license was not confirmed on a primary page; it is probably CC BY 4.0 like other OEDI data (UNVERIFIED).

---

## 6. Weather: NWS, Open-Meteo, NOAA ISD/LCD, NSRDB; historical pulls for Winter Storm Uri and the Aug 2023 heat wave

### Takeaway
All three keyless weather sources worked from curl today:
- **NWS** for live forecasts and observations.
- **Open-Meteo** for forecast plus history back to 1940. It returned Uri hourly temperatures down to 4.5 °F and an Aug 2023 daily maximum of 106.9 °F for Austin.
- **NOAA NCEI** Access Data Service for real KAUS station observations.

Open-Meteo's free tier is officially **non-commercial**, capped at 10,000 calls per day. NWS and NCEI are the public-domain fallbacks.

### Cited Findings
- **Tested NWS point lookup.** `GET https://api.weather.gov/points/30.2672,-97.7431` returned **HTTP 200 in 0.15 s**: `gridId` EWX, `gridX` 156, `gridY` 91, with forecast `.../gridpoints/EWX/156,91/forecast` and hourly `.../forecast/hourly`, time zone America/Chicago. — [NWS API points](https://api.weather.gov/points/30.2672,-97.7431)
- **Tested NWS observation.** `GET /stations/KAUS/observations/latest` returned **HTTP 200**: 2026-09-26T00:10Z, 34 °C, "Clear". — [KAUS latest](https://api.weather.gov/stations/KAUS/observations/latest)
- **NWS terms.** The service charges no fees. "The rate limit is not public information, but allows a generous amount for typical use." A User-Agent with contact information is required, e.g. `User-Agent: (myweatherapp.com, contact@myweatherapp.com)`, and "This will be replaced with an API key in the future." — [NWS API documentation](https://www.weather.gov/documentation/services-web-api)
- **Tested Open-Meteo forecast.** Hourly `temperature_2m` and `shortwave_radiation` for Austin returned **HTTP 200**. — [Open-Meteo forecast API](https://api.open-meteo.com/v1/forecast?latitude=30.27&longitude=-97.74&hourly=temperature_2m,shortwave_radiation&temperature_unit=fahrenheit&forecast_days=1&timezone=America%2FChicago)
- **Tested Open-Meteo Winter Storm Uri.** Archive 2021-02-14 to 2021-02-17 at 30.27, −97.74 returned **HTTP 200**, 96 hourly values, **minimum 4.5 °F, maximum 33.1 °F**. — [Open-Meteo archive (Uri)](https://archive-api.open-meteo.com/v1/archive?latitude=30.27&longitude=-97.74&start_date=2021-02-14&end_date=2021-02-17&hourly=temperature_2m&temperature_unit=fahrenheit&timezone=America%2FChicago)
- **Tested Open-Meteo Aug 2023 heat wave.** Archive 2023-08-01 to 2023-08-31 daily `temperature_2m_max` returned **HTTP 200**: **peak 106.9 °F, mean daily maximum 103.7 °F** over 31 days. — [Open-Meteo archive (Aug 2023)](https://archive-api.open-meteo.com/v1/archive?latitude=30.27&longitude=-97.74&start_date=2023-08-01&end_date=2023-08-31&daily=temperature_2m_max&temperature_unit=fahrenheit&timezone=America%2FChicago)
- **Open-Meteo historical sources.** ERA5 (0.25°, from 1940), ERA5-Land (0.1°, from 1950) and ECMWF IFS (9 km, from 2017). — [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api)
- **Open-Meteo free-tier terms.** "Less than 10'000 API calls per day, 5'000 per hour and 600 per minute. You may only use the free API services for non-commercial purposes. You accept to the CC-BY 4.0 licence." — [Open-Meteo terms](https://open-meteo.com/en/terms); [Open-Meteo pricing](https://open-meteo.com/en/pricing)
- **Tested NOAA NCEI.** Access Data Service, `dataset=global-hourly` (ISD), station `72254013904` (Austin-Bergstrom KAUS), returned **HTTP 200 with no token**. Sample row: `"72254013904","2021-02-15T00:00:00",...,"-0061,1"` (−6.1 °C). — [NCEI ADS query](https://www.ncei.noaa.gov/access/services/data/v1?dataset=global-hourly&stations=72254013904&startDate=2021-02-15T00:00:00&endDate=2021-02-15T06:00:00&dataTypes=TMP&format=csv)
- **Camp Mabry (KATT).** Its ISD station ID was not tested; `72254413958` is commonly cited but UNVERIFIED.
- **NSRDB.** The docs page moved to `developer.nlr.gov/docs/solar/nsrdb/` (HTTP 200, tested). It needs an API key; the email requirement is UNVERIFIED. — [NSRDB API docs](https://developer.nlr.gov/docs/solar/nsrdb/)

### Inferences
- **Open-Meteo is the fastest single source.** One JSON shape covers the live forecast and both historical events, and it includes `shortwave_radiation` for solar. Because the hackathon is sponsor-run, flag the "non-commercial" term; pre-download the few scenario windows once and store them as CSV.
- **Reanalysis smooths extremes.** ERA5 at about 25 km resolution may understate station peaks. Use NCEI KAUS observations as the "real" trace if judges probe realism.
- **Call budget.** About 6–10 calls total covers one live forecast plus the Uri, Aug 2023 and a normal-summer window. Rate limits are irrelevant if the data is cached.

### Gaps
- The Camp Mabry station ID was not tested.
- NOAA LCD v2 endpoints were not tested; ISD global-hourly was.
- NSRDB key and email requirements were not confirmed.

---

## 7. Rooftop solar output: PVWatts v8, pvlib, typical Austin system size

### Takeaway
**`developer.nrel.gov` no longer resolves** (DNS failure, tested). NREL was renamed the National Laboratory of the Rockies on 2025-12-01, and **PVWatts v8 now answers at `developer.nlr.gov`**.

With the public `DEMO_KEY`, a 7 kW south-facing Austin array yields **10,441 kWh/yr** (capacity factor 17.0%). The demo key is limited to 10 calls; a free personal key gets 1,000 per hour. pvlib (BSD-3) is the offline alternative.

SMART-DS also ships per-location solar profiles. Typical Austin residential systems are roughly **7–12 kW**, from weak sources.

### Cited Findings
- **Tested old host.** `https://developer.nrel.gov/api/pvwatts/v8.json?...` returned `curl: (6) Could not resolve host: developer.nrel.gov` (HTTP 000) on 2026-09-26 about 00:25 UTC.
- **Tested new host.** `https://developer.nlr.gov/api/pvwatts/v8.json?api_key=DEMO_KEY&lat=30.27&lon=-97.74&system_capacity=7&azimuth=180&tilt=25&array_type=1&module_type=0&losses=14` returned **HTTP 200**:
  - Headers `x-ratelimit-limit: 10`, `x-ratelimit-remaining: 9`.
  - `ac_annual` = 10,441.2 kWh; `capacity_factor` = 17.03%.
  - Weather source "NSRDB PSM V3 GOES tmy-2020 3.2.0"; version 8.5.0.
  - Source: [PVWatts v8 docs](https://developer.nrel.gov/docs/solar/pvwatts/v8/); [NLR Developer Network](https://developer.nlr.gov/)
- **Rate limits.** "Hourly Limit: 1,000 requests per hour. For each API key, these limits are applied across all developer.nlr.gov API requests." — [NLR rate limits](https://developer.nlr.gov/docs/rate-limits/)
- **Rename.** On December 1, 2025, DOE announced NREL's new name, the National Laboratory of the Rockies. — [DOE announcement](https://www.energy.gov/cmei/articles/energy-department-renames-nrel-national-lab-rockies); [NLR news release](https://www.nlr.gov/news/detail/press/2025/news-release-energy-department-renames-nrel-national-laboratory-of-the-rockies). A GitHub pull request records the same fix ("Point PVWatts at developer.nlr.gov"). — [lowellbw/balconyc PR #43](https://github.com/lowellbw/balconyc/pull/43)
- **pvlib.** Version 0.15.2, BSD-3-Clause (PyPI, tested). — [PyPI pvlib](https://pypi.org/project/pvlib/)
- **SMART-DS solar profiles** are named by NSRDB location, tilt and azimuth, for example `AUS_30.3459_-97.8095_15_135.csv` (about 261 KB); the README describes the naming. — [S3 profiles listing](https://oedi-data-lake.s3.amazonaws.com/?list-type=2&prefix=SMART-DS/v1.0/2018/AUS/P1U/profiles/&max-keys=3); [Readme](https://oedi-data-lake.s3.amazonaws.com/SMART-DS/v1.0/User_Guide/Readme.md)
- **Austin system size.** EnergySage reports an average of **11.88 kW** (quote-marketplace data from a search snippet; UNVERIFIED). Other snippets say about 7 kW is "best size" and the Texas median is 8.1 kW, with unclear provenance. — [EnergySage Austin](https://www.energysage.com/local-data/solar-panel-cost/tx/travis-county/austin/). Austin Energy's solar program deck exists but was not fetched. — [Austin Energy Solar Programs (PDF)](https://services.austintexas.gov/edims/document.cfm?id=460815)

### Inferences
- **Fix code before copying snippets.** Any tutorial or library still pointing at `developer.nrel.gov` will fail; replace the host with `developer.nlr.gov`.
- **Keep the call count small.** Pull about 10–15 PVWatts hourly archetypes (for example azimuths 90/135/180/225/270 × a few sizes) and scale per home; the DEMO_KEY's 10-call cap is enough only for testing. For weather-matched events (Uri snow cover, heat-wave days), run pvlib with Open-Meteo `shortwave_radiation`.
- **Sizing assumption.** Assume 6–12 kW DC per solar home and roughly 25–40% adoption on the demo feeder. This is a modeling choice, not a sourced figure; SMART-DS's low/medium/high/extreme scenarios give defensible placements.

### Gaps
- There is no authoritative Austin-specific median system size from LBNL Tracking the Sun or Austin Energy's program data; neither was fetched.

---

## 8. Outage data for replaying realistic outage patterns

### Takeaway
**EAGLE-I** (ORNL) is the usable dataset: county-level customers-out at 15-minute intervals for **2014–2025**, on figshare under **CC BY 4.0**. It includes an R script for mapping Winter Storm Uri. Yearly CSVs are about 1.1–1.4 GB.

The live outage maps for Austin Energy and Oncor are **Kubra StormCenter** apps; their JSON is undocumented. poweroutage.us and ORNL's OpenEnergyHub API both blocked curl with HTTP 403.

### Cited Findings
- **Tested EAGLE-I on figshare.** Article 24237376 is titled "The Environment for Analysis of Geo-Located Energy Information's Recorded Electricity Outages 2014-2025". It is v4, published 2026-02-25, CC BY 4.0, DOI 10.6084/m9.figshare.24237376.v4.
  - Yearly files: `eaglei_outages_2021.csv` 1,141 MB; 2023 1,200 MB; 2024 1,445 MB; 2025 1,402 MB; 2014 78 MB.
  - Also included: `Uri_Map.R`, `coverage_history.csv`, `DQI.csv` and `MCC.csv`.
  - Source: [figshare EAGLE-I](https://doi.org/10.6084/m9.figshare.24237376.v4)
- **EAGLE-I contents.** County-level outage estimates at 15-minute intervals, with FIPS code, county, state, customers out and timestamp. Coverage reached 92% of US customers by 2022. — [Scientific Data paper](https://www.nature.com/articles/s41597-024-03095-5); [OSTI 1975202](https://www.osti.gov/biblio/1975202)
- **Tested blocked endpoints.**
  - The ORNL OpenEnergyHub API (`/api/explore/v2.1/catalog/datasets/eaglei_outages_2014/records`) returned **HTTP 403 ForbiddenAccess**. — [OpenEnergyHub EAGLE-I](https://openenergyhub.ornl.gov/explore/dataset/eaglei_outages_2014/)
  - `poweroutage.us/area/state/texas` returned **HTTP 403** to curl. — [poweroutage.us](https://poweroutage.us/area/state/texas)
- **Tested utility outage maps.**
  - `outagemap.austinenergy.com` and `stormcenter.oncor.com` both returned HTTP 200, and both pages load Kubra StormCenter assets (`kubra.io/product/5.54.1/manifest.json`).
  - `outagemap.pec.coop` timed out (HTTP 000).
  - Kubra's JSON data endpoints behind these pages are undocumented (UNVERIFIED), and CenterPoint was not tested.
  - Sources: [Austin Energy outage map](https://outagemap.austinenergy.com/); [Oncor StormCenter](https://stormcenter.oncor.com/)
- **Other outage data.** An "Event-correlated Outage Dataset in America" exists on OEDI (not fetched). — [OEDI 6458](https://data.openei.org/submissions/6458)

### Inferences
- **Uri replay recipe.** Download only `eaglei_outages_2021.csv` (1.1 GB) and filter to FIPS 48453 (Travis), 48491 (Williamson) and 48209 (Hays) for 2021-02-10 to 02-22. Convert "percent of county customers out" into per-feeder outage probabilities.
- **Other scenarios are synthetic events.** Feeder or substation trips, generator trips and cyberattacks are cleaner to model as scripted events than to take from data. Present Uri as the "historical replay" scenario.
- **Skip live outage feeds.** Live scraping of Kubra maps is fragile and of doubtful terms-of-use compliance.

### Gaps
- I did not research DOE's ODIN (Outage Data Initiative Nationwide), so its access terms are unknown.
- The CenterPoint outage map and any public Kubra JSON were not tested.

---

## 9. Distribution capacity data and typical feeder and transformer ratings

### Takeaway
No utility in the Austin area publishes a usable public **hosting-capacity map or feeder dataset** that I could find, whether Oncor, Austin Energy or CenterPoint.

The best citable "typical values" come from SMART-DS's validated Austin feeders, measured directly:
- Median feeder peak **6.9 MW** at **12.47 kV**, with about **660 customers**.
- About **2.5 homes per service transformer**.
- Service transformers are predominantly **25/50/75 kVA nameplate**, stored as 27.5/55/82.5 kVA after SMART-DS's roughly 10% upsizing.

### Cited Findings
- **Tested feeder statistics** (AUS P1U `metrics.csv`): feeder peak planning load median 6.9 MW (max 17.0 MW); customers per feeder median 663.5 (max 1,872); service transformers per feeder median 238.5; loads per transformer median 2.5 (max 4.4); total transformer capacity per feeder median 16.0 MVA; nominal 12.47 kV. — [metrics.csv](https://oedi-data-lake.s3.amazonaws.com/SMART-DS/v1.0/2018/AUS/P1U/scenarios/base_timeseries/metrics.csv)
- **Tested transformer ratings.** `Transformers.dss` across the three feeders of substation `p1uhs0` (1,302 transformers in total):

  | Rating (kVA) | Count |
  |---|---|
  | 27.5 | 324 |
  | 55 | 498 |
  | 82.5 | 395 |
  | 110 | 21 |
  | 165 | 31 |
  | 330 | 15 |
  | 550 | 11 |
  | 1,100 | 6 |
  | 300,000 (source/substation) | 1 |

  Source: [p1uhs0 opendss folder](https://oedi-data-lake.s3.amazonaws.com/?list-type=2&prefix=SMART-DS/v1.0/2018/AUS/P1U/scenarios/base_timeseries/opendss/p1uhs0_1247/)
- **Why the ratings are upsized.** SMART-DS post-processing included "Increase line and transformer capacity to prevent overloads for timeseries scenarios." — [SMART-DS Readme](https://oedi-data-lake.s3.amazonaws.com/SMART-DS/v1.0/User_Guide/Readme.md)
- **Primary voltages.** Common US primary voltages are 7.2, 12.47, 14.4 and 24.94 kV, with 240/120 V secondaries (secondary source). — [Wikipedia: Distribution transformer](https://en.wikipedia.org/wiki/Distribution_transformer)
- **Vendor heuristics** (low-quality sources, UNVERIFIED): "A typical 25 kVA single-phase transformer can comfortably support 3–6 average homes." Diversity factors run about 1.1–1.2 for 3–5 customers and 1.3–1.5 for 10+ customers. — [Daelim residential transformer](https://www.daelimtransformer.com/residential-transformer.html); [NPC Electric sizing guide](https://www.npcelectric.com/news/residential-transformer-guide-sizing-kva-installation.html)
- **Oncor hosting capacity.** No public Oncor hosting-capacity map was found. A PUCT filing in Project 58306 (item 577, filed 2025-10-31) surfaced in search; its content was not fetched and is UNVERIFIED. — [PUCT 58306_577](https://interchange.puc.texas.gov/Documents/58306_577_1553814.PDF); [Oncor energy system developers](https://www.oncor.com/content/oncorwww/us/en/home/smart-energy/renewables-solar-and-more/energy-system-developers.html)

### Inferences
- **Ratings to use.** Feeder head about 7 MW; service transformers 25 kVA (2–3 homes) and 50 kVA (3–5 homes), with 75 kVA for larger clusters. Every number cites SMART-DS AUS.
- **The core demo mechanic.** A 25 kVA transformer serving 3 homes is stressed by coincident battery export or charging of about 10 kW per home. That is about 30 kW, or ~120% loading, on top of house load. Base's actual inverter kW is the Base researcher's scope; the 10 kW figure is illustrative and UNVERIFIED. This is exactly the "each additional battery on a stressed feeder" effect, and a controller that knows transformer and feeder kVA can throttle per-transformer export. The derivation is sound; the specific kW is an assumption.
- **Use nameplate for stress scenarios.** De-rate SMART-DS transformers back to 25/50/75 kVA; otherwise the extra 10% headroom masks stress.

### Gaps
- There is no IEEE, NREL or PNNL primary reference in hand for typical service-transformer customer counts; the PNNL-18035 and IEEE pages returned 403.
- Austin Energy and CenterPoint hosting-capacity or feeder data was not found.

---

## 10. Map and visualization stack: deck.gl, MapLibre and Mapbox, free tiles, kepler.gl

### Takeaway
**MapLibre GL JS** (BSD-3) plus **deck.gl** (MIT) with **OpenFreeMap** tiles needs no key, has no usage limits, and allows commercial use. Its style URL returned HTTP 200 today. **Protomaps** PMTiles is the self-hosted alternative.

Avoid **Mapbox GL** v2 and later, which ships under a proprietary license and needs a token. **kepler.gl** is MIT and good for quick data exploration, but its current npm "latest" tag is an alpha, and it is not a custom ops UI.

### Cited Findings
- **Tested npm registry versions:**

  | Package | Version | License |
  |---|---|---|
  | `maplibre-gl` | 6.11.2 | BSD-3-Clause |
  | `deck.gl` | 9.4.0 | MIT |
  | `kepler.gl` | 3.3.0-alpha.14 (the "latest" tag) | MIT |
  | `mapbox-gl` | 3.31.0 | "SEE LICENSE IN LICENSE.txt" (proprietary; token requirement UNVERIFIED here) |
  | `pmtiles` | 4.5.0 | BSD-3-Clause |

  Sources: [npm maplibre-gl](https://www.npmjs.com/package/maplibre-gl); [npm deck.gl](https://www.npmjs.com/package/deck.gl); [npm kepler.gl](https://www.npmjs.com/package/kepler.gl); [npm mapbox-gl](https://www.npmjs.com/package/mapbox-gl)
- **Tested OpenFreeMap style.** `https://tiles.openfreemap.org/styles/liberty` returned **HTTP 200**, a MapLibre style JSON with an `openmaptiles` vector source.
- **OpenFreeMap terms.** "There's no registration, no user database, no API keys, and no cookies." "There are no limits on the number of map views or requests." Commercial use is allowed. Required attribution is "OpenFreeMap © OpenMapTiles Data from OpenStreetMap." — [OpenFreeMap](https://openfreemap.org/)
- **Protomaps.** The Version 4 basemap daily build channel is at `maps.protomaps.com/builds`, with BLAKE3 hashes, and the generation code is open source. — [Protomaps downloads](https://docs.protomaps.com/basemaps/downloads); [protomaps/basemaps](https://github.com/protomaps/basemaps)
- **Stadia Maps** advertises "Get started for free", but the free tier requires signup; its details are UNVERIFIED. — [Stadia pricing](https://stadiamaps.com/pricing/)

### Inferences
- **Layer plan:**
  - SMART-DS feeder GeoJSON as a `GeoJsonLayer` or `PathLayer`, colored by line or transformer loading percentage.
  - Homes as a `ScatterplotLayer` of about 1,000 points, colored by battery state of charge or dispatch.
  - Substations from Overpass as an `IconLayer`.
  - An outage or cyber-compromised overlay as a polygon.
  deck.gl handles 1,000–10,000 features trivially.
- **Avoid external tokens.** Mapbox tokens and Stadia signup add a failure mode for no benefit; OpenFreeMap works offline-from-keys.

### Gaps
- I did not verify a `pmtiles extract` workflow for an Austin-only basemap file, or Stadia's free-tier limits.

---

## Summary catalog table

| Source | What it gives | Access/URL | Key needed? | License | Granularity | 48-hr feasible? | Verified (Y/N) |
|---|---|---|---|---|---|---|---|
| NREL SMART-DS AUS (2018) | Synthetic Austin sub-transmission, substations, 12.47 kV feeders, service transformers, customers; OpenDSS/CYME/GeoJSON; lon/lat; solar and battery placement scenarios | `s3://oedi-data-lake/SMART-DS/v1.0/2018/AUS/` via [HTTPS listing](https://oedi-data-lake.s3.amazonaws.com/?list-type=2&prefix=SMART-DS/v1.0/2018/AUS/&delimiter=/); [OEDI 2981](https://data.openei.org/submissions/2981) | No | CC BY 4.0 | Per-customer; 15-min loads 2016–2018; ~6 MB per substation | **Yes, top pick** | Y (downloaded and solved) |
| SMART-DS `load_data` / `profiles` | Per-home 15-min kW/kvar with end uses (`cooling_kw`) and solar profiles | Same bucket, `.../AUS/<region>/load_data`, `.../profiles` | No | CC BY 4.0 | 15-min, 1 year × 3 years | Yes | Y (listing), content partly |
| IEEE 13/34/123-bus test feeders | Small reference feeders | [IEEE PES](https://cmte.ieee.org/pes-testfeeders/resources/); [electricdss-tst](https://github.com/dss-extensions/electricdss-tst) | No | Research use (UNVERIFIED) | <200 buses, no geography | Yes but too small | N (403) |
| GridLAB-D Taxonomy feeders | Prototypical US feeders in GLM | [GitHub](https://github.com/gridlab-d/Taxonomy_Feeders) | No | UNVERIFIED | Feeder-level, no geography | Marginal | Partial (repo exists) |
| TAMU ACTIVSg2000 / Texas2k | Synthetic Texas transmission (2,000 buses) | [TAMU](https://electricgrids.engr.tamu.edu/electric-grid-test-cases/activsg2000) | Form (not a key) | Free, commercial or non-commercial; cite papers | Transmission buses | Only as backdrop | N (snippet) |
| OpenDSSDirect.py 0.9.4 | Unbalanced distribution power flow | `pip install OpenDSSDirect.py` | No | BSD-style | 41 ms per snapshot for 6,817 loads | **Yes** | Y (benchmarked) |
| pandapower 3.5.5 | Balanced / 3-phase PF, Pythonic | `pip install pandapower` | No | BSD-3 (UNVERIFIED) | 14 ms per PF for 1,000 homes (no numba) | Yes | Y (benchmarked) |
| py-dss-interface 2.3.0 | Alternate OpenDSS wrapper | PyPI | No | MIT | same engine family | Yes | Y (PyPI) |
| GridLAB-D | Agent-based distribution sim | [GitHub](https://github.com/gridlab-d/gridlab-d) | No | UNVERIFIED | seconds-level | No (setup cost) | Partial |
| HELICS 3.6.1 | Co-simulation bus | PyPI; [GitHub](https://github.com/GMLC-TDC/HELICS) | No | BSD-3 | — | No (not needed) | Y (PyPI/GitHub) |
| PyPSA 1.3.0 | Optimisation / LOPF | PyPI | No | MIT | — | Not for distribution PF | Y (PyPI) |
| OSM via Overpass | Real substations (200 in metro bbox), lines (856 in core) with operator tags | `https://overpass-api.de/api/interpreter` (bbox; area query → 406) | No | ODbL | Point/polygon/line | **Yes** (cache once) | Y |
| HIFLD Open | Substations and transmission lines | Shut down Aug 2025; archive at [HSDL](https://www.hsdl.org/hifld/), [Data Rescue](https://portal.datarescueproject.org/datasets/hifld-open-transmission-lines/) | No | Public (varies) | National | Only via mirrors | Y (shutdown; hub 404) |
| EIA U.S. Energy Atlas | Energy infrastructure layers | atlas.eia.gov | No | Public | — | Unknown | N |
| Austin Energy service-area page | Territory description (437 sq mi, cities) | [Austin Energy](https://austinenergy.com/about/company-profile/electric-system/service-area-map) | No | — | Text and image only | Yes (manual polygon) | Y |
| Base Power pricing page | Base territories (lists Oncor, CenterPoint, **Austin Energy**, TNMP, AEP, 3 co-ops, EPE, ComEd) | [basepowercompany.com/pricing](https://www.basepowercompany.com/pricing) | No | — | Utility-level | Yes | Y |
| Overture Maps buildings | Conflated footprints (OSM, MS, Google, Esri) with height/levels | `s3://overturemaps-us-west-2/release/2026-09-23.1/`; `overturemaps` CLI 1.0.2 | No | ODbL | Per building | Yes | Y (release listing, docs) |
| Microsoft US Building Footprints (legacy) | TX footprints | `usbuildingdata.blob.core.windows.net/...` | — | ODbL | Per building | **No (HTTP 409, dead)** | Y (dead) |
| Microsoft Global ML Building Footprints | Footprints by quadkey | [dataset-links.csv](https://minedbuildings.z5.web.core.windows.net/global-buildings/dataset-links.csv) | No | ODbL | Per building | Yes (Overture is easier) | Y |
| TxGIO StratMap Land Parcels / TCAD | Parcels, possibly year built and size | [TxGIO](https://tnris.org/stratmap/land-parcels.html) | No | UNVERIFIED | Per parcel | Marginal | N |
| ResStock 2024 AMY2018 r2 | Per-building 15-min end-use load (TX parquet) | [OEDI S3](https://oedi-data-lake.s3.amazonaws.com/?list-type=2&prefix=nrel-pds-building-stock/end-use-load-profiles-for-us-building-stock/2024/resstock_amy2018_release_2/&delimiter=/) | No | CC BY 4.0 (UNVERIFIED) | 15-min, 1 year (2018 weather) | Yes | Y (listing) |
| ResStock 2021 AMY2018 r1 by-county | Travis County (`g4804530`) aggregates by building type | [OEDI S3](https://oedi-data-lake.s3.amazonaws.com/?list-type=2&prefix=nrel-pds-building-stock/end-use-load-profiles-for-us-building-stock/2021/resstock_amy2018_release_1/timeseries_aggregates/by_county/state=TX/) | No | CC BY 4.0 (UNVERIFIED) | 15-min, county aggregate | Yes | Y (listing) |
| Pecan Street Kaggle sample | 10 Austin homes, circuit-level (HVAC, solar), 3 days Aug 2018 | Kaggle (exact URL UNVERIFIED) | Kaggle login | Kaggle terms (UNVERIFIED) | 1-min | Yes (validation only) | N (URL 404) |
| Pecan Street Dataport (university) | Up to 75 homes, Austin/NY/CA | [dataport.pecanstreet.org](https://dataport.pecanstreet.org/) | Account plus academic ID | Non-commercial, education and research only | 1-min / 1-sec | **No** (approval ~3 business days, licensing) | Y (terms page) |
| Smart Meter Texas | Customer's own meter data | smartmetertexas.com | Account | — | 15-min | No | N |
| NWS api.weather.gov | Live forecast and observations (KAUS) | `api.weather.gov/points/30.2672,-97.7431` → EWX/156,91 | No (User-Agent required) | US Gov public | Hourly forecast; obs about 5–60 min | Yes | Y |
| Open-Meteo | Forecast plus ERA5 history since 1940 (Uri min 4.5 °F; Aug 2023 max 106.9 °F) | `api.open-meteo.com`, `archive-api.open-meteo.com` | No | CC BY 4.0; free tier **non-commercial**, 10k calls/day | Hourly (0.1–0.25° reanalysis) | **Yes** | Y |
| NOAA NCEI ISD (global-hourly) | KAUS station observations | `ncei.noaa.gov/access/services/data/v1?dataset=global-hourly&stations=72254013904` | No | US Gov public | Sub-hourly / hourly | Yes | Y |
| NLR (ex-NREL) NSRDB | Solar irradiance | `developer.nlr.gov/docs/solar/nsrdb/` | Yes (API key) | UNVERIFIED | 5–60 min | Marginal | Partial (docs 200) |
| PVWatts v8 (NLR) | Hourly PV output (7 kW → 10,441 kWh/yr) | **`developer.nlr.gov`**/api/pvwatts/v8.json (`developer.nrel.gov` dead) | Yes (DEMO_KEY: 10 calls; free key 1,000/hr) | US Gov (UNVERIFIED) | Hourly TMY | Yes | Y |
| pvlib 0.15.2 | Offline PV modeling | PyPI | No | BSD-3 | Any | Yes | Y (PyPI) |
| EAGLE-I (figshare v4) | County customers-out 2014–2025, Uri script | [DOI 10.6084/m9.figshare.24237376.v4](https://doi.org/10.6084/m9.figshare.24237376.v4) | No | CC BY 4.0 | 15-min, county | Yes (download 2021 only, 1.1 GB) | Y |
| ORNL OpenEnergyHub EAGLE-I API | Same data via API | openenergyhub.ornl.gov | — | — | — | No (HTTP 403) | Y (blocked) |
| poweroutage.us | Live and historic outages | poweroutage.us | — | Commercial | Utility/county | No (HTTP 403) | Y (blocked) |
| Austin Energy / Oncor outage maps | Live outage maps (Kubra StormCenter) | outagemap.austinenergy.com; stormcenter.oncor.com | No | Terms UNVERIFIED | Live | No (undocumented JSON) | Partial |
| Utility hosting-capacity maps (Oncor, AE, CNP) | DER hosting capacity | None found public | — | — | — | No | N |
| MapLibre GL JS 6.11.2 | Web map renderer | npm | No | BSD-3 | — | Yes | Y |
| deck.gl 9.4.0 | GPU data layers | npm | No | MIT | — | Yes | Y |
| OpenFreeMap | Vector basemap tiles and styles | `https://tiles.openfreemap.org/styles/liberty` | **No** | Free incl. commercial; OSM attribution | — | **Yes** | Y |
| Protomaps PMTiles | Self-hosted basemap | [maps.protomaps.com/builds](https://docs.protomaps.com/basemaps/downloads) | No | OSM-derived (ODbL) | — | Yes | Partial |
| Stadia Maps | Hosted tiles | stadiamaps.com | Signup | Commercial tiers | — | Avoid | N |
| Mapbox GL JS 3.31 | Web map renderer | npm | Token | Proprietary | — | Avoid | Y (license field) |
| kepler.gl 3.3.0-alpha.14 | Exploratory geo viz | npm | No (Mapbox token optional, UNVERIFIED) | MIT | — | For exploration only | Y (npm) |

---

## Recommended minimal stack for 48 hours

1. **Grid topology: NREL SMART-DS AUS 2018, sub-region P1U.**
   - Take one ~1,000-customer feeder, for example `p1uhs19_1247--p1udt17263` (1,012 customers, 7.0 MW peak, 379 service transformers). Use the whole substation if the team wants multiple feeders under one substation to fail over.
   - Download the `opendss_no_loadshapes/<substation>/` folder (~6 MB), the matching `geojson/<feeder>.json`, and `metrics.csv`.
   - Why: it is the only free source with real Austin geography, service transformers, 12.47 kV feeders, and pre-attached AC-heavy load. It is CC BY 4.0, needs no key, and was tested today.
   - De-rate transformers from 27.5/55/82.5 back to 25/50/75 kVA so stress shows up.
2. **Physics referee: OpenDSSDirect.py 0.9.4.**
   - Measured 41 ms per snapshot and 1.1 s per simulated day at 5-minute steps on a 6,817-load substation, so real power flow is affordable every tick.
   - Report transformer loading and bus voltage (0.95/1.05 pu bands).
   - Use pandapower only if the team discards SMART-DS and generates its own network.
3. **Controller model: a capacity bucket per service transformer (kVA) and feeder head (MW).**
   - This is the "controller that knows feeder capacity."
   - Demo naive dispatch against capacity-aware dispatch, with OpenDSS as referee. That answers the Base engineer's "each additional battery on a stressed feeder" question directly and exposes voltage effects a bucket model misses.
4. **Load: SMART-DS `load_data` parquet** (15-minute, with `cooling_kw`), interpolated to 5 minutes.
   - For Uri and the Aug 2023 heat wave, rescale AC and heating with a simple temperature regression driven by weather data.
   - Fallback: ResStock 2024 TX building parquets, or the 2021 Travis County aggregates.
   - Skip Pecan Street: licensing and approval time.
5. **Weather: Open-Meteo.**
   - Use the archive for Uri (2021-02-10 to 22) and Aug 2023, and the forecast for "live". Cache as CSV, since the free tier is non-commercial.
   - Use NWS `api.weather.gov` (EWX/156,91, KAUS) for a live "today" panel.
   - Use NCEI global-hourly KAUS if judges ask for station truth.
6. **Solar:** SMART-DS solar profiles, or about 10–15 **PVWatts v8** archetype calls at **`developer.nlr.gov`**. Get a free key; DEMO_KEY is capped at 10 calls, and `developer.nrel.gov` no longer resolves. pvlib is the offline alternative.
7. **Outages:** **EAGLE-I 2021 CSV** from figshare (CC BY 4.0), filtered to Travis, Williamson and Hays, for a historical Uri replay. Model feeder/substation trips, generator trips and cyberattacks as scripted events.
8. **Real-world context layer:** one **Overpass bbox** pull of `power=substation` and `power=line` for the Austin metro, saved as static GeoJSON. Show operator tags (Austin Energy, Oncor, PEC, LCRA). Skip HIFLD (shut down) and the Microsoft legacy footprints (dead URL). Add Overture buildings only if there is time.
9. **Map UI: MapLibre GL JS 6.x + deck.gl 9.4 + OpenFreeMap "liberty" style.** No keys and no limits; attribution is "OpenFreeMap © OpenMapTiles Data from OpenStreetMap."
   - `GeoJsonLayer` for feeders, colored by loading.
   - `ScatterplotLayer` for 1,000 homes, colored by battery state of charge.
   - `IconLayer` for substations.
   - Avoid Mapbox and Stadia tokens.
10. **Framing caveats for the pitch:**
    - SMART-DS networks are synthetic, although placed on real Austin buildings.
    - The sample feeders sit in north Austin, which in reality is Austin Energy territory.
    - Base's pricing page now lists Austin Energy as well as Oncor. Confirm the plan type with the Base/ERCOT researcher before claiming where Base operates.
