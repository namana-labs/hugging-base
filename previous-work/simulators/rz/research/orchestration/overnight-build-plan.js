export const meta = {
  name: 'overnight-build-plan',
  description: 'Decide the build base with a judge panel, then write and harden a one-shot overnight build prompt for Hugging Base',
  phases: [
    { title: 'Scout', detail: 'map the repo as it is now and run every existing test' },
    { title: 'Propose', detail: 'three architects propose the build base from different angles' },
    { title: 'Judge', detail: 'two judges score the proposals' },
    { title: 'Write', detail: 'decision record and an overnight build prompt in the style of an earlier exemplar' },
    { title: 'Harden', detail: 'two critics attack the prompt, writer revises' },
  ],
}

function limiter(n){let active=0;const q=[];const next=()=>{if(active>=n||!q.length)return;active++;const j=q.shift();j.fn().then(j.res,j.rej).finally(()=>{active--;next();});};return fn=>new Promise((res,rej)=>{q.push({fn,res,rej});next();});}
const lim = limiter(3)   // another workflow is finishing; RZ's rule is max 5 agents at once
const A = (p, o) => lim(() => agent(p, o))

const H = '/Users/rzalagbada/Desktop/projects/base-power-hackathon'
const R = H + '/hugging-base'
const O = H + '/overnight'
const V = '/private/tmp/claude-501/-Users-rzalagbada-Desktop-projects-REDACTED/db7213a8-6bab-44d3-b22b-9fe4a11f46ca/scratchpad/venv/bin/python'

