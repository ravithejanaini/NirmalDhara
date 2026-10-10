# Several dimensions, several objects, several cameras: a simulation

**SIMULATED. No real camera, photo or flood is behind any number here.** Written by `scripts/simulate_multiview.py` (seed 7).
It tries the geometry in `nirmaldhara/multiview.py` with the errors a real camera would add. It does not test
finding a waterline or a floating thing in a real picture, which is where the real error was (see
[waterline-river.md](waterline-river.md)).

## What was simulated

- 300 cameras, each 3 to 7 m up and 8 to 20 m from the site at a random bearing, with its own focal length and a lens
  that bends straight lines by up to 10% at the edge. The calculation assumes a lens that does not bend.
- A site with three posts carrying marks at 50, 100 and 150 cm, and lane edges 7 m apart marked at three
  places along 12 m of road: 18 marks of known height, length and width in all.
- Each mark placed on the dry view 1.5 px out, a waterline found 2.0 px out, a floating thing 2.0 px out.
- Depths from 5 to 60 cm.

## 1. One camera, one post: one height against every known dimension

Error in the depth: the middle value, and the value 95% of readings stay under.

| Camera tilt below horizontal | Readings | One scale from the post's height (METHOD C2 as written) | The post's four marks | Camera fixed from all the marks |
|---|---|---|---|---|
| 0° to 15° | 3000 | 2.2 cm, 95% under 7.0 cm | 2.1 cm, 95% under 6.8 cm | 2.0 cm, 95% under 6.2 cm |
| 15° to 30° | 4104 | 2.2 cm, 95% under 6.7 cm | 2.0 cm, 95% under 6.4 cm | 1.9 cm, 95% under 6.1 cm |
| 30° to 60° | 96 | 2.8 cm, 95% under 6.0 cm | 2.2 cm, 95% under 6.3 cm | 1.9 cm, 95% under 5.7 cm |

## 2 and 3. Joining readings, each a couple of pixels out

Each reading here is right to within its pixels.

| Read by | Error in the depth | More than 10 cm out |
|---|---|---|
| One camera, one post | 1.9 cm, 95% under 6.1 cm | 0.4% |
| One camera, three posts joined | 1.2 cm, 95% under 4.0 cm | 0.0% |
| Two cameras, one post, joined | 1.4 cm, 95% under 4.4 cm | 0.0% |
| Three cameras, one post, joined | 1.3 cm, 95% under 4.0 cm | 0.0% |

Three posts agreed in 100% of readings, and three cameras in 100%. A reading's range was taken as ± 3.8 cm, which held 80% of single readings in question 1.

## 2 and 3 again, with one reading in 10 far out

Each reading is, one time in 10, between 15 and 60 cm out, high or low, which is how the detector's readings were spread on the real flood.

| Read by | Error in the depth | More than 10 cm out |
|---|---|---|
| One camera, one post | 2.2 cm, 95% under 42.3 cm | 10.2% |
| One camera, three posts joined | 1.4 cm, 95% under 5.0 cm | 1.3% |
| Two cameras, one post, joined | 1.8 cm, 95% under 24.4 cm | 16.7% |
| Three cameras, one post, joined | 1.4 cm, 95% under 5.0 cm | 1.3% |

Three posts agreed in 96% of readings, and three cameras in 96%. A reading's range was taken as ± 3.8 cm, which held 80% of single readings in question 1.

## 4. The speed of the water, from something floating on it

A thing moving at 0.2 to 2 m/s on water 5 to 50 cm deep, seen twice one second apart.

| Seen by | Error in the speed | More than 0.2 m/s out |
|---|---|---|
| Two cameras | 0.03 m/s, 95% under 0.17 m/s | 4.1% |
| One camera, told the true level | 0.06 m/s, 95% under 0.24 m/s | 8.4% |
| One camera, level from its own reading | 0.06 m/s, 95% under 0.24 m/s | 8.4% |
| One camera, told the road is dry | 0.09 m/s, 95% under 0.32 m/s | 16.4% |

## How to read this

- **These are the errors of the geometry, not of the method.** Every number assumes the waterline has
  already been found to within two pixels. On a real flood that was the hard part: the detector was 13 cm
  out, typically, and one reading in ten was more than half a metre out. No geometry mends that.
- **Question 1 is about the camera's angle.** One scale from one height is right for a camera that looks
  level and wrong for one that looks down. Fixing the camera from heights, lengths and widths together
  solves the angle and does not have to assume it.
- **The second run of questions 2 and 3 is the one that matters.** When readings are only a pixel or two
  out, joining three gains little. When one in ten is far out, the middle of three throws the wild one away.
  That gain depends on the three being wrong at different times. Three posts in one picture share its
  light, its rain and its lens, so they will be wrong together more often than this assumes. Cameras at
  different angles share less.
- **Two readings are not enough.** Two cannot outvote a wild one: the answer is pulled halfway towards it,
  and with two readings a wild one turns up twice as often. Three is the least that can throw one away.
- **Two cameras need no level to give a speed; one camera does.** Told the road is dry when it is not,
  one camera puts the floating thing in the wrong place and gets the speed wrong by that much.
- **Nothing here is a camera at a site.** No site has two cameras on one water, and none has its marks
  surveyed. This shows what would be gained if they had, and nothing more.
