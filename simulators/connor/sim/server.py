"""Local control-panel server: serves this folder and reruns a scenario on demand.

    .venv/bin/python -m sim.server            # http://127.0.0.1:4388/ui/four-node.html
    .venv/bin/python -m sim.server --port 4390

GET  /api/params        -> {"schema": [...knobs...], "defaults": {...}, "scenarios": ["day", "mechanics"]}
POST /api/run           <- {"scenario": "day"|"mechanics", "params": {name: value}, "policies": ["aware","naive"]}
                        -> the replay JSON (same shape as data/replays/*.json), or {"error": "..."} with 400

Everything is deterministic and runs in-process; OpenDSS is a singleton, so the
server is single-threaded and runs one scenario at a time. Binds to localhost only.
Nothing here is the demo: the demo is the static replays in data/replays/.
"""
from __future__ import annotations

import argparse
import json
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

from .params import Params, schema
from .scenarios.day import build_day
from .scenarios.four_node import build_mechanics

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ("day", "mechanics")


def run_request(body: dict) -> dict:
    """Validate one /api/run body and return the replay. Raises KeyError/ValueError on bad input."""
    scenario = body.get("scenario", "day")
    if scenario not in SCENARIOS:
        raise ValueError(f"scenario must be one of {SCENARIOS}")
    policies = tuple(body.get("policies") or ("aware", "naive"))
    if not policies or any(p not in ("aware", "naive") for p in policies):
        raise ValueError("policies must be a non-empty subset of ['aware', 'naive']")
    params = Params.from_overrides(body.get("params") or {})
    if scenario == "day":
        return build_day(policies=policies, out=None, quiet=True, params=params)
    return build_mechanics(params, policies, out=None)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def _json(self, payload: dict, status: int = 200) -> None:
        data = json.dumps(payload, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        if self.path.split("?")[0] == "/api/params":
            self._json({"schema": schema(), "defaults": Params().to_json(), "scenarios": list(SCENARIOS)})
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self.path.split("?")[0] != "/api/run":
            self._json({"error": "unknown endpoint"}, 404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length) or b"{}")
            self._json(run_request(body))
        except (KeyError, ValueError, TypeError) as e:
            self._json({"error": str(e)}, 400)

    def end_headers(self) -> None:
        if self.path.endswith(".json"):
            self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args) -> None:  # one quiet line per request
        if "/api/" in str(args[0] if args else ""):
            super().log_message(fmt, *args)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--port", type=int, default=4388)
    a = ap.parse_args()
    server = HTTPServer(("127.0.0.1", a.port), Handler)
    print(f"Control panel: http://127.0.0.1:{a.port}/ui/four-node.html   (Ctrl-C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
