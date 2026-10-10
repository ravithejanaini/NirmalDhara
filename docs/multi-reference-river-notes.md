
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
  (`nirmaldhara.multiview.camera_from_points`) and has only been checked on made scenes. The dataset does
  hold surveyed points in each camera's view, as positions and heights with no word of what each one is.
  Matching them to the picture was tried for this camera and could not be done with any confidence, so the
  one real test that was within reach was not made.
- **Not a street, and not Hyderabad.** A river lock in England.
- **Not independent levels.** The levels learnt from and the levels judged against were read by the same
  people from these same pictures.
- **Not the speed of the water.** Nothing here measures flow.
