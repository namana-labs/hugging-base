export const meta = {
  name: 'ems-data-story',
  description: 'Verify the operator data list, pull real ERCOT and simulated feeder data for each item, adversarially check, and design the console',
  phases: [
    { title: 'Gather', detail: 'one agent per data item: verify claims, pull real ERCOT data or re-solve the feeder, write compact JSON' },
    { title: 'Verify', detail: 'one adversarial reviewer per item: grid-ops correctness and data provenance' },
    { title: 'Repair', detail: 'fix major or critical problems' },
    { title: 'Synthesize', detail: 'design the operator console story from all verified items' },
  ],
}

// RZ rule: at most 5 subagents at once.
function limiter(n){let active=0;const q=[];const next=()=>{if(active>=n||!q.length)return;active++;const j=q.shift();j.fn().then(j.res,j.rej).finally(()=>{active--;next();});};return fn=>new Promise((res,rej)=>{q.push({fn,res,rej});next();});}
const lim = limiter(5)
const A = (prompt, opts) => lim(() => agent(prompt, opts))

const P = '/Users/rzalagbada/Desktop/projects/base-power-hackathon'
const V = '/private/tmp/claude-501/-Users-rzalagbada-Desktop-projects-REDACTED/db7213a8-6bab-44d3-b22b-9fe4a11f46ca/scratchpad/venv/bin/python'

const COMMON = `
CONTEXT
- Project: "Hugging Base", a Base Power x AITX hackathon project (Austin, due Sun 27 Sep 2026 11:00 CT). It simulates a fleet of Base home batteries on NREL's SMART-DS synthetic north-Austin feeder p1uhs19_1247--p1udt17263 (presented as an Oncor-suburb stand-in at LZ_NORTH, placeholder), with OpenDSS as the referee. Base's product lead (RZ) sent a list of grid-operator (EMS) data that users should be able to SEE on the project's visual walkthrough page. He said: "don't treat this as gospel, but a good starting point". Your job covers ONE item of that list.
- Now is about 23:00 CDT Fri 25 Sep 2026 (04:00 UTC Sat 26 Sep).
- Research to reuse (read what you need, don't re-research what's there): ${P}/hugging-base/docs/research-report.md ; research notes in ${P}/research_notes/Base Power system and ERCOT data/ (ercot_public_data_apis.md lists tested keyless ERCOT endpoints: dashboards at https://www.ercot.com/api/1/services/read/dashboards/<name>.json, MIS listing https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId=<id>, download https://www.ercot.com/misdownload/servlets/mirDownload?doclookupId=<id>); grid_physics_orchestration_and_attacks.md has physics numbers (critical inertia ~100 GW·s, 2,750 MW design trip, UFLS 59.3/58.9/58.5 Hz, PRC thresholds 3,000/2,500/2,000/1,500 MW).
- Cached real ERCOT data from 25 Sep 2026 evening: ${P}/evidence/scratchpad-20260925/ercot/ (db_*.json; some are empty files — re-fetch those live) and ${P}/evidence/scratchpad-20260925/bp-data-ingest/ (daily-prc.json, dc-tie-flows.json, supply-demand.json, system-wide-prices.json, energy-storage-resources.json, fme/ frequency events workbook, rtm2026_lz.csv prices).
- Team prototype (real OpenDSS solves, scripted inputs): code ${P}/hugging-base/demos/grid-stories/sim/ (feeder.py: Feeder() -> .homes list of dicts with id, tf (transformer index), distance (electrical path length km), coordinates; .transformers (id, kva, primary, secondary); .load(factor) scales all home loads; .battery({home_id: kW}) sets battery loads, POSITIVE kW = CHARGING; .solve(detail=True) -> dict with voltage (per home min pu), loading (per transformer %), feederMW etc.). Replay outputs ${P}/hugging-base/demos/grid-stories/ui/dist/replays.json: scenarios heatwave/rebound/covert, keys naive/aware(/_quarantine), 13 steps each with loadFactor, powers {home_id: kW}, minute, loading, voltage. To reproduce a replay state: f=Feeder(); f.load(step['loadFactor']); f.battery(step['powers']); f.solve(). Import with sys.path.insert(0, '${P}/hugging-base/demos/grid-stories') then from sim.feeder import Feeder. Python with OpenDSSDirect.py 0.9.4 + numpy: ${V} (add packages with ${V} -m pip install <pkg> if needed, e.g. openpyxl). After Feeder() you can use opendssdirect's dss module directly (from opendssdirect import dss) for lines (dss.Lines, dss.CktElement.CurrentsMagAng, NormalAmps, Powers), capacitors, buses (dss.Circuit.AllBusMagPu, AllBusNames, dss.Bus.Distance), etc.
- Heavy local runs (anything over ~20 s of CPU): prefix the command with  lockf -k /private/tmp/claude-501/heavy-local.lock nice -n 10  (a shared machine lock).

RULES
- NOT GOSPEL: first judge each claim in your item (holds / holds_with_caveat / wrong / unverifiable) with sources. Correct anything wrong. ERCOT-specific facts need an ERCOT, NERC or equally primary source; say UNVERIFIED otherwise.
- Every number you produce carries a status: REAL (public data; give endpoint + retrieval time), SIM (prototype OpenDSS on SMART-DS with scripted inputs), DERIVED (our arithmetic on REAL/SIM; give formula), ASSUMPTION. Never fabricate or interpolate data; if something isn't available say so.
- ERCOT politeness: at most 1 request per second, send a normal User-Agent, never loop-poll. Save every raw live fetch under ${P}/evidence/live-20260925/ (create it; name files <item>-<feed>.json) so provenance survives.
- Write ONLY into ${P}/site/ems/ (create it) using filenames that start with your item id (e.g. ${'${ITEM}'}-*.json, ${'${ITEM}'}-spec.md) and into ${P}/evidence/live-20260925/. Do not edit anything in hugging-base/, site/*.html, or other items' files.
- Output data for a browser chart: compact JSON (target < 150 KB per item; downsample long series and say how), documented shape at the top of your spec file.
- Never print or store credentials. No API keys are needed for anything here.
`

