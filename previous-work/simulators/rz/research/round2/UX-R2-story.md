# UX-R2-story: first glance and the story (round 2 design, angle "story")

Designer: "story" (first glance, the naive story told visually, story cues synced to the replay clock, attention and hierarchy).
Brief: `RZ_FEEDBACK_R2.md` (26 Sep 09:10 CDT). App: `~/hb-overnight/hb` main `0335760`.
Evidence: screenshots in `shots/r2-design-story/` (15 links: every beat link in `scripts/deeplinks.txt`, the bare `view=p1`, naive 21:45 and 22:00), taken with `scripts/smoke_ui.sh` (its own server, headless Chrome, 1920x1080), all `status=ready errors=0 fixture=0 offsite=0`. The icon set and the three story components below were rendered and checked: `shots/r2-design-story/proposal-icons-chain-caption.png` (source `proposal-icons.html`).
Every measured time and number in this file was computed from the committed `ui/data/p1/*.json` on `0335760` (commands in section 7); none is quoted from the round-1 docs.

---

## 0. The redesign in twelve lines

1. **The first open tells a story, not a state.** A bare `?view=p1` today opens feeder-aware at 22:30, where nothing is happening. It should open **naive at 21:45, paused, with a one-question intro card and one button: "Watch it happen"** (section 4.12).
2. **A three-step story chain sits top-centre over the scene**: `[price drops] -> [every battery charges at once] -> [transformers overload]`. Each step lights when the replay clock passes it, and goes dark again when you scrub back (4.1).
3. **A lower-third caption**, like TV subtitles, says in one plain sentence what just happened, with its icon and one provenance dot (4.2).
4. **Story cues come from the data, never from hard-coded times.** One pure function, `storyCues(meta, doc, branch)`, finds the moments (price peak, price drop, all charge, first overload, worst minute, all clear, charged, failures) in the committed arrays. So the same code tells the story for any real day RZ adds (7.1, 7.6).
5. **Slow at the moments that matter.** Speeds go to 0.1x, 0.25x, 0.5x, 1x, 2x and 4x, with a "1 min" step and a "next moment" jump. With **story pacing** on (the default), playback drops to 0.25x around each cue and holds for 1.2 s on it (4.7).
6. **One loud thing at a time.** Red means only "past a limit now". Batteries stop using orange (today "selling" and "overloaded" share one orange); selling becomes violet (2, 4.5, 8).
7. **The worst transformer is always findable.** When the hero's worst transformer is off-screen (T-121 at 16:00, T-240 at 16:45), an edge pointer says so and flies there on click (4.3).
8. **The NOW card speaks.** Under the one big number (kept), one generated sentence: "Every battery is charging at once. 3 transformers are past their emergency limit." Three status icons follow: price, batteries, transformers (4.4).
9. **Street A-D and T-240 become icon rows.** A transformer that fills like a container and spills over the top past 100%, one battery icon per battery (fill = charge, a badge = charging / selling / silent), and only the percentage as a number (4.5).
10. **A running money meter** in the transport shows what the fleet sold at the peak and what charging cost, at real prices. Its end value equals `money.energyValueUSD` exactly (measured: naive $893.83, aware $916.56, aware + failures $917.77) (4.7).
11. **3D story layers**: service-drop lines from each battery to its transformer light up with the flow, so "all 96 at once" and "30 at a time, rotating" read at a glance. Warning icons sit over every transformer above 110%, and a ground halo grows with the overload (8).
12. **Honesty labels become dots, with no contract change**: CSS turns `.chip` into a coloured marker, and the tooltip helper reads the label from the class and the cite from `title` (4.8, 4.9).

---

## 1. What a first-time viewer sees today (the 5-second test)

For each beat link I asked two things: where does the eye land in the first second, and what does a Base engineer who has never seen the app understand after five seconds?

| Beat (link) | Eye lands first on | Understood in 5 s | What breaks the story |
|---|---|---|---|
| `problem` naive 16:00 | the caption box (a 12-chip paragraph), then "67.1%" in green | "a 3D map of houses and green cylinders" | Nothing is happening at 16:00. The hero number is T-121, which is not on screen. Transformers (large green cylinders), batteries (small grey cylinders) and the 110%/150% discs floating in the air look like one family of objects. |
| `peak-relief` aware 16:45 | "119.5%" in orange | "something is at 119.5%" | That 119.5% is T-240, which is off-screen. A's relief, the point of the beat, is one small orange battery column that is hard to spot. |
| `backfeed` naive 20:00 | the orange cans and houses | "things are orange" | The discharging batteries are orange, the same orange as the over-110% transformers and their tinted houses, so "selling power" and "overloaded" look identical. A's gauge reads 116.7% while its bar is a short hatched stub, because the bar cannot draw power flowing backwards. |
| `rebound-naive` naive 22:30 (C3 shot) | "201.2%" in red, then the red cylinders | "A is at 201%" | This is the best frame. Still, the cause ("the price fell and every battery started at once") is only in the caption paragraph and a small red ribbon under the price line. The price collapse, the trigger, is a thin grey line. |
| `rebound-aware` aware 22:30 | the caption, then a mostly green scene | "things are green" | Rotation, the hero of feeder-aware, is invisible. You cannot see that 30 of 96 batteries charge while the rest wait their turn. |
| `faults` aware + failures 22:16 | the caption, then the "Pieces fail" list | "a list of events" | At 22:16 nothing in the scene marks the silent battery (it greys only at 22:18, when it goes stale, with a small "!"), and the list reads "now: charging". Nothing says "this battery stopped answering, and the others covered for it". |
| bare `view=p1` | "P1 · where to charge", then a green scene at 22:30 | "a dashboard" | There is no question, no call to action and no starting point. |
| P2 `insight`, `p2-controls`, `p2-flip`, `p2-capacity` | the caption box, then the charts | "rankings and histograms" | The insight "transformers peak at 16:00, prices at 18:00" needs a comparison of two separate histograms. The "existing fleet" contrast (naive 673 h above nameplate vs aware 2.0 h, `SIM screening`) is a table of chips. |
| More `money`, `plug-in` | the caption box | "a report" | It is fine as a reference page, but the money story ("how Base earns at the peak") has no visual. |

**The one-line diagnosis.** The data tells a strong three-act story: the price peaks and the batteries sell; the price collapses and every battery charges; the transformers overload. Today the screen shows a state, and the story lives in paragraphs. The fix is to give the story its own furniture: a chain, a caption, pacing, pointers and a few new 3D marks. Then the panel can hold far less text.

---

## 2. Attention rules (every component below follows them)

1. **One question per screen.** P1 asks: "96 home batteries, one cheap-power signal: what happens to the street's transformers?" P2 asks: "Where should the next battery go?"
2. **Size = importance.** One number is 48 px: the worst transformer now. Time and price are 28 px. Everything else is 15 px or smaller. No other number is larger than 18 px.
3. **Colour = meaning, exclusively.**
   - The tier ramp (green, amber, orange, red, grey) is used **only** for transformer load, and for the tint of the homes a transformer feeds.
   - Batteries use their own colours: teal `#0B6B6F` = charging, violet `#7B5CD6` = selling or discharging, slate `#7D8B99` = idle, grey with "!" = silent.
   - Money is gold `#B8860B`, as icon strokes only, never a fill.
   - Red is reserved for "past a limit now" and for the warning icon.
4. **Motion = change.** Only what changed this minute animates: a battery whose command changed pulses once, a transformer that crosses a tier pops its warning icon, and a chain step pops when it lights. Nothing loops.
5. **The story is readable without the panel.** Scene + chain + caption + transport must carry the story on their own; the panel is for detail. Acceptance test: cover the panel in a screenshot of naive 22:00 and a viewer should still say "the price fell, all the batteries charged, the transformers overloaded".
6. **Top to bottom is past to future inside a card, left to right is time on the strip.** The chain reads left to right in time order.
7. **Silence is allowed.** No caption shows when no cue is active. A calm scene is a message too.

---

## 3. P1 wireframes (1920x1080; the scene is 1480 px wide, the panel 440 px)

Glyph key for the ASCII: `[H]` house, `[B]` battery (`[B+]` charging, `[B^]` selling, `[B!]` silent), `[T]` transformer (`[T!]` over its limit), `[$]` price, `[c]` money coin, `[!]` warning, `(o)` provenance dot, `>` a play or next control.

### 3.1 First open: bare `?view=p1` (naive, 21:45, paused, intro card)

