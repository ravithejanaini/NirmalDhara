// Depth bands and per-vehicle passability, in the browser.
//
// A copy of src/nirmaldhara/bands.py. The two must give the same answers: data/rule-cases.json
// is generated from the Python and web/rules-check.html runs every case through this file.
// If you change a number here or there, regenerate the cases and open the check page.

export const BAND_EDGES_CM = [["B1", 12], ["B2", 20], ["B3", 30], ["B4", 50]];

// Depth at which each class must not enter still water, in cm.
export const NO_GO_CM = { two_wheeler: 15, auto: 15, car: 20, pedestrian: 30, suv: 30 };
export const NO_ANSWER_CLASSES = ["bus", "truck"];
export const EVERYONE_NO_GO_CM = 50;
export const MIN_CONFIDENCE = 0.6;
export const MOVING_NO_GO_CM = 12;

export const PASSABLE = "passable";
export const NOT_SAFE = "not safe";
export const UNKNOWN = "unknown: treat as not safe";
export const NO_ANSWER = "no answer: depth reported only";

export function bandFor(depthCm) {
  if (depthCm <= 0) return "B0";
  for (const [name, upper] of BAND_EDGES_CM) {
    if (depthCm < upper) return name;
  }
  return "B5";
}

export function answerFor(vehicle, lowCm, highCm, confidence, moving = false) {
  if (highCm >= EVERYONE_NO_GO_CM) return NOT_SAFE;
  if (NO_ANSWER_CLASSES.includes(vehicle)) return NO_ANSWER;
  let limit = NO_GO_CM[vehicle];
  if (moving) limit = Math.min(limit, MOVING_NO_GO_CM);
  if (highCm >= limit) return NOT_SAFE;
  if (confidence < MIN_CONFIDENCE) return UNKNOWN;
  return PASSABLE;
}

export function passability(lowCm, highCm, confidence, moving = false) {
  const classes = [...Object.keys(NO_GO_CM), ...NO_ANSWER_CLASSES];
  const out = {};
  for (const vehicle of classes) out[vehicle] = answerFor(vehicle, lowCm, highCm, confidence, moving);
  return out;
}
