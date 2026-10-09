# NirmalDhara: low-level design

[ARCHITECTURE.md](ARCHITECTURE.md) is the high-level design: components, events, flows and
who owns which state. This document is the level below it: the modules, the data structures
each one uses and why, the algorithms with their cost, and the properties the tests enforce.

Status column: **built** means the code exists with tests; **planned** means designed here and
not yet written.

---

## 1. From high-level design to modules

| Component in ARCHITECTURE.md | Module | Status |
|---|---|---|
| Rain Lambda (6.1) | `nirmaldhara/rain.py`, `handlers/rain.py` | built |
| State engine (6.2) | `nirmaldhara/state.py`, `nirmaldhara/store.py`, `handlers/engine.py` | built |
| Depth bands and passability | `nirmaldhara/bands.py` | built |
| Vision, fallback estimator | `nirmaldhara/reader.py` | built; not yet run against the real model |
| Intake checks, crop, blur | `nirmaldhara/intake.py` | built; detection-service call planned |
| Signed links (8) | `nirmaldhara/tokens.py` | built |
| Alert rules and templates (6.4, 6.9) | `nirmaldhara/alerts.py` | built |
| Prediction (METHOD 7) | `nirmaldhara/predict.py` | built |
| Camera agent change gate (6.6) | `nirmaldhara/change.py` | built |
| Nearby lookups | `nirmaldhara/geo.py` | built |
| Public map file (6.8) | `nirmaldhara/publish.py` | built |
| Volume curve for fix sizing (METHOD 15) | `nirmaldhara/volume.py` | built |
| Flood event workflow (6.3) | state machine definition, step handlers | planned |
| Notifier (6.9) | channel adapters | planned |
| Scenario engine (6.7) | inlet capacity, action ranking | planned |
| Fix sheet (METHOD 15) | inflow, uncertainty runs, pump search | planned |
| Camera agent and activation (6.5) | agent process, control topics | planned |

Rule for every module in `nirmaldhara/`: no network or cloud calls except in `reader.py` and
`rain.fetch`. Everything else is a pure function of its inputs, which is what lets 79 tests
run in a few seconds with no AWS account.

---

## 2. Core records

### 2.1 `Reading` and `Site` (state.py)

Both are frozen dataclasses: a value that never changes after it is made.

```
Reading(ts, low, high, confidence, source, device)

Site(site_id, rain_threshold_mm, state, version,
     readings,        # tuple of Reading, newest last, at most 12
     held,            # Reading | None: a sudden jump waiting for confirmation
     low, high,       # smoothed depth range, cm
     trusted,         # a trusted source vouches for the current depth
     water_seen, rain_low_since,
     events)          # facts produced by the last transition; not stored
```

**Why immutable.** `apply_rain(site, ...)` and `apply_reading(site, ...)` return a new `Site`.
The caller holds both the before and after values, which is exactly what the version check in
`store.save` needs, and a failed write leaves nothing half-changed.

**Why a bounded tuple for readings.** Only the last three are smoothed, the last four decide
"falling", and trust looks back ten minutes. Twelve covers all three with room to spare, keeps
the stored record a fixed small size, and makes every per-reading operation constant time.

### 2.2 Stored form (store.py)

One DynamoDB item per site. The engine writes three attributes: `doc` (the whole `Site` as
JSON), `state` and `version`. Registry attributes on the same item (name, position, contacts)
are never touched by the engine.

`doc` is JSON, not native attributes, because DynamoDB returns numbers as decimals; one string
avoids a conversion at every field.

---

## 3. Data structures, and why each was chosen

