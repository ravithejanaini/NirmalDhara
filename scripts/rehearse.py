"""Rehearse the video's replay on your own machine: nothing reaches AWS or the public map.

    python scripts/serve_web.py            # in one terminal
    python scripts/rehearse.py             # in another, then open http://127.0.0.1:8080/

It plays data/scenarios/evening.json into the development server's stand-in map, at the same
speed and with the same moments as the real replay (scripts/replay.py), so you can practise the
taps and the timing of the video as often as you like. The states come from the real state engine
run on the scenario, not from a recording.

This is practice. The video itself must show the deployed site, with scripts/replay.py --go.
"""

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nirmaldhara.state import Reading, Site, apply_rain, apply_reading  # noqa: E402
from nirmaldhara.workflow import confidence  # noqa: E402

SCENARIO = ROOT / "data" / "scenarios" / "evening.json"
# The four scenario sites take the place of four of the stand-in map's sample sites.
STAND_INS = {"a": ("sample-05", "Rehearsal: Lakdikapul railway bridge"),
             "b": ("sample-04", "Rehearsal: Raheja Mindspace underpass"),
             "c": ("sample-02", "Rehearsal: Cyber Towers junction"),
             "d": ("sample-01", "Rehearsal: Khairatabad junction")}
OTHERS = ("sample-03", "sample-06", "sample-07", "sample-08")


def frames(scenario, speed=45):
    """What the map should show and when: [(seconds from the start, sample id, fields)]."""
    sites = {key: Site(key) for key in STAND_INS}
    out = []
    for event in sorted(scenario["events"], key=lambda e: (e["t_min"], e["site"], e["type"] != "rain")):
        key, ts = event["site"], event["t_min"] * 60
        before = sites[key]
        if event["type"] == "rain":
            after = apply_rain(before, event["index_mm"], ts)
        else:
            after = apply_reading(before, Reading(ts, event["low"], event["high"], event["confidence"],
                                                  event["source"], event["device"]))
        sites[key] = after
        shown = lambda s: (s.state, round(s.low), round(s.high), s.trusted)       # noqa: E731
        if shown(after) != shown(before):
            out.append((event["t_min"] * 60 / speed, STAND_INS[key][0], {
                "state": after.state, "low": round(after.low), "high": round(after.high),
                "trusted": 1 if after.trusted else 0, "confidence": round(confidence(after), 2)}))
    return out


def call(base, path, **query):
    url = f"{base}{path}?{urllib.parse.urlencode(query)}" if query else f"{base}{path}"
    with urllib.request.urlopen(url, timeout=5) as response:
        return response.status


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--speed", type=float, default=45)
    parser.add_argument("--server", default="http://127.0.0.1:8080")
    args = parser.parse_args()
    scenario = json.loads(SCENARIO.read_text(encoding="utf-8"))
    try:
        call(args.server, "/__dev/reset")
    except Exception:
        print("The development server is not running. Start it first: python scripts/serve_web.py")
        return 1
    clear = {"state": "CLEAR", "low": 0, "high": 0, "trusted": 0, "confidence": 0}
    for sample in OTHERS:
        call(args.server, "/__dev/set", site=sample, name=f"Rehearsal: quiet place {sample[-1]}", **clear)
    for sample, name in STAND_INS.values():
        call(args.server, "/__dev/set", site=sample, name=name, **clear)

    plan = frames(scenario, args.speed)
    print(f"Rehearsal: {len(plan)} changes over {plan[-1][0]:.0f} seconds. Open {args.server}/ now.")
    began = time.monotonic()
    for delay, sample, fields in plan:
        wait = began + delay - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        call(args.server, "/__dev/set", site=sample, **fields)
        depth = f"{fields['low']}-{fields['high']} cm" if fields["high"] else "no water"
        print(f"  {delay:5.0f}s  {sample}  {fields['state']:9} {depth}{'' if fields['trusted'] or not fields['high'] else '  (unconfirmed)'}", flush=True)
    print("Done. Run it again to practise, or stop the development server to end.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
