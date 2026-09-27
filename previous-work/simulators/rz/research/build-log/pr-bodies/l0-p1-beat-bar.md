## [l0-p1-beat-bar] P1 beat links mount the caption bar

Lead fix for **REQUEST 1** in PR #9 (lane l5-p2-story). One file: `ui/app.js` (lead-owned, build prompt section 6).

After the panel mounts, a `?beat=` link on `view=p1` calls `mountBeatBar(ctx, panelEl)` from `ui/panels/more.js`. It uses a namespace import and a `typeof` guard, so on `main` today (where `more.js` is still the L0 stub) it does nothing. A thrown error counts in `data-errors` instead of blanking the page.

REQUEST 2 (the beat lines in `scripts/deeplinks.txt` and the P2 `home=` link) is **not** in this PR. The beat links need `ui/data/beats.json` on `main`, and the `home=` link needs L3's measured aware #1, so both land with the PR #9 merge.

### Gate, real output
Branch gate, `scripts/check_all.sh --lane l0-foundation` at `3d832cb`:
```
STEP unit: PASS (Ran 56 tests)
STEP node: PASS (# pass 10 # fail 0 )
STEP keep: PASS (prototype 8 + 3, four-home 17)
STEP contract: PASS ((23 files, 3.75 MB, 10174 labelled numbers))
STEP verify: PASS (labels p1 p2)
PATHS: PASS (1 changed paths, all inside lane l0-foundation; base ddf223f)
SMOKE: 3/3 ok
ALL CHECKS: PASS
```

I also checked it with L5's branch merged in a local throwaway checkout (not pushed), with the 12 beat lines added locally. `scripts/smoke_ui.sh beat` printed `SMOKE: 12/12 ok` (P1/P2 on fixtures). The P1 `peak-relief` screenshot shows the caption bar at the top of the panel.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
