# Designs borrowed from defence and from forecasting offices

Since the 1940s armed forces and forecasting offices have worked on the problem this project has: to say
where something is from sensors that are sometimes wrong, and where it will be next. On 10 October 2026 the
model was set against what they built. This page lists which of those designs it already held under plainer
names, which were added, which were tried on the real flood and not kept, and which were not tried and why.

Naming a design does not make the model closer. What it measures is in
[depth-model-river.md](depth-model-river.md) and [forecast-river.md](forecast-river.md), and nowhere else.

## Already in the model

| The design | Who built it, and for what | Where it is here |
|---|---|---|
| **Fusion in levels.** Sensor data is worked up in steps: signal, object, situation, impact, and then the managing of the sensors themselves. | The data fusion model of the US Joint Directors of Laboratories (White 1991; Steinberg, Bowman and White 1999), for joining military sensors. | The pipeline has the same steps. Pixels to a waterline (`waterline.py`, `gauge.py`). One level for the place (`depthmodel.py`, and the fusing in `state.py`). The site's state and who can pass (`state.py`, `bands.py`). When cars lose passage and who is told (`predict.py`, `alerts.py`). Asking for photos while a place is watched (`workflow.py`). |
| **A sensor that misses, and reports clutter.** Each report is either from the target or from clutter, and the target is not always detected. | Probabilistic data association (Bar-Shalom and Tse 1975), for radar and sonar following a target among false echoes. | A witness in `depthmodel.py`: how often it reports a line, "dry" or neither at each level, and the share of its lines that are nowhere near its curve, which are taken as equally likely at any row. |
| **Sensors that are wrong together.** When it is not known how far sensors share their errors, they are joined at shares that add to one. The result is never surer than it should be. | Covariance intersection (Julier and Uhlmann 1997), for trackers that pass their estimates to each other. | The share of face value that one camera's witnesses are counted at (`depthmodel.py`). Here it is learnt from days left out. At Strensham seven strips were counted at 0.05 to 0.20 each. Shares adding to one would be 0.14. |
| **Following through time on a grid.** What is believed is spread by how far the thing could have moved, then weighed by the new report. | Kalman's filter (1960), used to navigate Apollo and since then in radar trackers, is the form for bell-shaped errors. The form on a grid, for errors of any shape, is Bucy and Senne's (1971). | `depthmodel.follow` over levels, and `waterline.track` over the rows of a strip. On a grid, because a strip's evidence is not bell-shaped: it can point at two levels, or at none. |
| **Confirming before believing.** A track is declared only after several sweeps agree. | Track confirmation in radar trackers (Blackman 1986). | The engine's jump hold: a reading two bands away within two minutes is parked until the next one confirms or replaces it. And trust: a reading is trusted if its source is, or if an earlier reading within ten minutes and one band of it came from a trusted source or another device (`state.py`, METHOD C5). |
| **Saying when it cannot vouch for itself.** | Receiver autonomous integrity monitoring (Parkinson and Axelrad 1988): a satellite-navigation receiver in an aircraft checks its satellites against each other, and raises a flag when it cannot stand behind its position. | A road is called passable only at a confidence of 0.6 or more, and otherwise "unknown: treat as not safe" (`bands.py`). The detector answers "occluded", "unsure" or "unreadable" and gives no line. `depthmodel.to_reading` gives no confidence when the witnesses told levels apart no better than not looking. |
| **Figures that one wild value cannot move.** | Robust statistics: the median, and the slope of Theil (1950) and Sen (1968). | One photo's estimates are fused by a weighted median of their low ends, and the depth is the median of the last three readings (`state.py`). The rate of rise is the middle of the slopes of every pair of readings (`predict.rise_rate`). |
| **A camera fixed from known points, and a point fixed from two cameras.** | Photogrammetry, the making of maps from photographs. The direct linear transformation is Abdel-Aziz and Karara's (1971). | `multiview.py` (METHOD C8). Tested on made scenes and tried in a simulation only. |
| **The storage equation.** Water stored changes by what comes in less what goes out. | Level-pool routing, as in HEC-HMS, the flood model of the US Army Corps of Engineers' Hydrologic Engineering Center. | METHOD 15 uses it backwards: from the depths read during a flood, through the volume the road's profile holds (`volume.py`), to the inflow and the capacity the site is short by. Built, and nothing calls it. |

