# NirmalDhara

"Clean flow": a flood warning for Hyderabad's known waterlogging points, and a record of which
places flood again and again. Built solo for Environmental Hacks (Heat and Water track),
8 to 11 October 2026.

1. **Watches before the water.** Every 15 minutes it reads the rain forecast at nine places that
   published reports say flood, and opens a *watch* at any where heavy rain is coming.
2. **Answers "can I get through?" per vehicle.** Depth is a range, never one number. Bikes, autos,
   cars, SUVs and people on foot each get "passable with care", "not safe" or "unsure"; the top of
   the range decides, and anything under 0.6 confidence is never "passable".
3. **One engine per place, one decision per flood.** A single engine owns each site's state. A flood
   workflow decides who is alerted, repeats, escalates to the next contact after five minutes
   without acknowledgement, and withdraws the warning when the flood ends. Each alert is sent once;
   a failed send is retried, and one that keeps failing raises an alarm for a person.
4. **A public map and a sheet per place.** The map shows each place as a small road cross-section
   that fills with water. Tapping one shows the depth, a to-scale drawing, and who can pass.
5. **The environmental case.** Every closed flood is kept, so a page ranks places by how long they
   blocked the road for cars. That points repair work at the drains and pumps that fail most.

**Read this before relying on it.** No photo has been read by the model yet, so the depth
readings you see come from scripts and a replay, not from camera or phone photos. The
waste-and-drain tracking half of the pitch is designed, not built. The full list is under
[What is built](#what-is-built).

![Architecture: what is deployed, with designed parts dashed](docs/architecture.svg)

## Try it

Open **https://s76zfmc6n5xd65b32tzf46dw3m0kvvik.lambda-url.ap-south-1.on.aws/** on a phone.

Unless heavy rain is forecast in Hyderabad as you look, it shows nine places, all clear, because no
real flood has been recorded. That is the true state, not a broken page. If rain is forecast, some
places show a thin ring: a watch, opened by the live forecast. Tap a place to open its sheet. Press **Key**
to see how to read the glyphs. **Repeat floods** shows the history page, which is empty until a
flood has been recorded.

To see a flood, run a replay (it plays a made-up evening into four of the real places; the map
will show those floods until you reset it; see [Replay](#replay-a-flood)).

## Run the tests

You need Python 3.11 or newer. Node.js is optional: seven test files check the web pages' logic
with Node and skip themselves if it is missing.

```bash
git clone https://github.com/ravithejanaini/NirmalDhara.git
cd NirmalDhara
python -m venv .venv
```

Activate the environment: `.venv\Scripts\activate` on Windows, `source .venv/bin/activate` on
macOS or Linux. Then:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
```

The tests need no AWS account and no network, and all of them should pass. Then try the
rules directly:

```bash
python -m nirmaldhara check --low 15 --high 25 --confidence 0.8
```

## What is built

| | What | Evidence |
|---|---|---|
| **Built and running on AWS** | Rain check every 15 minutes at nine sites, from a live forecast | Run on the deployed stack |
| | State engine: one queue group per site, version-checked writes, no lost events, a repeated message counted once | `docs/smoke-test.md` |
| | Flood workflow and timer: alerts, repeat, escalation after 5 minutes, stand-down when it ends | `docs/smoke-test.md`, 21 checks passed |
| | Notifier: each alert sent once to a topic | Captured by a test queue; **no person is subscribed yet** |
| | Map file and flood-history file, kept current by two writers that cannot overwrite each other with an older picture | 0.6 to 0.7 s from a queued reading to a changed file |
| | The site: map, per-place sheet with drawing, key, repeat-floods page, served over HTTPS | The address above |
| | Replay and reset for a repeatable demonstration | Same map twice in a row |
| **Built and tested, never run on real input** | Photo reader (a Claude model on Amazon Bedrock) | Request shape only. Model access is blocked pending AWS account verification |
| | Photo checks: distance, age, duplicate, dark, blurred; crop; face and plate blur boxes | Functions with tests; no deployed handler |
| | Signed capture and acknowledgement links | Tests only |
| | Camera change gate; rise-rate prediction; storage-volume curve for pump sizing | Tests only |
| | Evaluation table and photo-to-reading script | **Simulated only.** Run on 22 drawn scenes with a stand-in reader ([docs/evaluation-simulated.md](docs/evaluation-simulated.md)). Shows the tools work and that a dangerous miss would be counted; it is not evidence of how a model reads real floods |
| | CloudFront in front of the site | In `template.yaml`, switched off: AWS has not verified the account |
| **Designed only** | Photo upload from phones; camera network with emergency activation; waste and drain-inlet tracking; scenario engine; fix sheet; alert channels to people (SMS, chat); acknowledgement endpoint; official console | [ARCHITECTURE.md](ARCHITECTURE.md), [METHOD.md](METHOD.md) |

## Limits

- **Depth reading has never been measured.** The photo reader has not run against a real photo, so
  there is no accuracy figure. The only table in the repository is a simulated one, on drawn scenes,
  and is labelled as such. The thresholds come from published vehicle and wheel sizes
  (METHOD.md section 17), not from a test.
- **Nine places, from published reports.** Each has a source and date in
  [data/SOURCES.md](data/SOURCES.md). Their map positions are approximate (a few hundred metres),
  which matters for the 150 m photo-distance check and is not yet corrected.
- **A replay is a demonstration on the real map.** While one runs, the public site shows floods at
  real places. It refuses to run if anyone is subscribed to the alerts topic unless told to. A fast
  replay records real, short durations, so the repeat-floods page shows near-zero minutes blocked;
  use `--speed 1` for realistic ones.
- **No CDN.** CloudFront needs AWS to verify the account, which has not happened, so a small
  read-only Lambda serves the site. Fine for a demonstration; every page load is a function call.
  The account also allows only 10 concurrent Lambda runs in total (DESIGN.md 17.2).
- **In-country model inference is a design, not a demonstration.** The reader names an India
  inference profile; it has never been called.
- **No people are wired in yet.** The alerts go to a topic that nobody is subscribed to, there is
  no contact list, and there is no way to acknowledge an alert, so escalation to the next contact
  always happens. The smoke test proved the timing, not a delivery to a person.
- **Single region.** Everything is in Mumbai (ap-south-1). There is no second region.
- **Checked in a browser at phone size, not on a phone**, and not with a screen reader. Reduced
  motion is checked by reading the style sheets.

## Deploy

Needs the AWS SAM CLI and credentials allowed to create the stack.

```bash
sam validate --lint
sam build
sam deploy --stack-name nirmaldhara --region ap-south-1 --resolve-s3 --capabilities CAPABILITY_IAM --no-confirm-changeset
```

Deployed on 9 October 2026: 51 resources, 8 functions, 3 tables, 4 queues, an event bus with
rules and a 30-day archive, a state machine, a topic, a bucket and 3 alarms. Resource names are in
`data/stack-outputs.json`. Then:

```bash
python scripts/seed.py --apply          # the nine sites
python scripts/deploy_web.py --apply    # the pages
```

Both show what they would do when run without `--apply`. Switch CloudFront on, once AWS has
verified the account, with `--parameter-overrides EnableCloudFront=true`.

### Replay a flood

```bash
python scripts/replay.py                # shows the schedule
python scripts/replay.py --go           # plays 90 minutes in 2
python scripts/reset.py --go            # puts the four sites back to clear
```

`scripts/smoke_test.py` walks one invented site through a whole flood in about ten minutes and
writes `docs/smoke-test.md`.

## Layout

| Folder or file | Holds |
|---|---|
| `src/nirmaldhara/`, `src/handlers/` | The logic and the AWS functions; `src/` is all that is packaged for Lambda |
| `statemachine/`, `template.yaml` | The flood timer loop and the deployment template |
| `web/` | The map, the sheet, the repeat-floods page and their tests' subjects |
| `tests/` | The automated tests |
| `scripts/` | Seeding, sending, replay, reset, smoke test and file generators |
| `data/` | Site list and sources, scenarios, sample files |
| `docs/` | Smoke-test record, architecture picture, video script, submission writeup, and the list of claims with their support |
| `layers/vision/` | Requirements for the photo functions, built as a layer |
| `METHOD.md`, `ARCHITECTURE.md`, `DESIGN.md`, `TASKS.md` | Method, high-level design, low-level design, task plan |

## AI tools used

- **Claude Code**, with **Claude Opus 5.5** for design, the hard parts (concurrency, the alert
  workflow, the interface's look) and review, and **Claude Sonnet 5.5** for well-specified
  routine tasks. The task plan ([TASKS.md](TASKS.md)) says which model does which task and when to
  switch. All code and documents here were written by Claude Code under my direction; the
  tests and the AWS runs described here were executed in those sessions.
- **A Claude model on Amazon Bedrock** is the intended photo reader (`src/nirmaldhara/reader.py`).
  It has not run: access is blocked pending AWS account verification.
- Not AI: AWS SAM CLI and `cfn-lint` to validate the template, MapLibre for the map, Open-Meteo
  for the rain forecast.

## Sources

- Thresholds and rules: [METHOD.md](METHOD.md) section 17.
- The nine places: [data/SOURCES.md](data/SOURCES.md).
- Map data, rain forecast and type: [web/CREDITS.md](web/CREDITS.md). Map data © OpenStreetMap
  contributors; tiles from OpenFreeMap; weather data by Open-Meteo.com (CC BY 4.0).
- What was tested on AWS: [docs/smoke-test.md](docs/smoke-test.md).

MIT licence, see [LICENSE](LICENSE).