| # | Need | Structure | Cost | Where |
|---|---|---|---|---|
| 3.1 | Process one site's messages in order, one at a time | Per-key ordered log: a FIFO queue with the site id as the message group | Order guaranteed by the queue | `template.yaml`, `handlers/engine.py` |
| 3.2 | Stop two writers overwriting each other | Version number with compare-and-set on write | One conditional write | `store.save` |
| 3.3 | Recent readings | Bounded tuple, 12 | O(1) per reading | `state.py` |
| 3.4 | Camera noise level | Sliding window: `deque(maxlen=60)` | O(1) append; lower quartile over 60 values per frame | `change.py` |
| 3.5 | Frame comparison | 32 x 32 grid of floats with the mean removed | 1,024 subtractions per frame | `change.signature` |
| 3.6 | "Who is within 500 m of this site?" | Geohash cell per subscriber, indexed; query the few cells a circle touches, then filter exactly | At most 9 cell lookups plus the matches, instead of scanning every subscriber | `geo.py` |
| 3.7 | Rain for hundreds of sites | Hash map from forecast grid cell to the sites in it | One forecast point per cell | `rain.grid_cells` |
| 3.8 | Depth to stored volume and back | Sorted breakpoint heights with running-total volumes; binary search then a closed-form step | O(n^2) to build for n profile points, O(log n) per lookup | `volume.VolumeCurve` |
| 3.9 | Last alert per audience | Hash map: audience -> (level, time) | O(1) | `alerts.due` |
| 3.10 | "Have we seen this photo?" | Set of SHA-256 digests, held as items with a time-to-live | O(1) | `intake.check`, Tokens table |
| 3.11 | Tamper-proof links | Claims plus an HMAC-SHA256 signature, compared in constant time | O(length) | `tokens.py` |
| 3.12 | Public map | Array of fixed-order rows with a single header naming the columns | See 6.2 | `publish.py` |
| 3.13 | Top actions for an area | Heap of size k over candidate actions | O(n log k) | planned, scenario engine |
| 3.14 | Which inlets serve which site | Adjacency map: site -> inlets, inlet -> cameras | O(1) per hop | planned, registry |

### 3.6 in detail: the nearby lookup

A geohash turns a position into a short string naming a rectangle. At six characters a cell is
about 1.2 km by 0.6 km.

- **Write:** each subscriber and camera is stored with its cell as an indexed attribute.
- **Read:** `cells_covering(lat, lon, 500)` steps across the circle's bounding box one cell at
  a time and returns every cell it touches; for 500 m that is at most 9. Each cell is one
  index query. `within(...)` then applies the exact distance.
- **Tested:** 2,000 random points around Hyderabad; every point inside the radius falls in a
  returned cell.

### 3.8 in detail: the volume curve

The ponded length at water height `z` is a piecewise-linear function of `z`, with a corner at
every height that appears in the profile. Volume is its integral, so it is piecewise
quadratic.

- **Build:** sort the distinct heights; compute the ponded length at each; accumulate volume
  between consecutive heights by the trapezium rule, which is exact for a linear length.
- **`volume(d)`:** binary search for the interval containing `d`, add the exact quadratic
  remainder.
- **`depth(v)`:** binary search on the running totals, then solve the quadratic. This inverse
  is what the replay check needs: it turns "volume after pumping" back into a depth.
- **Tested:** equals the closed form for a V-shaped dip (78.75 m3 at 0.5 m); `depth(volume(d))`
  returns `d`; volume never falls as depth rises; a flat bottom holds water from the first
  centimetre.

---

## 4. Algorithms

`n` is the number of readings considered, never more than 12.

| Algorithm | Method | Cost | Why this method |
|---|---|---|---|
| Rain index | Weighted sum of three hourly values | O(1) | METHOD 4 |
| Fusing one photo's estimates | Confidence-weighted median of low ends; highest credible high end | O(k log k), k objects | A median ignores one wild estimate; the highest credible top keeps the answer cautious |
| Smoothing | Median of the last 3 lows and of the last 3 highs | O(1) | One bad reading cannot move the state |
| Trust | Scan earlier readings for one within 10 minutes and one band, from a trusted source or a different device | O(n) | METHOD 6 C5 |
| Jump hold | A reading two bands away within 2 minutes is parked; the next reading confirms or replaces it | O(1) | A wrong reading costs one extra photo, not a false alarm |
| State transition | A function of (state, smoothed depth, trust, trend) | O(n) | Section 5 |
| Rise rate | Theil-Sen: median of the slopes of all pairs | O(n^2), at most 66 pairs | Unmoved by outliers in up to 29% of points; least squares is moved by one |
| Time to no-go | (limit - depth) / rate for each class | O(classes) | |
| Passability | Compare the top of the depth range with the class limit | O(1) | Section 5 |
| Frame gate | Signature, difference from last sent and from previous, threshold from the noise window | O(pixels) to shrink the frame, then O(1,024) | ARCHITECTURE 13.5 |
| Distance | Haversine | O(1) | |
| Sharpness | Variance of a 4-neighbour Laplacian on a 320-pixel-wide copy | O(pixels) | Cheap and standard; no model call |
| Link check | Recompute the signature; constant-time compare; then expiry and purpose | O(length) | Constant-time compare avoids leaking the signature byte by byte |

