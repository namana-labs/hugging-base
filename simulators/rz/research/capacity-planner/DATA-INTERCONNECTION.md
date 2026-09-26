# DATA-INTERCONNECTION: how Texas utilities decide whether a battery fits on a transformer

Interconnection rules scout, 26 Sep 2026. Every access claim was tested today with `curl`, with no account and no key. Status and byte counts for every fetch are in `overnight/evidence/interconnection/fetch-log.txt`. Copies of the documents are in the same folder, and the 2025 DG-report workbooks and the analysis script are in `evidence/interconnection/dg_reports_2025/`.

Labels: **REAL** = a published rule, tariff, filing or dataset (cited). **SIM** = produced by our simulator. **DERIVED** = arithmetic on REAL numbers, with the method stated. **ASSUMPTION** = a knob we choose. **UNVERIFIED** = not confirmed by a fetch today.

This scout is scoped to the capacity planner in RZ's 16:35Z ruling (pick a transformer, slide 0→50 batteries, naive vs feeder-aware, upgrade-or-not card). The engineer's framing is in [local-only engineer notes, not published]; nothing from that file is repeated here.

---

## 1. Bottom line

1. **Texas has no statewide service-transformer screen for small DER.** PUCT 16 TAC §25.211 (effective 5 Jan 2017) only screens at the feeder level. Pre-certified units up to 500 kW that export no more than 15% of feeder load and contribute no more than 25% of fault current pay no study fee (§25.211(g)(1)). Secondary networks use a 25%-of-network-load test (§25.211(h)). §25.212 dates from 1999 and never mentions storage. **REAL.** The service-transformer check is unpublished TDSP practice.
2. **In practice the TDSPs compare nameplate to transformer rating. Base says so itself in PUCT filings.**
   - 2024: most TDSPs grant permission to operate only when storage nameplate does not exceed transformer limits.
   - 2025: some utilities reject applications outright when nameplate exceeds the transformer rating, even though the system would never export that much ([Base, 54233 item 85](https://interchange.puc.texas.gov/Documents/54233_85_1397563.PDF); [item 92](https://interchange.puc.texas.gov/Documents/54233_92_1513556.PDF)).

   **REAL (Base's claim).** That rule is the likely mechanism behind blocked neighbourhoods.
3. **Only one Texas utility publishes a number, and it covers our feeder's territory.** Austin Energy denies a DG application when total DG kW AC on a transformer would exceed **90% of the transformer rating**. The customer can then downsize or pay AE to upgrade ([AE DG Interconnection Guide rev 14, Mar 2025](https://austinenergy.com/-/media/project/websites/austinenergy/contractors/ae_dg_interconnection_guide.pdf), p. 13). **REAL.** SMART-DS north Austin sits in AE territory, so this is the most defensible screen for our sim.
4. **Charging (import) counts, not only export.**
   - Oncor's certified-system application asks two things: the maximum charging demand drawn from the Oncor grid, and the worst-case outflow when control logic restricts it ([Oncor application](https://www.oncor.com/content/dam/oncorwww/documents/smart-energy/energy-system-developers/Oncor%20Interconnection%20Application%20for%20Certified%20Systems.pdf.coredownload.pdf)).
   - Oncor told the PUCT in June 2025 that battery DERs have "both a load characteristic as well as energy injection". It said its studies cover equipment loading, and that home batteries may trigger transformer upgrades ([54233 item 94, pp. 16–17](https://interchange.puc.texas.gov/Documents/54233_94_1513679.PDF)).
   - The PUCT draft pre-screen asks for storage "load charging level" ([54233 item 89](https://interchange.puc.texas.gov/Documents/54233_89_1498635.PDF)).

   **REAL.**
5. **Oncor accepts certified export limiting. CenterPoint has no position. No Texas utility says it credits import limiting.**
   - **Oncor:** has allowed power-control-system (PCS) limits since 2018, provided the manufacturer password-protects the settings ([54233 item 114, p. 4](https://interchange.puc.texas.gov/Documents/54233_114_1528557.PDF)).
   - **CenterPoint:** is still reviewing PCS technical barriers and has no position ([54233 item 118](https://interchange.puc.texas.gov/Documents/54233_118_1528663.PDF)).
   - **AEP Texas and TNMP:** nothing public.
   - **Import limiting:** no Texas document credits it as a way to avoid a transformer upgrade (**UNVERIFIED** either way).
6. **Base pays for the upgrade, and no deadline applies to it.**
   - §25.211(m)(3): the utility gives the customer an estimate of the schedule and the customer's cost. The two sign a contract, and interconnection follows within 2 weeks of completion. The rule sets no clock for the upgrade itself.
   - AEP Texas and Austin Energy both say the customer pays. Oncor's FAQ lists a "System Upgrade Fee" and offers the option to downsize instead.
   - No TDSP publishes a price for a service-transformer swap. **REAL.** Use the NREL unit costs already in `DATA-GRID-ASSETS.md`.
7. **The rules are being rewritten, slowly.**
   - PUCT Project 54233 opened in Oct 2022. Staff issued a draft in May 2025, and TDUs met DER providers at a summit in Mar 2026.
   - In Aug 2026, Base and others asked the PUCT to issue a proposal for publication at its 11 Sep open meeting. The filing list today shows no such proposal (last item 132, 25 Aug 2026).
   - In its comments, Base asked for three things: a <50 kW rule, deemed approval after 15 business days, and certified dynamic export limiting accepted in place of the transformer-nameplate test.

   **REAL.**
8. **ERCOT leaves distribution limits to the aggregator.** The ADER Governing Document says ERCOT's systems will not enforce identified distribution limitations when they award or dispatch an ADER ([ADER GD Phase 3.3](https://www.ercot.com/files/docs/2026/03/02/ADER-Pilot-Project-Governing-Document-Phase-3.3.docx), §5). **REAL.** So feeder-aware dispatch (our P1) is Base's job. Today the only way to make it binding for a TDSP is a certified per-site limit.
9. **Flexible connections elsewhere unlock most of the capacity** (all REAL):
   - SA Power Networks: flexible-export sites got 10 kW (or full system size) **99.4% of the time**, against a 1.5 kW fixed alternative.
   - PG&E Flex Connect: sites drew full capacity in **90% of hours**, and load was affected **<1% of the time**.
   - National Grid NY: curtailment target **≤5%** of annual energy.
   - UKPN: 100 MW connected; connection time fell from "years to weeks" (vendor case study).
   - California: Limited Generation Profiles live since July 2025, using 24-value export schedules on UL 3141-certified control.
   - None of these operate in Texas.
10. **New REAL Texas data: every TDSP files a feeder-tagged list of every DG facility each year** (§25.211(n); 2025 reports in [Project 59167](https://interchange.puc.texas.gov/search/filings/?controlNumber=59167), as xlsx).
    - **Oncor:** 3,199 battery-only facilities, 2,871 of them in service in 2025. 96% of those ≤50 kW sit at 11.5 or 23.0 kW.
    - **CenterPoint:** 4,336 new and 3,087 pending battery-only facilities in 2025. One feeder, VCR43, carries 215.

    This is the first public, real, per-feeder measure of Texas home-battery concentration. It is not per transformer (§4).

---

## 2. Source table

### A. Texas rules

| Source | What it says | URL + tested status | Applies to Texas? | How it plugs into the capacity planner |
|---|---|---|---|---|
| **PUCT 16 TAC §25.211** (eff. 1/5/17) | REAL. (g)(1): no pre-interconnection study fee for pre-certified DG ≤500 kW that exports ≤15% of feeder load and contributes ≤25% of fault current. (g)(2): other studies take ≤4 weeks, with a cost estimate first. (h): network secondary, 25% of network load. (m): interconnection within **4 weeks** (pre-certified) or **6 weeks** (other). (m)(3): substantial upgrades mean a schedule and **customer cost** estimate, a contract, and interconnection ≤2 weeks after completion. (n): annual DG report listing each facility and its **feeder**. | [PDF](https://www.puc.texas.gov/agency/rulesnlaws/subrules/electric/25.211/25.211.pdf) **200, 74,895 B** | Yes (TDSPs; only (o) applies to co-ops) | Feeder-level screen only. Put it in as a feeder check (15% of feeder load), not a transformer check. (m)(3) sets **payer = Base** on the upgrade card. (m) gives the timeline row |
| **PUCT 16 TAC §25.212** (1999) | REAL. Protection requirements by size. Reverse-power sensing is required "if the facility is not exporting". No storage, transformer or export-limit provisions | [PDF](https://www.puc.texas.gov/agency/rulesnlaws/subrules/electric/25.212/25.212.pdf) **200, 77,221 B** | Yes | Shows "non-export" is an old, recognised configuration. Nothing on import |
| **PUCT staff discussion draft, 54233 item 89** (14 May 2025): new §25.210, amended §25.211, replacement §25.212 | REAL (draft, not adopted). Pre-screen asks for export level and, for storage, **"approximate load charging level"**. The results must list upgrades, including transformer replacements. CIAC for DER upgrades, with any tariff "allowance" offsetting it. Interconnection-agreement exhibit: a site controller limits aggregate export to an **agreed export limit** | [p. 1–100](https://interchange.puc.texas.gov/Documents/54233_89_1498635.PDF) **200, 3.16 MB**; [p. 101–127](https://interchange.puc.texas.gov/Documents/54233_89_1498636.PDF) **200, 523 KB** | Draft only | Planner input fields to mirror: export kW, charging kW, agreed export limit. These are what a TDSP will ask for |
| **Project 54233 filing list** | REAL. 132 items, Oct 2022 → 25 Aug 2026. No proposal for publication yet. The CY2026 rulemaking calendar lists 54233 as "PFP" | [Filings](https://interchange.puc.texas.gov/search/filings/?controlNumber=54233) **200, 87 KB**; [calendar 24 Jul 2026](https://interchange.puc.texas.gov/Documents/59212_4_1668401.PDF) **200, 117 KB** | Yes | Status line on the "what's next" slide: the rules are in flux |
| **GRIT–TDU DER Interconnection Summit summary** (54233 item 131, 2 Mar 2026) | REAL. Oncor, CenterPoint, TNMP, AEP and SPS met GRIT (Base is a member). Parties agreed to define three capacities: nameplate, export, and **"self-limited export capacity"**. DER providers noted self-limited export is **often used to avoid transformer upgrades**. The allowance question was called a policy matter for PUCT or the Legislature. TDUs are open to a <50 kW track, but only in a separate rulemaking | [PDF](https://interchange.puc.texas.gov/Documents/54233_131_1620703.PDF) **200, 320 KB** | Yes | Supports the planner's three capacity numbers per site: nameplate, export limit, import limit |
| **Joint letter** (54233 item 132, 24 Aug 2026; Base among the signers) | REAL. Asks the PUCT to keep the 11 Sep 2026 date for the proposal. Notes SB 1252 exempts batteries from municipal permitting and SB 1202 allows third-party permit review | [PDF](https://interchange.puc.texas.gov/Documents/54233_132_1677036.PDF) **200, 130 KB** | Yes | Context only |
| **Joint TDUs on hosting capacity** (54233 item 46, Jun 2023: Oncor, AEP Texas, TNMP) | REAL. They oppose any requirement to report hosting capacity, on confidentiality and security grounds | [PDF](https://interchange.puc.texas.gov/Documents/54233_46_1300972.PDF) **200, 148 KB** | Yes | Why the planner must run on SIM data plus Base's own portal reads |
| **Oncor rate-case rebuttal, Nashawati** (58306 item 577) | REAL. Offers DER **pre-screening** on request instead of a hosting-capacity map. 111,450 DERs (>1,600 MW) are on Oncor's system | [PDF](https://interchange.puc.texas.gov/Documents/58306_577_1553814.PDF) **200, 2.57 MB** | Yes | The pre-screen is the real input the planner would replace or pre-empt |
| **Proposed 16 TAC §25.58** (Project 59523; PURA §35.153) | REAL (proposed Apr 2026). A TDU may contract storage capacity from a **power generation company** for distribution reliability. The TDU must show a cost-benefit against building or modifying a traditional distribution facility. **Statewide cap 100 MW**, allocated by load-ratio share. Public hearing noticed Jun 2026; adoption **UNVERIFIED** | [PFP](https://interchange.puc.texas.gov/Documents/59523_5_1615346.PDF) **200, 403 KB**; [filings](https://interchange.puc.texas.gov/search/filings/?controlNumber=59523) **200** | Yes (ERCOT TDUs) | The only Texas route found by which a **utility** pays a storage owner instead of upgrading. It feeds the later "utility ROI" view, not Sunday's card. Whether Base is registered as a PGC is **UNVERIFIED** |

### B. TDSP manuals, forms and tariffs

| Source | What it says | URL + tested status | Applies to Texas? | How it plugs into the capacity planner |
|---|---|---|---|---|
| **Oncor application, certified systems** (10/05/2022) | REAL. "Do you plan to export power". For storage: the **worst-case outflow** when control logic limits outflow below inverter capacity, and the **maximum charging demand from the Oncor grid (kW)**. Oncor secures funding for any system impacts. Meter reprogramming takes up to 30 days. Includes the DD36 study-fee table | [PDF](https://www.oncor.com/content/dam/oncorwww/documents/smart-energy/energy-system-developers/Oncor%20Interconnection%20Application%20for%20Certified%20Systems.pdf.coredownload.pdf) **200, 1.01 MB** | Yes, Oncor | Per-site inputs the planner should carry: `export_kw_limit` and `import_kw_max`. Oncor evaluates both directions |
| **Oncor tariff, DD36 DG study fee** (in the application; Tariff 6.1.2.4) | REAL. Pre-certified, not on network: $0 up to 10 kW. 10–500 kW: $269.70 non-exporting or $337.15 exporting, and **$0 if under 15% of feeder load and 25% of fault current** | as above; [Tariff for Retail Delivery Service](https://www.oncor.com/content/dam/oncorwww/documents/about-us/regulatory/tariff-and-rate-schedules/Tariff%20for%20Retail%20Delivery%20Service.pdf.coredownload.pdf) **200, 3.24 MB** (rev. 22, eff. 1 Jun 2026) | Yes, Oncor | Fee line on the card: study fees are trivial; the upgrade is the cost |
| **Oncor tariff §5.7 and 6.1.2.2** (Facilities Extension) | REAL. The payer is whoever asks for construction, paying CIAC above an allowance. §5.7.6: an upgrade caused by **added load** charges only the attributable cost. Standard allowance is $291/kW for secondary >10 kW (non-residential classes). §5.7.3: residential construction within 90 days of the agreement. §5.7.4: allowances add up when several applicants share one extension | Tariff above | Yes, Oncor | Whether battery **charging** load earns a load allowance is **UNVERIFIED**; ask Base. The shared-allowance rule is the tariff hook for a pooled "30 members, one upgrade" case |
| **Oncor Residential/Small Commercial Project Requirements** (rev. 1 May 2025) | REAL. Filing checklist for the eTRACK Installer Portal. Meter collars are not allowed. Every DG source needs a visible lockable labelled disconnect (VLLD) within 10 ft of the meter. One IA per metered premise. No transformer screen published | [PDF](https://www.oncor.com/content/dam/oncorwww/documents/for-installers/New-Residential-Requirements-2025.pdf.coredownload.pdf) **200, 1.18 MB** | Yes, Oncor | None (paperwork) |
| **Oncor Electric Service Guidelines** (Feb 2025), §700 | REAL. DG and storage must hold an IA before energising. Portal link given. No transformer or export-limit rule | [PDF](https://www.oncor.com/content/dam/oncorwww/documents/new-construction/construction-guidelines/Electric%20Service%20Guidelines%20Book.pdf.coredownload.pdf) **200, 2.02 MB** | Yes, Oncor | None |
| **Oncor FAQ** | REAL. **System Upgrade Fee:** if the system is big enough to need upgrades, Oncor gives a time and cost estimate, and the customer can reduce system size to avoid the cost. Meter reprogramming takes about 3 weeks after PTO | [page](https://www.oncor.com/content/oncorwww/us/en/home/faqs/faqs-details.html) **200, 451 KB** | Yes, Oncor | The two options on the card: **"limit" vs "upgrade"** |
| **Oncor initial and reply comments on the 2025 draft** (54233 items 94, 114) | REAL. PCS accepted since 2018 when manufacturer-password-protected (item 114). For network pre-interconnection studies, wants 60 working days (capped at 90) instead of 4 weeks, citing batteries' load plus injection (item 94). Proposed rule text: offer the option to **reduce or limit** DER capacity to avoid upgrades. Worries about <50 kW DER across whole subdivisions and their cumulative feeder impact | [item 94](https://interchange.puc.texas.gov/Documents/54233_94_1513679.PDF) **200, 3.47 MB**; [item 114](https://interchange.puc.texas.gov/Documents/54233_114_1528557.PDF) **200, 449 KB** | Yes, Oncor | **Decisive for the planner:** in Oncor territory a password-locked export limit is a real lever today. Import limiting is not stated |
| **CenterPoint Houston Tariff for Retail Delivery Service** (rev. 32, eff. 18 May 2026) | REAL. DG study-fee table: pre-certified, not on network, **non-exporting 10–500 kW $0; exporting $621**. Same 15%/25% waiver. Extensions to premises with DG follow Construction Services §2 and the IA. Transfer trip above 2 MW. Same §5.7.6 added-load rule | [PDF](https://assets.centerpointenergy.com/api/public/content/houston-electric-tariff-for-retail-delivery-service.pdf) **200, 6.77 MB** | Yes, CenterPoint | Fee line. The non-export vs export split is priced |
| **CenterPoint reply comments** (54233 item 118, Aug 2025) | REAL. On PCS: reviewing technical barriers, **no position**. Wants flexibility for DSP-specific review | [PDF](https://interchange.puc.texas.gov/Documents/54233_118_1528663.PDF) **200, 177 KB** | Yes | In CenterPoint territory, treat PCS credit as **not available** (a planner toggle, off by default) |
| **CenterPoint DG web pages** | Old DG manual and FAQ URLs all return 404 after a site rebuild. The current "customer generation" page is **Indiana** content | [customer-generation](https://www.centerpointenergy.com/en-us/our-services/electric-utility/customer-generation) 200 (Indiana); old PDFs **404** (see log) | — | Houston residential DG manual **UNVERIFIED / not found** |
| **AEP Texas quick guide for homeowners** (Oct 2020) | REAL. Typical approval under 35 days, with 90–95% approved on first review. Customer pays for any negative impact, investigation and **system upgrades** | [PDF](https://www.aeptexas.com/lib/docs/cleanenergy/renewable/solar/QuickStartGuide-AEPTexas.pdf) **200, 975 KB** | Yes, AEP Texas | Payer and timeline rows |
| **TNMP interconnection page, application, PTO guide** | REAL. PowerClerk portal; DG meter charge $227; load profile changed 30–45 days after the meter. Application asks whether and how much you will export. No transformer rule | [page](https://tnmp.com/customers/interconnecting) **200, 99 KB**; [app](https://tnmp.com/sites/default/files/2020-02/tnmp-dg-interconnection-app-0220.pdf) **200, 142 KB** | Yes, TNMP | Fee line only |
| **Austin Energy DG Interconnection Guide** (rev 14.0, 31 Mar 2025) | REAL. **All DG kW AC on a transformer ≤ 90% of its rating**, or the application is denied: downsize, or AE upgrades **at the customer's expense**. A NEC 750 energy management system **may be required to set export limits** at final inspection, locked after inspection. Storage and PV may not discharge together unless AE has reviewed the transformer | [PDF](https://austinenergy.com/-/media/project/websites/austinenergy/contractors/ae_dg_interconnection_guide.pdf) **200, 5.02 MB** | Yes (muni; Base's 40 MW AE deal) | **Default screen for our AE-territory feeder.** `N_max = floor((0.9·kVA − existing DG kW) / kW_per_unit)`. Whether AE counts the export-limited kW instead of nameplate is **UNVERIFIED** |

### C. Texas data (new, REAL)

| Source | What it says | URL + tested status | Applies to Texas? | How it plugs into the capacity planner |
|---|---|---|---|---|
| **2025 DG Interconnection Reports, §25.211(n)** (Project 59167, filed Mar 2026) | REAL. Every DG facility with kW, fuel, technology and **feeder**. DERIVED (script in `dg_reports_2025/`), with the per-TDSP counts listed below this table | [filing list](https://interchange.puc.texas.gov/search/filings/?controlNumber=59167) **200**. ZIPs: [Oncor](https://interchange.puc.texas.gov/Documents/59167_6_1612774.ZIP) **200, 12.5 MB**; [CenterPoint](https://interchange.puc.texas.gov/Documents/59167_7_1613100.ZIP) **200, 9.2 MB**; [AEP](https://interchange.puc.texas.gov/Documents/59167_5_1612713.ZIP) **200, 10.0 MB**; [TNMP](https://interchange.puc.texas.gov/Documents/59167_4_1606208.ZIP) **200, 5.2 MB** | Yes | A real per-feeder battery count to calibrate the planner's "existing batteries on this feeder" prior. It also sizes the queue: 3,050 small battery-only CenterPoint projects were pending at year end. There are **no reason codes**, so cancellations cannot be blamed on transformers. **Not per transformer.** An owner is never named, so "these are Base's" is an **INFERENCE** from the 11.3–11.5 kW single and 22.6–23.0 kW double pattern, which matches Base's 11.4 kW legacy inverter |

DERIVED counts from those reports (small = ≤50 kW):

- **Oncor:**
  - 122,767 facilities in total; **3,199 battery-only**, of which 283 went into service in 2024 and 2,871 in 2025;
  - 3,086 of the 3,181 small units sit at 11.0–11.7 kW or 22.0–23.5 kW (3,060 at exactly 11.5 or 23.0);
  - per-feeder counts are p50 2, p90 12 and max 281. Oncor's "Feeder #" is numeric only and may repeat across substations, so those counts are **UNVERIFIED**.
- **CenterPoint:**
  - battery-only facilities: 854 existing, **4,336 new in 2025** (94% of the small ones at 11.0–11.7 or 22.0–23.5 kW), **3,087 pending**, 341 cancelled;
  - over 1,031 feeders, small battery-only units are p50 3, p90 22, p99 58 and max 215 per feeder;
  - about 4.1% of small battery-only projects were cancelled.
- **AEP Texas:** 68 battery-only applications in 2025.
- **TNMP:** 40 storage-only applications in 2025.

### D. Certified control: what can make feeder-aware dispatch binding

| Source | What it says | URL + tested status | Applies to Texas? | How it plugs into the capacity planner |
|---|---|---|---|---|
| **UL 1741 CRD for Power Control Systems** (8 Mar 2019), per the BATRIES toolkit ch. III | REAL. The CRD tests three things: export limiting from all sources, export limiting from storage, and **import limiting to storage**. Operating modes include "import only" (non-export). Limits must hold with a maximum 30 s open-loop response for inadvertent export. Utilities should screen on the **Export Capacity** declared with a certified PCS | [Ch. III PDF](https://energystorageinterconnection.org/wp-content/uploads/2022/03/BATRIES-TOOLKIT-Chapter-III.pdf) **200, 411 KB**; [Ch. VIII](https://energystorageinterconnection.org/wp-content/uploads/2022/03/BATRIES-TOOLKIT-Chapter-VIII.pdf) **200, 216 KB** | The standard is national. Oncor accepts PCS; the other Texas TDSPs have not said | The certifiable "handle": per-site static `export_kw_limit` and `import_kw_limit`. **Base says its systems can use UL 1741 PCS** (item 92). Base's public certification list says only "UL 1741", with no PCS or CRD listing named (research note; **UNVERIFIED**) |
| **UL 3141** (Outline of Investigation for PCS, Ed. 2 2024) | REAL (secondary sources). It supersedes the PCS CRD and adds service-upgrade avoidance and feeder-overload control via load and source control. PG&E now requires **UL 3141 Issue 2** for LGP scheduling. SPAN panels were certified in Oct 2025. The SPAN release claims UL 3141 will be required for PCS in the 2026 NEC (**UNVERIFIED**) | [Mayfield explainer](https://www.mayfield.energy/technical-articles/ul-3141-and-power-control-systems-explained/) **200, 357 KB**; [PG&E Rule 21 cert sheet (Jun 2025)](https://www.pge.com/assets/pge/docs/about/doing-business-with-pge/rule-21-testing-and-certification-instruction-sheet.pdf) **200, 511 KB**; [SPAN](https://www.span.io/blog/span-smart-electrical-panels-earn-first-in-class-ul-3141-power-control-systems-pcs-certification-for-safety) **200, 89 KB**; [ANL tech doc](https://www.anl.gov/argonne-scientific-publications/pub/202752) **403** | Standard is national. Texas is on the 2023 NEC | Time-varying (scheduled) limits need UL 3141-class certification. That is the path to a dispatch *profile*, not just a static cap |
| **NEC 705.13 / 750.30** (2023 NEC) | REAL. An energy management system or PCS may limit current on the premises' busbars and conductors. **It protects premises wiring, not the utility transformer.** Texas adopted the 2023 NEC statewide effective 1 Sep 2023 | [Mayfield (quotes 2020/2023 text)](https://www.mayfield.energy/technical-articles/ul-3141-and-power-control-systems-explained/) 200; [TDLR](https://www.tdlr.texas.gov/electricians/compliance-guide.htm) **200, 53 KB**. NFPA text paywalled (**UNVERIFIED** directly) | Yes (premises) | Do not claim NEC makes a transformer limit binding. It only gives the certified mechanism. AE uses NEC 750 EMS to lock export limits |
| **IEEE 1547-2018 / IREC Model Interconnection Procedures 2023** | REAL. Screen: aggregate **Export Capacity** on a shared single-phase secondary **≤ 65% of transformer nameplate**. Service imbalance ≤20%. The application asks whether storage import is limited below nameplate charge rating, and how | [PDF](https://irecusa.org/wp-content/uploads/2023/08/IREC-Model-Interconnection-Procedures-2023-FINAL-8.23.23.pdf) **200, 952 KB** | Model only (not adopted in Texas) | "IREC 65% export" rule profile. Base cites IREC in item 125 |
| **FERC pro-forma SGIP**, screen 2.2.1.7 | REAL. Aggregate generation on a single-phase shared secondary **≤ 20 kW** | [PDF](https://www.ferc.gov/sites/default/files/2020-04/sm-gen-procedures.pdf) **200, 266 KB** | No (FERC-jurisdictional; ERCOT distribution is PUCT) | "FERC 20 kW" profile, as a conservative bound |
| **DOE i2X DER Interconnection Roadmap** (Jan 2025) | REAL. Distinguish nameplate from export capacity (Sol. 3.7). Allow flexible interconnection to defer upgrades, via PCS (Sol. 2.6, 3.9). Group studies share upgrade cost (Sol. 3.3) | [PDF](https://www.energy.gov/sites/default/files/2025-01/i2X%20DER%20Interconnection%20Roadmap.pdf) **200, 2.07 MB** | Guidance | Supports the "pooled upgrade" option on the card |
| **ENA EREC G100 Issue 2** (UK) | REAL (secondary). A customer limitation scheme caps **export and/or import** to the DNO-agreed value. Settings are locked to engineer level, excursions corrected within about 5 s, fail-safe required | [ENA PDF](https://www.energynetworks.org/assets/images/ENA_EREC_G100_Issue_2_Amendment_2_(2023).pdf) **403**; [Alternergy](https://www.alternergy.co.uk/blog/blog-2/g100-issue-2-import-export-limitation-recommendation-58) **200, 115 KB**; [Versinetic](https://www.versinetic.com/news-blog/g100-g100-import-limitations-explained/) **200, 143 KB** | No | Precedent that **import** limits are a recognised connection term |

### E. Flexible or managed interconnection precedents (results)

| Source | What it says | URL + tested status | Applies to Texas? | How it plugs into the capacity planner |
|---|---|---|---|---|
| **CA Rule 21 Limited Generation Profiles** (D.20-09-035; 2024 order; live 9 Jul 2025) | REAL. An export schedule kept under hosting capacity, using 24 values per month (a 12×24 month-hour profile). PG&E's rule caps it at 90% of the minimum ICA-SG. UL 3141 PCS required | [CPUC LGP page](https://www.cpuc.ca.gov/industries-and-topics/electrical-energy/infrastructure/rule-21-interconnection/limited-generation-profiles) **200, 56 KB**; [PG&E LGP procedures](https://www.pge.com/assets/pge/docs/about/doing-business-with-pge/limited-generation-profile-procedures.pdf) **200, 312 KB**; [IREC blog](https://irecusa.org/blog/regulatory-engagement/california-regulators-open-the-door-for-ders-to-avoid-interconnection-upgrades/) **200, 167 KB** | No | **Output format to copy:** the planner can emit, per transformer, a 12×24 import/export envelope from SIM headroom. That is what Base would file if Texas allowed it |
| **PG&E Flex Connect** (load side) | REAL. Full capacity in 90% of hours; load affected <1% of the time. 5 customers and about 85 prospective (2–10 MW sites). Energised in about 4–8 months versus 1–3 years. Site controls cost roughly $20k–50k+ each, so only large sites are viable today | [Utility Dive](https://www.utilitydive.com/news/pge-sees-rising-interest-in-customer-driven-flexible-interconnection-pil/829447/) **200, 229 KB** (page metadata dated 2 Sep 2026); [PG&E OpFlex report Feb 2025](https://www.cpuc.ca.gov/-/media/cpuc-website/divisions/energy-division/documents/rule21/smart-inverter-working-group/pge_opflex_report_2025.pdf) **200, 605 KB**; [PG&E press Apr 2025](https://investor.pgecorp.com/news-events/press-releases/press-release-details/2025/New-PGE-Service-Offering-Makes-It-Easier-and-Faster-to-Connect-EV-Chargers-EV-Fleets-and-Big-Batteries-to-the-Grid/default.aspx) **200, 115 KB** | No | Precedent for **managed charging (import) as a connection condition**. For Base the control cost is already sunk in the battery |
| **Hawaiian Electric Smart DER Non-Export / Rule 22** (from 1 Apr 2024) | REAL. Non-export systems get a streamlined interconnection with no capacity cap. The BYOD tariff pays for grid services | [Non-export page](https://www.hawaiianelectric.com/products-and-services/smart-renewable-energy-programs/smart-renewable-energy-non-export) **200, 100 KB**; [flyer](https://www.hawaiianelectric.com/documents/products_and_services/customer_renewable_programs/sre_smart_der_non-export_program_flyer.pdf) **200, 146 KB**; [Rule 22](https://www.hawaiianelectric.com/Documents/my_account/rates/hawaiian_electric_rules/22.pdf) **200, 839 KB**; [HPUC DER programs](https://puc.hawaii.gov/energy/der/programs/) **200, 73 KB** | No | "Non-export" profile: export limit 0, still import-limited |
| **National Grid NY ARI pilot and Flex IX petition** (21 Jan 2026) | REAL. Two solar sites (8.25 MW, Peterboro substation) commissioned Nov 2024–Jan 2025. Study-based curtailment target **≤5%** of annual uncurtailed energy, shared pro rata. The petition proposes up to 7 more substations | [Petition PDF](https://documents.dps.ny.gov/public/Common/ViewDoc.aspx?DocRefId=%7B8052E29B-0000-C025-93DD-13BD0999B99A%7D&DocTitle=Petition+Seeking+Approval+to+Offer+Flexible+Interconnection+Service+Options+Under+the+SIR+at+Limited+Locations) **200, 448 KB**; dps.ny.gov pages **403** | No | Pro-rata curtailment is the fairness rule when several batteries share one transformer limit |
| **UKPN Flexible Plug and Play / flexible connections** | REAL. FPP was a £9.7m trial. Vendor case study: over 20 generators and 100 MW connected; "tens of £millions" in avoided upgrades; connection time "from years to weeks". UKPN's own "£80m saved since 2014" is **UNVERIFIED** (site returns 403) | [UKPN innovation](https://innovation.ukpowernetworks.co.uk/projects/flexible-plug-and-play) **200, 98 KB**; [SGS case](https://www.smartergridsolutions.com/media-center/case-studies/uk-power-networks-flexible-plug-and-play) **200, 105 KB**; ukpowernetworks.co.uk **403** | No | Headline precedent (primary-level, large generators) |
| **SA Power Networks Flexible Exports trial** (final report, Oct 2023, ARENA) | REAL. Flexible limit of 1.5–10 kW per phase against a fixed 1.5 kW. Devices got 10 kW or full system capacity **99.4% of the time**. Uses the CSIP-AUS protocol | [PDF](https://arena.gov.au/assets/2024/01/SA-Power-Networks-Flexible-Exports-for-Solar-PV-Trial-Final-Report.pdf) **200, 3.67 MB** | No | The best residential-scale evidence that dynamic limits cost almost no energy while unlocking capacity |

### F. What Base says publicly, and the installer portals

| Source | What it says | URL + tested status | Applies to Texas? | How it plugs into the capacity planner |
|---|---|---|---|---|
| **Base comments, 54233 item 85** (28 May 2024) | REAL. Most TDSPs cap permission to operate at storage nameplate ≤ transformer limits. Base asks for **dynamic export limits**, hosting maps (even OEM-only), and SolarAPP-style automation. It notes installers only learn about viability after the customer has committed, and that some TDSPs take 30 + 30 days for review | [PDF](https://interchange.puc.texas.gov/Documents/54233_85_1397563.PDF) **200, 470 KB** | Yes | Base's own statement of the problem the planner solves: know **before** the member commits |
| **Base comments, 54233 item 92** (27 Jun 2025) | REAL. Base has more than 2,600 homes and 75 MWh installed. Its systems "are capable of using UL Standard 1741 PCS". It proposes a <50 kW rule: a single standard form listing export capability, max withdrawal kW and max injection kW; **approval if certified dynamic export limiting keeps export under the transformer rating**; decision within 15 business days, otherwise deemed approved | [PDF](https://interchange.puc.texas.gov/Documents/54233_92_1513556.PDF) **200, 459 KB** | Yes | Base's proposed rule **ignores import**. The planner can show where charging, not export, binds, which is a finding Base would need before pushing that rule |
| **Base reply, 54233 item 125** (8 Aug 2025) | REAL. 327 projects were past the §25.211 compliance window in April. The body says "this year" (2025); the executive summary says April 2024, so the year is inconsistent. Base supports the Silverstein <50 kW framework: approve if the system stays within transformer limits **or** uses certified dynamic export limiting | [PDF](https://interchange.puc.texas.gov/Documents/54233_125_1528809.PDF) **200, 279 KB** | Yes | Queue-delay input for the card's timeline |
| **Base help: IA and Tariff Agreement** | REAL. In Oncor territory the member signs a Tariff Application 7–10 business days after photo approval, then an IA, sometimes weeks after installation. Re-signing means the original was rejected over changed utility requirements | [Help 10283841](https://help.basepowercompany.com/en/articles/10283841) **200, 94 KB** | Yes | Shows the late-rejection path: the IA can arrive **after** installation |
| **Base utilities page** | REAL. Behind-the-meter batteries at the existing service point avoid new IAs or substation upgrades "in most cases". Core is 20 kW / 39.2 kWh | [page](https://www.basepowercompany.com/utilities) **200, 157 KB** | Yes | Per-unit kW for the screens (20 kW Core; legacy 11.4 kW per earlier research) |
| **Base blog: ADER Phase IV** | REAL. Each device's **max charge and discharge** is sent to the host utility and ERCOT, and the DSP reviews them | [blog](https://www.basepowercompany.com/blog/aggregated-ders-and-the-capacity-crunch) **200, 315 KB** | Yes | A second channel where TDSPs see import kW |
| **ERCOT ADER Governing Document, Phase 3.3** | REAL. The DSP reviews the "Details of the Aggregation" in 10 business days (up to 45) and may reject premises for safety or reliability. Known DSP limits such as premise injection limits go in the registration. ERCOT does **not** enforce distribution limits in dispatch | [docx](https://www.ercot.com/files/docs/2026/03/02/ADER-Pilot-Project-Governing-Document-Phase-3.3.docx) **200, 188 KB** | Yes | Premise injection limits are a real, registrable field. The planner's per-site caps can be written into ADER registration today |
| **Oncor DG portal (eTRACK)** | REAL. Login page only; the installer portal needs registration. Nothing is exposed anonymously | [oncor.anbetrack.com](https://oncor.anbetrack.com/) → oncordg-interconnection.anbetrack.com **200, 200 KB**; [plus.anbetrack.com/oncor-dg](https://plus.anbetrack.com/oncor-dg/#/) **200** | Yes | Base's portal reads (capacity, pre-screen results) are the real input. Planner hook: `utility_reported_headroom_kw` per transformer or premise, typed in by hand, SIM until then |
| **TNMP PowerClerk portal** | REAL. Login only | [tnmpinterconnect.powerclerk.com](https://tnmpinterconnect.powerclerk.com/MvcAccount/Login) **200, 18 KB** | Yes | None |

---

## 3. Short answers

1. **How is a residential battery reviewed against the service transformer?**
   - There is no PUCT transformer screen, only feeder-level 15%/25% study-fee waivers (REAL).
   - TDSPs compare nameplate kW to transformer kVA, according to Base (REAL claim).
   - Austin Energy publishes 90% of rating for all DG kW AC (REAL).
   - Both directions are studied. Oncor collects charging kW and says battery load and injection both drive transformer loading (REAL).
   - Oncor (item 94) wants network pre-interconnection studies at 60 working days, capped at 90, because batteries both load and inject. That shows how long battery studies take.
   - Timelines by rule: 4 or 6 weeks, with no clock on upgrades. AEP Texas says typically under 35 days. Base reports hundreds of projects past the deadline (REAL).
2. **Is certified control accepted?**
   - Oncor: yes for export limits, password-locked, since 2018 (REAL).
   - CenterPoint: no position (REAL).
   - AEP Texas and TNMP: nothing found (**UNVERIFIED**).
   - Import limiting as a way to avoid an upgrade: no Texas evidence (**UNVERIFIED**). Precedents exist in PG&E Flex Connect, UK G100 and IREC's form (REAL).
   - What makes P1 "binding" today is per-site static caps under UL 1741 PCS, or time-varying caps under UL 3141. A live orchestrator alone is not binding for any Texas TDSP (DERIVED from the above).
3. **Who pays and how long?** The DER owner, which is Base for its batteries (§25.211(m)(3); AEP, AE, Oncor documents; REAL). No published Texas price for a swap. No rule clock for the upgrade; interconnection follows within 2 weeks of completion. Lead times and unit costs come from `DATA-GRID-ASSETS.md` (NREL: $3,853–6,057 installed per 25–100 kVA unit in 2017; lead times up to 2 years).
4. **Precedents:** see §2E. The headline numbers are 99.4% (SAPN), 90% of hours (PG&E), ≤5% curtailment (National Grid) and 100 MW with "years to weeks" (UKPN).
5. **Base publicly:**
   - Base asks for dynamic export limits and hosting data.
   - Base says the transformer-nameplate rule causes unnecessary upgrades.
   - Its members sign Oncor's IA late in the process.
   - The portals expose nothing without a login.

---

## 4. Screen arithmetic for the planner (DERIVED)

Batteries per service transformer that pass each paper screen. Cells show **Core (20 kW) / legacy (11.4 kW)** counts.

Assumptions (ASSUMPTION):
- pf = 1, so kW = kVA;
- no existing solar on the transformer;
- one unit per home.

| Screen (source) | 25 kVA | 50 kVA | 75 kVA | Notes |
|---|---|---|---|---|
| A. Nameplate ≤ 100% of kVA (Base's description of TDSP practice; the exact % is **UNVERIFIED**) | 1 / 2 | 2 / 4 | 3 / 6 | Export caps earn **no** credit |
| B. Austin Energy, all DG kW AC ≤ 90% | 1 / 1 | 2 / 3 | 3 / 5 | REAL rule; counts nameplate |
| C. IREC, export capacity ≤ 65%, at full export | 0 / 1 | 1 / 2 | 2 / 4 | Model rule |
| C′. IREC 65% with a certified **5 kW** export cap per site | 3 | 6 | 9 | Same for Core and legacy |
| C″. IREC 65% with a **2 kW** export cap | 8 | 16 | 24 | |
| D. FERC SGIP, 20 kW per shared secondary | 1 / 1 | 1 / 1 | 1 / 1 | kVA-independent |
| E. Physics (SIM): OpenDSS loading plus IEEE C57.91 thermal limits, under naive vs feeder-aware dispatch | from P1 | from P1 | from P1 | The planner's actual answer; it includes charging load and neighbours' load |

Formulas:
- `N_A = floor(kVA / P)`
- `N_B = floor((0.9·kVA − DG_existing) / P)`
- `N_C = floor((0.65·kVA − E_existing) / E_cap)`

Reading:
- With DOE's figure of 2–6 homes per 25 kVA unit (in `DATA-GRID-ASSETS.md`), nameplate screens allow about one Core per transformer.
- A cluster of 30 members spread over a handful of transformers is blocked on paper long before physics binds. That is the gap Base describes (DERIVED illustration; homes per transformer is an ASSUMPTION).
- Rows C′ and C″ show what a certified cap buys, **if** a TDSP screens on export.
- Row E answers the part no paper screen covers: evening **charging** coincident with AC load. Oncor says it studies exactly this.

---

## 5. How it plugs into the capacity planner (Sunday scope)

1. **Rule profile selector.** Rows A–E above, defaulting to B (Austin Energy) for the SMART-DS feeder. Show the paper answer and the physics answer side by side. The difference is "batteries a certified cap could unlock".
2. **Per-site caps as the lever.** Each site carries `P_nameplate`, `export_kw_limit` and `import_kw_limit`.
   - Feeder-aware mode computes the smallest static caps, or a 12×24 month-hour envelope, that keep the transformer inside its thermal limit in OpenDSS.
   - Label a static cap "certifiable under UL 1741 PCS (Oncor accepts)".
   - Label a month-hour envelope "UL 3141-class, CA LGP-style (not yet accepted in Texas)".
3. **TDSP toggle** (REAL behaviour, above):
   - Oncor: export-limit credit on, import credit off;
   - CenterPoint: both off;
   - Austin Energy: nameplate 90%, export limit may be required.
4. **Upgrade-or-not card inputs from this scout:**
   - payer = Base (REAL);
   - options = limit or upgrade (REAL, from Oncor's FAQ and proposed rule text);
   - study fee $0–$621 (REAL);
   - schedule = TDSP estimate, then interconnect within 2 weeks (REAL);
   - swap cost and lead time from `DATA-GRID-ASSETS.md`;
   - pooled members on one transformer: allowances add up for multiple applicants on Oncor load extensions (REAL for load). Whether that applies to battery upgrades is **UNVERIFIED**.
5. **"Existing batteries on this feeder" prior.** Use the 2025 DG-report per-feeder distributions: CenterPoint p50 3, p90 22, max 215. They are REAL Texas concentrations, but per feeder, not per transformer.

---

## 6. What is real vs assumption

**REAL (cited, fetched today)**
- PUCT §25.211/§25.212 text: feeder screens, timelines, and the customer paying for upgrades.
- Austin Energy's 90% transformer screen and its export-limit clause.
- Oncor's forms ask for charging kW and control-limited outflow.
- Oncor accepts password-protected PCS; CenterPoint has no position.
- Oncor and CenterPoint study fees and facilities-extension rules.
- Base's own PUCT statements: the nameplate rule, UL 1741 PCS capability, 327 late projects, and its proposed <50 kW rule.
- The ADER rule that ERCOT does not enforce distribution limits.
- The 2025 DG reports: facility counts by fuel, kW and feeder.
- Precedent results: 99.4% (SAPN), 90%/<1% (PG&E), ≤5% (National Grid), 100 MW (UKPN via vendor).
- Proposed §25.58: 100 MW statewide cap on TDU storage contracts.

**DERIVED**
- The screen arithmetic in §4.
- Per-feeder battery distributions and the 4.1% cancellation share.
- The claim that live orchestration alone is not binding for a TDSP.

**SIM**
- Row E: transformer loading and thermal outcomes on SMART-DS, naive vs aware, and the resulting per-site caps and envelopes.

**ASSUMPTION**
- pf = 1 and kW = kVA.
- No existing solar per transformer.
- Homes per transformer.
- Screen A's exact 100%.
- Which rule profile each TDSP really applies to a given premise.
- Any 12×24 envelope being acceptable in Texas.

**INFERENCE (not in the data)**
- That the 11.3–11.5 kW and 22.6–23.0 kW battery-only facilities in the DG reports are Base installs.

---

## 7. Still UNVERIFIED: ask Base on site

1. What exact rule does each of Oncor and CenterPoint apply?
   - nameplate kW vs kVA;
   - 100% or some other %;
   - existing solar counted?
   - charging kW counted?
2. Has Oncor ever credited a password-locked PCS export cap on a Base application? Has any TDSP credited an import cap?
3. What does the Oncor portal actually show: transformer kVA, remaining kW, pre-screen text?
4. Does Oncor treat battery charging as added load under tariff §5.7.6 and §6.1.2.2, earning any allowance?
5. Is Base registered as a power generation company, which would matter for proposed §25.58?
6. Does Austin Energy count the export-limited kW or the nameplate kW in its 90% test?
7. Did the PUCT take up the 54233 proposal for publication at a Sept 2026 open meeting? It is not in the filing list as of today.

Also unverified:
- CenterPoint's Houston residential DG manual: all old URLs return 404.
- UKPN's "£80m" figure (site 403).
- The SPAN claim that UL 3141 will be required under the 2026 NEC.
- Whether Oncor's numeric feeder IDs are unique.

---

## 8. Access log (26 Sep 2026, curl, no account)

The full log is in `evidence/interconnection/fetch-log.txt` (107+ lines). Summary: every URL cited in §2 returned **200**, except those listed below.

| URL | Status |
|---|---|
| centerpointenergy.com old DG documents (DER Application Tariff, 2023 DG Process Overview, SmallScale-DER, DG specs, DGAP FAQs) | **404** (site rebuilt) |
| ukpowernetworks.co.uk flexible-connections and help pages | **403** |
| energynetworks.org G100 PDF and flexibility news | **403** |
| dps.ny.gov event page and ITWG slides | **403** (documents.dps.ny.gov petition 200) |
| anl.gov UL 3141 publication page | **403** |
| ferc.gov/…/sgip.pdf (guessed) | **404** (the sm-gen-procedures.pdf copy is 200) |
| nationalgridus.com/Flex-Connect | 200, but redirects to a 404.aspx page |
| guessed *.powerclerk.com hosts (centerpointenergy, cnp, tnmp, aeptexas) | redirect to cleanpower.com, **403** |

The four Project 59167 ZIPs (37 MB) were deleted after their xlsx files were extracted to `dg_reports_2025/`. The summary and the script that reproduces it are `dg_reports_2025_summary.json` and `summarize_dg_reports.py`.
