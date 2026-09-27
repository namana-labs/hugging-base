# video/

The Batter Up intro video for the submission, by Bo.

| File | What |
| --- | --- |
| `batterup-intro-video.mp4` | The rendered intro (1920x1080, about 31 s, with a synthesized score) |
| `intro-video-src/` | Its source: a deterministic canvas animation (`index.html`), the data prep (`prep.py`, `fit.py`), the score (`audio6.py`) and the capture script (`capture.js`). How to rebuild: `intro-video-src/README.md` |

Numbers in the video follow the same labels as the app (REAL / SIM / DERIVED / ASSUMPTION).
Note: the video quotes ERCOT's 22 Jul 2026 peak as 91,089 MW (unofficial); the app and `docs/research-report.md` use ERCOT's official 91,134 MW (`sim/history.py` `ERCOT_RECORD_MW`).
