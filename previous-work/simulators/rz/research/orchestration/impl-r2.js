export const meta = {
  name: 'round2-visual-data-history',
  description: 'Round 2: UX design panel + data audit + historical scout, then lanes build RZ\'s visual/data/history feedback, merge gate, judge with screenshots, fix rounds',
  phases: [
    { title: 'Gate', detail: 'usage check (pause at 90% 5-hour or 95% weekly)' },
    { title: 'Design', detail: 'three UX designers, a data auditor, a historical-days scout' },
    { title: 'Decide', detail: 'UX judge writes one UX_SPEC_R2 for builders' },
    { title: 'Build', detail: 'lanes l4 (P1 panel + 3D), l5 (P2 + story), l2 (history + money + P1 data fixes), l3 (P2 data fixes), l0 (lead files)' },
    { title: 'Merge', detail: 'lead merge gate, one at a time' },
    { title: 'Judge', detail: 'fresh clone + screenshots against RZ feedback' },
    { title: 'Fix', detail: 'owner lanes fix judge failures' },
    { title: 'Report', detail: 'append round 2 to docs/overnight/REPORT.md' },
  ],
}
const RUN = (args && args.run) || 1
function limiter(n){let active=0;const q=[];const next=()=>{if(active>=n||!q.length)return;active++;const j=q.shift();j.fn().then(j.res,j.rej).finally(()=>{active--;next();});};return fn=>new Promise((res,rej)=>{q.push({fn,res,rej});next();});}
const lim = limiter(3)
const A = (p, o) => lim(() => agent(p, o))
const OVN = '/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight'

const COMMON = `You are part of ROUND 2 of the Hugging Base build (Base Power x AITX hackathon; submission Sun 27 Sep 2026 11:00 CT). RZ tested round 1 himself and wrote feedback: ${OVN}/RZ_FEEDBACK_R2.md — READ IT FIRST, it is the brief. The root app is on main in ~/hb-overnight/hb (read docs/run-the-demo.md, docs/contracts.md, docs/overnight/REPORT.md). The round-1 build prompt ${OVN}/OVERNIGHT_BUILD_PROMPT.md still governs mechanics: lanes and ownership (scripts/lanes.json, scripts/check_paths.py), the merge gate (section 8.3), honesty labels, OpenDSS as referee, the static replay spine, commits as RZ with the Co-Authored-By trailer, never --no-verify, never touch demos/ or four-home-simulation/. Lane rules in its section 6 apply verbatim. Do not spawn agents or SendMessage anyone. RZ is awake: still never block on a question; log decisions for him in ${OVN}/NOTES.md. On a usage-limit warning, commit, push and stop cleanly. Never print credentials.`

const GATE = {type:'object',properties:{five_hour:{type:'number'},resets_at:{type:'string'},weekly:{type:'number'}},required:['five_hour','weekly']}
async function gate(label){
  const g = await A(`Usage check, round 2 run ${RUN}, before "${label}". Load the tool with ToolSearch query "select:mcp__ccd_session_mgmt__get_usage", call it once, return five_hour = 5-hour percentUsed, resets_at = its resetsAt, weekly = weekly all-models percentUsed. If unavailable return -1 for both.`, {label:`gate:${label}`, phase:'Gate', schema:GATE, model:'haiku', effort:'low'})
  if (g && (g.five_hour >= 90 || g.weekly >= 95)) { log(`PAUSE before ${label}: 5-hour ${g.five_hour}%, weekly ${g.weekly}%`); return g }
  if (g) log(`usage before ${label}: 5-hour ${g.five_hour}%, weekly ${g.weekly}%`)
  return null
}
const LANE_OUT = {type:'object',properties:{lane:{type:'string'},branch:{type:'string'},head_sha:{type:'string'},pr_number:{type:'number'},acceptance_passed:{type:'boolean'},not_done:{type:'array',items:{type:'string'}},summary:{type:'string'}},required:['lane','branch','acceptance_passed','not_done','summary']}
const MERGE_OUT = {type:'object',properties:{lane:{type:'string'},merged:{type:'boolean'},merge_sha:{type:'string'},main_green:{type:'boolean'},failures:{type:'array',items:{type:'object',properties:{what:{type:'string'},owner_lane:{type:'string'}},required:['what','owner_lane']}}},required:['lane','merged','main_green','failures']}
const JUDGE_OUT = {type:'object',properties:{verdicts:{type:'array',items:{type:'object',properties:{ask:{type:'string'},status:{type:'string'},evidence:{type:'string'}},required:['ask','status','evidence']}},failures:{type:'array',items:{type:'object',properties:{clause:{type:'string'},owner_lane:{type:'string'},evidence:{type:'string'},fix:{type:'string'}},required:['clause','owner_lane','evidence','fix']}},gate_green:{type:'boolean'}},required:['verdicts','failures','gate_green']}