## Added on 10 October 2026

| The design | Who built it, and for what | Where it is here |
|---|---|---|
| **A trend is believed only as far as it stands clear of the noise.** | Wiener's wartime work on predicting an aircraft's path for anti-aircraft fire, a restricted report of 1942 to the US National Defense Research Committee, published in 1949: the best forecast from noisy observations leans on a trend by as much as the signal stands above the noise. Kalata's tracking index (1984) is the same balance in a radar tracker: how much the target manoeuvres against how exact the radar is. | `predict.clear_rise`. The engine says how long until cars lose passage only when the newest reading's range lies wholly above the oldest's (`workflow.cars_lose_passage_min`). A yes-or-no form of the same balance, kept as a design choice. On the river it did not pick the moments when the slope was right: where the rise was clear, the slope was further out than "no change" more often than closer, at both cameras ([forecast-river.md](forecast-river.md)). It keeps the engine from putting minutes on most slopes, and that is all it has been shown to do. |
| **A forecast is judged against "no change".** | Forecast verification as weather services practise it: skill is accuracy set against a reference such as chance, the long-run average, or persistence (American Meteorological Society, Glossary of Meteorology). | `scripts/river_forecast.py`. Until then the prediction stage had not been tried on anything real. |

## Tried on the real flood and not kept

Each was tried on Tewkesbury, the camera used for building. None went as far as the test camera.

| The design | Who built it, and for what | What happened |
|---|---|---|
| **Holding the rate as well as the place.** Between sweeps, belief is moved on along the speed. | The alpha-beta tracker of early radar (Benedict and Bordner 1962) and its forms for targets that turn (Singer 1970). | A tracker that held the level and its rate of rise read the level no closer than `depthmodel.follow`. Its forecasts tied with "no change". From the measured levels the plain slope was closer across a night than it was. |
| **Not deciding early.** Every candidate is kept, and the other sensors and the next sweeps decide between them. | Track-before-detect for faint targets (Barniv 1985) and multiple-hypothesis tracking (Reid 1979). | The detector's belief over rows was kept whole in place of its one line. It held one line in nearly every picture. Where the detector was wrong it was sure, and there was no second line to keep. |
| **Carrying a curve on past what was measured.** | Stream gauging: a station's curve from level to flow is carried past the highest flow measured at it (Rantz and others 1982). | Each strip's curve from level to row would have been carried on past the levels learnt from. At the top of those levels the strips are blind. There is no slope there to carry on. |

## Not tried, and why

- **Running the storage equation forwards**, to say how deep a road will be from the rain forecast. That is
  what HEC-HMS does. It needs the area that drains to the site and the rate at which the site empties. METHOD
  15.2 yields those only after one flood has been recorded there, and no site has one.
- **A rain threshold that moves with how wet the ground is.** That is flash flood guidance (Georgakakos
  2006): the rain over a few hours that is just enough to flood a small catchment, worked out afresh as the
  ground wets and dries. The model's rain index and its fixed 20 mm threshold are the plainest form of it. A
  threshold that moves needs a record of rain against flooding at each site.
- **Several cameras at different angles on the same water.** `multiview.py` has the arithmetic. No two cameras
  in the registry are known to see the same water (METHOD C8).

## What this comes to

- The model already stood on these designs. Setting it beside them changed one rule.
- Four designs were tried on the real flood on 10 October 2026. One was kept, as a design choice: a rule to say
  less, which the river did not confirm.
- What limits the model is not which filter it uses. It is what a camera can see and what it has been
  taught. Every witness in one view fails in the same light. Nothing learnt from levels reads past them. And
  a model taught on some days of a flood reads the days between them, not three days it never saw.

