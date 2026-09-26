---
name: hugging-base-design
description: Hugging Base visual design system, the story-flow spec v2 (Configure, Run, Results, Learnings) and the Chapter 1 (option 3a) control-room spec. Use before building or changing any Hugging Base UI (ui/, demos/grid-stories/ui/), a mock, a slide or any visual asset, or when choosing colours, type, spacing, motion, icons or UI copy.
user-invocable: true
---

# Hugging Base design

`docs/design-handoff/` is the authoritative design source. Where it conflicts with `docs/ui-brief.md` or with the existing prototype's look, the handoff wins. `docs/design.md` still owns scope and the project's non-negotiables.

Read, in order:

1. `docs/design-handoff/README.md`: the spec. Layout, every component, interactions, state, tokens. Its values are final unless it says otherwise.
2. `docs/design-handoff/design-system/readme.md`: brand, content rules, iconography.
3. `docs/design-handoff/design-system/tokens/*.css` (imported by `styles.css`): use these custom properties; do not re-type hex values.
4. `docs/design-handoff/story-flow/README.md`: the story-flow spec v2 (1a Configure, 1b Running, 2b Run, 3a Results, 4b Learnings). For those screens it wins over the Chapter 1 spec. Serve the folder over HTTP to open the `.dc.html` references; v2 ships no screenshots.
5. `docs/design-handoff/prototype/Hugging Base Heartbeat v2.dc.html` (open with `support.js` beside it): the reference for look and motion. Option 3a is `<div class="dv-opt" id="3a">`; the logic is in the `<script data-dc-script>` block.

## Rules that are easy to get wrong

- The prototype is a reference, not code to copy. Rebuild in the target app, reading the real `topology.json`, `replays.json`, `candidates.json` and `model.json` instead of the scripted series.
- Green (`--brand`) means "ours" or "selected", never "safe". Safety is sage and the absence of amber or red.
- Transformer loading shows all three tiers (100 / 110 / 150% of nameplate as shipped) in the legend.
- The 20% member reserve is drawn as a floor and never breached.
- Every number carries a provenance tag (SOURCED / DERIVED / ASSUMPTION / UNVERIFIED), never colour-coded, never clipped.
- Hanken Grotesk 400/700 only, tabular figures for numbers. No shadows. 300 ms `cubic-bezier(.3,.7,.2,1)`, no bounces.
- No Base or ERCOT marks; the wordmark is plain type. The adversary is fictional. Never imply a language model chose a dispatch, setpoint or ranking.
- Must read at 1080p, 16:9, after video compression. No hover-only information.

For throwaway mocks, copy `styles.css` and `tokens/` next to a static HTML file.