let chain = Promise.resolve()
function mergeLane(laneId, res){
  const p = chain.then(() => A(`${COMMON}
You are L0, the lead, acting as the MERGE GATE (section 8.3) for lane ${laneId} (branch overnight/${laneId}). Lane report: ${JSON.stringify(res).slice(0,5000)}
In ~/hb-overnight/wt/gate: fetch, check out origin/overnight/${laneId}, merge origin/main, run scripts/check_all.sh --lane ${laneId} (plus the lane's acceptance under the heavy-run lock if it changed an artifact). Land any "REQUEST (lead)" items first in a small lead PR (branch overnight/l0-r2-<topic>). If green: gh pr ready + gh pr merge --merge (never squash, never --delete-branch), then in ~/hb-overnight/hb pull --ff-only and run scripts/check_all.sh. If main goes red, revert your merge at once. Update ${OVN}/STATUS.md. Return the structured result.`, {label:`merge:${laneId}`, phase:'Merge', schema:MERGE_OUT}))
  chain = p.catch(() => null)
  return p
}
const lanePrompt = (laneId, task) => `${COMMON}
You are lane ${laneId}, round 2. Work in ~/hb-overnight/wt/${laneId} on branch overnight/${laneId} (it exists from round 1: fetch, then git merge --no-edit origin/main before starting; never rebase). Stay inside your lane's globs in scripts/lanes.json; anything outside goes to the lead as "REQUEST (lead): ..." in your PR body. Open a PR (new round-2 PR titled "[${laneId}] R2: ...") within 30 minutes and push at least every 45. Do NOT merge; the lead's gate does. Your task:
${task}
Follow ${OVN}/UX_SPEC_R2.md exactly where it covers your lane, and ${OVN}/AUDIT-R2.md for data fixes you own. Run your acceptance commands and scripts/smoke_ui.sh --lane ${laneId}; take screenshots of your changed views into ${OVN}/shots/r2-${laneId}/ and open 2-3 of them with Read to check them yourself. Return the structured result.`

// ------------------------------------------------------------------
phase('Gate')
let p = await gate('design'); if (p) return {paused_before:'design', usage:p}

