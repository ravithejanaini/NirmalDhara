# Finding the waterline without a model: a simulation

**SIMULATED. Every scene here was rendered by the script, so no real camera, photo or flood is behind
any number.** Written by `scripts/simulate_waterline.py` (seed 2026, 150 scenes per condition).

The detector is `src/nirmaldhara/waterline.py`: a hidden Markov model down the rows of a strip, with four
states (dry, dry but re-lit, water, blocked), likelihoods calibrated on the rows known to be dry, a second
filter through time, and intervals set by conformal calibration. One row is 0.6 cm, as for a 150 cm
gauge about 250 pixels tall.

Each cell: typical error and the error 95% of readings stay under; how often a waterline was reported;
how often the true line was inside the 90% interval; and how often the view was reported blocked.

## Conditions the detector was designed on

| Condition | Tracked over 8 readings | One reading | Clip, no dry view | One photo |
|---|---|---|---|---|
| clear | 0.2 cm, 95% under 0.7; line 100%, in range 100% | 0.2 cm, 95% under 0.7; line 100%, in range 99% | 0.0 cm, 95% under 0.6; line 100%, in range 100% | 0.6 cm, 95% under 19.6; line 100%, in range 65% |
| murky | 0.3 cm, 95% under 0.7; line 100%, in range 100% | 0.3 cm, 95% under 0.7; line 100%, in range 100% | 0.0 cm, 95% under 0.6; line 100%, in range 100% | 0.6 cm, 95% under 0.8; line 100%, in range 63% |
| mirror | 0.0 cm, 95% under 12.0; line 96%, in range 92%; blocked 2% | 0.0 cm, 95% under 8.1; line 93%, in range 89%; blocked 3% | no line reported | 4.8 cm, 95% under 58.4; line 99%, in range 66% |
| night | 0.3 cm, 95% under 2.4; line 100%, in range 96% | 0.4 cm, 95% under 3.7; line 100%, in range 96% | 15.5 cm, 95% under 38.8; line 50%, in range 3% | 13.9 cm, 95% under 53.6; line 98%, in range 41% |
| rain | 0.9 cm, 95% under 1.3; line 100%, in range 85% | 0.8 cm, 95% under 1.3; line 100%, in range 100% | 0.6 cm, 95% under 1.3; line 100%, in range 77% | 0.7 cm, 95% under 18.1; line 100%, in range 57% |
| shadow | 0.3 cm, 95% under 1.1; line 100%, in range 97% | 0.3 cm, 95% under 1.1; line 100%, in range 95% | 0.0 cm, 95% under 0.6; line 100%, in range 100% | 0.7 cm, 95% under 53.7; line 100%, in range 44% |
| tide mark | 0.3 cm, 95% under 0.7; line 100%, in range 99% | 0.3 cm, 95% under 0.7; line 100%, in range 100% | 0.0 cm, 95% under 0.6; line 100%, in range 100% | 0.6 cm, 95% under 8.6; line 100%, in range 66% |
| vehicle passing | 0.6 cm, 95% under 0.8; line 100%, in range 99% | 0.6 cm, 95% under 0.9; line 100%, in range 97% | 0.6 cm, 95% under 1.2; line 100%, in range 95% | 0.6 cm, 95% under 39.4; line 100%, in range 61% |
| vehicle parked | 0.6 cm, 95% under 53.9; line 13%, in range 80%; blocked 91% | 0.2 cm, 95% under 14.3; line 11%, in range 94%; blocked 89% | no line reported | 22.0 cm, 95% under 63.5; line 100%, in range 3% |
| shake and light | 1.1 cm, 95% under 2.2; line 100%, in range 50%; blocked 3% | 1.2 cm, 95% under 2.4; line 96%, in range 68%; blocked 4% | 1.2 cm, 95% under 2.4; line 95%, in range 42% | 1.3 cm, 95% under 5.8; line 100%, in range 28% |
| storm at night | 0.7 cm, 95% under 10.0; line 100%, in range 81%; blocked 3% | 0.7 cm, 95% under 16.0; line 97%, in range 85%; blocked 3% | 19.9 cm, 95% under 40.7; line 35%, in range 0% | 15.3 cm, 95% under 48.1; line 100%, in range 35% |

## Conditions held out

Written before the detector was finished and not used to adjust it.

| Condition | Tracked over 8 readings | One reading | Clip, no dry view | One photo |
|---|---|---|---|---|
| fog | 0.3 cm, 95% under 0.7; line 100%, in range 99% | 0.3 cm, 95% under 0.9; line 100%, in range 99% | 0.0 cm, 95% under 0.6; line 100%, in range 99% | 0.6 cm, 95% under 10.6; line 100%, in range 72% |
| foam line | 1.4 cm, 95% under 2.8; line 100%, in range 3% | 1.4 cm, 95% under 2.7; line 100%, in range 4% | 1.8 cm, 95% under 2.4; line 100%, in range 16% | 2.2 cm, 95% under 19.0; line 100%, in range 10% |
| sun glint | 0.3 cm, 95% under 0.7; line 100%, in range 99% | 0.3 cm, 95% under 0.7; line 100%, in range 100% | 0.0 cm, 95% under 0.6; line 100%, in range 100% | 0.6 cm, 95% under 1.0; line 100%, in range 65% |
| pole in front | 0.4 cm, 95% under 31.2; line 37%, in range 88%; blocked 63% | 0.5 cm, 95% under 31.6; line 35%, in range 91%; blocked 65% | 0.0 cm, 95% under 0.6; line 100%, in range 100% | 0.6 cm, 95% under 23.2; line 100%, in range 61% |
| compressed | 0.9 cm, 95% under 3.7; line 100%, in range 57% | 0.9 cm, 95% under 4.0; line 100%, in range 61% | 0.6 cm, 95% under 3.5; line 100%, in range 60% | 1.2 cm, 95% under 22.6; line 100%, in range 43% |
| night shadow | 0.5 cm, 95% under 2.9; line 100%, in range 91% | 0.6 cm, 95% under 7.0; line 100%, in range 93% | 16.8 cm, 95% under 41.2; line 50%, in range 0% | 18.4 cm, 95% under 50.6; line 99%, in range 24% |
| parked at night | 20.9 cm, 95% under 61.3; line 99%, in range 23%; blocked 1% | 20.9 cm, 95% under 60.9; line 99%, in range 34% | no line reported | 24.9 cm, 95% under 62.4; line 100%, in range 4% |
| dusk flat water | 0.4 cm, 95% under 0.9; line 100%, in range 97% | 0.4 cm, 95% under 1.2; line 100%, in range 94% | no line reported | 0.6 cm, 95% under 11.7; line 100%, in range 72% |
| rising | 0.2 cm, 95% under 0.4; line 100%, in range 100% | 0.2 cm, 95% under 0.7; line 100%, in range 100% | 0.0 cm, 95% under 0.6; line 100%, in range 99% | 0.6 cm, 95% under 42.8; line 100%, in range 57% |

## Dry scenes

How often a waterline was reported on a strip with no water in it:

| Kind of dry scene | One reading | Clip, no dry view | One photo |
|---|---|---|---|
| clear | 0% | 0% | 57% |
| night | 0% | 0% | 18% |
| rain | 0% | 0% | 97% |
| shadow | 3% | 0% | 100% |
| shake and light | 0% | 0% | 53% |
| fog | 0% | 0% | 53% |
| pole in front | 5% | 0% | 48% |
| compressed | 2% | 0% | 100% |
| night shadow | 0% | 0% | 100% |

With a dry view, the worst kind gave a false waterline 5% of the time.

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
