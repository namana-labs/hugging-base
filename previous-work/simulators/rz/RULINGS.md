# RZ's rulings from 26 Sep 2026 (apply in the engine path)

## Wi-Fi / comms loss behaviour: CONFIRMED (Base engineers, on site)
A battery that loses its connection sits idle in backup-only mode: it does not charge, and it does NOT discharge to the grid. It only backs up its own home in an outage.
- The sim already does this: `sim/devices.py` idles with backup armed at command expiry, and `ui/panels/p1.js` shows "Its command expired: it waits, backup armed".
- Relabel the **behaviour** REAL, cited "Base engineer, on site, 26 Sep 2026 (verbal)". Never quote the private notes and never name the engineer.
- The **timings** stay ASSUMPTION: `COMMAND_TTL_S` = 300 s, `COMMS_STALE_S` = 180 s, `FAULT_COMMS_AFTER_MIN` = 15.
- Files to touch: `sim/constants.py`, `docs/data-sources.md`, `docs/how-base-plugs-in.md` (the device-contract bullet; open question 4 now asks only for the timings), the `faults` beat in `docs/demo-script.md`, `ui/panels/more.js`, and the tooltip in `ui/panels/p1.js`.

## The fuse rule stays ASSUMPTION
The rule: `FUSE_PCT` 200% for `FUSE_MINUTES` 10, and `FUSE_INSTANT_PCT` 300% for 60 s. In round 1, the naive rebound peaked at 201.2% on transformer A at 22:30 and stayed above 200% for 9 minutes; the rule needs 10, so no dark homes. Re-check this knife edge against the round-2 data.

## The capacity planner scope (three layers)
See `research/capacity-planner/DATA-SCOPE-RZ-CAPACITY-PLANNER.md`:
1. Which transformers have room and which are full, under naive and under feeder-aware charging.
2. One transformer, 0 to 50 batteries.
3. Which transformers are worth upgrading, ranked by the growth an upgrade unlocks: a full transformer whose homes are all members already is worth little; a full one with many non-members or pending requests is worth a lot; age adds replacement odds. The profit/reliability dial and the utility's ROI are a slide only.

## The story and the team
- A four-page story: scenario → what happens → result → answers.
- Connor owns the visuals. RZ + Michael own the engine and the data. Amy owns the presentation. Bo does design support.
- Everyone works in their own folder. See `handoff/README.md` at the repo root.
