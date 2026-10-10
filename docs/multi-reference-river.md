# Several reference surfaces in one view, on a real flood

**Real fixed cameras, a real flood, measured water levels.** Written by `scripts/river_multi_reference.py` on the
hourly pictures of two river cameras near Tewkesbury, 21 November to 5 December 2012, published with the
water level read from each picture against surveyed points ([credits](../samples/tewkesbury/CREDITS.md)). The
pictures are not in the repository. This is a river, not a street, and not Hyderabad.

The waterline detector reads each camera through several strips, each on a different surface that the water
climbs. Each strip is given a curve from row to level, and a record, on half of the days.
`nirmaldhara.multiview.combine` joins what the strips say on the other half. Every error is on days not
learnt from.

### Tewkesbury: used to work out how to join strips

| Read through | Pictures given a level | Typical error | 90% under | Within 10 / 20 cm |
|---|---|---|---|---|
| Strip A alone: the grass bank, right of the tables (the strip used before) | 105 of 132 | 29 cm | 101 cm | 22% / 39% |
| Strip B alone: the gravel and grass at the left | 0 of 132 | - | - | - |
| Strip C alone: the grass bank at the far right | 105 of 132 | 37 cm | 108 cm | 22% / 29% |
| The one strip with the best record on the days learnt from | 105 of 132 | 37 cm | 108 cm | 22% / 29% |
| **All strips together** | 111 of 132 | 33 cm | 96 cm | 17% / 34% |
| All strips together, where three or more gave a line | 0 of 132 | - | - | - |

The joined range held the measured level in 94 of 111 pictures, and was 173 cm wide, typically. In no picture did three strips agree.

### Strensham: run once, with the new strips fixed beforehand

| Read through | Pictures given a level | Typical error | 90% under | Within 10 / 20 cm |
|---|---|---|---|---|
| Strip A alone: the lock gates (the strip used before) | 107 of 109 | 13 cm | 54 cm | 42% / 55% |
| Strip B alone: the left lock wall and its red marker post | 105 of 109 | 11 cm | 40 cm | 38% / 73% |
| Strip C alone: the right bank and its white post | 107 of 109 | 14 cm | 50 cm | 34% / 57% |
| Strip D alone: the steps down to the water | 90 of 109 | 28 cm | 87 cm | 14% / 40% |
| The one strip with the best record on the days learnt from | 107 of 109 | 13 cm | 69 cm | 34% / 56% |
| **All strips together** | 108 of 109 | 10 cm | 46 cm | 43% / 73% |
| All strips together, where three or more gave a line | 105 of 109 | 10 cm | 45 cm | 44% / 75% |

The joined range held the measured level in 96 of 108 pictures, and was 107 cm wide, typically. Where three or more strips agreed (105 pictures) it held it in 93 and was 107 cm wide.

## How to read this

**Strensham is the test.** Its three new strips were fixed on the dry view before any other picture had been
read through them, and it was run once. Its strip A is the one `river_camera_test.py` used, whose figures
were already known.

**Tewkesbury was used to work out the joining**, so its figures come after choices made while looking at
them. Two things were settled there and then applied to Strensham unseen:

- With two strips the level is their weighted mean. Two cannot say which of them is wrong, so neither is
  thrown away. The middle one is taken only of three or more.
- A strip counts for more the better its record on the days learnt from. That record comes from a few days
  and is itself uncertain, so each strip's typical error is first mixed with the typical error of all of
  them. At Tewkesbury the strip with the better record turned out the worse of the two.

## What Strensham shows

- **Four surfaces together were closer than the lock gates alone.** 10 cm out, typically, against 13 cm.
  Nine in ten within 46 cm against 54 cm. Within 20 cm in 73% of pictures against 55%.
- **They did not beat the best single surface.** The left lock wall with its marker post, read alone, was 11
  cm out and nine in ten within 40 cm. What the joining did was match the best surface without being told
  which one that was. Choosing the strip with the best record on the days learnt from gave 13 cm, and nine
  in ten within 69 cm.
- **A poor surface did not drag the rest down.** The steps were 28 cm out and gave no line in 19 pictures of
  109. With three better strips beside it, it was outvoted.
- **The range is honest and too wide to use.** It held the measured level in 96 of 108 pictures and was 107
  cm wide, typically. Each strip's range comes from its own left-out errors, and those have a long tail.

## What Tewkesbury shows

- Two strips gave lines, both on the same grass bank. The third, on gravel, gave no line at all.
- Together they were 33 cm out, between the 29 cm and 37 cm of each alone. No gain.
- Both look over the same wall, which hides the water's edge for part of the range. Two surfaces with the
  same flaw are wrong at the same time, and joining them mends nothing.

## What it means

- **Reading several reference objects helps when they are different kinds of thing**, wrong at different
  times: a gate, a wall, a post. It does not help when they are the same thing seen twice.
- **The gain is modest.** 13 cm to 10 cm, and the long tail is still there: one reading in ten more than 46
  cm out. A depth band here is 8 to 20 cm wide. This is still not a reading to close a road on.
- **Three is the least that can outvote a wrong one.** With two, the answer is their mean and the range
  widens to hold both.
- For a site, it means marking every upright, man-made surface the camera can see when the view is
  enrolled, not one.

## What this is not

- **Not several cameras.** One camera, several surfaces in its one picture. Several cameras on the same
  water have not been tried on anything real, because the dataset has no such pair and no site has one. What
  the geometry would allow is in [multiview-simulation.md](multiview-simulation.md), and that is a
  simulation.
- **Not marks of known size.** Each strip's curve from row to level was fitted from the measured levels of
  half the days. Fixing a camera from the surveyed height, length and width of things in view is written
  (`nirmaldhara.multiview.camera_from_points`) and has only been checked on made scenes.
- **Not a street, and not Hyderabad.** A river lock in England.
- **Not independent levels.** The levels learnt from and the levels judged against were read by the same
  people from these same pictures.
- **Not the speed of the water.** Nothing here measures flow.