const BRIEF = `
THE PROJECT
- "Hugging Base": a 5-person team's entry to the Base Power x AITX hackathon (Base Power HQ, Austin). Submission due **Sunday 27 Sep 2026, 11:00 AM Central**: a 5-minute demo video + a link to the codebase. Judged by Base engineers on: technical execution & completeness 30 (core workflow runs without crashing 15, real engineering depth 15), fit to track 30 (the problem 15, the why 15), value & impact 20 (non-obvious insight 10, could Base use it tomorrow 10), innovation & execution 20 (creativity / looks good 10, performance / speed or scale 10). Tracks: Orchestration (primary: "coordinate many independent things; what matters is how it holds up when pieces fail"), Open Grid Data (ERCOT data insight), Most Commercializable.
- The ONE problem (the only thing set in stone): ERCOT dispatches Base's home-battery fleet as one number per load zone and does not enforce neighbourhood (feeder / service transformer) limits. When prices drop and every battery charges at once, small 25 kVA transformers overload and voltage sags while the market sees "all good". We show it on a real-looking Austin feeder and fix it with a feeder-aware orchestrator, and we answer Base's two on-site questions: where to charge relative to congestion, and where the next battery should go. Plus: spot compromised batteries from physics, and keep working when parts of our own controller crash.
- It is now about 01:00 CDT Sat 26 Sep. An unattended agent team will build overnight from a prompt you help write. RZ (team lead, computer engineer, not a power engineer) said: "we don't want to overcomplicate things"; the build must be "actually walkable and usable"; the prompt must let an agent "one-shot the whole thing from beginning all the way to the end".

RULINGS ALREADY MADE BY RZ (do not reopen)
- Overnight scope = "Core + failure beat": (1) real ERCOT LZ_NORTH 15-min prices in the replays instead of the scripted price drop; (2) transformer limits in three tiers: over nameplate kVA (>100%, amber, counted not a violation), normal rating exceeded (>110% for >=30 min, the violation we headline), emergency (>150% at any step); (3) a comms-loss scenario (battery silent 180 s -> stale; when its command expires it idles with backup armed; a neighbour on the same feeder covers); (4) a small RECORDED multi-process controller run: several worker processes hold leases on groups of transformers, one is killed (kill -9), another takes over at a higher epoch, the battery rejects stale-epoch (zombie) commands; recorded into the same replay format so the UI plays it with no live server; (5) next-battery siting re-scored greedily after each placement, plus a "useful capacity" metric (batteries added before the first normal-tier violation or before curtailment passes a stated share); (6) an operator console fed by real ERCOT data (frequency, inertia, PRC reserve, net-load ramp, reserves, congestion/shadow prices, DC ties, data quality) — specs and data are being produced in ${H}/site/ems/ (read *-spec.md and SYNTHESIS.md if present; data JSON beside them; raw evidence in ${H}/evidence/live-20260925/). Keep everything that already works (heat wave, charging rebound naive vs feeder-aware, covert channel + quarantine, next-battery score, feeder board). Stretch only: Claude scenario studio, stolen-key hijack, feeder outage/restoration, real basemap with OSM substations, transmission layer.
- Git flow = one lead agent plans and runs up to 5 helper agents in separate lanes, each on its own branch, merging through PRs into main with tests passing; stops at checkpoints and writes a morning report. Commits as RZ (git identity already set to [personal email removed]) with the Co-Authored-By trailer; never --no-verify.
- The BUILD BASE (which code the overnight build starts from) is NOT decided: RZ asked for agents to decide it "based on what is best", against the problem above. Options include: extend Connor's working prototype (demos/grid-stories) into a main app at the repo root; build fresh from the Headroom PRD (docs/headroom/PRD.md: NATS, multi-process, full contracts); improve the prototype in place; build on Michael's new four-home-simulation; or a hybrid you define.
- Honesty rules: every number labelled REAL / SIM / DERIVED / ASSUMPTION; feeder presented as an Oncor-suburb stand-in at LZ_NORTH (placeholder); fictional adversary only; OpenDSS judges every violation; replay is the demo spine (no live dependency on stage); no language model ever produces a setpoint, base point or rank.
- Usage pacing for any agent session (RZ standing rule): work until the account's 5-hour window reaches 90%, then stop launching, let in-flight work finish, wait for the reset, continue; stop at 95% of the weekly limit. Max 5 subagents at once.

WHERE THINGS ARE
- Team repo (git, public): ${R} — run git fetch first; read origin/main. Key: CLAUDE.md, README.md, docs/README.md, docs/design.md, docs/plan.md, docs/ui-brief.md, docs/reconciliation.md, docs/research-report.md, docs/headroom/ (our PRD, round-1 designs, critiques, research notes), demos/grid-stories/ (Connor's prototype: sim/ Python + OpenDSS, ui/dist static app, README with limitations), four-home-simulation/ (Michael's new four-home sim with real ERCOT 25 Sep data), headroom-gridspine-dossier.html (Michael's GridSpine Atlas design).
- Real ERCOT extracts and analysis scripts: ${H}/evidence/ (scratchpad-20260925/bp-data-ingest/rtm2026_lz.csv = 15-min settlement point prices by load zone 2026; fme/ = frequency events; critique-scratch/*.py = Track 1 analyses).
- The team's visual walkthrough page (what the product should feel like): ${H}/site/hugging-base-atlas.src.html (published as https://claude.ai/artifact/L4E5u7XwJYMCj6dhLSRdK6).
- Python with OpenDSSDirect.py 0.9.4 + numpy: ${V} (Python 3.14; it lives in a session scratchpad a reboot can wipe, so the build prompt must tell builders to create their own venv from requirements). Homebrew python3.14 and python3.11 exist; node v26 exists.
- Heavy local runs (>20 s CPU): prefix with  lockf -k /private/tmp/claude-501/heavy-local.lock nice -n 10
- Format exemplar for the build prompt (structure and tone only; do not copy its content): [a build prompt from an unrelated project; path removed]
- Do NOT modify the repo. Write only under ${O}/.
`