const ITEMS = [
 { id:'freq', name:'Frequency and its trend', text:`"Frequency and its trend. Not just the number but its rate of change (RoCoF), the time error, and the reserve that can arrest a fall. In ERCOT the operational proxy for that reserve is Physical Responsive Capability, and system inertia in MW seconds tells you how fast frequency will move when a unit trips. Frequency alone is a lagging indicator; inertia plus RoCoF is the leading one."`,
   tasks:`- Fetch live https://www.ercot.com/api/1/services/read/dashboards/dc-tie-flows.json (10-s frequency + system inertia since midnight 25 Sep) and daily-prc.json (PRC ~10 s). Also check ancillary-services.json / system-frequency feeds if useful.
- Compute: frequency stats for the day (mean, sigma, min/max with times); RoCoF from the 10-s series (and explain why 10-s differences understate true sub-second RoCoF); cumulative time error in seconds = integral of (f-60)/60 dt, and check whether ERCOT/NERC still perform time error correction (BAL-004 status) so we don't overclaim; inertia trend for the day (min/max, GW·s) vs ERCOT's ~100 GW·s critical inertia; the theoretical initial RoCoF for a 2,750 MW trip at the day's min and max inertia (RoCoF = dP * f0 / (2 * Ek), state the formula and units carefully); PRC trend vs Watch/EEA thresholds.
- Output ${'freq'}-series.json: 1-minute (or finer where it matters) aligned series of frequency, PRC, inertia, time error; plus the full-resolution window around the day's largest frequency excursion; plus the stats. Visual spec: how to show "leading vs lagging" (e.g. inertia band + expected RoCoF under the frequency trace).`},
 { id:'volt', name:'Voltage everywhere and reactive power', text:`"Voltage, everywhere. Voltage magnitude per bus against its limits, and reactive power (MVAr) flows and reserves, because voltage is a local phenomenon that voltage support (capacitors, reactors, generator excitation, synchronous condensers) holds up region by region. A grid can be at perfect 60 Hz and collapsing in voltage in one corner. This is the value people forget when they start from frequency and MW."`,
   tasks:`- Feeder level with OpenDSS: reproduce the prototype replay states rebound step 0 (19:30) and step 3 (19:45) for naive and aware, and heatwave step 12. For each: voltage at EVERY bus (not just homes; include primary buses) vs 0.95–1.05 pu, a voltage PROFILE (pu vs electrical distance from the substation, downsampled sensibly, with min/max per distance bin), count of buses/homes outside limits, feeder-head P (kW) and Q (kvar), capacitor banks in the SMART-DS files (location, kvar, on/off), per-transformer kvar summary.
- Optional cheap what-if if it can be done honestly: how much the worst voltage would improve if the Cores supplied reactive power (IEEE 1547-2018 default volt-var; state the curve you used).
- ERCOT level: say what voltage/reactive data ERCOT publishes publicly (likely none in real time) — don't invent.
- Output ${'volt'}-profile.json + spec. Visual spec: the classic voltage-profile-along-the-feeder chart (naive vs aware), plus a per-home voltage map layer note (the page already has per-home voltages).`},
 { id:'flow', name:'Real power flows against limits (incl. DC ties)', text:`"Real power flows against limits. MW on every line and transformer against its thermal rating, and the interchange on ties (in ERCOT, the five DC ties). The core question is whether any single element is overloaded now, and the harder one below."`,
   tasks:`- Feeder level with OpenDSS: for rebound step 3 (19:45) naive vs aware and heatwave step 12: loading of EVERY line segment vs its NormalAmps (ampacity), every transformer vs kVA (already in replays), the feeder head vs its rating (head line normamps x sqrt3 x 12.47 kV). Top 15 most-loaded elements per case, and a histogram of loading % by element type.
- ERCOT level: DC tie flows from live dc-tie-flows.json (fields dcE, dcN, dcL, dcR, dcS or similar) for 25 Sep; verify the claim "five DC ties": name each tie, its location/neighbour and nominal rating from ERCOT/primary sources; note which appear in the dashboard feed.
- Output ${'flow'}-limits.json + spec. Visual spec: "every element vs its limit" (e.g. sorted loading bars / strip plot) and a DC-tie flow chart with signs explained (import vs export).`},
 { id:'n1', name:'Contingency margin (N-1)', text:`"Contingency margin. The defining EMS function is not the current state, it is N-1: for every credible single failure, would anything overload or any voltage collapse. The real time contingency analysis runs continuously and its output, the list of binding and near binding constraints with their shadow prices, is what actually drives operator action and, in ERCOT, drives the congestion component of price."`,
   tasks:`- Verify the ERCOT mechanics: how RTCA results feed SCED constraints, shadow prices and the congestion component of LMP (ERCOT protocol/training sources).
- REAL: find and download ERCOT's public SCED binding-constraint / shadow-price report (NP6-86-CD "SCED Shadow Prices and Binding Transmission Constraints"; find its reportTypeId via the MIS listing or data-product page) for 25 Sep 2026 (keyless MIS). Summarize: number of binding constraints by interval, top constraints by max/avg shadow price, and any constraint whose name suggests the Austin area (e.g. contains AUSTIN, LCRA, AEN, or known Austin substation names; don't overclaim location). If 22 Jul 2026 is still in retention, include its evening too.
- SIM, feeder level: a bounded N-1 on the radial SMART-DS feeder at rebound step 3 (aware case): open each of the ~30 most important primary segments and each of the 10 most loaded transformers one at a time; for each, count homes de-energized, how many of those have a Base battery (they island and keep power), and the worst remaining voltage / loading. Radial feeders have little N-1 redundancy — say that plainly; the insight is who loses power and who rides through on a battery.
- Output ${'n1'}-contingency.json + spec. Visual spec: a ranked contingency list (the operator's to-do list) and a shadow-price chart.`},
 { id:'res', name:'Reserves and their deployability', text:`"Reserves and their deployability. Regulation up and down, responsive reserve, non spin, and ECRS, both procured and physically available. Reserve that exists on paper but sits behind a transmission constraint is not reserve."`,
   tasks:`- REAL: live ERCOT ancillary service capacity monitor (dashboard names like ancillaryServiceCapacityMonitor.json or ancillary-services.json; see research notes) for 25 Sep: procured vs available/deployed by product (RegUp, RegDown, RRS incl. FFR, ECRS, Non-Spin), and the share from storage if the feed has it. Note post-RTC+B (Dec 2025) naming.
- SIM/DERIVED: the fleet's deliverable reserve on this feeder. From replays (heatwave and rebound, naive/aware): nameplate discharge (96 Cores x 20 kW), what the aware controller could actually deliver without violations, and energy duration: with 37 kWh usable (ASSUMPTION) and the 20% floor, how many kW the fleet can back for ECRS (1 h) and Non-Spin (4 h) at the SoC seen in the replays. This is the "reserve behind a constraint is not reserve" point at feeder scale — make it concrete.
- Output ${'res'}-reserves.json + spec. Visual spec: procured vs deployable bars for ERCOT, and a nameplate -> feeder-deliverable -> energy-backed waterfall for the fleet.`},
 { id:'load', name:'Load and net load, actual and forecast, and the ramp', text:`"Load and net load, actual and forecast. And critically the ramp: the rate the net load is about to change as solar sets, which is what strands an operator who was balanced a minute ago."`,
   tasks:`- REAL: live ERCOT supply-demand / system-wide-demand / solar and wind production (actual + forecast) / fuel-mix feeds for 25 Sep 2026. Compute net load = demand - wind - solar (state exactly which series you used), its 5-min ramp (MW/min) and hourly ramp, the evening ramp as solar sets (max rate, time), and forecast error where a forecast exists.
- Context numbers from research (cite): record 91,134 MW peak and ~75,733 MW net load peak around 20:00 on 22 Jul 2026; Base's Houston partition ramp 12.1 -> 46.7 MW in 15 min.
- Tie to the fleet: when on 25 Sep would batteries be discharging to help the ramp.
- Output ${'load'}-netload.json + spec. Visual spec: load, solar, wind, net load (actual vs forecast) with a ramp-rate strip underneath.`},
 { id:'dq', name:'Data quality as a first-class value', text:`"Data quality itself. An EMS treats the freshness and validity of every telemetered point as a first class value, because a stale or bad measurement feeding the state estimator produces confident wrong answers. This is exactly the mw:Provenance and quality discipline and it is not decoration here, it is a stability input."`,
   tasks:`- REAL: for each ERCOT dashboard feed the page uses (dc-tie-flows, daily-prc, supply-demand, fuel-mix, system-wide-prices, ancillary services), measure: lastUpdated vs fetch time (age), HTTP cache max-age, sample cadence, gaps in the day's series, runs of identical repeated values (possible stale), timezone/DST fields. Use the cached files plus at most one fresh fetch each.
- SIM: the fleet's telemetry quality model from the prototype and PRD (180 s stale rule, COMMS_LOST, meter vs claimed power residual as a state-estimator analogue; the covert detector residuals in replays.json 'detector' per step).
- Verify the modelling vocabulary: IEC 61970 CIM MeasurementValueQuality (validity GOOD/QUESTIONABLE/INVALID and related flags) and MeasurementValueSource; the "mw:Provenance" term appears to be the team's own namespace from the GridSpine Atlas design (headroom-gridspine-dossier.html in ${P}/hugging-base/) — check what it says and use it consistently; don't invent a standard.
- Output ${'dq'}-quality.json + spec. Visual spec: a data-quality ribbon (per feed: source, age, cadence, validity, status label) that every panel on the page can carry, and what should happen visually when a feed goes stale.`},
]