```
+--------------------------------------------------------------------------------------------+----------------------------------+
| Hugging Base   [P1 where to charge] [P2 where the next battery goes] [More]      Sun 23 Aug 2026 v   (o)REAL feeder (o)ASSUMPTION |
+--------------------------------------------------------------------------------------------+----------------------------------+
|        .-----------------------------------------------------------------.                 | [H] none  [BBB] naive(o)  [~] aware  [!] faults |
|        | [$v] Price drops  ->  [B+] Every battery charges  ->  [T!] Transformers overload |  (ghosted: not yet)                |
|        '-----------------------------------------------------------------'   [Feeder][Street][T-240]  NOW 21:45          |
|                                                                                            |   [T] 50.3%(o)   T-313 within limit |
|              .------------------------------------------------------.                     |   "Batteries are waiting. Every     |
|              |  96 home batteries. One cheap-power signal.            |                     |    transformer is within its        |
|              |  What happens to this street's transformers?           |                     |    limit."                          |
|              |                                                        |                     |   [$] $101 expensive  [B] 0/96      |
|              |  A real Texas evening (ERCOT prices, 23 Aug 2026)(o)   |                     |   [T] 0 over                        |
|              |  on a simulated neighbourhood, checked by OpenDSS      |                     |----------------------------------|
|              |  every minute (o)                                      |                     | STREET A-D  and T-240             |
|              |                                                        |                     |  [T]A  [B][B]            41%      |
|              |      [ >  Watch it happen ]    Explore on my own       |                     |  [T]B  [B][B]            35%      |
|              '------------------------------------------------------'                     |  [T]C  [B][B]            23%      |
|                         (3D street A-D, calm colours)                                      |  [T]D  [B][B][B]         22%      |
|  .------------------------------.                                                          |  [T]T-240  no battery    29%      |
|  | [H] home [B] battery [T] transformer  (?) |                                             |----------------------------------|
|  '------------------------------'                                                          | > How the evening ended           |
+--------------------------------------------------------------------------------------------+ > Money                           |
| [>]  0.1 0.25 0.5 [1] 2 4   <1m 1m>  <<moment moment>>  [x] slow at key moments  CC         | > Why one street matters          |
| 21:45   [$] $100.97/MWh expensive (o)   [c] +$1,015 sold  -$0 bought  (o)                   | > The controller's log            |
| ~~~ price line, filled, big; icon markers: [B^] 19:45  [$^] 21:00  [$v] 22:00  [T!] 22:00 ~~~ | > Grid checks                     |
| ### transformer trouble ribbon ###                                             cursor |     | > Sources and assumptions         |
+--------------------------------------------------------------------------------------------+----------------------------------+
```

The intro card is centred on the scene, 560 px wide, and dims the scene to 70% behind it. "Watch it happen" dismisses it, turns on story pacing and "follow the story", sets 1x and plays. "Explore on my own" only dismisses. The card never shows when the link carries `branch`, `t` or `beat`, so every beat link and every smoke link stays deterministic.

### 3.2 Naive at 22:00: the overload minute (`view=p1&branch=naive&t=22:00&cam=street`)

```
+--------------------------------------------------------------------------------------------+----------------------------------+
|        .-----------------------------------------------------------------------------.     | [H] none [BBB] naive(o) [~] aware [!] faults |
|        | [$v] Price drops    ->  [B+] Every battery charges  ->  [T!] Transformers overload |     |  NOW 22:00                        |
|        |  $566 -> $55 /MWh       at once: 96 of 96 (o)          14 over, 3 past 150% (o)  |     |   [T!] 197.4%(o)                  |
|        '-----------------------------------------------------------------------------'     |   A . past its emergency limit    |
|                                              [!]                   [Feeder][Street][T-240] |   "Every battery is charging at   |
|                         [!]  B 195%          |  A 197%                                     |    once. 3 transformers are past  |
|                           \                 [T!]==( halo )                                 |    their emergency limit (150%)." |
|        D 140%  [!]   [B+]--[T!]      [B+]---/  \---[B+]                                    |   [$] $55 cheap  [B+] 96/96       |
|                [T!]---[B+]                                                                 |   [T!] 14 over                    |
|               /    \                         C 181% [!]                                    |----------------------------------|
|           [B+]      [B+]                        [T!]---[B+]                                |  [T!]A  [B+][B+]        197% (o)  |
|   (every service-drop line lit teal: 96 at the same minute)                                |  [T!]B  [B+][B+]        195%      |
|  .--------------------------------------------------------------------.                   |  [T!]C  [B+][B+]        181%      |
|  | [!] 22:00  Every battery on the street starts charging in the same  |                   |  [T!]D  [B+][B+][B+]    140%      |
|  |     minute. A goes to 197%: about twice what it is rated for. (o)   |                   |  [T] T-240 no battery    24%      |
|  '--------------------------------------------------------------------'                   |----------------------------------|
+--------------------------------------------------------------------------------------------+ > How the evening ended           |
| [>] ... 22:00  [$] $55.42/MWh cheap (o)   [c] +$1,015 sold  -$0 bought  (o)                 | ...                               |
+--------------------------------------------------------------------------------------------+----------------------------------+
```

(Wireframe values are measured from `naive.json` at step 360 (22:00): A 197.4%, B 195.4%, C 180.8%, D 139.6%, T-240 23.8%; 14 transformers at tier codes 1-4, 3 at code 4. First open, step 345 (21:45): price $100.97/MWh, the worst is T-313 at 50.3%, 0 batteries charging or selling, and $1,014.74 sold so far. D has 3 batteries; A, B and C have 2 each. The builder reads every value from the data; none is typed in.)

### 3.3 Feeder-aware at 22:30: taking turns (`view=p1&branch=aware&t=22:30&cam=street`)

```
|        | [$v] Price drops    ->  [ok] Room checked first   ->  [~] Batteries take turns     |
|        |  $566 -> $55 /MWh       30 of 96 may charge (o)       D's hand off every few min  |
|  3D: only the drops of the batteries charging now are lit; the rest are dark. No warning icons.
|      A's two drops light at 22:30 (A's first grant, from the data); D's three take turns from 22:00.
|  caption: [~] 22:30  A finally has room: its first battery starts, while D's batteries keep taking turns. (o)
|  NOW: [T] 96.5% (o)  T-231 within limit.  "31 of 96 batteries are charging, taking turns. Every transformer is within its limit."
```

The chain's third step reads "Batteries take turns" (lit at the first hand-off, 22:05). It changes to **"0 battery-caused overloads all evening"** only at the `charged` cue (03:50), because that is a claim about the whole evening and cannot be made at 22:05.

### 3.4 The right panel, top to bottom (the default, collapsed state fits 1080 px with no scroll)

```
(beat bar, only with &beat: one line "1:25-2:00 The price collapse: naive rebound  [more v]  < prev  next >")
BRANCH   [H] No batteries | [BBB] Naive: all at once (o)ASSUMPTION | [~] Feeder-aware: take turns | [!] Aware + failures
NOW      [T icon filled]  197.4% (o)            <- the one big number (48 px), tier-coloured
         A . past its emergency limit           <- click: fly the camera there
         One generated sentence (15 px, ink)
         [$] $55 cheap   [B+] 96 of 96 charging   [T!] 14 over limit      <- icons, hover for detail
STREET   five icon rows: A, B, C, D, T-240 (4.5)
DETAILS  <details> sections, all closed by default except "Failures" on the aware + failures branch:
         How the evening ended . Money . Why one street matters (scale ladder) . The controller's log
         Failures (aware + failures only) . Grid checks . Sources and assumptions
LEGEND   (o) REAL  (o) SIM  (o) DERIVED  (o) ASSUMPTION    <- one line: the four markers, hover for meaning
```

---

## 4. Components (DOM + CSS), in build order

All P1 components are built by **l4-scene-p1** in `ui/panels/p1.js` and `ui/css/p1.css`. The shared pieces (`ui/lib/icons.js`, `ui/lib/tip.js`, the dot CSS in `base.css`) come from **l0-foundation** first (section 10). Class names are prefixed `p1-` as today.

### 4.1 Story chain

```html
<div class="p1-overlay p1-chain" role="list" aria-label="What happens this evening">
  <div class="chain-step" role="listitem" data-cue="drop" data-state="off" data-tip="cue">
    <span class="chain-ico"><!-- icons.price('down') --></span>
    <span class="chain-txt"><b>Price drops</b><small><!-- filled when lit: $566 -> $55 /MWh --></small></span>
  </div>
  <span class="chain-arrow" aria-hidden="true"></span>
  <div class="chain-step" data-cue="allcharge" data-state="off"> ... </div>
  <span class="chain-arrow" aria-hidden="true"></span>
  <div class="chain-step" data-cue="overload" data-state="off"> ... </div>
</div>
```

```css
.p1-chain { top: calc(var(--header-h) + 12px); left: calc((100vw - var(--panel-w)) / 2); transform: translateX(-50%);
  display: flex; align-items: center; gap: 6px; padding: 6px 8px; border-radius: 12px;
  background: color-mix(in srgb, var(--paper) 94%, transparent); border: 1px solid var(--rule); box-shadow: 0 4px 18px rgb(16 22 19 / .12); }
.chain-step { display: flex; align-items: center; gap: 8px; padding: 6px 10px; border-radius: 9px; font-size: 13px; line-height: 1.2;
  border: 1px solid var(--rule); background: var(--paper); cursor: pointer; transition: opacity .25s, background .25s; }
.chain-step .ico { width: 30px; height: 30px; }
.chain-step small { display: block; font-weight: 400; color: var(--muted); font-size: 11.5px; min-height: 14px; }
.chain-step[data-state="off"] { opacity: .35; border-style: dashed; background: transparent; }
.chain-step[data-state="bad"] { background: color-mix(in srgb, var(--crit) 13%, var(--paper)); border-color: var(--crit); color: var(--crit); }
.chain-step[data-state="ok"]  { background: color-mix(in srgb, var(--good) 13%, var(--paper)); border-color: var(--good); }
.chain-step.pop { animation: chain-pop .35s ease-out; }
@keyframes chain-pop { 50% { transform: scale(1.07); } }
.chain-arrow { width: 16px; height: 2px; background: var(--muted); position: relative; }
.chain-arrow::after { content: ""; position: absolute; right: -1px; top: -4px; border: 5px solid transparent; border-left-color: var(--muted); border-right: 0; }
@media (prefers-reduced-motion: reduce) { .chain-step.pop { animation: none; } }
```

