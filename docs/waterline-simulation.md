# Finding the waterline without a model: a simulation

**SIMULATED. Every scene here was rendered by the script, so no real camera, photo or flood is behind
any number.** Written by `scripts/simulate_waterline.py` (seed 2026, 150 scenes per condition).

The detector is `src/nirmaldhara/waterline.py`: a Bayesian change-point model over several cues (the
difference from a dry view of the same spot, frame-to-frame flicker, brightness, texture and colour),
combined into one distribution over rows, then filtered through time with a hidden Markov model.
One row is 0.6 cm, as for a 150 cm gauge about 250 pixels tall.

## Result

Each cell: typical error, the error 95% of readings stay under, how often a waterline was reported,
and how often the true line was inside the 90% interval the detector gave.

| Condition | Fixed camera, tracked over 8 readings | Fixed camera, one reading | One photo, nothing else |
|---|---|---|---|
| clear | 0.9 cm, 95% under 1.5 cm; found 100%, interval right 96% | 0.9 cm, 95% under 2.0 cm; found 100%, interval right 93% | 0.6 cm, 95% under 26.9 cm; found 100%, interval right 93% |
| murky | 0.9 cm, 95% under 1.7 cm; found 100%, interval right 95% | 0.9 cm, 95% under 1.8 cm; found 100%, interval right 94% | 0.6 cm, 95% under 0.9 cm; found 100%, interval right 100% |
| mirror | 0.3 cm, 95% under 24.5 cm; found 99%, interval right 89% | 0.3 cm, 95% under 27.5 cm; found 98%, interval right 88% | 7.2 cm, 95% under 61.8 cm; found 97%, interval right 69% |
| night | 3.6 cm, 95% under 27.3 cm; found 100%, interval right 41% | 3.3 cm, 95% under 24.4 cm; found 97%, interval right 49% | 20.4 cm, 95% under 55.8 cm; found 99%, interval right 47% |
| rain | 0.9 cm, 95% under 2.9 cm; found 100%, interval right 89% | 1.1 cm, 95% under 11.7 cm; found 100%, interval right 79% | 0.9 cm, 95% under 32.5 cm; found 100%, interval right 86% |
| shadow | 1.0 cm, 95% under 2.0 cm; found 100%, interval right 95% | 1.0 cm, 95% under 2.4 cm; found 100%, interval right 95% | 0.6 cm, 95% under 49.1 cm; found 100%, interval right 86% |
| tide mark | 1.2 cm, 95% under 3.9 cm; found 100%, interval right 85% | 1.2 cm, 95% under 3.8 cm; found 100%, interval right 89% | 0.6 cm, 95% under 23.8 cm; found 100%, interval right 91% |
| vehicle passing | 1.5 cm, 95% under 2.7 cm; found 100%, interval right 57% | 1.4 cm, 95% under 3.4 cm; found 100%, interval right 65% | 0.6 cm, 95% under 32.1 cm; found 100%, interval right 93% |
| vehicle parked | 20.6 cm, 95% under 58.8 cm; found 100%, interval right 25% | 18.8 cm, 95% under 60.3 cm; found 100%, interval right 27% | 25.7 cm, 95% under 58.9 cm; found 100%, interval right 3% |
| shake and light | 1.1 cm, 95% under 2.7 cm; found 100%, interval right 63% | 1.4 cm, 95% under 3.0 cm; found 100%, interval right 58% | 1.4 cm, 95% under 30.2 cm; found 100%, interval right 51% |
| storm at night | 8.1 cm, 95% under 34.7 cm; found 100%, interval right 13% | 8.8 cm, 95% under 35.3 cm; found 89%, interval right 22% | 17.0 cm, 95% under 58.1 cm; found 100%, interval right 47% |

On dry scenes, a waterline was wrongly reported in 1% of fixed-camera readings and
63% of single photos.

The detector's settings were chosen on scenes from one random seed; the table above is from a
different seed, so it was not tuned on the scenes it reports.

## What it means

**Works, in these scenes.** In daylight on a fixed camera with a dry view to compare against, the
line is found to about 1 cm, and 95% of readings are within 2 to 4 cm, in clear and murky water,
under a shadow edge, with a wet tide mark above the water, with a vehicle driving through, and with
a shaken camera in changed light. Rain is as good once readings are tracked over time (95% within
3 cm) and worse on a single reading (12 cm). A dry strip was given a waterline in 1% of readings.

**Does not work.**

- **Night.** Typical error 3 to 4 cm, but one reading in twenty is out by 25 cm or more, and the
  interval the detector gives is right less than half the time, so it is too sure of itself. Glare
  lying on dark water is read as the start of the water. With rain as well it is worse: 8 cm
  typical.
- **Mirror-calm water.** Usually excellent (0.3 cm), but about one reading in ten fails badly:
  still water that reflects the object above it looks like more of the object.
- **A vehicle parked in front.** It is read as water starting at the vehicle's roof: 20 cm typical
  error, on the side of too deep. Nothing in these cues separates a still vehicle from still water.
  The state engine's rule that holds back a sudden jump of two bands until a second source confirms
  it is the only protection, and it was not written for this.
- **One photo, nothing else.** The typical error looks small, but one in twenty is out by 25 to
  60 cm, and a waterline is reported on 63% of dry scenes. Without a dry view to compare against
  there is no way to tell a waterline from a painted line or a shadow. This is not usable, and it
  is the case a resident's phone photo is in. That case still needs a vision model.
- **Intervals.** Where the table says "interval right" well under 90% (a vehicle passing, shake and
  light, night), the detector is over-confident, and its ranges should be widened before use.

## What this changes, and what it does not

- For a fixed camera with a dry reference view, in daylight, finding the waterline does not need a
  vision model. That is a real result for the camera half of the design.
- It does not help the phone-photo path at all, which is the path the deployed system and the demo
  rest on.
- It is not an accuracy figure. These are my own renderings of what makes a flood image hard. A real
  street has difficulties nobody listed here: floating waste against the gauge, spray, a lens with
  drops on it, headlights sweeping across, a gauge that is dirty or bent. The detector has not been
  run on a single real image, because no fixed-camera footage of a flood with a dry view of the same
  spot was available. None of the nine sites has a gauge or a reference view recorded.
- Nothing calls this module yet. It is built and tested; it is not part of the deployed pipeline.

## What would make it real

1. Footage from one fixed camera that shows the same spot dry and flooded, with something of known
   height in view. Ten minutes of it would say more than this whole table.
2. Night: use the camera's own infrared image if it has one, and take readings over a longer window
   so passing headlights fall out of the median.
3. A parked vehicle: an object detector, or the rule that water cannot rise a metre between two
   readings, applied before the reading is trusted.
4. Widen the intervals until "interval right" is 90% in every row that is to be used.
