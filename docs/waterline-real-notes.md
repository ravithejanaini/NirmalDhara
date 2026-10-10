
## How to read this

**This is not a clean test.** The detector was designed on rendered scenes and frozen. It was then
run on this footage for the first time, and it failed:

| | First run, design frozen on simulation | Now |
|---|---|---|
| Nothing changed, camera nearly still: waterline reported | 42 of 124 readings (34%) on the first strips | see check 1 |
| Nothing changed, hand-held drift | 21 of 44 (48%) | see check 1 |
| Made line: typical error | 22 rows; true line inside the interval 17% of the time | see check 2 |

The detector was then changed, for reasons found by looking at what each cue said on these strips. So the
figures above the fold are measured on the same footage the changes were made against. They show that
the faults found were real and were fixed; they do not show how it will do on footage it has not seen.

The strips for check 1 were also chosen again. Some of the first ones had foliage in them, which moves,
and reporting change there is correct. The new ones are on a gate, a fence and the fronts of buildings.

## What real video showed that the simulation could not

Every one of these is an assumption that held in every rendered scene and does not hold in a real one.

1. **A real strip crosses different materials.** In the renders every row is the same surface. In a real
   strip the rows taken as dry may be sky and the rows below them a wall. A line fitted on the first, per
   colour channel, was far off on the second, and the colour cue was 20 to 50 times too large on rows where
   nothing had changed. Brightness is now fitted as a gain alone unless an offset clearly earns its place,
   colour as one number per channel, and how far colour may wander is learnt also from rows further down
   that the pattern confirms are still the surface.
2. **Noise is not the same everywhere.** A codec, and a fraction of a pixel of misalignment, miss by more
   where the picture has edges. With one noise level for the whole strip, every small miss on a strongly
   textured row looked decisive. Each row now has its own noise: a constant plus a share of the dry view's
   gradients, fitted on the rows known to be dry.
3. **Rows are not independent evidence.** Eight rows of small, correlated misses were enough to declare a
   line. All evidence is now tempered.
4. **A view that is no longer the enrolled one can look fine.** With enough noise allowed, anything fits.
   The rows taken as dry must now be as like the dry view as their texture and the noise measured between
   frames allow, or the view is reported blocked.

## What it still cannot do

- **A hand-held camera.** Over two seconds a hand moves the picture by up to six pixels, and the top and
  bottom of a strip by different amounts. No single shift undoes that. About one reading in seven still reports
  a line where nothing changed, and one made line in twenty is missed by 45 rows or more. A camera on a pole does not move
  like this, but no footage from one was available, so that case is argued here, not shown.
- **The clip mode on a real line (check 3).** With no dry view and only flicker to go on, the detector did
  not find the fence's waterline: it reported lines 50 to 140 rows too high, or none. The water against
  the fence is nearly still, so there is little flicker to see. On the gate, whose bars turn wavy in the
  water, it was within about 30 rows. This mode does not work on this footage.
- **A tail even with the camera still.** The typical miss on a made line is a tenth of a row, but one in
  twenty is off by 16 rows or more, and the worst by 39.
- **16 of 216 made lines were withheld** as "blocked" when the camera was nearly still: the check that the
  dry rows still look like the dry view is cautious.
- **The interval.** With the camera nearly still, the true line was inside the reported 90% interval 84%
  of the time, a little short. The widths were fitted on rendered scenes and need fitting on real ones.

## What is still missing

- **No depth.** Nothing here has a known size, so there is no centimetre in this file.
- **No real line with a dry view.** The fence and gate were only ever filmed in the flood. The only way the
  dry-view method meets real water here is with the water put there by hand (check 2), which has no
  reflection of the surface in it and no wet edge.
- **One shot, two and a half seconds.** All of check 2 and check 3 is one hand-held shot of one compound on
  one afternoon. It is one piece of evidence.
- **No night, no heavy rain on the lens, no pole camera.**

Some of this has since been answered on a real flood with measured levels: four fixed river cameras at
Tewkesbury, November 2012. See [waterline-river.md](waterline-river.md). The answer there is tens of
centimetres at best.
