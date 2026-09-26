export const meta = {
  name: 'teammate-review',
  description: 'Compare teammates\' work (Connor, Michael) with the overnight root app; judges decide what to adopt; critics verify',
  phases: [
    { title: 'Read', detail: 'one reader per teammate contribution, running their code' },
    { title: 'Judge', detail: 'two judges: Base-engineer lens and integration lens' },
    { title: 'Critique', detail: 'two critics try to refute readers and judges' },
    { title: 'Synthesize', detail: 'TEAMMATES_REVIEW.md with adopt/adapt/skip and credits' },
  ],
}
function limiter(n){let active=0;const q=[];const next=()=>{if(active>=n||!q.length)return;active++;const j=q.shift();j.fn().then(j.res,j.rej).finally(()=>{active--;next();});};return fn=>new Promise((res,rej)=>{q.push({fn,res,rej});next();});}
const lim = limiter(3)  // the overnight build is still running; RZ's cap is 5 agents at once
const A = (p, o) => lim(() => agent(p, o))
const H = '/Users/rzalagbada/Desktop/projects/base-power-hackathon'
const OVN = H + '/overnight'

const CTX = `
CONTEXT
- Team repo namana-labs/hugging-base ("Hugging Base", Base Power x AITX hackathon; submission Sun 27 Sep 2026 11:00 CT, 5-minute video + codebase; judged by Base engineers on completeness 15, depth 15, problem 15, why 15, insight 10, usability 10, creativity 10, performance 10).
- The one problem: ERCOT dispatches Base's home-battery fleet as one number per load zone and does not enforce neighbourhood (service transformer / feeder) limits. RZ's priorities: P1 where to charge (orchestrator + 3D neighbourhood visual, naive vs feeder-aware, peak relief, who earns what), P2 where the next battery goes (the CEO's priority: month-long what-if harness with counterfactual ranking), P3 secondary (hack detection, crash survival, ERCOT console).
- Overnight, an agent team built a NEW ROOT APP on main (sim/, ui/, data/, scripts/, docs/contracts.md, docs/demo-script.md, docs/how-base-plugs-in.md, docs/overnight/*). Its build prompt is ${OVN}/OVERNIGHT_BUILD_PROMPT.md (DECISION.md explains why proposal A won: copy Connor's simulator into root sim/, keep demos/ untouched, add Michael's patterns, deck.gl 3D). The latest independent verification is ${OVN}/JUDGE-R1.md (C1 and C2 pass; C3 freeze pending).
- Teammates' work (all pushed by 26 Sep 04:25 UTC; nothing newer exists on GitHub):
  * Connor Daly: demos/grid-stories/ (prototype: OpenDSS on the 1,010-home SMART-DS feeder, three scenario replays, siting score, SVG UI) and docs/design.md, docs/plan.md, docs/ui-brief.md, docs/README.md, CLAUDE.md (after PR #3 folding in the reconciliation).
  * Michael Palacios: four-home-simulation/ (a four-home street with real ERCOT data for 25 Sep 2026, water-fill, tiers, tests, two HTML views) and headroom-gridspine-dossier.html (GridSpine Atlas: substation-level N-1 siting, CIM18 data model, real OSM Austin substations; plus our PRD and research).
- Repo: work from a detached worktree you create: git -C ~/hb-overnight/hb fetch origin && git -C ~/hb-overnight/hb worktree add --detach ~/hb-overnight/review-<yourlabel> origin/main (unique path). NEVER modify ~/hb-overnight/hb or any lane worktree, never push, never open PRs. Python venv: ~/hb-overnight/.venv (do not pip install into it; make your own venv under ~/hb-overnight/tmp if you need packages). Heavy runs (>20 s CPU): prefix with lockf -k -t 2400 /private/tmp/claude-501/heavy-local.lock nice -n 10. Node v26: node --test 'ui/test/**/*.test.js' style globs.
- Honesty: every claim you make about code must come from reading or running it; say which. Never print credentials.
`

