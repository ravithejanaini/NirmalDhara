
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
