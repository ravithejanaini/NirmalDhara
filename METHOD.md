# NirmalDhara: detailed method

"Clean flow": flood warning and drain-waste tracking from one camera network (Environmental Hacks, Heat and Water track).

The pitch has two halves, served by one camera network.

- **Public safety:** nobody enters floodwater they cannot cross. The system raises a **watch**
  from the rain forecast, gets a picture of that one place, reads the water depth, predicts
  when each vehicle type loses passage, and alerts the people who need to know (sections 2
  to 8).
- **Environment:** the same cameras track the waste and plastic that block drains, and send
  the responsible department live updates with the consequence of leaving it and the action
  that avoids it (section 16). The flood record also yields the drainage capacity each site
  lacks (sections 14 and 15).

Values marked **(assumption)** are starting points that must be checked or calibrated. They are
not verified facts. Section 17 lists where every threshold comes from and which are still
unverified.

---

## 1. Terms

| Term | Meaning |
|---|---|
| Site | One underpass or low point that is monitored |
| Reading | One depth estimate for a site at a time, with a confidence |
| Watch | Flooding is likely at a site; no picture has confirmed it yet |
| Warning | A picture has confirmed water at a depth that blocks at least one vehicle type |
| Guardian | A person who is normally at the site (shopkeeper, guard, pump attendant) and has agreed to send photos |

## 2. Site states

```
CLEAR -> WATCH -> WARNING -> CRITICAL -> RECEDING -> CLEAR
           |                                ^
           +------ (no water confirmed) ----+--> CLEAR
```

| State | Entered when | Leaves when |
|---|---|---|
| CLEAR | Default | Rain index crosses the site threshold |
| WATCH | Rain index >= site threshold | A reading confirms water (-> WARNING), or rain index stays below threshold for 60 min with no water confirmed (-> CLEAR) |
| WARNING | Smoothed depth >= band B2 | Depth reaches the car no-go band (-> CRITICAL) or slope turns negative for 3 readings (-> RECEDING) |
| CRITICAL | Smoothed depth >= car no-go band | Slope negative for 3 readings (-> RECEDING) |
| RECEDING | Depth falling | Depth back to B0/B1 for 2 readings (-> CLEAR), or depth rising again (-> WARNING or CRITICAL by depth) |

"Depth" in this table means the upper end of the smoothed depth range (section 6, C5). The car
no-go band is B3 (section 6, C4).

State changes are made by code from the rules above. The language model never changes state.

---

## 3. Stage 0: build the site registry (one-off, per city)

1. Pull candidate sites from OpenStreetMap with an Overpass query for road segments tagged
   `tunnel=yes` or `layer=-1` on `highway=*`, inside the city boundary.
2. Add known waterlogging points from news reports and traffic-police advisories by hand.
3. For each site store:

```json
{
  "site_id": "blr-0042",
  "name": "Example underpass",
  "lat": 12.97, "lon": 77.59,
  "max_depth_cm": 250,
  "rain_threshold_mm": 20,
  "flood_history_count": 6,
  "camera": {"type": "none | cctv", "snapshot_url": null},
  "reference_objects": [
    {"name": "wall gauge", "real_height_cm": 150, "px_top": [412, 220], "px_base": [412, 640]}
  ],
  "guardians": ["sub_017", "sub_044"],
  "authority_contacts": {"traffic": "…", "pump": "…"}
}
```

`reference_objects` is filled only for sites with a fixed view and a dry reference photo.

## 4. Stage A: watch trigger (no picture needed)

Runs every 15 minutes for every site (EventBridge schedule -> Lambda).

1. Fetch from the rain-forecast API for the site's coordinates:
   - `P_past1` = rain in the last hour (mm)
   - `P_past3` = rain in the last three hours (mm)
   - `P_next1` = forecast rain for the next hour (mm)
2. Compute the rain index:

   `R = P_past1 + 0.5 * (P_past3 - P_past1) + P_next1`

   The middle term gives half weight to older rain, which has partly drained.
3. If `R >= rain_threshold_mm` and the state is CLEAR, move to WATCH.

**Why the threshold does not need to be exact.** A watch sends photo requests to guardians and
nothing to the public (section 8). A false watch therefore costs a few unanswered requests,
while a missed watch costs the whole warning. So the threshold is set low on purpose.

**The default.** 20 mm is a design choice, not a measured value. No single figure exists for
Indian cities: Delhi's public works department is reported to estimate its 1976-era drains
cope with at most 50 mm of rain, and each underpass differs with its pumps and drains.

**Calibrating a site.** Take the dates it is known to have flooded, pull historical hourly rain
for those dates and for the rest of that monsoon, and choose the lowest threshold that catches
every known flood date. Report the false-watch count that threshold produces. If a site has no
history, use the lowest calibrated threshold in the city.

**Status.** Done for the first time on 11 October 2026 (`scripts/watch_history.py`,
`docs/watch-history.md`), and the answer is not a threshold. Sixteen dated news reports of water at
the nine places were set against four seasons of the provider's hourly rain, with this section's
rule replayed by the engine's own functions. A watch would have stood on none of the 11 days a
report names the place. The provider's rain comes from a weather model on a grid about 8 km
across, and on five of six occasions held a twentieth to a quarter of what a rain gauge near the
place recorded. Seven other models, and the highest of them hour by hour, did no better at 20 mm.
A threshold low enough to catch the reports keeps a watch standing on a day in three. The rule
needs rain measured on the ground: the state's automatic rain gauges, which these reports quote,
or weather radar. Neither is connected.

## 5. Stage B: getting the picture in time

Triggered when a site enters WATCH. Sources are tried in this order:

1. **Fixed camera**, if the site has one: fetch a snapshot every 2 minutes.
2. **Guardians**: send each guardian a message with a one-tap capture link.
3. **Nearby residents** who opted in and are within 500 m: same link.

**Capture link.** A web page (no app install) that:
- shows a safety notice: stand on dry, raised ground; never approach the water;
- shows a framing guide: "include a vehicle, a person, or the wall marking";
- takes two frames one second apart, so moving water can be flagged (section 6, C6);
- uploads straight to storage through a pre-signed URL that expires in 20 minutes;
- attaches the browser's GPS position and capture time.

**Acceptance checks on upload.** Reject the image if:
- its position is more than 150 m from the site;
- its capture time is more than 5 minutes old;
- its hash matches an image already received (duplicate or recycled photo).

**Re-ask cadence.** Every 10 minutes in WATCH, every 5 minutes in WARNING or CRITICAL. After 3
unanswered requests, stop asking that person for this event.

**If no picture arrives.** The site stays in WATCH. Alerts go out labelled "unconfirmed: based
on rain forecast only". The system never invents a depth.

## 6. Stage C: depth from a picture

### C1. Pre-checks
- Too dark or too blurred (variance-of-Laplacian below a cut-off) -> return `cannot_tell`.
- Blur faces and number plates before the image is stored.

### C2. Three estimators

**Estimator 1: reference object (fixed views only).**
For a vertical object of known height with stored pixel positions for its top and base:

```
scale_cm_per_px = real_height_cm / (px_base_y - px_top_y)
depth_cm        = (px_base_y - waterline_y) * scale_cm_per_px
```

