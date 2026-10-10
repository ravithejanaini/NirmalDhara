
## How these numbers were made, in order

1. The detector was designed and adjusted on the eleven design conditions, many times, with one random seed.
2. Its design was frozen and the nine held-out conditions were run for the first time, on another seed.
   That first look is the table below.
3. It was then run on real video for the first time and failed (see [waterline-real.md](waterline-real.md)).
4. It was changed, for reasons found on the real video.
5. The interval widths were fitted again, and everything above was run again.

So the tables above are a second look. The design conditions were tuned on; the held-out conditions were
seen once before the last changes. Nothing in the last changes was aimed at a held-out condition, but they
are no longer untouched.

## First look at the held-out conditions, before real video changed anything

One reading, 150 scenes each.

| Condition | Typical error | 95% under | Line reported | In range | Blocked | False line on a dry scene |
|---|---|---|---|---|---|---|
| fog | 0.1 cm | 0.6 cm | 100% | 100% | | 0% |
| foam line | 1.2 cm | 3.7 cm | 100% | 1% | | |
| sun glint | 0.1 cm | 0.6 cm | 100% | 100% | | |
| pole in front | 0.6 cm | 65.3 cm | 83% | 59% | 16% | 20% |
| compressed | 0.7 cm | 6.4 cm | 100% | 57% | | 2% |
| night shadow | 0.4 cm | 6.0 cm | 100% | 88% | | 5% |
| parked at night | 23.1 cm | 62.7 cm | 100% | 23% | 0% | |
| dusk flat water | 0.4 cm | 0.7 cm | 100% | 99% | | |
| rising | 0.0 cm | 0.6 cm | 100% | 100% | | |

Five of nine were fine. Compression widened the errors past the interval. A pole in front gave gross errors
and a false waterline on one dry scene in five. A vehicle parked at night was read as water every time.

## What it means

**Works, in these scenes.** With a dry view to compare against and six frames per reading, the line is
found to within about a centimetre, typically, in clear and murky water, rain, fog, sun glint, flat water
at dusk, under a shadow, with a wet tide mark above the water, with a vehicle driving through, and while
the water rises. Night is at 0.4 cm typical, with one reading in twenty out by 4 cm or more. A dry strip
was given a waterline in at most 5% of readings, in the worst kind of scene.

**Mostly withheld rather than wrong.** A vehicle parked in front in daylight is reported as blocking the view
in nine readings out of ten. Most of the rest are scenes where the water stands above the vehicle's roof and
the line given is right; a few are wrong. A pole in front of a third of the strip is reported blocked in two
readings out of three; of the lines given in the rest, one in twenty is off by 30 cm or more.

**Does not work.**

- **A vehicle parked at night** is read as water: 21 cm typical error. In the dark, a still vehicle and still
  water give the same cues, and nothing here tells them apart.
- **One photo, nothing else.** A waterline is reported on 18% to 100% of dry scenes, depending on the kind.
  Without a dry view there is no way to tell a waterline from a painted line. This is the case a resident's
  phone photo is in, and it still needs a vision model.
- **A clip with no dry view** finds the line by flicker alone. In these renders that works by day in moving
  water and fails at night, in still water, and behind a vehicle. On the one real waterline tried, it failed.
- **Mirror-calm water on an evenly marked gauge.** The mirror image keeps the gauge's pattern, and once colour
  has to be allowed to wander, as real video requires, little separates it from a gauge in other light. About
  one reading in ten is withheld or off by 8 cm or more.
- **The intervals are too narrow in four conditions.** A foam line shifts the estimate by about two rows and
  the interval misses it nearly always, though the error is 1.4 cm. Under camera tremble the interval is right
  two times in three; under compression, three in five; in a storm at night, 85%.
- **Tracking over eight readings** helps in a storm at night and does harm behind a parked vehicle, where the
  few readings that report a line are sometimes wrong and nothing contradicts them.

## What this changes, and what it does not

- For a fixed camera with a dry view, finding the waterline does not need a vision model, by day or by night,
  in these renders. On real video with the camera nearly still, the same detector found a made line to a
  tenth of a row, typically, and reported a line where nothing had changed in 3% of readings.
- It does not help the phone-photo path, which is the path the deployed system and the demo rest on.
- It is not an accuracy figure. These are my own renderings of what makes a flood image hard, and the real
  video had a made line and no known depth. The detector has not been run on one image of a real waterline
  with a dry view of the same spot, because none was available. None of the nine sites has a gauge or a
  reference view recorded.
- The first run on real video failed in ways no rendered scene had shown. There is no reason to think that
  was the last such lesson.
- Nothing calls this module yet. It is built and tested; it is not part of the deployed pipeline.

## What would make it real

1. Footage from one fixed camera that shows the same spot dry and flooded, with something of known height in
   view. A published set exists: four river cameras through the 2012 Tewkesbury flood, hourly, with water
   levels read against surveyed points (doi:10.17632/769cyvdznp.1, CC BY 4.0). It has not been used.
2. The interval widths fitted on real readings, not rendered ones.
3. For a parked vehicle at night: an object detector, or the rule that water cannot rise a metre between two
   readings, applied before a reading is trusted.