const DIRECTION = `
UPDATED DIRECTION FROM RZ (2026-09-26 ~01:15 CDT). This OVERRIDES the "Core + failure beat" scope ruling wherever they conflict. Focus on Base's two questions; everything else is secondary.

P1 — WHERE TO CHARGE: the orchestrator and its visual. Before sending a charge instruction, check each transformer's headroom and send charging only where it fits. The UI must make this visible and obvious to a non-engineer:
 - A 3D view of the neighbourhood: homes rendered as battery columns (fill = state of charge), transformers rendered with their capacity and current load so headroom is visible.
 - NAIVE dispatch: one market instruction reaches every battery at once; transformers overload and turn red.
 - FEEDER-AWARE dispatch: charging goes to transformers A, B, C, D in turn; as a battery fills or its homes' load rises, it throttles and the next takes over, so nothing ever exceeds its limit. A continuously re-balancing animation at fine time steps (e.g. 1 minute), driven by a real time-stepped simulation, not a canned animation.
 - The reverse at peak: when a transformer is overloaded by its homes' load (air conditioning) and Base batteries behind it are charged, discharging them offsets their homes' load and the transformer's load drops at once. Show before/after, and show who saves money and how Base earns: peak prices / arbitrage at real ERCOT prices (REAL/DERIVED), avoided transformer failure and member outages, utility programs that pay for local peak relief or upgrade deferral (CoServ, GVEC, Austin Energy exist; say honestly that in Oncor territory Base is not paid for local relief today — an opportunity, labelled).
 - Fold Track 2's "holds up when pieces fail" cheaply into P1: a battery goes offline or a transformer runs hot mid-balance and the orchestrator re-balances around it.

P2 — WHERE THE NEXT BATTERY GOES (the CEO said this matters most): a what-if harness.
 - Simulate a real month (real ERCOT LZ_NORTH 15-minute prices for e.g. July or August 2026, with SMART-DS load profiles for the matching month) and rank candidate homes: with vs without a battery there — transformer stress hours in each tier, peak loading, whether that transformer would have failed or caused an outage, energy shaved, revenue.
 - The user adjusts controls (dispatch policy naive vs feeder-aware, battery class, number of batteries, charge rule) and sees the counterfactual: "if you had put it here / managed it this way, this transformer would not have overloaded".
 - Make the ranking and the what-if visual (map or 3D + charts). Use a fast per-transformer model for the month screening and OpenDSS as the referee on the shortlist and the demo frames; say which numbers come from which.

P3 — SECONDARY, only after P1 and P2 work end to end: spotting hacked batteries (the existing covert-channel replay can stay as is), surviving our own controller crashes (the multi-process worker-kill run moves to STRETCH), and the ERCOT operator console / Open Grid Data insights (site/ems data exists; wire it in only if time allows).

Still standing: real ERCOT prices (no scripted price drop in anything new), three-tier transformer limits, honesty labels, replay/static spine for the demo, the git flow (lead + <=5 lanes + PRs), usage pacing, don't overcomplicate.
`
const BRIEF2 = BRIEF + DIRECTION

phase('Scout')
const scout = await A(`${BRIEF2}
A scout already wrote ${O}/REPO_STATE.md (repo state, both teammates' simulations with their tests actually run, what design.md / plan.md / ui-brief.md now say, environment facts). Your job: git fetch in ${R} and check for anything pushed since it was written (new commits, branches, PRs); append a short "Update" section to REPO_STATE.md if anything changed; do not redo the tests unless new code landed. Then return a concise summary (under 500 words) of the facts most relevant to deciding the build base for RZ's UPDATED DIRECTION (P1 where to charge with a 3D balancing visual and peak relief; P2 a month-long next-battery what-if harness): which existing code already does per-transformer headroom, time-stepped dispatch, SoC, OpenDSS solves, real ERCOT prices, month-long runs, and 3D or map rendering; test status; and performance numbers.`, {label:'scout', phase:'Scout'})

phase('Propose')
const ANGLES = [
 {k:'A', t:'RELIABILITY FIRST: what gives a crash-proof, recordable demo of the full scope by morning with the least risk. Unattended agents will build it.'},
 {k:'B', t:'JUDGING FIRST: what scores highest on the rubric (especially Orchestration "holds up when pieces fail", technical depth, Open Grid Data insight, performance) while still finishing the scope in one night.'},
 {k:'C', t:'TEAM AND MERGE FIRST: four teammates and their agents are pushing to the same repo; what structure lets up to 5 overnight lanes build in parallel without colliding with each other or with Connor\'s and Michael\'s work, and keeps the repo coherent for judges reading the codebase.'},
]
const PROPOSAL = {type:'object',properties:{
  angle:{type:'string'}, base_option:{type:'string'}, summary:{type:'string'},
  layout:{type:'string'}, reuse:{type:'string'},
  lanes:{type:'array',items:{type:'object',properties:{name:{type:'string'},owns:{type:'string'},depends_on:{type:'string'},first_deliverable:{type:'string'},acceptance:{type:'string'}},required:['name','owns','acceptance']}},
  scope_mapping:{type:'array',items:{type:'object',properties:{scope_item:{type:'string'},how:{type:'string'},acceptance_test:{type:'string'}},required:['scope_item','how','acceptance_test']}},
  risks:{type:'array',items:{type:'object',properties:{risk:{type:'string'},mitigation:{type:'string'}},required:['risk','mitigation']}},
  cut_order:{type:'array',items:{type:'string'}},
  why_not_others:{type:'string'}
},required:['angle','base_option','summary','layout','reuse','lanes','scope_mapping','risks','cut_order','why_not_others']}
const proposals = (await Promise.all(ANGLES.map(a => A(`${BRIEF2}
You are architect ${a.k}. Angle: ${a.t}
Read ${O}/REPO_STATE.md first (the scout's facts), then the code and docs you need. Scout summary:
${String(scout||'').slice(0,4000)}
Propose the build base and the overnight build: which option (or hybrid) and why, the concrete repo layout, which existing code is reused from where (Connor's prototype, Michael's four-home sim, PRD ideas), up to 5 lanes with what each owns and its acceptance test, how P1 (where to charge: 3D balancing visual, naive vs feeder-aware, peak discharge relief with the money) and P2 (where the next battery goes: month-long what-if harness with controls and ranking) get built and proved (a command and its expected output), what the 3D view is built with (must work offline in the static demo), and where P3 fits if time allows, the data contracts between simulator and UI, risks with mitigations, and the cut order if the night runs short. Be concrete enough that an unattended agent could start from it. Keep it simple: RZ said don't overcomplicate. Write your proposal to ${O}/PROPOSAL-${a.k}.md and return the structured version.`, {label:`propose:${a.k}`, phase:'Propose', schema:PROPOSAL})))).map((p,i)=>p?{...p,id:ANGLES[i].k}:null).filter(Boolean)