`waterline_y` is the row where the water mask meets the object, taken from a water
segmentation of the frame. This is the most accurate estimator and is trusted first.

**Estimator 2: vehicle and person landmarks (any photo).**
1. Detect vehicles and people with an object detector.
2. For each vehicle, classify the water level against its landmarks. This classifier is trained
   on the public submerged-vehicle image set (five levels).
3. For each person, run pose estimation and find the lowest visible joint.
4. Convert the level to a depth range using the table below.

Wheel landmarks, derived from standard tyre sizes (see section 17):

| Water reaches | Car, wheel about 62 cm | Motorcycle, wheel about 61 cm | Scooter, wheel about 43 cm |
|---|---|---|---|
| Tyre sidewall only, rim dry | 0–12 cm | 0–9 cm | 0–9 cm |
| Rim, below one-third of the wheel | 12–20 cm | 9–20 cm | 9–14 cm |
| One-third of the wheel up to the axle | 20–31 cm | 20–31 cm | 14–22 cm |
| Axle up to the top of the tyre | 31–62 cm | 31–61 cm | 22–43 cm |
| Above the tyre | above 62 cm | above 61 cm | above 43 cm |

Auto-rickshaw wheels (tyre 4.00-8) are about 41 cm across, close to a scooter's, so autos use
the scooter column.

Body landmarks, from Indian adult measurements (men and women combined, 5th to 95th
percentile, heights from the floor):

| Landmark | Height | Water at this landmark means |
|---|---|---|
| Ankle bone | 5–7 cm | 5–7 cm |
| Middle of the kneecap | 41–52 cm | 41–52 cm |
| Crotch | 68–85 cm | 68–85 cm |
| Hip joint | 77–94 cm | 77–94 cm |
| Waist | 88–105 cm | 88–105 cm |

When the water is between two landmarks, the depth is measured, not guessed:
1. Pose estimation gives the knee and hip positions in the image.
2. The thigh (hip joint to kneecap) is about 39 cm in the median adult, which sets the scale
   in cm per pixel for that person.
3. Depth = knee height minus the visible length of shin, both in cm.

The system cannot tell an adult from a child. Treating everyone as an adult makes the
estimated depth equal to or deeper than the true depth for a shorter person, which errs on the
cautious side. Readings that rest only on a person are capped at confidence 0.6.

**Estimator 3: multimodal model (fallback).**
Send the image with a fixed instruction and require this JSON back:

```json
{
  "flood_present": true,
  "objects": [{"type": "car", "level": "top_of_tyre", "confidence": 0.7}],
  "depth_band": "B3",
  "confidence": 0.6,
  "reason": "Water reaches the top of the front tyre of the white car."
}
```

Used when estimators 1 and 2 return nothing, and as a cross-check when they do.

### C3. Depth bands

Band edges sit on the no-go depths in C4, so a band maps to one passability answer.

| Band | Depth | What it looks like on a car wheel |
|---|---|---|
| B0 | 0 cm | Dry road |
| B1 | under 12 cm | Sidewall wet, rim dry |
| B2 | 12–20 cm | Rim wet, under one-third of the wheel |
| B3 | 20–30 cm | One-third of the wheel, up to the axle |
| B4 | 30–50 cm | Axle covered |
| B5 | above 50 cm | Near or above the top of the tyre |

### C4. Passability table

| Who | No-go depth | No-go from band | Basis |
|---|---|---|---|
| Scooters and motorcycles | 15 cm | B2 | Scooter guidance: not above the axle, about 15–20 cm. Rider guidance for motorcycles also uses the front axle, about 30 cm on a 17-inch wheel, but no manufacturer publishes a figure, so one cautious limit covers all two-wheelers |
| Auto-rickshaws | 15 cm | B2 | Ground clearance is 170–200 mm and kerb weight as low as 398 kg, so the floor is reached just above this depth and the vehicle is easily moved |
| Hatchbacks and sedans | 20 cm | B3 | Wading depth usually 18–20 cm; stop if water is above the wheel hub centre |
| Pedestrians and cyclists | 30 cm | B4 | Flood-hazard guidance treats up to 30 cm of slow water as generally safe for people; open manholes make any deeper water unsafe |
| SUVs | 30 cm | B4 | Wading depth 30–60 cm depending on model; the low end is used |
| Buses and trucks | No answer given | n/a | No manufacturer wading figure is public. The system reports the depth to the operator and never says "passable" for these classes |
| Everyone | 50 cm | B5 | Flood-hazard guidance: above 50 cm is unsafe for vehicles. Small cars become buoyant at 30 cm, large passenger cars at 40 cm, large 4WDs at 50 cm |

**Why the Australian figures are not relaxed for India.** The tests behind them used a 1.05
tonne small car. Common Indian hatchbacks weigh 716–945 kg with 163–170 mm of ground clearance,
so they are lighter and no higher. The limits above are therefore kept or tightened, never
loosened.

**Moving water.** These depths are for still water, which is the usual case in an underpass
sag. In the same tests, water moving at 3.6 km/h shifted the 1.05 tonne car at 15 cm depth.
So when water is flagged as moving (C6), every class is "not safe" from band B2 (12 cm) up,
and every message says "do not enter moving water".

**How a reading becomes an answer.** A reading is a depth range, not a point.
- "Passable" for a vehicle class is given only when the **upper** end of the range is below
  that class's no-go depth **and** confidence is at least 0.6.
- If the range straddles the no-go depth, the answer is "not safe".
- If confidence is below 0.6 and the upper end is below the no-go depth, the answer is
  "unknown: treat as not safe".

### C5. Fusing estimates

Within one image:
1. Collect every object-level depth range from estimators 1 and 2.
2. The reading's range runs from the confidence-weighted median of the low ends to the
   **highest** high end among estimates with confidence of at least 0.4.
3. Confidence is the mean of the contributing confidences, halved if the estimates span more
   than two bands.
4. If estimator 3 disagrees by two or more bands, widen the range to include its band and mark
   the reading `low_confidence`.

Across time, per site:
1. Smoothed depth range = median of the low ends and median of the high ends of the last 3
   accepted readings.
2. A reading that jumps two or more bands within 2 minutes is held, not rejected: it triggers
   an immediate photo request, and is accepted if the next reading agrees.

Trust tiers decide what a single reading may do:

| Source | Tier | Alone, it can |
|---|---|---|
| Fixed camera with a reference object | Trusted | Move the site to any state |
| Guardian | Trusted | Move the site to any state |
| Resident, passes position and time checks | Unconfirmed | Warn the public and advise officials, marked "unconfirmed" |
| Two residents, different devices, within 10 minutes, bands within one of each other | Trusted | Move the site to any state |

So one anonymous photo is never ignored and never delays the public warning. What it cannot do
alone is produce a closure recommendation to officials.

### C6. Moving-water flag

The capture page takes two frames one second apart; a fixed camera supplies consecutive frames.
1. Compute dense optical flow between the two frames, inside the water mask only.
2. Subtract the median flow of the non-water area, which removes hand shake.
3. If the remaining flow is consistent in direction over more than 30% of the water area, set
   `moving = true`.

This is a yes/no flag, not a speed. Ripples from passing vehicles and rain on the surface will
cause false positives, which push the answer toward "not safe". The 30% cut-off is untested and
is tuned during evaluation. With a single still photo the flag is `unknown`, and the message
carries the moving-water caution without changing the answer.

