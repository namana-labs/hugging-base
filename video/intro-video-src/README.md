# BatterUp intro video: source

Renders `batterup-intro.mp4` (1920×1080, 60 fps, 31.3 s, with a synthesized score).

- `index.html`: the whole animation as one deterministic `render(t)` on a canvas. Open it over HTTP to preview it live in a loop.
- `prep.py`: builds `data.json` from `previous-work/docs-history/design-handoff/story-flow/ui/data/` (moved there on 27 Sep; the live app data is `ui/data/`) (topology, footprints, the P2 next-battery ranking). Edit the `D=` path at the top.
- `fit.py`: ports `fitModel` from `ui/story.js` to get the Street D headroom and the upgrade list (needs `p1/none.json`, `p1/aware.json`).
- `audio6.py`: synthesizes `score.wav` for the current BatterUp cut (earlier cuts: audio2/audio3) (`audio.py` is the old Hugging Base cut) (numpy + scipy), cued to the same timeline.
- `capture.js`: Playwright → PNG frames → ffmpeg.

```
npm i playwright @fontsource/hanken-grotesk
python -m http.server 8777 &
node capture.js                      # writes video_noaudio.mp4
python audio6.py                     # writes score.wav
ffmpeg -i video_noaudio.mp4 -i score.wav -c:v copy -af loudnorm=I=-14:TP=-1.5 -c:a aac -b:a 256k -shortest batterup-intro.mp4
```

Numbers shown: ERCOT peak records (SOURCED, ercot.com; 91,089 MW on 22 Jul 2026 is unofficial until settlement). Feeder counts and geometry (REAL, NREL SMART-DS). A/B transformer colours and the 30 → 3 count (SIM, P2 naive/aware-core-d26-g0 August peak). 383 vs 1,007 (SIM, OpenDSS-checked, p2/index.json usefulCapacity). Street D headroom and the upgrade list (SCREENING, fitModel at +20% load). Ranked homes (SIM, P2 ranking). The single-transformer gauge in "The limit" is illustrative.
