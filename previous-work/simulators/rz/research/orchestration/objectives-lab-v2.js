export const meta = {
  name: 'objectives-lab-research',
  description: 'Research real data for profit vs reliability vs transformer capacity and upgrade decisions, design the capacity planner, adversarially critique it, write the spec',
  phases: [
    { title: 'Research', detail: 'grid-asset data scout and market/profit data scout (cached)' },
    { title: 'Research 2', detail: 'interconnection rules scout and asset-age/demand/repo scout' },
    { title: 'Design', detail: 'transformer capacity planner design' },
    { title: 'Critique', detail: 'Base-engineer lens and physics/data-honesty lens' },
    { title: 'Synthesize', detail: 'DATA_AND_OBJECTIVES_LAB.md' },
  ],
}
function limiter(n){let active=0;const q=[];const next=()=>{if(active>=n||!q.length)return;active++;const j=q.shift();j.fn().then(j.res,j.rej).finally(()=>{active--;next();});};return fn=>new Promise((res,rej)=>{q.push({fn,res,rej});next();});}
const lim = limiter(3)   // round 2 runs 3 lanes; RZ cap is under 10 agents at once
const A = (p, o) => lim(() => agent(p, o))
const H = '/Users/rzalagbada/Desktop/projects/base-power-hackathon'
const OVN = H + '/overnight'
const CTX = `
CONTEXT: "Hugging Base", Base Power x AITX hackathon (submission Sun 27 Sep 2026 11:00 CT). We simulate Base home batteries on NREL's SMART-DS synthetic north-Austin feeder (1,010 homes, 379 service transformers, OpenDSS referee) with real ERCOT LZ_NORTH prices; the root app on main (~/hb-overnight/hb) has P1 (where to charge: naive vs feeder-aware, 3D) and P2 (where the next battery goes: month what-if). Research already done: ${H}/reports/Base Power system and ERCOT data.md and ${H}/research_notes/ (read what you need; don't redo it).
NEW DIRECTION (via RZ). A Base engineer said (paraphrased): three kinds of scenario would interest Base: running the fleet for the most market revenue, keeping every transformer inside its limits, and working out which transformers should be replaced or upsized and what that is worth to the utility. RZ's idea: rather than fixed scenarios, a general what-if lab where you choose the metrics (profit, reliability, asset life). His hard requirement: the data must be correct and actionable, not a toy.
Rules: cite a URL for every claim; actually test access (curl, no accounts, no credentials) where you can and record HTTP status and size; mark anything unverified UNVERIFIED; label REAL / SIM / DERIVED / ASSUMPTION. Write only under ${OVN}/. Do not edit the repo.`

phase('Research')
const [grid, market] = await Promise.all([
 A(`${CTX}
You are the GRID-ASSET DATA SCOUT. Find what real data we can get NOW (no accounts, or free and instant) to make reliability and transformer-replacement scenarios correct:
- Utility hosting-capacity or feeder-loading maps/APIs with feeder or transformer detail: Oncor, CenterPoint, AEP Texas, Austin Energy, Pedernales (PEC). Out-of-Texas references: PG&E ICA, SCE DRPEP, ComEd, Xcel, National Grid, Dominion. Say what fields they expose (feeder peak MW, thermal limit, transformer kVA, loading %, age?).
- Service-transformer loading or age data (any open AMI-derived datasets, utility filings, PUCT or ERCOT reports, DOE/EIA).
- Transformer thermal aging and loss-of-life models (IEEE C57.91 / IEC 60076-7 parameters, hot-spot equations) and whether SMART-DS gives what they need.
- Transformer failure rates and replacement or upsizing costs ($ per 25→50 kVA swap, labour, truck roll) from utility rate cases, NREL/LBNL/EPRI reports.
- Non-wires-alternative / deferral values utilities pay (LBNL, NY REV, ConEd BQDM) for the "take it to the utility" ROI.
- Outage and reliability data: EIA-861 SAIDI/SAIFI by utility, DOE EAGLE-I.
Write ${OVN}/DATA-GRID-ASSETS.md with a table: Source | What it gives | Access (URL, tested status) | Granularity | License | Usable by Sunday? | How it plugs into our sim. Return a 250-word summary: what is real and usable now, and what must stay ASSUMPTION.`, {label:'scout:grid', phase:'Research'}),
 A(`${CTX}
You are the MARKET AND PROFIT DATA SCOUT. Make a profit-max scenario defensible:
- ERCOT data on disk (${H}/evidence/, data/ercot/ in the repo) and fetchable now: RT and DA settlement point prices, post-RTC+B ancillary service prices (NP6-331-CD etc.), 4CP intervals, ADER pilot rules and caps (what Base can actually sell from home batteries, which services).
- Battery economics: round-trip efficiency, cycle-life and degradation cost per MWh throughput (LFP), warranty cycle limits, Base's 20% reserve rule, member backup value.
- The right optimisation for a hackathon: perfect-foresight LP as an upper bound vs a rule-based or MPC policy with a price forecast; what is honest to claim.
- How much of Base's revenue is realistically energy arbitrage vs ancillary vs utility programmes (cite).
Test one or two keyless ERCOT endpoints. Write ${OVN}/DATA-MARKET-PROFIT.md with the same table format plus a short "honest profit claim" section. Return a 250-word summary.`, {label:'scout:market', phase:'Research'}),
])