### C7. Reading record

```json
{
  "site_id": "blr-0042",
  "ts": "2026-10-10T17:42:10+05:30",
  "source": "guardian | cctv | resident",
  "depth_cm_low": 30, "depth_cm_high": 45,
  "band": "B3",
  "moving": "true | false | unknown",
  "confidence": 0.72,
  "estimators": ["landmark", "vlm"],
  "image_key": "readings/blr-0042/….jpg"
}
```

### C8. Several reference objects, and several cameras

Added 10 October 2026. C2 takes one scale from one object's height, C5 joins object-level ranges by
a cautious rule, and C6 says only yes or no for moving water. Where a view has more to offer, three
things are done instead (`nirmaldhara/multiview.py`).

**Fixing the camera from every known dimension.** At enrolment, marks of known height (posts, gauge
boards, courses of a wall), length and width (a length of kerb, the width of a lane) are placed on
the dry view: six or more, not all in one plane. Heights alone cannot fix a camera and ground
distances alone cannot; together they fix where it is, which way it points and how it magnifies.
After that, where the water meets any upright thing at a known spot is a height, at any camera
angle. With fewer marks the mapping along one object is used: one scale from two marks, which is C2
as written, or the map that perspective obeys from three or more.

**Joining readings.** Each reference surface in a view, and each camera at a site, gives its own
range, weighted by its record. With three or more that agree, the range runs from the weighted
middle of the low ends to the weighted middle of the high ends, so one reading that is far out
cannot move it. With fewer, or with no agreement, the rule of C5 stands: the highest high end. Two
readings cannot outvote a wrong one, so the single figure from two is their weighted mean.

**The speed of the water.** Two cameras that both see something floating place it in space. Placed
twice, a known time apart, it gives the water's speed and direction and the height of the surface
it floats on. One camera can do the same only when the level is already known, and is wrong by as
much as that level is. This is a measurement in metres a second where C6 has yes or no. The
passability rule is unchanged: no speed threshold has a source in section 17.

**Existing cameras only.** Nothing here asks for a camera to be installed. It applies where two or
more cameras already see the same water, and no site in the registry has been checked for that.

**Status.** Joining was measured on a real flood (`docs/multi-reference-river.md`): four surfaces at
one river lock were 10 cm out, typically, against 13 cm for one, and there was no gain where the
surfaces were all one grass bank. Fixing the camera, and the speed, are tested on made scenes and
tried in a simulation (`docs/multiview-simulation.md`) only.

### C9. One level from every witness, through time

Added 10 October 2026. C8 joins readings once each is finished. Underneath, there is one water
level at a place at a moment, and every reference object in every camera is a witness to it
(`nirmaldhara/depthmodel.py`).

**What is learnt about a witness**, from moments at which the level was measured: the row it
reports at each level, as a curve that only goes one way; how far its reports lie from that curve,
within a day and between days, measured on days the curve did not see; the share of its reports
that are nowhere near; and how often, at each level, it reports a line, "dry", or neither. Where
its curve is flat the witness is blind: the water's edge is hidden, or has run off its strip.

**One level from many.** For each level, each witness's report has a likelihood, never smaller than
its wild rate allows. The likelihoods are multiplied. A blind witness then says nothing, a sharp one
outweighs a blunt one by as much as it is sharper, and a wild one is outvoted by degrees. Witnesses
in one camera share its light, so their evidence is counted at a share of face value: the share
under which days left out are predicted best. Each camera has its own.

**Through time.** What was believed is spread by as much as the level could have moved in the time
gone by, at a rate learnt from the measured levels, and multiplied by what the witnesses say now.
Only the past is used. A witness wrong at one hour is usually wrong the same way the next, so
through time its evidence is counted at a second, smaller share.

**What comes out.** A level, and a range stretched until it would have held nine in ten of the days
left out. `depthmodel.to_reading` gives the engine a depth range above the road and a confidence,
which is zero when the witnesses said nothing that tells levels apart.

**Two limits.** It cannot read past the levels it learnt from, and does not know when it is there.
And it learns from measured levels, which no site has.

**Status.** Measured on a real flood (`docs/depth-model-river.md`): at one river lock, seven surfaces
and the learnt gauge gave every picture a level, 11 to 12 cm out, typically, with one in ten more
than 41 to 47 cm out, against 13 cm and 54 cm for one surface. The strips' evidence was counted at
a twentieth to a fifth of face value. The chain from several cameras' frames to the engine's answer
has been run on rendered scenes only (`docs/site-simulation.md`).

## 7. Stage D: prediction

**Rise rate.** Fit a robust slope (Theil–Sen) to the last 3 to 6 smoothed readings:
`r` in cm per minute.

**Rain adjustment.** Scale by how the coming rain compares with the recent rain:

```
k     = clip(P_next60 / max(P_last60, 1 mm), 0.25, 3.0)
r_adj = r * k
```

**Forecast depth.** `d(t) = min(d_now + r_adj * t, max_depth_cm)` for t = 30 and 60 minutes.

**Time to no-go** for each vehicle class with threshold `D_v`:

```
t_v = (D_v - d_now) / r_adj      (only if r_adj > 0 and d_now < D_v)
```

Reported as a range using the low and high ends of the current depth range.

**With fewer than 3 readings** there is no slope. The output is then only "likely" or
"unlikely" from the rain index, with no minutes attached.

**Receding.** Declared from a negative slope over 3 readings. No clearing time is predicted,
because that depends on pumps and drains the system cannot see.

**A rise must stand clear of the readings' doubt.** Added 10 October 2026. Minutes are attached only
when the newest of the readings the slope was taken through has a range lying wholly above the
oldest's (`predict.clear_rise`). Otherwise the output is as with fewer than 3 readings: no minutes.
A rise smaller than the doubt in the readings may be no rise at all. This is a design choice. A
radar tracker weighs a target's speed against the radar's noise in the same way before it leans on
it; the designs this method shares with defence and with forecasting offices, and those tried and
not kept, are in `docs/borrowed-designs.md`.

**Status.** The slope was tried on real water for the first time on 10 October 2026: two river
cameras with measured levels, three days in a row left unseen, each forecast set against saying the
level would stay where it was (`docs/forecast-river.md`). From readings a camera can give, the slope
told the level ahead no better: a coin at one camera and worse at the other, with its largest
misses across a night a third to a half larger. From the measured levels themselves it was closer across
a night and no closer within a day. The guard did not pick the moments when the slope was right. It
keeps minutes off most slopes, and that is all it has been shown to do. A river read hourly over
days is not a street read every few minutes, and nothing here has been measured on a street.

## 8. Stage E: the agent

Built with the Strands Agents SDK. The agent is invoked on every state change and every new
accepted reading.

### Tools

| Tool | What it returns or does |
|---|---|
| `get_site(site_id)` | Registry record |
| `get_rain(site_id)` | Past and forecast rain |
| `get_readings(site_id, n)` | Last n readings |
| `predict(site_id)` | Forecast depth and time to no-go per vehicle class |
| `request_photos(site_id, audience)` | Sends capture links |
| `find_detours(site_id)` | Alternative routes avoiding the site, from a routing service |
| `notify(audience, channel, lang, message, evidence_url)` | Sends an alert |
| `log_decision(site_id, text)` | Writes the agent's reasoning to the audit log |

