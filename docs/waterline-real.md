# The waterline detector on real video

**Real video, but not a real measurement of depth.** Written by `scripts/real_strip_test.py` on steady
stretches of a licensed news clip ([credits](../samples/footage/CREDITS.md)). The frames are not in
the repository. Nothing in these pictures has a known size, so this is about finding the line, in
rows of the picture, not about centimetres.

The footage is hand-held. Each check is run twice: with the reading cut so close to the dry view that
the camera has hardly moved, which is what a camera on a pole gives, and with two seconds between them,
over which a hand drifts the picture by a few pixels and not evenly.

## 1. Nothing changed: no waterline may be reported

13 strips of things that do not move (a gate's panel, a fence above the water, the fronts of
buildings, one shot in rain). The first frames are the dry view, later frames the reading.

| | Readings | A waterline was reported | Reported dry | Withheld |
|---|---|---|---|---|
| camera nearly still (0.4 s) | 78 | **2** (3%) | 75 | 1 |
| hand-held drift (2 s) | 26 | **4** (15%) | 22 | 0 |

## 2. A made line between real pixels

A real fence and a real gate, with real moving flood water from the same frames put over the lower
part of each from a chosen row down: 3 surfaces, 3 patches of water, 4 lines.
Both sides of the line are real video; where the line is, is known.

| | Readings | Line reported | Typical error, rows | 95% under | Worst | True line inside the 90% interval |
|---|---|---|---|---|---|---|
| camera nearly still (0.4 s) | 216 | 200 (93%) | 0.1 | 15.7 | 38.9 | 169 of 200 (84%) |
| hand-held drift (2 s) | 72 | 72 (100%) | 1.0 | 45.5 | 48.6 | 43 of 72 (60%) |

What this is not: the water was put there, so it has no reflection of the fence in it and no wet edge
where they meet. A real line has both.

## 3. A real line, with no dry view

A fence and a gate standing in real flood water. No dry view of them exists, so only the clip mode can
run: six frames, flicker only. The true line was marked by eye on one enlarged frame before the detector
was run on this shot.

| Strip | Marked by eye | six frames in a row (0.2 s) | six frames over 1.2 s |
|---|---|---|---|
| fence, left | 562 ± 3 | 473, 479, 420; 3 not reported | 466, 485, 472, 510 |
| fence, middle | 555 ± 3 | no line | no line |
| fence, right | 540 ± 3 | no line | no line |
| gate bars | 523 ± 6 | 512, 512, 504; 3 not reported | 516, 506, 551, 514 |

The readings of a strip overlap or follow each other within one shot, so they are one piece of evidence, not several.

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
