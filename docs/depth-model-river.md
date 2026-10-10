# One level from every reference surface, through time, on a real flood

**Real fixed cameras, a real flood, measured water levels.** Written by `scripts/river_depth_model.py` on the
hourly pictures of two river cameras near Tewkesbury, 21 November to 5 December 2012, published with the
water level read from each picture against surveyed points ([credits](../samples/tewkesbury/CREDITS.md)). The
pictures are not in the repository. This is a river, not a street, and not Hyderabad.

Each camera is read through several strips. `nirmaldhara/depthmodel.py` learns, on half of the days, what
each strip reports at each level, and makes one level of them on the other half. Every error is on days
not learnt from. The range is the model's own, stretched until it would have held nine in ten of the
days left out while it was learning.

## Tewkesbury: used to build the model

132 pictures with a measured level, 8.87 to 12.02 m, read through 5 strips.

| Read by | Pictures given a level | Typical error | 90% under | Within 10 / 20 cm | Range held the level |
|---|---|---|---|---|---|
| One strip (the grass bank, right of the tables), its row through a curve | 105 of 132 | 29 cm | 101 cm | 22% / 39% | - |
| Every strip through its own curve, the middle one taken | 132 of 132 | 40 cm | 79 cm | 20% / 35% | 121 of 132, 171 cm wide |
| **The model**, each moment by itself | 132 of 132 | 38 cm | 80 cm | 17% / 29% | 118 of 132, 176 cm wide |
| **The model, through time** | 132 of 132 | 27 cm | 68 cm | 19% / 39% | 120 of 132, 176 cm wide |
| **The model, through time, with the learnt gauge as one more witness** | 132 of 132 | 12 cm | 42 cm | 46% / 61% | 117 of 132, 121 cm wide |

What the model learnt about each strip, from each half of the days:

| Strip | Runs over | Lines learnt from | Spread, rows | Wild | Levels it can tell apart |
|---|---|---|---|---|---|
| A | the grass bank, right of the tables | 50 / 55 | 35.2 / 24.2 | 2% / 3% | 11.57 to 11.84 m, 12% of them ; 8.88 to 11.87 m, 31% of them |
| C | the grass bank at the far right | 51 / 54 | 43.8 / 48.8 | 2% / 2% | 11.58 to 11.86 m, 13% of them ; 9.89 to 11.88 m, 26% of them |
| D | the concrete pier at the end of the weir | 62 / 64 | 26.1 / 47.3 | 8% / 1% | 11.82 to 12.03 m, 2% of them ; 12.02 to 12.02 m, 0% of them |
| E | the far lock wall | 63 / 64 | 12.0 / 3.7 | 11% / 26% | 10.17 to 11.83 m, 55% of them ; 9.90 to 10.38 m, 14% of them |
| G | the bank between the tables, down to the gravel | 60 / 65 | 8.7 / 35.9 | 27% / 1% | 10.07 to 12.03 m, 15% of them ; 11.79 to 12.02 m, 7% of them |

Share of face value the strips' evidence was counted at: 0.05 / 0.35 for a moment by itself, 0.05 / 0.10 through time. Rate the level was taken to move at: 1.5 / 1.6 cm an hour. Stretch of the range: 1.0 / 1.0 times by itself, 1.1 / 1.2 through time. The learnt gauge's evidence was counted at 0.003 / 0.001 of what it claimed.

## Strensham: run once, with the strips and the model fixed beforehand

109 pictures with a measured level, 10.65 to 13.23 m, read through 7 strips.

| Read by | Pictures given a level | Typical error | 90% under | Within 10 / 20 cm | Range held the level |
|---|---|---|---|---|---|
| One strip (the lock gates, right half), its row through a curve | 107 of 109 | 13 cm | 54 cm | 42% / 55% | - |
| Every strip through its own curve, the middle one taken | 108 of 109 | 11 cm | 48 cm | 40% / 63% | 98 of 108, 112 cm wide |
| **The model**, each moment by itself | 109 of 109 | 12 cm | 47 cm | 46% / 67% | 88 of 109, 94 cm wide |
| **The model, through time** | 109 of 109 | 11 cm | 43 cm | 41% / 68% | 89 of 109, 89 cm wide |
| **The model, through time, with the learnt gauge as one more witness** | 109 of 109 | 12 cm | 41 cm | 39% / 67% | 83 of 109, 57 cm wide |

What the model learnt about each strip, from each half of the days:

| Strip | Runs over | Lines learnt from | Spread, rows | Wild | Levels it can tell apart |
|---|---|---|---|---|---|
| A | the lock gates, right half | 53 / 54 | 11.1 / 25.8 | 2% / 3% | 11.21 to 12.64 m, 41% of them ; 10.65 to 12.64 m, 23% of them |
| B | the left lock wall and its red marker post | 53 / 52 | 3.7 / 12.2 | 35% / 13% | 11.09 to 13.23 m, 58% of them ; 10.68 to 12.65 m, 70% of them |
| C | the right bank and its white post | 53 / 54 | 7.9 / 11.5 | 14% / 6% | 11.24 to 12.64 m, 40% of them ; 10.65 to 12.63 m, 77% of them |
| D | the steps down to the water | 48 / 42 | 13.6 / 42.2 | 5% / 2% | 11.09 to 12.61 m, 40% of them ; 10.67 to 12.82 m, 14% of them |
| E | the lock gates, left half | 42 / 42 | 5.2 / 12.1 | 19% / 21% | 11.09 to 13.24 m, 64% of them ; 10.65 to 12.86 m, 29% of them |
| F | the right quay, under the hut | 53 / 55 | 15.8 / 13.1 | 3% / 3% | 11.22 to 13.22 m, 62% of them ; 10.69 to 12.89 m, 56% of them |
| G | the far right bank and its handrail | 52 / 50 | 31.4 / 32.0 | 2% / 2% | 11.09 to 12.61 m, 16% of them ; 10.73 to 12.84 m, 37% of them |

Share of face value the strips' evidence was counted at: 0.05 / 0.20 for a moment by itself, 0.05 / 0.10 through time. Rate the level was taken to move at: 1.0 / 2.4 cm an hour. Stretch of the range: 1.0 / 1.0 times by itself, 1.2 / 1.0 through time. The learnt gauge's evidence was counted at 0.010 / 0.010 of what it claimed.

## How to read this

**Strensham is the test.** Its strips were fixed on the dry view, the model was fixed on Tewkesbury, and it
was run once. This was the fourth time Strensham's pictures were read: by one strip, by the learnt gauge, by
four strips joined, and now by this. The figures of the first four of its strips were already known.

**Tewkesbury was used to build the model**, so its figures come after choices made while looking at them.
Three things were settled there:

- How far a witness lies from its curve is measured on days the curve did not see, and split into how much it
  wanders within a day and how far a whole day sits off. Measured on the days it was fitted to, every strip
  looked several times more exact than it is.
- The strips' evidence is counted at a share of its face value, learnt from days left out, and at a second,
  smaller share when the level is followed through time.
- The learnt gauge is one more witness, at a share learnt the same way.

**One thing was tried after the run and taken out again.** On two days Strensham's water was higher or lower
than anything in the half of the days learnt from, and the model read it as a level inside what it had
learnt. A change was made so that a row lying past the end of a witness's curve counted as evidence of water
past the end of the levels, and the answer became "above what was learnt". On made witnesses that worked. On
Strensham it did not fire once, and the figures moved by a centimetre or two the wrong way. It was not kept.
The tables above are from the model as it was run.

## What Strensham shows

- **Every picture was given a level**, 11 to 12 cm out, typically, and nine in ten within 41 to 47 cm. One
  strip gave 107 of 109, 13 cm, and nine in ten within 54 cm.
- **That is a small gain.** Two centimetres in the typical error, about ten in the tail.
- **Seven surfaces are not seven opinions.** The model learnt to count the strips' evidence at a twentieth to
  a fifth of its face value. In one camera, in one light, they are wrong together, and the days left out said
  so.
- **Most of the tail is water beyond what it had learnt from.** Looked at afterwards, for the strips followed
  through time: on 26 November the level was 13.2 m and the highest level learnt from was 12.9 m; on 3
  December it was 10.7 m and the lowest learnt from was 11.1 m. Those 14 pictures were 42 and 82 cm out, and
  the five of 21 November, just below the lowest, 75 cm. The other 90 were 9 cm out, typically.
- **The range is too narrow.** Stretched to hold nine in ten of the days left out while learning, it held
  76% to 82% of the unseen days.
- **The learnt gauge added nothing here.** 12 cm with it and 11 cm without. Its range was narrower and held
  the level less often.

## What Tewkesbury shows

- Every strip there is blind over most of the range: the table shows each telling levels apart over a tenth
  to a half of it. On strips alone the model was 27 cm out, typically, against 29 cm for one strip.
- With the learnt gauge as a witness it was 12 cm out, and nine in ten within 42 cm. There the gauge carried
  it, and the model's part was to give every picture a level and to keep the strips from spoiling it.

## What it means

- **The model does what it was built to do.** It lets a blind witness say nothing, weighs a sharp one above a
  blunt one, outvotes a wild one, and follows the level through time. On made witnesses with those faults it
  is closer than the best of them. On the real camera all of that bought two centimetres.
- **The limit is not the arithmetic of joining.** It is that every witness in one view fails in the same
  light, and that nothing learnt from levels can read past the levels it learnt from.
- **Two things would change that, and neither has been tried on anything real.** Cameras at different angles,
  which do not share their light. And a witness whose curve comes from the known size of what it looks at,
  which does not end where the levels learnt from end. `nirmaldhara/multiview.py` has the arithmetic for
  both.
- This is still not a reading to close a road on.

## What this is not

- **Not several cameras.** One camera, several surfaces in its one picture.
- **Not a street, and not Hyderabad.** A river lock in England.
- **Not independent levels.** The levels learnt from and the levels judged against were read by the same
  people from these same pictures.
- **Not a second flood.** It learnt from days of one flood and was read on other days of that flood.
- **Not connected to anything.** `depthmodel.to_reading` turns an answer into the reading the engine takes,
  and nothing calls it.