const GATHER = {type:'object',properties:{
  item_id:{type:'string'},
  claim_verdicts:{type:'array',items:{type:'object',properties:{claim:{type:'string'},verdict:{type:'string',enum:['holds','holds_with_caveat','wrong','unverifiable']},correction:{type:'string'},sources:{type:'array',items:{type:'string'}}},required:['claim','verdict','sources']}},
  files_written:{type:'array',items:{type:'string'}},
  headline_numbers:{type:'array',items:{type:'object',properties:{label:{type:'string'},value:{type:'string'},unit:{type:'string'},status:{type:'string',enum:['REAL','SIM','DERIVED','ASSUMPTION']},source:{type:'string'}},required:['label','value','status','source']}},
  visual_spec:{type:'object',properties:{panel_title:{type:'string'},chart_type:{type:'string'},encodings:{type:'string'},interactions:{type:'string'},story_role:{type:'string'},data_file:{type:'string'},json_shape:{type:'string'}},required:['panel_title','chart_type','encodings','story_role','data_file','json_shape']},
  base_relevance:{type:'string'},
  caveats:{type:'array',items:{type:'string'}},
  not_available:{type:'array',items:{type:'string'}}
},required:['item_id','claim_verdicts','files_written','headline_numbers','visual_spec','base_relevance','caveats']}

