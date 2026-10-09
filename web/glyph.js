// The depth glyph: a site drawn as a small cross-section of the road that fills with water.
//
// One mark carries five things:
//   level        solid water to the low end of the range, a lighter band up to the high end
//   depth        the blue darkens with the high end: under 12 cm, 12 to 30, above 30
//   trust        a clean edge when confirmed, a perforated edge when it rests on one photo
//   urgency      an outer ring: fine and breathing for a watch, firm and Signal for critical
//   age          faded when the reading is more than 30 minutes old
//
// Water is drawn on a paper disc, never straight onto the night map (tokens.css explains why).
// `glyphState` is pure, so the same rules can be checked without a browser.

const SVG = "http://www.w3.org/2000/svg";

export const SIZE = 44;          // the box, and the touch target
export const RADIUS = 14;        // the disc: 28 px across
export const FULL_CM = 60;       // the disc is full at this depth
export const STALE_S = 30 * 60;
const CENTRE = SIZE / 2;
const FLOOR = CENTRE + RADIUS;   // y of the bottom of the disc
const HIDDEN = FLOOR + 4;        // a level parked below the disc: no water
const WAVE = { period: 14, height: 1.3 };

/** Where the water surface sits, in px from the top of the box, for a depth in cm. */
export function levelY(depthCm) {
  if (!(depthCm > 0)) return HIDDEN;
  return FLOOR - (Math.min(depthCm, FULL_CM) / FULL_CM) * (2 * RADIUS);
}

/** Everything the drawing needs, from one site. `now` and `site.updated` are in seconds. */
export function glyphState(site, now) {
  const wet = site.high > 0;
  const tone = !wet ? "none" : site.high < 12 ? "shallow" : site.high <= 30 ? "water" : "deep";
  const ring = site.state === "CRITICAL" ? "critical" : site.state === "WATCH" && !wet ? "watch" : "none";
  const stale = wet && now - site.updated > STALE_S;
  const unconfirmed = wet && !site.trusted;
  const falling = site.state === "RECEDING";
  const words = {
    CLEAR: "clear", WATCH: "watch", WARNING: "warning", CRITICAL: "critical", RECEDING: "receding",
  }[site.state] || "unknown";
  const depth = wet ? `${Math.round(site.low)} to ${Math.round(site.high)} centimetres` : "no water reported";
  const age = wet ? `, seen ${ageWords(now - site.updated)} ago` : "";
  return {
    tone, ring, stale, unconfirmed, falling,
    lowY: levelY(site.low), highY: levelY(site.high),
    label: `${site.name}, ${words}, ${depth}${unconfirmed ? ", from one unconfirmed photo" : ""}${age}`,
  };
}

export function ageWords(seconds) {
  const minutes = Math.max(0, Math.round(seconds / 60));
  if (minutes < 1) return "less than a minute";
  if (minutes < 60) return `${minutes} minute${minutes === 1 ? "" : "s"}`;
  const hours = Math.round(minutes / 60);
  return `${hours} hour${hours === 1 ? "" : "s"}`;
}

// A strip of water wider than the disc, its surface a sine line centred on y = 0. Drawn two
// periods too wide so it can drift one period sideways and loop without a seam.
function wavePath(closed) {
  const { period, height } = WAVE;
  let d = `M ${-period} 0`;
  for (let x = -period; x < SIZE + period; x += period) {
    d += ` q ${period / 4} ${-height} ${period / 2} 0 t ${period / 2} 0`;
  }
  return closed ? `${d} V ${SIZE} H ${-period} Z` : d;
}

function el(name, attributes, parent) {
  const node = document.createElementNS(SVG, name);
  for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, value);
  if (parent) parent.append(node);
  return node;
}

let serial = 0;

/** Build the glyph for a site. Call `updateGlyph` with newer data to move the water. */
export function createGlyph(site, now = Date.now() / 1000) {
  const clipId = `glyph-clip-${++serial}`;
  const svg = el("svg", { class: "glyph", viewBox: `0 0 ${SIZE} ${SIZE}`, width: SIZE, height: SIZE, role: "img" });

  el("circle", { class: "glyph-ring", cx: CENTRE, cy: CENTRE, r: RADIUS + 4.5 }, svg);
  el("circle", { class: "glyph-disc", cx: CENTRE, cy: CENTRE, r: RADIUS }, svg);

  const clip = el("clipPath", { id: clipId }, el("defs", {}, svg));
  el("circle", { cx: CENTRE, cy: CENTRE, r: RADIUS }, clip);
  const water = el("g", { "clip-path": `url(#${clipId})` }, svg);
  for (const part of ["band", "solid", "surface"]) {
    const level = el("g", { class: `glyph-level glyph-${part}` }, water);
    el("path", { class: "glyph-wave", d: wavePath(part !== "surface") }, level);
  }

  // Receding: a small downward mark in the dry part of the disc.
  el("path", { class: "glyph-falling", d: `M ${CENTRE - 3} ${CENTRE - 8.5} l 3 3 l 3 -3` }, svg);
  // The edge. Dashes in the ground colour bite into the disc when the reading is unconfirmed.
  el("circle", { class: "glyph-edge", cx: CENTRE, cy: CENTRE, r: RADIUS }, svg);

  // Start with the water below the disc so the first update is seen to rise.
  for (const level of svg.querySelectorAll(".glyph-level")) level.style.transform = `translateY(${HIDDEN}px)`;
  svg.getBoundingClientRect();       // commit that starting position before moving it
  updateGlyph(svg, site, now);
  return svg;
}

export function updateGlyph(svg, site, now = Date.now() / 1000) {
  const state = glyphState(site, now);
  svg.dataset.tone = state.tone;
  svg.dataset.ring = state.ring;
  svg.toggleAttribute("data-stale", state.stale);
  svg.toggleAttribute("data-unconfirmed", state.unconfirmed);
  svg.toggleAttribute("data-falling", state.falling);
  svg.setAttribute("aria-label", state.label);
  svg.querySelector(".glyph-solid").style.transform = `translateY(${state.lowY}px)`;
  svg.querySelector(".glyph-band").style.transform = `translateY(${state.highY}px)`;
  svg.querySelector(".glyph-surface").style.transform = `translateY(${state.highY}px)`;
  return state;
}
