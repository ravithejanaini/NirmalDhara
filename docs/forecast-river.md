# The level ahead: the slope of the last readings against "no change", on a real flood

**Real fixed cameras, a real flood, measured water levels.** Written by `scripts/river_forecast.py` on the
hourly pictures of two river cameras near Tewkesbury, 21 November to 5 December 2012, published with the
water level read from each picture against surveyed points ([credits](../samples/tewkesbury/CREDITS.md)). The
pictures are not in the repository. This is a river, not a street, and not Hyderabad.

The prediction stage takes a slope through the last three to six readings and carries it forward
(`nirmaldhara/predict.py`). Each table sets that against saying the level will stay where the last reading
put it, which is how a forecasting office judges a forecast. Three days in a row are left out together,
the model learns from the rest, and follows the level through those three as the pictures came. Each cell
is the typical miss and the miss nine in ten were under.

## Tewkesbury: used to choose the guard

132 pictures on 15 days, 8.87 to 12.02 m, left out in 5 runs of three days. Read by the model through time, with the learnt gauge as one more witness, the level now was 23 cm out, typically, and nine in ten within 88 cm. Its range held the level in 73 of 132. The dataset's own doubt in a measured level is 15 cm, typically.

**From the camera's readings:**

| Ahead by | Forecasts | No change | The slope | The slope when it is clear | Times it was clear |
|---|---|---|---|---|---|
| 1 hour | 105 | 20 / 86 cm | 23 / 86 cm | 22 / 86 cm | 7 of 105 |
| 3 hours | 78 | 14 / 85 cm | 24 / 97 cm | 20 / 85 cm | 7 of 78 |
| 6 hours | 38 | 11 / 87 cm | 28 / 97 cm | 22 / 87 cm | 5 of 38 |
| The next morning | 10 | 32 / 96 cm | 38 / 95 cm | 32 / 96 cm | 0 of 10 |
| 24 hours | 67 | 26 / 112 cm | 53 / 177 cm | 26 / 112 cm | 3 of 67 |

Forecast by forecast, the slope was closer than "no change" in 70 of 298 and further out in 215. Of the 22 in which it was clear, it was closer in 1 and further out in 21.

**From the measured levels themselves, each with the dataset's own doubt as its range:**

| Ahead by | Forecasts | No change | The slope | The slope when it is clear | Times it was clear |
|---|---|---|---|---|---|
| 1 hour | 105 | 0 / 5 cm | 1 / 7 cm | 0 / 7 cm | 15 of 105 |
| 3 hours | 78 | 0 / 10 cm | 3 / 14 cm | 0 / 17 cm | 13 of 78 |
| 6 hours | 38 | 5 / 26 cm | 5 / 14 cm | 5 / 18 cm | 8 of 38 |
| The next morning | 10 | 14 / 55 cm | 18 / 30 cm | 14 / 36 cm | 1 of 10 |
| 24 hours | 67 | 20 / 75 cm | 15 / 60 cm | 20 / 64 cm | 7 of 67 |

Forecast by forecast, the slope was closer than "no change" in 61 of 298 and further out in 72. Of the 44 in which it was clear, it was closer in 19 and further out in 23.

## Strensham: run once, with the guard fixed beforehand

109 pictures on 13 days, 10.65 to 13.23 m, left out in 4 runs of three days. Read by the model through time, with the learnt gauge as one more witness, the level now was 32 cm out, typically, and nine in ten within 59 cm. Its range held the level in 85 of 109. The dataset's own doubt in a measured level is 5 cm, typically.

**From the camera's readings:**

