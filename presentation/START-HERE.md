# Hugging Base: presentation startup doc (for Amy)

26 Sep 2026 · RZ

> This is a snapshot of the live doc, which RZ shares with you. Comment and edit there; this copy is here so everything lives in the repo. Put your scripts, Q&A sheet and slide notes in this `presentation/` folder, on your own branch.
>
> **Run the app today:** from the repo root, `scripts/setup.sh && scripts/serve.sh`, then open http://127.0.0.1:8765/ui/. The demo beats are in `docs/demo-script.md`. Once RZ's folder lands, the same app runs from `simulators/rz/` and the script moves to `simulators/rz/docs/demo-script.md`.

## Your job in one screen

You own how we explain Hugging Base to the judges: the story, the video script, who says what, and how each number is shown. The team builds; you make sure it lands in 5 minutes and survives a Base engineer's questions.

What done looks like:

- **The video script:** 5 minutes, beat by beat, following the four-page story (section 4). Each beat has a speaker, what is on screen, and the exact words.
- **Talking points per speaker:** 3 to 5 lines each, in plain words.
- **A judge Q&A sheet:** the questions Base engineers will likely ask, each with a short, true answer.
- **Words to use and words to avoid:** one list the whole team follows (a start is in section 12).
- **One slide:** the profit-vs-reliability dial and the utility's return on an upgrade. It is a spec only, not built.
- **The first screen of the repo README:** 10 lines a judge reads before running anything.

You don't need to know power engineering. Every term you need is in section 3, and every number you may say is in section 8 with its label.

## The event and how we are judged

We submit a 5-minute demo video and a link to our code by Sun 27 Sep 2026, 11:00 AM Central. Base Power's own engineers judge both, and Base is hiring in Texas off what gets built. Their words: "real, working systems, not slide decks or simple API wrappers."

| Criterion | Points | What earns it for us |
| --- | --- | --- |
| Completeness | 15 | Every page of the story runs without crashing; every link in the video works. |
| Technical depth | 15 | A real physics engine (OpenDSS) checks every result; a real controller, not a wrapper. |
| The problem | 15 | We attack a problem Base has today: street transformers the market cannot see. |
| The "why" | 15 | We can say in one breath why our approach fixes it. This is mostly your job. |
| Insight | 10 | Something non-obvious, for example: how you charge decides where the next battery should go. |
| Usability | 10 | Base could use it tomorrow: a ranked list beside their install queue, our controller behind their dispatch. |
| Creativity | 10 | Real ERCOT evenings on a real feeder model, told as a story. |
| Performance | 10 | Measured speed: milliseconds per physics solve, microseconds per controller call. |

Tracks: **Orchestration** is our main one ("coordinate many independent things; what matters is how it holds up when pieces fail"). **Open Grid Data** is the second. **Most Commercializable** may also fit.

## The one problem, in plain words

ERCOT, the Texas grid operator, tells Base's fleet of home batteries one number per price zone, such as "charge this many megawatts now". It never looks at the equipment on your street. Each street has small transformers, each serving a handful of homes (about 3 on average on our feeder: 1,010 customers (971 homes, 39 small businesses) on 379 transformers). When prices crash at night and every battery charges at once, those small transformers overload, while the market sees "all good".

Base asked us two questions on site. **Where should batteries charge, given this?** And, the CEO's priority, **where should the next battery go?** A Base engineer then added the business pain: installs get blocked late because the utility says the street transformer needs an upgrade.

