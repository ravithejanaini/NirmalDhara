// Offline last-known: the page and the last map file are kept, so the map still opens with no
// signal and says how old its data is.
//
// Network first for everything on this site, so a deploy is seen at once and a live map is
// never stale by this file's doing. The copy is used only when the network or the host fails. A map file
// served that way carries the header below, which data.js reads as "could not refresh".
//
// Not kept: map tiles and fonts from other hosts (their terms are not ours to extend), and
// anything that is not a plain GET. Offline, the sites show on a blank ground.

const VERSION = "v2";
const CACHE = `nirmaldhara-${VERSION}`;
const OFFLINE_HEADER = "x-offline-copy";
// Kept at install so the very first offline visit already works. Cross-origin files are
// fetched without CORS, as the page's own script and style tags do, and kept as they come.
const SHELL = [
  "./", "index.html", "tokens.css", "base.css", "glyph.css", "map.css", "sheet.css", "guide.css",
  "map.js", "data.js", "sites.js", "sheet.js", "section.js", "guide.js", "glyph.js", "rules.js",
  "style.json", "manifest.json", "icon-192.png", "icon-512.png", "offenders.html", "offenders.css", "offenders.js",
];
const LIBRARY = [
  "https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js",
  "https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css",
];

/** Whether this request is one the worker should answer at all. */
function handles(request, origin) {
  if (request.method !== "GET") return false;
  const url = new URL(request.url);
  return url.origin === origin || LIBRARY.includes(url.href);
}

/** The cached copy of a map file marked as an offline copy, so the page can say so. */
function marked(response) {
  const headers = new Headers(response.headers);
  headers.set(OFFLINE_HEADER, "1");
  return new Response(response.body, { status: response.status, statusText: response.statusText, headers });
}

async function install() {
  const cache = await caches.open(CACHE);
  // One missing file must not stop the rest from being kept.
  await Promise.allSettled([
    ...SHELL.map((path) => cache.add(path)),
    // cache.add refuses an opaque answer, so these are fetched and put.
    ...LIBRARY.map(async (href) => { const request = new Request(href, { mode: "no-cors" }); await cache.put(request, await fetch(request)); }),
  ]);
}

async function activate() {
  for (const name of await caches.keys()) {
    if (name.startsWith("nirmaldhara-") && name !== CACHE) await caches.delete(name);
  }
  await self.clients.claim();
}

async function answer(request) {
  const cache = await caches.open(CACHE);
  const offlineCopy = async () => {
    const kept = await cache.match(request, { ignoreSearch: true });
    if (kept) return new URL(request.url).pathname.endsWith("/data/hyderabad.json") ? marked(kept) : kept;
    if (request.mode === "navigate") return cache.match("index.html");
    return undefined;
  };
  let fresh;
  try {
    fresh = await fetch(request);
  } catch (error) {
    const kept = await offlineCopy();
    if (kept) return kept;
    throw error;
  }
  if (fresh.ok || fresh.type === "opaque") {          // a cross-origin file fetched without CORS is opaque
    await cache.put(request, fresh.clone());
    return fresh;
  }
  // The host answered with an error (a server down counts as no signal): prefer the kept copy.
  return (await offlineCopy()) || fresh;
}

self.addEventListener("install", (event) => { event.waitUntil(install().then(() => self.skipWaiting())); });
self.addEventListener("activate", (event) => { event.waitUntil(activate()); });
self.addEventListener("fetch", (event) => {
  if (handles(event.request, self.location.origin)) event.respondWith(answer(event.request));
});
