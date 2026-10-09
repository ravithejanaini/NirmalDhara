# Credits

## Map

| What | From | Licence and terms |
|---|---|---|
| Map data | [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors | Open Database License (ODbL) |
| Vector tile schema | [OpenMapTiles](https://openmaptiles.org/) | CC BY 4.0 for the schema |
| Tile and font hosting | [OpenFreeMap](https://openfreemap.org/) public instance | Free, including commercial use. No key, no registration, no request limit. Attribution required |
| Map library | [MapLibre GL JS](https://maplibre.org/) 4.7.1, loaded from unpkg | BSD 3-Clause |

**Decision, 9 October 2026.** The task allowed vector tiles only if the provider's own page
states that no key is needed and public use is allowed. https://openfreemap.org/ states: "no
limits on the number of map views or requests", "no registration, no user database, no API
keys, and no cookies", commercial usage allowed, attribution required. So tiles are used and
the hand-drawn SVG fallback was not built.

**Attribution.** MapLibre shows it on the map. In print or video it must be shown as:

> OpenFreeMap © OpenMapTiles Data from OpenStreetMap

The demo video must carry this line on any shot that shows the map.

**No service guarantee.** OpenFreeMap offers no uptime commitment. If its public instance is
unreachable the page shows an error and no map. A production deployment should self-host the
tiles for the city, which the project's licence allows.

## Rain forecast

| What | From | Licence and terms |
|---|---|---|
| Hourly rain forecast at each site, read every 15 minutes | [Open-Meteo](https://open-meteo.com/) forecast API (`src/nirmaldhara/rain.py`) | Data under CC BY 4.0, attribution required. The free API needs no key and is offered for non-commercial use |

Weather data by Open-Meteo.com. A deployment that is commercial, or that a city relies on, needs
Open-Meteo's paid plan or the weather service's own feed.

## Type

Fraunces and Inter, both under the SIL Open Font License, loaded from Google Fonts.
