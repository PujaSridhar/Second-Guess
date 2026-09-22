"""Local dashboard. Click Run, the real pipeline executes, the page shows what it found.

    python -m secondguess.serve

No pinned files, no fixtures: /api/run executes extract -> lint -> live web
resolve -> drafts and returns that run's output. The page renders whatever
comes back, including a bad run. Stdlib only.
"""
import json
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .config import GROUND_TRUTH, ROOT

PORT = 8765
SHELL = ROOT / "scripts" / "dashboard_shell.html"

_state = {"status": "idle", "log": [], "result": None, "scores": None, "error": None}
_lock = threading.Lock()


def _log(msg):
    with _lock:
        _state["log"].append(msg)


def _execute(learned, use_web):
    from .run import run
    from scripts.score import score

    try:
        _log("Reading corpus: email, Slack, meeting notes, calendar")
        if learned:
            _log("Recalling learned rules from Cognee's permanent graph")
        _log("Extracting commitments")
        result = run(learned=learned, use_web=use_web)
        if use_web:
            _log("Resolved external dependencies via Bright Data (live)")
        _log("Calendar lint + closure + dedupe applied")
        _log("Drafting follow-ups for flagged commitments")

        out = ROOT / "runs" / ("live_improved.json" if learned else "live_baseline.json")
        out.write_text(json.dumps(result, indent=2))
        scores = score(str(out))
        _log(f"Scored against {len(json.loads((GROUND_TRUTH / 'commitments.json').read_text())['commitments'])} labelled commitments")

        with _lock:
            _state.update(status="done", result=result, scores=scores)
    except Exception as exc:
        with _lock:
            _state.update(status="error", error=f"{type(exc).__name__}: {exc}")
        _log(f"FAILED: {exc}")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        data = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/":
            return self._send(200, SHELL.read_text(), "text/html; charset=utf-8")
        if u.path == "/api/state":
            with _lock:
                return self._send(200, json.dumps(_state))
        if u.path == "/api/run":
            q = parse_qs(u.query)
            if _state["status"] == "running":
                return self._send(409, json.dumps({"error": "already running"}))
            learned = q.get("learned", ["1"])[0] == "1"
            use_web = q.get("web", ["1"])[0] == "1"
            # Flip to running here, not inside the worker: a client that polls
            # immediately would otherwise read "idle" and stop watching.
            with _lock:
                _state.update(status="running", log=["Starting run"], result=None,
                              scores=None, error=None)
            threading.Thread(target=_execute, args=(learned, use_web), daemon=True).start()
            return self._send(202, json.dumps({"started": True}))
        self._send(404, json.dumps({"error": "not found"}))


def main():
    sys.path.insert(0, str(ROOT))
    url = f"http://localhost:{PORT}/"
    print(f"\n  Second Guess dashboard -> {url}")
    print("  Click 'Run analysis'. Ctrl-C to stop.\n")
    threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