| Ahead by | Forecasts | No change | The slope | The slope when it is clear | Times it was clear |
|---|---|---|---|---|---|
| 1 hour | 86 | 33 / 60 cm | 34 / 61 cm | 34 / 60 cm | 7 of 86 |
| 3 hours | 61 | 34 / 61 cm | 34 / 60 cm | 34 / 61 cm | 5 of 61 |
| 6 hours | 31 | 44 / 69 cm | 44 / 62 cm | 44 / 69 cm | 3 of 31 |
| The next morning | 9 | 56 / 103 cm | 51 / 160 cm | 63 / 111 cm | 1 of 9 |
| 24 hours | 58 | 68 / 95 cm | 61 / 125 cm | 68 / 108 cm | 3 of 58 |

Forecast by forecast, the slope was closer than "no change" in 106 of 245 and further out in 101. Of the 19 in which it was clear, it was closer in 5 and further out in 14.

**From the measured levels themselves, each with the dataset's own doubt as its range:**

| Ahead by | Forecasts | No change | The slope | The slope when it is clear | Times it was clear |
|---|---|---|---|---|---|
| 1 hour | 86 | 0 / 5 cm | 1 / 5 cm | 0 / 5 cm | 29 of 86 |
| 3 hours | 61 | 0 / 10 cm | 2 / 9 cm | 3 / 10 cm | 25 of 61 |
| 6 hours | 31 | 7 / 21 cm | 8 / 21 cm | 8 / 21 cm | 19 of 31 |
| The next morning | 9 | 26 / 62 cm | 10 / 48 cm | 26 / 48 cm | 2 of 9 |
| 24 hours | 58 | 35 / 56 cm | 27 / 63 cm | 30 / 59 cm | 8 of 58 |

Forecast by forecast, the slope was closer than "no change" in 68 of 245 and further out in 87. Of the 83 in which it was clear, it was closer in 33 and further out in 48.

## How to read this

**Strensham is the test.** Its strips, the model and the guard were fixed before it was run, and it was run
once. This was the fifth time Strensham's pictures were read. After the run one line was added under each
table, counting forecast by forecast how often the slope was closer. No figure in the tables changed.

**Tewkesbury was used to choose the guard.** Two forms were tried there: the one kept, and one that shrinks the
slope by how far it stands clear of its own doubt. They did much the same. The plainer was kept.

**The leaving-out is harder than before.** In [depth-model-river.md](depth-model-river.md) every other day was
left out, so each unseen day had days learnt from on either side of it. Here three days in a row are left out,
so that a forecast can cross a night inside days the model never saw. Nothing in the model was changed.

**"The slope when it is clear"** carries the slope forward only when the newest of the readings it was taken
through has a range lying wholly above the oldest's, or wholly below. Otherwise it says no change.

## What Strensham shows

- **From the camera's readings, neither way tells the level ahead.** An hour ahead "no change" was 33 cm out,
  typically. That is the reading's own miss, 32 cm. The slope was within a centimetre of it at one, three and
  six hours. Forecast by forecast it was closer 106 times and further out 101 times: a coin.
- **Across a night the slope's worst misses were a third to a half larger.** To the next morning nine in ten were
  under 160 cm, against 103 cm for "no change". A day ahead, 125 cm against 95 cm. Its typical miss was a
  little smaller, 51 against 56 cm and 61 against 68 cm. There are only 9 forecasts to the next morning.
- **From the measured levels the slope gained much across a night and lost a little, often, within a day.**
  To the next morning it was 10 cm out against 26 cm. A day ahead, 27 cm against 35 cm, though its worst
  misses were no smaller. Within six hours the river barely moved, and forecast by forecast the slope was
  further out 87 times and closer 68.
- **The guard did not pick the moments when the slope was right.** With the camera's readings it let the slope
  through in 19 of 245 forecasts. In those the slope was closer than "no change" 5 times and further out 14
  times. With the measured levels it let it through in 83, and there it was closer 33 times and further out
  48.
- **Against the slope as it was, the guard traded.** Across a night its typical miss was larger, 63 against
  51 cm, and its worst ones smaller, nine in ten under 111 against 160 cm. Within a day there was nothing
  between them. Against "no change" it was never closer.