phase('Judge')
const SCORE = {type:'object',properties:{
  scores:{type:'array',items:{type:'object',properties:{id:{type:'string'},demo_reliability:{type:'number'},rubric_fit:{type:'number'},unattended_executability:{type:'number'},team_fit:{type:'number'},simplicity:{type:'number'},total:{type:'number'},notes:{type:'string'}},required:['id','demo_reliability','rubric_fit','unattended_executability','team_fit','simplicity','total','notes']}},
  winner:{type:'string'}, graft:{type:'array',items:{type:'string'}}, must_fix:{type:'array',items:{type:'string'}}
},required:['scores','winner','graft','must_fix']}
const JUDGES = [
 'You are a skeptical Base Power engineer who will judge the hackathon. Score for what would impress and convince you in a 5-minute video plus the codebase, and for honesty.',
 'You are an engineering manager who has run unattended overnight agent builds. Score for whether an agent team can actually execute this from a prompt without getting stuck, with tests that prove each step, and for merge safety.',
]
const verdicts = (await Promise.all(JUDGES.map((j,i) => A(`${BRIEF2}
${j}
Score each proposal 1-10 on demo_reliability, rubric_fit, unattended_executability, team_fit, simplicity; total = sum. Read the full proposals in ${O}/PROPOSAL-*.md and check their claims against the repo (${O}/REPO_STATE.md and the code) — penalize anything that relies on code or data that does not exist or tests that do not pass. Name a winner, the best ideas to graft from the others, and anything the winner must fix.
Structured proposals: ${JSON.stringify(proposals).slice(0,30000)}`, {label:`judge:${i+1}`, phase:'Judge', schema:SCORE})))).filter(Boolean)
const tally = {}
verdicts.forEach(v => v.scores.forEach(s => { tally[s.id] = (tally[s.id]||0) + s.total }))
const ranked = Object.entries(tally).sort((a,b)=>b[1]-a[1])
log('Judge totals: ' + ranked.map(r=>r[0]+'='+r[1]).join(', '))

