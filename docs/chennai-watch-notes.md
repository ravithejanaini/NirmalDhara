
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
