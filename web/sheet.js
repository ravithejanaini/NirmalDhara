// The site sheet: what a resident sees after tapping a site. One question, answered in order:
// how deep, is it safe for me, how sure are we, how old is this.
//
// `sheetModel` decides every word and is pure, so it is checked against the Python rules
// (tests/test_sheet.py). `SiteSheet` only draws the model and handles opening and closing.

import { ageWords, STALE_S } from "./glyph.js";
import { bandFor, passability, MIN_CONFIDENCE, PASSABLE, NOT_SAFE, UNKNOWN } from "./rules.js";

// The same words as alerts.py, so the sheet and a text message never describe one depth two ways.
export const BAND_LABEL = {
  B0: "dry", B1: "ankle deep", B2: "shin deep", B3: "below the knee",
  B4: "about knee deep", B5: "above the knee",
};
// In a sentence ("bikes, scooters and autos") and as a row heading ("Bikes and scooters").
export const VEHICLES = [
  { id: "two_wheeler", inSentence: "bikes, scooters", row: "Bikes and scooters" },
  { id: "auto", inSentence: "autos", row: "Autos" },
  { id: "car", inSentence: "cars", row: "Cars" },
  { id: "suv", inSentence: "SUVs", row: "SUVs" },
  { id: "pedestrian", inSentence: "people on foot", row: "People on foot" },
];
export const MOVING_WATER = "Do not enter moving water at any depth.";

const WORDS = {
  [PASSABLE]: { word: "Passable with care", tone: "clear", mark: "tick" },
  [NOT_SAFE]: { word: "Not safe", tone: "critical", mark: "cross" },
  [UNKNOWN]: { word: "Unsure: treat as not safe", tone: "critical", mark: "query" },
};

function join(words) {
  return words.length === 1 ? words[0] : `${words.slice(0, -1).join(", ")} and ${words.at(-1)}`;
}

/** "Not safe for … . Passable with care for … ." The same sentence alerts.py builds. */
export function advice(answers) {
  const unsafe = VEHICLES.filter((v) => answers[v.id] !== PASSABLE).map((v) => v.inSentence);
  const safe = VEHICLES.filter((v) => answers[v.id] === PASSABLE).map((v) => v.inSentence);
  let text = unsafe.length ? `Not safe for ${join(unsafe)}.` : "";
  if (safe.length) text += ` Passable with care for ${join(safe)}.`;
  return text.trim();
}

/** Every word on the sheet for one site. `now` and `site.updated` are in seconds. */
export function sheetModel(site, now) {
  const wet = site.high > 0;
  const base = { id: site.id, name: site.name, state: site.state, wet, moving: MOVING_WATER };
  if (!wet) {
    const watching = site.state === "WATCH";
    return {
      ...base,
      band: watching ? "Watch" : "Clear",
      headline: "No water",
      sentence: watching
        ? "Heavy rain is forecast here. No water has been reported yet."
        : "No water has been reported here.",
      urgent: null, rows: [], notes: [], seen: null, trust: null,
    };
  }

  const answers = passability(site.low, site.high, site.confidence);
  const notes = [];
  if (site.confidence < MIN_CONFIDENCE) notes.push("This reading is uncertain, so nothing is marked passable.");
  if (now - site.updated > STALE_S) notes.push("This reading is old. The water may have changed since.");
  notes.push("Buses and trucks: no advice is given. Use the depth and your own judgement.");
  return {
    ...base,
    band: BAND_LABEL[bandFor(site.high)],
    headline: `${Math.round(site.low)}–${Math.round(site.high)} cm`,
    sentence: advice(answers),
    urgent: site.state === "CRITICAL" ? "Do not enter." : site.state === "RECEDING" ? "The water is falling." : null,
    rows: VEHICLES.map((v) => ({ id: v.id, label: v.row, answer: answers[v.id], ...WORDS[answers[v.id]] })),
    notes,
    seen: `Seen ${ageWords(now - site.updated)} ago`,
    trust: site.trusted ? "Confirmed" : "From one unconfirmed photo",
  };
}

// --- drawing ------------------------------------------------------------------------------

const MARKS = {
  tick: '<path d="M4 10.5l4 4 8-9" />',
  cross: '<path d="M5 5l10 10M15 5L5 15" />',
  query: '<path d="M7 7.5a3 3 0 1 1 4.2 2.7c-.8.4-1.2 1-1.2 1.8v.5" /><path d="M10 15.6v.1" />',
};

