"""web/sw.js, web/manifest.json and the offline notice: what is kept, what is not, how it is marked.

The worker is run in Node against a stand-in for the browser's cache and network. That it
installs and works in a real browser is checked by hand (DESIGN.md 20.4).
"""

import json
import re
import shutil
import struct
import subprocess
import zlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="Node is not installed")

HARNESS = """
import { readFileSync } from "node:fs";
import vm from "node:vm";
const listeners = {}, stores = new Map();
let online = true, status = 200;
const keyOf = (req) => { const u = new URL(req.url ?? req, "https://x.test/"); return u.pathname; };
const cacheFor = (name) => {
  if (!stores.has(name)) stores.set(name, new Map());
  const m = stores.get(name);
  return {
    async put(req, res) { m.set(keyOf(req), res); },
    async add(req) { const url = typeof req === "string" ? new URL(req, "https://x.test/").href : req.url; m.set(keyOf(url), new Response("shell " + url)); },
    async match(req) { const hit = m.get(keyOf(req)); return hit ? hit.clone() : undefined; },
  };
};
const self = { location: { origin: "https://x.test" }, clients: { claim: async () => {} }, skipWaiting: async () => {},
  addEventListener: (type, fn) => { listeners[type] = fn; } };
const sandbox = { self, URL, Request, Response, Headers, console,
  caches: { open: async (n) => cacheFor(n), keys: async () => [...stores.keys()], delete: async (n) => stores.delete(n) },
  fetch: async (req) => { if (!online) throw new TypeError("offline"); return new Response("live " + req.url, { status }); } };
vm.runInContext(readFileSync(%(sw)s, "utf8"), vm.createContext(sandbox));
const get = (url, mode = "same-origin") => {
  let reply = null;
  const request = { url, method: "GET", mode };
  listeners.fetch({ request, respondWith: (p) => { reply = p; } });
  return reply;
};
const fire = async (type) => { let work; await listeners[type]({ waitUntil: (p) => { work = p; } }); await work; };
const text = async (p) => {
  try { const r = await p; return r ? [r.status, await r.text(), r.headers.get("x-offline-copy")] : null; }
  catch (e) { return ["error", e.message, null]; }
};
"""


def run(body):
    script = HARNESS % {"sw": json.dumps(str(WEB / "sw.js"))} + body
    out = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True, encoding="utf-8")
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout.strip().splitlines()[-1])


@needs_node
def test_online_the_live_answer_is_used_and_kept():
    out = run("""
await fire("install");
const live = await text(get("https://x.test/data/hyderabad.json"));
online = false;
const kept = await text(get("https://x.test/data/hyderabad.json"));
console.log(JSON.stringify([live, kept]));""")
    assert out[0] == [200, "live https://x.test/data/hyderabad.json", None]
    assert out[1][1] == "live https://x.test/data/hyderabad.json"       # the last live answer, not the shell copy


@needs_node
def test_offline_the_map_file_is_marked_and_the_pages_are_not():
    out = run("""
await text(get("https://x.test/data/hyderabad.json")); await text(get("https://x.test/map.js"));
online = false;
console.log(JSON.stringify([await text(get("https://x.test/data/hyderabad.json")), await text(get("https://x.test/map.js"))]));""")
    assert out[0][2] == "1" and out[1][2] is None


@needs_node
def test_a_failing_host_is_treated_like_no_signal_when_a_copy_exists():
    out = run("""
await text(get("https://x.test/data/hyderabad.json"));
status = 503;
console.log(JSON.stringify([await text(get("https://x.test/data/hyderabad.json")), await text(get("https://x.test/never-seen.js"))]));""")
    assert out[0][0] == 200 and out[0][2] == "1"           # the kept copy, marked
    assert out[1][0] == 503                                # nothing kept: the host's own answer is shown


@needs_node
def test_a_navigation_with_nothing_kept_falls_back_to_the_page_and_a_plain_asset_does_not():
    out = run("""
await fire("install");
online = false;
console.log(JSON.stringify([await text(get("https://x.test/somewhere", "navigate")), await text(get("https://x.test/other.png"))]));""")
    assert out[0][0] == 200 and out[0][1].startswith("shell") and out[1][0] == "error"


