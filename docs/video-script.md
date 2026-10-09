# Video script and shot list

Target length **2:45**, hard limit 3:00. The event page asks for "Three minutes, recorded… to show
what it does, who it is for, and where AWS fits"; shot 1 says who it is for, shot 5 where AWS fits.
The narration below is about 370 words: at an ordinary
speaking pace of 150 words a minute that is 2:20 of speech, which leaves 25 seconds of breathing
room across seven shots. `tests/test_video_script.py` fails if the narration grows past 400 words.

Lines beginning with `>` are what you say. Everything else is what is on screen.

## Rules for this video

1. **Say it is a replay.** The floods on the map are a scripted evening played into the real
   system. Keep the caption **"Replay of a scripted evening · 45× speed"** on screen for shots 2, 3
   and 6. Nothing here happened to these places today.
2. **Say what has not run.** The photo reader has not read a real photo. Shot 7 says so in words.
3. **Keep the map credit in frame.** Any shot of the map must show the line at the bottom:
   "OpenFreeMap © OpenMapTiles Data from OpenStreetMap". The licence requires it in video.
4. **Do not show a secret.** No terminal with keys, no AWS account page with billing details.

## Before recording

| Step | Command or action |
|---|---|
| Phone-sized browser window | About 390 px wide. Open the public address from the README |
| Clear the welcome | Press "Got it" once, or keep it for shot 1 if you want it in the video |
| Clean start | `python scripts/reset.py --go --forget-floods` |
| Check | The map shows nine places, all empty discs; the bar reads "No water reported in Hyderabad right now…" |
| AWS console tabs, signed in, region Mumbai | SQS → the engine queue · Step Functions → the flood state machine · DynamoDB → the Sites table, Explore items |
| For shot 6 | Decide A or B below, and prepare it before you start |
| Practise first | `python scripts/serve_web.py`, then `python scripts/rehearse.py`: the same replay on your own machine, touching neither AWS nor the public map |

**The record for shot 6.** A fast replay records about a minute of blocked road, so the repeat floods
page would show "0 min". Pick one:

- **A: one real-time replay beforehand.** Run `python scripts/replay.py --go --speed 1` about 100
  minutes before you record, and do not reset afterwards. The page then shows a flood the system
  itself recorded: **one row**, Lakdikapul railway bridge, 1 flood, 18 minutes blocked for cars, peak
  33 cm (worked out by running the scenario through the real workflow on a simulated clock). True,
  but one row does not show a ranking. The public map shows the replay's floods for those 90 minutes.
- **B, recommended for the picture: the sample page.** Run `python scripts/serve_web.py` and open
  `http://127.0.0.1:8080/offenders.html`. It shows invented data under a red "Sample data" banner.
  If you use it, replace the last sentence of shot 6 with: "What you see here is sample data, to
  show the page; real records build up with each monsoon."

## Shots

### 1 · 0:00–0:18 · The map, all clear

Screen: the map at night, nine empty discs, the bar at the bottom. Slow pan or still.

> Every monsoon the same underpasses in Hyderabad flood, and people drive into water they cannot
> judge. NirmalDhara is for those drivers, and for the engineers who fix the drains. It watches
> nine such places, answers one question, can I get through, and records which ones keep failing.

### 2 · 0:18–0:38 · Rain starts a watch

Action: in a terminal off screen, run `python scripts/replay.py --go`. Start the screen recording as
you press Enter. Three places gain a thin breathing ring within two seconds.

Screen: the map, caption on. Use replay seconds 0 to 20.

> This is a replay of a scripted evening, not a real flood. Every fifteen minutes the system reads
> the rain forecast. Heavy rain is coming at three places, so each goes on watch before any water
> arrives, and a request for photos is issued.

### 3 · 0:38–1:15 · Depth, and who can pass

Screen: keep recording the same replay. What happens, in seconds from the start of the replay:

| Second | On the map |
|---|---|
| 24 | Lakdikapul railway bridge shows its first water |
| 28 | It becomes a warning |
| 36 | **Tap it now:** the sheet reads 14–19 cm, with the drawing |
| 40 | It turns critical: red ring, "Do not enter". The Mindspace underpass shows a notched edge |
| 60 | Lakdikapul starts to recede: a small arrow down |
| 72 | It clears |

Cut this shot from second 24 to about second 60. Close the sheet at about second 44 and tap the
Mindspace underpass to show the notched edge and "From one unconfirmed photo".

> As readings arrive, each place fills like a cross-section of the road. Depth is always a range,
> never one number. Tap a place: fourteen to nineteen centimetres, not safe for bikes and autos,
> passable with care for cars, drawn to scale. At twenty centimetres from a trusted source it turns
> critical. This other place rests on one resident's photo, so its edge is notched: the public is
> warned, but nobody is asked to close a road on a single photo.

### 4 · 1:15–1:35 · Alerts

Screen: `docs/smoke-test.md` on GitHub, scrolled to "Alerts as delivered". Move down the table as
you speak. If you have subscribed your email to the alerts topic, show the inbox instead and add
`--alerts-ok` to the replay command.

> Each alert is sent once. This is the record from the test on AWS: a warning to residents, a
> closure recommendation to traffic control, five minutes with no answer and it goes to the next
> contact, and when the water falls, everyone who was warned is told it has ended.

### 5 · 1:35–1:58 · AWS

Screen: three quick console views, about seven seconds each: the SQS engine queue; the Step
Functions execution graph of a flood (open the latest execution); the Sites table with a site's
state. The rules require AWS to be visibly in use, so do not skip this.

> It runs on AWS in Mumbai, with no servers to keep up. A queue keeps each place's readings in
> order. One engine owns each place's state. A Step Functions timer drives repeats and escalation.
> Lambda, DynamoDB, EventBridge, S3 and SNS do the rest.

### 6 · 1:58–2:28 · The environmental case

Screen: the repeat floods page (option A or B above), caption on.

> The same readings, kept, are the environmental case. Every flood that ends is recorded: how deep
> it got, and how long it blocked the road. Places are ranked by time blocked, so drain and pump
> repairs go where flooding keeps coming back. This record came from the replay; real ones build up
> with each monsoon.

### 7 · 2:28–2:48 · What is not proven

Screen: the README on GitHub, scrolled to "What is built", then "Limits".

> What is not proven. The photo reader has not yet read a real photo, because AWS has not verified
> the account for model access, so there is no accuracy figure. Tracking the waste that blocks
> drains is designed, not built. The code, the tests and every limit are in the repository.

## After recording

- Total under 3:00. Check the caption is on shots 2, 3 and 6 and the map credit is readable.
- Run `python scripts/reset.py --go --forget-floods` so the public map does not keep showing the
  replay's floods.
- Upload to YouTube with the visibility the submission form asks for.
