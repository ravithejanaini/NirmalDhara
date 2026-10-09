"""Write the site registry from data/hyderabad_sites.json into the Sites table.

    python scripts/seed.py            # shows what would change
    python scripts/seed.py --apply    # writes it

Only the registry attributes are set (name, lat, lon, rain_threshold_mm, source). The state
engine's attributes (doc, state, version) are never touched, so re-running the seed on a live
site does not reset it. Running it twice changes nothing the second time.
"""

import argparse
import json
import re
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "hyderabad_sites.json"
BOUNDS = (78.05, 17.08, 78.90, 17.72)      # west, south, east, north: the map's limits
ATTRIBUTES = ("name", "lat", "lon", "rain_threshold_mm", "source")


def load(path=DATA):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def problems(document):
    """Everything wrong with the file, as a list of sentences. Empty means it can be seeded."""
    out, seen = [], set()
    for n, site in enumerate(document.get("sites", []), 1):
        label = site.get("id", f"entry {n}")
        if not re.fullmatch(r"hyd-\d{3}", str(site.get("id", ""))):
            out.append(f"{label}: id must look like hyd-001")
        if site.get("id") in seen:
            out.append(f"{label}: id used twice")
        seen.add(site.get("id"))
        if not str(site.get("name", "")).strip():
            out.append(f"{label}: no name")
        lat, lon = site.get("lat"), site.get("lon")
        if not (isinstance(lat, (int, float)) and isinstance(lon, (int, float))
                and BOUNDS[1] <= lat <= BOUNDS[3] and BOUNDS[0] <= lon <= BOUNDS[2]):
            out.append(f"{label}: position missing or outside Hyderabad")
        if not re.match(r"https?://\S+$", str(site.get("source", ""))):
            out.append(f"{label}: no source link, and every site needs one")
        threshold = site.get("rain_threshold_mm", 20)
        if not isinstance(threshold, (int, float)) or threshold <= 0:
            out.append(f"{label}: rain_threshold_mm must be a positive number")
    return out


def wanted(site):
    return {"name": site["name"].strip(), "lat": Decimal(str(site["lat"])),
            "lon": Decimal(str(site["lon"])),
            "rain_threshold_mm": Decimal(str(site.get("rain_threshold_mm", 20))),
            "source": site["source"]}


def seed(table, document, apply=False):
    """Returns {"added": [...], "changed": [...], "unchanged": [...]} by site id."""
    result = {"added": [], "changed": [], "unchanged": []}
    for site in document["sites"]:
        key = {"city": document["city"], "site_id": site["id"]}
        item = table.get_item(Key=key, ConsistentRead=True).get("Item")
        want = wanted(site)
        if item is None:
            kind = "added"
        elif all(item.get(k) == v for k, v in want.items()):
            result["unchanged"].append(site["id"])
            continue
        else:
            kind = "changed"
        result[kind].append(site["id"])
        if apply:
            table.update_item(
                Key=key,
                UpdateExpression="SET " + ", ".join(f"#{k} = :{k}" for k in ATTRIBUTES),
                ExpressionAttributeNames={f"#{k}": k for k in ATTRIBUTES},
                ExpressionAttributeValues={f":{k}": v for k, v in want.items()})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--apply", action="store_true", help="write the changes")
    parser.add_argument("--file", default=str(DATA))
    args = parser.parse_args()
    document = load(args.file)
    bad = problems(document)
    if bad or not document.get("sites"):
        print("The site file is not ready:" if bad else "The site file has no sites.")
        print("\n".join(f"  - {line}" for line in bad))
        return 1

    import boto3
    outputs = json.loads((ROOT / "data" / "stack-outputs.json").read_text("utf-8"))
    table = boto3.resource("dynamodb", region_name=outputs["region"]).Table(
        outputs["resources"]["SitesTable"])
    result = seed(table, document, apply=args.apply)
    verb = "written" if args.apply else "would be written"
    print(f"{len(result['added'])} added, {len(result['changed'])} changed, "
          f"{len(result['unchanged'])} unchanged ({verb})")
    if not args.apply and (result["added"] or result["changed"]):
        print("Run again with --apply to write them.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