const ITEMS = [
 {id:'connor-proto', who:'Connor', what:'demos/grid-stories (prototype simulator + SVG UI + replays + siting)', ours:'root sim/ (copied from it and extended), ui/ (deck.gl 3D), P1 and P2 builds'},
 {id:'connor-docs', who:'Connor', what:'docs/design.md, docs/plan.md, docs/ui-brief.md, docs/README.md, CLAUDE.md (scope, milestones, UI brief, rules)', ours:'the root app as built, docs/contracts.md, docs/demo-script.md, docs/how-base-plugs-in.md, the build prompt\'s scope'},
 {id:'michael-fourhome', who:'Michael', what:'four-home-simulation/ (four_home.py, constants, tests, two HTML views, real 25 Sep ERCOT data)', ours:'root sim/ orchestrator, tiers, prices, money; ui P1 view'},
 {id:'michael-atlas', who:'Michael', what:'headroom-gridspine-dossier.html Parts I-IV (GridSpine Atlas: substation N-1 siting, CIM18 model, OSM Austin substations, operator graphs, provenance)', ours:'root P2 harness (siting), ui P2 view and More tab, data provenance/labels'},
]
const READ = {type:'object',properties:{
  id:{type:'string'},
  what_it_does:{type:'string'},
  ran:{type:'array',items:{type:'string'}},
  got_right:{type:'array',items:{type:'object',properties:{point:{type:'string'},aligns_with:{type:'string'},evidence:{type:'string'}},required:['point','aligns_with','evidence']}},
  better_than_ours:{type:'array',items:{type:'object',properties:{point:{type:'string'},evidence:{type:'string'}},required:['point','evidence']}},
  already_absorbed:{type:'array',items:{type:'string'}},
  reusable:{type:'array',items:{type:'object',properties:{piece:{type:'string'},where:{type:'string'},how_to_integrate:{type:'string'},owner_area:{type:'string'},effort:{type:'string',enum:['S','M','L']},risk:{type:'string'},value_for_video_or_judges:{type:'string'}},required:['piece','where','how_to_integrate','effort','value_for_video_or_judges']}},
  misaligned_or_wrong:{type:'array',items:{type:'object',properties:{point:{type:'string'},evidence:{type:'string'}},required:['point','evidence']}},
  bugs_found:{type:'array',items:{type:'string'}}
},required:['id','what_it_does','ran','got_right','better_than_ours','already_absorbed','reusable','misaligned_or_wrong']}

phase('Read')
const reads = (await Promise.all(ITEMS.map(it => A(`${CTX}
You are reader "${it.id}". Review ${it.who}'s work: ${it.what}. Compare it with what we have: ${it.ours}.
Read it thoroughly and RUN it (its tests, its build or its HTML in headless Chrome if relevant) inside your own worktree. Then read the matching parts of our root app on main and run the relevant check (e.g. scripts/check_all.sh --quick or the verify command named in docs/overnight or the build prompt section 7, whichever is cheap).
Answer: what it does; what ${it.who} got RIGHT that aligns with the shared goal, RZ's priorities, the rubric, or the team's rules (cite the doc and line); what is BETTER than ours (with evidence); what our build already absorbed; specific reusable pieces (file/function/idea, how to integrate into the root app, which lane area owns it, effort S/M/L, risk, and its value for the video or the judges); anything misaligned or wrong; bugs you found (with the command that shows them). Write ${OVN}/REVIEW-${it.id}.md and return the structured result.`, {label:`read:${it.id}`, phase:'Read', schema:READ})))).filter(Boolean)

