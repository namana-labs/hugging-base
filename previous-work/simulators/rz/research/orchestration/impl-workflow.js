export const meta = {
  name: 'overnight-build',
  description: 'Build Hugging Base overnight from OVERNIGHT_BUILD_PROMPT.md: setup, foundation + lanes, lead merge gate, judge checkpoints, fix rounds, morning report',
  phases: [
    { title: 'Gate', detail: 'usage check before each wave (pause at 90% of the 5-hour window or 95% weekly)' },
    { title: 'Setup', detail: 'section 8.1: clone, venv, worktrees' },
    { title: 'Foundation', detail: 'L0 foundation (lead) and L1 loads in parallel' },
    { title: 'Lanes', detail: 'L2 P1, L3 P2, L4 3D + P1 view, L5 P2 + story' },
    { title: 'Merge', detail: 'lead merge gate per section 8.3, one merge at a time' },
    { title: 'Judge', detail: 'fresh-clone checkpoint verification per sections 7 and 9' },
    { title: 'Fix', detail: 'owner lanes fix judge failures and finish their done-when' },
    { title: 'Report', detail: 'docs/overnight/REPORT.md per section 9' },
  ],
}

const RUN = (args && args.run) || 1
function limiter(n){let active=0;const q=[];const next=()=>{if(active>=n||!q.length)return;active++;const j=q.shift();j.fn().then(j.res,j.rej).finally(()=>{active--;next();});};return fn=>new Promise((res,rej)=>{q.push({fn,res,rej});next();});}
const lim = limiter(5)   // RZ rule: max 5 agents at once
const A = (p, o) => lim(() => agent(p, o))

const OVN = '/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight'
const PROMPT = OVN + '/OVERNIGHT_BUILD_PROMPT.md'

const COMMON = `You are part of the overnight build of Hugging Base (Base Power x AITX hackathon; submission Sun 27 Sep 2026 11:00 CT). RZ, the team lead, is asleep. His instruction: "implement it, don't just plan it; by morning some version of this must be working."
Your single source of truth is ${PROMPT}. READ IT IN FULL before acting, then ${OVN}/DECISION.md and ${OVN}/STATUS.md (if it exists). $OVN = ${OVN}. Follow its rulings (section 3), mechanics (section 8), honesty labels and acceptance tests (section 7) exactly. The lane rules in section 6 ("Paste these rules into every lane brief") apply to you verbatim.
Do not spawn agents and do not SendMessage anyone. Usage pacing is RZ's standing rule: if you see a usage-limit warning, commit and push at once, write where you stopped into ${OVN}/NOTES.md, and stop cleanly. Never print credentials. While RZ sleeps, never block on a question: take the conservative option, log it under "Decisions RZ should check" in ${OVN}/NOTES.md, and keep building.`

const LANES = [
  { id: 'l1-loads',     name: 'L1 Loads + surrogate' },
  { id: 'l2-p1',        name: 'L2 P1' },
  { id: 'l3-p2',        name: 'L3 P2' },
  { id: 'l4-scene-p1',  name: 'L4 3D + P1 view' },
  { id: 'l5-p2-story',  name: 'L5 P2 + More + story' },
]

const GATE = {type:'object',properties:{five_hour:{type:'number'},resets_at:{type:'string'},weekly:{type:'number'}},required:['five_hour','weekly']}
const LANE_OUT = {type:'object',properties:{lane:{type:'string'},branch:{type:'string'},head_sha:{type:'string'},pr_number:{type:'number'},acceptance_passed:{type:'boolean'},not_done:{type:'array',items:{type:'string'}},summary:{type:'string'}},required:['lane','branch','acceptance_passed','not_done','summary']}
const MERGE_OUT = {type:'object',properties:{lane:{type:'string'},merged:{type:'boolean'},merge_sha:{type:'string'},main_green:{type:'boolean'},failures:{type:'array',items:{type:'object',properties:{what:{type:'string'},owner_lane:{type:'string'}},required:['what','owner_lane']}},requests_landed:{type:'array',items:{type:'string'}}},required:['lane','merged','main_green','failures']}
const JUDGE_OUT = {type:'object',properties:{checkpoints:{type:'object',properties:{C0:{type:'string'},C1:{type:'string'},C2:{type:'string'},C3:{type:'string'}}},failures:{type:'array',items:{type:'object',properties:{clause:{type:'string'},owner_lane:{type:'string'},evidence:{type:'string'},fix:{type:'string'}},required:['clause','owner_lane','evidence','fix']}},working:{type:'array',items:{type:'string'}},headline_numbers:{type:'array',items:{type:'string'}}},required:['checkpoints','failures','working']}

async function gate(label){
  const g = await A(`Usage check, run ${RUN}, before "${label}". Load the tool with ToolSearch query "select:mcp__ccd_session_mgmt__get_usage", call it once, and return five_hour = the 5-hour window percentUsed, resets_at = its resetsAt, weekly = the weekly all-models percentUsed. If the tool cannot be loaded, return five_hour = -1 and weekly = -1.`, {label:`gate:${label}`, phase:'Gate', schema:GATE, model:'haiku', effort:'low'})
  if (g && (g.five_hour >= 90 || g.weekly >= 95)) { log(`PAUSE before ${label}: 5-hour ${g.five_hour}%, weekly ${g.weekly}%, resets ${g.resets_at}`); return g }
  if (g) log(`usage before ${label}: 5-hour ${g.five_hour}%, weekly ${g.weekly}%`)
  return null
}