phase('Design')
const DESIGN_ANGLES = [
 {k:'story', t:'FIRST GLANCE AND STORY: what a first-time viewer (a Base engineer, or anyone) sees in the first 5 seconds; how the naive branch tells its story visually (price drops, everyone charges, transformer overloads); story cues synced to the replay clock; attention and hierarchy.'},
 {k:'clarity', t:'OPERATOR CLARITY: declutter the right panel into a few front cards plus collapsible sections and detail drawers; plain-language copy; icons instead of numbers (keep the worst transformer %); battery icons in the A-D / T-240 gauges; honesty labels as compact dots or badges with hover tooltips; hover explanations for every icon; playback 0.1x/0.25x/0.5x plus step.'},
 {k:'scene', t:'3D REALISM AND RECOGNISABILITY (deck.gl 9.4.0 vendored, offline, must also work in the 2D fallback): houses with pitched roofs and house-like proportions and colours (from the OSM footprints), transformers as recognisable pad-mount or pole-mount models with a load/headroom display that explains itself, batteries as a distinct cabinet beside the house with a charge level, a visual legend (house / battery / transformer), deck.gl pick/hover tooltips on every object; performance on a laptop GPU and in headless SwiftShader.'},
]
const [designs, audit, hist] = await Promise.all([
  Promise.all(DESIGN_ANGLES.map(d => A(`${COMMON}
You are UX designer "${d.k}". Angle: ${d.t}
Run the app (scripts/serve.sh on a free port, or headless Chrome as scripts/smoke_ui.sh does) and look at every beat link in scripts/deeplinks.txt: take screenshots into ${OVN}/shots/r2-design-${d.k}/ and open them with Read. Read ui/panels/p1.js, ui/panels/p2.js, ui/lib/scene*.js, ui/css/*.css. Then write ${OVN}/UX-R2-${d.k}.md: a concrete redesign for P1 (and P2 where it applies) that answers every ask in RZ_FEEDBACK_R2.md from your angle. Include ASCII wireframes of the P1 screen, the exact components (DOM structure, CSS, inline SVG icon set: house, battery with fill levels, transformer, price, money, warning), the tooltip copy for each icon/object, the story cue script for naive and aware, the deck.gl layer changes, and which lane owns each file (scripts/lanes.json). Keep it buildable in a few hours by one lane per area. Return a 200-word summary.`, {label:`design:${d.k}`, phase:'Design'}))),
  A(`${COMMON}
You are the DATA AUDITOR (read-only; do not edit the repo). Verify that every number and label a viewer sees is correct: P1 (all four branches, gauges, ticker, money card, scale ladder, tiers, fuse margin, the A-D and T-240 figures) against OpenDSS re-solves (sim.verify p1, spot re-solves of 3-5 frames with the venv) and the price file; P2 (ranking, candidate cards, counterfactual text, useful capacity, referee badge, screening chips) against sim.verify p2 and the referee; the More tab money and "how Base plugs in" figures against their cited sources in the research. Check every REAL/SIM/DERIVED/ASSUMPTION label is the right one. Write ${OVN}/AUDIT-R2.md with a table: where on screen, shown value, correct value, evidence (command + output), owner lane (l2-p1, l3-p2, l4-scene-p1, l5-p2-story, l0-foundation), severity. Return a 200-word summary.`, {label:'audit', phase:'Design'}),
  A(`${COMMON}
You are the HISTORICAL-DAYS SCOUT. RZ wants to jump between real dates and times using historical data, and to see how Base makes money during peak hours with real prices. Work out, with measurements: which real days to precompute for P1 (candidates: 2026-07-22 ERCOT all-time peak; 2026-08-23 the current day; the August 2026 max-price day; a cheap/negative-price day; one 2025 summer spike day), what data exists on disk (ERCOT LZ_NORTH 15-min prices in evidence/ and data/ercot/, SMART-DS load profiles by calendar date, any weather), how long one P1 day build takes (engine.json, or time a --quick build), the data size per day against the size budget, how the UI should switch days (date picker + real clock, deep link param like &date=YYYY-MM-DD), and how to show Base's peak-hour money per day (energy arbitrage at real prices, peak relief value, labelled honestly; research: docs/research-report.md). Write ${OVN}/HIST-R2.md as a buildable spec for lane l2-p1 (sim side) and l4-scene-p1 / l0 (UI side). Return a 200-word summary.`, {label:'hist', phase:'Design'}),
])

phase('Decide')
const spec = await A(`${COMMON}
You are the UX JUDGE. Three designers wrote ${OVN}/UX-R2-story.md, UX-R2-clarity.md, UX-R2-scene.md. Score each against RZ_FEEDBACK_R2.md (every ask), buildability in one lane-afternoon, and honesty (labels must survive as compact markers). Then write ONE spec, ${OVN}/UX_SPEC_R2.md, for the builders: the winning structure with the best ideas grafted, per lane (l4-scene-p1: P1 panel + 3D + gauges + tooltips + speeds + P1 story cues; l5-p2-story: P2 declutter with the same patterns + More tab + beats/demo-script; l0-foundation: shared shell pieces such as the icon set, tooltip helper, provenance-dot component, the date picker and the &date param routing; l2-p1: sim data the UI needs, e.g. per-minute story events). Include the HIST-R2.md plan (${OVN}/HIST-R2.md) and the data fixes in AUDIT-R2.md, each assigned to its owner lane. Include acceptance checks (commands + what a screenshot must show). Designer summaries: ${JSON.stringify(designs).slice(0,6000)} Audit: ${String(audit||'').slice(0,3000)} Hist: ${String(hist||'').slice(0,3000)}. Return a 300-word summary.`, {label:'ux-judge', phase:'Decide'})

phase('Gate')
p = await gate('build'); if (p) return {paused_before:'build', usage:p, spec}

