# One flooding place, three cameras, from frames to the engine's answer: a simulation

**SIMULATED. No real camera, photo or flood is behind any number here.** Written by `scripts/simulate_site.py` (seed 2026).
Rendered scenes are read by the real detector, joined by `nirmaldhara/depthmodel.py`, and handed to the site
engine. It checks that the chain holds together, and shows what several cameras are worth when each has its
own light. On a real flood the detector was tens of centimetres out, where on these scenes it is fractions
of one ([waterline-river.md](waterline-river.md)).

## What was simulated

- Three cameras on the same water, at 0.45 cm, 0.6 cm, 0.9 cm of height to a row.
- 20 evenings of 6 moments each, 10 minutes apart. On each the water rises to a peak of 0 to 50 cm and falls again.
- Each camera has its own conditions each evening: clear, murky, rain, a shadow, a mirror-like surface or a passing vehicle. A vehicle
  was parked across a camera's view on 15%, 20%, 25% of its moments, and it was dark for all three on 25%.
- 60 moments were learnt from, with the true depth known, and 60 read.

## Depth

| Read by | Typical error | 90% under | More than 10 cm out | Moments with a confidence of 0.6 or more |
|---|---|---|---|---|
| North alone, each moment | 1.5 cm | 18.1 cm | 15% | 63% |
| North alone, through time | 2.4 cm | 29.1 cm | 17% | 77% |
| East alone, each moment | 2.2 cm | 15.9 cm | 15% | 0% |
| East alone, through time | 4.4 cm | 21.3 cm | 25% | 23% |
| South alone, each moment | 2.1 cm | 33.0 cm | 28% | 58% |
| South alone, through time | 2.5 cm | 45.2 cm | 37% | 77% |
| North and east, each moment | 1.2 cm | 7.2 cm | 8% | 70% |
| North and east, through time | 2.0 cm | 11.0 cm | 12% | 92% |
| All three, each moment | 1.5 cm | 4.2 cm | 8% | 80% |
| All three, through time | 1.5 cm | 11.0 cm | 13% | 97% |

## The engine's answer for a car

All three cameras, through time, handed to the site engine as readings. The answer for a car from the
model's range is set beside the answer the true depth would give.

- The same answer in 46 of 60 moments.
- **Passable when the true depth said not: 0.**
- Not passable when the true depth said it was: 14. A range's upper end decides, so a wide range errs this way.
- The site passed through these states: CLEAR, CRITICAL, RECEDING, WARNING.

## How to read this

- **This is a check that the parts fit, and a statement of what independence is worth.** Each camera here has
  its own light, drawn apart from the others. That is what cameras at different angles would have to be like
  for these numbers to mean anything outside the simulation, and no real pair has been looked at.
- **One camera is blind when a vehicle parks across it. Three are not.** The share of moments at which the
  model was confident enough for the engine to call a road passable is the plainest gain, with the readings
  more than 10 cm out.
- **Following the level through time did not help here.** A camera keeps its conditions for a whole evening,
  so what it gets wrong it gets wrong at every moment of it, and repeating a mistake is not evidence. And the
  water here rises by up to 15 cm between one moment and the next: a model that expects the level to stay
  near where it was lags behind a fast rise. On the river, where the level moved a centimetre or two an
  hour, following it through time did help.
- **The errors are the renderer's.** The detector reads these scenes to within a centimetre or two. It read a
  real flood to within 13 cm, typically, at the better of two cameras.
- Nothing here is a camera at a site, and nothing in the system calls this chain.