const CTX2 = `
UPDATE (RZ, 26 Sep ~16:25Z): a SECOND Base engineer conversation changes the focus. [The conversation itself is in [local-only engineer notes, not published].] A Base engineer said (paraphrased): a utility transformer limit can block a planned group of installs late in the sales process; the useful tool answers how many batteries a given transformer can take, and when paying for an upgrade is worth it given how many more members are likely to want a battery there. Utility asset data (age, last replacement) is hard to get, so simulate realistic transformer ages now and plug real utility and ERCOT data in later.
Already researched (read, don't redo): ${OVN}/DATA-GRID-ASSETS.md and ${OVN}/DATA-MARKET-PROFIT.md (and ${OVN}/evidence/grid-assets/, ${OVN}/evidence/market-profit/).`

phase('Research 2')
const [inter, assets] = await Promise.all([
 A(`${CTX}${CTX2}
You are the INTERCONNECTION RULES SCOUT. Find, with citations and tested URLs:
- How Texas TDSPs (Oncor, CenterPoint, AEP Texas, TNMP) review a RESIDENTIAL BATTERY against service-transformer capacity: PUCT Substantive Rules 25.211 / 25.212, each TDSP's DG interconnection manual or tariff. Do they count battery nameplate kW, export only, or charging (import) too? Is there a screen like "aggregate DG on a secondary transformer must not exceed X% of its kVA"? Typical timelines.
- Whether they accept certified control to cap what a site can import or export: UL 1741 CRD Power Control Systems / UL 3141, NEC 705.13, IEEE 1547-2018 limited export, "non-export" or "managed charging" configurations. Evidence of acceptance in Texas or not. If feeder-aware dispatch (our P1 orchestrator) could be made binding this way, more batteries would fit per transformer: find what is real here.
- Who pays for a service-transformer upgrade triggered by DG or storage in Texas (tariff sections, typical charges), and how long it takes.
- Flexible or managed interconnection precedents elsewhere: CA Rule 21 limited generation profiles, Hawaii, New York, National Grid, UK flexible connections; results.
- What Base itself says publicly about utility approval, interconnection or transformer upgrades (blog, FAQ, filings), and what Oncor's or CenterPoint's installer portal exposes.
Write ${OVN}/DATA-INTERCONNECTION.md: a source table (Source | What it says | URL + tested status | Applies to Texas? | How it plugs into the capacity planner) plus a short "what is real vs assumption" list. Return a 250-word summary.`, {label:'scout:interconnect', phase:'Research 2'}),
 A(`${CTX}${CTX2}
You are the ASSET-AGE, DEMAND AND REPO SCOUT. Cite everything; label REAL / SIM / DERIVED / ASSUMPTION.
1. Transformer age: hazard or failure models for distribution transformers by age (Weibull parameters from the literature or utility filings), typical replacement ages, the age distribution of US or Texas distribution transformers, Oncor or CenterPoint resiliency-plan data on replacements by age, and how IEEE C57.91 normal insulation life relates to calendar age. Output: a defensible way to SIMULATE ages for our 379 transformers and turn age into a probability of needing replacement within N years.
2. Demand: the probability of more members in a neighbourhood. Solar and battery peer effects (e.g. Bollinger & Gillingham 2012), neighbourhood adoption rates, Bass-diffusion parameters for home storage, anything public on Base member density. Output: a defensible demand distribution to simulate (e.g. "N more likely in 2 years, with this spread").
3. Decision method: expected NPV vs minimax regret vs real options for "upgrade now / wait / cap with controls"; what utility probabilistic planning uses. Give the formulas we would implement.
4. The root app (~/hb-overnight/hb, READ ONLY; also fetch origin and look at origin/main and the overnight/* branches): what does the P2 harness (sim/siting.py and friends) already compute? Can it compute "the most batteries transformer T can take" under naive vs feeder-aware dispatch, refereed by OpenDSS? What would it take (functions, run time)? Where are transformer kVA ratings and home-to-transformer links in the data? Does the sim use the IEC ageing formula the grid scout flagged (file:line)? What does the LP-with-transformer-rows idea from DATA-MARKET-PROFIT.md need?
Write ${OVN}/DATA-ASSETS-DEMAND.md and return a 250-word summary.`, {label:'scout:assets-demand', phase:'Research 2'}),
])

