"""web/data.js: reading the map file, diffing it, the stale notice, and polling behaviour.

Run with Node, like test_glyph.py. The page itself is checked in a browser.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="Node is not installed")

FIELDS = ["i", "n", "y", "x", "s", "b", "l", "h", "t", "u", "c"]


def doc(*rows, generated_at=1000, fields=FIELDS):
    return {"city": "hyderabad", "generated_at": generated_at, "fields": fields, "sites": list(rows)}


def row(i="a", state="WARNING", low=11, high=16, trusted=1, updated=900, confidence=0.8):
    return [i, f"Site {i}", 17.4, 78.45, state, "B2", low, high, trusted, updated, confidence]


def node(body):
    script = f"""
import {{ parseDocument, diffSites, statusFor, startLive, STALE_AFTER_S }} from "{(ROOT / 'web' / 'data.js').as_uri()}";
globalThis.document = {{ hidden: false, addEventListener() {{}}, removeEventListener() {{}} }};
{body}
"""
    out = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout.strip().splitlines()[-1])


def test_columns_are_read_by_name_not_position():
    shuffled = ["h", "i", "n", "y", "x", "s", "b", "l", "t", "u", "c"]
    reordered = [16, "a", "Site a", 17.4, 78.45, "WARNING", "B2", 11, 1, 900, 0.8]
    out = node(f"""
const d = parseDocument({json.dumps(doc(reordered, fields=shuffled))});
console.log(JSON.stringify([...d.sites.values()]));""")
    assert out[0]["id"] == "a" and out[0]["high"] == 16 and out[0]["trusted"] is True
    assert out[0]["confidence"] == 0.8 and out[0]["lat"] == 17.4


def test_a_file_without_the_confidence_column_counts_as_unsure_not_confident():
    old = [f for f in FIELDS if f != "c"]
    out = node(f"""
const d = parseDocument({json.dumps(doc(row()[:10], fields=old))});
console.log(JSON.stringify([...d.sites.values()][0].confidence));""")
    assert out == 0


def test_diff_finds_added_changed_and_removed_and_ignores_the_rest():
    before = doc(row("a"), row("b"), row("c"))
    after = doc(row("a"), row("b", high=22), row("d"))
    out = node(f"""
console.log(JSON.stringify(diffSites(parseDocument({json.dumps(before)}), parseDocument({json.dumps(after)}))));""")
    assert out == {"added": ["d"], "changed": ["b"], "removed": ["c"]}


def test_the_first_load_adds_everything_and_an_identical_load_changes_nothing():
    same = doc(row("a"), row("b"))
    out = node(f"""
const d = parseDocument({json.dumps(same)});
console.log(JSON.stringify([diffSites(null, d), diffSites(d, parseDocument({json.dumps(same)}))]));""")
    assert out[0] == {"added": ["a", "b"], "changed": [], "removed": []}
    assert out[1] == {"added": [], "changed": [], "removed": []}


def test_the_notice_says_nothing_when_all_is_well_and_the_age_when_it_is_not():
    out = node("""
console.log(JSON.stringify([
  statusFor({loaded: true, failed: false, ageSeconds: 60}),
  statusFor({loaded: true, failed: false, ageSeconds: STALE_AFTER_S}),
  statusFor({loaded: true, failed: false, ageSeconds: STALE_AFTER_S + 1}),
  statusFor({loaded: true, failed: true, ageSeconds: 180}),
  statusFor({loaded: false, failed: true, ageSeconds: 0}),
  statusFor({loaded: false, failed: false, ageSeconds: 0}),
]));""")
    assert out[0] is None and out[1] is None
    assert out[2] == {"text": "Last updated 20 minutes ago", "level": "stale"}
    assert out[3] == {"text": "Could not refresh. Last updated 3 minutes ago", "level": "stale"}
    assert out[4] == {"text": "The map data could not be loaded.", "level": "error"}
    assert out[5] is None


def test_polling_loads_once_then_only_reports_real_changes_and_survives_failures():
    first, second = doc(row("a"), generated_at=1000), doc(row("a", high=30), generated_at=1020)
    out = node(f"""
const files = [{json.dumps(first)}, {json.dumps(first)}, "fail", {json.dumps(second)}];
const loads = [], notices = [];
let n = 0;
const fetchFn = async () => {{
  const file = files[Math.min(n++, files.length - 1)];
  if (file === "fail") return {{ ok: false, status: 503 }};
  return {{ ok: true, json: async () => file, headers: {{ get: () => null }} }};
}};
const live = startLive({{ url: "x", interval: 10_000_000, fetchFn, nowFn: () => 1_100_000,
  onData: (l) => loads.push(l.diff), onStatus: (s) => notices.push(s && s.level) }});
await new Promise((r) => setTimeout(r, 20));
await live.refresh(); await live.refresh(); await live.refresh();
live.stop();
console.log(JSON.stringify({{ loads, notices, kept: live.current().sites.get("a").high }}));""")
    assert out["loads"] == [{"added": ["a"], "changed": [], "removed": []},
                            {"added": [], "changed": ["a"], "removed": []}]     # repeats are not reported
    # first load, an identical load, a failure, then the changed file: the notice comes and goes
    assert out["notices"] == [None, None, "stale", None]
    assert out["kept"] == 30


def test_a_failure_before_anything_has_loaded_says_so():
    out = node("""
const notices = [];
const live = startLive({ url: "x", interval: 10_000_000, fetchFn: async () => { throw new Error("offline"); },
  nowFn: () => 5_000_000, onData: () => {}, onStatus: (s) => notices.push(s) });
await new Promise((r) => setTimeout(r, 20));
live.stop();
console.log(JSON.stringify(notices));""")
    assert out == [{"text": "The map data could not be loaded.", "level": "error"}]


def test_the_servers_clock_not_the_phones_decides_how_old_the_data_is():
    # The phone's clock is an hour fast. The file was generated 60 s before the server's Date.
    out = node("""
const notices = [];
const server = Date.parse("2026-10-09T12:00:00Z");
const fetchFn = async () => ({ ok: true, headers: { get: () => new Date(server).toUTCString() },
  json: async () => ({ city: "x", generated_at: server / 1000 - 60, fields: ["i","n","y","x","s","b","l","h","t","u","c"], sites: [] }) });
const live = startLive({ url: "x", interval: 10_000_000, fetchFn, nowFn: () => server + 3_600_000,
  onData: () => {}, onStatus: (s) => notices.push(s) });
await new Promise((r) => setTimeout(r, 20));
live.stop();
console.log(JSON.stringify(notices));""")
    assert out == [None]                      # 60 s old by the server's clock: no notice
