// A wheel read by a person: where the water stands on a wheel, as a depth.
//
// A copy of src/nirmaldhara/wheel.py, as rules.js is a copy of bands.py. The two must give the same
// answers: tests/test_wheel_page.py compares every figure and, where Node is installed, runs this file.
//
// An answer is the depth where the vehicle stands, and a road is usually deeper further in. So this
// can say a class of road user must not enter and never says that one may: the confidence it hands
// to the rules is under the mark at which they will call a road passable.

import { passability, NOT_SAFE, PASSABLE } from "./rules.js";

export const ASK = "Find a parked car, auto or bike standing in the water. Where has the water come to on its wheel?";
export const MARKS = {
  tyre: "Only the tyre is wet. The rim is dry.",
  rim: "The rim is wet, less than halfway from its edge to the hub.",
  third: "More than halfway to the hub. The hub is still dry.",
  axle: "The hub is under water. The top of the tyre still shows.",
  over: "The tyre is covered.",
};
// Depth in centimetres for each answer, from standard tyre sizes.
export const TABLE = {
  car: { tyre: [0, 12], rim: [12, 20], third: [20, 31], axle: [31, 62], over: [62, 62] },
  motorcycle: { tyre: [0, 9], rim: [9, 20], third: [20, 31], axle: [31, 61], over: [61, 61] },
  scooter: { tyre: [0, 9], rim: [9, 14], third: [14, 22], axle: [22, 43], over: [43, 43] },
};
export const SAME_AS = { auto: "scooter" };
export const WHEELS = { car: "Car", auto: "Auto", motorcycle: "Motorcycle", scooter: "Scooter" };
export const SOMEWHERE = 0.5;

// The same rows, in the same order, as the sheet on the map (sheet.js).
export const CLASSES = [
  { id: "two_wheeler", row: "Bikes and scooters" },
  { id: "auto", row: "Autos" },
  { id: "car", row: "Cars" },
  { id: "suv", row: "SUVs" },
  { id: "pedestrian", row: "People on foot" },
];
export const WORD_NOT_SAFE = "Not safe";
export const WORD_UNSURE = "Unsure: treat as not safe";
// How far up the drawn wheel the water is shown for each answer, as a share of its height.
const DRAWN = { tyre: 0.14, rim: 0.28, third: 0.44, axle: 0.74, over: 1.0 };

/** [low, high] in centimetres where the vehicle stands. "over" is a floor. */
export function depth(wheel, mark) {
  const row = TABLE[SAME_AS[wheel] ?? wheel];
  if (!row || !row[mark]) throw new Error(`no such wheel or mark: ${wheel}, ${mark}`);
  return row[mark];
}

/** What one answer says of each class, in the rules' own words. Never "passable". */
export function answers(wheel, mark) {
  const [low, high] = depth(wheel, mark);
  return passability(low, high, SOMEWHERE);
}

export function depthWords(wheel, mark) {
  const [low, high] = depth(wheel, mark);
  if (mark === "over") return `Over ${low} cm`;
  return low === 0 ? `Under ${high} cm` : `${low} to ${high} cm`;
}

/** The five rows the page shows: [{ row, word, ruledOut }]. */
export function verdicts(wheel, mark) {
  const said = answers(wheel, mark);
  return CLASSES.map(({ id, row }) => {
    if (said[id] === PASSABLE) throw new Error("a wheel alone must never clear a road");
    return { row, word: said[id] === NOT_SAFE ? WORD_NOT_SAFE : WORD_UNSURE, ruledOut: said[id] === NOT_SAFE };
  });
}

function wheelArt(mark) {
  const top = 46 - 44 * DRAWN[mark];
  return `<svg class="mark-art" viewBox="0 0 48 48" width="48" height="48" aria-hidden="true" focusable="false">
    <defs><clipPath id="clip-${mark}"><circle cx="24" cy="24" r="22"/></clipPath></defs>
    <circle class="art-tyre" cx="24" cy="24" r="21"/>
    <circle class="art-rim" cx="24" cy="24" r="13.5"/>
    <circle class="art-hub" cx="24" cy="24" r="2.5"/>
    <rect class="art-water" x="0" y="${top.toFixed(1)}" width="48" height="48" clip-path="url(#clip-${mark})"/>
    <line class="art-level" x1="0" x2="48" y1="${top.toFixed(1)}" y2="${top.toFixed(1)}"/>
  </svg>`;
}

function choice(group, value, words, art, checked) {
  return `<label class="pick-one${art ? " pick-mark" : ""}">
    <input type="radio" name="${group}" value="${value}"${checked ? " checked" : ""}>
    ${art}<span class="pick-words">${words}</span>
  </label>`;
}

/** Draws the two questions and keeps the answer below them in step with what is chosen. */
export function startPage(doc) {
  const form = doc.getElementById("wheel-form");
  doc.getElementById("ask").textContent = ASK;
  doc.getElementById("wheels").innerHTML =
    Object.entries(WHEELS).map(([id, name]) => choice("wheel", id, name, "", id === "car")).join("");
  doc.getElementById("marks").innerHTML =
    Object.entries(MARKS).map(([id, words]) => choice("mark", id, words, wheelArt(id), false)).join("");
  const said = doc.getElementById("said");

  function show() {
    const data = new FormData(form);
    const wheel = data.get("wheel"), mark = data.get("mark");
    if (!wheel || !mark) {
      said.innerHTML = `<p class="muted">Choose where the water has come to.</p>`;
      return;
    }
    const whose = WHEELS[wheel].toLowerCase();
    said.innerHTML = `
      <h2 class="display title said-depth">${depthWords(wheel, mark)}</h2>
      <p class="muted small">where that ${whose} stands. The road is usually deeper further in.</p>
      <ul class="plain verdicts">
        ${verdicts(wheel, mark).map((v) => `<li><span>${v.row}</span><strong class="is-critical">${v.word}</strong></li>`).join("")}
      </ul>`;
  }
  form.addEventListener("change", show);
  form.addEventListener("submit", (event) => event.preventDefault());
  show();
}