- **Three days in a row is much harder than every other day.** The level now was 32 cm out, typically, and
  nine in ten within 59 cm. With every other day left out the same model was 12 cm out and nine in ten
  within 41 cm.

## What Tewkesbury shows

- From the camera's readings the slope was further out than "no change" at every distance, and twice as far
  a day ahead: 53 against 26 cm. Forecast by forecast it was further out 215 times in 298.
- The guard was chosen for that. It let the slope through in 22 of 298, and the worst misses were those of
  "no change" again. But in those 22 the slope was further out 21 times.
- From the measured levels, which the dataset doubts by 15 cm here, the slope's worst misses were smaller
  from six hours on: nine in ten under 14 against 26 cm, 30 against 55 cm, 60 against 75 cm.
- The level now was 23 cm out, typically, where it was 12 cm with every other day left out.

## What it means

- **A forecast is as good as the reading it starts from, and no better.** With the camera's readings the miss
  ahead is the miss now. Nothing in the prediction stage can mend that.
- **On this river the slope did not earn its place.** From the camera's readings it was a coin at one camera
  and worse than one at the other. From the measured levels it told the next morning better at Strensham and
  cut the worst misses at Tewkesbury, and within a day it was the worse guide.
- **The guard is a rule to say less, and nothing more.** It does not find the moments when the slope is
  right: in all four tables, where the rise or fall was clear the slope was further out more often than
  closer. What it does is keep the engine quiet. Without it the engine puts minutes on any upward slope. With
  it the engine speaks in about one forecast in thirteen from the camera's readings here.
- **It was kept as a design choice, not as a finding.** A rise smaller than the doubt in the readings may be
  no rise at all, and minutes should not be put on it. That is reasoning. This river did not confirm it, and
  on the test camera the guard was no closer than the slope it replaced. Read strictly, this river says
  that readings like a camera's should carry no minutes at all.
- **"Cars are likely to lose passage in N minutes" has nothing real behind it.** The engine can write that
  line (`workflow.cars_lose_passage_min`). It has never been in a delivered alert, and the one trial of its
  arithmetic on real water is this one.
- **The depth model's 12 cm was reading between days it had seen.** Left without the days on either side, it
  was 23 and 32 cm out. A camera that has watched some days of a flood has not learnt the others.

## What was tried on the way and not kept

Three more designs were tried on Tewkesbury while this was built. None went as far as Strensham.

- **A tracker that holds the level and its rate of rise**, as a radar holds where an aircraft is and how fast
  it is going. It read the level no closer than the model as it is. Its forecasts tied with "no change". From
  the measured levels the plain slope was closer across a night than it was.
- **Keeping every line the detector might have meant**, and letting the other strips and the hours decide
  between them, as a tracker does with a faint target. The detector's belief held one line in nearly every
  picture. Where it was wrong it was sure, and there was no second line to keep.
- **Carrying each strip's curve on past the levels learnt from**, as a river gauge's curve is carried past
  the highest flow measured at it. At the top of the levels the strips are blind: the two on the grass bank
  report nothing above 11.9 m, and the far lock wall reports the same row from 11.45 m up. There is no slope
  there to carry on.

All of the designs looked at, kept or not, are listed in [borrowed-designs.md](borrowed-designs.md).

## What this is not

- **Not a street, and not Hyderabad.** A river in England that moved a few centimetres in six hours and was
  read once an hour. A flooded underpass can rise that much in minutes, read minutes apart. Whether the slope
  is a guide there has not been measured either way.
- **Not a forecast from rain.** Nothing here uses rain. It is the level carried forward from the level.
- **Not independent levels.** The levels learnt from and the levels judged against were read by the same
  people from these same pictures. A level in the dataset often stands still all day and then steps
  overnight, which a river does not do: the levels look to have been read to the nearest surveyed mark.
- **Not many forecasts across a night.** 9 and 10 to the next morning. Those rows can turn on one day.
- **Not a second flood.**