const VERDICT = {type:'object',properties:{
  refuted:{type:'boolean'},
  problems:{type:'array',items:{type:'object',properties:{what:{type:'string'},severity:{type:'string',enum:['critical','major','minor']},fix:{type:'string'}},required:['what','severity','fix']}},
  rechecked:{type:'array',items:{type:'string'}}
},required:['refuted','problems','rechecked']}

const gatherPrompt = it => `${COMMON.replaceAll('${ITEM}', it.id)}
YOUR ITEM (id: ${it.id}) — ${it.name}
RZ's text: ${it.text}

TASKS
${it.tasks}

Also write ${P}/site/ems/${it.id}-spec.md: claim verdicts with sources, what data exists (REAL) vs what we simulate (SIM), the JSON shape, the visual spec, caveats, and how it tells part of "the full story of everything happening" for Base (who at Base cares and why). Return the structured result.`

const lenses = [
 {k:'ops', t:'GRID-OPERATIONS CORRECTNESS. You are a senior ERCOT/EMS engineer. Try to REFUTE the item: wrong physics or formulas (RoCoF, time error, ampacity, N-1, reserves), wrong units, wrong ERCOT-specific facts (tie names/ratings, PRC thresholds, AS products after RTC+B, RTCA/SCED mechanics), overclaims, misleading visual framing. Read the spec and the JSON.'},
 {k:'data', t:'DATA PROVENANCE AND REPRODUCIBILITY. Try to REFUTE the item: open the JSON it wrote and the raw evidence it cites (files under evidence/live-20260925 or the cached evidence), independently recompute at least 3 headline numbers (re-run OpenDSS with the venv python for SIM numbers if needed, within the heavy-run lock), check every number carries the right status (REAL vs SIM vs DERIVED vs ASSUMPTION), check nothing is fabricated or interpolated, check sizes are compact and the documented JSON shape matches the file.'},
]
const verifyPrompt = (it, g, lens) => `${COMMON.replaceAll('${ITEM}', it.id)}
You are an adversarial reviewer. Default to refuted=true if a headline number or claim verdict cannot be reproduced or sourced. Only report real problems; do not edit any files.
LENS: ${lens.t}
ITEM ${it.id} — ${it.name}. RZ's text: ${it.text}
The gatherer's result:
${JSON.stringify(g).slice(0, 12000)}
Files are in ${P}/site/ems/ (${it.id}-*). Return refuted, problems (severity critical/major/minor with a concrete fix) and what you rechecked.`

