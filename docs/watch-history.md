# The rain rule against the days these places were reported under water

**Real rain history and real reports.** Written by `scripts/watch_history.py` from `data/flood-reports.json`,
news reports found on 11 October 2026 that name one of the nine places or its neighbourhood as under water on a
stated day, and `data/rain-history.json.gz`, hourly rain at each place from Open-Meteo, the provider the live
system asks (CC BY 4.0). The engine's own rule is replayed over the rain hour by hour. This tests the first
step of the system, the watch, and nothing after it. It is not a measurement of depth.

"The provider's own choice" is the rain as the live system asks for it, with the provider picking the weather
model. "The highest of seven" takes that and six models asked for by name, and uses the largest of the seven in each
hour; all seven are held for 2024, 2025, 2026.
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
| Lakdikapul railway bridge | 19 Aug 2024 | Names the place. [Deccan Chronicle](https://deccanchronicle.com/southern-states/telangana/hyderabad-rain-wreaks-havoc-in-several-areas-1817640): Two hours of heavy rain on Monday afternoon; Lakdikapul is named among the places where water held up the roads. | **no watch**, index to 8 | **no watch**, index to 19 |
| Lakdikapul railway bridge | 21 Sep 2024 | Names the place. [Deccan Chronicle](https://deccanchronicle.com/southern-states/telangana/heavy-rains-bring-city-to-a-standstill-1825095): A storm on Saturday with knee-deep water reported elsewhere; traffic slowed to a crawl at Lakdikapul. | **no watch**, index to 4 | **no watch**, index to 16 |
| Lakdikapul railway bridge | 3 Apr 2025 | Names the place. [ETV Bharat](https://www.etvbharat.com/en/!state/heavy-rains-lash-hyderabad-bring-relief-from-heat-enn25040305708): A downpour from about two in the afternoon; Lakdikapul is listed among the flooded roads. | **no watch**, index to 7 | **no watch**, index to 13 |
| Lakdikapul railway bridge | 17 Jul 2025 | Names the place. [Siasat Daily](https://www.siasat.com/hyderabad-witnesses-heavy-rains-many-roads-waterlogged-3247404/): Heavy rain on Thursday; disaster teams worked on the flow of floodwater at Lakdikapul. | **no watch**, index to 5 | **no watch**, index to 8 |
| Lakdikapul railway bridge | 3 to 4 Aug 2025 | Names the place. [The News Minute](https://www.thenewsminute.com/telangana/heavy-rains-lash-hyderabad-roads-waterlogged-and-traffic-disrupted): By midday on Monday waterlogging had been reported at Lakdikapul among other places. | **no watch**, index to 3 | **no watch**, index to 9 |
| Lakdikapul railway bridge | 7 Aug 2025 | Names the place. [PTI, in The Week](https://www.theweek.in/wire-updates/national/2025/08/07/mes28-tl-rain.html): Heavy rain on Thursday evening; traffic crawled at Lakdikapul amid waterlogged roads. | **no watch**, index to 10 | **no watch**, index to 17 |
| Lakdikapul railway bridge | 22 Sep 2026 | Names the place. [The Hans India](https://www.thehansindia.com/news/cities/hyderabad/heavy-rains-trigger-traffic-snarls-across-hyderabad-1124724): Heavy rain in the evening rush hour; traffic jammed at Lakdikapul. | **no watch**, index to 0 | **no watch**, index to 5 |
| Khairatabad junction | 2 Aug 2022 | Names the place. [The News Minute](https://www.thenewsminute.com/article/heavy-rains-lash-hyderabad-roads-waterlogged-traffic-disrupted-166417): A downpour from eight in the morning; water standing on the roads held up traffic at Khairatabad. | **no watch**, index to 5 | seven not held |
| Khairatabad junction | 14 Jul 2024 | Names the area only. [South First](https://thesouthfirst.com/telangana/heavy-rains-lash-hyderabad-waterlogging-in-various-localities): 74 mm recorded at Khairatabad between 08:30 and 20:00; waterlogging at several places that are not named. | **no watch**, index to 6 | **no watch**, index to 14 |
| Khairatabad junction | 19 Aug 2024 | Names the place. [Deccan Chronicle](https://deccanchronicle.com/southern-states/telangana/hyderabad-rain-wreaks-havoc-in-several-areas-1817640): Two hours of heavy rain on Monday afternoon; Khairatabad is named among the places where water held up the roads. | **no watch**, index to 8 | **no watch**, index to 19 |
| Khairatabad junction | 3 Apr 2025 | Names the place. [ETV Bharat](https://www.etvbharat.com/en/!state/heavy-rains-lash-hyderabad-bring-relief-from-heat-enn25040305708): The main road at Khairatabad was flooded and traffic was turned away towards Panjagutta. | **no watch**, index to 7 | **no watch**, index to 13 |
| Khairatabad junction | 7 Aug 2025 | Names the area only. [Deccan Chronicle](https://deccanchronicle.com/southern-states/telangana/cloudburst-like-rain-alert-issued-for-hyderabad-1896141): Three rain gauges at Khairatabad recorded over 100 mm. Water on the road there is not stated. | **no watch**, index to 10 | **no watch**, index to 17 |
| Khairatabad junction | 3 Aug 2026 | Names the place. [Telangana Today](https://telanganatoday.com/hyderabad-roads-waterlogged-after-heavy-afternoon-downpour): Khairatabad is named among the inundated places; traffic slowed near its Metro station. | **no watch**, index to 3 | **no watch**, index to 11 |
| Khairatabad junction | 22 Sep 2026 | Names the place. [The Hans India](https://www.thehansindia.com/news/cities/hyderabad/heavy-rains-trigger-traffic-snarls-across-hyderabad-1124724): Heavy rain in the evening rush hour; traffic jammed at Khairatabad. | **no watch**, index to 0 | **no watch**, index to 5 |
| Maitrivanam, Ameerpet | 7 Aug 2025 | Names the area only. [Deccan Chronicle](https://deccanchronicle.com/southern-states/telangana/cloudburst-like-rain-alert-issued-for-hyderabad-1896141): 101.5 mm recorded at Maitrivanam; police alerts for waterlogged roads in Ameerpet. Three days later the road at Maitrivanam was said to have been under water several times that month. | **no watch**, index to 11 | **no watch**, index to 17 |
| Maitrivanam, Ameerpet | 9 to 10 Aug 2025 | Names the area only. [South First](https://thesouthfirst.com/telangana/telangana-cm-revanth-inspects-flood-hit-hyderabad-directs-relief-measures/): Torrential rain on Saturday night flooded parts of Ameerpet; the Chief Minister went to Maitrivanam the next day. | **no watch**, index to 9 | **no watch**, index to 15 |
| Maitrivanam, Ameerpet | 19 Sep 2025 | Names the place. [Deccan Chronicle](https://deccanchronicle.com/southern-states/telangana/heavy-rain-floods-hyderabad-causes-traffic-chaos-1904811): The main road at Maitrivanam was under water on Friday evening and people waded through it. | **no watch**, index to 11 | **no watch**, index to 13 |
| Al Jubail Colony, Falaknuma | 13 to 14 Oct 2020 | Names the place. [The Caravan](https://caravanmagazine.in/photo-essay/hyderabad-struggles-in-aftermath-of-rains-floods): On the first day of the October 2020 floods the water in Al Jubail Colony was reported at over four feet. | **no watch**, index to 19 | seven not held |
| Al Jubail Colony, Falaknuma | 14 to 15 Jul 2021 | Names the place. [Gulf News](https://gulfnews.com/world/asia/india/heavy-rains-bring-indian-city-of-hyderabad-to-its-knees--again-1.80701789): After a night of very heavy rain Al Jubail was among the colonies hit hard, as it had been in October 2020. | **no watch**, index to 1 | seven not held |

## How many were caught

| Reports | Rain | A watch stood on the day |
|---|---|---|
| That name the place | The provider's own choice | 0 of 20 |
| That name the area only | The provider's own choice | 0 of 7 |
| That name the place, 2024, 2025, 2026 | The highest of seven models | 1 of 14 |
| That name the area only, 2024, 2025, 2026 | The highest of seven models | 0 of 5 |

With nothing forecast for the hours ahead, the rule counting only rain already fallen: 0 of 20 with the provider's own choice, 1 of 14 with the highest of seven.

One more report gives no day. [The News Minute](https://www.thenewsminute.com/article/rainfall-choking-hyderabads-it-corridor-police-suggest-alternative-routes-104141): A police advisory published in the small hours of 24 June 2019 names all four as places that waterlog, 'with the onset of monsoon'. It gives no day. The three days before it are taken here, and counted apart from the dated reports.

| Place | The provider's own choice |
|---|---|
| Raheja Mindspace entrance underpass | **no watch**, index to 6 |
| Near Shilparamam, Madhapur | **no watch**, index to 6 |
| Nectar Gardens, Madhapur | **no watch**, index to 6 |
| Cyber Towers junction | **no watch**, index to 6 |

## Model by model, 2024, 2025, 2026

The reports of those years, and the days from 1 March to 31 October with a watch standing, for one place on average.

| Rain from | Caught, of those that name the place | Caught, of those that name the area | Watch days a season |
|---|---|---|---|
| The provider's own choice | 0 of 14 | 0 of 5 | 1 |
| ECMWF IFS | 0 of 14 | 0 of 5 | 1 |
| NOAA GFS | 0 of 14 | 0 of 5 | 3 |
| DWD ICON | 1 of 14 | 0 of 5 | 1 |
| Canadian GEM | 1 of 14 | 0 of 5 | 4 |
| JMA | 0 of 14 | 0 of 5 | 0 |
| UK Met Office | 0 of 14 | 0 of 5 | 5 |
| **The highest of the seven, hour by hour** | 1 of 14 | 0 of 5 | 13 |

## What the rule costs, year by year

| Year | Rain | Days of history | Watches opened at one place | Days with a watch standing |
|---|---|---|---|---|
| 2019 | The provider's own choice | 245 | 0 | 0 |
| 2020 | The provider's own choice | 245 | 1 | 1 |
| 2021 | The provider's own choice | 245 | 1 | 1 |
| 2022 | The provider's own choice | 245 | 1 | 1 |
| 2024 | The provider's own choice | 245 | 3 | 3 |
| 2024 | The highest of seven | 245 | 15 | 18 |
| 2025 | The provider's own choice | 245 | 0 | 0 |
| 2025 | The highest of seven | 245 | 16 | 18 |
| 2026 | The provider's own choice | 223 | 0 | 0 |
| 2026 | The highest of seven | 223 | 3 | 3 |

## Other thresholds

The reports that name the place, and the days in a season with a watch standing at one place, on average.

| Threshold | Caught, the provider's own choice | Watch days a season | Caught, the highest of seven | Watch days a season |
|---|---|---|---|---|
| 5 mm | 9 of 20 | 32 | 14 of 14 | 100 |
| 10 mm | 3 of 20 | 7 | 9 of 14 | 51 |
| 15 mm | 1 of 20 | 2 | 5 of 14 | 24 |
| **20 mm** | 0 of 20 | 1 | 1 of 14 | 13 |
| 30 mm | 0 of 20 | 0 | 0 of 14 | 6 |
| 40 mm | 0 of 20 | 0 | 0 of 14 | 3 |
| 50 mm | 0 of 20 | 0 | 0 of 14 | 2 |

## What the rain history holds

The provider's own choice, at one forecast cell on average. A watch needs an index of 20 mm, which one hour of 20 mm gives by itself.

| Year | Days | Rain in all | Hours with rain | Hours of 10 mm or more | The wettest hour at any of the cells |
|---|---|---|---|---|---|
| 2019 | 245 | 813 mm | 1443 | 0 | 12.1 mm |
| 2020 | 245 | 1073 mm | 1447 | 3 | 18.7 mm |
| 2021 | 245 | 778 mm | 1213 | 1 | 14.8 mm |
| 2022 | 245 | 891 mm | 1232 | 2 | 15.0 mm |
| 2024 | 245 | 1312 mm | 1541 | 6 | 17.3 mm |
| 2025 | 245 | 862 mm | 1341 | 2 | 14.7 mm |
| 2026 | 223 | 407 mm | 935 | 0 | 7.5 mm |

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
| Khairatabad junction | 14 Jul 2024 | [Khairatabad, 08:30 to 20:00](https://thesouthfirst.com/telangana/heavy-rains-lash-hyderabad-waterlogging-in-various-localities): 74 mm | 18 mm | 30 mm |

## How to read this

**The reports are what two rounds of searching found.** Twenty-seven dated reports, twenty of which name the place itself.
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

- **The watch would not have opened for any of them.** None of the twenty reports that name the place, and
  none of the seven that name the area. In seven seasons the rule opened a watch on three days of a season at
  most, and in most seasons on one or none.
- **The rain it is fed is far too small.** On six of seven occasions the model held between a twentieth and a
  quarter of what a gauge near the place recorded: 13 mm against 148, 6 against 117, 4 against 60, 23 against
  102, 18 against 74. A storm that drops 100 mm on one neighbourhood in an evening is smaller than the
  model's grid.
- **The model rains often and never hard.** A season's rain adds up to 780 to 1310 mm in the six full seasons,
  spread over 1200 to 1500 hours. In seven seasons no hour at any of these places held 20 mm: the wettest
  held 18.7 mm. A cloudburst that a gauge records as 100 mm in an evening arrives in the model as a long
  light rain.
- **No other model does better.** The provider's own choice and six models asked for by name each caught none
  or one of the fourteen reports of 2024 to 2026. The highest of the seven in each hour caught one, with a
  watch standing on 13 days of a season.
- **A lower threshold catches them by watching often.** With the highest of seven, 10 mm caught nine of
  fourteen with a watch on 51 days of a season, and 5 mm caught all fourteen with a watch on 100 days, two
  days in five. Those figures were read off the same fourteen reports they are judged on.

## What it means

- **The first step of the system does not work as built.** On this evidence the live rain check would have
  sat silent through the floods it exists to announce. Whether the rule itself is right cannot be told: the
  rain it is fed is too far short for any rule to work on.
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
- **Not rain from a gauge at the place.** Seven gauge figures taken from the reports are set beside the model's.
- **Not the live system's own record.** It has run since 9 October 2026 and has not yet seen a storm.
- **Not a tuned threshold.** The table of other thresholds says what each would have cost on these reports. It
  is not a recommendation.
