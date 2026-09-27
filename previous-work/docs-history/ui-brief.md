# UI brief: Hugging Base

One document for whoever sketches the interface. It says what the product is, who watches it and how, what already exists, what every screen must show, and the visual language to use. Written 26 Sep 2026. If something here conflicts with [design.md](design.md), the design doc wins; tell us and we will fix this file. **For visual design (colours, type, spacing, motion, components), [design-handoff/](design-handoff/README.md) is authoritative and supersedes §6–7 below.**

Labels follow the repo convention: **INFERENCE** is a guess from indirect evidence, **ASSUMPTION** is a placeholder, and anything unlabelled is decided.

---

## 1. The product in five sentences

Base Power runs thousands of home batteries in Texas as one power plant. The market pays a battery the same wherever it sits in a price zone, but the neighbourhood grid does not benefit the same, and nothing in the market protects a street transformer from batteries that all charge at once. Hugging Base is a simulator of one real-looking Austin feeder that answers three questions: which batteries to recharge or discharge when a piece of the grid is congested, where the next battery should go and what it is worth, and what happens when pieces fail (devices lose comms, a group is hijacked, our own controller dies). Physics is judged by a real power-flow solver at every five-minute step. The interface is the story told over that engine: a feeder board, a timeline, and panels that show one honest number per beat.

## 2. Who sees it, and how

| Audience | How | What that means for the UI |
|---|---|---|
| Base's engineers as judges | A **5-minute screen-recorded video**, plus a look at the code. Due Sunday 27 Sep 2026, 11:00 Central. | Everything must read at 1080p, 16:9, after video compression. One big number per beat. No hover-only information. No sound cues. |
| Teammates on stage or at a laptop | Run locally from static files | Nothing may depend on a server or the network. Must survive a presenter's nerves: big targets, obvious next action. |
| A Base engineer trying it later | Same static bundle | Every figure labelled with its provenance. Nothing that pretends to be Base's product. |

Desktop only. No phone layout is needed.

## 3. Hard constraints

These come from the project's non-negotiables and cannot be traded for a nicer layout.

1. **Static files, no server.** The browser plays precomputed replays. The one live piece (a controller runtime that gets killed on camera) records itself into the same replay format, so the UI never needs it running.
2. **The feeder board is an SVG diagram, not a map.** Real SMART-DS topology stretched onto a board. A real-basemap inset is a later enhancement, so leave a place for it but do not design around it.
3. **Framing labels are always visible:** "Oncor-suburb stand-in · LZ_NORTH" near the board, "SMART-DS · CC BY 4.0" attribution, and an ASSUMPTION tag wherever prices or load are scripted rather than real.
4. **Every number carries its label** (SOURCED, DERIVED, ASSUMPTION, UNVERIFIED) somewhere reachable in one click. Do not strip a label to make a screen cleaner.
5. **The adversary is fictional.** No real company name, logo or hint appears anywhere near the covert-channel scenario.
6. **No language model decides anything.** The UI must never imply that a model chose a dispatch, a setpoint or a ranking. If a model drafts a scenario or explains a number, say so in words on that element.
7. **Do not present the next-battery score as a Base product.** Copy says "adds a grid lens to install scheduling", never "Base's siting tool".
8. **Transformer loading shows three tiers,** not one red line: over nameplate (amber, counted), above normal rating for a sustained window (the violation we headline), above emergency rating (immediate). The legend must show all three.
9. **The 20% member reserve is never breached.** If a panel shows state of charge, the reserve is drawn as a floor.
10. **Do not reproduce the Base wordmark or logo** (a registered trademark) or the ERCOT logo. Our wordmark is "Hugging Base".

## 4. What exists today

The prototype at `demos/grid-stories/ui/dist/` is a working single-page app in plain JavaScript and one stylesheet. It plays three scenarios end to end. Start from it; the engine and data contracts underneath are staying.

**Current layout** (1900px max, dark theme):