let chain = Promise.resolve()
function mergeLane(lane, res){
  const p = chain.then(() => A(`${COMMON}
You are L0, the lead, acting as the MERGE GATE (section 8.3) for lane ${lane.name} (branch overnight/${lane.id}).
The lane reported: ${JSON.stringify(res).slice(0, 6000)}
Do: in ~/hb-overnight/wt/gate, fetch, check out origin/overnight/${lane.id}, merge origin/main, run scripts/check_all.sh --lane ${lane.id} (plus the lane's acceptance command under the heavy-run lock if it changes an artifact). Land any "REQUEST (lead)" items from the PR body in a small lead PR first (branch overnight/l0-<topic>). If green: gh pr ready + gh pr merge --merge (merge commits, never squash, never --delete-branch), then pull main and run scripts/check_all.sh on main. If main goes red, revert at once per 8.3. If the gate fails, do not merge; say exactly what fails and which lane owns it. Respect section 8.3's merge order. Update ${OVN}/STATUS.md (lane map, SHAs, state, next step). Return the structured result.`, {label:`merge:${lane.id}`, phase:'Merge', schema:MERGE_OUT}))
  chain = p.catch(() => null)
  return p
}

const lanePrompt = (lane, extra) => `${COMMON}
You are lane ${lane.name}. Your row is in section 6 of the build prompt (branch overnight/${lane.id}); do what it says, within its "Owns" globs only, toward its "Done when", in ~/hb-overnight/wt/${lane.id} (create the worktree per section 8.1 if it is missing; first fetch origin/overnight/${lane.id} and continue from anything already pushed there). Open a draft PR within 30 minutes and push at least every 45 (section 6 rules). Do NOT merge your own PR; the lead's merge gate does that. Run your acceptance command(s) from section 7 and paste the real output.
${extra || ''}
Return the structured result: branch, head SHA, PR number, whether your acceptance passed, and what is NOT done.`

// ---------------------------------------------------------------- run
phase('Gate')
let p = await gate('setup'); if (p) return {paused_before:'setup', usage:p}

phase('Setup')
const setup = await A(`${COMMON}
You are L0, the lead. Do ONLY section 8.1 setup now: create ~/hb-overnight/{wt,cache/smartds,pr-bodies,tmp}, clone the repo to ~/hb-overnight/hb (if already cloned, fetch), set git identity, create the shared venv from demos/grid-stories/requirements.txt, copy the seed profiles, run the "before building" checks (gh pr list, recent branches), create the gate worktree ~/hb-overnight/wt/gate, and start ${OVN}/STATUS.md with T0 = now (UTC) and the lane map. Do not start the foundation yet. Return a short summary with the origin/main SHA and anything new from teammates since 4bcca51.`, {label:'setup', phase:'Setup'})

phase('Gate')
p = await gate('foundation'); if (p) return {paused_before:'foundation', usage:p, setup}

phase('Foundation')
const [l0, l1] = await Promise.all([
  A(`${COMMON}
You are L0, the lead, building the FOUNDATION (section 6 "L0 foundation", branch overnight/l0-foundation, worktree ~/hb-overnight/wt/l0-foundation): the lead-only files, scripts (setup.sh, serve.sh, build_all.sh, smoke_ui.sh, check_all.sh, check_paths.py, lanes.json, deeplinks.txt), sim core copied from demos/grid-stories/sim and extended per section 5, fixtures, data/fleet.json, data/ercot/, the UI shell with health flags and stubs, docs/contracts.md, the CLAUDE.md banner and README "Run the demo" pointer. Open the PR, run the merge gate yourself (section 8.3) and merge it when check_all.sh passes on fixtures. Update ${OVN}/STATUS.md and write ${OVN}/CHECKPOINT-C0.md. Return the structured result (lane = l0-foundation).`, {label:'L0 foundation', phase:'Foundation', schema:LANE_OUT}),
  A(lanePrompt(LANES[0], 'Before the foundation merges, use --dss demos/grid-stories/data/smartds/Loads.dss as section 6 says. Sync with origin/main at each work unit so you pick up the foundation when it lands.'), {label:'L1 loads', phase:'Foundation', schema:LANE_OUT}),
])
const m1 = l1 ? await mergeLane(LANES[0], l1) : null

phase('Gate')
p = await gate('lanes'); if (p) return {paused_before:'lanes', usage:p, l0, l1, m1}

phase('Lanes')
const wave = await pipeline(LANES.slice(1),
  lane => A(lanePrompt(lane, 'Start at your first deliverable, then keep going toward your "Done when". Sync origin/main at each work unit: producers you depend on (L1, L2, L3) merge while you work. If a dependency has not landed yet, build against the fixtures (section 5.3) and leave a clear NOT-done note.'), {label:`${lane.id}`, phase:'Lanes', schema:LANE_OUT}),
  (res, lane) => res ? mergeLane(lane, res).then(m => ({lane: lane.id, res, merge: m})) : {lane: lane.id, res: null, merge: null}
)

