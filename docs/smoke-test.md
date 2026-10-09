# Smoke test on AWS

Run on 09 October 2026 at 19:14 IST against the stack `nirmaldhara` in `ap-south-1`, by `python scripts/smoke_test.py`. It took 7.2 minutes.

**Result: every step passed.**

One test site, `hyd-900`, was walked through a whole flood: rain, rising readings, a repeated reading, five minutes with no acknowledgement, falling readings, and clearing. The site is not a real place and has no position, so it never appeared on the public map. Everything the test created was removed afterwards.

| Step | Expected | Seen | Took | |
|---|---|---|---|---|
| 1 Rain index 25 mm | Site WATCH | WATCH | 1.1 s | pass |
| 1 Flood event | One open event | open, start 1791553017 | 2.1 s | pass |
| 1 Timer | Execution running, named after the flood | [('hyd-900-1791553017', 'RUNNING')] | 0.5 s | pass |
| 1 Photo request | Sent to guardians | ['Heavy rain is expected at SMOKE TEST (not a real place). Please send a photo of the road from a safe, dry spot. Do not go near the water.'] | 1.1 s | pass |
| 2 Reading 11-16 cm | Site WARNING | WARNING | 1.1 s | pass |
| 2 Alerts | warning, advisory, pump_request, blocked, each marked sent | ['advisory', 'blocked', 'photo_request', 'pump_request', 'warning'] | 0.5 s | pass |
| 2 Wording | Residents told depth and who is not safe | ['Water at SMOKE TEST (not a real place) is shin deep (11-16 cm, seen 7:07 pm). Not safe for bikes, scooters and autos. Passable with care for cars, SUVs and people on foot. Do not enter moving water at any depth.'] | 1.4 s | pass |
| 3 Readings 24, 28 cm | Site CRITICAL (median of three is 24, trusted source) | CRITICAL, 15-20 cm | 0.0 s | pass |
| 3 Alerts | do_not_enter, closure_recommendation, pump_urgent, each marked sent | ['advisory', 'blocked', 'closure_recommendation', 'do_not_enter', 'photo_request', 'pump_request', 'pump_urgent', 'warning'] | 0.3 s | pass |
| 3 Closure wording | Recommends closing; never says the road is closed | ['CRITICAL: SMOKE TEST (not a real place). Water is below the knee (15-20 cm, seen 7:07 pm), confidence 0.8. Recommend closing both entries.'] | 1.3 s | pass |
| 4 Same reading sent again | Counted once: readings, alerts and version unchanged | readings 3, alerts 9, version 4 | 0.0 s | pass |
| 5 No acknowledgement for 5 min | Closure recommendation goes to the next contact | ['CRITICAL: SMOKE TEST (not a real place). Water is below the knee (19-24 cm, seen 7:07 pm), confidence 0.8. Recommend closing both entries.'] \| 5.9 min after the first | 341.4 s | pass |
| 5 Photo re-ask during the flood | Quotes the last reading, not the forecast | ['Water at SMOKE TEST (not a real place) was below the knee (19-24 cm, seen 7:07 pm). Please send a photo of the road from a safe, dry spot. Do not go near the water.'] | 1.0 s | pass |
| 6 Reading 18 cm | Site CRITICAL | CRITICAL | 0.4 s | pass |
| 6 Reading 10 cm | Site WARNING | WARNING | 1.1 s | pass |
| 6 Reading 8 cm | Site RECEDING | RECEDING | 1.1 s | pass |
| 6 Reading 6 cm | Site CLEAR | CLEAR | 0.0 s | pass |
| 6 Flood event closes | Closed as a flood, with its peak | flood, peak 19-24 cm, cars blocked 6 min, 2 photo requests | 0.0 s | pass |
| 6 Stand-down | Everyone who was warned is told the warnings have ended | ['fleet', 'pump_operator', 'residents', 'traffic_control'] | 1.4 s | pass |
| 6 Stand-down wording | Says what was seen; never that the road is open or safe | ['SMOKE TEST (not a real place): water is now ankle deep (3-8 cm, seen 7:13 pm). Earlier warnings for this site have ended. Do not enter moving water at any depth.'] | 1.1 s | pass |
| 6 Timer ends | Execution succeeded, none left running | [('hyd-900-1791553017', 'SUCCEEDED'), ('hyd-900-1791552397', 'SUCCEEDED')] | 45.2 s | pass |

