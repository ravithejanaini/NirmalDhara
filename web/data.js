// Live data for the map: fetch the city file, work out what changed, and say when it is old.
//
// The file is data/hyderabad.json, written by the publisher (DESIGN.md 15.3). Everything here
// is pure except `startLive`, so the rules can be checked without a browser.

import { ageWords } from "./glyph.js";

export const POLL_MS = 20_000;
// The publisher rewrites the file at least every 5 minutes while it runs, and the 15-minute
// schedule is its backstop. Older than this means the data is no longer being kept current.
export const STALE_AFTER_S = 20 * 60;

const FIELD_NAMES = {
  i: "id", n: "name", y: "lat", x: "lon", s: "state", b: "band",
  l: "low", h: "high", t: "trusted", u: "updated", c: "confidence",
};

/** The file as {generatedAt, sites: Map(id -> site)}, reading columns by the names it declares. */
export function parseDocument(doc) {
  const names = doc.fields.map((field) => FIELD_NAMES[field] || field);
  const sites = new Map();
  for (const row of doc.sites) {
    const site = {};
    names.forEach((name, index) => { site[name] = row[index]; });
    site.trusted = site.trusted === 1;
    site.updated = site.updated ?? 0;            // 0 means nothing reported
    site.confidence = site.confidence ?? 0;      // a file without the column counts as unsure
    sites.set(site.id, site);
  }
  return { generatedAt: doc.generated_at, sites };
}

/** Which site ids were added, changed or removed between two parsed files. */
export function diffSites(previous, next) {
  const before = previous ? previous.sites : new Map();
  const added = [], changed = [], removed = [];
  for (const [id, site] of next.sites) {
    if (!before.has(id)) added.push(id);
    else if (JSON.stringify(before.get(id)) !== JSON.stringify(site)) changed.push(id);
  }
  for (const id of before.keys()) if (!next.sites.has(id)) removed.push(id);
  return { added, changed, removed };
}

/**
 * The notice to show, or null when all is well. `age` is how old the data on screen is, in
 * seconds. Shown when a fetch has failed, or when the file itself has stopped being refreshed.
 */
export function statusFor({ loaded, failed, ageSeconds }) {
  if (!loaded) return failed ? { text: "The map data could not be loaded.", level: "error" } : null;
  if (failed) {
    return { text: `Could not refresh. Last updated ${ageWords(ageSeconds)} ago`, level: "stale" };
  }
  if (ageSeconds > STALE_AFTER_S) {
    return { text: `Last updated ${ageWords(ageSeconds)} ago`, level: "stale" };
  }
  return null;
}

/**
 * Poll the file. Calls `onData({data, diff, now})` whenever it loads, and
 * `onStatus(notice | null)` after every attempt. A failed fetch keeps the last data on screen.
 * Pauses while the page is hidden and fetches at once when it returns.
 */
export function startLive({
  url, onData, onStatus, interval = POLL_MS,
  fetchFn = (...args) => fetch(...args), nowFn = () => Date.now(),
}) {
  let current = null, offset = 0, timer = null, stopped = false;
  const serverNow = () => (nowFn() + offset) / 1000;

  async function poll() {
    let failed = false;
    try {
      const response = await fetchFn(url, { headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const next = parseDocument(await response.json());
      const header = response.headers && response.headers.get && response.headers.get("date");
      if (header && !Number.isNaN(Date.parse(header))) offset = Date.parse(header) - nowFn();
      const diff = diffSites(current, next);
      const first = current === null;
      current = next;
      if (first || diff.added.length || diff.changed.length || diff.removed.length) {
        onData({ data: current, diff, now: serverNow() });
      }
    } catch (error) {
      failed = true;
      console.warn("map data:", error.message);
    }
    onStatus(statusFor({
      loaded: current !== null, failed,
      ageSeconds: current ? Math.max(0, serverNow() - current.generatedAt) : 0,
    }));
  }

  function schedule() {
    if (stopped) return;
    timer = setTimeout(async () => {
      if (!(typeof document !== "undefined" && document.hidden)) await poll();
      schedule();
    }, interval);
  }

  const onVisible = () => { if (!document.hidden) { clearTimeout(timer); poll().then(schedule); } };
  if (typeof document !== "undefined") document.addEventListener("visibilitychange", onVisible);

  poll().then(schedule);
  return {
    refresh: poll,
    now: serverNow,
    current: () => current,
    stop() {
      stopped = true;
      clearTimeout(timer);
      if (typeof document !== "undefined") document.removeEventListener("visibilitychange", onVisible);
    },
  };
}