const results = await pipeline(ITEMS,
  it => A(gatherPrompt(it), {label:`gather:${it.id}`, phase:'Gather', schema:GATHER}),
  async (g, it) => {
    if (!g) return {item: it.id, gather: null, status: 'gather_failed'}
    const v = await A(`${COMMON.replaceAll('${ITEM}', it.id)}
You are an adversarial reviewer with two lenses at once. Default to refuted=true if a headline number or claim verdict cannot be reproduced or sourced. Only report real problems; do not edit any files.
LENS 1 — ${lenses[0].t}
LENS 2 — ${lenses[1].t}
ITEM ${it.id} — ${it.name}. RZ's text: ${it.text}
The gatherer's result:
${JSON.stringify(g).slice(0, 12000)}
Files are in ${P}/site/ems/ (${it.id}-*). Recompute at least 3 headline numbers. Return refuted, problems (severity critical/major/minor with a concrete fix) and what you rechecked.`, {label:`verify:${it.id}`, phase:'Verify', schema:VERDICT})
    const serious = v ? (v.problems||[]).filter(p => p.severity !== 'minor') : []
    if (!v) return {item: it.id, gather: g, verdicts: [], status: 'verify_failed'}
    if (!serious.length) return {item: it.id, gather: g, verdicts: [v], status: 'verified'}
    log(`${it.id}: ${serious.length} major/critical problems, repairing`)
    const g2 = await A(`${COMMON.replaceAll('${ITEM}', it.id)}
You are repairing item ${it.id} (${it.name}) after adversarial review. RZ's text: ${it.text}
Original result: ${JSON.stringify(g).slice(0, 10000)}
Problems to fix (fix every critical/major one in the files under ${P}/site/ems/${it.id}-*, re-running computations as needed; if a problem is itself wrong, say why in the spec file under "Review responses"):
${JSON.stringify(serious).slice(0, 8000)}
Return the full updated structured result.`, {label:`repair:${it.id}`, phase:'Repair', schema:GATHER})
    return {item: it.id, gather: g2 || g, verdicts: [v], status: g2 ? 'repaired' : 'needs_review', fixed: serious}
  }
)

