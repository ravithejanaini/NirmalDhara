// The cross-section: a car, a scooter and a person's legs to one scale, with the water drawn
// across all three at the measured range. "Not safe for cars" is seen before it is read.
//
// One unit of the drawing is one centimetre. The ground is y = 0 and up is negative. The top
// is cropped at one metre: what matters happens below the knee.

import { NO_GO_CM } from "./rules.js";

export const CAR_WHEEL_CM = 62;        // the same sizes the photo reader is told (reader.py)
export const SCOOTER_WHEEL_CM = 43;
export const KNEE_CM = 46;
const TOP = 100, WIDTH = 420;
const WAVE = { period: 28, height: 1.6 };

/** What the drawing shows for a site, in centimetres. Pure, so it can be checked without a browser. */
export function sectionModel(site) {
  const low = Math.max(0, Math.min(site.low, TOP)), high = Math.max(0, Math.min(site.high, TOP));
  const tone = high < 12 ? "shallow" : high <= 30 ? "water" : "deep";
  const share = (wheel) => Math.min(1, high / wheel);
  return {
    low, high, tone,
    carWheelShare: share(CAR_WHEEL_CM), scooterWheelShare: share(SCOOTER_WHEEL_CM),
    limits: { car: NO_GO_CM.car, two_wheeler: NO_GO_CM.two_wheeler, pedestrian: NO_GO_CM.pedestrian },
    label: `Drawing to scale: water ${Math.round(site.low)} to ${Math.round(site.high)} centimetres deep ` +
      `beside a car wheel, a scooter and a person's legs. It reaches ${fraction(share(CAR_WHEEL_CM))} of the car's wheel. ` +
      `Limits are marked at ${NO_GO_CM.two_wheeler}, ${NO_GO_CM.car} and ${NO_GO_CM.pedestrian} centimetres.`,
  };
}

function fraction(share) {
  if (share >= 0.95) return "the top";
  if (share >= 0.6) return "about two thirds";
  if (share >= 0.42) return "about half";
  if (share >= 0.28) return "about a third";
  if (share >= 0.18) return "about a quarter";
  return "the bottom";
}

function wave(closed) {
  let d = `M ${-WAVE.period} 0`;
  for (let x = -WAVE.period; x < WIDTH + WAVE.period; x += WAVE.period) {
    d += ` q ${WAVE.period / 4} ${-WAVE.height} ${WAVE.period / 2} 0 t ${WAVE.period / 2} 0`;
  }
  return closed ? `${d} V ${TOP + 20} H ${-WAVE.period} Z` : d;
}

// A limit: a fine tick at that height beside the figure, with its number.
const tick = (x, cm) => `
    <g class="section-limit">
      <path d="M ${x} ${-cm} h 12" />
      <text x="${x}" y="${-cm - 4}">${cm}</text>
    </g>`;

const R_CAR = CAR_WHEEL_CM / 2, R_SCOOTER = SCOOTER_WHEEL_CM / 2;

// The front of a car, cropped behind the front door: bumper, bonnet, windscreen, one wheel.
const CAR = `
    <g class="section-figure" transform="translate(24 0)">
      <path class="section-body" d="M 132 -17 H 124 A 36 36 0 0 0 52 -17 H 16 Q 6 -17 6 -28 V -46 Q 6 -57 18 -59 L 64 -66 L 98 -100 H 132 Z" />
      <path d="M 132 -17 H 124 A 36 36 0 0 0 52 -17 H 16 Q 6 -17 6 -28 V -46 Q 6 -57 18 -59 L 64 -66 L 98 -100" />
      <path d="M 12 -50 q 9 -4 18 -1" />
      <path d="M 70 -66 v 49" />
      <circle class="section-body" cx="88" cy="${-R_CAR}" r="${R_CAR}" />
      <circle cx="88" cy="${-R_CAR}" r="19" />
      <circle cx="88" cy="${-R_CAR}" r="4" />
    </g>`;

