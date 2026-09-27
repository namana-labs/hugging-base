# Four home charging rebound, standalone simulation

Four homes with one battery each, two SMART-DS service transformers, one
12.47 kV feeder, and real ERCOT data for 2026-09-25. OpenDSS solves the AC
power flow at every 5 minute step and is the only referee of loading and
voltage. Three dispatch policies are compared: naive, naive plus jitter, and
feeder aware.

This is a self contained copy of chapter 04 of the Hugging Base grid stories
demo. It does not need the rest of that repository.

## Open the visual, no install

Double click `four-home-visual.html`. The replay is embedded, so it opens from
disk with no server and no dependencies. Pick a policy, press play or use the
arrow keys, and read the one line diagram, the scale ladder, and the nine
charts.

## Regenerate the physics

Requires Python 3.12 or newer.

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python four_home.py            # rewrites ui/four-home-replay.json
.venv/bin/python -m unittest test_four_home -v
```

`four_home.py` reads the CSVs in `data/`, builds the circuit, solves each step,
joins the real frequency, demand and storage series, and writes the replay the
page reads. After regenerating, refresh `four-home.html` (the non embedded page)
against a local server, or rebuild the embedded `four-home-visual.html` by
pasting the new `ui/four-home-replay.json` back in.

```sh
python3 -m http.server 8000        # then open http://127.0.0.1:8000/four-home.html
```

## What is real and what is modeled

- **Real, from ERCOT public dashboards, pre extracted to `data/`:** LZ_NORTH
  15 minute settlement point prices (priced by interval ending), 10 second
  system frequency and inertia, 5 minute system demand, and 5 minute grid scale
  storage. Provenance and source URLs are in `data/four_home_provenance.json`.
- **SMART-DS, used verbatim:** the service transformer, triplex service drop,
  and 350 kcmil primary parameters, from the source files in `data/smartds/`.
- **Labeled assumptions:** every constant in `four_home_constants.py` carries a
  tag (SOURCED, DERIVED, ASSUMPTION, UNVERIFIED) and a citation. The visual's
  constants drawer shows the same table.

## The finding

The same 71 kW of charging reads as roughly 210 percent of the small
transformer, 1.1 percent of the feeder, 0.0001 percent of ERCOT demand, and a
5 to 9 microhertz shift in system frequency. The market sees only the last two;
the limit that bites lives at the transformer. Feeder aware dispatch clears
every thermal tier and pays for it in about 12 kWh of charging deferred behind
the small transformer, which is the market position the desk gives up.

## Files

```
four-home-visual.html      self contained page, replay embedded, open directly
four-home.html             same page, reads ui/four-home-replay.json (needs a server)
four_home.py               the simulator and replay generator
four_home_constants.py     every constant, tagged and cited
test_four_home.py          17 tests: topology, power balance, tiers, data joins
requirements.txt           OpenDSSDirect.py
ui/four-home-replay.json   generated replay the pages read
data/                      real ERCOT CSVs, provenance, and SMART-DS source files
```

Sign convention: positive battery kW is charging, matching the grid stories
demo. The Headroom PRD binding convention is the opposite.
