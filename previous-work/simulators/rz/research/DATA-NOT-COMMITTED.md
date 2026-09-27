# Data not committed

What stayed on RZ's machine when `simulators/rz/research/` was built (26 Sep 2026), why, and how to get it back. Budget for this folder: 40 MB in total and no file over 5 MB. Local paths are RZ's machine; sizes are on-disk sizes.

One more file stays local on purpose and is never published: a notes file of the Base engineer conversations from 26 Sep. Its substance, paraphrased, is in `capacity-planner/` and in RZ's ruling (`brief/HANDOVER-account1.md`, section 3).

## 1. Whole folders left out

| Local path | Size | What it is | How to get it back |
|---|---|---|---|
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/evidence/scratchpad-20260925` | 207.5 MB | Research-phase scratch (25 Sep): copies of Base Power web pages and PDFs (`base/`), ERCOT annual price workbooks and zips (`ercot/rtm2021`, `bp-data-ingest/rtm2025*`, `rtm2026*`, including the 7.8 MB all-zones `rtm2026_lz.csv` that `data/ercot/lz_north_2026.csv` in the repo was extracted from), SMART-DS feeder models (`sds/`, `sds2/`), third-party reports (`som2025.pdf`, `uri.pdf`, `inertia.pdf`, `blackiot.pdf`, `ashandout.pdf`), `msb.csv`, job-listing and Reddit dumps, failed API probes. Only the small analysis scripts and data pulls listed in `evidence/README.md` were kept. | ERCOT MIS report 13061 (NP6-785-ER, RTM load-zone and hub prices; listing kept at `evidence/research-20260925/scratch/bp-data-ingest/mis_13061.json`), download `https://www.ercot.com/misdownload/servlets/mirDownload?doclookupId=<DocID>` then `extract_rtm.py` (kept). SMART-DS: `https://oedi-data-lake.s3.amazonaws.com/SMART-DS/v1.0/2018/AUS/P1U/`. Base pages: basepowercompany.com. Report URLs are cited in `notes/` and `reports/`. |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/shots` | 274.7 MB | Full-resolution PNG screenshots from every checkpoint, judge round, design panel and lane (about 700 files). 24 were downscaled into `shots/`. | Regenerate with `scripts/smoke_ui.sh all` (copy in `orchestration/smoke_ui.sh`) against any commit; links in `scripts/deeplinks.txt`. |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/scout-main` | 8.6 MB | A copy of the team repo as of 25 Sep 23:25 CDT (docs, demos, four-home-simulation) taken by the repo scout. No unique outputs. | Git history of https://github.com/namana-labs/hugging-base. |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/scout-rebuild` | 7.4 MB | Copies of `four-home-simulation/` and `demos/grid-stories/` used to try a rebuild; its `build_replays.log` is empty and `http.log` is a local server log. No unique outputs. | Git history of the team repo. |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/.venv-critic` | 87.0 MB | Python virtual environment used by critics. | Recreate: `python3 -m venv` + `pip install OpenDSSDirect.py==0.9.4 numpy`. |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/.venv-scout` | 74.5 MB | Python virtual environment used by the scout. | Same as above. |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/hugging-base` | 9.1 MB | A stale clone of the team repo (main at dd891ca, 3 commits behind origin). Checked on 26 Sep 17:10Z: no untracked files (only an ignored `__pycache__/`), no unpushed commits, no stashes. | Not needed; the remote has everything. |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/site/ems/__pycache__` | 170 KB | Python bytecode. | Regenerated on import. |
| `/Users/rzalagbada/hb-overnight/cache` | 334.5 MB | SMART-DS per-home load shapes (`smartds/*.csv`, about 500 files) and `osm_buildings.json` (2.7 MB, OpenStreetMap footprints). | SMART-DS: `https://oedi-data-lake.s3.amazonaws.com/SMART-DS/v1.0/2018/AUS/P1U/profiles/<name>.csv`. OSM: the Overpass query in `build-log/OVERNIGHT_BUILD_PROMPT.md` (section on `osm_buildings.json`). The repo commits only the slices it uses. |
| `/Users/rzalagbada/hb-overnight/tmp` | 1.2 GB | Working scratch from the overnight build and round 2: per-run screenshot folders, headless-Chrome profiles, local `http-*.log` server logs, review checkouts, one-off shell scripts. Kept: 10 probe scripts (`evidence/overnight/probes/`) and one PR body (`build-log/pr-bodies/gate-l3-pr8-body.md`). | Not needed. |
| `/Users/rzalagbada/hb-overnight/c3, /Users/rzalagbada/hb-overnight/judge-0, judge-1, judge-2, review-* (11 folders)` | about 470 MB | Fresh checkouts of the team repo used for the C3 gate, the three judge rounds and the teammate reviews (37 to 49 MB each). Their outputs are in `evidence/overnight/` and `reviews/`. | Git history of the team repo. |
| `/Users/rzalagbada/hb-overnight/wt` | 694.3 MB | Lane git worktrees (l0 to l5, gate). Not copied and not touched. The only uncommitted work (lane l5) is preserved as `round2/l5-p2-story-UNCOMMITTED-20260926T1655Z.patch`. | Branches `overnight/*` on the team repo; draft PRs #27, #28, #34, #35. |
| `/Users/rzalagbada/hb-overnight/evidence` | 0 B | Empty folder. | - |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/judge-R1/committed, judge-R2/committed` | about 18 MB | Copies of the committed `ui/data/*.json` the judges checked against (about 9 MB per round). | The same files are in the repo at the commit each judge report names. |

## 2. Large single files left out (500 KB or more)

Raw downloads (PDF, HTML, XLSX, ZIP, DOCX, PPT), text pulled out of third-party PDFs, and anything over 2 MB. The scripts that used them and their JSON/CSV outputs are in `evidence/`.

| Local path | Size | Why left out | How to re-fetch |
|---|---|---|---|
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/assets-demand/doe_dt_nopr_tsd_complete.pdf` | 15.1 MB | raw download / binary (.pdf) | <https://www1.eere.energy.gov/buildings/appliance_standards/pdfs/dt_nopr_tsd_complete.pdf> |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/evidence/live-20260925/freq-nprotocols-20260302.pdf` | 11.6 MB | raw download / binary (.pdf) | <https://www.ercot.com/files/docs/2026/02/26/March-2-2026-Nodal-Protocols.pdf> |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/evidence/live-20260925/dq-src-2003-blackout-final-report.pdf` | 6.7 MB | raw download / binary (.pdf) | <https://www.energy.gov/sites/default/files/oeprod/DocumentsandMedia/BlackoutFinal-Web.pdf> |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/interconnection/cnp_houston_tariff_retail_delivery.pdf` | 6.5 MB | raw download / binary (.pdf) | listed in evidence/capacity-planner/interconnection/fetch-log.txt |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/interconnection/dg_reports_2025/oncor_dg_report_2025.xlsx` | 5.7 MB | raw download / binary (.xlsx) | listed in evidence/capacity-planner/interconnection/fetch-log.txt |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/assets-demand/arxiv_2410.04540.pdf` | 5.3 MB | raw download / binary (.pdf) | <https://arxiv.org/pdf/2410.04540> |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/interconnection/ae_dg_interconnection_guide_r14.pdf` | 4.8 MB | raw download / binary (.pdf) | listed in evidence/capacity-planner/interconnection/fetch-log.txt |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/assets-demand/arxiv_2604.18411.pdf` | 4.1 MB | raw download / binary (.pdf) | <https://arxiv.org/pdf/2604.18411> |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/interconnection/sapn_flexible_exports_final_report.pdf` | 3.5 MB | raw download / binary (.pdf) | listed in evidence/capacity-planner/interconnection/fetch-log.txt |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/interconnection/puct54233_094_oncor_2025.pdf` | 3.3 MB | raw download / binary (.pdf) | listed in evidence/capacity-planner/interconnection/fetch-log.txt |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/assets-demand/nrel_dgen_65231.pdf` | 3.2 MB | raw download / binary (.pdf) | <https://docs.nlr.gov/docs/fy16osti/65231.pdf> |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/interconnection/dg_reports_2025/cnp_dg_report_2025.xlsx` | 3.2 MB | raw download / binary (.xlsx) | listed in evidence/capacity-planner/interconnection/fetch-log.txt |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/interconnection/oncor_tariff_retail_delivery.pdf` | 3.1 MB | raw download / binary (.pdf) | listed in evidence/capacity-planner/interconnection/fetch-log.txt |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/interconnection/puct54233_089_draft_p1-100.pdf` | 3.0 MB | raw download / binary (.pdf) | listed in evidence/capacity-planner/interconnection/fetch-log.txt |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/market-profit/damlzhbspp_2025/rpt.00013060.0000000000000000.DAMLZHBSPP_2025.xlsx` | 2.8 MB | raw download / binary (.xlsx) | listed in evidence/capacity-planner/market-profit/fetch-log.txt |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/assets-demand/graziano_gillingham_2015.pdf` | 2.4 MB | raw download / binary (.pdf) | <https://resources.environment.yale.edu/gillingham/GrazianoGillingham_15_SpatialPatternsPVSystems.pdf> |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/interconnection/puct58306_577_oncor_nashawati_rebuttal.pdf` | 2.4 MB | raw download / binary (.pdf) | listed in evidence/capacity-planner/interconnection/fetch-log.txt |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/evidence/live-20260925/freq-nog-20260201.pdf` | 2.3 MB | raw download / binary (.pdf) | <https://www.ercot.com/files/docs/2026/01/29/February-1-2026-Nodal-Operating-Guide.pdf> |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/assets-demand/tf_capacity_sweep_g20.json` | 2.2 MB | over 2 MB | listed in evidence/capacity-planner/assets-demand/fetch-log.txt |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/assets-demand/tf_capacity_sweep_g0.json` | 2.2 MB | over 2 MB | listed in evidence/capacity-planner/assets-demand/fetch-log.txt |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/evidence/live-20260925/freq-ercot-as-study-2024.pdf` | 2.2 MB | raw download / binary (.pdf) | <https://www.ercot.com/files/docs/2024/10/07/ERCOT-Ancillary-Services-Study-Final-White-Paper.pdf> |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/assets-demand/arxiv_1805.00630.pdf` | 2.0 MB | raw download / binary (.pdf) | <https://arxiv.org/pdf/1805.00630> |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/market-profit/damlzhbspp_2026/rpt.00013060.0000000000000000.DAMLZHBSPP_2026.xlsx` | 2.0 MB | raw download / binary (.xlsx) | listed in evidence/capacity-planner/market-profit/fetch-log.txt |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/interconnection/doe_i2x_der_roadmap_2025.pdf` | 2.0 MB | raw download / binary (.pdf) | listed in evidence/capacity-planner/interconnection/fetch-log.txt |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/market-profit/damlzhbspp_2025.zip` | 2.0 MB | raw download / binary (.zip) | listed in evidence/capacity-planner/market-profit/fetch-log.txt |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/interconnection/oncor_esg_2025.pdf` | 1.9 MB | raw download / binary (.pdf) | listed in evidence/capacity-planner/interconnection/fetch-log.txt |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/assets-demand/tsd.txt` | 1.9 MB | text extracted from a third-party document (re-fetch from source) | listed in evidence/capacity-planner/assets-demand/fetch-log.txt |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/assets-demand/osti_1347199_ca_pv_forecast.pdf` | 1.9 MB | raw download / binary (.pdf) | <https://osti.gov/servlets/purl/1347199> |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/evidence/live-20260925/n1-doe-flisr-2014.pdf` | 1.9 MB | raw download / binary (.pdf) | <https://www.energy.gov/sites/prod/files/2016/10/f33/Fault_Location_Impact_Duration_Dec_2014.pdf> |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/interconnection/puct54233_111_aep_2025.pdf` | 1.8 MB | raw download / binary (.pdf) | listed in evidence/capacity-planner/interconnection/fetch-log.txt |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/interconnection/oncor_dg_interconnection_presentation.pdf` | 1.7 MB | raw download / binary (.pdf) | listed in evidence/capacity-planner/interconnection/fetch-log.txt |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/interconnection/dg_reports_2025/aeptx_dg_report_2025.xlsx` | 1.7 MB | raw download / binary (.xlsx) | listed in evidence/capacity-planner/interconnection/fetch-log.txt |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/evidence/live-20260925/res-src-2026-as-methodology.pdf` | 1.6 MB | raw download / binary (.pdf) | <https://mis.ercot.com> |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/evidence/live-20260925/volt-ercot-api-specs-pubapi-github.json` | 1.5 MB | copy of a third-party file (ERCOT public API OpenAPI spec) | <https://raw.githubusercontent.com/ercot/api-specs/main/pubapi/pubapi-apim-api.json> |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/interconnection/tnmp_pto_guidelines.pdf` | 1.4 MB | raw download / binary (.pdf) | listed in evidence/capacity-planner/interconnection/fetch-log.txt |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/market-profit/damlzhbspp_2026.zip` | 1.4 MB | raw download / binary (.zip) | listed in evidence/capacity-planner/market-profit/fetch-log.txt |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/assets-demand/puct_54233_58_1312998.pdf` | 1.4 MB | raw download / binary (.pdf) | <https://interchange.puc.texas.gov/Documents/54233_58_1312998.PDF> |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/evidence/live-20260925/flow-src-ercot-ros-dc-ties-2007-12-11.ppt` | 1.2 MB | raw download / binary (.ppt) | listed in evidence/research-20260925/ercot-live-20260925/ |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/assets-demand/puct_54233_31_1265324.pdf` | 1.2 MB | raw download / binary (.pdf) | <https://interchange.puc.texas.gov/Documents/54233_31_1265324.PDF> |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/interconnection/puct_59523_023.pdf` | 1.2 MB | raw download / binary (.pdf) | listed in evidence/capacity-planner/interconnection/fetch-log.txt |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/interconnection/oncor_res_small_comm_requirements_2025.pdf` | 1.1 MB | raw download / binary (.pdf) | listed in evidence/capacity-planner/interconnection/fetch-log.txt |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/assets-demand/bollinger_gillingham_2012.pdf` | 1.0 MB | raw download / binary (.pdf) | <https://resources.environment.yale.edu/gillingham/BollingerGillingham_PeerEffectsSolar.pdf> |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/assets-demand/arxiv_1706.06255.pdf` | 1014 KB | raw download / binary (.pdf) | <https://arxiv.org/pdf/1706.06255> |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/interconnection/oncor_app_certified.pdf` | 990 KB | raw download / binary (.pdf) | listed in evidence/capacity-planner/interconnection/fetch-log.txt |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/interconnection/oncor_tariff_retail_delivery.txt` | 985 KB | text extracted from a third-party document (re-fetch from source) | listed in evidence/capacity-planner/interconnection/fetch-log.txt |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/assets-demand/doe_dt_final_rule_2024.htm` | 965 KB | raw download / binary (.htm) | <https://www.govinfo.gov/content/pkg/FR-2024-04-22/html/2024-07480.htm> |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/assets-demand/ukpn_dnoa_methodology_2026.pdf` | 965 KB | raw download / binary (.pdf) | <https://media.umbraco.io/ukpn-cms/1pfciexi/dnoa-methodology-march-2026-final-encrypted.pdf> |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/interconnection/aeptx_quickstart.pdf` | 952 KB | raw download / binary (.pdf) | listed in evidence/capacity-planner/interconnection/fetch-log.txt |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/interconnection/puct54233_097_cnp_2025.pdf` | 947 KB | raw download / binary (.pdf) | listed in evidence/capacity-planner/interconnection/fetch-log.txt |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/evidence/live-20260925/n1-ercot-rtcb-sim-examples-training.pdf` | 946 KB | raw download / binary (.pdf) | <https://www.ercot.com/files/docs/2025/04/17/RTC_RealTime_Market_Simulator_April-RTCBTF.pdf> |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/interconnection/irec_mip_2023.pdf` | 930 KB | raw download / binary (.pdf) | listed in evidence/capacity-planner/interconnection/fetch-log.txt |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/evidence/live-20260925/n1-protocols-section6.docx` | 928 KB | raw download / binary (.docx) | <https://www.ercot.com/files/docs/2024/06/28/06-082826_Nodal.docx> |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/interconnection/oncor_app_dgr_desr.pdf` | 923 KB | raw download / binary (.pdf) | listed in evidence/capacity-planner/interconnection/fetch-log.txt |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/market-profit/lbnl_vos_2015.pdf` | 863 KB | raw download / binary (.pdf) | listed in evidence/capacity-planner/market-profit/fetch-log.txt |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/interconnection/cnp_houston_tariff_retail_delivery.txt` | 839 KB | text extracted from a third-party document (re-fetch from source) | listed in evidence/capacity-planner/interconnection/fetch-log.txt |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/interconnection/heco_rule22.pdf` | 820 KB | raw download / binary (.pdf) | listed in evidence/capacity-planner/interconnection/fetch-log.txt |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/market-profit/modo_bess_make_money.html` | 766 KB | raw download / binary (.html) | <https://modoenergy.com/research/en/how-does-battery-energy-storage-make-money> |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/market-profit/notboring_base_ch2.html` | 670 KB | raw download / binary (.html) | <https://www.notboring.co/p/base-power-company-chapter-2> |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/market-profit/modo_capture_rates.html` | 654 KB | raw download / binary (.html) | <https://modoenergy.com/research/en/ercot-capture-rates-benchmarking-optimizer-performance-jupiter-power-hunt-energy-network-smt> |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/market-profit/modo_feb2026.html` | 647 KB | raw download / binary (.html) | <https://modoenergy.com/research/en/february-2026-ercot-bess-benchmark-rtcb-revenues-batteries-performance> |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/assets-demand/nrel_dt_demand_2024.pdf` | 621 KB | raw download / binary (.pdf) | <https://www.osti.gov/servlets/purl/2309697> |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/assets-demand/osti_1894504_peer_effects.pdf` | 610 KB | raw download / binary (.pdf) | <https://www.osti.gov/servlets/purl/1894504> |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/interconnection/pge_opflex_report_2025.pdf` | 591 KB | raw download / binary (.pdf) | <https://www.cpuc.ca.gov/-/media/cpuc-website/divisions/energy-division/documents/rule21/smart-inverter-working-group/pge_opflex_report_2025.pdf> |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/assets-demand/puct_54233_105_1513917.pdf` | 553 KB | raw download / binary (.pdf) | <https://interchange.puc.texas.gov/Documents/54233_105_1513917.PDF> |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/interconnection/doe_i2x_der_roadmap_2025.txt` | 537 KB | text extracted from a third-party document (re-fetch from source) | listed in evidence/capacity-planner/interconnection/fetch-log.txt |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/interconnection/aeptx_customer_info_packet.pdf` | 531 KB | raw download / binary (.pdf) | listed in evidence/capacity-planner/interconnection/fetch-log.txt |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/interconnection/puct54233_089_draft_p101-127.pdf` | 510 KB | raw download / binary (.pdf) | listed in evidence/capacity-planner/interconnection/fetch-log.txt |

## 3. Screenshots left out, by folder

App screenshots taken by gates, judges and lanes (PNG, 0.4 to 0.8 MB each). A curated, downscaled set is in `shots/`; the matching page text is kept next to the logs in `evidence/overnight/`. Regenerate any of them with `scripts/smoke_ui.sh` against the commit the log names.

| Local folder | Files | Total |
|---|---|---|
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/gate/l3-r2-shots` | 12 | 8.0 MB |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/gate/l4-r2-shots` | 12 | 7.9 MB |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/gate/l4-shots-fixture` | 9 | 5.8 MB |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/gate/l4-shots-real` | 7 | 4.8 MB |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/gate/l5-r2-main-shots` | 32 | 22.5 MB |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/gate/l5-r2-shots` | 32 | 22.5 MB |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/judge-R1/screen` | 11 | 7.9 MB |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/judge-R2/screen` | 23 | 15.6 MB |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/l2-p1-r2/page-text` | 3 | 2.2 MB |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/l4-scene-p1/fr0-shots` | 9 | 5.9 MB |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/l4-scene-p1/shots-real` | 7 | 4.8 MB |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/l5-p2-story/shots-r1-beats` | 14 | 9.5 MB |

## 4. Smaller files left out, by folder (under 500 KB each)

| Local folder | Files | Total | Types | Why | How to re-fetch |
|---|---|---|---|---|---|
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/evidence/live-20260925` | 33 | 4.1 MB | .docx, .html, .pdf, .xlsx, .zip | raw download / binary (.docx); raw download / binary (.html); raw download / binary (.pdf); raw download / binary (.xlsx); raw download / binary (.zip) | URLs in evidence/research-20260925/ercot-live-20260925/ |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/evidence/live-20260925/n1-np686-raw` | 24 | 64 KB | .zip | raw download / binary (.zip) | URLs in evidence/research-20260925/ercot-live-20260925/ |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/assets-demand` | 30 | 2.9 MB | .html, .pdf, .txt | raw download / binary (.html); raw download / binary (.pdf); text extracted from a third-party document (re-fetch from source) | URLs in evidence/capacity-planner/assets-demand/fetch-log.txt |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/grid-assets` | 4 | 720 KB | .xlsx | raw download / binary (.xlsx) | URLs in capacity-planner/DATA-GRID-ASSETS.md (source table and tested-URL table) |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/interconnection` | 116 | 15.6 MB | .docx, .html, .pdf, .txt, .xml | raw download / binary (.docx); raw download / binary (.html); raw download / binary (.pdf); raw download / binary (.xml); text extracted from a third-party document (re-fetch from source) | URLs in evidence/capacity-planner/interconnection/fetch-log.txt |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/interconnection/dg_reports_2025` | 1 | 458 KB | .xlsx | raw download / binary (.xlsx) | URLs in evidence/capacity-planner/interconnection/fetch-log.txt |
| `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/market-profit` | 20 | 2.4 MB | .html, .pdf, .txt, .xlsx, .zip | raw download / binary (.html); raw download / binary (.pdf); raw download / binary (.xlsx); raw download / binary (.zip); text extracted from a third-party document (re-fetch from source) | URLs in evidence/capacity-planner/market-profit/fetch-log.txt |