phase('Write')
const writePrompt = `${BRIEF2}
You are the lead author. Three proposals (${O}/PROPOSAL-A.md, -B.md, -C.md) were scored by two judges. Combined totals: ${JSON.stringify(ranked)}. Judge verdicts: ${JSON.stringify(verdicts).slice(0,12000)}
1) Write ${O}/DECISION.md: the build base chosen (normally the top total; override only with a stated reason), the scores table, what was grafted from the runners-up, and the must-fixes applied. Plain language, one page.
2) Write ${O}/OVERNIGHT_BUILD_PROMPT.md — the single file the overnight lead agent reads and builds from, in the style and rigor of the exemplar (read it for structure). Target 7,000–11,000 words. Sections, in this order:
 0. Your role and mine (lead builder runs up to 5 helper lanes; RZ and the coordinator judge in the morning; what RZ decides)
 1. The mission in one screen (the problem, the product, the tracks, the deadline)
 2. Read these, in this order (exact repo paths and why)
 3. The rulings (settled; don't re-ask): scope, git flow, build base + why, honesty labels, framing, usage pacing (90% per 5-hour window, wait for reset, stop at 95% weekly; max 5 subagents)
 4. Facts that shape the build (real numbers with labels: feeder counts, kVA mix, rebound results, detector results, ERCOT data findings, what is scripted today; from REPO_STATE.md, the research, site/ems specs)
 5. Architecture and repo layout (tree), data contracts between simulator and UI (exact JSON shapes, file names), the P1 time-stepped balancing simulation and 3D view (library, offline), the P2 month harness pipeline (fast per-transformer screening + OpenDSS referee) and its controls, and where P3 plugs in
 6. Lanes (<=5): each with owns, branch name, first deliverable, interfaces it consumes/produces, and done-when
 7. Acceptance tests for P1 and P2 first, then P3 (exact commands and expected outputs; include the demo-replay check that the UI opens from static files with no server)
 8. Mechanics: repo, branches, PRs (gh), merge order, rebase discipline with teammates' pushes, commit identity + trailer, venv creation from requirements, heavy-run lock, where evidence goes, what never to touch (other teammates' folders unless the decision says otherwise)
 9. Checkpoints and the morning report: where to write (docs/overnight/REPORT.md in the repo via PR, plus NOTES), report shape, what the judge will re-run
 10. Rules (never --no-verify, labels, no secrets, no fabricated data, fictional adversary, don't break main)
 11. Cut order if behind, and what "done" looks like for recording the 5-minute video
 12. Open items and questions for Base engineers on site (don't let them block)
Every command in the prompt must be one you verified works against the repo as it is now, or be clearly marked as something the builder creates. Return a 300-word summary.`
const written = await A(writePrompt, {label:'write', phase:'Write'})

phase('Harden')
const CRIT = {type:'object',properties:{problems:{type:'array',items:{type:'object',properties:{where:{type:'string'},what:{type:'string'},severity:{type:'string',enum:['critical','major','minor']},fix:{type:'string'}},required:['where','what','severity','fix']}},verdict:{type:'string'}},required:['problems','verdict']}
const CRITICS = [
 'EXECUTABILITY: pretend you are the overnight lead agent with only this prompt and the repo. Walk through it step by step and actually try the commands that should already work (read-only; use a temp copy or venv under '+O+'/.venv-critic). Where would you get stuck, guess, build the wrong thing, collide with a teammate, or be unable to prove "done"? Missing or wrong paths, commands, contracts, contradictions with the repo.',
 'CORRECTNESS AND HONESTY: check every number, claim and label in the prompt against the repo, the research report, the site/ems specs and REPO_STATE.md. Check that the UPDATED DIRECTION from RZ is applied exactly (P1 where to charge with the 3D balancing visual and peak relief, P2 the month-long next-battery harness, P3 secondary) along with the standing rulings (git flow, pacing, labels, framing), that nothing overcomplicates the build beyond what the scope needs, and that the demo story still proves the one problem.',
]
const crits = (await Promise.all(CRITICS.map((c,i) => A(`${BRIEF2}
You are an adversarial critic of ${O}/OVERNIGHT_BUILD_PROMPT.md (and ${O}/DECISION.md). Lens: ${c}
Report only real problems, each with a concrete fix. Do not edit the files.`, {label:`critic:${i+1}`, phase:'Harden', schema:CRIT})))).filter(Boolean)
const probs = crits.flatMap(c => c.problems).filter(p => p.severity !== 'minor')
log(`Critics raised ${probs.length} major/critical problems`)
const revised = probs.length ? await A(`${BRIEF2}
Revise ${O}/OVERNIGHT_BUILD_PROMPT.md (and DECISION.md if needed) to fix every critical and major problem below. Verify any command you change. Keep the structure. Append a short "Revision log" at the end listing each fix. Return a 300-word summary of the final prompt and the decision.
Problems: ${JSON.stringify(probs).slice(0,20000)}
Minor notes you may also apply: ${JSON.stringify(crits.flatMap(c=>c.problems).filter(p=>p.severity==='minor')).slice(0,5000)}`, {label:'revise', phase:'Harden'}) : written

return { scout: String(scout||'').slice(0,3000), tally: ranked, winner_by_judge: verdicts.map(v=>v.winner), must_fix: verdicts.flatMap(v=>v.must_fix), critics: crits.map(c=>({verdict:c.verdict, n:c.problems.length})), final: revised }
