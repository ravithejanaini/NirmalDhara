# The rain rule against the days these places were reported under water

**Real rain history and real reports.** Written by `scripts/watch_history.py` from `data/flood-reports.json`,
news reports found on 11 October 2026 that name one of the nine places or its neighbourhood as under water on a
stated day, and `data/rain-history.json.gz`, hourly rain at each place from Open-Meteo, the provider the live
system asks (CC BY 4.0). The engine's own rule is replayed over the rain hour by hour. This tests the first
step of the system, the watch, and nothing after it. It is not a measurement of depth.

"The provider's own choice" is the rain as the live system asks for it, with the provider picking the weather
model. "The highest of seven" takes seven models by name, the provider's own choice among them, and uses the largest in each
hour; all seven are held for 2025 and 2026.
A watch opens when the rain index reaches 20 mm.

## Each report

| Place | Day | The report | The provider's own choice | The highest of seven models |
|---|---|---|---|---|
| Lingampally railway underpasses | 21 to 22 Mar 2025 | Names the place. [Siasat Daily](https://www.siasat.com/rains-bring-respite-but-waterlogging-cripples-kondapur-lingampally-3198056/): A storm on Friday night; next morning police said traffic was disrupted at the Lingampally railway underbridge on both sides. | **no watch**, index to 0 | **no watch**, index to 6 |
| Lingampally railway underpasses | 11 to 12 Jun 2025 | Names the place. [South First](https://thesouthfirst.com/telangana/heavy-rains-lash-parts-of-hyderabad-and-telangana/): Rain through the night of 11 June; police said traffic was slow at the Lingampally railway underbridge because of waterlogging. | **no watch**, index to 4 | watch from 11 Jun 06:30, index to 28 |
| Lingampally railway underpasses | 22 to 23 Jun 2026 | Names the area only. [Siasat Daily](https://www.siasat.com/waterlogging-power-cuts-grip-hyderabad-after-overnight-rain-3494620/): Rain overnight; 11.7 cm recorded at Lingampally. The underpass is not named. | **no watch**, index to 4 | **no watch**, index to 8 |
| Raheja Mindspace entrance underpass | 2 Aug 2019 | Names the area only. [The News Minute](https://www.thenewsminute.com/article/rains-lash-hyderabad-flooded-roads-and-traffic-snarls-return-106608): A large traffic jam on the road from Mindspace to Biodiversity junction during rain. Water at the underpass is not stated. | **no watch**, index to 13 | seven not held |
| Near Shilparamam, Madhapur | 30 Sep 2019 | Names the place. [The News Minute](https://www.thenewsminute.com/article/moderate-rainfall-brings-traffic-standstill-cyberabad-it-corridor-109758): Police reported waterlogging and slow traffic near Shilparamam. | **no watch**, index to 3 | seven not held |
| Nectar Gardens, Madhapur | 24 Sep 2019 | Names the place. [The News Minute](https://www.thenewsminute.com/article/torrential-rains-bring-hyderabad-standstill-roads-flood-109448): Inundation at Nectar Gardens towards Road No 45 on Tuesday evening. | **no watch**, index to 4 | seven not held |
| Nectar Gardens, Madhapur | 30 Sep 2019 | Names the place. [The News Minute](https://www.thenewsminute.com/article/moderate-rainfall-brings-traffic-standstill-cyberabad-it-corridor-109758): Heavy flow of water on the Nectar Gardens road, with cars stuck in it. | **no watch**, index to 3 | seven not held |
| Cyber Towers junction | 2 Aug 2019 | Names the area only. [The News Minute](https://www.thenewsminute.com/article/rains-lash-hyderabad-flooded-roads-and-traffic-snarls-return-106608): A large traffic jam in and around Cyber Towers during rain. Water at the junction is not stated. | **no watch**, index to 13 | seven not held |
| Lakdikapul railway bridge | 3 Apr 2025 | Names the place. [ETV Bharat](https://www.etvbharat.com/en/!state/heavy-rains-lash-hyderabad-bring-relief-from-heat-enn25040305708): A downpour from about two in the afternoon; Lakdikapul is listed among the flooded roads. | **no watch**, index to 7 | **no watch**, index to 13 |
| Lakdikapul railway bridge | 7 Aug 2025 | Names the place. [PTI, in The Week](https://www.theweek.in/wire-updates/national/2025/08/07/mes28-tl-rain.html): Heavy rain on Thursday evening; traffic crawled at Lakdikapul amid waterlogged roads. | **no watch**, index to 10 | **no watch**, index to 17 |
| Khairatabad junction | 3 Apr 2025 | Names the place. [ETV Bharat](https://www.etvbharat.com/en/!state/heavy-rains-lash-hyderabad-bring-relief-from-heat-enn25040305708): The main road at Khairatabad was flooded and traffic was turned away towards Panjagutta. | **no watch**, index to 7 | **no watch**, index to 13 |
| Khairatabad junction | 7 Aug 2025 | Names the area only. [Deccan Chronicle](https://deccanchronicle.com/southern-states/telangana/cloudburst-like-rain-alert-issued-for-hyderabad-1896141): Three rain gauges at Khairatabad recorded over 100 mm. Water on the road there is not stated. | **no watch**, index to 10 | **no watch**, index to 17 |
| Khairatabad junction | 3 Aug 2026 | Names the place. [Telangana Today](https://telanganatoday.com/hyderabad-roads-waterlogged-after-heavy-afternoon-downpour): Khairatabad is named among the inundated places; traffic slowed near its Metro station. | **no watch**, index to 3 | **no watch**, index to 11 |
| Maitrivanam, Ameerpet | 7 Aug 2025 | Names the area only. [Deccan Chronicle](https://deccanchronicle.com/southern-states/telangana/cloudburst-like-rain-alert-issued-for-hyderabad-1896141): 101.5 mm recorded at Maitrivanam; police alerts for waterlogged roads in Ameerpet. Three days later the road at Maitrivanam was said to have been under water several times that month. | **no watch**, index to 11 | **no watch**, index to 17 |
| Maitrivanam, Ameerpet | 19 Sep 2025 | Names the place. [Deccan Chronicle](https://deccanchronicle.com/southern-states/telangana/heavy-rain-floods-hyderabad-causes-traffic-chaos-1904811): The main road at Maitrivanam was under water on Friday evening and people waded through it. | **no watch**, index to 11 | **no watch**, index to 13 |
| Al Jubail Colony, Falaknuma | 13 to 14 Oct 2020 | Names the place. [The Caravan](https://caravanmagazine.in/photo-essay/hyderabad-struggles-in-aftermath-of-rains-floods): On the first day of the October 2020 floods the water in Al Jubail Colony was reported at over four feet. | **no watch**, index to 19 | seven not held |

## How many were caught

| Reports | Rain | A watch stood on the day |
|---|---|---|
| That name the place | The provider's own choice | 0 of 11 |
| That name the area only | The provider's own choice | 0 of 5 |
| That name the place, 2025 and 2026 | The highest of seven models | 1 of 7 |
| That name the area only, 2025 and 2026 | The highest of seven models | 0 of 3 |

With nothing forecast for the hours ahead, the rule counting only rain already fallen: 0 of 11 with the provider's own choice, 1 of 7 with the highest of seven.

One more report gives no day. [The News Minute](https://www.thenewsminute.com/article/rainfall-choking-hyderabads-it-corridor-police-suggest-alternative-routes-104141): A police advisory published in the small hours of 24 June 2019 names all four as places that waterlog, 'with the onset of monsoon'. It gives no day. The three days before it are taken here, and counted apart from the dated reports.

| Place | The provider's own choice |
|---|---|
| Raheja Mindspace entrance underpass | **no watch**, index to 6 |
| Near Shilparamam, Madhapur | **no watch**, index to 6 |
| Nectar Gardens, Madhapur | **no watch**, index to 6 |
| Cyber Towers junction | **no watch**, index to 6 |

## Model by model, 2025 and 2026

The reports of those years, and the days from 1 March to 31 October with a watch standing, for one place on average.

| Rain from | Caught, of those that name the place | Caught, of those that name the area | Watch days a season |
|---|---|---|---|
| The provider's own choice | 0 of 7 | 0 of 3 | 0 |
| ECMWF IFS | 0 of 7 | 0 of 3 | 0 |
| NOAA GFS | 0 of 7 | 0 of 3 | 2 |
| DWD ICON | 1 of 7 | 0 of 3 | 1 |
| Canadian GEM | 1 of 7 | 0 of 3 | 3 |
| JMA | 0 of 7 | 0 of 3 | 0 |
| UK Met Office | 0 of 7 | 0 of 3 | 4 |
| **The highest of the seven, hour by hour** | 1 of 7 | 0 of 3 | 10 |

## What the rule costs, year by year

| Year | Rain | Days of history | Watches opened at one place | Days with a watch standing |
|---|---|---|---|---|
| 2019 | The provider's own choice | 245 | 0 | 0 |
| 2020 | The provider's own choice | 245 | 1 | 1 |
| 2025 | The provider's own choice | 245 | 0 | 0 |
| 2025 | The highest of seven | 245 | 16 | 18 |
| 2026 | The provider's own choice | 223 | 0 | 0 |
| 2026 | The highest of seven | 223 | 3 | 3 |

## Other thresholds

The reports that name the place, and the days in a season with a watch standing at one place, on average.

| Threshold | Caught, the provider's own choice | Watch days a season | Caught, the highest of seven | Watch days a season |
|---|---|---|---|---|
| 5 mm | 5 of 11 | 26 | 7 of 7 | 86 |
| 10 mm | 3 of 11 | 6 | 6 of 7 | 41 |
| 15 mm | 1 of 11 | 1 | 2 of 7 | 19 |
| **20 mm** | 0 of 11 | 0 | 1 of 7 | 10 |
| 30 mm | 0 of 11 | 0 | 0 of 7 | 4 |
| 40 mm | 0 of 11 | 0 | 0 of 7 | 1 |
| 50 mm | 0 of 11 | 0 | 0 of 7 | 1 |

## The rain history against gauges

Where a report gives what a rain gauge near the place recorded, beside what the rain history holds for the same days.

| Place | Days | Gauge | The provider's own choice | The wettest of the seven models |
|---|---|---|---|---|
| Lingampally railway underpasses | 11 to 12 Jun 2025 | [University of Hyderabad, about 5 km away](https://thesouthfirst.com/telangana/heavy-rains-lash-parts-of-hyderabad-and-telangana/): 148 mm | 13 mm | 74 mm |
| Lingampally railway underpasses | 22 to 23 Jun 2026 | [Lingampally](https://www.siasat.com/waterlogging-power-cuts-grip-hyderabad-after-overnight-rain-3494620/): 117 mm | 6 mm | 14 mm |
| Near Shilparamam, Madhapur | 30 Sep 2019 | [Madhapur](https://www.thenewsminute.com/article/moderate-rainfall-brings-traffic-standstill-cyberabad-it-corridor-109758): 60 mm | 4 mm | seven not held |
| Cyber Towers junction | 2 Aug 2019 | [Madhapur, 08:30 to 18:00](https://www.thenewsminute.com/article/rains-lash-hyderabad-flooded-roads-and-traffic-snarls-return-106608): 38 mm | 47 mm | seven not held |
| Maitrivanam, Ameerpet | 7 Aug 2025 | [Maitrivanam, Ameerpet](https://deccanchronicle.com/southern-states/telangana/cloudburst-like-rain-alert-issued-for-hyderabad-1896141): 102 mm | 23 mm | 26 mm |
| Khairatabad junction | 7 Aug 2025 | [Khairatabad, three gauges, each over](https://deccanchronicle.com/southern-states/telangana/cloudburst-like-rain-alert-issued-for-hyderabad-1896141): 100 mm | 24 mm | 26 mm |

## How to read this

**The reports are what an hour's search found.** Sixteen dated reports, eleven of which name the place itself.
They are not every flood. A day with no report was not shown to be dry, so this can count floods the rule
missed and cannot count false watches. "Watch days" is what the rule costs, water or no water.

**The rain is a weather model's, not a gauge's.** Asked as the live system asks, the provider answered from
one model on a grid about 8 km across. Five grid points serve the nine places.

**The rule is the engine's own**, `state.rain_index` and `state.apply_rain`, not a copy of them.

**The hours ahead are taken from the archive**, as if each forecast for the next two hours had been as good as
the record made afterwards. That flatters the rule.

**Hour by hour**, where the live system looks every 15 minutes. For India the provider makes its 15-minute
figures from its hourly ones, so nothing is lost by that.

## What it shows

- **The watch would not have opened for any of them.** None of the eleven reports that name the place, and
  none of the five that name the area. In four seasons the rule opened a watch on one day at most.
- **The rain it is fed is far too small.** On five of six occasions the model held between a twentieth and a
  quarter of what a gauge near the place recorded: 13 mm against 148, 6 against 117, 4 against 60, 23 against
  102. A storm that drops 100 mm on one neighbourhood in an evening is smaller than the model's grid.
- **No other model does better.** Each of seven models, asked for by name, caught none or one of the seven
  reports of 2025 and 2026. The highest of the seven in each hour caught one, with a watch standing on 10 days
  of a season.
- **A lower threshold catches them by watching often.** With the highest of seven, 10 mm caught six of seven
  with a watch on 41 days of a season, and 5 mm caught all seven with a watch on 86 days, a day in three.
  Those figures were read off the same seven reports they are judged on.

## What it means

- **The first step of the system does not work as built.** The arithmetic of the rule is sound and the rain
  is wrong for it. On this evidence the live rain check would have sat silent through the floods it exists to
  announce.
- **The 20 mm was never the question.** No threshold on this rain separates the reported days from the rest
  at a cost anyone would accept.
- **What would mend it is rain measured on the ground.** The figures these reports quote come from the
  state's automatic rain gauges, one of them at Maitrivanam itself. They are not connected to this system and
  their terms of use have not been looked at. Weather radar is the other thing that sees a storm of this size.
- **Without a watch nobody is asked for a photo.** The engine acts on a depth reading whether or not a watch
  is open, so the warnings after the first reading do not depend on the rain. The asking does.
- **Nothing after the watch was tested here.**

## What this is not

- **Not a count of false alarms.** No list of dry days exists to count them against.
- **Not every flood**, and not chosen at random: these are the days a reporter named the place.
- **Not rain from a gauge at the place.** Six gauge figures taken from the reports are set beside the model's.
- **Not the live system's own record.** It has run since 9 October 2026 and has not yet seen a storm.
- **Not a tuned threshold.** The table of other thresholds says what each would have cost on these reports. It
  is not a recommendation.