Behaviour:
- `CHAINS[branch]` (in p1.js) lists three `{cue, icon, title}`. For each, the step is `off` before `cue.step`, and from then on `on`, `bad` or `ok` (the cue's `tone`). It is a pure function of `k`, so scrubbing back unlights it.
- The `pop` class is added only when the state changes (compare with the previous render), then removed on `animationend`.
- Clicking a step seeks to its cue step (the clock jumps, the caption shows).
- The `<small>` line is empty while off, so it never reveals a future number, and is filled with the cue's short facts when lit.

| Branch | Step 1 | Step 2 | Step 3 |
|---|---|---|---|
| none | `[H]` "No batteries" (lit at 16:00) | `[T]` amber "One home's spike puts A over its limit" (`spike`) | `[$]` "Price peak and drop: no batteries, nothing changes" (`drop`) |
| naive | `[$v]` "Price drops" (`drop`) | `[B+]` "Every battery charges at once" with an ASSUMPTION dot (`allcharge`) | `[T!]` "Transformers overload", bad (`overload`) |
| aware | `[$v]` "Price drops" (`drop`) | `[ok]` "Room checked first" (`check`) | `[~]` "Batteries take turns" (`turns`), then ok "0 battery-caused overloads all evening" (`charged`) |
| aware_faults | `[no-signal]` "A battery goes silent" (`comms_lost`) | `[EV]` "An EV plugs in" (`hot`) | `[pause]` "Our controller stalls" (`stall`); the NOW sentence carries the outcome |

### 4.2 Caption (lower third)

```html
<div class="p1-overlay p1-caption" aria-live="polite" data-tone="bad" hidden>
  <span class="cap-ico"><!-- the cue's icon --></span>
  <p><time>22:00</time> <span class="cap-txt">Every battery on the street starts charging in the same minute.</span>
     <span class="chip chip-SIM" title="OpenDSS tier counts; battery states from sim.orchestrator">SIM</span></p>
  <button type="button" class="cap-act" hidden>Now watch the same evening feeder-aware &gt;</button>
</div>
```

```css
.p1-caption { bottom: calc(var(--transport-h) + 34px); left: calc((100vw - var(--panel-w)) / 2); transform: translateX(-50%);
  max-width: 760px; display: flex; gap: 12px; align-items: center; padding: 10px 16px 10px 12px; border-radius: 12px;
  background: rgb(16 22 19 / .86); color: #fff; font-size: 18px; line-height: 1.32; box-shadow: 0 6px 24px rgb(0 0 0 / .25); }
.p1-caption .ico { width: 34px; height: 34px; flex: none; }
.p1-caption[data-tone="bad"] .cap-ico { color: #ff8a7a; } .p1-caption[data-tone="ok"] .cap-ico { color: #7ee08a; }
.p1-caption[data-tone="info"] .cap-ico { color: #9fe0da; } .p1-caption[data-tone="money"] .cap-ico { color: #f1c75b; }
.p1-caption time { font-weight: 700; color: #9fe0da; margin-right: 6px; font-variant-numeric: tabular-nums; }
.p1-caption .chip { color: #cfd8d2; }
.cap-act { margin-top: 6px; font: inherit; font-size: 14px; padding: 5px 10px; border-radius: 7px; border: 0; background: #9fe0da; color: #101613; cursor: pointer; }
body.no-captions .p1-caption { display: none; }
```

Rules:
- The active cue is the latest cue with `step <= k < min(nextCue.step, step + CAPTION_HOLD_STEPS)`, with `CAPTION_HOLD_STEPS = 20` (display only). With no active cue, the caption is hidden.
- The text is the cue's `text` (7.2 to 7.5). Its numbers are labelled values rendered with `nv()`, and it ends with one dot per distinct label used.
- A "CC" toggle in the transport hides captions for clean takes (`&cap=0`, 4.7).
- The credits line (the ODbL attribution) stays at the bottom right, shortened to "Buildings (c) OpenStreetMap contributors (ODbL) . Feeder NREL SMART-DS (CC BY 4.0) . Prices ERCOT". The full credit moves to "Sources and assumptions".

### 4.3 The worst transformer is always findable (off-screen pointer)

```html
<button class="p1-overlay p1-pointer" data-tf="240" style="left:1462px; top:420px" data-edge="right">
  <!-- icons.tf(119.5) --> T-240 . 119.5% <span class="ptr-arrow" aria-hidden="true"></span>
</button>
```
- Shown only when the worst transformer is over nameplate (tier code 1 or higher) **and** projects outside the visible scene rectangle. It is clamped to the scene edge 24 px in, and its arrow rotates to point along the bearing. Click: `scene.flyTo(lonlat)` (4.13).
- When the worst transformer is on-screen, no pointer is drawn: its warning icon (section 8) already marks it.
- Needs the scene API additions `scene.project([lon, lat, z]) -> [x, y] | null` and `scene.onViewChange(cb)` (l4 owns `scene3d.js` and `fallback2d.js`; the contract line in `docs/contracts.md` A.9 is a REQUEST to the lead).

### 4.4 NOW card and `nowSentence`

```html
<section class="p1-now" data-tone="bad" id="p1-now">
  <button class="now-big tier-4" data-tip="worst"><span class="now-ico"><!-- icons.tf(197.4) --></span>
    <span class="num">197.4%</span><span class="chip chip-SIM" title="OpenDSS loading, % of nameplate">SIM</span></button>
  <div class="now-who"><b>A</b> . past its emergency limit</div>
  <p class="now-say">Every battery is charging at once. <span class="num">3</span> transformers are past their emergency limit (150%). <span class="chip chip-SIM">SIM</span></p>
  <div class="now-icons">
    <span class="nowi" data-tip="price"><!-- icons.price('down') -->$55 <small>cheap</small></span>
    <span class="nowi" data-tip="batteries"><!-- icons.bat(.21,'C') -->96/96 <small>charging</small></span>
    <span class="nowi" data-tip="tfs"><!-- icons.tf(150) -->14 <small>over limit</small></span>
  </div>
</section>
```

```css
.p1-now { border: 1px solid var(--rule); border-radius: 12px; padding: 10px 14px 12px; background: var(--bg); }
.p1-now[data-tone="bad"] { border-color: var(--crit); }
.now-big { all: unset; cursor: pointer; display: flex; align-items: center; gap: 10px; font-size: 48px; font-weight: 700; line-height: 1; font-variant-numeric: tabular-nums; }
.now-big .ico { width: 44px; height: 44px; }
.now-who { font-size: 14px; color: var(--muted); margin: 4px 0 6px; }
.now-say { font-size: 15px; line-height: 1.35; margin: 0 0 8px; }
.now-icons { display: flex; gap: 14px; font-size: 14px; font-weight: 600; }
.nowi { display: inline-flex; align-items: center; gap: 5px; } .nowi .ico { width: 22px; height: 22px; }
.nowi small { font-weight: 400; color: var(--muted); }
```

`nowSentence(doc, k, fleetN, branch)` is pure and exported for `ui/test/p1.test.js`. It returns HTML, and every count in it goes through `nv()`, so it stays labelled.

Batteries (the first match wins; C, D and so on come from `stateCounts`):

| Condition | Sentence |
|---|---|
| `branch === 'none'` | "No batteries in this replay." |
| `C >= 0.9 * fleet` | "Every battery is charging at once." |
| `D >= 0.9 * fleet` | "Every battery is selling power back at once (the market plan)." |
| `C > 0` | "`C` of `fleet` batteries are charging, taking turns." |
| `D > 0` | "`D` battery (or batteries) pushing back to relieve a transformer." |
| `S + X > 0` | adds "`S + X` battery silent." |
| otherwise | "Batteries are waiting." |

Transformers (from `countsAt`, whose index 0 to 4 = tier codes 1 to 5):

| Condition | Sentence |
|---|---|
| `c[4] > 0` | "`c[4]` transformers' protection has opened (the fuse rule, ASSUMPTION)." |
| `c[3] > 0` | "`c[3]` transformers are past their emergency limit (150%)." |
| `c[1] + c[2] > 0` | "`c[1] + c[2]` transformers are above their normal rating (110%)." |
| `c[0] > 0` | "`c[0]` transformer is slightly over its nameplate (amber: not a failure)." |
| otherwise | "Every transformer is within its limit." |

Price word (DERIVED from REAL): `cheap` below the day's median price; `expensive` at or above `meta.plan.threshold` (2x the median, already in the data); otherwise `normal`. The tooltip gives the rule.

The relief line (today's `heroReliefHTML`) stays, rewritten as one sentence: "A's own batteries push back 6.9 kW: A reads 97.8% instead of 122.1%."

### 4.5 Street rows (A-D and T-240) with battery icons

```html
<div class="p1-rows">
  <button class="tfrow" data-tier="4" data-key="A" data-tip="row">
    <span class="tfrow-ico"><!-- icons.tf(pct) --></span>
    <span class="tfrow-name"><b>A</b><small>25 kVA . 2 homes</small></span>
    <span class="tfrow-bats"><!-- one icons.bat(soc, state) per battery on this transformer; T-240: "no battery" --></span>
    <span class="tfrow-pct tier-4">197.4%<span class="chip chip-SIM">SIM</span></span>
    <span class="tfrow-dir" data-dir="in"><!-- arrow: in = drawing from the grid, out = back-feeding --></span>
  </button>
  ...
</div>
```

```css
.tfrow { all: unset; box-sizing: border-box; width: 100%; display: grid; grid-template-columns: 40px 1fr auto auto 16px; gap: 8px; align-items: center;
  padding: 6px 8px; margin: 4px 0; border-left: 4px solid var(--good); border-radius: 6px; background: var(--paper); cursor: pointer; }
.tfrow[data-tier="1"] { border-left-color: var(--warn); } .tfrow[data-tier="2"], .tfrow[data-tier="3"] { border-left-color: var(--serious); }
.tfrow[data-tier="4"] { border-left-color: var(--crit); } .tfrow[data-tier="5"] { border-left-color: var(--open); }
.tfrow-ico .ico { width: 36px; height: 36px; } .tfrow-bats { display: flex; gap: 2px; } .tfrow-bats .ico { width: 24px; height: 24px; }
.tfrow-name small { display: block; color: var(--muted); font-size: 11.5px; font-weight: 400; }
.tfrow-pct { font-size: 20px; font-weight: 700; font-variant-numeric: tabular-nums; }
```

- The transformer icon fills with `|loading|` up to 100% and spills a solid cap above the box past 100% (the cap height is proportional to the overload, capped at 200%). This is the container metaphor: full = at its limit, spilling = overloaded. It covers back-feed too: the arrow on the right shows the direction (`out` while `homeKW + batKW < 0`). That fixes today's 116.7%-with-a-stub-bar confusion at 20:00.
- Battery icons: fill = SoC, colour = state (teal charging, violet selling, slate idle, grey + "!" silent), and a badge glyph (bolt, up-arrow, "!"). They come from `doc.soc[k][j]` and `doc.state[k][j]` for the fleet indices on this transformer.
- Visible numbers: the percentage only. Home kW, battery kW, room, evening max, minutes above 110% and 150% and the fuse rule all move to the row's hover tooltip (6), with their labels.
- Click: fly the camera to that transformer, and outline it (a `highlightTf` field in the scene model).

### 4.6 Branch pictograms (the toggle tells the story)

```html
<div class="hb-seg p1-branches p1-branch-pics" role="tablist">
  <a data-branch="none"><!-- icons.house --><span>No batteries</span></a>
  <a data-branch="naive"><!-- three icons.bat(.5,'C') --><span>Naive: all at once</span><span class="chip chip-ASSUMPTION" title="...NAIVE_FRAMING...">ASSUMPTION</span></a>
  <a data-branch="aware"><!-- icons.turns --><span>Feeder-aware: take turns</span></a>
  <a data-branch="aware_faults"><!-- icons.warn --><span>Aware + failures</span></a>
</div>
```

It keeps the existing hrefs and click handler. Each option is a 2x2 grid cell at 440 px: an icon above and two words below. The naive framing moves out of the always-visible `p1-framing` paragraph into the ASSUMPTION dot's tooltip and the "Sources and assumptions" section. The naive option always shows its dot, per build prompt 3.4.

### 4.7 Transport: speeds, step, moments, pacing, captions, money

```html
<div class="p1-overlay p1-transport">
  <button class="p1-play" aria-label="play"></button>
  <div class="p1-speeds hb-seg" role="radiogroup" aria-label="speed">
    <button data-speed="0.1">0.1x</button><button data-speed="0.25">0.25x</button><button data-speed="0.5">0.5x</button>
    <button data-speed="1" aria-checked="true">1x</button><button data-speed="2">2x</button><button data-speed="4">4x</button>
  </div>
  <div class="p1-steps"><button data-step="-1" title="back 1 minute (Left; Shift = 10)">&lt; 1 min</button><button data-step="1">1 min &gt;</button>
    <button data-moment="-1" title="previous moment ([)">&lt;&lt;</button><button data-moment="1" title="next moment (])">&gt;&gt;</button></div>
  <label class="p1-pace"><input type="checkbox" checked> slow at key moments</label>
  <button class="p1-cc" aria-pressed="true" title="captions">CC</button>
  <div class="p1-clock"><div class="p1-time">22:00</div><div class="p1-price"><!-- icons.price --> $55.42/MWh <small>cheap</small> (o)</div></div>
  <div class="p1-money" data-tip="money"><!-- icons.money --> <b>+$1,015</b> sold . <b>-$0</b> bought (o)</div>
  <div class="p1-strip-wrap"> (canvas strip + icon markers) </div>
</div>
```

- `SPEEDS = [0.1, 0.25, 0.5, 1, 2, 4]`. The 8x option goes, because a whole evening at 4x is already 18 s. At 1x one simulated minute takes 100 ms (unchanged), so 0.1x = 1 s per simulated minute and the 60 minutes after the onset take 60 s. `&speed=` sets it from a link (a REQUEST: `data.parseLink` is L0's).
- Step: the "< 1 min" and "1 min >" buttons, and the existing Left/Right keys. Moments: "<<" and ">>" (keys `[` and `]`) seek to the previous or next cue.
- **Story pacing** (default on, `&pace=0` turns it off): in `tick()`, when playing and `cue.step - 2 <= k <= cue.step + 6` for any major cue (a cue with `chain` set, or tone `bad`), the effective speed is `min(speed, 0.25)`. On reaching `cue.step` the clock holds for `PACE_HOLD_MS = 1200` ms of real time, once per cue per play session. At 1x with pacing on, the whole evening plays in about 100 s instead of 72 s, and every story moment gets about 4.5 s on screen.
- **Money meter**: `moneyRunning(meta, doc)` is pure and computed once per branch doc. It returns cumulative `sold[k]` and `bought[k]` in dollars: `sold += max(0, -P) * price * dt`, `bought += max(0, P) * price * dt`, with P = the sum of `batKW[k]` in kW, `dt = stepSeconds / 3600` h and price in $/MWh divided by 1000. The label is DERIVED, cite "REAL ERCOT LZ_NORTH price x SIM battery kW; gross energy value, not Base's P&L". Measured end values on `0335760`:

  | Branch | Sold | Bought | Net | `money.energyValueUSD` |
  |---|---|---|---|---|
  | naive | $1,014.74 | $120.91 | $893.83 | $893.83 |
  | aware | $1,001.11 | $84.55 | $916.56 | $916.56 |
  | aware + failures | $1,001.11 | $83.34 | $917.77 | $917.77 |

  A test asserts the net equals `energyValueUSD` to the cent (11). This is RZ's "how Base makes money during peak hours", told on the clock: the coin counter climbs at the 19:45 to 21:30 peak and barely moves at the 22:00 charge.
- **Price strip**:
  - The price line becomes 2.5 px with a 12%-alpha area fill.
  - The y-axis gets two gridlines ($100 and the day's max).
  - The strip is 30 px taller (`--transport-h: 152px`).
  - The text marker labels become 18 px icon buttons in one row above the line, one per cue (7). Hovering a marker shows its text in the tooltip, and clicking seeks.
  - The tier ribbon is labelled at its left end "transformer trouble" and grows to 14 px.
  - The discharge-plan bands stay.

```css
.p1-speeds button { font: inherit; font-size: 12.5px; padding: 4px 7px; border: 1px solid var(--rule); background: var(--paper); color: var(--ink); cursor: pointer; }
.p1-speeds button[aria-checked="true"] { background: var(--accent); color: var(--paper); border-color: var(--accent); }
.p1-money { font-size: 14px; white-space: nowrap; } .p1-money .ico { width: 20px; height: 20px; color: #B8860B; vertical-align: -4px; }
.p1-strip-marks .mark { height: 22px; width: 22px; transform: translateX(-11px); }
.p1-strip-marks .mark .ico { width: 18px; height: 18px; }
```

### 4.8 Honesty labels as compact markers, with no contract change

`format.js` `chip()` (L0) keeps its exact markup (`<span class="chip chip-SIM" title="...">SIM</span>`), because `ui/test/p2.test.js` `unscreenedChips` matches that string. The dot is pure CSS, in `base.css` (L0), under a body class the shell sets on P1 and P2:

```css
body.pv-dots .chip { font-size: 0; width: 9px; height: 9px; padding: 0; margin: 0 1px 0 4px; border: 0; vertical-align: 1px; line-height: 0; cursor: help; }
body.pv-dots .chip-REAL       { background: var(--real); border-radius: 50%; }                                   /* filled circle */
body.pv-dots .chip-SIM        { background: transparent; border: 2px solid var(--sim); border-radius: 50%; }      /* ring */
body.pv-dots .chip-DERIVED    { background: var(--derived); transform: rotate(45deg) scale(.82); border-radius: 1px; } /* diamond */
body.pv-dots .chip-ASSUMPTION { background: transparent; border: 2px solid var(--assumption); border-radius: 2px; } /* hollow square */
```

- The shape plus the colour keeps the four labels distinct for colour-blind viewers.
- The panel's last line is a legend of the four markers.
- The tooltip helper (4.9) turns hover and focus on `.chip` into "SIM: simulated by our model, checked by OpenDSS . <cite>".
- The screening chip (`.p2-badge.screen`) becomes a dashed ring in `p2.css` (l5).
- The FIXTURE banner is unchanged.

### 4.9 Tooltip helper (`ui/lib/tip.js`, l0)

```js
// one floating tooltip for the whole page; hover, focus and deck.gl hover all use it
export function installTips(root = document, registry = {}) -> { show(html, x, y), hide() }
//   delegated pointerover/pointerout/focusin/focusout on [data-tip] and .chip
//   [data-tip="key"] -> registry[key](el) returns HTML (p1 and p2 register their dynamic ones)
//   .chip -> LABEL_MEANING[label] + ' . ' + cite; on first hover it moves title -> data-cite (no double native tooltip)
//   positions 12 px right and below the pointer, flips at the viewport edges, max-width 320 px, and hides on scroll or Escape
```
```css
.hb-tip { position: fixed; z-index: 40; max-width: 320px; padding: 8px 10px; border-radius: 8px; background: var(--ink); color: var(--paper);
  font-size: 12.5px; line-height: 1.4; pointer-events: none; box-shadow: 0 6px 20px rgb(0 0 0 / .22); }
.hb-tip b { font-weight: 700; } .hb-tip .chip { filter: brightness(1.4); }
```

deck.gl hover: `scene.onHover(cb)`, a new scene API. `scene3d.js` passes deck's `onHover` `{layer, object, x, y}`, and p1 builds the HTML (6) and calls `tip.show`. `fallback2d.js` does a nearest-object hit test on `pointermove` with the same callback. Hover replaces the "Selected" panel section. Click still picks, and the pick now flies the camera.

### 4.10 Legend (bottom-left, icons first)

```html
<div class="p1-overlay p1-legend2">
  <span data-tip="legend-home"><!-- icons.house --> home</span>
  <span data-tip="legend-bat"><!-- icons.bat(.6,'C') --> battery</span>
  <span data-tip="legend-tf"><!-- icons.tf(60) --> transformer</span>
  <span class="lg-ramp" data-tip="legend-tier"><i style="background:var(--good)"></i><i style="background:var(--warn)"></i><i style="background:var(--serious)"></i><i style="background:var(--crit)"></i><i style="background:var(--open)"></i> load</span>
</div>
```
One line, `bottom: calc(var(--transport-h) + 12px); left: 12px`. Each item's tooltip holds today's legend text, split per object. The 290 px text legend at the top left is deleted, which frees the top left of the scene.

### 4.11 Collapsible sections

Native `<details class="p1-more"><summary>`. Open state is remembered per section in `localStorage` (inside try/catch; everything renders the same without it).

| Section | Holds |
|---|---|
| How the evening ended | the claim line, the branch summary and relief |
| Money | the meter's sold, bought and net, then `moneyHTML` |
| Why one street matters | the scale ladder |
| The controller's log | the ticker, 6 lines |
| Failures | aware + failures only, open by default there |
| Grid checks | `gridCheckHTML` |
| Sources and assumptions | controller view, naive framing, sources, full credits |

`summary` style: 14 px, 600 weight, a chevron that rotates, and a one-line teaser on the right in muted text (for example "Money . $894 net"). The teaser is a labelled value with its dot.

### 4.12 Intro card (first open only)

```html
<div class="p1-intro" role="dialog" aria-labelledby="p1-intro-h">
  <h2 id="p1-intro-h">96 home batteries. One cheap-power signal.<br>What happens to this street's transformers?</h2>
  <p>A real Texas evening (ERCOT LZ_NORTH prices, 23 Aug 2026) <span class="chip chip-REAL">REAL</span> on a simulated
     neighbourhood feeder, checked by OpenDSS every minute <span class="chip chip-SIM">SIM</span>.</p>
  <div class="intro-chain"><!-- the naive chain, all three steps ghosted --></div>
  <button class="intro-go">&gt; Watch it happen</button> <button class="intro-skip">Explore on my own</button>
</div>
```
- The date and the fleet size come from `meta.day` and `topology.fleet.length`.
- The card shows only when `link.bare` is true: no `branch`, `t` or `beat` in the query (a REQUEST: `parseLink` must say so).
- "Watch it happen" sets branch naive, seeks to `drop.step - 15`, turns on pacing and follow, and plays at 1x.
- At the naive `clear` cue the caption shows its action button, "Now watch the same evening feeder-aware >". It switches to aware, seeks to `drop.step - 5` and plays. That is the problem-to-solution loop in two clicks.

### 4.13 Follow the story (camera)

There is a fourth camera button, "Follow", `aria-pressed`, default off (on after "Watch it happen"). While it is on, a cue with a `focusTf` flies the camera to that transformer at street zoom (`scene.flyTo(lonlat, {zoom: 18.3, pitch: 55})`, 1,400 ms). A user drag turns follow off, so the camera never fights the user.

---

## 5. Icon set (`ui/lib/icons.js`, l0, shared by P1, P2 and More)

`currentColor` strokes on a 24x24 viewBox, so one SVG serves the DOM (`innerHTML`) and deck.gl (`IconLayer` with `mask: true`, tinted by `getColor`). `icons.dataURL(svg)` = `'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg)`: no network, so `data-offsite` stays 0. The builder must still re-check that flag in the smoke run, because Chrome does not add data: URLs to resource timing. Rendered and checked: `shots/r2-design-story/proposal-icons-chain-caption.png`.

```js
// ui/lib/icons.js (L0): the shared icon set. Pure strings; no DOM at import time (node-testable).
const S = (body) => `<svg viewBox="0 0 24 24" class="ico" aria-hidden="true" focusable="false">${body}</svg>`;
const st = 'fill="none" stroke="currentColor" stroke-width="1.8"';
export const house = S(`<path d="M3 11.2 12 3.8l9 7.4" ${st} stroke-linejoin="round" stroke-linecap="round"/><path d="M5.6 9.6v10.4h12.8V9.6" ${st} stroke-linejoin="round"/><path d="M10.2 20v-5h3.6v5" fill="none" stroke="currentColor" stroke-width="1.6"/>`);
/** battery cabinet: soc 0..1 = fill; state C (charging, bolt badge), D (selling, up-arrow badge), S/X (silent, "!" badge), else none */
export function bat(soc = 0.6, state = '') {
  const h = 13.6 * Math.max(0, Math.min(1, soc)), y = 19.4 - h;
  const g = { C: '<path d="M18.9 15.4 16.9 18.7h2.4l-1.3 2.4" fill="none" stroke="#fff" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>',
              D: '<path d="M18.2 21V16M16.3 17.8l1.9-1.9 1.9 1.9" fill="none" stroke="#fff" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>',
              S: '<path d="M18.2 15.9v2.8" stroke="#fff" stroke-width="1.6" stroke-linecap="round"/><circle cx="18.2" cy="20.6" r=".95" fill="#fff"/>' };
  const badge = g[state === 'X' ? 'S' : state] ? `<circle cx="18.2" cy="18.4" r="4.6" fill="currentColor" stroke="var(--paper,#fff)" stroke-width="1.4"/>${g[state === 'X' ? 'S' : state]}` : '';
  return S(`<rect x="4.4" y="3.6" width="12" height="18" rx="2.2" ${st}/><rect x="8" y="1.6" width="4.8" height="2.2" rx=".7" fill="currentColor"/>`
    + `<rect x="6.6" y="${y.toFixed(2)}" width="7.6" height="${h.toFixed(2)}" rx=".8" fill="currentColor" opacity=".85"/>`
    + `<path d="M5.6 16.7h1.2M14 16.7h1.2" stroke="currentColor" stroke-width="1"/>${badge}`);   // the tick = the 20% reserve
}
/** pad-mount transformer: pct = loading; fills to 100%, then a solid cap spills over the top (height ~ overload, capped at 200%) */
export function tf(pct = 60) {
  const f = Math.max(0, Math.min(pct, 100)) / 100, h = 10.2 * f, y = 19.1 - h, oh = Math.min(5.4, 5.4 * (pct - 100) / 100);
  return S(`<path d="M8 7.8V5M12 7.8V3.8M16 7.8V5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>`
    + `<rect x="5" y="${y.toFixed(2)}" width="14" height="${h.toFixed(2)}" rx=".6" fill="currentColor" opacity=".32"/>`
    + (pct > 100 ? `<rect x="5" y="${(7.8 - oh).toFixed(2)}" width="14" height="${(oh + 1.4).toFixed(2)}" rx="1" fill="currentColor"/>` : '')
    + `<rect x="3.6" y="7.8" width="16.8" height="12.6" rx="1.3" ${st}/><path d="M12.9 11.2 10.7 14.4h2.4l-1.8 3" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>`);
}
export function price(dir = '') {   // '' | 'down' | 'up'
  const a = dir === 'down' ? '<path d="M14.6 9.2v6.2M12.3 13.1l2.3 2.3 2.3-2.3" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>'
    : dir === 'up' ? '<path d="M14.6 15.4V9.2M12.3 11.5l2.3-2.3 2.3 2.3" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>' : '';
  return S(`<path d="M3.4 11.8V4.4a1 1 0 0 1 1-1h7.4l8.1 8.1a1.4 1.4 0 0 1 0 2l-6.4 6.4a1.4 1.4 0 0 1-2 0z" ${st} stroke-linejoin="round"/><circle cx="7.8" cy="7.8" r="1.5" fill="currentColor"/>${a}`);
}
export const money = S(`<circle cx="12" cy="12" r="9" ${st}/><path d="M14.9 8.9c-.5-1-1.6-1.6-2.9-1.6-1.6 0-2.8.9-2.8 2.2 0 3 5.8 1.6 5.8 4.6 0 1.3-1.3 2.3-3 2.3-1.4 0-2.6-.7-3-1.8M12 5.6v1.7M12 16.4v2" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>`);
export const warn = S(`<path d="M12 3.4 21.6 20.2H2.4z" ${st} stroke-linejoin="round"/><path d="M12 9.4v5.1" stroke="currentColor" stroke-width="2.1" stroke-linecap="round"/><circle cx="12" cy="17.3" r="1.25" fill="currentColor"/>`);
export const check = S(`<circle cx="12" cy="12" r="9" ${st}/><path d="M7.8 12.3l2.8 2.8 5.6-5.8" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>`);
export const turns = S(`<path d="M19.5 9.5A8 8 0 0 0 5.2 7.4M4.5 14.5a8 8 0 0 0 14.3 2.1" ${st} stroke-linecap="round"/><path d="M4.6 3.8v3.9h3.9M19.4 20.2v-3.9h-3.9" ${st} stroke-linecap="round" stroke-linejoin="round"/>`);
export const nosignal = S(`<path d="M4 9.6a11.5 11.5 0 0 1 16 0M7 12.8a7.2 7.2 0 0 1 10 0M10 16a3 3 0 0 1 4 0" ${st} stroke-linecap="round"/><circle cx="12" cy="19" r="1.2" fill="currentColor"/><path d="M4 4l16 16" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/>`);
export const ev = S(`<path d="M4 15.5l1.6-4.8a2 2 0 0 1 1.9-1.4h9a2 2 0 0 1 1.9 1.4l1.6 4.8v3H4z" ${st} stroke-linejoin="round"/><circle cx="7.5" cy="18.5" r="1.4" fill="currentColor"/><circle cx="16.5" cy="18.5" r="1.4" fill="currentColor"/><path d="M12.8 2.8 10.9 5.9h2.2L11.4 8.6" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>`);
export const pause = S(`<circle cx="12" cy="12" r="9" ${st}/><path d="M9.7 8.4v7.2M14.3 8.4v7.2" stroke="currentColor" stroke-width="2.1" stroke-linecap="round"/>`);
export const fuse = S(`<path d="M2.5 12h5M16.5 12h5" ${st} stroke-linecap="round"/><rect x="7.5" y="8.5" width="9" height="7" rx="1.5" ${st}/><path d="M9.5 13.8l2-3.6 1 1.6 2-2.4" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>`);
export const bolt = S(`<path d="M13.5 2.8 6.5 13.4h5l-1.6 7.8 7.6-11h-5.2z" fill="currentColor"/>`);
export const dataURL = (svg) => 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg.replace('class="ico" ', 'width="64" height="64" '));
```

Colours (CSS tokens added to `base.css`, light and dark):

| Token | Light | Dark | Used for |
|---|---|---|---|
| `--bat-charge` | = `--accent` `#0B6B6F` | `#5CC4BE` | charging |
| `--bat-sell` | `#7B5CD6` | `#A994F0` | selling or discharging (was orange) |
| `--bat-idle` | `#7D8B99` | `#93A1AE` | idle |
| `--money` | `#B8860B` | `#E0B24A` | money |
| `--house` | `#B9774E` | `#D39A72` | house icon |
| `--tf-body` | `#3F6B4A` | `#6FA27B` | pad-mount green, icon at tier 0 |

---

## 6. Tooltip copy (hover or focus; `[x]` = a live labelled value)

| Object | Tooltip (first line bold) |
|---|---|
| House (3D, legend) | **Home 0212** . on transformer **A** (25 kVA) . has a battery. "Its colour is its transformer's state now: green within limit, amber over nameplate, orange above its rating, red past emergency." |
| Battery (3D, icon) | **Battery at Home 0212** . **charging +20.0 kW** (o) . charge **47%** (o). "The dark tick is the 20% reserve Base keeps for backup (REAL). Teal = charging, violet = selling, slate = waiting, grey ! = not answering." |
| Transformer (3D, row, legend) | **Transformer A** . 25 kVA pad-mount . 2 homes, 2 batteries. **Now 197.4% of its rating** (o) (past emergency). "It fills like a box: full = its nameplate limit; the cap spilling over the top is the overload." Then: home load [x] kW . batteries [x] kW . room to its limit [x] kW (DERIVED) . tonight's max [x] at [t] . minutes above 110% [x], above 150% [x] . fuse rule: opens at 200% for 10 min (ASSUMPTION). |
| Transformer warning icon | **Past a limit now.** "Above 110% of nameplate is past its normal rating; above 150% is past its emergency rating (SMART-DS ratings, REAL). Heat, not an instant failure; the fuse rule is our ASSUMPTION." |
| Ground halo | **How far over.** "The ring grows with the overload: at 200% it is twice the transformer's own radius." |
| Service-drop line | **Power flow, battery to transformer**: [x] kW "charging (teal) or selling (violet); thicker = more power." |
| Price (clock, NOW, strip) | **$55.42/MWh at 22:00** (o REAL, ERCOT LZ_NORTH real-time, the 15-min interval containing this minute). "Cheap = below the day's median; expensive = at least twice the median ($74.43, DERIVED)." |
| Money meter | **Gross energy value so far: $894** (o DERIVED). "Sold at the peak: $1,015; bought to recharge: $121, at real prices. Not Base's profit: no fees, losses, customer share or battery wear. Local relief is not priced (no sourced price exists)." |
| Chain step | the cue's full text and time, and "click to jump here". |
| Strip marker | the cue's time, icon and full text. |
| Off-screen pointer | **The worst transformer now is T-240**, off-screen, "click to fly there." |
| Provenance dot | **REAL**: from a public source (ERCOT prices, SMART-DS feeder data, OSM, sourced programme facts). **SIM**: our simulation's output, checked by OpenDSS. **DERIVED**: arithmetic on REAL or SIM numbers (dollars, shares). **ASSUMPTION**: a constant we chose; the cite names it. Then " . " + the cite. |
| Branch "naive" dot | the full `NAIVE_FRAMING`, ending "Base may not charge this way today." |
| Speed "slow at key moments" | "Slows to 0.25x around each story moment and pauses 1.2 s on it. Turn off for an even replay." |

---

## 7. Story cue engine and the scripts

### 7.1 `storyCues(meta, doc, branch, topology)` (pure, in `ui/panels/p1.js`, node-tested)

It returns `[{id, step, t, tone: 'info'|'bad'|'ok'|'money', icon, chain: 0|1|2|null, text(fmt) -> html, short(fmt) -> html, focusTf|null}]`, sorted by step. Every rule reads the committed arrays. **A rule that does not fire emits nothing, and there are no default times.**

| id | Rule (k = step) | Uses |
|---|---|---|
| `spike` | first k before the first plan discharge where the transformers at tier codes 1-4 (`counts[k][0..3]`) number more than 0; `focusTf` = the worst | `counts`, `loading`, `meta.relief.driver` / `meta.unrelieved[].driver` |
| `relief` | aware branches: `meta.relief.reliefKW.step` | `meta.relief` |
| `sell` | first k with `D >= 0.9 * fleet` | `state` |
| `backfeed` | first k at or after `sell` with `D >= 0.9 * fleet` and at least 1 transformer at codes 1-4; `focusTf` = the worst | `state`, `counts`, `loading` |
| `peak` | argmax of `meta.price` | `price` (REAL), money meter at k (DERIVED) |
| `drop` | `meta.plan.onset` (the D-26 onset, DERIVED) | `plan.onsetPrice` (REAL) |
| `allcharge` | naive: first k at or after the onset with `C >= 0.9 * fleet` | `state` |
| `check` | aware branches: first k at or after the onset with `C > 0` | `state`, `fleet` |
| `turns` | aware branches: first ticker line at or after the onset containing "hands off" | `ticker` (SIM) |
| `firstgrant:<key>` | aware branches, per A-D key: first k at or after the onset with `focus[key].batKW[k] > 0` (the beats' `chargeOrder`) | `focus` |
| `overload` | first k at or after the onset with transformers at codes 1-4 > 0; `focusTf` = the worst | `counts`, `loading` |
| `worst` | argmax over k at or after the onset of `max(loading[k])` if it is over 1000 (100%) | `loading` |
| `clear` | first k after `overload` with no transformer at codes 1-4 | `counts` |
| `charged` | first k after the onset with mean SoC >= 99% | `soc`, `summary.chargedPctBy0400` |
| `comms_lost`, `hot`, `stall` | `meta.events[branch]`, at `e.step` | events (ASSUMPTION times, SIM outcomes) |

Words for ratios (DERIVED): at 1.9 to 2.1x of nameplate, "about twice what it is rated for"; at 1.4 to 1.6x, "about one and a half times"; otherwise the percentage alone.

### 7.2 Naive script (the times are what the rules return on the committed data)

| Measured | id | Chain | 3D cue | Caption (numbers are labelled values from the data) |
|---|---|---|---|---|
| 16:38 | `spike` | none | A's can turns amber, halo; follow flies to A | "One home on A starts a big load (a 15-minute spike, `22.7 kW` SIM): A goes over its nameplate. No battery helps in this branch." |
| 19:45 | `sell` | none | all 96 drops turn violet; the coin meter starts climbing | "Power is expensive (`$380.73/MWh` REAL). The market plan sells: all `96` batteries send power back at once. (o ASSUMPTION: no feeder check)" |
| 19:45 | `backfeed` | none | warning icons over C, and over A and B when over; follow to C | "Sending that much back at once overloads `C` in reverse: `132.5%` (SIM). Back-feed is an overload too." |
| 21:00 | `peak` | none | coin pulse | "The price peaks at `$566.42/MWh` (REAL). The fleet has sold `$535.29` of energy so far tonight (DERIVED, gross; the meter at 21:00)." |
| 22:00 | `drop` | step 1 | the price marker pops | "The price falls to `$55.42/MWh` (REAL), about a tenth of the peak an hour earlier. That is the charge signal." (The "about a tenth" phrase comes from the ratio, `55.42 / 566.42 = 0.098`, DERIVED. Bands: under 0.15 "about a tenth", 0.15-0.35 "about a quarter", 0.35-0.65 "about half"; otherwise no phrase.) |
| 22:00 | `allcharge` | step 2 | all 96 drops turn teal in the same frame; one pulse on every cabinet | "Every battery on the street starts charging in the same minute (`96` of `96`, SIM; the naive rule, o ASSUMPTION)." |
| 22:00 | `overload` | step 3 (bad) | warning icons pop over 14 cans; halos; follow to A | "`14` transformers go over their limit at once; `3` pass the emergency rating (SIM, OpenDSS). A reaches `197.4%`: about twice what it is rated for." |
| 22:30 | `worst` | none | A's halo at its widest | "A peaks at `201.2%` (SIM). Past 110% for 30 minutes counts as a normal-rating violation: `11` of them tonight." |
| 23:32 / 23:34 | `charged`, `clear` | none | drops go dark; warnings drop | "Batteries full; every transformer back under its limit. Tonight's cost to the street: `11` normal-rating events and `3` transformers past emergency, all caused by batteries (SIM)." The action button: "Now watch the same evening feeder-aware >". |

(When `charged` and `clear` are 1-2 steps apart, the caption merges them; the rule is "cues within 3 steps share one caption", and the later text wins.)

### 7.3 Feeder-aware script

| Measured | id | Chain | 3D cue | Caption |
|---|---|---|---|---|
| 16:39 | `spike` | none | pointer to T-240 (off-screen at the street camera) | "T-240 goes over its nameplate from one home's spike (`22.7 kW` SIM). T-240 has no battery: P2 asks where the next one should go." |
| 16:46 | `relief` | none | A's two drops turn violet (thin), A's halo shrinks | "A's own batteries push back `6.9 kW` (SIM): A reads `97.8%` instead of `122.1%` with no batteries." |
| 19:45 | `sell` | none | 96 drops violet, capped | "The market plan sells, but each transformer only sends back what it has room for: nothing overloads in reverse (worst `95.8%` SIM, the highest loading on the feeder while the fleet sells)." |
| 21:00 | `peak` | none | coin pulse | as naive |
| 22:00 | `drop` | step 1 | price marker | as naive |
| 22:00 | `check` | step 2 | only 30 drops light | "Before any charge goes out, the controller checks each transformer's room. `30` of `96` batteries may charge now (SIM)." |
| 22:00 | `firstgrant:D` | none | D's drops light | "D has room first: its batteries take turns (the controller's log names every grant)." |
| 22:05 | `turns` | step 3 (on) | a D drop goes dark as another lights | "Turns: when a battery's dwell is over, the next lowest-charged battery on the same transformer takes its place." |
| 22:30 | `firstgrant:A` | none | A's first drop lights | "A had little room until now (its homes were busy). Its first battery starts at `22:30`." |
| 22:55 / 23:05 | `firstgrant:B`, `firstgrant:C` | none | drops light | "B's turn." / "C's turn." |
| 03:50 | `charged` | step 3 (ok) | all drops dark | "Charged `100%` by 04:00 (SIM), and `0` battery-caused overloads all evening. Taking turns bought power later, when it was cheaper: `$22.73` more energy value than naive (DERIVED, gross)." |

### 7.4 Aware + failures script (adds to 7.3; chain = the three failures)

| Measured | id | 3D cue | Caption |
|---|---|---|---|
| 22:15 | `comms_lost` | a no-signal icon over Home 0222's cabinet; its drop goes dashed grey | "The battery at Home 0222 (behind D) stops answering while holding a `+19.0 kW` command (ASSUMPTION timing). The controller marks it stale at `22:18`; its command expires at `22:20` and it goes idle, backup armed; at `22:20` Home 0593 and Home 0934 on the same transformer take up its share (SIM)." (The times come from the event's `staleStep`, `expiredStep`, `coveredStep` and `coveredBy`.) |
| 22:35 | `hot` | an EV icon at Home 0427, C's halo | "Home 0427 plugs in an EV: `+7.2 kW` for `60 min` on C (ASSUMPTION). The controller sees less room on C and sends less." |
| 22:55 | `stall` | a pause icon on the chain; drops go dark one by one as commands expire | "Our controller stalls for `8 min`. Every battery's command expires on schedule (300 s), so they stop and wait safely." |
| 23:03 | resume (first `C > 0` after the stall) | drops relight | "The controller is back; charging resumes where there is room." |

