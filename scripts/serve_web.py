"""Serve web/ on localhost for development, with a stand-in for the map file.

    python scripts/serve_web.py [port]          # default 8080

/data/hyderabad.json comes from data/sample-map.json with its times shifted to now, so the
sample always looks current. Three development-only addresses change what it returns, so the
page's behaviour can be watched without deploying anything:

    /__dev/set?site=sample-04&low=30&high=40&state=CRITICAL&trusted=1   change one site
    /__dev/fail?on=1                                                    make the file fail (503); on=0 mends it
    /__dev/age?minutes=25                                               make the file look 25 minutes old
    /__dev/history?mode=sample|empty|fail                               what /data/hyderabad-floods.json returns
    /__dev/reset                                                        undo all of the above

Listens on 127.0.0.1 only. It is never deployed: scripts/deploy_web.py uploads web/ and this
file is not in it.
"""

import json
import sys
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "sample-map.json"
SAMPLE_FLOODS = ROOT / "data" / "sample-floods.json"
STATE = {"overrides": {}, "fail": False, "age_s": 0, "history": "sample"}


def current_document(now=None):
    """The sample file as it should look right now, with any development overrides applied."""
    now = int(now if now is not None else time.time())
    doc = json.loads(SAMPLE.read_text(encoding="utf-8"))
    shift = now - STATE["age_s"] - doc["generated_at"]
    names = doc["fields"]
    index = {name: i for i, name in enumerate(names)}
    doc["generated_at"] += shift
    for row in doc["sites"]:
        if row[index["u"]] > 0:
            row[index["u"]] += shift
        for key, value in STATE["overrides"].get(row[index["i"]], {}).items():
            row[index[key]] = value
        row[index["b"]] = band_for(row[index["h"]])
    return doc


def band_for(high):
    return "B0" if high <= 0 else "B1" if high < 12 else "B2" if high < 20 else "B3" if high < 30 else "B4" if high < 50 else "B5"


def apply_set(query):
    site = query["site"][0]
    row = {}
    for key, field, cast in (("low", "l", float), ("high", "h", float), ("state", "s", str),
                             ("trusted", "t", int), ("confidence", "c", float), ("name", "n", str)):
        if key in query:
            row[field] = cast(query[key][0])
    if "high" in query:
        # A new reading is current. A dry site has reported nothing, which the file writes as 0.
        row["u"] = int(time.time()) if row["h"] > 0 else 0
    STATE["overrides"].setdefault(site, {}).update(row)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / "web"), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        url = urlparse(self.path)
        query = parse_qs(url.query)
        if url.path == "/data/hyderabad.json":
            if STATE["fail"]:
                return self.send_json(503, {"error": "development: file failing"})
            return self.send_json(200, current_document())
        if url.path == "/data/hyderabad-floods.json":
            mode = STATE["history"]
            if mode == "fail":
                return self.send_json(503, {"error": "development: history failing"})
            doc = json.loads(SAMPLE_FLOODS.read_text(encoding="utf-8"))
            if mode == "empty":
                doc.update(sites=[{**site, "floods": [], "confirmed": 0, "unconfirmed": 0, "cars_min": 0,
                                   "two_wheelers_min": 0, "peak_high": 0} for site in doc["sites"]], sample=False)
            doc["generated_at"] = int(time.time())
            return self.send_json(200, doc)
        if url.path == "/data/rule-cases.json":
            body = (ROOT / "data" / "rule-cases.json").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            return self.wfile.write(body)
        if url.path == "/__dev/set":
            apply_set(query)
        elif url.path == "/__dev/fail":
            STATE["fail"] = query.get("on", ["1"])[0] == "1"
        elif url.path == "/__dev/age":
            STATE["age_s"] = int(float(query.get("minutes", ["0"])[0]) * 60)
        elif url.path == "/__dev/history":
            STATE["history"] = query.get("mode", ["sample"])[0]
        elif url.path == "/__dev/reset":
            STATE.update(overrides={}, fail=False, age_s=0, history="sample")
        else:
            return super().do_GET()
        self.send_json(200, {"ok": True, "state": STATE})

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    print(f"http://127.0.0.1:{port}/", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