## Alerts as delivered

Every message the alerts topic delivered during the run, in order.

| After | To | Contact | Text |
|---|---|---|---|
| 0.1 min | guardians | 0 | Heavy rain is expected at SMOKE TEST (not a real place). Please send a photo of the road from a safe, dry spot. Do not go near the water. |
| 0.2 min | residents | 0 | Water at SMOKE TEST (not a real place) is shin deep (11-16 cm, seen 7:07 pm). Not safe for bikes, scooters and autos. Passable with care for cars, SUVs and people on foot. Do not enter moving water at any depth. |
| 0.2 min | fleet | 0 | SMOKE TEST (not a real place): shin deep (11-16 cm, seen 7:07 pm). |
| 0.2 min | pump_operator | 0 | Water at SMOKE TEST (not a real place) is shin deep (11-16 cm, seen 7:07 pm) and rising. Please start the pump. |
| 0.2 min | traffic_control | 0 | Advisory: SMOKE TEST (not a real place). Water is shin deep (11-16 cm, seen 7:07 pm), confidence 0.8. Not safe for bikes, scooters and autos. Passable with care for cars, SUVs and people on foot. |
| 0.3 min | fleet | 0 | SMOKE TEST (not a real place): below the knee (15-20 cm, seen 7:07 pm). |
| 0.3 min | residents | 0 | DO NOT ENTER SMOKE TEST (not a real place). Water is below the knee (15-20 cm, seen 7:07 pm). Use another route. Do not enter moving water at any depth. |
| 0.3 min | traffic_control | 0 | CRITICAL: SMOKE TEST (not a real place). Water is below the knee (15-20 cm, seen 7:07 pm), confidence 0.8. Recommend closing both entries. |
| 0.3 min | pump_operator | 0 | URGENT: water at SMOKE TEST (not a real place) is below the knee (15-20 cm, seen 7:07 pm). Pumping is needed now. |
| 5.2 min | guardians | 0 | Water at SMOKE TEST (not a real place) was below the knee (19-24 cm, seen 7:07 pm). Please send a photo of the road from a safe, dry spot. Do not go near the water. |
| 6.2 min | traffic_control | 1 | CRITICAL: SMOKE TEST (not a real place). Water is below the knee (19-24 cm, seen 7:07 pm), confidence 0.8. Recommend closing both entries. |
| 6.4 min | residents | 0 | SMOKE TEST (not a real place): water is now ankle deep (3-8 cm, seen 7:13 pm). Earlier warnings for this site have ended. Do not enter moving water at any depth. |
| 6.4 min | pump_operator | 0 | SMOKE TEST (not a real place): water is now ankle deep (3-8 cm, seen 7:13 pm). Earlier warnings for this site have ended. Do not enter moving water at any depth. |
| 6.4 min | fleet | 0 | SMOKE TEST (not a real place): water is now ankle deep (3-8 cm, seen 7:13 pm). Earlier warnings for this site have ended. Do not enter moving water at any depth. |
| 6.4 min | traffic_control | 0 | SMOKE TEST (not a real place): water is now ankle deep (3-8 cm, seen 7:13 pm). Earlier warnings for this site have ended. Do not enter moving water at any depth. |

## What this does and does not show

- It shows the deployed services accept the same writes and conditions the unit tests imitate, and that the real one-minute and five-minute clocks drive the workflow.
- Alerts were captured from the topic by a temporary queue. Nothing was delivered to a person: the topic had no email or phone subscribed.
- Readings were typed in by the script. No photo was read by a model in this test.
