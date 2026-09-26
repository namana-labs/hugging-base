export const meta = {
  name: 'objectives-lab-research',
  description: 'Research real data for profit vs reliability vs transformer-replacement scenarios, critique the metrics-lab idea, write a buildable spec',
  phases: [
    { title: 'Research', detail: 'grid-asset data scout and market/profit data scout' },
    { title: 'Critique', detail: 'critique the metrics-lab idea and design the trustworthy version' },
    { title: 'Synthesize', detail: 'DATA_AND_OBJECTIVES_LAB.md' },
  ],
}
function limiter(n){let active=0;const q=[];const next=()=>{if(active>=n||!q.length)return;active++;const j=q.shift();j.fn().then(j.res,j.rej).finally(()=>{active--;next();});};return fn=>new Promise((res,rej)=>{q.push({fn,res,rej});next();});}
const lim = limiter(2)   // round 2 build runs 3 lanes; RZ's cap is 5 agents at once
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

phase('Critique')
const crit = await A(`${CTX}
You are the CRITIC and lab designer. Read ${OVN}/DATA-GRID-ASSETS.md and ${OVN}/DATA-MARKET-PROFIT.md, and look at the root app (~/hb-overnight/hb: sim/orchestrator.py, sim/siting.py, sim/money.py, ui/panels/p1.js and p2.js, docs/contracts.md) read-only.
1. Critique RZ's pluggable-metrics lab against fixed scenarios. Consider: garbage in / garbage out, too many knobs for a 5-minute video, judge comprehension, what Base could actually use tomorrow, honesty. Give a verdict and the version that stays trustworthy (e.g. a few named objectives plus weight sliders over a verified cost model; a Pareto frontier of profit vs reliability vs transformer life; presets "profit max", "reliability first", "balanced").
2. Specify the objective model concretely: the terms (energy revenue at real prices, AS revenue if allowed, degradation cost, tier-hour and emergency penalties, transformer loss-of-life via the IEC/IEEE aging factor, replacement ROI with sourced cost and deferral value), with each input's source and status label.
3. Specify the transformer-replacement view: rank transformers by loss-of-life and violation hours under each objective, and a one-page utility ROI summary (upgrade cost vs deferral value vs battery alternative).
4. Say what can be built by Sunday 11:00 CT on top of the root app, by lane (l2 sim, l3 P2, l4 P1 UI, l5 P2 UI/story, l0 shared), with acceptance checks.
Write ${OVN}/CRITIQUE-OBJECTIVES-LAB.md. Return a 300-word summary.`, {label:'critic', phase:'Critique'})

phase('Synthesize')
const synth = await A(`${CTX}
Write ${OVN}/DATA_AND_OBJECTIVES_LAB.md for RZ and for the next agent (on RZ's other account) who will build it. Plain language, scannable:
1. The answer to RZ's question first: what data we can get right now to make these scenarios correct (verified table), and what must stay labelled ASSUMPTION.
2. The critique verdict on the metrics-lab idea and the recommended design (objectives, presets, weights, Pareto view).
3. The transformer-replacement and utility-ROI view.
4. A build plan on the root app by lane, with acceptance checks and a cut order, sized for the time left before Sun 27 Sep 11:00 CT.
5. Open questions to ask Base engineers on site.
Inputs: ${OVN}/DATA-GRID-ASSETS.md, ${OVN}/DATA-MARKET-PROFIT.md, ${OVN}/CRITIQUE-OBJECTIVES-LAB.md. Summaries: ${String(grid||'').slice(0,2500)} ${String(market||'').slice(0,2500)} ${String(crit||'').slice(0,3000)}. Return a 250-word summary.`, {label:'synthesize', phase:'Synthesize'})
return { summary: synth }
