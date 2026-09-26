# Hugging Base

A playable neighborhood-grid simulator for the Base Power × AITX hackathon. Explore a real SMART-DS feeder, replay three stories, compare dispatch policies, and test the next home battery with OpenDSS.

```sh
python3 -m http.server 4387 --bind 127.0.0.1 --directory ui/dist
```

Open **http://127.0.0.1:4387**. The bundled app needs no dependency installation.

- [Playbook, regeneration, validation, and limitations](docs/implementation.md)
- [Design and project scope](docs/design.md)
- [Research and source references](docs/research-report.md)
- [Data provenance and modifications](data/README.md)

`sim/` owns the physics and scoring; `ui/dist/` is the complete static app plus solved data. Core assumptions are centralized in `sim/constants.py`. Prices and temporal load profiles are illustrative, explicitly labeled assumptions. OpenDSS is the referee.