phase('Design')
const design = await A(`${CTX}${CTX2}
You are the DESIGNER. Inputs: [local-only engineer notes, not published], ${OVN}/DATA-GRID-ASSETS.md, ${OVN}/DATA-MARKET-PROFIT.md, ${OVN}/DATA-INTERCONNECTION.md, ${OVN}/DATA-ASSETS-DEMAND.md, the root app (read only), and the UI design language in ~/hb-overnight/hb/docs/design-handoff/ plus ${OVN}/UX_SPEC_R2.md.
Design the TRANSFORMER CAPACITY PLANNER. It must unify all three asks: profit-max vs reliability-first (one dial), how many batteries a transformer can take (naive vs feeder-aware, OpenDSS-refereed), and "upgrade or not" (age, demand probability, cost, shadow price, regret), inside an environment where real data plugs in later.
1. Critique RZ's pluggable-metrics idea first. Keep what is right; say what to fix (e.g. "pluggable DATA, fixed QUESTIONS").
2. The data contract: an asset file schema (per transformer: kVA, phase, install year, last replaced, homes served, members, pending installs) that a person could fill from utility (Oncor or CenterPoint) data; its default is our SIM feeder plus simulated ages (the age method from DATA-ASSETS-DEMAND.md). The price feeds are ERCOT (REAL).
3. The computations, each with inputs, formula, source, status label and run time: hosting capacity for batteries per transformer (naive vs feeder-aware); the upgrade decision (expected NPV and minimax regret over the demand distribution; value per Core-year from DATA-MARKET-PROFIT.md; upgrade cost; age-driven replacement probability; the "upsize at planned replacement" increment); and the profit-vs-reliability dial with the transformer shadow price.
4. The UI: how it sits in the root app (P2 tab or its own), one 60-second demo beat judges understand, hover and honesty rules, and RZ's round-2 visual asks (icons over numbers, battery icons, slow playback).
5. A build plan by lane (l2 sim, l3 P2 harness, l4 P1 UI, l5 P2 UI/story, l0 shared) with acceptance checks and a cut order, sized for Sunday 11:00 CT. The build happens on RZ's other account after the round-2 merge.
Write ${OVN}/DESIGN-CAPACITY-PLANNER.md and return a 300-word summary.`, {label:'designer', phase:'Design'})

phase('Critique')
const LENSES = [
 {key:'base', prompt:`You are a BASE POWER field-operations and product engineer. Try to REFUTE the design in ${OVN}/DESIGN-CAPACITY-PLANNER.md. Does it solve installs blocked late by a transformer limit? Would Base use it tomorrow with the utility capacity data it can actually get? Is the demo beat clear in 60 seconds to Base engineers judging completeness, depth, problem, why, insight, usability, creativity and performance? What is missing, overbuilt or naive about how Base actually sells, installs and gets utility approval?`},
 {key:'physics', prompt:`You are a distribution power engineer and data-honesty auditor. Try to REFUTE the design in ${OVN}/DESIGN-CAPACITY-PLANNER.md. Check every number against its cited source and status label; the capacity method (battery charging counted as load, diversity, thermal vs the team's 110%-for-30-min rule, whether feeder-aware control can be treated as binding by a utility, OpenDSS as referee); the decision maths (units, discounting, expected value vs regret); the ageing model (IEEE C57.91, not IEC). Would a Base or Oncor grid engineer find an error within five minutes?`},
]
const crits = await parallel(LENSES.map(l => () => A(`${CTX}${CTX2}
${l.prompt}
Read the inputs the designer used (${OVN}/DATA-*.md, [local-only engineer notes, not published]) and the root app read-only. Write ${OVN}/CRITIQUE-CAP-${l.key}.md: a verdict (sound / sound-with-fixes / unsound), a numbered MUST-FIX list (each with evidence), SHOULD-FIX, and what the design gets right. Return the verdict and the must-fix list in under 300 words.`, {label:`critic:${l.key}`, phase:'Critique'})))

phase('Synthesize')
const synth = await A(`${CTX}${CTX2}
Write ${OVN}/DATA_AND_OBJECTIVES_LAB.md for RZ and for the next agent (on RZ's other account) who will build it. Plain language (RZ is a computer engineer, not a power engineer), scannable, short sentences, tables where they help:
1. FIRST, answer RZ's question "what should we focus on for the best benefit": rank the options (profit-max scenario, reliability-first scenario, transformer replacement ROI, the capacity planner, RZ's metrics lab) by value to Base, fit to the judging criteria and tracks, data honesty and buildability by Sunday 11:00 CT. Give one recommendation.
2. What data we can get right now to make it correct (verified table), and what must stay labelled ASSUMPTION or SIM, including how hard utility asset data is to get and the "plug real utility data in later" path.
3. The critique of the metrics-lab idea and the recommended framing.
4. The final capacity-planner design with EVERY must-fix from both critics applied (list each must-fix and how it was resolved).
5. The build plan by lane with acceptance checks and a cut order.
6. The 60-second demo beat.
7. Questions to ask Base engineers on site tomorrow morning.
Inputs: ${OVN}/DESIGN-CAPACITY-PLANNER.md, ${OVN}/CRITIQUE-CAP-base.md, ${OVN}/CRITIQUE-CAP-physics.md, ${OVN}/DATA-*.md, [local-only engineer notes, not published]. Summaries: ${String(design||'').slice(0,3000)} ${crits.filter(Boolean).map(c=>String(c).slice(0,2500)).join(' || ')}. Return a 300-word summary that leads with the recommendation.`, {label:'synthesize', phase:'Synthesize'})
return { summary: synth }
