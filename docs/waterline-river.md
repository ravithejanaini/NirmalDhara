# The waterline detector on a real flood

**Real fixed cameras, a real flood, measured water levels.** Written by `scripts/river_camera_test.py` on the
hourly pictures of river cameras near Tewkesbury, 21 November to 5 December 2012, published with the water
level read from each picture against surveyed points ([credits](../samples/tewkesbury/CREDITS.md)). The
pictures are not in the repository. This is a river, not a street, and not Hyderabad.

One frame an hour, a dry view from another day, and a water's edge that runs across ground and structures:
each of these is outside what the detector was built for. The row it reports is turned into a level by a
rising-only curve fitted on half of the days, and the error is measured on the other half.

| Camera | | Pictures with a measured level | Line reported | Withheld | Pairs put in the right order | Error on days not fitted, typical | 90% under | Guessing the middle level | The dataset's own error |
|---|---|---|---|---|---|---|---|---|---|
| Tewkesbury | used to find out how to use the detector here | 132, 8.87 to 12.02 m | 105 (80%) | 27 occluded | 81% of 4005 | 29 cm | 101 cm | 58 cm | ± 15 cm typical |
| Strensham | run once, with the strip fixed beforehand | 109, 10.65 to 13.23 m | 107 (98%) | 1 dry, 1 occluded | 93% of 4669 | 13 cm | 54 cm | 45 cm | ± 5 cm typical |

Each camera's strip, and the picture taken as its dry view:

- **Tewkesbury**: a grass bank in the foreground, read from the near side up to the river. Columns 1400 to 1508, rows 700 to 1536. Dry view: the 6 pictures of 21/11 from 9:00 to 14:00, level 9.07 to 9.62 m. Lines were reported at levels from 8.87 to 12.02 m.
- **Strensham**: a lock: far fields at the top, the gates and walls, then the water in the foreground. Columns 690 to 798, rows 300 to 1140. Dry view: the 5 pictures of 3/12 from 10:00 to 14:00, level 10.65 to 10.72 m. Lines were reported at levels from 10.65 to 13.23 m.

## How to read this

**Strensham is the test.** Its strip and its dry view were fixed before any of its pictures had been read,
and it was run once. Nothing was changed afterwards.

**Tewkesbury was used to learn**, so its figures come after choices made while looking at them. Two things
were settled there and then applied to Strensham unseen:

- The dry view is built from several pictures at low water, not one.
- With a single frame there is no measure of noise, so the detector asks instead that the texture of the
  rows taken as dry is at least faintly the dry view's. Without that it reported a line on pictures where
  the whole strip was under water.

## What Strensham shows

A lock gate: large, close to the camera, man-made, with far fields above it that stay dry.

- The detector's rows put 93% of pairs of levels in the right order.
- On days the curve from row to level had not seen, the level was 13 cm out, typically. 42% of readings were
  within 10 cm, 55% within 20 cm, 62% within 30 cm. Always guessing the middle level is 45 cm out.
- It is uneven. Between 12.4 and 12.8 m the typical error was 3 cm, and between 11.2 and 12.0 m, 14 cm. At
  the low end (10.6 to 11.2 m) it was 48 cm, and between 12.0 and 12.4 m, 43 cm.
- At the top it runs out. Above about 12.6 m the water has reached the part of the strip the detector takes
  as dry, so every higher level reads the same row. That is the strip's doing, not the flood's.
- Five of the eight worst readings are the afternoon of 21 November, the first day, read about a metre too
  high. Why was not looked into, because looking would have meant changing things on the test camera.

## What Tewkesbury shows

Where the camera looks decides whether this can work at all.

- **The bank in the foreground.** The camera looks over the top of a wall. While the water is below the top
  of the wall, between about 10.4 and 11.5 m, its edge is hidden behind the wall and the line in the picture
  does not move. No method could read those levels from that strip. Over the whole range the error was 29 cm
  against 58 cm for guessing.
- **A stone pier in the middle distance**, which the water does climb in view. There the detector did no
  better than guessing. The whole 2.7 m of the flood covers about 40 rows of the picture, so one row is 7 cm;
  the light swings between overcast and direct sun from day to day; and the strip took in a sunlit face and
  a shaded recess side by side, which one gain per row cannot describe.
- Grass does not keep its pattern from one day to the next the way a painted gauge or a wall does. On the
  bank, the pattern cue, which carries the detector in the renders, had little to say.

## What it means

- **This is the first figure from a real flood, and it is tens of centimetres**, not the fractions of a
  centimetre the renders gave. Where the view suited the method it was 13 cm, typically, with a long tail.
  Where the view did not suit it, it was of no use.
- A depth band in this project is 8 to 20 cm wide. An error of 13 cm, with one reading in ten more than half
  a metre out, would put many readings in the wrong band. As it stands this cannot decide whether a road is
  passable.
- What the camera needs to see is now clear: a vertical, man-made surface, close enough that a row of the
  picture is a centimetre or so, that the water climbs in full view, with part of it above the highest water.

## What this is not

- **Not the use the detector was built for**, which is six frames a second apart, minutes after a dry view
  taken in the same light. Here there is one frame an hour and a dry view from another day. That use is
  easier in two ways and has still not been tried on a real flood.
- **Not a surveyed scale.** The curve from row to level was fitted from the measured levels of half the
  days. In use it would come from measuring the surface once. That step is not tested here, and the curve's
  own error is inside the figures above.
- **Not a street, and not Hyderabad.** A river lock in England.
- **Two of the four cameras were not used.** Diglis Lock and Evesham have levels for about 50 pictures each,
  over 0.6 m and 1.0 m, too narrow a range to say much at this size of error.
- No tracking through time was used, and no picture was taken at night.

A second way to read these cameras, learnt from the pictures and their measured levels, was tried
afterwards: [gauge-river.md](gauge-river.md).