const escape = (text) => String(text).replace(/[&<>"']/g, (c) => (
  { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

export function sheetHtml(model) {
  const rows = model.rows.map((row) => `
      <li class="sheet-row">
        <span>${escape(row.label)}</span>
        <span class="sheet-answer is-${row.tone}">
          <svg class="sheet-mark" viewBox="0 0 20 20" aria-hidden="true">${MARKS[row.mark]}</svg>${escape(row.word)}
        </span>
      </li>`).join("");
  return `
    <div class="sheet-grab" aria-hidden="true"><div class="sheet-handle"></div></div>
    <header class="sheet-head">
      <h2 class="display title" id="sheet-title" tabindex="-1">${escape(model.name)}</h2>
      <button class="sheet-close" type="button" aria-label="Close">
        <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M5 5l10 10M15 5L5 15" /></svg>
      </button>
    </header>
    <p class="label">${escape(model.band)}</p>
    <p class="display hero sheet-depth">${escape(model.headline)}</p>
    ${model.urgent ? `<p class="sheet-urgent is-${model.state === "CRITICAL" ? "critical" : "clear"}">${escape(model.urgent)}</p>` : ""}
    <p class="sheet-sentence">${escape(model.sentence)}</p>
    <div class="sheet-section" data-slot="section"></div>
    ${rows ? `<hr class="rule"><ul class="sheet-rows">${rows}</ul>` : ""}
    <hr class="rule">
    ${model.seen ? `<p class="sheet-meta"><span>${escape(model.seen)}</span><span class="${model.trust === "Confirmed" ? "" : "is-critical"}">${escape(model.trust)}</span></p>` : ""}
    ${model.notes.map((note) => `<p class="muted small">${escape(note)}</p>`).join("")}
    <p class="sheet-moving">${escape(model.moving)}</p>
    <button class="button sheet-done" type="button">Close</button>`;
}

export class SiteSheet {
  constructor(element, now) {
    this.element = element;
    this.now = now;
    this.site = null;
    this.returnTo = null;
    element.addEventListener("click", (event) => {
      if (event.target.closest(".sheet-close, .sheet-done")) this.close();
    });
    this.watchGrab();
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && this.site) this.close();
    });
    document.addEventListener("site-selected", (event) => this.open(event.detail.site, event.detail.source));
  }

  /** The handle at the top of the sheet: drag it down to close, or tap it. One hand reaches it
   *  when the sheet's top corner is out of reach. */
  watchGrab() {
    const el = this.element;
    let start = null;
    el.addEventListener("pointerdown", (event) => {
      const grab = event.target.closest(".sheet-grab");
      if (!grab) return;
      start = { y: event.clientY, dy: 0 };
      grab.setPointerCapture(event.pointerId);
      el.style.transition = "none";
    });
    el.addEventListener("pointermove", (event) => {
      if (!start) return;
      start.dy = Math.max(0, event.clientY - start.y);
      el.style.transform = `translateY(${start.dy}px)`;
    });
    const end = (event) => {
      if (!start) return;
      const { dy } = start;
      start = null;
      el.style.transition = "";
      el.style.transform = "";
      // A tap (almost no movement) or a pull down of 80 px or more closes it.
      if (event.type !== "pointercancel" && (dy < 6 || dy >= 80)) this.close();
    };
    el.addEventListener("pointerup", end);
    el.addEventListener("pointercancel", end);
  }

  open(site, returnTo) {
    const wasOpen = Boolean(this.site);
    this.site = site;
    this.returnTo = returnTo || this.returnTo;
    this.draw();
    this.element.hidden = false;
    // Let the browser register the starting position before sliding the sheet up.
    if (!wasOpen) requestAnimationFrame(() => this.element.classList.add("is-open"));
    this.element.querySelector("#sheet-title").focus({ preventScroll: true });
  }

  /** New data for the open site: redraw in place, keeping focus where it is. */
  update(site) {
    if (!this.site || site.id !== this.site.id) return;
    // Redrawing replaces what was focused, so note where focus was before, not after.
    const active = document.activeElement;
    const inside = this.element.contains(active);
    const onClose = inside && Boolean(active.closest(".sheet-close"));
    this.site = site;
    this.draw();
    if (inside) this.element.querySelector(onClose ? ".sheet-close" : "#sheet-title").focus({ preventScroll: true });
  }

  draw() {
    const model = sheetModel(this.site, this.now());
    this.element.dataset.state = model.state;
    this.element.innerHTML = sheetHtml(model);
    this.element.dispatchEvent(new CustomEvent("sheet-drawn", { detail: { model, site: this.site }, bubbles: true }));
  }

  close() {
    this.site = null;
    this.element.classList.remove("is-open");
    const done = () => { if (!this.site) this.element.hidden = true; };
    const slow = !matchMedia("(prefers-reduced-motion: reduce)").matches;
    slow ? setTimeout(done, 320) : done();
    if (this.returnTo && document.contains(this.returnTo)) this.returnTo.focus({ preventScroll: true });
  }
}