### Division of labour

- **Code decides**: state, alert level, who is eligible to be alerted, rate limits.
- **The agent decides**: which eligible audiences to alert now, what to ask for next, and how to
  word each message in the recipient's language.

### Alert rules (enforced in code)

| State | Residents nearby | Guardians | Traffic control | Pump operator | Fleet feed |
|---|---|---|---|---|---|
| WATCH | No | Photo request | No | No | No |
| WARNING | Yes, per vehicle type | Photo request | Advisory | Pump request | Yes |
| CRITICAL | Yes, "do not enter" | Photo request | Closure recommendation | Urgent | Yes |
| RECEDING | Update | Photo request | Update | Update | Yes |

- An unconfirmed reading at B3 or deeper sends residents "do not enter, unconfirmed" straight
  away, sends officials an advisory with the photo, and requests more photos every 2 minutes.
  The closure recommendation waits for a trusted source.
- At most one alert per audience per site every 20 minutes, unless the level rises.
- Every alert carries the depth band, the confidence, the time of the reading, and the image.
- The words "road closed" are never sent. The agent recommends; an officer confirms.

### Acknowledgement and escalation

Messages to officials include three links: **Acknowledge**, **Road closed**, **Pump started**.
- A click is written back to the site record and shown on the map.
- A CRITICAL alert with no acknowledgement after 5 minutes goes to the next contact in the list.

### Example messages

Resident on a two-wheeler:
> Water at Example underpass is about knee deep (photo 5:42 pm). Not safe for bikes or autos.
> Cars are likely to lose passage in 15–25 minutes. Use the flyover route instead.

Traffic control:
> CRITICAL: Example underpass. Depth 60–80 cm, rising about 2 cm a minute, confidence 0.7,
> confirmed by a guardian photo at 5:51 pm. Recommend closing both entries. [Acknowledge]
> [Road closed]

## 9. Data stores

| Table | Key | Holds |
|---|---|---|
| `Sites` | `site_id` | Registry record and current state |
| `Readings` | `site_id` + `ts` | Every accepted reading |
| `Events` | `site_id` + `start` | One row per flood event (section 14) |
| `Subscribers` | `sub_id` | Role, language, vehicle type, location, contact |
| `Alerts` | `site_id` + `ts` | What was sent, to whom, acknowledgement |
| `Decisions` | `site_id` + `ts` | Agent audit log |
| `Cameras` | `camera_id` | Owner, location, shared region, route, consent record, health (section 16) |
| `Activations` | `zone_id` + `start` | Emergency declarations: who declared, zone, expiry |
| `WasteObservations` | `camera_id` + `ts` | Inlet blockage, litter counts by class, vehicle count |
| `Scenarios` | `area_id` + `ts` | Scenario results and the ranked action list sent |

Images go to object storage under `raw/` (deleted after blurring) and `readings/`.

## 10. Interfaces

| Method and path | Purpose |
|---|---|
| `GET /sites` | Map data: every site with state, band and time of last reading |
| `GET /sites/{id}` | Detail, readings, forecast |
| `POST /sites/{id}/upload-url` | Pre-signed upload URL for the capture page |
| `POST /readings` (internal) | Called when an image lands; runs Stage C |
| `GET /passable?site={id}&vehicle={type}` | Yes / no / unknown, with the reason |
| `POST /ack/{alert_id}` | Acknowledgement from an official |
| `GET /feed/blocked` | Blocked sites for fleet routing |
| `GET /ranking?from=&to=` | Repeat offenders table for a period |
| `GET /sites/{id}/events` | Flood events for one site |
| `GET /sites/{id}/fix-sheet` | Capacity shortfall and required pumping or storage (section 15) |
| `POST /cameras` | Enrol a camera: owner, location, shared region, consent (section 16) |
| `DELETE /cameras/{id}` | Owner withdraws; the camera is disabled at once |
| `GET /cameras/{id}/activity` | Owner's view of when the camera was active and why |
| `POST /activations` | Authority declares an emergency for a zone, with expiry |
| `GET /waste/live?zone=` | Live blockage and litter per camera, over WebSocket |
| `GET /waste/actions?zone=` | Ranked actions with the scenario behind each |

## 11. How it is evaluated

| What | Measure | Data |
|---|---|---|
| Depth reading | Exact-band accuracy; within-one-band accuracy | Held-out split of the public image set |
| Depth reading on Indian streets | Same two measures | About 50 hand-labelled frames from Indian flood footage |
| Safety | **Critical-miss rate**: share of frames read as passable for cars when the true band is B3 or deeper | Both sets |
| Watch trigger | Known flood dates caught; false alarms per monsoon | Historical rain for 3 to 5 sites |
| Lead time | Minutes between the first warning and the car no-go band | Replayed clip sequences |
| Speed | Seconds from photo upload to alert sent | End-to-end test |

### The safety test in detail

**Definition.** A critical miss is a frame where the system answers "passable" for a vehicle
class and the true depth is at or above that class's no-go depth. "Not safe" and "unknown" are
never critical misses. It is counted separately for two-wheelers, cars and pedestrians.

**Target.** Zero critical misses on the test frames. A false warning costs a detour; a critical
miss can cost a life, so the two are not traded evenly.

**What zero means with a small test set.** With `n` frames at or above the no-go depth and zero
misses, the true miss rate is below about `3 / n` at 95% confidence. With 50 such frames that is
6%; reaching 2% needs 150. The writeup reports `n` and this bound, never "0% error".

**The price.** Also report the false-warning rate: frames answered "not safe" or "unknown" where
the true depth was passable. If it exceeds half of passable frames, the system is too cautious
to be useful and the confidence cut-off in C4 is tuned down, as long as critical misses stay
at zero.

**Tuning order.** First reach zero critical misses by widening ranges and raising the confidence
cut-off. Only then reduce false warnings.

## 12. Failure cases

| Case | Behaviour |
|---|---|
| No picture arrives | Stay in WATCH; alerts say "unconfirmed" |
| Night, glare, rain on the lens | `cannot_tell`; ask another source |
| No object of known size in frame | `cannot_tell`; the capture page asks for a retake |
| Two sources disagree by two bands | Use the deeper band for passability, mark low confidence, request another photo |
| Fake or old photo | Blocked by position, time and duplicate checks; CRITICAL needs a trusted source or two reports |
| Forecast API down | Use the last fetched forecast for up to 60 minutes, then mark the rain index stale |

## 13. Build order

1. Site registry for one city with 10 to 20 sites.
2. Stage C estimator 3 (multimodal fallback) end to end: image in, reading out.
3. Stage A watch trigger on the schedule.
4. Stage B capture page and upload checks.
5. Stage C estimator 2 (landmark classifier) and the evaluation in section 11.
6. Stage D prediction.
7. Stage E agent, alerts and acknowledgement links.
8. Map and control-room views.
9. Repeat offenders view (section 14), filled from replayed and backfilled events.
10. Fix sizing (section 15): volume curve, inflow, fix sheet and replay check.
11. Stage C estimator 1 on one fixed view (needed for fix sizing).
12. Camera network (section 16): agent on one PC, activation switch, frame pipeline.
13. Waste tracking and scenarios (section 16): blockage estimate, flood scenario, live console.

