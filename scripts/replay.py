"""Play the evening scenario into the deployed system, so the map shows the same flood each time.

    python scripts/replay.py                       # shows the schedule; sends nothing
    python scripts/replay.py --go                  # plays it at 45x: 90 minutes in 2
    python scripts/replay.py --go --speed 1        # plays it in real time

Run scripts/reset.py first: a replay refuses to start on a site that is not clear.

The four scenario sites (a to d) stand for four real registry sites; --sites changes which:
    --sites a=hyd-006,b=hyd-002,c=hyd-005,d=hyd-007

What it does and does not do (DESIGN.md 20.3):
- The engine gets each message with a simulated time, so rain that is "light for an hour"
  really ends a watch even in a two-minute replay.
- The flood workflow runs on the real clock. At 45x its timers cannot show repeat alerts
  (every 20 minutes) or escalation (5 minutes): the video uses the smoke test's record for
  those. Flood records made by a fast replay therefore carry real, short durations. Use
  --speed 1 for records with realistic ones.
- It is a demonstration on the real map. The public site shows these floods at these real
  places while it runs, and any subscriber to the alerts topic receives the alerts. It
  refuses to run while the topic has a confirmed subscriber unless --alerts-ok is given.
"""

import argparse
import json
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import send  # noqa: E402
import stack  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SCENARIO = ROOT / "data" / "scenarios" / "evening.json"
DEFAULT_SITES = {"a": "hyd-006", "b": "hyd-002", "c": "hyd-005", "d": "hyd-007"}


def parse_sites(text):
    """'a=hyd-006,b=hyd-002' -> {'a': 'hyd-006', 'b': 'hyd-002'}, over the defaults."""
    mapping = dict(DEFAULT_SITES)
    for part in filter(None, (p.strip() for p in (text or "").split(","))):
        key, _, site = part.partition("=")
        if key not in DEFAULT_SITES or not site.startswith("hyd-"):
            raise ValueError(f"cannot read {part!r}: use a=hyd-006 with a to d on the left")
        mapping[key] = site
    if len(set(mapping.values())) != len(mapping):
        raise ValueError("two scenario sites cannot be the same registry site")
    return mapping


def plan(scenario, mapping, start_ts, speed):
    """The messages to send, in order: [{delay_s, sim_min, site, message}].

    `delay_s` is seconds after the start of the replay. `message` carries the simulated time
    (start_ts plus the scenario minute), which is what the engine reads.
    """
    if speed <= 0:
        raise ValueError("speed must be above zero")
    missing = {e["site"] for e in scenario["events"]} - set(mapping)
    if missing:
        raise ValueError(f"the scenario uses sites with no registry site: {sorted(missing)}")
    out = []
    for event in sorted(scenario["events"], key=lambda e: (e["t_min"], e["site"], e["type"] != "rain")):
        site, ts = mapping[event["site"]], start_ts + event["t_min"] * 60
        if event["type"] == "rain":
            message = send.rain_message(site, event["index_mm"], ts)
        else:
            message = send.reading_message(
                site, event["high"], event["low"], event["confidence"], event["source"], event["device"], ts)
        out.append({"delay_s": event["t_min"] * 60 / speed, "sim_min": event["t_min"], "site": site, "message": message})
    return out


def public_row(aws, bucket, site_ids):
    """What the public map file says about these sites right now, without the times."""
    import gzip
    raw = aws.client("s3").get_object(Bucket=bucket, Key="data/hyderabad.json")["Body"].read()
    doc = json.loads(gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw)
    return {row[0]: row[4:9] + row[10:] for row in doc["sites"] if row[0] in site_ids}


def site_states(aws, resources, site_ids):
    table = aws.resource("dynamodb").Table(resources["SitesTable"])
    out = {}
    for site in site_ids:
        item = table.get_item(Key={"city": send.CITY, "site_id": site}, ConsistentRead=True).get("Item")
        if item is None:
            out[site] = None                                  # not in the registry
        else:
            out[site] = json.loads(item["doc"])["state"] if "doc" in item else "CLEAR"
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--go", action="store_true", help="send the messages (default: show them)")
    parser.add_argument("--speed", type=float, default=45, help="scenario minutes per real minute")
    parser.add_argument("--sites", help="a=hyd-006,b=hyd-002,c=hyd-005,d=hyd-007")
    parser.add_argument("--scenario", default=str(SCENARIO))
    parser.add_argument("--alerts-ok", action="store_true", help="run although the alerts topic has subscribers")
    args = parser.parse_args()

    scenario = json.loads(Path(args.scenario).read_text(encoding="utf-8"))
    mapping = parse_sites(args.sites)
    start = int(time.time())
    steps = plan(scenario, mapping, start, args.speed)
    real_minutes = scenario["duration_min"] / args.speed
    print(f"{scenario['name']}: {len(steps)} messages over {scenario['duration_min']} scenario minutes, "
          f"{real_minutes:.1f} real minutes at {args.speed:g}x")
    for key, site in mapping.items():
        print(f"  {key} -> {site}: {scenario['sites'][key]['role']}")

    if not args.go:
        for step in steps[:6]:
            m = step["message"]
            print(f"  +{step['delay_s']:6.1f}s  {step['site']}  {m['type']}"
                  f"{'' if m['type'] == 'rain' else ' ' + str(m['reading']['high']) + ' cm'}")
        print("  ...\nRun again with --go to play it. Run scripts/reset.py first if any site is not clear.")
        return 0

    aws = stack.session()
    resources = stack.resources(aws)
    states = site_states(aws, resources, list(mapping.values()))
    unknown = [s for s, st in states.items() if st is None]
    busy = {s: st for s, st in states.items() if st not in (None, "CLEAR")}
    if unknown:
        print(f"Not in the registry: {unknown}. Nothing was sent.")
        return 1
    if busy:
        print(f"Not clear: {busy}. Run scripts/reset.py first. Nothing was sent.")
        return 1
    subscribers = [s for s in aws.client("sns").list_subscriptions_by_topic(
        TopicArn=resources["AlertsTopic"])["Subscriptions"] if s["SubscriptionArn"].startswith("arn:")]
    if subscribers and not args.alerts_ok:
        print(f"The alerts topic has {len(subscribers)} confirmed subscriber(s). They would be sent alerts that "
              "real places are flooding. Pass --alerts-ok if that is what you want. Nothing was sent.")
        return 1

    queue = send.queue_url(aws, resources)
    sqs, run_id = aws.client("sqs"), uuid.uuid4().hex[:8]
    began = time.monotonic()
    print(f"Replay {run_id} started. The public map shows these as real floods until you run reset.py.", flush=True)
    for n, step in enumerate(steps):
        wait = began + step["delay_s"] - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        send.send(sqs, queue, step["message"], dedup=f"replay-{run_id}-{n}")
        m = step["message"]
        detail = f"rain {m['index_mm']:g}" if m["type"] == "rain" else f"{m['reading']['low']:g}-{m['reading']['high']:g} cm"
        print(f"  t={step['sim_min']:3d} min  {step['site']}  {detail}", flush=True)

    time.sleep(8)
    final = site_states(aws, resources, list(mapping.values()))
    print("Finished. States now:", {site: state for site, state in final.items()})
    expected = {mapping[k]: v["expect"]["final_state"] for k, v in scenario["sites"].items()}
    wrong = {s: (final[s], want) for s, want in expected.items() if final[s] != want}
    print("As the scenario says." if not wrong else f"Different from the scenario: {wrong}")
    return 0 if not wrong else 2


if __name__ == "__main__":
    sys.exit(main())
