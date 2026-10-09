"""The flood history file: each site's past floods, for the repeat offenders page.

METHOD.md section 14. Built only from what the flood workflow records when a flood closes
(workflow.summary), so it holds no number the system did not measure. Of the measures that
section names, this file carries the count, the time blocked for cars and for two-wheelers,
the peak depth and whether a trusted source confirmed it. It does not yet carry trigger rain,
drain time, pump response or a coverage flag: those are not recorded, and are listed in the
page rather than invented.

Counted as floods: closed records whose outcome is "flood". A watch that saw no water
("no_flood") is counted separately. A record closed by hand ("reset", from scripts/reset.py)
is not a flood and is ignored. A flood still in progress is not history yet.
"""

FLOOD, NO_FLOOD = "flood", "no_flood"


def flood_row(event):
    """One closed flood event (a FloodEvent as a dict) as a row of the file."""
    return {
        "start": event["start"], "end": event["closed_at"],
        "low": event["peak_low"], "high": event["peak_high"],
        "cars_min": event["blocked_cars_s"] // 60,
        "two_wheelers_min": event["blocked_two_wheelers_s"] // 60,
        "confirmed": bool(event["confirmed"]),
    }


def site_entry(site_id, name, events):
    """One site's history from all its flood records, open and closed, in any order."""
    closed = [e for e in events if e.get("closed_at") is not None]
    floods = sorted((flood_row(e) for e in closed if e["outcome"] == FLOOD), key=lambda f: f["start"])
    confirmed = [f for f in floods if f["confirmed"]]
    return {
        "id": site_id, "name": name,
        "floods": floods,
        "confirmed": len(confirmed), "unconfirmed": len(floods) - len(confirmed),
        "cars_min": sum(f["cars_min"] for f in confirmed),
        "two_wheelers_min": sum(f["two_wheelers_min"] for f in confirmed),
        "peak_high": max((f["high"] for f in confirmed), default=0),
        "dry_watches": sum(1 for e in closed if e["outcome"] == NO_FLOOD),
    }


def document(city, generated_at, entries):
    """`entries` from site_entry, one per registry site. Sites with no floods are kept: the page
    needs to say how many places are watched, not only how many have flooded."""
    return {"city": city, "generated_at": int(generated_at),
            "sites": sorted(entries, key=lambda e: e["id"])}


def ranking(entries):
    """The page's order, as site ids: most time blocked for cars first, most floods next, then
    the name. Only sites with a confirmed flood are ranked; an unconfirmed flood does not move a
    site up (METHOD.md section 14)."""
    ranked = [e for e in entries if e["confirmed"] > 0]
    return [e["id"] for e in sorted(ranked, key=lambda e: (-e["cars_min"], -e["confirmed"], e["name"]))]