## 14. Repeat offenders view

The warning protects people during a flood. This view uses the same readings to show a city
which sites flood most, so the drains and pumps there get fixed first. It is the part of the
project that works on the flooding itself.

### Flood events

Readings are grouped into events, one row per flood at a site.

- **Start:** the first accepted reading whose upper depth is in band B2 or deeper.
- **End:** the site returns to CLEAR.
- **Written by code** when the event ends; nothing here uses the language model.

```json
{
  "site_id": "blr-0042",
  "event_id": "blr-0042-2026-10-10T17:20",
  "start": "2026-10-10T17:20:00+05:30",
  "end": "2026-10-10T20:05:00+05:30",
  "peak_depth_cm_low": 45, "peak_depth_cm_high": 60,
  "minutes_blocked_two_wheelers": 165,
  "minutes_blocked_cars": 120,
  "rain_index_at_start_mm": 24,
  "rain_total_mm": 61,
  "minutes_to_drain": 85,
  "moving_seen": false,
  "confirmed": true,
  "origin": "live | replay | backfilled_from_news",
  "pump_requested_at": "…", "pump_acknowledged_at": "…"
}
```

- `minutes_blocked_*` counts time the upper depth was at or above that class's no-go depth.
- `minutes_to_drain` runs from the rain index falling below the site threshold to CLEAR.
- `confirmed` is true only if a trusted source (section 6, C5) contributed a reading.

### Measures per site, over a chosen period

| Measure | Meaning | What it points to |
|---|---|---|
| Events | Number of confirmed flood events | How often the site fails |
| Hours blocked for cars | Sum of `minutes_blocked_cars` | The cost to the city |
| Typical peak depth | Median of the peak depth ranges | How dangerous it gets |
| Trigger rain | Lowest `rain_index_at_start_mm` across events | A low value means it floods in ordinary rain: undersized or blocked inlets |
| Drain time | Median `minutes_to_drain` | A high value means water cannot leave: blocked outlet or failed pump |
| Pump response | Median minutes from pump request to acknowledgement | An operations problem, not a drain problem |

### Ranking

Sites are sorted by **hours blocked for cars**, with the number of events as the tie-break.
The other measures are shown as columns, not blended into a score, so an engineer can see why
a site ranks where it does. No weights are invented.

Two plain flags are added once a site has at least 3 confirmed events:
- **Floods in light rain:** trigger rain is below the city median.
- **Slow to drain:** drain time is more than twice the city median.

### Guarding against a biased ranking

A site with a camera or active guardians produces more readings and will look worse than a
site nobody photographs. To keep that visible:
- each site shows **watches with no picture** next to its event count;
- a site where more than half its watches got no picture is marked "low coverage" and is
  listed separately, not ranked;
- unconfirmed events are counted in their own column and excluded from the ranking.

### What the user sees

- **Table:** rank, site, events, hours blocked, typical peak depth, trigger rain, drain time,
  flags, coverage.
- **Site page:** a timeline of events with the evidence photos, and depth against rain for
  each event.
- **Export:** CSV of the table, and a one-page site report. The agent writes the report's
  summary paragraph from the numbers above and may not add any figure that is not in the event
  records.

### For the hackathon

There will be no season of live data by Sunday. The view is filled from replayed footage and
from past flood dates found in news reports, and each event carries its `origin`, so the demo
shows clearly which rows are replayed or backfilled.

## 15. Fix sizing: the engineering specification that ends the flooding at a site

An underpass floods when water arrives faster than it can leave. The reported cures are all
capacity fixes: at Minto Bridge, upgraded pump motors, an automatic pump and an added drain;
a 2014 audit found Delhi's drains were designed for at most 25 mm of rain in an hour. This
section computes, from the system's own readings, how much capacity each site is short by.
It needs no one to respond and no new data.

### 15.1 Site geometry

The sag is described by its real road profile, not an idealised shape. The site registry gains:

```json
"geometry": {
  "width_m": 14,
  "profile": [[-60, 2.4], [-40, 1.5], [-20, 0.7], [0, 0.0], [20, 0.9], [40, 1.9]],
  "source": "survey | phone_level | map_estimate"
}
```

`profile` is a list of points along the road centreline: distance from the lowest point in
metres, and height above the lowest point in metres.

**Getting the profile**, in order of trust:
1. **Survey drawing** from the road agency, where one exists.
2. **Phone level walk.** In dry weather a guardian lays a phone flat on the road every 10 m
   along both ramps. The capture page reads the phone's tilt sensor at each stop. Slopes
   between stops are integrated into heights. About 10 stops per ramp.
3. **Map estimate**, used only until one of the above exists. Ramp slopes are assumed between
   2% and 6% (a secondary summary of the urban interchange code gives 4% as the desirable
   maximum and 6% as the absolute maximum; not checked against the code itself).

**Volume from depth.** For water depth `d`, the ponded length at any height `z` below the
surface is read off the profile, and:

```
V(d) = width_m * (area between the profile and the water line)      (cubic metres)
```

computed by the trapezium rule on the profile points. For two straight ramps of slopes `a`
and `b` this reduces to `0.5 * width_m * d^2 * (1/a + 1/b)`; with a = 0.04, b = 0.05 and
d = 0.5 m that is 78.75 m3.

**Checking the profile against the site itself: the drawdown test.** Pump stations routinely
measure pump output by timing how fast a known volume falls. The same test runs here on every
flood, for free:
- Use only readings from at least 30 minutes after the rain has stopped, with the pump
  recorded as running, so that inflow is near zero.
- Between two readings the pump removed `V(d1) - V(d2)` in the elapsed time. That gives the
  pump's real discharge.
- Geometry and pump rate cannot both be found from the same readings; one must be known.
  The measured profile supplies geometry, so the drawdown yields pump rate.
- **Consistency alarm:** a pump cannot deliver much more than its rated discharge. If the
  drawdown implies a rate above the rated figure by more than the uncertainty, the profile
  is wrong and the site is sent back for a phone level walk.

### 15.2 What each flood event reveals

From the depth readings of one event:

1. **Volume over time.** Convert each smoothed depth to `V(d)`.
2. **Net inflow.** `Q_net(t) = (V(t2) - V(t1)) / (t2 - t1)`.
3. **True inflow.** `Q_in(t) = Q_net(t) + Q_pump(t)`, where `Q_pump` is the rated pump
   discharge while the pump is recorded as running through the "Pump started" acknowledgement (section 8), else zero.
4. **Peak inflow.** The largest `Q_in` sustained over 10 minutes.
5. **Total inflow volume.** The sum of `Q_in` over the event.
6. **Effective catchment.** `A_eff = total inflow volume / rain depth during the event`.
   This is the area of ground whose runoff actually reaches the underpass. A value far larger
   than the underpass itself means water is arriving from surrounding streets whose drains
   are failing.
7. **Actual drain rate.** After the rain stops, `-Q_net` is the rate at which the site
   really empties. Comparing it with the rated pump discharge shows whether the pump is
   delivering what it should.

### 15.3 The fix sheet

Issued for a site once it has at least 3 confirmed events with 4 or more readings each, a
profile from a survey or phone level walk, and a reference gauge (15.4).

