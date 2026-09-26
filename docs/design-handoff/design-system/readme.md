# Hugging Base design system

Hugging Base is a hackathon simulator of one Austin-like feeder run by a fleet of home batteries. It shows which batteries to dispatch under congestion, where the next battery should go, and what happens when pieces fail. It is inspired by Base Power's public look (deep forest green on warm cream) but is not Base's product and uses none of its marks.

Sources: `docs/ui-brief.md` and the prototype at `demos/grid-stories/ui/dist/`. The spec in `../README.md` is authoritative; if this file disagrees with it, the spec wins.

## Content fundamentals
- Plain language first, jargon in parentheses on first use: "transformer (the street box shared by two or three homes)".
- Sentence case everywhere. Bold short titles: "One feeder, one hot evening".
- Confident, unhurried, factual. No game framing (no "mission", difficulty pips).
- Every number has a provenance tag: SOURCED, DERIVED, ASSUMPTION, UNVERIFIED.
- Never imply a language model chose a dispatch, setpoint or ranking.
- No emoji. Unicode arrows (→ ↑) and ▶ ❚❚ are the only glyphs.

## Visual foundations
- Colour: cream page (#f7f4ec), panels #fffdf8, board #efece3. Brand green #1e4d2b means "ours" and "selected", never "safe". Safety is sage (#8aa58f). Tiers: amber, red, dark red. Tiers show in fills of transformer dots, never in text colour.
- Type: Hanken Grotesk 400/700 only, tabular figures for numbers. The beat's one number is the largest thing on screen (≥58px, up to 150px).
- Surfaces: flat cards, 1px warm hairline, radius 10. No shadows. The emphasised stat tile gets a 1.5px ink border.
- Backgrounds: flat. The only gradient is the day/night band on timelines.
- Motion: the interface has a heartbeat. One day = 20 s. Pulse rate follows fleet power: `40 + 80·|P|` beats per minute, where |P| is normalised fleet power (see ../README.md). Each beat is a lub-dub that travels from the substation outward; lines thicken and brighten on the beat; transformers above a tier swell harder. The big number breathes 2.5% on each beat. The day trace clears at midnight and redraws; yesterday fades as a ghost over 4 s. Numbers update only on 5-minute market steps. State changes use 300 ms ease-out; no bounces.
- Hover: primary darkens to --brand-hover. Selected: --brand-tint background, brand text.
- Layout: 16:9, legible at 1080p after video compression. One primary action per screen.

## Iconography
Feeder board uses Lucide (ISC licence) glyphs as inline SVG symbols: `house` for homes (filled brand green when it has one of our batteries, darker as it fills), `zap` inside a rounded tier-coloured badge for transformers, and a larger ink badge for the substation. Elsewhere Unicode glyphs only (▶ ❚❚ → ↑ + −). No logo: the wordmark is plain type, "Hugging Base", in brand green.

## Index
- styles.css → tokens/{fonts,colors,typography,spacing,motion}.css
- guidelines/ specimen cards
- ../prototype/Hugging Base Heartbeat v2.dc.html: chapter 1 layout directions with the live heartbeat
- The agent skill lives at `.claude/skills/hugging-base-design/SKILL.md`
