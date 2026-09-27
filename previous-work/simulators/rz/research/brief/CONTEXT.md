# Hackathon context (shared brief for every agent)

## Event
- Base Power & AITX Talent Hackathon, hosted at Base Power's Austin HQ. 48 hours.
- **Submissions due Sunday 2026-09-27, 11:00 AM (Central).** Each team submits a **5-minute demo video + a link to the codebase**. Top submissions per track present live at awards.
- Base's own engineers judge every track. Base is hiring in Texas off what gets built.

## Tracks (one project may enter up to 2)
1. **Open Grid Data**: ERCOT publishes more public grid data than almost any market (prices, load, generation, congestion). Base's business runs on reading it better than everyone else. "Show us what you can see in the data that most people miss."
2. **Orchestration**: "Build a system that coordinates many independent things. Agents, jobs, workers, whatever you want. What matters is how it holds up when pieces fail."
3. **Most Commercializable**: "Base is a power company, not a battery company ... Build something that could actually ship as a product on top of what Base does. Show off your taste."

## Judging (100 points), judged off the 5-minute video and the codebase
"We are judging real, working systems, not slide decks or simple API wrappers."
1. Technical Execution & Completeness (30): completeness 15 (core workflow runs without crashing); technical depth 15 (real engineering, a complex pipeline, not a wrapper).
2. Fit to the Track (30): the problem 15 (meaningfully attacks the track's problem set); the "why" 15 (team can articulate why the approach solves a meaningful problem).
3. Value & Impact (20): insight quality 10 (non-obvious, genuinely useful output); usability 10 (could Base or another user use this tomorrow?).
4. Innovation & Execution (20): creativity 10 (novel combination of tools/data; looks and feels good); performance 10 (quality engineering; optimized for speed or scale).

## Team
Five people. Skills in the room: a backend-heavy engineer who ran load balancing at scale (Box, traffic peaks from China) and insists "functionality over visuals": the balancing logic must be real; someone with ~2 years working alongside ERCOT market participants (control rooms, 5-minute data, calling generators for reserve); someone keen on cybersecurity and failure modes ("the red case"); someone who can help with front end but is new to power; RZ (founding engineer, full-stack). Several members know little about electricity, so explanations need plain language. **Who does what, timelines and what gets cut are the team's call; agents propose scope and dependency order, never staffing or schedules.**

## What the team agreed in the room
- Build an honest **simulator** of a fleet of Base home batteries on a grid (start small, e.g. 4 batteries, then scale to ~1,000 homes on a small Austin-like map and beyond), driven by **real ERCOT data** (and weather), with an **orchestration / load-balancing layer** that coordinates the batteries and keeps members served and the grid balanced **when pieces fail**.
- Three layers: (1) simulation of a fake grid with fake Base units; (2) **observability** on top: detect that a box went down or something odd is happening, and apply mitigations; (3) a **narrative UI wrapper**: a map (houses, batteries, feeders, substations, power flows) with side graphs (frequency, power, prices, SoC) like an operator's real-time screen, plus scenario buttons.
- A **scenario creator**: the user can type out a scenario and get a story version of it, e.g. "an AI takes over 1,000 batteries", "ERCOT loses a large generator", "heat wave", "winter storm", "substation outage", "contractor mis-installs a whole install batch", "members tamper with boxes to hoard power", "an intelligent adversary that fights back, either mass outage or subtle degradation over time so it's never caught".
- The backend-heavy member's point, adopted by the team: the value is in **how the balancing actually works** (where the data comes from, tracking where power needs to be, load balancing) rather than the visuals. Visuals are window dressing on a real engine.
- Leaning **Orchestration** as the primary track, possibly **Open Grid Data** as the second.
- All public data used must have a named, verified source.

## What a Base engineer (deployment software team) told us
- In a grid outage a Base battery just **backs up its own home**; it is not a grid participant then. "Not too interesting."
- The interesting problem is **dynamic behavior**: some batteries charge, some discharge, offsetting load; power flows through a grid whose parts are not equally resilient; batteries are independent actors. There is a real interplay that needs simulation.
- A great question: **how does each additional battery on a stressed feeder / substation affect it**, and **how would the batteries behave differently if the controller knew grid state (e.g. feeder capacity)**? A distressed feeder is a very interesting example.
- Base's dispatch algorithm is a complex ML, black-box objective; what can be modeled are the **key signals** it ingests and what new signals would change its actions.
- A battery that **loses Wi-Fi** defaults to grid bypass / backup-only: idle, no charge or discharge unless an outage happens.
- Base does grid-load estimation math today, but not in a way that teaches their software to act better; no outage simulator; "a place to play the what-ifs" (scenario testing: battery count and placement, parts of the grid acting volatile) would be meaningful.
- Their hair-on-fire problem is **site survey** (member photos of meter/panel, where a 3x3x3 ft battery fits, manual review). Not our chosen project, but useful context.
- Security framing they liked: a good attacker either degrades performance over time so it looks intentional, or causes a mass outage.

## Research
Full report: `reports/Base Power system and ERCOT data.md` (read "What this means for our build" first). Source notes with every citation: `research_notes/Base Power system and ERCOT data/` (5 files: company/business, product/system with a simulator-parameter table, ERCOT public data/APIs with tested endpoints, simulator datasets/tools with timings, grid physics/orchestration/attacks with a scenario catalog).
