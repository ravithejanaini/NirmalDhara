
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