phase('Judge')
const JUDGE = {type:'object',properties:{
  decisions:{type:'array',items:{type:'object',properties:{source:{type:'string'},piece:{type:'string'},decision:{type:'string',enum:['adopt_now','adopt_if_time','adapt','skip']},why:{type:'string'},priority:{type:'number'}},required:['source','piece','decision','why','priority']}},
  credits:{type:'array',items:{type:'object',properties:{who:{type:'string'},credit:{type:'string'}},required:['who','credit']}},
  scores:{type:'array',items:{type:'object',properties:{source:{type:'string'},alignment:{type:'number'},quality:{type:'number'},notes:{type:'string'}},required:['source','alignment','quality','notes']}}
},required:['decisions','credits','scores']}
const LENSES = [
 'You are a skeptical Base Power engineer judging the hackathon. Decide what, from the teammates\' work, would most improve what Base engineers see in the 5-minute video and the codebase before 11:00 CT Sunday, and what would only add noise.',
 'You are the integration lead of the root app. Decide what can actually be merged into the root app safely in the time left (lane ownership in scripts/lanes.json, contracts in docs/contracts.md, the gate scripts/check_all.sh), what conflicts with it, and what should stay where it is.',
]
const verdicts = (await Promise.all(LENSES.map((l,i) => A(`${CTX}
${l}
The four readers' results (full reviews in ${OVN}/REVIEW-*.md): ${JSON.stringify(reads).slice(0,40000)}
For every reusable piece: adopt_now / adopt_if_time / adapt / skip, with why and a priority (1 = highest). Score each teammate contribution for alignment (1-10) and quality (1-10). Credit what each teammate got right, specifically. Check claims against the code where cheap (your own detached worktree per the context).`, {label:`judge:${i+1}`, phase:'Judge', schema:JUDGE})))).filter(Boolean)

phase('Critique')
const CRIT = {type:'object',properties:{refuted:{type:'array',items:{type:'object',properties:{claim:{type:'string'},why:{type:'string'},evidence:{type:'string'}},required:['claim','why','evidence']}},confirmed:{type:'array',items:{type:'string'}},missed:{type:'array',items:{type:'string'}}},required:['refuted','confirmed','missed']}
const CLENS = [
 'Refute the READERS: re-run the commands behind their "better than ours", "bugs found" and "got right" claims and try to prove them wrong. Also say what they missed.',
 'Refute the JUDGES: for every adopt_now decision, try to show it would break the root app, its contracts or its gate, cost more than stated, or not matter for the video. For every skip, check whether it was a mistake.',
]
const crits = (await Promise.all(CLENS.map((c,i) => A(`${CTX}
You are adversarial critic ${i+1}. ${c} Default to refuting when a claim can't be reproduced.
Readers: ${JSON.stringify(reads).slice(0,25000)}
Judges: ${JSON.stringify(verdicts).slice(0,15000)}`, {label:`critic:${i+1}`, phase:'Critique', schema:CRIT})))).filter(Boolean)

phase('Synthesize')
const synth = await A(`${CTX}
Write ${OVN}/TEAMMATES_REVIEW.md for RZ (plain language, scannable):
1. The finding first: nothing new from teammates has been pushed since 26 Sep 04:25 UTC; this review covers what they created before then (Connor: grid-stories + design/plan/ui-brief; Michael: four-home + GridSpine Atlas).
2. What each teammate got right that aligns with what was shared (credits, specific).
3. A ranked table of pieces to use: adopt now / adopt if time / adapt / skip, with where it goes in the root app, effort, and why. Drop anything a critic refuted; mark anything disputed.
4. Conflicts or misalignments between their work and the root app, and how to resolve each.
5. Bugs found in their work or ours (with the command that shows them).
6. A short message RZ could post to the team (do not send it).
Inputs: readers ${JSON.stringify(reads).slice(0,25000)} judges ${JSON.stringify(verdicts).slice(0,12000)} critics ${JSON.stringify(crits).slice(0,12000)}.
Return a 250-word summary.`, {label:'synthesize', phase:'Synthesize'})
return { summary: synth, n_reads: reads.length, judges: verdicts.map(v => v.decisions.filter(d=>d.decision==='adopt_now').map(d=>d.source+': '+d.piece)) }