// judge + fix rounds
let judge = null, round = 0
const merges = [m1].concat(wave.map(w => w && w.merge)).filter(Boolean)
while (round < 3) {
  phase('Gate')
  p = await gate(`judge-${round}`); if (p) return {paused_before:`judge-${round}`, usage:p, wave: wave.map(w=>w&&{lane:w.lane, merged: w.merge&&w.merge.merged}), judge}
  phase('Judge')
  judge = await A(`${COMMON}
You are the JUDGE (section 0 "I am the judge" and section 9 "What the judge will re-run" / "spot-check"). Round ${round}. Clone main fresh into ~/hb-overnight/judge-${round} (never reuse a lane worktree), run scripts/setup.sh and scripts/check_all.sh --full (heavy-run lock), sim.verify p1 and p2, sim.calibrate, scripts/smoke_ui.sh all, and the spot-checks. Decide each checkpoint C0-C3 as pass / fail / not_reached against section 9's table. For every failure name the clause, the owner lane (l0-foundation, l1-loads, l2-p1, l3-p2, l4-scene-p1, l5-p2-story), the evidence (command + real output) and the fix. List what works (with the deep links that smoke-ok). Write ${OVN}/JUDGE-R${round}.md. Do not edit the repo.`, {label:`judge-r${round}`, phase:'Judge', schema:JUDGE_OUT})
  if (!judge) break
  const c = judge.checkpoints || {}
  const fails = judge.failures || []
  if (!fails.length && c.C1 === 'pass' && c.C2 === 'pass') { log(`round ${round}: C1 and C2 pass`); break }
  phase('Gate')
  p = await gate(`fix-${round}`); if (p) return {paused_before:`fix-${round}`, usage:p, judge}
  phase('Fix')
  const owners = {}
  fails.forEach(f => { const o = (f.owner_lane || 'l0-foundation').replace(/^overnight\//,''); (owners[o] = owners[o] || []).push(f) })
  // every lane that is not yet done also gets a round, so L4/L5 pick up real P1/P2 data
  wave.forEach(w => { if (w && w.res && (!w.res.acceptance_passed || (w.res.not_done||[]).length)) owners[w.lane] = owners[w.lane] || [] })
  const fixItems = Object.keys(owners).map(o => ({ id: o, fails: owners[o] }))
  log(`fix round ${round}: ${fixItems.map(f=>f.id+'('+f.fails.length+')').join(', ')}`)
  await pipeline(fixItems,
    f => {
      const lane = LANES.find(l => l.id === f.id)
      if (!lane) return A(`${COMMON}
You are L0, the lead. Fix these failures in lead-owned files (section 6 "Lead-only files") on a small branch overnight/l0-fix-r${round}, open a PR, run the merge gate (8.3) and merge on green. Failures: ${JSON.stringify(f.fails).slice(0,8000)}
Return the structured result (lane = l0-foundation).`, {label:`fix-r${round}:l0`, phase:'Fix', schema:LANE_OUT})
      return A(lanePrompt(lane, `FIX ROUND ${round}. The judge found these failures in your lane (fix every one, then keep going toward your "Done when"; if C2 passes and your P1/P2 items are done, do your P3 items per section 5.7):
${JSON.stringify(f.fails).slice(0,8000)}`), {label:`fix-r${round}:${lane.id}`, phase:'Fix', schema:LANE_OUT})
    },
    (res, f) => {
      const lane = LANES.find(l => l.id === f.id)
      return (res && lane) ? mergeLane(lane, res) : res
    }
  )
  round++
}

phase('Gate')
p = await gate('report'); if (p) return {paused_before:'report', usage:p, judge}
phase('Report')
const report = await A(`${COMMON}
You are L0, the lead, writing the MORNING REPORT per section 9 ("Report shape": NOT DONE first, what works and how to see it with deep links and 3-5 screenshots, proof output of 7.2-7.6 verbatim, headline numbers with labels and commands, deviations, findings for teammates, questions for RZ with your recommendation). Base it on ${OVN}/STATUS.md, ${OVN}/NOTES.md, the latest ${OVN}/JUDGE-R*.md and fresh command output from main. Commit docs/overnight/REPORT.md (and docs/overnight/BUILD_PROMPT.md = a copy of the build prompt, and at most 8 screenshots in docs/overnight/shots/) on branch overnight/report, open the PR, run the gate and merge it. Copy the report to ${OVN}/MORNING-REPORT.md. Return a 300-word summary that starts with the NOT-done count.`, {label:'report', phase:'Report'})

return { setup: String(setup||'').slice(0,1500), l0, l1, merges: merges.map(m=>({lane:m.lane, merged:m.merged, main_green:m.main_green})), judge_checkpoints: judge && judge.checkpoints, judge_failures: judge && (judge.failures||[]).length, report }