### Planned algorithms

| Algorithm | Method | Cost | Note |
|---|---|---|---|
| Required pumping (METHOD 15.5) | Binary search on pump rate; each probe replays the recorded events | O(log(range / step)) replays | Valid because peak depth can only fall as pumping rises. Replaces "raise until it passes" |
| Uncertainty in the fix sheet | 1,000 runs with inputs drawn from their error ranges; report median and 10th to 90th percentile | O(1,000 x events) | |
| Inlet capacity | Smaller of weir and orifice flow, with perimeter and area scaled by the clear share | O(1) per inlet | METHOD 16.10 |
| Which inlets to clear first | Sites have few inlets, so every subset of up to 8 is evaluated (256 cases) and the best set of each size is kept | O(2^m), m <= 8 | Clearing one inlet changes the value of clearing the next, so ranking them one at a time can be wrong. Above 8 inlets, fall back to greedy and say so |
| Top actions across an area | Heap of size k | O(n log k) | |
| Power-cut detection | Count cameras newly offline per geohash cell; flag a cell above a share of its cameras | O(cameras in zone) | |

---

## 5. The state machine, precisely

```
state_for(site):
  if state in {WARNING, CRITICAL} and the last 4 readings fall each time   -> RECEDING
  if state == RECEDING:
      last two readings both below 12 cm                                   -> CLEAR
      last reading not above the one before                                -> RECEDING
      otherwise (rising again) fall through
  if smoothed high >= 20 cm and trusted                                    -> CRITICAL
  if smoothed high >= 12 cm                                                -> WARNING
  if state in {WARNING, CRITICAL}                                          -> RECEDING
  if state == RECEDING                                                     -> CLEAR
  otherwise                                                                -> unchanged
```

Rain alone moves CLEAR to WATCH, and ends a WATCH that has seen no water after an hour below
the threshold.

### Properties the tests enforce

Checked over 300 random histories of 40 steps each, mixing rain and readings from all sources:

1. The version rises by exactly one on every transition.
2. The state is always one of the five.
3. The smoothed low never exceeds the smoothed high.
4. Never more than 12 readings are kept.
5. A state-change event is produced if and only if the state changed.
6. A site enters CRITICAL only with depth of at least 20 cm and a trusted source.

Checked exhaustively over depths 0 to 79 cm for every class, still and moving water:

7. Deeper water is never more passable.
8. Lower confidence is never more passable.

Checked over 500 random sets of estimates:

9. A fused range is ordered and its confidence is between 0 and 1.

---

## 6. Interfaces

### 6.1 Module functions (built)

```
bands.band_for(depth_cm) -> "B0".."B5"
bands.answer_for(vehicle, low, high, confidence, moving=False) -> answer
bands.passability(low, high, confidence, moving=False) -> {vehicle: answer}

state.rain_index(past1, past3, next1) -> mm
state.fuse([(low, high, confidence)]) -> (low, high, confidence) | None
state.apply_rain(site, index_mm, ts) -> Site
state.apply_reading(site, reading) -> Site

store.load(table, city, site_id) -> Site
store.save(table, city, site, expected_version)        # raises if the version moved

rain.grid_cells(sites) -> {(lat, lon): [site_id]}
rain.fetch(sites) -> {site_id: (past1, past3, next1)}
rain.indexes(sites) -> {site_id: mm}

predict.rise_rate([(minute, depth)]) -> cm per minute | None
predict.minutes_to_no_go(depth, rate) -> {vehicle: minutes | None}

intake.check(image, hash, photo_pos, site_pos, requested_at, received_at, seen) -> reason
intake.crop_to_region(image, polygon) -> image
intake.blur_boxes(image, boxes) -> image

tokens.issue(key, purpose, subject, target, now, ttl) -> token
tokens.verify(key, token, purpose, now) -> claims | None

alerts.due(state, high, trusted, last_sent, now) -> {audience: kind}
alerts.template(kind, site_name, low, high, confidence, seen_at, ...) -> text

change.ChangeGate().should_send(image, now) -> bool
geo.encode(lat, lon) -> cell ; geo.cells_covering(lat, lon, radius) -> {cell}
volume.VolumeCurve(profile, width).volume(depth) / .depth(volume)
publish.site_entry(...) ; publish.city_document(...) ; publish.to_json(document)
reader.read_depth(image_path) -> reading dict
```

