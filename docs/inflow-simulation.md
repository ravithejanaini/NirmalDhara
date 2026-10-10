# The storage equation on a made underpass

**SIMULATED. No real place, rain or flood is behind any number here.** Written by `scripts/simulate_inflow.py`. The underpass is the worked example of
METHOD.md section 15.1: ramps of 4% and 5%, 14 m wide. 24 storms were made, of 17 to 78 mm in 30 to 90 minutes, and the water was moved by the
same equation `nirmaldhara/inflow.py` uses. So this shows the arithmetic holding together, and how it bends as
the readings and the rain get worse. It cannot show that a real underpass behaves this way. No place in this
project has a flood on record.

The floods were made with 8000 square metres of ground draining to the dip and 40 litres a second leaving it.

## What the floods reveal

| Depth read by | From | The ground the water came from | The rate it drains at |
|---|---|---|---|
| A painted gauge, 3 cm | One flood | 7913 to 8430 sq m, about 8171 | 39 to 43 litres a second, about 41 |
| A painted gauge, 3 cm | Three floods | 7826 to 8430 sq m, about 8104 | 38 to 43 litres a second, about 40 |
| A painted gauge, 3 cm | All of them | 7731 to 8658 sq m, about 8108 | 37 to 44 litres a second, about 40 |
| A wheel or a kerb, 8 cm | One flood | 7983 to 9400 sq m, about 8658 | 36 to 46 litres a second, about 41 |
| A wheel or a kerb, 8 cm | Three floods | 7656 to 9400 sq m, about 8350 | 36 to 46 litres a second, about 40 |
| A wheel or a kerb, 8 cm | All of them | 7459 to 9725 sq m, about 8312 | 33 to 48 litres a second, about 40 |

## Each flood from the ones before it

Every flood after the first, played forward from its first reading by what the floods before it revealed.

| Depth read by | The rain | The deepest water said held the deepest read | Width of what was said |
|---|---|---|---|
| A painted gauge, 3 cm | Known exactly | 23 of 23 | 10 cm |
| A painted gauge, 3 cm | Known to a tenth | 23 of 23 | 10 cm |
| A painted gauge, 3 cm | A fifth of what fell | 0 of 23 | 10 cm |
| A wheel or a kerb, 8 cm | Known exactly | 23 of 23 | 23 cm |
| A wheel or a kerb, 8 cm | Known to a tenth | 23 of 23 | 23 cm |
| A wheel or a kerb, 8 cm | A fifth of what fell | 0 of 23 | 22 cm |

## Minutes until cars lose passage

Said when the reading first passes 8 cm, in the floods that went on to 20 cm. Minus is too soon.

| Depth read by | Floods | The straight line of `predict.py` | The same line through the volume |
|---|---|---|---|
| A painted gauge, 3 cm | 14 | -1 minutes, typically; -4 to +3 | +0 minutes, typically; -2 to +9 |
| A wheel or a kerb, 8 cm | 6 | -4 minutes, typically; -8 to +0 | -4 minutes, typically; -8 to +0 |

## The rain that closes the road

The rain in one hour that would bring a dry road to the depth at which each class loses passage.

| Class | With the true figures | With what three floods revealed, read by a painted gauge |
|---|---|---|
| two wheeler | 18.9 mm | 17.2 to 20.5 mm |
| auto | 18.9 mm | 17.2 to 20.5 mm |
| car | 19.6 mm | 17.9 to 21.2 mm |
| pedestrian | 21.5 mm | 19.7 to 23.2 mm |
| suv | 21.5 mm | 19.7 to 23.2 mm |

## How to read this

- **The figures come back because the water was made by the same equation.** That is a check on the arithmetic and
  on nothing else.
- **Loose readings give wide answers, not wrong ones.** Read to 8 cm, the ground the water came from is known to
  within a wide range, and what is said ahead is as wide.
- **A forecast from rain is no better than the rain.** With a fifth of the rain that fell, which is how far short
  [watch-history.md](watch-history.md) found the forecast the live system is fed, the deepest water said held the
  deepest read in none of the floods.
- **With water running in steadily the straight line says cars are lost sooner than they are**, because a dip
  widens as it fills: 16 minutes where it is 27, in the case `tests/test_inflow.py` works by hand. In these made
  storms the rain was still building when the forecast was made, and the two lines came out within a minute or
  two of each other. Neither knows that the rain will ease or grow.
- **The rain that closes the road needs no forecast.** It is a figure for this place that a person can hold any
  forecast, warning or gauge reading against.

## What this is not

- **Not a real underpass.** A real one has drains that block, pumps that start late, and water arriving from
  streets around it after the rain has stopped.
- **Not a test of the equation.** The made water obeys it by construction.
- **Not connected to anything.** Nothing calls `nirmaldhara/inflow.py`, and no place in the registry has a road
  profile, without which it cannot run.