| Term | What it means |
| --- | --- |
| ERCOT | The operator of the Texas grid and its electricity market. Publishes real prices every 15 minutes. |
| Load zone (LZ_NORTH) | A region that shares one market price. We use LZ_NORTH as a placeholder zone. |
| Feeder | One neighbourhood circuit coming out of a substation. Ours serves 1,010 customers (971 homes, 39 small businesses). |
| Service transformer | The box or can on your street that steps power down for a few homes. We have 379 of them. |
| kVA / kW | The size of a transformer (kVA) and power being used (kW). A 25 kVA transformer is a common small one. |
| Base battery (Core) | Base's home battery: 20 kW. It keeps 20% in reserve for the home's backup. |
| Naive charging | Split ERCOT's number across all batteries with no street check. Our assumption of the simple way, not how Base works today. |
| Feeder-aware charging | Our way: check each transformer's spare room first and send only what fits. |
| OpenDSS | A standard physics engine for power grids. It is our referee: it checks every result, and is never part of the controller. |
| NREL SMART-DS | A published, realistic model of an Austin-area grid from a US national lab. Realistic, but not a real Oncor circuit. |
| Oncor | The utility that owns the wires in much of North Texas. Our feeder is a stand-in for an Oncor suburb. |
| Back-feed | Batteries sending power out at the same time. Too much of it overloads a transformer too. |
| Headroom / room | How much more power a transformer can carry before it passes its rating. |

## The four-page story

The demo is a story in four pages: you set up a scenario, watch it play out, see the result, then see how it answers Base's questions. Connor owns how the pages look. RZ owns what data each page shows and that it is correct. You own what we say on each page.

| Page | The question it answers | What it shows | Data status |
| --- | --- | --- | --- |
| 1. Scenario | "What are we testing?" | Pick a real ERCOT evening, how batteries charge (none, naive, feeder-aware), and what goes wrong (a battery loses Wi-Fi, an EV plugs in, a controller crashes, a hidden attacker). | Evenings and charging choices exist. The full menu of combinations is being defined now. |
| 2. What happens | "What does the grid do, minute by minute?" | The evening plays out: the price drops, batteries respond, transformers fill up or overload, story lines explain each moment. | Exists for the real evenings, from the simulation. |
| 3. The result | "How did it go?" | Worst transformer and when, how many passed their limit, whether any street went dark, money earned, reserve kept, versus the other charging policy. | Mostly exists. A clean summary per scenario is being built. |
| 4. The answers | "What should Base do?" | Which transformers have room and which are full. How many batteries one transformer can take (0 to 50). Which transformers are worth paying to upgrade. Where to charge. Where the next battery goes. What happens when pieces fail. The money. | Where-to-charge, next-battery and failures exist. The capacity planner is being designed now. |

The natural spine for the script: **page 2 shows the problem, page 3 proves it, page 4 is the payoff.** Page 1 is the hook: "you pick the evening; the grid can't lie about what happens".

## How the pieces fit, and who built what