// A scooter, whole: two small wheels, footboard, seat, front column and handlebar.
const SCOOTER = `
    <g class="section-figure" transform="translate(196 0)">
      <path class="section-body" d="M 44 -28 H 96 C 106 -30 104 -52 108 -62 V -74 H 158 C 168 -68 168 -50 158 -42 L 140 -46 A 26 26 0 0 0 108 -22 L 96 -24 Z" />
      <path d="M 44 -28 H 96 C 106 -30 104 -52 108 -62 V -74 H 158 C 168 -68 168 -50 158 -42" />
      <path class="section-body" d="M 30 -44 C 30 -62 34 -76 40 -92 L 50 -90 C 46 -70 46 -44 52 -28 H 44 C 40 -34 34 -40 30 -44 Z" />
      <path d="M 30 -44 C 30 -62 34 -76 40 -92 L 50 -90 C 46 -70 46 -44 52 -28" />
      <path d="M 32 -98 L 54 -92" />
      <path d="M 24 ${-R_SCOOTER} L 42 -92" />
      <circle class="section-body" cx="24" cy="${-R_SCOOTER}" r="${R_SCOOTER}" />
      <circle cx="24" cy="${-R_SCOOTER}" r="8" />
      <circle class="section-body" cx="134" cy="${-R_SCOOTER}" r="${R_SCOOTER}" />
      <circle cx="134" cy="${-R_SCOOTER}" r="8" />
    </g>`;

// A person from the waist down, walking: two legs with a bend at the knee (46 cm) and shoes.
const PERSON = `
    <g class="section-figure" transform="translate(366 0)">
      <path d="M 6 -100 C 4 -82 7 -62 9 -${KNEE_CM} C 9 -32 7 -18 8 -7 L 3 -3 V 0 H 21 Q 21 -5 16 -6 L 17 -8 C 18 -20 21 -32 21 -${KNEE_CM} C 22 -62 24 -82 25 -100" />
      <path d="M 27 -100 C 27 -82 28 -62 30 -${KNEE_CM} C 30 -32 30 -18 31 -7 L 30 -3 V 0 H 48 Q 48 -5 43 -6 L 41 -8 C 42 -20 43 -32 42 -${KNEE_CM} C 43 -62 45 -82 46 -100" />
      <path d="M 6 -100 H 46" />
    </g>`;

/** The drawing, with the water parked at `from` (centimetres) so it can be seen to move to its level. */
export function sectionSvg(model, from = { low: 0, high: 0 }) {
  return `
  <svg class="section" viewBox="0 ${-TOP - 4} ${WIDTH} ${TOP + 12}" role="img" aria-label="${model.label}" data-tone="${model.tone}">
    <defs><clipPath id="section-clip"><rect x="0" y="${-TOP - 4}" width="${WIDTH}" height="${TOP + 4}" /></clipPath></defs>
    ${CAR}${SCOOTER}${PERSON}
    <g clip-path="url(#section-clip)">
      <g class="section-level section-band" style="transform: translateY(${-from.high}px)"><path d="${wave(true)}" /></g>
      <g class="section-level section-solid" style="transform: translateY(${-from.low}px)"><path d="${wave(true)}" /></g>
      <g class="section-level section-surface" style="transform: translateY(${-from.high}px)"><path d="${wave(false)}" /></g>
    </g>
    <path class="section-ground" d="M 0 0 H ${WIDTH}" />
    ${tick(4, model.limits.car)}${tick(178, model.limits.two_wheeler)}${tick(350, model.limits.pedestrian)}
  </svg>`;
}

let shown = null;      // the site and levels last drawn, so an update moves the water from there

/** Draw the cross-section into `slot` for a site with water; empty the slot for a dry one. */
export function mountSection(slot, site) {
  if (!(site.high > 0)) {
    slot.innerHTML = "";
    shown = null;
    return;
  }
  const model = sectionModel(site);
  const from = shown && shown.id === site.id ? shown : { low: 0, high: 0 };
  slot.innerHTML = sectionSvg(model, from);
  shown = { id: site.id, low: model.low, high: model.high };
  const svg = slot.querySelector("svg");
  svg.getBoundingClientRect();                 // commit the starting level before moving it
  svg.querySelector(".section-band").style.transform = `translateY(${-model.high}px)`;
  svg.querySelector(".section-surface").style.transform = `translateY(${-model.high}px)`;
  svg.querySelector(".section-solid").style.transform = `translateY(${-model.low}px)`;
}

export function forgetSection() {
  shown = null;
}
