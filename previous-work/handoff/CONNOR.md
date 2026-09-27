# Hugging Base: Connor's handoff (the four pages)

> **Snapshot of 26 Sep, before PR #42; the root app is the submission:** see [README.md](../README.md) and [docs/run-the-demo.md](../docs/run-the-demo.md).

26 Sep 2026 · RZ. Snapshot of the live doc; RZ shares the live version.

## Your job, and what you hand back

You own how the four story pages look: where each container goes, what is displayed, how the story reads on each page, and the icons. RZ and Michael own the data behind them. You never compute a number; you show what the data files say, with their labels.

What you hand back to the team by the final combine:

1. **The four pages, running as a static web page** from committed data files: no server, no live calls. They must read clearly at 1080p after video compression.
2. **A page-1 picker that offers only real scenarios:** the ones in the engine's scenario catalogue. Anything else is greyed out with the reason.
3. **One link per video beat:** a URL that opens a page in a given scenario at a given moment, so Amy's script is a list of clicks. Hand her the list.
4. **A tag on every number:** REAL, SIM, DERIVED or ASSUMPTION, as a compact marker with a hover explanation.
5. **A short README in your folder:** how to open the pages and which data files they read.
6. **A request list for the engine:** any field you need that the data files don't have. Send it to RZ and Michael early; don't fake it on screen.

## The four pages and what each must show

The story runs scenario → what happens → result → answers. The layout is yours; this table is only the content each page must carry. "Ready" means it is in a committed data file today.

| Page | Must show | Status |
| --- | --- | --- |
| 1. Scenario | The real evening (22 Jul, 14 Aug, 23 Aug default, 26 Aug 2026). The charging policy (none, naive, feeder-aware). What fails (a battery goes silent, an EV plugs in, the controller stalls, a controller worker crashes, a hidden attacker). Combinations that don't exist are greyed out with a reason. | Evenings and policies ready. Failures exist for 23 Aug only. The catalogue file that lists valid combinations is not built yet. |
| 2. What happens | The feeder board with 379 transformers loading minute by minute and their tier, the batteries' charge and power, the price, the story line (one timestamped sentence per moment), and optionally the money meter. Your Chapter 1 control room is most of this page. | Ready, except per-home voltage and feeder-total load, which need a small export. |
| 3. The result | Harm to the grid (worst transformer, when, how many passed their limit, whether protection operated), members kept whole (reserve, charged by 04:00), the money, and the same result for the other policy on the same evening. | Ready in `p1/meta.json` `summary`. A per-transformer "worst of the night" list is not built yet. |
| 4. The answers | Which transformers have room and which are full. How many batteries one transformer can take (0 to 50). Whether an upgrade is worth paying for. Where to charge. Where the next battery goes. What happens when pieces fail. The money. | Where-to-charge, next battery, failures and money ready. The capacity planner (the first three) is designed, not built: Michael and RZ are building it. |

**Two things your current dashboard does differently from our data:**

- **Our evenings are 720 one-minute steps, from 16:00 to 04:00 the next morning.** Your day is 288 five-minute steps from midnight. Read the step length and start time from the data instead of hard-coding them, and let the clock keep counting past midnight. At your 1× speed our evening would flash by, so play slower; RZ's app defaults to 0.25×.
- **Our feeder is 1,010 homes, 379 transformers and 96 batteries,** not 4 of each. The board needs to scale.

## The data you get from the engine

The data lives in `simulators/rz/ui/data/` in the repo, as plain JSON your pages fetch with relative paths. Build against it today. The full analysis of what your code reads and how our files map onto it is `simulators/rz/story/STORY-CONNOR-NEEDS.md`: read that first.

| File | What it holds | Size |
| --- | --- | --- |
| `topology.json` | Every home, transformer and line with coordinates; which home is on which transformer; street A–D and T-240 marked | Under 1 MB |
| `p1/meta.json` | The evening: price per minute, markers and story events, the result summary per policy, the money | About 50 KB |
| `p1/<policy>.json` (`none`, `naive`, `aware`, `aware_faults`) | Per minute: loading of all 379 transformers, tier codes, each battery's charge, power and state, the story ticker | About 2 MB each |
| `p1/days/` | The other real evenings (gzipped: `*.json.gz`) and the money calendar | Small |
| `p2/index.json`, `p2/<combo>.json` | Where the next battery goes: ranking, before/after, the flip, capacity | 0.1–0.3 MB each |
| `mpalacios/out/p1/worker_kill.json`, `mpalacios/out/p3/covert.json` | Michael's controller crash and hidden-attacker runs | Small |