Everything flows one way: **real data → the controller (orchestration) → the physics referee → the answers → the story pages**. Each teammate built in their own folder of the team repo ([github.com/namana-labs/hugging-base](https://github.com/namana-labs/hugging-base)); at the end we combine the best into one submission folder.

| Who | Folder | What it is | Where it shows up in the story |
| --- | --- | --- | --- |
| RZ | `simulators/rz/` | The main engine: the controller, the OpenDSS referee, real ERCOT evenings, where-to-charge, where-the-next-battery-goes, the money, the capacity planner (in progress). | Pages 2, 3 and 4: the data behind all of them. |
| Michael | `mpalacios/` | Controller crash survival: 3 workers share the batteries; kill one and another takes over. A detector that catches a hidden (fictional) attacker from physics. | Page 1 failure choices; page 4 "what happens when pieces fail". |
| Michael | `four-home-simulation/` | The first small 4-home model the main engine grew from. | Background: "we started small". |
| Connor | `simulators/connor/` | A four-node simulator, a simulated day, and the control-room dashboard. | The visual design of all four pages. |
| Connor | `docs/design-handoff/` | The team's design language: colours, type, the battery-shaped fleet card, compact source tags. | How every page looks. |
| Connor | `demos/grid-stories/` | The first prototype, where the main app started. | Background. |
| Bo | `bo/` (branch, not merged yet) | Design tokens and a town-grid mockup. | Visual polish. |

The honest one-liner for judges: "one engine, many hands". The engine produces every number; the other folders make it survive failure, look right, and prove each piece in small first.

## What "orchestration" means here

Our orchestration is the controller that turns ERCOT's one number into safe commands for 96 separate home batteries, and keeps working when parts of the system fail. That is exactly what the Orchestration track asks for.

1. **The input:** ERCOT gives Base one number per zone, such as "charge this many MW now".
2. **The split:** our controller first helps any transformer that is already over its limit, by discharging that street's own batteries. Then it hands out charging to the emptiest batteries first, never past a transformer's spare room and never below the member's 20% backup reserve.
3. **Taking turns:** a battery keeps its turn for a few minutes before the next one gets it, so batteries don't flicker on and off.
4. **Surviving lost contact:** every command has a number and an expiry. A battery ignores old commands. If it loses its connection, it sits idle in backup-only mode: no charging, and no sending power to the grid. Base engineers confirmed this behaviour on site.
5. **Surviving a controller crash (Michael):** three controller workers share the fleet. Kill one mid-way and another takes over, and batteries refuse the dead worker's late commands.
6. **Catching an attacker (Michael):** a fictional attacker hides a signal in the fleet. We catch it from physics and home meters, then quarantine it.
7. **The referee:** after every simulated minute, OpenDSS checks the whole feeder. It grades the controller; it never helps it.

Two sentences to have ready: "No AI model sets any battery command; the controller is plain, testable code." And: "The physics engine is the referee, not a player."

## What is real, and what is not

Every number on screen carries one of four labels: REAL, SIM, DERIVED or ASSUMPTION. Judges will test this, so the script must say each number the way its label allows. An independent audit is re-checking every label right now; section 11 says where its report lands.

| Label | What it covers | Say it like this |
| --- | --- | --- |
| REAL | ERCOT prices every 15 minutes, 1 Jan to 19 Sep 2026, and four real evenings: 22 Jul (Texas's record demand), 14 Aug (a quiet night), 23 Aug (the one we know best), 26 Aug (August's priciest). The NREL feeder's layout and its 379 transformer sizes. OpenStreetMap buildings. Base facts: 20 kW Core, 20% backup reserve, Base's Houston fleet charging as one block on 22 Jul (Base's blog). A battery that loses Wi-Fi sits idle in backup-only mode (Base engineers, on site). | "Real ERCOT prices on a published national-lab model of an Austin-area grid." |
| SIM | Everything the physics engine computes: how full each transformer gets, voltages, minutes over a limit. The home loads (driven by real NREL load shapes). | "Simulated with a real power-flow engine." |
| DERIVED | Arithmetic on the above: money, rankings, the moment charging starts, price drops. | "Calculated from the real prices and the simulation." |
| ASSUMPTION | The naive branch. Where the 96 batteries sit. Battery capacity (37 kWh) and efficiency. The fuse rule (below). 2018 loads paired with 2026 prices by calendar date. How long before a silent battery counts as lost. LZ_NORTH as the zone. | "This is our assumption, and here is what would change it." |

**Three things we never claim:**

- It is not Base's real grid. The feeder is realistic but synthetic: an Oncor-suburb stand-in.
- The naive branch is not how Base charges today. Base's real method is not public; naive is our assumption of the simple way.
- Dollar figures are gross energy value, not Base's profit.

**The fuse rule, since you will be asked.** A transformer's fuse melts if it carries far too much for too long, and the homes on it go dark. We don't have Oncor's real fuse curve, so we assume it blows above 200% for 10 minutes, or above 300% for 60 seconds. It matters: in the naive branch on 23 Aug, transformer A reaches 201.2% and stays above 200% for 9 minutes, one short of our rule. So we show no dark homes, and we say the margin out loud.

## Numbers you can use today

These come from the round-1 build report, which passed a full fresh-clone check on 26 Sep. Round 2 changed some data, so treat the SIM and DERIVED rows as drafts until the data-truth audit confirms them. Rows marked "re-check" are the most likely to move.

**The audited numbers, each with its label, file and field, are in [NUMBERS.md](NUMBERS.md) (26 Sep 2026 audit). Where this table and NUMBERS.md differ, NUMBERS.md wins.**

| Claim | Number | Label | Status |
| --- | --- | --- | --- |
| Our feeder | 1,010 customers (971 homes, 39 small businesses), 379 street transformers, 96 Base batteries | REAL (feeder); ASSUMPTION (where batteries sit) | Stable |
| Base battery | 20 kW each, 20% kept for home backup | REAL | Stable |
| Naive charging, 23 Aug, 22:30 | Transformer A at 201.2% of nameplate; 11 normal-rating events; 3 transformers past emergency (150%) | SIM | Re-check |
| Feeder-aware, same evening | 0 overloads caused by batteries; fleet charged 100.0% by 04:00; the 20% reserve never breached by dispatch | SIM | Re-check |
| Pieces fail (23 Aug) | A battery goes silent at 22:15; the controller stalls; still 0 overloads caused by batteries | SIM | Re-check |
| 50 random failure runs | 0 battery-caused normal-rating or emergency events in all 50; batteries that never went silent charged at least 99.6% | SIM | Re-check |
| August, 96 batteries | Hours above nameplate (screening): 673 naive vs 2 feeder-aware | SIM | Re-check |
| Where the next battery goes | #1 is Home 0409: its transformer's month peak falls from 119.5% to 96.9% (OpenDSS-checked) | SIM | Re-check |
| How charging changes siting | The top-10 homes differ between naive and feeder-aware: 7 of 10 overlap | DERIVED | Re-check |
| How many batteries fit, empty feeder | Feeder-aware: 1,007 (OpenDSS-checked). Naive: 100 hold and the 101st takes the feeder-head cable over its rating (OpenDSS). | SIM | Re-check: round 2 changed how naive is measured |
| Money, 23 Aug | $893.83 naive vs $916.56 feeder-aware: being careful earned slightly more | DERIVED (gross, not profit) | Re-check |
| Real price crashes, 2026 | 27 times the price fell by half or more within 15 minutes (from $60 or more); 13 in the evening | DERIVED | Stable |
| Scale | A 40 kW battery burst is 160% of a 25 kVA street transformer, but 0.000049% of ERCOT's peak | DERIVED | Stable |
| Speed | 2.13 ms per OpenDSS solve; 66.6 µs per controller call at 96 batteries; about 65 ms at 100,000 | DERIVED (measured on a shared laptop) | Re-check |

The insight line judges remember: **"the grid's peak and the price peak are different hours"**. Street transformers peak around 16:00 (SIM); prices peak around 18:00 (REAL).

## The current script, and where it goes in the story

A 5-minute script already exists (`docs/demo-script.md` today; `simulators/rz/docs/demo-script.md` once RZ's folder lands), written for the old tab layout: 12 beats, each one deep link into the app. Keep its facts and its careful wording; re-cut its order into the four pages. Your first draft can be mostly re-ordering.

| Old beat (time) | What it shows | Goes to page |
| --- | --- | --- |
| The problem (0:00) | Street A to D in 3D; Base's real Houston charging block; the scale ladder | 1 (the hook) |
| Afternoon peak relief (0:25) | A's own batteries discharge to bring A back under its rating | 2 |
| Grid peak vs price peak (0:50) | The street peaks at one hour, the price at another | 4 (insight) |
| Evening back-feed (1:00) | Naive sells all at once and overloads on the way out | 2 |
| Price crash, naive (1:25) | Price drops, every battery charges, transformers overload | 2, then 3 |
| Price crash, feeder-aware (2:00) | Room checked first; batteries take turns; no overload caused by batteries | 2, then 3 |
| Pieces fail (2:30) | A battery goes silent, an EV plugs in, the controller stalls; still safe | 1 (choice), 2, 4 |
| Where the next battery goes (3:00) | #1 home, its transformer with and without the battery | 4 |
| The flip (3:30) | The best homes change with how you charge | 4 (insight) |
| How many fit (3:55) | Naive vs feeder-aware capacity, checked by OpenDSS | 4 (capacity planner) |
| Money (4:20) | Money per evening, real evenings, the calendar | 3 and 4 |
| How Base plugs it in (4:45) | The ranked list beside the install queue; the controller behind dispatch | 4 (close) |

New material you will script once it exists: the page-1 scenario picker, the page-3 result summary, and the capacity planner's three layers (which transformers have room, how many fit on one, which are worth upgrading).

## Your deliverables and first steps

Start with the story skeleton today; fill in exact numbers only after the data audit lands. Work in the `presentation/` folder of the repo (this doc is there as `START-HERE.md`), on your own branch, so nobody's changes collide.

First steps:

1. Read sections 3 to 7 of this doc, then open the app and click through the beats (ask RZ for the one command that starts it).
2. Write the one-breath "why": one sentence a Base engineer nods at. Test it on RZ.
3. Draft the 5-minute beat list over the four pages: time, page, speaker, what is on screen, the words. Reuse the table in section 9.
4. Draft the judge Q&A sheet (section 11 has the open questions; a judges' guide with likely questions is coming).
5. Swap in final numbers once the audit and the capacity planner land, and keep every label.

Done when:

- [ ] The "why" sentence is agreed with RZ
- [ ] The beat list covers all four pages in 5:00 or less, with a speaker per beat
- [ ] Every number in the script is in the audited table, said the way its label allows
- [ ] The Q&A sheet has at least 10 questions with short, true answers
- [ ] The profit-vs-reliability and utility-return slide is drafted (clearly marked "spec, not built")
- [ ] The first 10 lines of the repo README are written for a judge
- [ ] One full dry run, timed, with the people speaking

## Who to ask, what's coming, and questions for Base

| Ask | About |
| --- | --- |
| RZ | The story, the data, whether a number or claim is allowed |
| Connor | How each of the four pages looks; screenshots and screen recordings |
| Michael | Controller crash survival and the attacker detector |
| Bo | Visual design tokens and mockups |

Coming today into `simulators/rz/` in the repo:

| File | What it gives you |
| --- | --- |
| `judges/JUDGES-GUIDE.md` | How everything fits, real vs simulated, the video map, likely judge questions with answers |
| `judges/ORCHESTRATION.md` | The orchestration explained plainly, with each failure it survives |
| `judges/DATA-TRUTH-*.md` | The audit of every input and every on-screen number: the source for final numbers |
| `story/STORY-DATA-CONTRACT.md` | Exactly what data each of the four pages shows |
| `research/capacity-planner/DATA_AND_OBJECTIVES_LAB.md` | The capacity planner spec and its 60-second demo beat |
| `TASKS.md` | Every workstream and who is on it |

Questions to ask Base engineers on site (their answers make our numbers stronger):

1. What actually protects a 25 kVA pole-top transformer running at 150 to 200% for over an hour: which fuse and curve, or heat damage with no trip?
2. How long before a battery that stops hearing from Base gives up on its last command? We assume 3 minutes to mark it silent and 5 minutes to expire a command.
3. Which ERCOT price zone do Oncor's Austin-suburb members settle in?
4. How do Texas utilities check a battery install against the street transformer, and who pays for an upgrade?
5. What transformer data (age, size, last replaced) can Base get from the utility portal?
6. Does Base already stagger charging after a price crash, or charge as one block?

## Rules for everything we say and show

One wrong claim costs trust in the whole demo, so these rules outrank a punchier line.

| Say | Never say |
| --- | --- |
| "The naive branch, which is our assumption" | "How Base charges today" |
| "No street transformer passes its limit because of batteries" | "Nothing passes its limit" |
| "Over its rating: amber, not a failure" | "It overheats" or "it fails" |
| "Protection may operate, under our assumed fuse rule" | "The street goes dark" as a fact |
| "Gross energy value, not Base's profit" | "Base earns $X" |
| "Local relief is an unpriced opportunity" | "Revenue from relief" |
| "An Oncor-suburb stand-in on a published NREL model" | "Base's grid" or "Oncor's grid" |
| "A fictional attacker" | Any real company or group as the attacker |
| "The ranking adds a grid lens to Base's install queue" | "Base's siting product" |
| "A band of 3 to 17 mHz" for a 1,000-battery hijack's effect on grid frequency | A single number, or "3 to 5 mHz" |

Also:

- Read numbers exactly as the screen shows them; never round up a claim.
- Say "screening" for a number with the ≈ mark; say "OpenDSS-checked" only where the screen shows the check.
- The demo replays saved results; nothing live is needed on camera.
- Never share or quote our private notes from Base engineers outside the team. Paraphrase "a Base engineer told us" only, and never name them.