## Sources

Those marked *checked* had their details confirmed against a catalogue, a publisher's record or an
independent citation on 10 October 2026. The rest are given as they are commonly cited and were not checked
that day.

- Abdel-Aziz, Y. I. and Karara, H. M. (1971). Direct linear transformation from comparator coordinates into
  object space coordinates in close-range photogrammetry. *Proceedings of the Symposium on Close-Range
  Photogrammetry*, American Society of Photogrammetry.
- American Meteorological Society. *Glossary of Meteorology*, "skill". https://glossary.ametsoc.org/wiki/Skill
  *Checked.*
- Barniv, Y. (1985). Dynamic programming solution for detecting dim moving targets. *IEEE Transactions on
  Aerospace and Electronic Systems* AES-21. *Checked: title, journal, volume and year.*
- Bar-Shalom, Y. and Tse, E. (1975). Tracking in a cluttered environment with probabilistic data association.
  *Automatica* 11, 451–460. *Checked.*
- Benedict, T. R. and Bordner, G. W. (1962). Synthesis of an optimal set of radar track-while-scan smoothing
  equations. *IRE Transactions on Automatic Control* AC-7.
- Blackman, S. S. (1986). *Multiple-Target Tracking with Radar Applications*. Artech House.
- Bucy, R. S. and Senne, K. D. (1971). Digital synthesis of non-linear filters. *Automatica* 7, 287–298.
  *Checked.*
- Georgakakos, K. P. (2006). Analytical results for operational flash flood guidance. *Journal of Hydrology*
  317, 81–103. *Checked.*
- Julier, S. J. and Uhlmann, J. K. (1997). A non-divergent estimation algorithm in the presence of unknown
  correlations. *Proceedings of the American Control Conference*, 2369–2373. *Checked.*
- Kalata, P. R. (1984). The tracking index: a generalized parameter for α-β and α-β-γ target trackers. *IEEE
  Transactions on Aerospace and Electronic Systems* AES-20(2), 174–182. *Checked.*
- Kalman, R. E. (1960). A new approach to linear filtering and prediction problems. *Journal of Basic
  Engineering* 82, 35–45.
- Parkinson, B. W. and Axelrad, P. (1988). Autonomous GPS integrity monitoring using the pseudorange
  residual. *Navigation* 35(2), 255–274. *Checked.*
- Rantz, S. E. and others (1982). *Measurement and computation of streamflow*. US Geological Survey
  Water-Supply Paper 2175.
- Reid, D. B. (1979). An algorithm for tracking multiple targets. *IEEE Transactions on Automatic Control*
  24(6), 843–854.
- Sen, P. K. (1968). Estimates of the regression coefficient based on Kendall's tau. *Journal of the American
  Statistical Association* 63, 1379–1389.
- Singer, R. A. (1970). Estimating optimal tracking filter performance for manned maneuvering targets. *IEEE
  Transactions on Aerospace and Electronic Systems* AES-6(4), 473–483.
- Steinberg, A. N., Bowman, C. L. and White, F. E. (1999). Revisions to the JDL data fusion model.
  *Proceedings of SPIE* 3719. *Checked: that it exists and what it revised.*
- Theil, H. (1950). A rank-invariant method of linear and polynomial regression analysis. *Proceedings of the
  Royal Netherlands Academy of Sciences* 53.
- US Army Corps of Engineers, Hydrologic Engineering Center. *HEC-HMS Technical Reference Manual*.
- White, F. E. (1991). *Data Fusion Lexicon*. Joint Directors of Laboratories, Data Fusion Sub-Panel.
  *Checked: that it exists and what it defined.*
- Wiener, N. (1949). *Extrapolation, Interpolation, and Smoothing of Stationary Time Series*. Technology
  Press of MIT and Wiley. First issued as a restricted report to the National Defense Research Committee,
  1 February 1942. *Checked.*