How to read them without rewriting your model code:

- **Our files store one array per quantity, as whole numbers** (tenths of a percent, per-mille charge). Yours use one object per time step. Don't convert whole files; write a small adapter that builds one frame on demand. There is a sketch, `frameAt()`, in STORY-CONNOR-NEEDS section 3.1.
- **Load one policy file at a time.** Keep every file under 4 MB; that's the team's cap.
- **The other evenings are gzipped.** Plain `fetch().json()` can't read them; RZ's app has a 15-line `getGz()` helper in `ui/lib/` you can copy.

Coming from RZ and Michael (ask if you need it sooner):

- `story/index.json`: the catalogue of valid scenarios, with titles and the reason a combination is unavailable.
- `p2/planner.json`: the capacity planner (room per transformer, the 0–50 curve, the upgrade verdict).
- A small per-scenario result file with each transformer's worst moment of the night.
- Distance along the feeder per home and transformer, for your board layout.

**What has no real source. Don't draw it as if it did:**

- **ERCOT frequency, RoCoF, time error, PRC and inertia for our evenings.** We only have 25 Sep 2026, a different day, and our small fleet cannot move ERCOT's frequency anyway.
- **Solar.** Not modelled.
- **Inverter reactive power.** Batteries run at unity power factor, so it is zero by assumption.

## How to show numbers honestly

Base engineers judge this, and one mislabelled number costs trust in the whole demo. The rules are short:

- **Show numbers; don't make them.** Every number on screen comes from a data file. Your code may format, colour, sort and animate, but never computes a tier, a rank, or a result. If you need a number that isn't in the files, ask RZ or Michael for it.
- **Every number carries its tag.** Our files store each value as `{v, label, cite}` with one of four labels: REAL (published data), SIM (our simulation or OpenDSS), DERIVED (arithmetic on those), ASSUMPTION (a value we chose). Show it as a compact tag with a hover explanation; your design handoff already has the provenance-tag style. Map your UNVERIFIED to ASSUMPTION, and SOURCED to REAL.
- **Tier colours follow the data's tier codes.** Codes run 0–5: ok, over nameplate, normal rating exceeded, the same sustained (the headline violation, 110% for 30 minutes or more), emergency, and fuse open. Over nameplate is amber and not a failure. Your "green never means safe" rule stands.
- **Missing is missing.** If a field doesn't exist (solar, per-home voltage), show "not modelled". Never draw a flat line at zero.

Words that must appear somewhere on the relevant page:

- "Naive: our assumption of one number, no feeder check". Never "how Base charges today".
- "Oncor-suburb stand-in on NREL's synthetic feeder" in the footer.
- "Gross energy value, not Base's profit" beside any dollar figure.
- "Fictional attacker" on the covert-channel view.

## What you need from whom, and what they need from you

| From | You get | When |
| --- | --- | --- |
| RZ + Michael | The data files above today; then the scenario catalogue, the capacity planner file and the per-scenario result file | As each lands in `simulators/rz/ui/data/` |
| RZ + Michael | Answers to your request list (a missing field, a unit, a label) | Send requests early; they build them |
| Bo | Design tokens and the town-grid mockup (branch `bo/frontend`), icons on request | Anytime |
| Amy | The beat list: which page, scenario and moment each part of the video shows | Once her script draft is ready |

| To | You give | Why |
| --- | --- | --- |
| Amy | One link per video beat, plus screenshots | Her script is a list of clicks |
| RZ + Michael | Your request list, and a note whenever a page shows a number that looks wrong | They own correctness |
| Everyone | The four pages, in a folder that can be copied into the submission | The final combine |

## Done when, and the final combine

- [ ] All four pages open from a static server with no errors in the browser console
- [ ] Every scenario in the catalogue plays on page 2 and shows its result on page 3
- [ ] Page 4 answers all seven questions, including the capacity planner once its file lands
- [ ] Every number on screen has its REAL / SIM / DERIVED / ASSUMPTION tag with a hover explanation
- [ ] Nothing drawn without a data source (no solar, no ERCOT system cards for our evenings)
- [ ] Readable at 1920×1080 after compression; playback slow enough to follow (0.25× or slower)
- [ ] The beat-link list and screenshots are handed to Amy
- [ ] A README in your folder says how to open the pages and which files they read

**The combine.** At the end, the team builds one submission folder: your four pages plus the engine's data files, plus Amy's README for judges. Keep your pages reading data by relative paths from one `data/` location, so the combine is a copy, not a rewrite. The last check is a fresh clone, the engine's test gate, and a click through every beat link before recording.
