#!/usr/bin/env bash
# Judge R2: the heavy steps after check_all --full, in ONE hold of the heavy-run lock (8.4).
# Runs in the fresh clone ~/hb-overnight/judge-2; screen reads are served from a `git archive HEAD` copy.
set -u
E=/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/judge-R2
PY=$HOME/hb-overnight/.venv/bin/python
S=/private/tmp/claude-501/-Users-rzalagbada-Desktop-projects-REDACTED/db7213a8-6bab-44d3-b22b-9fe4a11f46ca/scratchpad/judge-r2-tree
cd $HOME/hb-overnight/judge-2
echo "acquired $(date -u +%H:%M:%S)" >> $E/hold.times
# 1 calibrate (writes surrogate.json + SOURCE.md section; the tree must stay clean = byte-identical)
$PY -m sim.calibrate > $E/calibrate.log 2>&1
git status --porcelain > $E/calibrate_dirty.log
# 2 dwell builds (the section 9 spot-check): MIN_DWELL_MIN 1 and 15, to a tmp dir, never the repo
$PY -m sim.p1_build --dwell 1 --out $HOME/hb-overnight/tmp/judge-r2-d1 > $E/p1_dwell1.log 2>&1
$PY -m sim.p1_build --dwell 15 --out $HOME/hb-overnight/tmp/judge-r2-d15 > $E/p1_dwell15.log 2>&1
git status --porcelain > $E/dwell_dirty.log
$PY $E/scripts/judge_r2_dwell.py dwell1=$HOME/hb-overnight/tmp/judge-r2-d1/aware.json \
  dwell5_committed=$E/committed/ui_data_p1_aware.json dwell15=$HOME/hb-overnight/tmp/judge-r2-d15/aware.json > $E/dwell_handoffs.log 2>&1
# 3 independent OpenDSS solves at 6 steps vs the committed loading
$PY $E/scripts/judge_r2_opendss_spot.py $E/committed > $E/opendss_spot.log 2>&1
# 4 screen reads (page text + flags + 1080p shot) over one headless Chrome, served from the archive copy
PORT=$(python3 -c 'import socket;s=socket.socket();s.bind(("127.0.0.1",0));print(s.getsockname()[1])')
python3 -m http.server $PORT --bind 127.0.0.1 --directory "$S" > /dev/null 2>&1 &
SRV=$!
sleep 1
SMOKE_TMP=$HOME/hb-overnight/tmp node $E/scripts/judge_r2_screen.mjs "http://127.0.0.1:$PORT/ui/" $E/screen \
  'view=p1&branch=none&t=16:45&cam=street' 'view=p1&branch=aware&t=16:45' 'view=p1&branch=naive&t=22:30' \
  'view=p1&branch=aware&t=22:30' 'view=p1&branch=aware_faults&t=22:16' 'view=p1&branch=naive&t=20:00&cam=feeder' \
  'view=p1&branch=aware&t=22:30&nowebgl=1' \
  'view=p2&combo=aware-core-d26-g0' 'view=p2&combo=naive-core-d26-g0&home=p1ulv24700' 'view=p2&combo=aware-core-d26-g0&n=5' \
  'view=more' \
  'view=p1&branch=naive&t=16:00&cam=street&beat=problem' 'view=p1&branch=aware&t=16:45&cam=street&beat=peak-relief' \
  'view=p2&combo=aware-core-d26-g0&beat=insight' 'view=p1&branch=naive&t=20:00&cam=street&beat=backfeed' \
  'view=p1&branch=naive&t=22:30&cam=street&beat=rebound-naive' 'view=p1&branch=aware&t=22:30&cam=street&beat=rebound-aware' \
  'view=p1&branch=aware_faults&t=22:16&cam=street&beat=faults' 'view=p2&combo=aware-core-d26-g0&n=5&beat=p2-controls' \
  'view=p2&combo=naive-core-d26-g0&beat=p2-flip' 'view=p2&combo=aware-core-d26-g0&n=10&beat=p2-capacity' \
  'view=more&beat=money' 'view=more&beat=plug-in' > $E/screen.log 2>&1
# prototype still renders from the same root
SMOKE_TMP=$HOME/hb-overnight/tmp node $E/scripts/judge_r2_proto.mjs "http://127.0.0.1:$PORT/demos/grid-stories/ui/dist/" /Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/shots/judge-R2-extra > $E/proto_check.log 2>&1
curl -s -o /dev/null -w "proto index %{http_code}\n" "http://127.0.0.1:$PORT/demos/grid-stories/ui/dist/" >> $E/proto_check.log
kill $SRV
echo "released $(date -u +%H:%M:%S)" >> $E/hold.times