| Line | How it is computed |
|---|---|
| Design rain | The intensity for the return period the national storm water drainage manual sets for underpasses, read from the city's rainfall intensity curves. A secondary summary gives 25 to 50 years; the engineer confirms the figure from the manual |
| Design inflow | `A_eff * design rain` (the rational method, with the runoff coefficient already contained in `A_eff`) |
| Safe storage | `V(0.12 m)`: the volume the sag can hold before two-wheelers are blocked |
| Required pumping | The discharge that keeps volume at or below safe storage through the design storm |
| Present pumping | The measured drain rate from step 7 |
| Shortfall | Required pumping minus present pumping |
| Alternative: holding sump | The storage volume that absorbs the design storm with present pumping |
| Diagnosis | See below |

**Diagnosis without invented cut-offs.** Each test compares a measured interval with a
reference the site already has:
- **Pump underperforming:** the whole 80% interval of the measured drain rate lies below the
  pump's rated discharge less the tolerance on its test certificate. If no certificate
  tolerance is on record, the sheet prints measured against rated and makes no judgement.
- **Water arriving from outside:** the low end of the `A_eff` interval exceeds the mapped
  catchment, which is the area of the ramps and road that is meant to drain into the sag,
  measured from the map.

**The sheet as an engineer's input.** The sheet lists every input, formula and reading used,
so a drainage engineer can audit it line by line, and it has a sign-off field. It uses the
rational method, the same method the national manual prescribes, so its numbers can be checked
against a conventional design. It does not replace that design: choosing equipment, power
supply, outfall and structure remains the engineer's work.

### 15.4 Keeping the error small

Volume depends on depth squared, so depth error roughly doubles in volume. Three measures
contain it.

1. **Reference gauge required.** A fix sheet is issued only for sites read by estimator 1
   (section 6): a fixed view with marks painted on the wall every 10 cm. The target reading
   error is 3 cm, to be confirmed in evaluation; published work using known-size objects
   reports about 3 cm. At 50 cm depth that is 6% in depth and about 12% in volume, against
   about 40% from landmark readings. Painting a gauge on a repeat-offender site costs almost
   nothing.
2. **Fit the whole event.** A smooth curve that only rises during rain and only falls after
   it is fitted to all the readings of an event, and rates are taken from the curve, not from
   pairs of neighbouring readings. Independent errors then average out.
3. **Carry the uncertainty through.** The calculation is run 1,000 times with depth, profile
   heights and rated pump discharge each varied within their error. Every line of the sheet
   shows the median and the 80% interval, and **required pumping is taken from the upper end
   of its interval**, so the error works toward a safe size.

### 15.5 Checking the sizing against the record

The fix sheet is tested before it is shown:

1. Replay each past event with the required pumping applied.
2. The simulated depth must stay below 12 cm throughout every event at or below the design
   rain.
3. If it does not, required pumping is raised until it does.

This turns the sheet from an estimate into a statement that can be verified: "with this
capacity, none of the recorded floods at this site would have blocked a two-wheeler."

### 15.6 Proving it on a bench model

No real flood can be measured before Sunday, so the whole chain is tested on a scale model
where the true values are known.

**Build**
- A plastic trough with two ramps, its profile measured with a ruler.
- A ruler fixed to the side as the reference gauge, and a toy vehicle of measured wheel size.
- A flat tray of measured area draining into the trough, as the catchment.
- A small aquarium pump whose discharge is measured by timing it into a measuring jug.
- A phone on a stand, photographing at fixed intervals.

**Run**
1. Pour water over the tray at a rate measured with the jug and a timer. This is the true
   inflow, and the volume poured over the tray area is the true rain depth.
2. The system reads depth from the photos and computes volume, inflow, effective catchment
   and pump rate.
3. It issues the fix sheet for the model.
4. Apply the recommended pumping and repeat the same pour. The water must stay below the
   scaled threshold.

**Report**

| Quantity | Truth from | Reported |
|---|---|---|
| Depth | Ruler | Mean error in mm |
| Volume | Water poured in | Error in % |
| Inflow rate | Jug and timer | Error in % |
| Effective catchment | Tray area | Error in % |
| Pump discharge | Jug and timer | Error in % |
| Fix | Second run | Stayed below threshold: yes or no |

Step 4 is the important one: the recommendation is physically tested, not just calculated.

The model proves the vision and the arithmetic. It does not prove behaviour at a real site,
where drains, debris and inflow from surrounding streets add effects the model lacks. The
demo also shows the calculation on replayed footage of a real flood, marked as replayed.

### 15.7 What remains open

- Width is taken as constant along the sag. Kerbs and footpaths make this approximate.
- An event with fewer than 4 readings is not used.
- Recession readings assume inflow has stopped 30 minutes after rain ends. Slow drainage from
  a large catchment breaks this and makes the pump look weaker than it is.
- The return period for underpasses and the ramp gradient limits are from secondary summaries
  of the national manual and road code, and must be confirmed from the documents.