- Top bar: wordmark with a lightning-bolt tile, "NORTH AUSTIN / P1U–17263" label, "Model & sources" button opening a dialog.
- Left rail: three numbered "chapters" (Heat-wave evening, Charging rebound, Covert channel).
- Workspace: eyebrow + scenario title, a four-tile stat row (feeder demand MW, highest transformer load %, lowest home voltage pu, market position forgone kW), then a two-column board: the SVG feeder (layer buttons Loading / Voltage / Next battery / Detector, legend, zoom, north arrow, attribution) beside a "mission" panel (eyebrow "MISSION 02", a difficulty meter, objective, an Even split / Feeder-aware toggle, a story block with a timestamp, a primary "Run the scenario" button).
- Below: a transport bar (play, restart, clock, scrubber with event markers, speed) and a "Where should the next battery go?" dock that opens the candidate explorer in a dialog.
- Dialogs: candidate detail (value and risk components, λ slider, "Test a battery here", "Plan this as the next build"), model and sources.

**Current look:** near-black green backgrounds (#101713, #142019, #20291f), a lime accent (#c4ee85) for everything interactive, amber (#efbe70) and coral (#fa8272) for status, a display face for headlines. Copy leans on game tropes: "MISSION", "●●○ INTERMEDIATE", "YOUR OBJECTIVE", "DECISIONS CHANGE THE OUTCOME".

**Keep:** the information architecture (chapters → board + side panel → transport → next move), the four board layers, the stat row as the place the one big number lives, the scrubber with named event markers, the policy toggle, the candidate explorer's controls, the model-and-sources dialog.

**Change:** the visual language (section 7), the game framing (section 8), and add the screens in section 5 that do not exist yet.

**Data the UI already reads** (all static JSON next to the page):

| File | Holds |
|---|---|
| `topology.json` | homes, transformers, edges with board coordinates; which lateral was shaped dense and which weak |
| `replays.json` | per scenario and policy, one record per 5-minute step: per-transformer loading, per-home voltage, per-device power and state, fleet vs base point, detector outputs |
| `candidates.json` | 911 candidate homes with score components under each scenario; hosting sweep; weights |
| `model.json` | every assumption constant with its label; provenance strings for the sources dialog |

New scenarios (comms loss, controller worker killed) will arrive as more keys in `replays.json`, with per-worker lease state and per-device rejected-command counts added to each step.

## 5. The seven beats, and what is on screen for each

This is the storyline the video follows. Each beat needs one number the viewer can read from across the room.

| # | Beat | On screen | The one number | Interaction |
|---|---|---|---|---|
| 1 | **The neighbourhood** | Heat-wave evening. Board on the Loading layer, transformers coloured by tier, the dense lateral and the weak lateral called out by name. | Highest transformer load, % of nameplate | Switch layers; scrub the evening |
| 2 | **The next battery** | Next-battery layer: every candidate home tinted by score. Click one: a panel with the value stack (market · capacity/deferral · congestion relief · voltage support) against risk (headroom consumed · voltage excursion · concentration), rank, and the λ slider. "Plan this as the next build" re-ranks neighbours downward. | Rank (e.g. "#3 of 911") and **useful capacity** ("N batteries before the first sustained violation, at ≤ X% curtailment") | Click a home; drag λ; plan a build; see a build order form |
| 3 | **The recharge** | Charging rebound. A real LZ_NORTH price series drops; the scrubber marker says "Price drops". Toggle **Even split**: a dense-lateral transformer crosses the normal tier, the weak lateral sags under 0.95 pu. Toggle **Feeder-aware**: inside limits. | Market position forgone, kW (shown, not hidden) | Policy toggle; scrub to the peak |
| 4 | **Pieces fail** *(new)* | 4a: a subset of the weak lateral loses comms. Their homes grey out with a "comms lost · stale after 180 s" badge; the base point is re-covered by neighbours; tiers stay clear. 4b: a strip of **worker cards** (each with its transformer group, lease timer, controller epoch). One is killed; its lease expires, another claims it, and a counter of "late commands rejected by devices" ticks up. | Base-point tracking error through the gap (inside max(2 MW, 15%)) and seconds to lease takeover | "Kill worker 2" button (replays the recorded run); scrub |
| 5 | **The covert channel** | Fictional compromised cohort on the dense lateral modulates a few hundred watts. Market tracking stays green. Detector layer: residual-structure and voltage-corroboration panels turn red on that lateral within N samples. "Compare automatic quarantine" branches the replay. | Time to detect (samples) and false positives on the clean fleet (0) | Quarantine compare; hover a flagged home for its residual trace |
| 6 | **Open grid data** *(new)* | One quiet panel, two findings from real ERCOT archives, each with its caveat line: the cheapest 2-hour charge window started 07:00–10:59 on 66–67 of 92 summer-2026 days (worth about $0.40 per Core per day with perfect foresight); per MW lost, ERCOT frequency dips about 2.6× less than in 2015–17 (n = 9, reporting standard changed 2022). | The two figures themselves | None needed |
| 7 | **Close** | A metrics table: useful capacity naive vs aware; % transformers below the normal tier; tracking error; kW forgone; time to detect; seconds to takeover; reserve kept. Each row carries its label. | The headline: useful capacity, naive vs aware | None |

## 6. Components

Group these however the layout wants; the list is what has to exist.

- **Header strip.** Wordmark "Hugging Base". Scenario name. Framing label "Oncor-suburb stand-in · LZ_NORTH". Optional live ERCOT frequency ticker, clearly marked "live · decoration" and safe to hide if offline.
- **Chapter rail.** Five core scenarios in dependency order: Heat-wave evening, Charging rebound, Pieces fail, Covert channel, Open grid data. (Stretch scenarios may appear greyed with "not built".)
- **Stat row.** Four to five tiles. The tile for the beat's one number is emphasised. Every tile has a one-line footer stating the limit or the label.
- **Feeder board.** SVG. Layers: Loading (three tiers), Voltage (0.95–1.05 pu band), Next battery (score tint), Detector (flagged / quarantined / clean). Legend that changes with the layer. Zoom, reset, north. Attribution bar. Named callouts for the dense lateral and the weak lateral. Space reserved for a later basemap inset.
- **Side panel.** Scenario story (timestamped narration that advances with the scrubber), the policy toggle, the primary action for the beat.
- **Transport.** Play, restart, speed, clock, scrubber with named event markers.
- **Candidate panel** (dialog or drawer). Value stack vs risk with named parts; dollars only on market ($1.58/day, DERIVED) and the $3.12–$8.50/kW·month band ($3.12 a grid-scale storage revenue benchmark, REAL; $8.50 DERIVED from the City of Austin's upper-bound estimate); everything else dimensionless. λ slider with visible weights. Rank. "Test a battery here" (charge and discharge counterfactuals). "Plan this as the next build" and the resulting build order.
- **Failure panel** *(new)*. Comms-lost badges on the board; worker cards with group, lease, epoch; rejected-command counter; a "kill worker" control that plays the recorded run.
- **Detector panels.** Per-lateral residual structure, peer-voltage corroboration, meter-vs-claim, quarantine compare. A **harm vs time-to-detect** curve replaces any "never caught" language.
- **Open grid data panel** *(new)*. Two findings, two caveats, source names.
- **Model & sources dialog.** Every constant with its label, every source with attribution, the list of deliberate substitutions (scripted load, fictional district names).
- **Metrics table** for the close.

## 7. Visual language

### Brand direction (from Base's public site, INFERENCE unless noted)

The only hard data point is Base's `theme-color` meta tag, **#1e4d2b** (RGB 30 77 43, HSL ≈ 137° 44% 21%): a deep, slightly blue-leaning forest green, closer to racing or hunter green than anything bright. Nearest print match is around Pantone 350 C (INFERENCE). The rest is read from their design language: warm off-white or cream backgrounds rather than pure white, so the green reads earthy rather than corporate; a clean grotesk sans throughout, bold weights for headlines, sentence case ("Save money. Stay powered."); a plain heavy geometric wordmark with no bolt or battery icon; press logos and badges kept monochrome so green stays the only brand colour on the page; golden-hour photography of Texas homes (INFERENCE, and not used inside the app).

We are **inspired by** this, not imitating Base: our wordmark is our own, no Base logo appears, and copy never claims to be theirs.

### Proposed tokens (superseded: use `design-handoff/design-system/tokens/`)

| Token | Value | Use |
|---|---|---|
| `--brand` | `#1e4d2b` | Wordmark, primary buttons, selection ring, active chapter |
| `--brand-hover` | `#2a6a3b` | Hover on primary |
| `--brand-tint` | `#e4efe6` | Selected rows, active toggle background |
| `--ink` | `#10231a` | Body text on cream |
| `--muted` | `#5f6b63` | Secondary text, footers, eyebrows |
| `--bg` | `#f7f4ec` | Page background (warm cream) |
| `--panel` | `#fffdf8` | Cards, dialogs |
| `--border` | `#e3dfd3` | Hairlines |
| `--board` | `#efece3` | Feeder board field; slightly darker than the page so the network reads |
| `--healthy` | `#8aa58f` | Lines and transformers inside limits (muted sage, so brand green stays reserved) |
| `--tier-1` | `#c7962b` | Over nameplate (amber) |
| `--tier-2` | `#b23a2f` | Above normal rating, sustained (the headline violation) |
| `--tier-3` | `#6e1d17` | Above emergency rating |
| `--flag` | `#b23a2f` | Detector flagged; shares the violation red on purpose |
| `--quarantine` | `#4a4f4c` | Quarantined or comms-lost: desaturated, not alarming |

Rule: **green means "ours" and "selected"; it never means "safe".** Safety is shown by the absence of amber and red, and by the sage neutral. This keeps brand green as the single brand colour the way Base's own pages do.

### Type

One grotesk sans family, two weights (regular, bold), plus a tabular-figure setting for numbers. Headlines bold, sentence case, short. Stat tiles use the largest size on screen; at 1080p video the one-number tile should be at least 40px. Labels (SOURCED, ASSUMPTION…) are small caps or a bordered tag in `--muted`, never colour-coded by severity.

### Tone

Plain language first, jargon in parentheses on first use ("transformer loading (how full the street's transformer is)"). Several teammates and some judges are new to power systems. Every claim on screen is either a number with a label or a sentence a Base engineer would not object to. Copy is confident and unhurried, like the brand's "Save money. Stay powered."

### Density

The current prototype is dense and it works for a lab feel. For the video, reduce: one primary action per screen, secondary controls on hover or one click away, and the one number large. The candidate panel can stay dense because beat 2 is the "look how much we know" beat.

## 8. Recommendations and open questions

- **Cream, not dark.** The prototype's dark board is a common operator-screen trope. We recommend the cream direction to match the brand and to keep the tiers legible in a compressed video, where dark greens muddy. If the designer wants to keep a dark field for the board only, it should be `--board` darkened, not black.
- **Drop the game framing, keep the chapters.** "Mission", difficulty pips and "decisions change the outcome" undercut the honesty the judges score. Chapters with a timestamped story and one clear next action carry the narrative without the tropes.
- **Where does the failure panel live?** Best guess: it replaces the side panel during beat 4 and the worker cards sit in the space above the transport. Open.
- **Where does the basemap inset go later?** Reserve the bottom-right of the board.
- **Stretch scenarios** (stolen-key hijack, feeder outage and restoration) may appear in the rail greyed out, or not at all. Our preference: not at all in the video build.

## 9. Glossary for the design session

- **Feeder**: the medium-voltage line from a substation that serves a neighbourhood, here about a thousand homes. Our whole world is one feeder.
- **Transformer**: the street-level box that steps voltage down for two or three homes. Rated in kVA (25 / 50 / 75). Our smallest unit of risk.
- **Tier**: how far above its nameplate a transformer is running: above 100% (counted), above 110% for a sustained window (violation), above 150% (emergency).
- **pu (per unit)**: voltage as a fraction of nominal. Homes must stay between 0.95 and 1.05. Below 0.95 is the "sag" the weak lateral shows.
- **Lateral**: a branch off the feeder. We shaped one dense (a battery on every home) and one weak (long and thin, at the far end).
- **Base point**: the power ERCOT asks the whole fleet to deliver, every five minutes. Tracking it within max(2 MW, 15%) is the market's only demand.
- **Splitter / policy**: how a fleet base point is divided among batteries. Even split vs feeder-aware.
- **Headroom**: how much more charge or discharge a transformer or feeder can take right now. The per-feeder signal we publish.
- **Useful capacity**: how many batteries can be added, in rank order, before the first sustained violation or before curtailment passes a stated share.
- **LZ_NORTH**: the ERCOT price zone we settle in, as a labelled placeholder for an Oncor suburb.
- **Reserve**: the 20% of every battery held back for the member's own backup. Never touched.
- **Comms lost**: a battery that cannot hear the cloud; it idles after 180 s (UNVERIFIED).
- **Lease / epoch**: a controller worker holds a lease on a group of transformers; every command carries the worker's epoch, a sequence number and an expiry, so a dead worker's late commands are rejected.
- **Covert channel**: compromised batteries wiggling power by a few hundred watts to signal each other through the wires; invisible to the market, visible to physics.
- **Quarantine**: exclude a flagged group from commitments and hold it at zero.
