# Camera angles: a simulation

**SIMULATED. No real camera, photo or flood is behind any number here.** Written by
`scripts/simulate_cameras.py` (seed 7). It tests one narrow thing: whether the geometry of the
reference-object method in METHOD.md still gives the right depth when cameras are mounted at
different heights, distances and angles. It does not test finding the waterline in a real image.

## What was simulated

- 400 cameras, each at a random height (2.5 to 7 m), distance (3 to 25 m), sideways offset,
  tilt, roll (up to 4°), focal length and barrel distortion.
- 24 were refused at enrolment because the 150 cm gauge was out of frame or under 60
  pixels tall. 376 were kept.
- The gauge was marked by hand with an error of about 1.5 px, 40 times per camera, and the
  waterline found with an error of about 2.0 px, at depths from 5 to 60 cm.

## Result

Error in centimetres: the middle value, and the value 95% of readings stay under.

| Camera tilt below horizontal | Cameras | Two marks (as designed) | Three marks |
|---|---|---|---|
| 0° to 15° | 159 | 2.4 cm, 95% under 7.9 cm | 2.3 cm, 95% under 7.8 cm |
| 15° to 30° | 136 | 2.1 cm, 95% under 6.5 cm | 1.7 cm, 95% under 6.3 cm |
| 30° to 45° | 52 | 2.6 cm, 95% under 6.9 cm | 1.3 cm, 95% under 4.5 cm |
| 45° to 70° | 29 | 3.6 cm, 95% under 8.4 cm | 1.4 cm, 95% under 5.0 cm |
| **All** | 376 | 2.4 cm, 95% under 7.4 cm | 1.8 cm, 95% under 6.8 cm |

The same readings, grouped by how large the gauge appears (a distant camera sees it small):

| Gauge height in the image | Cameras | Two marks (as designed) | Three marks |
|---|---|---|---|
| 60 to 120 px | 189 | 2.7 cm, 95% under 8.3 cm | 2.6 cm, 95% under 8.1 cm |
| 120 to 250 px | 163 | 2.0 cm, 95% under 6.1 cm | 1.5 cm, 95% under 4.5 cm |
| over 250 px | 24 | 2.5 cm, 95% under 7.0 cm | 0.8 cm, 95% under 2.6 cm |

## What it means

- **Distance matters most.** When the 150 cm gauge covers under 120 pixels, one pixel is more than
  1.25 cm, so a two-pixel slip in finding the waterline is already several centimetres. Neither
  method can fix that; only a closer camera, a longer lens or a larger image can.
- **Angle matters for the designed method.** Two marks and one scale need no angle to be calculated,
  but they assume every centimetre of the gauge covers the same number of pixels. A camera looking
  steeply down breaks that, and the error grows at the steepest tilts.
- **A third mark removes the angle error.** Three known points fix the exact mapping from image
  position to height, so steep cameras read as well as level ones. What is left is the marking and
  waterline error and lens distortion.
- The depth bands are 8 to 20 cm wide and a reading is always a range. The 95% figures above say how
  wide that range must be for a camera of each kind to be honest.

## A handheld phone (an iPhone's main camera)

A resident's photo has no gauge and no dry view to mark, so the depth is read against a car's
wheel, as METHOD.md C2 estimator 2 intends. The wheel's base is under water, so only its top, its
hub and the waterline can be found.

- 300 photo positions: held 1.0 to 1.6 m above the road, 3 to 15 m from the car, tilted to look
  at it, never level (roll up to 8°).
- The camera is nominal: 4032 x 3024 pixels, a lens equal to 26 mm. These are
  the published figures for a recent iPhone's main camera, not measurements of one.
- The car's wheel is anywhere from 56 to 70 cm; the method assumes 62 cm.
- Depths of 5 to 25 cm. Above about 31 cm the hub is under water and this reading fails.

| Distance to the car | Photos | Wheel height in the image | If the wheel's size were known | Assuming 62 cm |
|---|---|---|---|---|
| 3 to 6 m | 68 | about 403 px | 1.1 cm, 95% under 3.4 cm | 1.3 cm, 95% under 3.8 cm |
| 6 to 10 m | 107 | about 220 px | 2.0 cm, 95% under 6.0 cm | 2.1 cm, 95% under 6.2 cm |
| 10 to 15 m | 125 | about 146 px | 2.9 cm, 95% under 8.8 cm | 3.0 cm, 95% under 9.0 cm |
| **All** | 300 | about 200 px | 2.0 cm, 95% under 7.2 cm | 2.1 cm, 95% under 7.5 cm |

- **Distance decides it.** From within 6 m the wheel is about 400 pixels tall and the reading is
  within about 4 cm 95% of the time. From 10 to 15 m it is about 150 pixels and the same slip in
  finding the waterline costs up to 9 cm. Standing closer is worth more than any correction.
- **Not knowing the car matters less than expected.** The wheel sets both the scale and the height
  the depth is taken from, so a wrong wheel size shifts the answer only in proportion to the depth:
  at most about 3 cm at 25 cm deep, and under 1 cm in shallow water.
- **The tilt and roll of a handheld shot cost little**, because the phone is low and looks almost
  level at the wheel.
- This is why a resident's photo gives a range, and why the capture page should ask for a photo from
  a few metres, not from across the road.

## What it does not show

- Whether a model or a segmentation step can find the waterline at night, in rain, with reflections
  or with a vehicle in front of the gauge. That is the dominant error in practice and is untested.
- Any real lens, mounting, or camera that has been knocked out of position since it was enrolled.
- That sites have a gauge. None of the nine sites has a reference object recorded.
