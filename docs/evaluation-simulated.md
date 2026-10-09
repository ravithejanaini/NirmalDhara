# Depth reading: evaluation (SIMULATED)

> **SIMULATED. These are drawn scenes read by a stand-in, not photographs read by a model. Nothing below is evidence of how accurately any model reads real floods.**

Reader: `scripts/simulated_reader.py`. 22 photos.

**Labels are one person's reading of each photo, not measured depth** (here, the depth each scene was drawn at).
The reader's band is the band of the top of its depth range, the cautious end.

| Measure | Result |
|---|---|
| Band agrees with the label | 12 of 18 (67%) of the photos it read |
| Band within one of the label | 18 of 18 (100%) |
| Declined a photo it should decline (dark, blurred, nothing of known size) | 4 of 4 (100%) |
| Answered a photo it should have declined | 0 |
| Declined a photo that was readable | 0 |
| **Dangerous misses**: told a class it can pass when the photo was at least as deep as that class's limit | **0** photos (two-wheelers 0, cars 0, people on foot 0) |
| Over-cautious for cars: would not say "passable" though the photo was under the limit | 1 |

## Every photo

| Photo | Label | Reader said | Band | Result |
|---|---|---|---|---|
| `normal-00cm.png` | B0 | 0-0 cm, conf 0.8 | B0 | exact |
| `normal-04cm.png` | B1 | 1.3-6.8 cm, conf 0.85 | B1 | exact |
| `normal-08cm.png` | B1 | 5.2-11.1 cm, conf 0.85 | B1 | exact |
| `normal-12cm.png` | B2 | 9-15.5 cm, conf 0.85 | B2 | exact |
| `normal-16cm.png` | B2 | 12.8-19.8 cm, conf 0.85 | B2 | exact |
| `normal-20cm.png` | B3 | 16.2-23.6 cm, conf 0.85 | B3 | exact |
| `normal-25cm.png` | B3 | 20.9-28.9 cm, conf 0.85 | B3 | exact |
| `normal-30cm.png` | B4 | 25.6-34.2 cm, conf 0.85 | B4 | exact |
| `normal-38cm.png` | B4 | 33.2-42.8 cm, conf 0.85 | B4 | exact |
| `normal-46cm.png` | B4 | 40.9-51.4 cm, conf 0.85 | B5 | within one band |
| `waves-10cm.png` | B1 | 3.9-16.9 cm, conf 0.55 | B2 | within one band; cautious for two_wheeler, car, pedestrian |
| `waves-22cm.png` | B3 | 14.3-30.1 cm, conf 0.55 | B4 | within one band |
| `waves-34cm.png` | B4 | 25.3-42.6 cm, conf 0.55 | B4 | exact |
| `glare-18cm.png` | B2 | 0-27.1 cm, conf 0.55 | B3 | within one band; cautious for pedestrian |
| `glare-24cm.png` | B3 | 0-33.3 cm, conf 0.55 | B4 | within one band |
| `glare-36cm.png` | B4 | 1.7-46.3 cm, conf 0.55 | B4 | exact |
| `occluded-14cm.png` | B2 | 12.1-18.9 cm, conf 0.85 | B2 | exact |
| `occluded-26cm.png` | B3 | 24.8-33.2 cm, conf 0.85 | B4 | within one band |
| `no_wheel-20cm.png` | B3 | declined |  | declined, as it should |
| `no_wheel-40cm.png` | B4 | declined |  | declined, as it should |
| `dark-22cm.png` | B3 | declined |  | declined, as it should |
| `blurred-28cm.png` | B3 | declined |  | declined, as it should |

## What this does and does not show

- It shows the evaluation works from end to end: labels in, a reader run on every photo, the
  measures above out, and a dangerous miss would be counted and named.
- It does **not** show how a model reads a real photograph. The reader here measures the water
  line against a wheel in pictures drawn for the purpose, where the wheel is dark and the water
  blue. The scenes were chosen by the person who wrote the reader.
- When a real route and labelled photos exist, run `python scripts/evaluate.py --reader bedrock`.
