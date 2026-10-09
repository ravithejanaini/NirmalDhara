"""Write docs/architecture.svg: what is deployed, with what is only designed drawn dashed.

    python scripts/make_architecture.py

Each solid box names the resources in template.yaml it stands for (`resources`), and
tests/test_architecture.py checks that every one exists and that every function in the template
appears in the picture. A dashed box has no resources: it is designed, or built but never run.
"""

from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
W, H = 1120, 760

NIGHT, PANEL, LINE, SHALLOW, PAPER, MIST, SIGNAL = (
    "#0E1A2B", "#16304A", "#2B3F5C", "#7FB7BE", "#F3EDE1", "#A9B6C6", "#E4572E")

# key: (x, y, w, h, title, sub, kind, template resources)
# kind: deployed (solid), designed (dashed), outside (faint outline)
NODES = {
    "om": (24, 60, 170, 60, "Open-Meteo", "rain forecast", "outside", ()),
    "rc": (244, 60, 170, 60, "Rain check", "every 15 minutes", "deployed", ("RainFunction",)),
    "sc": (684, 60, 150, 60, "Scenario engine,", "fix sheet", "designed", ()),
    "ph": (24, 180, 170, 76, "Photo upload,", "intake, photo reader", "designed", ()),
    "eq": (244, 180, 170, 60, "Engine queue", "one site at a time", "deployed", ("EngineQueue", "EngineDeadLetters")),
    "se": (464, 180, 170, 60, "State engine", "only writer of state", "deployed", ("EngineFunction",)),
    "bus": (684, 180, 150, 60, "Event bus", "30-day archive", "deployed", ("Bus", "BusArchive")),
    "wf": (880, 180, 190, 66, "Flood workflow", "reactor, tick, timer", "deployed",
           ("ReactorFunction", "TickFunction", "FloodStateMachine")),
    "cam": (24, 300, 170, 76, "Cameras, waste", "tracking", "designed", ()),
    "st": (244, 300, 170, 60, "Sites table", "state and registry", "deployed", ("SitesTable",)),
    "fl": (880, 290, 190, 56, "Floods table", "one record per flood", "deployed", ("FloodsTable",)),
    "hi": (464, 430, 170, 60, "History", "flood history file", "deployed", ("HistoryFunction",)),
    "pu": (684, 430, 150, 60, "Publisher", "the map file", "deployed", ("PublisherFunction", "PublishQueue")),
    "nt": (880, 430, 190, 60, "Notifier", "sends each alert once", "deployed", ("NotifierFunction", "AlertsTable")),
    "tp": (880, 540, 190, 60, "Alerts topic", "SNS", "deployed", ("AlertsTopic",)),
    "ch": (880, 640, 190, 60, "SMS, chat, email", "to people", "designed", ()),
    "bk": (464, 550, 170, 60, "Public bucket", "map and history files", "deployed", ("PublicBucket",)),
    "sh": (464, 660, 170, 60, "Site host", "HTTPS, read-only", "deployed", ("SiteFunction",)),
    "me": (244, 660, 170, 60, "Resident's phone", "map, sheet, repeat floods", "outside", ()),
    "cf": (684, 660, 150, 60, "CloudFront", "off: account unverified", "designed", ()),
}

# (from, to, dashed, both ways, waypoints). Waypoints are the whole path, drawn as given.
EDGES = [
    ("om", "rc", False, False, [(194, 90), (244, 90)]),
    ("rc", "eq", False, False, [(329, 120), (329, 180)]),
    ("ph", "eq", True, False, [(194, 210), (244, 210)]),
    ("cam", "eq", True, False, [(150, 300), (270, 240)]),
    ("eq", "se", False, False, [(414, 210), (464, 210)]),
    ("se", "st", False, True, [(500, 240), (380, 300)]),
    ("se", "bus", False, False, [(634, 210), (684, 210)]),
    ("bus", "wf", False, False, [(834, 210), (880, 210)]),
    ("wf", "fl", False, True, [(975, 246), (975, 290)]),
    ("wf", "nt", False, False, [(1070, 214), (1092, 214), (1092, 460), (1070, 460)]),
    ("nt", "tp", False, False, [(975, 490), (975, 540)]),
    ("tp", "ch", True, False, [(975, 600), (975, 640)]),
    ("bus", "pu", False, False, [(759, 240), (759, 430)]),
    ("bus", "hi", False, False, [(710, 240), (590, 430)]),
    ("pu", "bk", False, False, [(710, 490), (600, 550)]),
    ("hi", "bk", False, False, [(549, 490), (549, 550)]),
    ("bk", "sh", False, False, [(549, 610), (549, 660)]),
    ("sh", "me", False, False, [(464, 690), (414, 690)]),
    ("cf", "sh", True, False, [(684, 690), (634, 690)]),
    ("bus", "sc", True, False, [(759, 180), (759, 120)]),
]

