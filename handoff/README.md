# Hugging Base: team hub (who needs which doc)

26 Sep 2026 · RZ. Snapshot of the live team hub doc; RZ shares the live docs.

> **Update, 26 Sep 2026 (evening sprint): the root app is now the submission** (branch `submission`). Root `sim/` is the one engine and root `ui/` is the four story pages (Configure → Run → Results → Learnings); the old tab app is `ui/explore.html`. `simulators/rz/` stays as reference; where this hub says `simulators/rz/ui/data/` or `simulators/rz/docs/`, read the root `ui/data/` and `docs/`. Rulings and path ownership: [`docs/story-contract.md`](../docs/story-contract.md). Amy's audited numbers, each with its file and field: [`presentation/NUMBERS.md`](../presentation/NUMBERS.md).

## Who does what, and the one doc each person reads

We submit a 5-minute video and the code by Sun 27 Sep, 11:00 AM Central. The demo is a four-page story: set up a scenario, watch what happens, see the result, see the answers. Each person reads one doc.

| Person | Owns | Read this |
| --- | --- | --- |
| RZ + Michael | The engine: the simulator and data behind pages 2, 3 and 4, and that every number is correct | [handoff/ENGINE.md](ENGINE.md) |
| Connor | How all four pages look: layout, what's displayed, the story on the page, icons | [handoff/CONNOR.md](CONNOR.md) |
| Amy | The presentation: story, 5-minute script, who says what, the judges' Q&A | [presentation/START-HERE.md](../presentation/START-HERE.md) |
| Bo | Design help, plus help for anyone who needs it | Section 3 below |
| Jeff | Not assigned yet | Section 3 below |

## Hand-offs: who gives what to whom

| From | To | What | Where |
| --- | --- | --- | --- |
| RZ + Michael | Connor | Data files for every page: scenario catalogue, page-2 timeline, page-3 results, the capacity planner file | `simulators/rz/ui/data/`, documented in `simulators/rz/docs/contracts.md` |
| Connor | RZ + Michael | A request list: any field, unit or label the pages need that the files lack | A GitHub issue or message; never faked on screen |
| RZ + Michael | Amy | Audited numbers, and a yes or no on any claim | The numbers table in `presentation/START-HERE.md` |
| Connor | Amy | One link per video beat, plus screenshots | Her script is a list of clicks |
| Amy | Everyone | Who says what in the video, and the README first screen for judges | `presentation/` |
| Bo | Connor, Amy | Design tokens, icons, slide design on request | `bo/` (branch `bo/frontend`) |
| Everyone | The submission | Their piece, copied into one submission folder at the end | Section 5 |

## Bo and Jeff

**Bo: design support.** Bo's design tokens and town-grid mockup are on branch `bo/frontend`, not yet on main.

1. Open a PR from `bo/frontend` so the work lands on main in the `bo/` folder.
2. Read the team's design language in `docs/design-handoff/README.md` (colours, type, the battery-shaped fleet card, provenance tags, "green never means safe").
3. Ask Connor what the four pages need first: icons (house, battery cabinet, pad-mount and pole-mount transformer, price, money, warning) are the likely first request.
4. Offer Amy slide design for the one spec-only slide and the title card.

The only rule: design never changes a number or its label. Numbers come from the engine's files.

**Jeff: not assigned yet.** Useful places to help, in order: a second pair of hands on the capacity planner with Michael; checking every beat link in a fresh clone before recording; or helping Amy with the judges' Q&A.

## Where everything lives in the repo

One folder per person or path. Each can be deleted without breaking another.

| Folder | Whose | What |
| --- | --- | --- |
| `simulators/rz/` | RZ + Michael | The engine and app: run with `./run.sh`; gate `scripts/check_all.sh`. Also `research/`, `judges/`, `story/`, `RULINGS.md`. |
| `mpalacios/` | Michael | Controller-crash survival and the attacker detector (imports the root `sim/`, which stays frozen) |
| `simulators/connor/` | Connor | His simulator and control-room dashboard; the four pages get built here |
| `docs/design-handoff/` | Connor | The team's design language |
| `presentation/` | Amy | Her startup doc, script, Q&A |
| `bo/` (branch) | Bo | Design tokens and mockup |
| `handoff/` | Everyone | This hub and the Connor and engine handoffs |
| `sim/`, `ui/`, `scripts/`, `data/` at the root | Frozen | The older copy of the app; Michael's code depends on it. Don't edit. |
| `demos/grid-stories/`, `four-home-simulation/` | Connor, Michael | Earlier prototypes, kept for history |

Never commit `overnight/BASE_ENGINEER_INPUT.md`; it stays on RZ's laptop. The repo is public.

## The finish line

In dependency order. The team picks one code-freeze time that leaves room to record before 11:00 AM Sunday.

1. **Build in parallel.** The engine produces the data files; Connor builds the four pages against them; Amy drafts the script; Bo supports design.
2. **Freeze.** No new features after the agreed time; only fixes.
3. **Combine.** One submission folder: Connor's four pages, the engine's data files and simulator, Amy's README for judges. Pages read data by relative paths, so this is a copy, not a rewrite.
4. **Check from a fresh clone.** The engine gate `scripts/check_all.sh --full`, the browser smoke `scripts/smoke_ui.sh all`, and a click through every beat link.
5. **Record** the 5-minute video, following Amy's beat list.
6. **Submit** the video and the repo link (RZ).
