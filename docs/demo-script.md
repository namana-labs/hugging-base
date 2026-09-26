# Demo script: the five-minute video

RZ records by clicking; no terminal on screen. Each beat is **one deep link**. Its caption is built from the committed JSON at view time, and every number in it carries its label, so **read the caption as written**: if the data refuted an expectation, the caption already says what was measured instead. Never say a number the screen does not show.

Source of truth: `ui/data/beats.json` (the same beats, same ids). `ui/test/p2.test.js` checks that every beat below exists there and that no caption carries a bare number.

## Before you record

1. `scripts/serve.sh`, then open http://127.0.0.1:8765/ui/?view=more at 1920 x 1080.
2. The More tab lists every beat with its resolved caption. Click through once:
   - **no yellow FIXTURE banner** on any beat (real data for P1 and P2 is built);
   - **no "(not built yet)"** in any caption you plan to read;
   - the P1 beats play in 3D (if the 3D area is blank, add `&nowebgl=1` for the 2D fallback).
3. Each beat's caption bar has **next beat ›**: that is the whole click path.

## The beats

Base URL: `http://127.0.0.1:8765/ui/`

| Clock | Beat (`id`) | Link | On screen | Say (the caption carries the numbers) |
|---|---|---|---|---|
| 0:00–0:25 | **The problem** (`problem`) | `?view=p1&branch=naive&t=16:00&cam=street&beat=problem` | Street A–D in 3D at 16:00; the naive toggle with its ASSUMPTION chip; the scale ladder on the P1 panel once `p1/meta.json` carries `scaleLadder` (not built at the time of writing: judge R0 F7, L2's). | ERCOT dispatches one number per load zone and does not check feeders. Our naive branch splits it with no feeder check, all at once: an assumption, because Base's real split is not public. Never imply Base charges this way today. |
| 0:25–0:50 | **Afternoon peak: relief at its true size** (`peak-relief`) | `?view=p1&branch=aware&t=16:45&cam=street&beat=peak-relief` | A's gauge at its afternoon peak; the `driver` line under it. | A is over nameplate for the minutes the caption shows: amber, **not a failure**. Name the driver: one home's load, one SMART-DS profile that also runs at Home 0409 on T-240 (one shape, not two pieces of evidence). A's own batteries discharge and A drops. T-240 has no battery; P2 answers that. |
| 0:50–1:00 | **When transformers peak vs when prices peak** (`insight`) | `?view=p2&combo=aware-core-d26-g0&beat=insight` | The P2 insight bars: transformer peak hour (SIM) vs the day's max-price hour (REAL). | Across August, when transformers peak vs when prices peak. Say only what the bars show. |
| 1:00–1:25 | **Evening price peak: naive back-feed** (`backfeed`) | `?view=p1&branch=naive&t=20:00&cam=street&beat=backfeed` | Street A–D exporting at the evening price peak. | Back-feed is an overload too. Naive exports all at once; feeder-aware caps export by headroom. |
| 1:25–2:00 | **The price collapse: naive rebound** (`rebound-naive`) | `?view=p1&branch=naive&t=22:30&cam=street&beat=rebound-naive` | Red cans on A–C; the fuse margin on each gauge; the grid line (minimum voltage, feeder head). | The price collapses at the D-26 onset and every battery charges at once. Read the worst loading, the tier counts, and the fuse margin. Voltage and the feeder head: read them as measured. |
| 2:00–2:30 | **The price collapse: feeder-aware rotation** (`rebound-aware`) | `?view=p1&branch=aware&t=22:30&cam=street&beat=rebound-aware` | Same clock, feeder-aware: the ticker names each grant and hand-off; the gauges stay under their limits. | Check each transformer's headroom, send only what fits. Read the order the caption gives for when charge first reaches A, B, C and D (measured; on 23 Aug it starts at D, not A, and the A→B→C→D rotation expectation is refuted, see `$OVN/NOTES.md`). **No service transformer** passes its limit (say "service transformer"; the feeder head is reported separately). Name what the controller is assumed to see. |
| 2:30–3:00 | **Pieces fail mid-balance** (`faults`) | `?view=p1&branch=aware_faults&t=22:16&cam=street&beat=faults` | A battery goes silent (grey, "!"), C runs hot, the controller stalls. | Stale, expired, idle with backup armed; name the neighbours the caption names. For C, read the caption as measured: on 23 Aug C's batteries were **not charging** when the EV arrived, so there was nothing to shift (never say "charge shifts away" unless the caption does). Zero battery-caused violations, if the caption says zero. |
| 3:00–3:30 | **Where the next battery goes** (`p2-controls`) | `?view=p2&combo=aware-core-d26-g0&n=5&beat=p2-controls` | The P2 controls, the ranked table, candidate pins and five greedy placements in the scene, the referee badge. | The CEO's question. A month on real prices; candidates ranked with vs without a battery. Point at the OpenDSS badge (or the screening chip). |
| 3:30–3:55 | **The flip** (`p2-flip`) | `?view=p2&combo=naive-core-d26-g0&beat=p2-flip` | The flip card: top-ten overlap, Spearman, the untied overlap, the biggest movers, and feeder-aware's first choice under naive dispatch. | "How you charge decides where the next battery goes" **only if the card shows that headline**; otherwise read the measured overlap (all candidates and untied) and the mover the caption names. |
| 3:55–4:20 | **Useful capacity and dark homes** (`p2-capacity`) | `?view=p2&combo=aware-core-d26-g0&n=10&beat=p2-capacity` | The useful-capacity numbers and curve; the "Where protection may operate" list. | How many batteries the feeder takes before trouble, naive vs feeder-aware. Protection: "protection may operate (ASSUMPTION rule)", and read how many homes would go dark as the caption states it (on this data: none, every home behind those transformers has a battery). |
| 4:20–4:45 | **Money, labelled** (`money`) | `?view=more&beat=money` | The money card. | Energy value both ways and the cost of awareness. Fleet kW at the **system** peak is worth the benchmark band; **never** apply it to local relief. CoServ, GVEC and Austin Energy pay for system peak, coincident peaks and arbitrage; local relief is an unpriced opportunity. |
| 4:45–5:00 | **How Base plugs it in tomorrow** (`plug-in`) | `?view=more&beat=plug-in` | The plug-in and performance cards. | The siting file beside the install queue; `allocate()` behind the zone base point; the performance numbers. |

## Words to use, and to avoid

- Say **"over nameplate (amber; not a failure)"** for A's afternoon peak. Never "overheats".
- Say **"no service transformer passes its limit"**, never "nothing passes its limit".
- Say **"the naive branch (an assumption)"**, never "how Base charges today".
- Say **"protection may operate (ASSUMPTION rule)"** for dark homes.
- Say **"local relief is an opportunity, unpriced"**, never revenue.
- The feeder is an **Oncor-suburb stand-in settled at LZ_NORTH (placeholder)**; 2018 SMART-DS load is paired with 2026 prices by calendar date (ASSUMPTION).
- **The next-battery score is not a Base product.** Base schedules installs by demand; we add the grid lens.