STYLE = {
    "deployed": f'fill="{PANEL}" stroke="{SHALLOW}" stroke-width="1.6"',
    "designed": f'fill="none" stroke="{MIST}" stroke-width="1.4" stroke-dasharray="6 5"',
    "outside": f'fill="none" stroke="{LINE}" stroke-width="1.6"',
}
TEXT = {"deployed": PAPER, "designed": MIST, "outside": MIST}


def box(key):
    x, y, w, h, title, sub, kind, _ = NODES[key]
    cx = x + w / 2
    return (
        f'<g id="node-{key}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" {STYLE[kind]} />'
        f'<text x="{cx}" y="{y + h / 2 - 3}" text-anchor="middle" font-size="16" font-weight="600" '
        f'fill="{TEXT[kind]}">{escape(title)}</text>'
        f'<text x="{cx}" y="{y + h / 2 + 17}" text-anchor="middle" font-size="14" fill="{MIST}">{escape(sub)}</text></g>')


def edge(spec):
    a, b, dashed, both, points = spec
    d = "M " + " L ".join(f"{x} {y}" for x, y in points)
    dash = ' stroke-dasharray="6 5"' if dashed else ""
    start = ' marker-start="url(#arrow-start)"' if both else ""
    return (f'<path d="{d}" fill="none" stroke="{MIST}" stroke-width="1.5"{dash}{start} '
            f'marker-end="url(#arrow)" data-from="{a}" data-to="{b}" />')


def legend(y):
    items = [("deployed", "Deployed, and run on AWS"), ("designed", "Designed, or built but not run"),
             ("outside", "Outside the system")]
    out, x = [], 24
    for kind, label in items:
        out.append(f'<rect x="{x}" y="{y}" width="34" height="22" rx="4" {STYLE[kind]} />'
                   f'<text x="{x + 46}" y="{y + 16}" font-size="14" fill="{MIST}">{escape(label)}</text>')
        x += 46 + 8 * len(label) + 28
    return "".join(out)


def svg():
    deployed = sum(1 for n in NODES.values() if n[6] == "deployed")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t d" font-family="Inter, system-ui, sans-serif">
<title id="t">NirmalDhara on AWS, 9 October 2026</title>
<desc id="d">{deployed} deployed parts in the Mumbai region: a rain check feeds a queue; one engine per site writes state and publishes events; a flood workflow decides alerts; a notifier sends them once to a topic; a publisher and a history writer keep two public files that a read-only site host serves to a phone. Photo reading, cameras and waste tracking, a scenario engine, alert channels to people and CloudFront are designed or off.</desc>
<defs>
  <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="{MIST}" /></marker>
  <marker id="arrow-start" viewBox="0 0 10 10" refX="1" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="{MIST}" /></marker>
</defs>
<rect width="{W}" height="{H}" fill="{NIGHT}" />
<text x="24" y="30" font-size="20" font-weight="600" fill="{PAPER}" font-family="Fraunces, Georgia, serif">NirmalDhara on AWS (ap-south-1)</text>
{"".join(edge(e) for e in EDGES)}
{"".join(box(k) for k in NODES)}
{legend(H - 34)}
</svg>
'''


if __name__ == "__main__":
    out = ROOT / "docs" / "architecture.svg"
    out.write_text(svg(), encoding="utf-8", newline="\n")
    print(f"wrote {out}")