### 6.2 Public map file

```json
{"city": "hyderabad", "generated_at": 1760000000,
 "fields": ["i", "n", "y", "x", "s", "b", "l", "h", "t", "u"],
 "sites": [["hyd-000", "Underpass 0", 17.3, 78.4, "WARNING", "B2", 14, 19, 1, 1760000000]]}
```

Rows are arrays in the order given by `fields` (id, name, latitude, longitude, state, band,
low, high, trusted, updated). Naming the columns once, not on every row, is what keeps the
file small. Passability is not included: the browser computes it from `h` with the same rules
as `bands.py`.

Measured size:

| Sites | Bytes | Compressed |
|---|---|---|
| 100 | 9,273 | 1,110 |
| 500 | 46,385 | 5,301 |
| 2,000 | 186,553 | 21,021 |

ARCHITECTURE.md set a 50 KB target. It holds uncompressed up to about 500 sites and compressed
well beyond 2,000.

### 6.3 Queue message to the engine

```json
{"type": "rain",    "city": "hyderabad", "site_id": "hyd-001", "index_mm": 24.0, "ts": 1760000000}
{"type": "reading", "city": "hyderabad", "site_id": "hyd-001",
 "reading": {"ts": 1760000300, "low": 10, "high": 15, "confidence": 0.8,
             "source": "guardian", "device": "g1"}}
```

Message group: `site_id`. Deduplication id: `rain-{site_id}-{15-minute window}` for rain, the
photo's hash for readings.

---

## 7. Review of the code against this design

Each item was found by reading the code with the question "what happens at 10 or 100 times the
size, or when the input is hostile?"

### Fixed in this pass

| Finding | Effect | Fix |
|---|---|---|
| The rain function asked the forecast service for every site separately in one request, and a 100-site request timed out at 10 seconds on the live service | No rain index, so no watches, in any city of real size | Sites are grouped by forecast grid cell. 500 sites across Hyderabad became 56 points and one 3.3-second request, measured live |
| The rain function read only the first page of sites | Sites beyond the first page would never be watched | Reads every page |
| Rain messages were sent one call per site | 500 calls every 15 minutes | Sent ten per call, and a partial failure fails the run so it is retried |
| The rain function's time limit was 30 seconds against a service measured at 8 to 16 seconds per request | Timeouts under load | Limit raised to 120 seconds |

### Open

| Finding | Effect | Proposed fix |
|---|---|---|
| A site's rain threshold is copied into its record on first write and never refreshed | Changing a threshold in the registry has no effect afterwards | Read the threshold from the registry attributes on every load |
| `reader.py` has no retry on throttling | A burst of photos fails outright | Retry with backoff and jitter, then return `cannot_tell` |
| The engine treats a lost version check like any other failure | A harmless race waits for the queue's retry delay | Catch that one error and retry at once, up to 3 times |
| Building the volume curve is O(n^2) | None at 10 to 30 profile points | A single sweep in height order would be O(n log n); not worth doing yet |
| Theil-Sen is O(n^2) | None at 12 readings | Leave |
| The forecast grid cell is fixed at 0.05 degrees | If the provider's grid for India is coarser, some requests are redundant; if finer, some detail is lost | Confirm the grid for India and set the cell to match |
| Fallback alert wording is English only | Unusable for many residents | Templates in Telugu, Urdu and Hindi, checked by native speakers |

---

## 8. Test inventory

| File | Tests | Covers |
|---|---|---|
| `test_core.py` | 8 | Bands, passability, prediction |
| `test_state.py` | 14 | Transitions, trust, jump hold, fusion |
| `test_engine.py` | 4 | Engine handler against an in-memory table and bus |
| `test_rain.py` | 5 | Request building, parsing, grid grouping |
| `test_reader.py` | 2 | Request shape and refusal handling, against a stand-in client |
| `test_intake.py` | 11 | Photo checks, crop, blur, signed links |
| `test_alerts.py` | 18 | Who is alerted, repeat rule, wording |
| `test_change.py` | 5 | Frame gate |
| `test_design.py` | 12 | Geohash, volume curve, map file, and the properties in section 5 |
| **Total** | **79** | |

Not covered by any test: a real model call, a real deployment, and anything in the "planned"
rows of section 1.
