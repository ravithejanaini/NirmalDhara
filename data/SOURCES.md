# Sources for the site registry

`hyderabad_sites.json` lists nine places that published reports name as flooding. Each has the
link, the date and who said it. Nothing here was measured by this project.

## What is and is not established

- **Established:** a named public body or news report said each place waterlogs.
- **Not established:** how deep, how often, or whether it still does. The reports are from 2019
  to 2025. The pre-monsoon meeting of 29 May 2026 counted 523 waterlogging points in the city
  corporation area ([Siasat](https://www.siasat.com/officials-to-tackle-523-waterlogging-points-within-ghmc-ahead-of-monsoon-3479402/)),
  but the list itself is not public in any article found, so these nine are a small sample of
  a much larger set.
- **Not included:** places a source mentions only as an area (Toli Chowki, Karwan, Madhapur's
  100 Feet Road, Mehdipatnam, Masab Tank) because one position cannot stand for them; and IIIT
  Junction and Biodiversity Junction, named by [Telangana Today](https://telanganatoday.com/heavy-monsoon-rains-nearly-1000-waterlogging-hotspots-trouble-hyderabad-commuters)
  (8 Aug 2026), because OpenStreetMap's search finds only a campus and a park centre
  hundreds of metres away.

## Positions are approximate

Positions come from OpenStreetMap's search (Nominatim, a rate-limited public service used once
per name, 9 October 2026). Data © OpenStreetMap contributors, ODbL.

| Site | Precision |
|---|---|
| hyd-001 Lingampally railway underpasses | The station, close to the underpasses |
| hyd-002 Raheja Mindspace entrance underpass | A building inside the campus; the underpass is on its road |
| hyd-003 Near Shilparamam | Park centre; the flooding is on the road beside it |
| hyd-004 Nectar Gardens | Locality |
| hyd-005 Cyber Towers junction | The junction |
| hyd-006 Lakdikapul railway bridge | Within a few hundred metres |
| hyd-007 Khairatabad junction | The flyover |
| hyd-008 Maitrivanam | The junction |
| hyd-009 Al Jubail Colony | Neighbourhood centre |

**Why this matters.** The position does three jobs. For rain, a site's forecast cell is about
5 km, so none of this matters. For the map, a pin a few hundred metres off is harmless. For
photos, `intake.check` rejects a photo taken more than 150 m from the site, so **a site whose
position is hundreds of metres off will wrongly reject real photos.** Before real photo upload
goes live, correct each position to the exact road point, for example by dropping a pin on the
spot in OpenStreetMap or a phone's map. For the replay demo this does not matter.

## Reports used

| Report | Date | Used for |
|---|---|---|
| [South First: persistent railway underpass flooding at Lingampally](https://thesouthfirst.com/telangana/hyderabad-persistent-railway-underpass-flooding-plagues-serilingampally-ngt-summons-ghmc) | 23 Sep 2023 | hyd-001 |
| [The News Minute: Cyberabad Traffic Police advisory for the IT corridor](https://www.thenewsminute.com/article/rainfall-choking-hyderabads-it-corridor-police-suggest-alternative-routes-104141) | 24 Jun 2019 | hyd-002 to hyd-005 |
| [Deccan Chronicle: GHMC to solve waterlogging on roads](https://deccanchronicle.com/southern-states/telangana/ghmc-to-solve-waterlogging-on-roads-1831553) | 19 Oct 2024 | hyd-006 |
| [Siasat: list of waterlogging-prone areas in Hyderabad](https://www.siasat.com/list-of-waterlogging-prone-areas-during-rains-in-hyderabad-3257411/) | page modified 11 Aug 2025; first publication date not shown | hyd-007 to hyd-009 |

The News Minute also carries GHMC's 2019 list of 123 points, but publishes it as images, so no
place could be taken from it.

## Rain threshold

Every site uses the default of 20 mm rain index, a design choice in METHOD.md, not a measured
value for any site.
