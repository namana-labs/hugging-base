# story/: data for the four-page story

The demo is a four-page story: **scenario → what happens → result → answers**. Connor owns how the pages look; the engine path (RZ + Michael) owns the data.

| File | What |
| --- | --- |
| `STORY-CONNOR-NEEDS.md` | What Connor's current dashboard code reads, what each page needs, which of his placeholder series our data replaces (and which have no real source), and a `frameAt()` adapter sketch. **Connor: read this first.** |
| `STORY-INVENTORY.md` | Every piece of data that already exists per page, the scenario knobs we can offer (which combinations are precomputed), and the gaps with the cheapest honest fix. |
| `probe/` | The inventory's timing probes (how long a new evening or variant takes to build). |

Not written before RZ's laptop stopped: the story data contract, its JSON schema and a sample file. The engine path builds them as `ui/data/story/` (see `handoff/ENGINE.md`, steps 2 to 4) and documents them in `docs/contracts.md`.