@needs_node
def test_only_plain_gets_to_this_site_and_the_pinned_map_library_are_handled():
    out = run("""
const asked = (url, method = "GET") => { let hit = false;
  listeners.fetch({ request: { url, method, mode: "no-cors" }, respondWith: () => { hit = true; } }); return hit; };
console.log(JSON.stringify([
  asked("https://x.test/index.html"),
  asked("https://x.test/uploads", "POST"),
  asked("https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"),
  asked("https://tiles.openfreemap.org/planet/20260101/5/1/2.pbf"),
  asked("https://fonts.googleapis.com/css2?family=Inter"),
]));""")
    assert out == [True, False, True, False, False]


@needs_node
def test_a_new_version_removes_the_old_cache():
    out = run("""
await cacheFor("nirmaldhara-v0").put("https://x.test/a", new Response("old"));
await cacheFor("something-else").put("https://x.test/a", new Response("not ours"));
await fire("activate");
console.log(JSON.stringify([...stores.keys()]));""")
    assert "nirmaldhara-v0" not in out and "something-else" in out


def test_the_library_the_worker_keeps_is_the_one_the_page_loads():
    page = (WEB / "index.html").read_text("utf-8")
    worker = (WEB / "sw.js").read_text("utf-8")
    urls = re.findall(r'"(https://unpkg\.com/maplibre-gl@[^"]+)"', worker)
    assert len(urls) == 2
    for url in urls:
        assert url in page, url
    assert 'navigator.serviceWorker.register("sw.js")' in page


def test_every_file_the_worker_keeps_exists():
    worker = (WEB / "sw.js").read_text("utf-8")
    shell = re.search(r"const SHELL = \[(.*?)\];", worker, re.S).group(1)
    names = re.findall(r'"([^"]+)"', shell)
    assert len(names) > 20
    for name in names:
        assert name == "./" or (WEB / name).is_file(), name


def test_the_manifest_is_installable_and_its_colours_are_tokens():
    manifest = json.loads((WEB / "manifest.json").read_text("utf-8"))
    tokens = (WEB / "tokens.css").read_text("utf-8").lower()
    assert manifest["display"] == "standalone" and manifest["start_url"] == "./"
    assert manifest["theme_color"].lower() in tokens and manifest["background_color"].lower() in tokens
    assert {icon["sizes"] for icon in manifest["icons"]} >= {"192x192", "512x512"}
    for icon in manifest["icons"]:
        assert (WEB / icon["src"]).is_file()
    assert f'content="{manifest["theme_color"]}"' in (WEB / "index.html").read_text("utf-8")


def test_the_icons_are_real_pngs_of_the_stated_size():
    for size in (192, 512):
        data = (WEB / f"icon-{size}.png").read_bytes()
        assert data[:8] == b"\x89PNG\r\n\x1a\n"
        assert struct.unpack(">II", data[16:24]) == (size, size)
        start = data.index(b"IDAT")
        length = struct.unpack(">I", data[start - 4:start])[0]
        assert len(zlib.decompress(data[start + 4:start + 4 + length])) == size * (size * 3 + 1)


@needs_node
def test_a_map_file_served_from_the_kept_copy_shows_as_a_refresh_that_did_not_happen():
    doc = {"city": "hyderabad", "generated_at": 1000,
           "fields": ["i", "n", "y", "x", "s", "b", "l", "h", "t", "u", "c"],
           "sites": [["a", "A", 17.4, 78.4, "CLEAR", "B0", 0, 0, 0, 0, 0]]}
    script = f"""
import {{ startLive }} from "{(WEB / 'data.js').as_uri()}";
globalThis.document = {{ hidden: false, addEventListener() {{}}, removeEventListener() {{}} }};
const answer = (marked) => async () => ({{ ok: true, json: async () => ({json.dumps(doc)}),
  headers: {{ get: (n) => (n === "x-offline-copy" && marked ? "1" : null) }} }});
const result = [];
for (const marked of [false, true]) {{
  let last;
  const live = startLive({{ url: "x", fetchFn: answer(marked), nowFn: () => 1_060_000, interval: 1e9,
    onData: () => {{}}, onStatus: (n) => {{ last = n; }} }});
  await live.refresh(); live.stop();
  result.push(last);
}}
console.log(JSON.stringify(result));"""
    out = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True, encoding="utf-8")
    assert out.returncode == 0, out.stderr
    fresh, from_copy = json.loads(out.stdout.strip().splitlines()[-1])
    assert fresh is None                                 # a minute old and live: nothing to say
    assert from_copy["level"] == "stale" and from_copy["text"].startswith("Could not refresh. Last updated")