phase('Synthesize')
const ok = results.filter(Boolean)
const synth = await A(`${COMMON.replaceAll('${ITEM}', 'synth')}
You are the lead designer. Seven items from RZ's operator-data list were researched, computed and adversarially verified. Their results (status, claim verdicts, headline numbers, visual specs, caveats, open problems):
${JSON.stringify(ok).slice(0, 60000)}
Also read the spec files ${P}/site/ems/*-spec.md and glance at the JSON files.
Design ONE new section for the existing walkthrough page (${P}/site/hugging-base-atlas.src.html — read its structure: sheets 00-11, dark "screen" mockups, page-themed charts, status labels REAL/SIM) that lets a user "visually see the full story of everything happening": an operator's console that runs from system level (ERCOT frequency, inertia, PRC, net load ramp, reserves, congestion) down to the feeder (flows vs limits, voltage profile, N-1) and the device/data level (telemetry quality), and shows how they connect to Base's fleet. Write ${P}/site/ems/SYNTHESIS.md with: the story order and why; each panel (title, data file, exact fields, chart form, annotations with the real numbers, status label, caveat line, interactions); a single time-alignment approach (ERCOT real day 25 Sep 2026 vs the feeder replay hour — be explicit that they are different time bases); which claims in RZ's list were corrected and how to say so on the page; and anything an ERCOT operator would expect that is still missing. Items with status needs_review must be shown with their open problems or left out — decide and say which. Return a concise summary (under 400 words) of the design and the list of panels in order.`, {label:'synthesize', phase:'Synthesize'})

return { items: ok.map(r => ({item: r.item, status: r.status, open_problems: r.open_problems || [], files: r.gather && r.gather.files_written, headline: r.gather && r.gather.headline_numbers, verdicts: r.gather && r.gather.claim_verdicts.map(v => ({claim: v.claim.slice(0,120), verdict: v.verdict, correction: (v.correction||'').slice(0,200)}))})), synthesis: synth }
