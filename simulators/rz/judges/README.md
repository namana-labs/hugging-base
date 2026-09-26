# judges/: what we can claim, checked

An independent audit of the app's data, run on 26 Sep 2026 against the round-2 build (`rz/r2-integrate` @ `9a461e9`, the same tree as this folder), plus a plain-language explainer of the orchestration.

| File | What |
| --- | --- |
| `DATA-TRUTH-inputs.md` | Every input and constant checked against its source (sha256 manifests, raw ERCOT files, cited URLs with HTTP status). The most important problems come first, with fixes. |
| `DATA-TRUTH-outputs.md` | Every on-screen number traced to its JSON field, recomputed, and checked with fresh OpenDSS re-solves. Problems first, with fixes. |
| `ORCHESTRATION.md` | What the orchestration is: `allocate()`, device commands with sequence and expiry, failure handling, Michael's worker leases and attacker detector, measured performance. |
| `data-truth-outputs-scripts/` | The auditor's own check scripts, re-runnable from a clone. |

The fix list is summarised in `handoff/ENGINE.md` at the repo root (the engine path owns it). The judges' guide was not written before RZ's laptop stopped. Amy writes the presentation from `presentation/START-HERE.md` and these files.
