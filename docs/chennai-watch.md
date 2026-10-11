# The rain rule in a second city: Chennai

**Real rain history and real reports. Nothing is deployed in Chennai.** Written by `scripts/chennai_watch.py` from
`data/chennai-flood-reports.json`, news reports found on 11 October 2026 of nine Chennai subways closed for water,
and `data/chennai-rain-history.json.gz`, hourly rain at each from Open-Meteo, the provider the live system asks
(CC BY 4.0). The engine's own rule is replayed over the rain hour by hour, unchanged from Hyderabad: a watch opens
when the rain index reaches 20 mm. This tests the first step of the system and nothing after it.

**A watch stood on 9 of 17 reports.** In Hyderabad the same rule, on the same provider, stood on 0 of 20
([watch-history.md](watch-history.md)).

## Each event

| Event | Report | Places named | A watch stood | Earliest watch | Rain in the history | Wettest hour |
|---|---|---|---|---|---|---|
| Rain of 26 November 2021 | [The News Minute](https://www.thenewsminute.com/article/traffic-diversions-announced-chennai-city-waterlogged-due-rains-158103): Rain from Friday night; 82.5 mm by 05:30 on Saturday. Police closed the Rangarajapuram and Ganeshapuram subways and restricted traffic at Madley subway. | 3 | 0 of 3 | none | 70 to 72 mm | 7.0 mm |
| Rain of 30 December 2021 | [The News Minute](https://www.thenewsminute.com/tamil-nadu/subways-closed-chennai-due-water-logging-traffic-moving-slowly-159328): Rain from the morning into the evening. The Gengu Reddy, Madley, Aranganathan and RBI subways were closed. | 4 | 0 of 4 | none | 7 to 12 mm | 3.6 mm |
| Rain of 29 November 2023 | [DT Next](https://www.dtnext.in/news/chennai/heavy-downpour-throws-life-out-of-gear-in-chennai-751565): Rain on Wednesday night, 62 mm at Kolathur. The Perambur subway was waterlogged. | 1 | 0 of 1 | none | 14 to 14 mm | 3.2 mm |
| Cyclone Michaung | [The News Minute](https://www.thenewsminute.com/tamil-nadu/chennai-rains-list-of-subways-closed-and-traffic-updates): A list of closed subways published at 04:10 on 4 December names all nine. | 9 | 9 of 9 | 04 Dec 04:30 | 266 to 310 mm | 28.0 mm |

## Each place

| Event | Place | The rule | Highest index | Rain on the days |
|---|---|---|---|---|
| Rain of 26 November 2021 | Ganeshapuram subway, Vyasarpadi | **no watch** | 10 | 70 mm |
| Rain of 26 November 2021 | Madley subway, T. Nagar | **no watch** | 9 | 72 mm |
| Rain of 26 November 2021 | Rangarajapuram subway, Kodambakkam | **no watch** | 9 | 72 mm |
| Rain of 30 December 2021 | Gengu Reddy subway, Egmore | **no watch** | 6 | 12 mm |
| Rain of 30 December 2021 | Madley subway, T. Nagar | **no watch** | 6 | 12 mm |
| Rain of 30 December 2021 | Aranganathan subway, Saidapet | **no watch** | 3 | 7 mm |
| Rain of 30 December 2021 | RBI subway, Rajaji Salai | **no watch** | 6 | 12 mm |
| Rain of 29 November 2023 | Sembium subway, Perambur | **no watch** | 5 | 14 mm |
| Cyclone Michaung | Ganeshapuram subway, Vyasarpadi | watch from 04 Dec 04:30 | 59 | 310 mm |
| Cyclone Michaung | Gengu Reddy subway, Egmore | watch from 04 Dec 04:30 | 59 | 310 mm |
| Cyclone Michaung | Madley subway, T. Nagar | watch from 04 Dec 04:30 | 63 | 289 mm |
| Cyclone Michaung | Rangarajapuram subway, Kodambakkam | watch from 04 Dec 04:30 | 63 | 289 mm |
| Cyclone Michaung | Aranganathan subway, Saidapet | watch from 04 Dec 06:30 | 44 | 266 mm |
| Cyclone Michaung | Duraisamy subway, T. Nagar | watch from 04 Dec 04:30 | 63 | 289 mm |
| Cyclone Michaung | Villivakkam subway | watch from 04 Dec 06:30 | 50 | 289 mm |
| Cyclone Michaung | Sembium subway, Perambur | watch from 04 Dec 04:30 | 59 | 310 mm |
| Cyclone Michaung | RBI subway, Rajaji Salai | watch from 04 Dec 04:30 | 59 | 310 mm |

## What the rule costs

Days from 1 October to 31 December with a watch standing, at one forecast cell on average, and the reports caught, at other thresholds.

| Threshold | Reports caught | Watch days, 2021 | Watch days, 2023 |
|---|---|---|---|
| 10 mm | 10 of 17 | 13 | 12 |
| **20 mm** | 9 of 17 | 2 | 2 |
| 30 mm | 9 of 17 | 1 | 1 |
| 40 mm | 9 of 17 | 1 | 1 |
| 50 mm | 8 of 17 | 1 | 1 |

## Model by model

| Rain from | Reports caught |
|---|---|
| The provider's own choice | 9 of 17 |
| ECMWF IFS | not held |
| NOAA GFS | 9 of 17 |
| DWD ICON | 9 of 10 |
| Canadian GEM | 9 of 10 |
| JMA | 9 of 17 |
| UK Met Office | 9 of 10 |

## What this shows, and what it does not

- **The rule opens on the cyclone and on nothing smaller.** Cyclone Michaung put 266 to 310 mm into the rain
  history over two days, with an hour of 28 mm, and the watch opened at every one of the nine subways. The three
  ordinary rains closed subways too, and the watch opened at none of them: their wettest hour in the history was
  3 to 7 mm. That is the Hyderabad failure again. A forecast spreads a downpour over its cell and its hours, and
  a subway floods under the downpour.
- **It was not early.** The watch opened at 04:30 on 4 December. The list of closed subways was published at
  04:10 the same morning. The rule would have confirmed the closures. It would not have come before them.
- **One event of four.** Nine of seventeen reports is one storm counted nine times. The honest figure is that
  the rule opened for one event in four.
- **Misses only.** A watch on a day with no report is not shown to be a false alarm, because no report is not a
  dry subway. The rule cost about two watch days a season in each of the two years.
- **The positions are rough.** Each subway is placed by hand to about a kilometre. That is enough for a forecast
  cell of about 5 km and no more.
- **Nothing is built in Chennai.** No camera, no site record in the live system, no visit. What this adds is
  that the first step of the system has now been set against a coastal city's rain, with the rule unchanged,
  and that the step after it, a camera reading depth at the subway, is what the three missed rains would need.
- **2021 holds three weather models and 2023 six.** ECMWF is held for neither year.

## To run it again

    python scripts/chennai_watch.py              # from the rain history in the repository
    python scripts/chennai_watch.py --fetch      # asks Open-Meteo again first