Sources: Tribune on Minto Bridge
(https://www.tribuneindia.com/news/delhi/no-waterlogging-at-minto-bridge-as-rain-lashes-capital/amp);
CAG audit of Delhi drainage, 2014
(https://www.indiaenvironmentportal.org.in/news-clippings/delhis-drainage-desilting-and-flood-control-a-big-fraud-cag);
drawdown pump test, Rural Community Assistance Partnership
(https://www.rcap.org/wastewater-maintenance-drawdown-pump-test/);
storm water manual return periods, secondary summary (https://infralens.in/cpheeo/cpheeo-sw-01);
interchange ramp gradients, secondary summary (https://infralens.in/code/IRC-92-2017).

## 16. Camera network and waste tracking

During a declared emergency, cameras that owners have enrolled (shops, offices, housing
societies, homes facing a street) send frames. The system tracks the waste and plastic that
block drains, and sends the responsible department live updates: what is there, what will
happen if it stays, and what to clear first. No new hardware is installed anywhere.

### 16.1 Why this is feasible

| Point | Evidence |
|---|---|
| Private cameras already feed government control rooms at scale | Hyderabad police report more than 16,000 police-owned cameras and over 50,000 community and privately contributed feeds. Under the "Nenu Saitham" programme, Cyberabad counts 1.37 lakh community cameras and Malkajgiri 2.58 lakh |
| The law has an emergency route | Digital Personal Data Protection Act, section 7(h): personal data may be processed "for taking measures to ensure safety of, or provide assistance or services to, any individual during any disaster, or any breakdown of public order" |
| Authorities can call on private resources | Disaster Management Act, section 65: a district authority may requisition "any resources with any authority or person" needed for prompt response |
| Waste is the documented cause of blocked drains | Bengaluru survey: solid waste, mainly plastic and cloth, at almost 90% of flood sites visited |
| Counting waste by camera is an established method | Jakarta river study: 68.7% precision, and about 35% more items found than by people counting |

The two legal points are the basis for an agreement with the district disaster authority.
They are not legal clearance, and this document is not legal advice. The design below relies
on owner consent first and treats the emergency provisions as the authority's backing.

### 16.2 Three ways a camera connects

| Route | How | Needs on site | Best for |
|---|---|---|---|
| A. Control room | One integration with the city control room that already receives community feeds; it forwards frames for the affected zone | Nothing | Scale |
| B. Recorder push | The owner's recorder sends a snapshot on a schedule, by email or file upload, to an address issued for that camera | A recorder with snapshot upload, which many have; model-dependent | Shops and homes with no computer |
| C. Agent | A small program on a PC already at the premises reads the camera's stream on the local network and uploads single frames | A PC that stays on | Commercial premises |

Rules common to all routes:
- **Outbound only.** The recorder or agent calls out to the cloud. Nothing is opened on the
  owner's network.
- **Frames, not video.** One frame every 30 to 60 seconds. Waste accumulates slowly, so this
  loses nothing, and it cuts bandwidth, cost and privacy exposure.
- **Shared region.** At enrolment the owner draws the part of the view to share: road and
  drain only. Route C crops before upload. Routes A and B crop on arrival, before storage.

### 16.3 Enrolment and consent

```json
{
  "camera_id": "cam-00412",
  "owner": {"name": "…", "contact": "…", "type": "shop | office | society | home"},
  "lat": 17.44, "lon": 78.38,
  "route": "control_room | recorder_push | agent",
  "shared_region": [[120, 300], [900, 300], [900, 700], [120, 700]],
  "inlets_in_view": ["in-7", "in-8"],
  "consent": {"given_at": "…", "scope": "declared emergencies only",
              "text_version": "v1", "withdrawn_at": null},
  "health": {"last_heartbeat": "…", "status": "dormant | active | offline"}
}
```

- Consent is standing, limited to declared emergencies, and recorded with the exact text shown.
- A home camera is accepted only if the shared region is a public street and excludes doors
  and windows. An operator checks the drawn region before the camera is approved.
- The owner can withdraw at any time; the camera is disabled at once.

### 16.4 Emergency activation

Cameras are **dormant by default**. A dormant camera sends a heartbeat and nothing else.

1. An authorised officer of the disaster authority declares an emergency for a zone, with an
   expiry time. The declaration is stored with the officer's identity.
2. Every enrolled camera in the zone is switched to active:
   - Route C: the desired state of each device in AWS IoT Core is set to `capture: on` with a
     frame interval. The agent picks this up within seconds.
   - Route B: frames are always arriving or not, depending on the recorder; frames received
     outside an active window are discarded unread.
   - Route A: the control room is asked for the zone's feeds for the window.
3. At expiry, or when the officer ends it, every camera returns to dormant. Expiry needs no
   action from anyone.
4. Each owner can see every activation of their camera: when, for how long, under which
   declaration.

### 16.5 The pipeline

```
camera
  -> route A / B / C
  -> S3  frames/{zone}/{camera_id}/{timestamp}.jpg      (cropped to the shared region)
  -> SQS queue
  -> Lambda  blur faces and number plates, then run the detectors
  -> DynamoDB  WasteObservations (one row per camera per frame)
  -> EventBridge  on a change in blockage, or every 5 minutes per area
  -> Step Functions  scenario engine (16.7)
  -> API Gateway WebSocket  live console for the department
  -> SNS  alerts to the named officers
```

| Concern | How it is handled |
|---|---|
| Device identity (route C) | Each agent has its own certificate in AWS IoT Core. It exchanges the certificate for temporary credentials that allow writing only to its own folder. No access keys are stored on the PC |
| Recorder push (route B) | Email is received by Amazon SES and written to S3; the address encodes the camera. Attachments up to 40 MB are accepted |
| Live video on request | Where an officer needs to look, the agent can stream to Kinesis Video Streams, which supports RTSP cameras. Off by default |
| Bursts | The queue absorbs them; inference scales with queue depth |
| Failures | A frame that fails three times goes to a dead-letter queue and is counted |
| Duplicates | The key camera + timestamp makes writes idempotent |
| Offline agent | It keeps the last 20 frames and sends them when the connection returns |
| Camera health | Heartbeat every 5 minutes. A camera silent for 15 minutes is marked offline; several going offline together in one area is reported as a likely power cut |
| Load control | The frame interval is set per camera from the cloud: shorter at inlets that are filling, longer elsewhere |
| Encryption | In transit by TLS; at rest with a managed key |
| Retention | Raw frames are deleted once processed. Frames behind an alert are kept up to 72 hours as evidence, then deleted. Counts and estimates are kept |
| Audit | Every declaration, activation, frame count and officer view is logged |

**Sizing.** 1,000 cameras at one frame a minute is 1.44 million frames a day. At an assumed
100 KB per frame that is about 144 GB a day, which is why raw frames are not kept.

### 16.6 What is tracked

For each frame, inside the shared region:

```json
{"camera_id": "cam-00412", "ts": "…",
 "inlets": [{"inlet_id": "in-7", "blocked_share": 0.6, "material": "plastic", "confidence": 0.7}],
 "litter": {"bottle": 9, "bag_film": 17, "foam": 4, "wrapper": 6, "other": 1},
 "mud_cover_share": 0.0,
 "vehicles_per_min": 22}
```

- **Blocked share:** the part of the visible grate covered by waste, from a segmentation of
  the grate area marked at enrolment.
- **Litter by class:** a detector trained on floating and street litter.
- **Build-up rate:** the slope of blocked share over the last 30 minutes, which gives the time
  until the inlet is fully blocked.
- **Mud cover and vehicle count:** inputs to the dust scenario.

### 16.7 The scenario engine

Each scenario answers three questions: what is there now, what happens if it stays, and what
action avoids it.

**Flooding (strongest).**
1. An inlet's flow capacity falls in proportion to its blocked share. Capacity at a given
   water depth comes from the standard weir and orifice equations for drain inlets.
2. The reduced capacity replaces the drain term in the mass balance of section 15, with the
   forecast rain as inflow.
3. The result is depth over time, with and without clearing each inlet.
4. Inlets are ranked by depth avoided if cleared.

> Inlets 7 and 8 at Example junction are 60% blocked. With the rain forecast for 6 pm, water
> reaches about 30 cm in 40 minutes, enough to stop cars. Cleared before 5 pm, it stays under
> 10 cm. Clear inlet 7 first.

**Dust (approximate).** After the water recedes, mud left on the road dries and is raised by
traffic. The mud cover share and the vehicle count go into the standard paved-road dust
emission formula to estimate road dust per day if the silt is not removed. Estimating the
quantity of mud from an image is rough, so this scenario is labelled approximate and gives a
range.

**Plastic into waterways.** Items counted moving into a drain per hour, by class, with the
total since the emergency began.

Every scenario carries its inputs, its confidence and the word "approximate" where it applies.
The language model writes the sentence; the numbers come from the calculation.

### 16.8 What the department sees

- **Live map:** every active camera, coloured by inlet blockage.
- **Action list:** ranked, each with the scenario behind it and the photo.
- **Acknowledge and done:** an officer marks an action taken; the next frames confirm it by a
  fall in blocked share, with no separate report needed.
- **After the emergency:** a summary of blockage, actions taken and not taken, and what
  followed.

### 16.9 Checks

| What | Measure |
|---|---|
| Blocked share | Mean error against hand-labelled frames of Indian drain inlets |
| Litter detector | Precision and recall on at least 100 labelled frames; the Jakarta study found accuracy fell at new sites and recovered with about 50 local examples |
| Flood scenario | Replay recorded events: predicted depth with the observed blockage against the depth that occurred |
| Latency | Seconds from frame captured to console updated |
| Activation | Time from declaration to first frame, and confirmation that nothing arrives after expiry |
| Privacy | Share of frames with a face or plate left unblurred, on a labelled sample |

### 16.10 Limits

- The department must still clear the waste. The system gives a precise, timed instruction
  and shows whether it was carried out.
- The inlet equations were checked against a published calculator that follows the US federal
  drainage manual: a grate in a dip passes `1.66 * P * d^1.5` as a weir and
  `0.67 * A * sqrt(2 g d)` as an orifice, in metric units, and the lower of the two governs.
  Blocked share reduces `P` and `A` in proportion. The manual itself was not read.
- The road-dust formula could not be checked: the source document could not be opened. The
  dust scenario is therefore unverified as well as approximate.
- Whether a given recorder can push snapshots depends on its model.
- Email receiving on AWS is offered in the Mumbai region (checked).
- Route A depends on an agreement with the city control room.
- Cameras fail in power cuts, which are common in floods. Coverage will thin exactly when it
  matters, and the console shows this.
- Night and heavy rain reduce what any camera can see.

### 16.11 For the hackathon

Built for real: the agent on one PC reading a camera or a recorded clip, certificate-based
identity, the activation switch with expiry, the frame pipeline, blocked share and litter
counts, the flood scenario, and the live console. Routes A and B are described and not built.
The dust scenario is shown as a calculation.

Sources: Hyderabad police press note, 27 November 2025
(https://www.hyderabadpolice.gov.in/assets/news/2025/11Nov/27112025.pdf);
Cyberabad re-verification of Nenu Saitham cameras
(https://www.thehindu.com/news/cities/Hyderabad/cyberabad-begins-re-verification-of-137-lakh-nenu-saitham-cctv-cameras/article71123016.ece);
Malkajgiri community cameras (https://hyderabadmail.com/malkajgiri-32000-cctv-cameras-nenu-saitham-2-0/);
DPDP Act section 7 (https://indiankanoon.org/doc/62814281/);
Disaster Management Act section 65 (https://indiankanoon.org/doc/181028/);
AWS IoT Core credential provider
(https://docs.aws.amazon.com/iot/latest/developerguide/authorizing-direct-aws.html);
Kinesis Video Streams with RTSP cameras
(https://docs.aws.amazon.com/kinesisvideostreams/latest/dg/examples-gstreamer-plugin.html);
Amazon SES delivery to S3 (https://docs.aws.amazon.com/ses/latest/dg/receiving-email-action-s3.html);
Bengaluru drain survey (https://wgbis.ces.iisc.ac.in/energy/paper/iconswm_urban_flooding/ufsw.pdf);
camera counting of river plastic
(https://theoceancleanup.com/scientific-publications/automated-river-plastic-monitoring-using-deep-learning-and-cameras/).

## 17. Where the thresholds come from

| Value | Source | Status |
|---|---|---|
| Car wheel about 62 cm | Tyre sizes 165/80 R14 (620 mm) and 185/65 R15 (622 mm) | Sourced |
| Car sidewall about 12 cm, axle about 31 cm | Same tyre sizes: sidewall 120–132 mm; axle is half the diameter | Derived |
| Motorcycle wheel about 61 cm, scooter about 43 cm | Calculated from tyre sizes 100/90-17 and 90/100-10; published figures for the neighbouring sizes agree (110/90-17 is 634 mm, 100/90-10 is 436 mm) | Derived and cross-checked |
| Auto-rickshaw wheel about 41 cm, ground clearance 170–200 mm, kerb weight from 398 kg | Bajaj RE specifications; wheel diameter calculated from tyre 4.00-8 | Sourced; diameter derived |
| Indian hatchbacks 716–945 kg, ground clearance 163–170 mm | Published specifications for Alto K10, WagonR, Swift, Tiago, i20 | Sourced |
| Small car moved at 15 cm, mid-sized at 30 cm, 4WD at 45 cm, in water at 3.6 km/h | UNSW Water Research Laboratory tests, as published by Victoria's emergency service | Sourced |
| Body landmark heights | Chakrabarti, Indian Anthropometric Dimensions (1997), tables read from the IIT Guwahati reference datasheet | Sourced; adults only, 1997 data |
| Hatchback and sedan wading depth 18–20 cm | Motoring guidance | Sourced, general guidance, not per model |
| SUV wading depth 30–60 cm | Motoring guidance; examples 300, 350 and 700 mm | Sourced |
| Scooter limit 15–20 cm | Motoring guidance | Sourced, single source |
| Cars buoyant at 30, 40, 50 cm by size | Australian Rainfall and Runoff vehicle-stability work | Sourced, Australian vehicles |
| Up to 30 cm generally safe for people; above 50 cm unsafe for vehicles | Australian Rainfall and Runoff hazard classes H1 to H3 | Sourced, Australian guidance |
| Motorcycle limit | Rider guidance only (front axle); no manufacturer figure exists publicly | Settled by rule: scooter limit applied |
| Bus and truck limits | No public manufacturer figure | Settled by rule: no "passable" answer is given |
| Moving-water cut-off (30% of water area) | None | Design choice, tuned in evaluation |
| 20 mm rain threshold | None | Design choice. Set against 11 dated flood reports on 11 October 2026: no watch on any of them, because the rain it is fed is far too small (`docs/watch-history.md`) |
| Minutes only for a rise clear of the readings' ranges | None | Design choice. Not confirmed by its one trial on real water (`docs/forecast-river.md`) |

Sources:
- Australian Rainfall and Runoff, people and vehicle stability: https://arr.ga.gov.au/__data/assets/pdf_file/0006/40488/ARR_People_and_Vehicles_stability.pdf
- UNSW Water Research Laboratory, vehicle stability testing for flood flows: https://www.unsw.edu.au/content/dam/pdfs/engineering/civil-environmental/water-research-laboratory/publications/WRL-TR2017-07-Vehicle-Stability-Testing-for-Flood-Flows.pdf
- The Quint, what to do if your car is stuck in floods: https://www.thequint.com/explainers/what-to-do-if-your-car-is-stuck-in-floods
- Motorist, how deep can your car wade through floodwater: https://www.motorist.my/article/6114/how-deep-can-your-car-wade-through-floodwater
- Scooter wading depth: https://us.ok.com/ask/what-is-the-wading-depth-of-a-scooter/
- IIT Guwahati ergonomics lab, Indian anthropometric reference datasheet: http://ergonomics-iitg.vlabs.ac.in/Reference%20Datasheet_static.html
- Victoria State Emergency Service, "15 to float": https://www.ses.vic.gov.au/media/campaigns/15-to-float
- Bajaj RE specifications: https://trucksbuses.com/3-wheeler/passenger/bajaj-re-cng/specifications
- Hatchback specifications (comparison page): https://www.cartrade.com/compare-cars/maruti-suzuki-swift-vs-maruti-suzuki-alto-k10-vs-maruti-suzuki-wagon-r/
- Adventure rider guidance on water crossings: https://www.adventurebikerider.com/article/water-crossings-motorcycle/
- Swarajya, Delhi drainage capacity: https://swarajyamag.com/amp/story/infrastructure%2Fdelhi-deluge-drainage-here-are-the-details
