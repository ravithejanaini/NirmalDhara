// The guide: a welcome on first open, a one-line summary of the city, and a key to the glyphs.
//
// `summaryModel` decides the summary's words and is pure, so the all-clear wording is checked
// without a browser. Nothing here asks for anything from the person; the welcome is remembered
// in the browser only if the browser lets it.

import { createGlyph } from "./glyph.js";

export const WELCOME_LINES = [
  "Floodwater depth at known waterlogging points in Hyderabad, read from photos.",
  "Tap a place to see whether bikes, autos, cars and people on foot can pass.",
  "The map updates by itself. Never enter moving water, whatever the depth.",
];

const places = (n) => `${n} place${n === 1 ? "" : "s"}`;

/** The summary line for the whole city, from the sites in the latest file. */
export function summaryModel(sites) {
  const n = sites.length;
  if (n === 0) return { text: "No places are being watched yet.", tone: "quiet" };
  const wet = sites.filter((s) => s.high > 0);
  const critical = sites.filter((s) => s.state === "CRITICAL");
  const watching = sites.filter((s) => s.state === "WATCH" && !(s.high > 0));
  if (wet.length === 0 && watching.length === 0) {
    return {
      text: `No water reported in Hyderabad right now. No heavy rain is forecast near the ${places(n)} watched.`,
      tone: "clear",
    };
  }
  if (wet.length === 0) {
    return {
      text: `No water reported yet. Heavy rain is forecast near ${watching.length} of ${places(n)}.`,
      tone: "watch",
    };
  }
  const worst = critical.length ? ` · ${critical.length} critical` : "";
  return { text: `${wet.length} of ${places(n)} have water${worst}`, tone: critical.length ? "critical" : "water" };
}

/** What the key explains. Each example is a site drawn by the real glyph, never a copy of it. */
export function legendItems(now) {
  const site = (over) => ({ id: "key", name: "Example", state: "WARNING", low: 0, high: 0, trusted: true,
    confidence: 0.8, updated: now - 240, ...over });
  return [
    { site: site({ state: "CLEAR" }), word: "Clear", text: "No water reported." },
    { site: site({ state: "WATCH" }), word: "Watch", text: "Heavy rain forecast. No water yet." },
    { site: site({ low: 4, high: 9 }), word: "Shallow", text: "Under 12 cm: pale water, low." },
    { site: site({ low: 14, high: 19 }), word: "Water", text: "Deeper: higher and darker." },
    { site: site({ low: 12, high: 17, trusted: false }), word: "One photo", text: "Notched edge: one unconfirmed photo." },
    { site: site({ state: "CRITICAL", low: 28, high: 38 }), word: "Critical", text: "Red ring: do not enter." },
    { site: site({ state: "RECEDING", low: 8, high: 13 }), word: "Falling", text: "Small arrow: the water is going down." },
    { site: site({ low: 13, high: 18, updated: now - 2700 }), word: "Old", text: "Faded: reading over 30 minutes old." },
  ];
}

const KEY = "nirmaldhara-welcome-seen";
const remembered = () => { try { return localStorage.getItem(KEY) === "1"; } catch { return false; } };
const remember = () => { try { localStorage.setItem(KEY, "1"); } catch { /* the browser said no: it will be shown again */ } };

const escape = (text) => String(text).replace(/[&<>"']/g, (c) => (
  { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

export class Guide {
  constructor(root, now) {
    this.root = root;
    this.now = now;
    root.innerHTML = `
      <section class="welcome paper sheet" id="welcome" role="region" aria-labelledby="welcome-title" hidden>
        <h2 class="display title" id="welcome-title">What this shows</h2>
        <ul class="welcome-lines">${WELCOME_LINES.map((l) => `<li>${escape(l)}</li>`).join("")}</ul>
        <button class="button" type="button" data-action="dismiss">Got it</button>
      </section>
      <section class="key paper sheet" id="key" role="dialog" aria-labelledby="key-title" hidden></section>
      <div class="bar">
        <button class="button key-button" type="button" aria-expanded="false" aria-controls="key" data-action="key">Key</button>
        <p class="summary-line" id="summary-line" role="status" aria-live="polite"></p>
      </div>`;
    this.welcome = root.querySelector("#welcome");
    this.key = root.querySelector("#key");
    this.button = root.querySelector(".key-button");
    this.line = root.querySelector("#summary-line");
    root.addEventListener("click", (event) => {
      const action = event.target.closest("[data-action]")?.dataset.action;
      if (action === "dismiss") this.dismissWelcome();
      if (action === "key") this.toggleKey();
      if (action === "close-key") this.closeKey();
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && !this.key.hidden) this.closeKey();
    });
    // One sheet at a time: opening a site closes the key.
    document.addEventListener("site-selected", () => this.closeKey(false));
  }

  /** Called with each new file's sites (an iterable of site objects). */
  update(sites) {
    const model = summaryModel([...sites]);
    this.line.textContent = model.text;
    this.line.dataset.tone = model.tone;
    if (!remembered() && this.welcome.hidden && !this.welcomeDone) this.welcome.hidden = false;
  }

  dismissWelcome() {
    this.welcome.hidden = true;
    this.welcomeDone = true;
    remember();
    this.button.focus({ preventScroll: true });
  }

  toggleKey() {
    this.key.hidden ? this.openKey() : this.closeKey();
  }

  openKey() {
    this.key.innerHTML = `
      <header class="key-head">
        <h2 class="display title" id="key-title" tabindex="-1">How to read the map</h2>
        <button class="sheet-close" type="button" aria-label="Close the key" data-action="close-key">
          <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M5 5l10 10M15 5L5 15" /></svg>
        </button>
      </header>
      <ul class="key-items">${legendItems(this.now()).map((item, i) => `
        <li class="key-item"><span class="key-glyph" data-slot="${i}"></span>
          <span><strong>${escape(item.word)}</strong><br><span class="muted small">${escape(item.text)}</span></span></li>`).join("")}
      </ul>
      <p class="muted small">Inside a glyph, solid water reaches the lowest likely depth, the lighter band above it the highest,
        and the dark line marks the cautious end. Colour is never the only sign: every state also has a shape.</p>`;
    legendItems(this.now()).forEach((item, i) => {
      const glyph = createGlyph(item.site, this.now());
      glyph.removeAttribute("role");
      glyph.setAttribute("aria-hidden", "true");
      this.key.querySelector(`[data-slot="${i}"]`).append(glyph);
    });
    this.key.hidden = false;
    this.button.setAttribute("aria-expanded", "true");
    this.key.querySelector("#key-title").focus({ preventScroll: true });
  }

  closeKey(returnFocus = true) {
    if (this.key.hidden) return;
    this.key.hidden = true;
    this.button.setAttribute("aria-expanded", "false");
    if (returnFocus) this.button.focus({ preventScroll: true });
  }
}