phase('Build')
const LANES = [
 {id:'l0-foundation', task:'As L0 (lead-owned files only): build the shared pieces UX_SPEC_R2.md assigns to l0 (icon set, tooltip helper, provenance-dot component, date picker and &date routing, speed options, legend container), plus the l0 data fixes in AUDIT-R2.md. Open your PR, then run the merge gate on it yourself and merge on green, first, so other lanes can use the shared pieces.'},
 {id:'l2-p1', task:'Build the sim side of HIST-R2.md (real historical days for P1 with the &date data layout, peak-hour money per day with honest labels) and the story-event data UX_SPEC_R2.md needs from the sim, plus every l2-p1 fix in AUDIT-R2.md. Heavy builds under the lock.'},
 {id:'l4-scene-p1', task:'Build the P1 redesign and the 3D realism in UX_SPEC_R2.md: declutter + collapsible panel, plain copy, icons, battery icons in the gauges, hover tooltips on panel icons and 3D objects, realistic houses, recognisable transformers and battery cabinets, legend, 0.1x/0.25x/step playback, P1 story cues, the day switcher UI, plus every l4 fix in AUDIT-R2.md. Sync origin/main after l0 and l2 land and use their pieces.'},
 {id:'l5-p2-story', task:'Build the P2 declutter with the same patterns (UX_SPEC_R2.md), the More tab money-per-day story, beats.json and docs/demo-script.md updated for the new visuals and the day switcher, plus every l5 fix in AUDIT-R2.md.'},
 {id:'l3-p2', task:'Fix every l3-p2 item in AUDIT-R2.md (P2 numbers, ranking, referee, labels). If there are none, verify P2 once more (sim.verify p2) and return with nothing to merge.'},
]
const built = await pipeline(LANES,
  l => A(lanePrompt(l.id, l.task), {label:`r2:${l.id}`, phase:'Build', schema:LANE_OUT}),
  (res, l) => (res && l.id !== 'l0-foundation') ? mergeLane(l.id, res).then(m => ({id:l.id, res, merge:m})) : ({id:l.id, res, merge:null})
)

let judge = null
for (let round = 0; round < 2; round++) {
  phase('Gate')
  p = await gate(`judge-${round}`); if (p) return {paused_before:`judge-${round}`, usage:p, built: built.map(b=>b&&{id:b.id, merged:b.merge&&b.merge.merged})}
  phase('Judge')
  judge = await A(`${COMMON}
You are the ROUND 2 JUDGE, round ${round}. Clone main fresh into ~/hb-overnight/judge-r2-${round}; run scripts/setup.sh, scripts/check_all.sh (and --full under the lock if time allows), sim.verify p1 and p2, scripts/smoke_ui.sh all. Screenshot every beat and the new day switcher at 1920x1080 into ${OVN}/shots/judge-r2-${round}/ and OPEN them with Read. For each ask in RZ_FEEDBACK_R2.md give status met / partly / not met with evidence, and re-check the AUDIT-R2.md rows. List failures with the owner lane and the fix. Write ${OVN}/JUDGE-R2-${round}.md. Do not edit the repo.`, {label:`judge-r2-${round}`, phase:'Judge', schema:JUDGE_OUT})
  if (!judge || !(judge.failures||[]).length) break
  phase('Gate')
  p = await gate(`fix-${round}`); if (p) return {paused_before:`fix-${round}`, usage:p, judge}
  phase('Fix')
  const by = {}; judge.failures.forEach(f => { const o=(f.owner_lane||'l0-foundation').replace(/^overnight\//,''); (by[o]=by[o]||[]).push(f) })
  await pipeline(Object.keys(by),
    o => A(lanePrompt(o, `FIX ROUND ${round} of round 2. Fix every one of these judge failures: ${JSON.stringify(by[o]).slice(0,6000)}${o==='l0-foundation'?' (as L0, run the merge gate on your own PR and merge on green)':''}`), {label:`r2-fix${round}:${o}`, phase:'Fix', schema:LANE_OUT}),
    (res, o) => (res && o !== 'l0-foundation') ? mergeLane(o, res) : res
  )
}

phase('Report')
const report = await A(`${COMMON}
You are L0. Append a "Round 2 (26 Sep, RZ's visual/data/history feedback)" section to docs/overnight/REPORT.md on branch overnight/report-r2: NOT done first; each ask in RZ_FEEDBACK_R2.md with met/partly/not met and a deep link; the data audit outcome; the new real days and how to switch; 3-5 screenshots (<=400 KB each) in docs/overnight/shots/; commands to run. Open the PR, run the gate, merge. Copy it to ${OVN}/ROUND2-REPORT.md. Return a 250-word summary starting with the NOT-done count.`, {label:'r2-report', phase:'Report'})
return { spec: String(spec||'').slice(0,1500), built: built.map(b=>b&&{id:b.id, ok:b.res&&b.res.acceptance_passed, merged:b.merge&&b.merge.merged}), judge_failures: judge && (judge.failures||[]).length, report }