### 7.5 No-batteries script

| Measured | id | Caption |
|---|---|---|
| 16:38 | `spike` | "One home's spike puts A over its nameplate for `17 min` (SIM). Amber: not a failure." |
| 21:00 | `peak` | "The price peaks at `$566.42/MWh`. With no batteries, nothing on the street reacts." |
| 22:00 | `drop` | "The price falls to `$55.42/MWh`. No batteries, so nothing charges: every transformer stays within its limit." |

### 7.6 Other real days (RZ's ask 3)

- `storyCues` reads only the branch doc and meta, so a day built by l2 (the `&date=YYYY-MM-DD` layout from HIST-R2.md) gets its own chain and captions with no UI change.
- When a rule does not fire (for example a day with no price spike, so no `sell` cue), its chain step stays ghosted with the tooltip "did not happen on this day". That is honest, and it is itself a story ("on a flat-price day there is no rebound").
- The intro card's date and the header date picker come from `meta.day`.
- The money meter per day answers "how does Base make money during peak hours". The More tab gets a per-day bar row, sold vs bought vs net (l5, from each day's meta).

### 7.7 How the times above were measured

On `0335760`, a Python pass over `ui/data/p1/{none,naive,aware,aware_faults}.json` and `meta.json` applied the rules of 7.1 (the same thresholds). Its output, per branch:

| Branch | Cues |
|---|---|
| naive | `spike` 16:38 (A 101.7%), `sell` and `backfeed` 19:45 (C 132.5%, 3 transformers over), `peak` 21:00 ($566.42), `drop`, `allcharge` and `overload` 22:00 (96 charging; 14 over, 3 in emergency; A 197.4%), `worst` 22:30 (A 201.2%), `charged` 23:32, `clear` 23:34 |
| aware | `spike` 16:39 (T-240 102.0%), `sell` 19:45, `peak` 21:00, `drop` and `check` 22:00 (30 of 96), first grants D 22:00, A 22:30, B 22:55, C 23:05; no `overload`; `charged` 03:50 |
| aware_faults | as aware, with B 23:03 and C 23:13, plus events 22:15, 22:35 and 22:55, resume 23:03, `charged` 03:56 |
| none | `spike` 16:38, `peak`, `drop`; nothing else fires |

While the fleet sells (73 steps, 19:45-21:29), the highest loading anywhere on the feeder is 95.8% on aware and 139.7% on naive. The builder's node test re-derives all of this from the files. These numbers are for review only and must not be copied into code.

---

## 8. deck.gl layer changes (the story layers; the house, transformer and cabinet models are the "scene" designer's)

All of these are data arrays built in `scene-model.js` (pure, node-tested) and drawn in `scene3d.js`; `fallback2d.js` draws a 2D equivalent. Owner: l4-scene-p1.

| New or changed layer | Type | Data (scene model) | Encoding | 2D fallback |
|---|---|---|---|---|
| `drops` (new) | `LineLayer` (or `PathLayer`, width in pixels) | `drops[96] {j, from: batteryPos[j] at z=1.5, to: can lonlat at z=CAN_H_M*0.6, kw, color}` | Hidden at 0 kW; width 1.5 + 3.5 x \|kW\|/20 px; teal charging, violet selling; a silent battery is dashed grey (`PathStyleExtension`, `getDashArray: [3, 2]`) | straight lines, same widths |
| `tf-warn` (new) | `IconLayer`, billboard, `sizeUnits: 'pixels'` | cans with tier code 2 or higher: `{position: [lon, lat, CAN_H_M*max(1.55, pct/100) + 10], code}` | `icons.warn`, 30 px at code 4, 24 px at codes 2-3, red and orange; `getColor` by code | a triangle glyph at the can |
| `tf-halo` (new) | `ScatterplotLayer`, flat, stroked, not filled | cans with tier code 1 or higher: `{position, radius: r * (1 + min(1, (pct - 100) / 100)) * 2.2}` | tier colour, 3 px stroke, alpha 200 | a ring |
| `event-icons` (new) | `IconLayer` | `meta.events[branch]` whose `step <= k` and is still active: comms_lost (until `coveredStep` + 10), hot (for `minutes`), stall (for `minutes`) | nosignal over the battery, ev over the home, pause over the feeder head | the same glyphs |
| `batteries` (changed) | as today, or the scene designer's cabinet | `color` from the new battery tokens | **discharging = violet `--bat-sell`, no longer `--serious`** | the same |
| `pulses` (changed) | as today | only the batteries whose command changed this step | at `allcharge`, all 96 pulse once: it reads as "everyone at once" | none |
| `homes` (changed) | as today | colour: code 0 = the house palette (the scene designer's), codes 1-5 = tier colour blended 45% into the roof colour; dark and backup unchanged | calmer default; red homes appear only under a red transformer | the same |
| `highlight` (new) | `ScatterplotLayer` | the row or pointer-selected transformer | a 2 px ink ring, 1.4x the halo | a ring |
| labels (changed) | `TextLayer` | A-D: "A 197%" (short), full text at zoom 16.2 or more | the kVA and room text move to the tooltip | the same |

Scene API additions (the contract line is a REQUEST to the lead for `docs/contracts.md` A.9):

| Method | Does |
|---|---|
| `scene.onHover(cb)` | `cb({layer, object, x, y})`; null object on leave |
| `scene.project(lonlatz)` | returns `[x, y]` in CSS px, or null |
| `scene.onViewChange(cb)` | called after every view-state change |
| `scene.flyTo(lonlat, {zoom, pitch, bearing})` | flies the camera |

Performance: 96 lines, at most about 20 icons and at most about 20 halos per frame. That is far below the 1,010 extruded homes that already render in SwiftShader smoke runs.

---

## 9. P2: where the same patterns apply (owner l5-p2-story)

1. **One question, one answer, above the fold.** "Where should the next battery go?" Then the answer card: `[H]+[B]` "Home 0409 on T-240" and one sentence: "T-240 has no battery and goes over its nameplate on hot evenings; a battery here removes the most overload." The numbers come from the combo doc, with dots. The ranked list follows as compact rows: a rank, a house icon, the transformer icon filled by its month peak, and one bar for "overload removed".
2. **A P2 story chain** (the same component, class `p2-chain`): `[$] a month of real prices` -> `[H+B] try a battery at each home` -> `[T ok] rank by overload removed`. It is static (P2 has no clock), and each step is a link that scrolls to its section.
3. **The insight beat as one chart.** Overlay the two histograms (transformer monthly-peak hour, teal; daily max-price hour, purple) on one 0-23 h axis, with an annotated bracket "`2` hours apart" between the two modes (DERIVED from `modeIndex`). The caption shrinks to one line.
4. **The "existing fleet" table becomes three icon rows**: `[H]` no batteries, `[BBB]` managed naively, `[~]` feeder-aware. Each row carries one horizontal bar (hours above nameplate, log scale), with the event counts as `[!]` icons with numbers and dots, and the screening marker as a dashed-ring dot.
5. **The flip as its biggest movers.** The data says the flip is partial: the two top tens share 7 homes, Spearman 0.94 (`p2-flip` beat, DERIVED). A slope chart of the whole top ten would show mostly parallel lines and undersell it. Draw the **biggest movers** instead, the list the panel already computes, as a slope chart: naive rank on the left on a log axis, feeder-aware rank on the right. Home 0409 on T-240 falls from naive rank 345 to feeder-aware rank 1 as one steep line, labelled. The partial-overlap sentence stays as one line above the chart.
6. Provenance dots, tooltips, collapsible sections and the icon set: the same l0 pieces.
7. **Beat captions** (`beats.json`, l5): every caption gets a one-line `headline` field shown by default. The full caption opens under "more". The P1 beats' headlines match the 7.2 to 7.4 caption texts, so the video and the replay say the same thing.

---

## 10. Ownership, order and time (one lane per area)

| Order | Lane | Files (`scripts/lanes.json`) | Work | Estimate |
|---|---|---|---|---|
| 1 | **l0-foundation** (lands first) | NEW `ui/lib/icons.js`, NEW `ui/lib/tip.js` (added to l0's `owns` in `lanes.json`); `ui/css/base.css` (dots, `.hb-tip`, `.ico`, the colour tokens); `ui/lib/data.js` (`parseLink`: `bare`, `speed`, `cap`, `pace`, `follow`, `date`; `linkQuery` round-trips them); `ui/app.js` (body class `pv-dots` on P1 and P2, `installTips()`); `ui/test/core.test.js` (icons are strings; `bat()` fill monotone; `parseLink` bare); `scripts/deeplinks.txt` (add `p1 view=p1` as the first-open link and `p1 view=p1&branch=naive&t=22:00&cam=street`); `docs/contracts.md` A.9 (scene API additions; new link params) | the shared pieces | 1.5 h |
| 2 | **l4-scene-p1** | `ui/panels/p1.js`, `ui/css/p1.css`, `ui/lib/scene-model.js`, `ui/lib/scene3d.js`, `ui/lib/fallback2d.js`, `ui/test/p1.test.js`, `ui/test/scene-model.test.js` | P0: `storyCues`, `nowSentence`, `moneyRunning` + tests; the chain, caption, NOW card, rows, branch pictograms, transport speeds, step and moments, and collapsibles. P1: `drops`, `tf-warn`, `tf-halo`, onHover tooltips, story pacing, money meter, off-screen pointer. P2: intro card, follow, `event-icons` | P0 3 h, P1 2 h, P2 1 h |
| 3 | **l5-p2-story** | `ui/panels/p2.js`, `ui/panels/more.js`, `ui/css/p2.css`, `ui/data/beats.json`, `docs/demo-script.md`, `ui/test/p2.test.js` | section 9; beat `headline` fields; demo script updated for the chain, captions and pacing | 2.5 h |
| any | **l2-p1** | none for the story | Nothing required: every cue is derived in the UI from committed arrays. Optional later: emit `meta.story` if the judge prefers sim-side cues | 0 |

**No two lanes edit one file.** p1.js consumes `icons.js` and `tip.js` through imports only. The P1 beat bar lives in `more.js` (l5), so l5 shortens it to the one-line headline, and l4 does not touch it.

If l4 runs short, cut in this order: P2 items, then the off-screen pointer, then story pacing. **Never cut** the chain, the caption, the 0.1x/0.25x speeds with step, the battery icons in the rows, the dots or the tooltips. Those are RZ's explicit asks.

---

## 11. Tests and acceptance

Node tests (`ui/test/p1.test.js`, l4), on the committed data (measure; do not hard-code the times above):
- `storyCues(meta, naive)` returns `drop <= allcharge <= overload <= worst < clear`, all within `[0, steps)`, with `overload` and `worst` present. `storyCues(meta, aware)` has **no** `overload` cue, and has `check` and `turns`. `storyCues(meta, none)` has no `sell`, `allcharge` or `check`.
- Every cue's `text(fmt)` renders without throwing (format.js throws on a bare number), and contains no digit outside a `<span class="num">` (the same rule `p2.test.js` applies to captions).
- `moneyRunning(meta, doc)`: the net at the last step equals `meta.money.energyValueUSD[branch].v` within $0.005 for naive, aware and aware_faults, and `sold` and `bought` never decrease.
- `nowSentence` at naive `drop.step` contains "Every battery is charging at once", and at aware `drop.step` "taking turns".
- `scene-model.test.js`: `drops` has 96 entries (0 on `hideBatteries`); `tf-warn` contains exactly the cans at tier code 2 or higher; the discharging battery colour is not in `TIER_RGB`.

Smoke: `scripts/smoke_ui.sh --lane l4-scene-p1` all ok, fixture 0, errors 0, offsite 0 (IconLayer data: URLs must not count).

The screenshots the judge must open (1920x1080), and what each must show:

| Link | Must show |
|---|---|
| `view=p1` (bare) | The intro card with the question and "Watch it happen"; the naive chain ghosted; the scene calm; no text paragraph in the panel above the fold. |
| `view=p1&branch=naive&t=22:00&cam=street` | All three chain steps lit, the third red; the caption "Every battery on the street starts charging in the same minute"; warning icons over A-D; 96 lit teal drops; battery icons with bolt badges in the rows; the NOW sentence. |
| `view=p1&branch=naive&t=20:00&cam=street&beat=backfeed` | Violet drops, not orange; a warning over C; the row arrows pointing out; the coin meter above $0. |
| `view=p1&branch=aware&t=22:30&cam=street&beat=rebound-aware` | Only some drops lit; no warning icons on A-D; chain steps 1-2 lit and step 3 "take turns" lit (not the "0 overloads" ok state). |
| `view=p1&branch=aware_faults&t=22:16&cam=street&beat=faults` | The no-signal icon at Home 0222's cabinet; chain step 1 lit; its caption. |
| `view=p1&branch=aware&t=16:45&cam=street&beat=peak-relief` | The off-screen pointer to T-240; A's violet relief drops; the relief sentence in the NOW card. |
| Any P1 view with the panel covered | The story still reads from the chain, caption, scene and strip (rule 2.5). |

---

## 12. Honesty guardrails (story mode must not bend the labels)

- Every number in a chain step, caption, tooltip, meter or sentence is a labelled value (`fmt` or `nv`). One dot per distinct label ends each sentence. A number with no label throws, as today.
- The naive story always carries its ASSUMPTION marker: on the branch option, on chain step 2 ("every battery charges at once" is our naive rule, not observed Base behaviour), and in the `sell` caption. "Base may not charge this way today" stays in the naive tooltip.
- "0 battery-caused overloads" appears only at the `charged` cue: it is an evening claim, scoped to service transformers and to battery-caused events (build prompt 3.4). The live NOW sentence only states what is true this minute.
- Money is "gross energy value, not Base's profit", and local relief is never priced (its tooltip says so).
- The fuse rule is an ASSUMPTION everywhere it appears (warning tooltip, row tooltip).
- Captions use only the data's outcomes. If a rule's measurement differs on another day, the caption says what was measured. Cue thresholds (`0.9 * fleet`, 99% SoC) are display rules for **when to speak**, never tuned to make a beat appear (build prompt 3.5). Any refuted expectation stays in NOTES.md.

---

## 13. Decisions for RZ (also appended to `NOTES.md`)

1. **The bare `?view=p1` opens naive at 21:45, paused, with an intro card.** Today it opens feeder-aware at 22:30, where nothing is happening. Beat and smoke links are unaffected (the card needs a link with no `branch`, `t` or `beat`). Conservative alternative: keep aware at 22:30 and show the card anyway.
2. **Story pacing is on by default**: 0.25x around each moment and a 1.2 s hold. At 1x the evening then takes about 100 s instead of 72 s. It is off with the checkbox or `&pace=0`, for even takes.
3. **Battery "selling or discharging" changes from orange to violet**, so it can no longer be mistaken for an overloaded transformer.
4. **Captions are on by default**; "CC" or `&cap=0` hides them for narrated takes.
5. **The 8x speed is dropped** (4x plays the evening in 18 s); 0.1x and 0.25x are added.
6. **The chain's "0 battery-caused overloads" lights only at the end of the evening (03:50)**, not at the first hand-off, because it is an evening claim.
