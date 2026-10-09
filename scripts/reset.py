"""Put the four demo sites back to clear, ready for another replay.

    python scripts/reset.py                      # shows what it would do
    python scripts/reset.py --go                 # does it
    python scripts/reset.py --go --forget-floods # also deletes their flood and alert records

For each site, in this order:
  1. stops its flood timer, so nothing acts on it while it is being reset;
  2. closes any open flood record, with the outcome "reset" (repeat-offenders views must
     ignore that outcome: it is not a flood that ended);
  3. removes the engine's own record of the site (its state, readings and version), which
     makes it clear again. The registry's name, position and rain threshold are untouched;
  4. with --forget-floods, deletes every flood record and alert claim for the site.
Then it asks the publisher to refresh the public map.

Only the sites named by --sites (default: the four the replay uses) are touched.
"""

import argparse
import sys
import time
from dataclasses import replace
from pathlib import Path

from boto3.dynamodb.conditions import Attr, Key

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import replay  # noqa: E402
import stack  # noqa: E402
from nirmaldhara import store  # noqa: E402

CITY = "hyderabad"
ENGINE_ATTRIBUTES = ("doc", "state", "version")


def stop_timers(steps_client, machine_arn, site_id, apply):
    """Stop the running flood timers of one site. Returns their names."""
    names = []
    token = None
    while True:
        page = steps_client.list_executions(stateMachineArn=machine_arn, statusFilter="RUNNING",
                                            maxResults=100, **({"nextToken": token} if token else {}))
        names += [e["executionArn"] for e in page["executions"] if e["name"].startswith(site_id + "-")]
        token = page.get("nextToken")
        if not token:
            break
    if apply:
        for arn in names:
            steps_client.stop_execution(executionArn=arn, cause="reset.py")
    return [arn.split(":")[-1] for arn in names]


def close_open_flood(floods, site_id, now, apply):
    """Close the site's open flood record as 'reset'. Returns its start, or None."""
    event = store.load_open_event(floods, site_id)
    if event is None:
        return None
    if apply:
        store.save_event(floods, replace(event, closed_at=now, outcome="reset", version=event.version + 1),
                         expected_version=event.version)
    return event.start


def clear_engine_record(sites, site_id, apply):
    """Remove the engine's attributes from a site. Returns whether there were any."""
    item = sites.get_item(Key={"city": CITY, "site_id": site_id}, ConsistentRead=True).get("Item", {})
    present = [a for a in ENGINE_ATTRIBUTES if a in item]
    if present and apply:
        sites.update_item(Key={"city": CITY, "site_id": site_id},
                          UpdateExpression="REMOVE " + ", ".join(f"#{a}" for a in ENGINE_ATTRIBUTES),
                          ExpressionAttributeNames={f"#{a}": a for a in ENGINE_ATTRIBUTES})
    return bool(present)


def forget_floods(floods, alerts, site_id, apply):
    """Delete all flood records and alert claims of a site. Returns (floods, claims) counts."""
    records = floods.query(KeyConditionExpression=Key("site_id").eq(site_id), ConsistentRead=True)["Items"]
    claims, kwargs = [], {"FilterExpression": Attr("site_id").eq(site_id), "ConsistentRead": True}
    while True:
        page = alerts.scan(**kwargs)
        claims += page["Items"]
        if "LastEvaluatedKey" not in page:
            break
        kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]
    if apply:
        for item in records:
            floods.delete_item(Key={"site_id": site_id, "start": item["start"]})
        for item in claims:
            alerts.delete_item(Key={"alert_id": item["alert_id"]})
    return len(records), len(claims)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--go", action="store_true", help="do it (default: show what would happen)")
    parser.add_argument("--sites", help="a=hyd-006,b=hyd-002,c=hyd-005,d=hyd-007")
    parser.add_argument("--forget-floods", action="store_true", help="also delete flood and alert records")
    args = parser.parse_args()

    aws = stack.session()
    resources = stack.resources(aws)
    dynamo = aws.resource("dynamodb")
    sites, floods, alerts = (dynamo.Table(resources[k]) for k in ("SitesTable", "FloodsTable", "AlertsTable"))
    steps_client, machine = aws.client("stepfunctions"), resources["FloodStateMachine"]
    now = int(time.time())

    for site_id in replay.parse_sites(args.sites).values():
        if sites.get_item(Key={"city": CITY, "site_id": site_id}).get("Item") is None:
            print(f"{site_id}: not in the registry, skipped")
            continue
        timers = stop_timers(steps_client, machine, site_id, args.go)
        started = close_open_flood(floods, site_id, now, args.go)
        cleared = clear_engine_record(sites, site_id, args.go)
        line = [f"timers {len(timers)}", f"open flood {'closed' if started else 'none'}",
                f"engine record {'removed' if cleared else 'already clear'}"]
        if args.forget_floods:
            n_floods, n_claims = forget_floods(floods, alerts, site_id, args.go)
            line.append(f"deleted {n_floods} flood records, {n_claims} alert claims")
        print(f"{site_id}: " + ", ".join(line))

    if not args.go:
        print("Nothing was changed. Run again with --go to do it.")
        return 0
    aws.client("lambda").invoke(FunctionName=resources["PublisherFunction"], InvocationType="Event")
    print("Asked the publisher to refresh the public map.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
