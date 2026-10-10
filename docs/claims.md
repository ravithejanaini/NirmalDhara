# Claims and their support

Every claim made in the [README](../README.md), the [submission writeup](submission-writeup.md) and
the [video script](video-script.md), with what backs it. A claim with no support was reworded or
removed; the last section lists those.

How to read the support column:

- An entry beginning **tests/** names an automated test in this repository.
- An entry beginning **smoke:** names a row of [smoke-test.md](smoke-test.md), run on the deployed
  stack on 9 October 2026.
- An entry beginning **template:** names a resource in `template.yaml`, and **file:** a file in the
  repository.
- An entry beginning **design:** quotes a measurement or record written in `DESIGN.md`, so it can be
  found there.

`tests/test_claims.py` fails if any test, smoke row, resource, file or phrase named here does not exist.

## What it does

| # | Claim | Support | Qualification |
|---|---|---|---|
| 1 | It watches nine places that published reports say flood | `file: data/hyderabad_sites.json`, `file: data/SOURCES.md`, `tests/test_seed.py::test_a_site_is_refused_for_each_kind_of_fault` | Reports are from 2019 to 2025. Positions are approximate |
| 2 | It reads the rain forecast every 15 minutes | `template: RainFunction`, `tests/test_rain.py::test_one_request_covers_every_site`, `design: "live forecast, nine sites"` | |
| 3 | It opens a watch where heavy rain is coming, before any water | `tests/test_state.py::test_rain_starts_a_watch`, `smoke: 1 Rain index 25 mm` | "Heavy" is a rain index of 20 mm, a design choice. Set against real reports it would not have opened (claim 41) |
| 4 | Depth is a range, and the top of the range decides | `tests/test_core.py::test_passable_needs_upper_end_below_limit` | |
| 5 | A reading under 0.6 confidence is never "passable" | `tests/test_core.py::test_low_confidence_is_never_passable` | |
| 6 | Each vehicle class gets its own answer, the same on the page as in an alert | `tests/test_rules_match.py::test_rules_js_gives_every_stored_answer`, `tests/test_sheet.py::test_the_sentence_is_the_one_an_alert_would_send` | Limits come from published wheel and vehicle sizes, not from a trial |
| 7 | Critical needs 20 cm and a trusted source; one resident's photo is not enough | `tests/test_state.py::test_guardian_reading_moves_watch_to_warning_then_critical`, `tests/test_state.py::test_one_resident_cannot_make_a_site_critical` | |
| 8 | One unconfirmed photo warns the public but recommends no closure | `tests/test_alerts.py::test_one_unconfirmed_photo_warns_the_public_but_recommends_no_closure` | |
| 9 | One engine owns each place's state, and a queue keeps its readings in order | `template: EngineQueue`, `tests/test_engine.py::test_after_a_failure_the_sites_later_messages_wait_their_turn` | |
| 10 | Each alert is sent once | `tests/test_flood.py::test_a_warning_alerts_each_audience_once_however_often_it_is_run`, `smoke: 4 Same reading sent again` | If the function dies between sending and recording it, that alert can go twice |
| 11 | A failed send is retried, and one that keeps failing raises an alarm | `tests/test_flood.py::test_a_failed_send_is_not_lost`, `template: WorkflowDeadLettersAlarm` | Until a person acts on the alarm, that alert is late |
| 12 | A closure recommendation escalates after five minutes without acknowledgement | `smoke: 5 No acknowledgement for 5 min`, `tests/test_workflow.py::test_unacknowledged_closure_recommendation_escalates_twice_then_stops` | There is no way to acknowledge yet, so it always escalates. Measured at 5.7 minutes |
| 13 | When a flood ends, everyone who was warned is told | `smoke: 6 Stand-down`, `tests/test_workflow.py::test_a_flood_that_ends_tells_everyone_it_warned_and_a_dry_watch_tells_nobody` | |
| 14 | No message says a road is closed, open or safe | `tests/test_alerts.py::test_no_message_ever_says_the_road_is_closed`, `tests/test_alerts.py::test_the_stand_down_says_what_was_seen_and_never_that_the_road_is_open_or_safe` | |
| 15 | The map shows each place as a cross-section that fills, and the sheet's drawing is to scale | `tests/test_glyph.py::test_the_disc_fills_from_bottom_to_top_over_sixty_centimetres`, `tests/test_section.py::test_at_twenty_centimetres_the_water_reaches_a_third_of_the_car_wheel` | |
| 16 | Every flood that ends is recorded, and places are ranked by time blocked for cars | `tests/test_history.py::test_ranking_is_minutes_blocked_for_cars_then_floods_then_name_and_skips_unconfirmed_sites`, `tests/test_offenders.py::test_the_page_ranks_exactly_as_the_python_does` | No real flood has been recorded. A fast replay records about a minute of blocked road |

## How it runs

| # | Claim | Support | Qualification |
|---|---|---|---|
| 17 | It runs serverless on AWS in Mumbai: 8 functions, 3 tables, 4 queues, an event bus with an archive, a state machine, a topic and a bucket | `file: data/stack-outputs.json`, `tests/test_architecture.py::test_every_function_in_the_template_is_in_the_picture_once`, `file: docs/smoke-test.md` | Counted on the live stack on 9 October 2026 |
| 18 | A queued reading changes the public map file in 0.6 to 0.7 seconds | `design: "0.6 to 0.7 seconds"` | Three runs, from idle, with one site. Not a load test |
| 19 | A replay gives the same map every time | `design: "identical public map"`, `tests/test_scenario.py::test_each_site_tells_the_story_the_file_says` | Run twice |
| 20 | In the replay, three places go on watch, one becomes critical and recedes, one stays an unconfirmed warning | `tests/test_scenario.py::test_each_site_tells_the_story_the_file_says`, `tests/test_video_script.py::test_the_cut_points_are_the_moments_the_replay_really_produces` | A scripted evening, not a real flood |
| 21 | The tests run from a clean clone with no AWS account | `design: "tests failed to collect on a clean install"` | Done once, on Windows with Python 3.13, on 9 October 2026 |
| 22 | The replay refuses to start on a site that is not clear, or while the alerts topic has a subscriber | `file: scripts/replay.py` | By reading the code. No automated test covers these two refusals |
| 23 | Claude Code wrote the code and documents, with Opus 5.5 and Sonnet 5.5 assigned per task | `file: TASKS.md` | The commit history carries a co-author line for the model on each commit |

## What is said to be unproven

These are claims too: that something has *not* been done. Each is true as of 9 October 2026.

| # | Claim | Support |
|---|---|---|
| 24 | The photo reader has never read a real photo, and there is no accuracy figure | `design: "never run against the real model"`, `tests/test_reader.py::test_request_carries_image_and_schema` (a stand-in client only) |
| 25 | The photo reader's only evaluation table is simulated, on drawn scenes | `file: docs/evaluation-simulated.md`, `tests/test_evaluation.py::test_a_simulated_run_never_touches_the_real_evaluation` |
| 26 | No person is subscribed to the alerts, and there is no contact list | `design: "No person is wired in."` |
| 27 | Waste and drain-inlet tracking and the camera network are designed, not built | `design: "planned, section 16"` |
| 28 | CloudFront is written and switched off | `tests/test_architecture.py::test_the_cloudfront_resources_are_drawn_dashed_because_they_are_off` |
| 29 | Site positions are approximate | `file: data/SOURCES.md` |
| 30 | The pages were checked in a browser at phone size, not on a phone or with a screen reader | `tests/test_accessibility.py::test_the_controls_come_before_the_map_in_the_page_so_the_keyboard_reaches_them_first` (static guards only) |

## What was measured on a real flood

Added 10 October 2026. A published set of river-camera pictures from England, each with a measured water
level ([credits](../samples/tewkesbury/CREDITS.md)). A river, not a street, and not Hyderabad.

| # | Claim | Support | Qualification |
|---|---|---|---|
| 31 | A waterline detector for a fixed camera, with no model, was 13 cm out, typically, at one river lock, and of no use at a second camera | `file: docs/waterline-river.md`, `tests/test_river_camera.py::test_the_report_says_which_camera_is_the_test_and_how_far_out_it_was` | One reading in ten was more than 54 cm out. One picture an hour; the strip was fixed beforehand and run once |
| 32 | A gauge learnt from a camera's own measured pictures gave a level for 4 pictures in 10 at that lock, 8 cm out typically; with the detector, 8 cm for nearly every picture; 31 cm when learning only from earlier days; no use at two other cameras | `file: docs/gauge-river.md`, `tests/test_learn_river_cameras.py::test_the_report_says_which_cameras_were_run_once_and_what_was_changed_after` | The levels were read by the dataset's authors from the same pictures. One correction was made after the first run and is recorded in the report |
| 33 | Neither is connected to the warnings, and no place has a camera or a measured level | `design: "Never on a street; no caller yet"`, `design: "Needs measured levels, which no site has; no caller yet"` | |
| 34 | Four reference surfaces in one view, read together, were 10 cm out, typically, at that lock, against 13 cm for one; at a second camera joining gained nothing | `file: docs/multi-reference-river.md`, `tests/test_multi_reference.py::test_the_report_says_which_camera_is_the_test_and_what_joining_gained` | One reading in ten was still more than 46 cm out, and the best single surface did about as well alone |
| 35 | Fixing a camera from several known dimensions, and two cameras giving the speed of the water, are tested code and a simulation only | `tests/test_multiview.py::test_two_cameras_place_a_floating_thing_and_time_gives_its_speed`, `file: docs/multiview-simulation.md` | No place has two cameras on one water |
| 36 | One model of every reference surface in a view, through time, gave every picture a level at that lock, 11 to 12 cm out, typically, against 13 cm for one surface | `file: docs/depth-model-river.md`, `tests/test_river_depth_model.py::test_the_report_says_which_camera_is_the_test_what_was_gained_and_what_was_taken_out` | One in ten was still more than 41 to 47 cm out, most of it water beyond the levels learnt from |
| 37 | The chain from several cameras' frames to the site engine's answer has been run on rendered scenes only | `tests/test_site_simulation.py::test_the_chain_holds_from_frames_to_the_engines_answer`, `file: docs/site-simulation.md` | |
| 38 | The prediction stage's slope was tried on real water for the first time: from readings a camera can give it told the level ahead no better than saying "no change"; from the measured levels it was closer across a night and no closer within a day | `file: docs/forecast-river.md`, `tests/test_river_forecast.py::test_the_report_says_which_camera_is_the_test_what_was_found_and_what_was_not_kept` | A river read hourly over days, not a street. Only 9 and 10 forecasts run across a night. With three days in a row unseen the model's reading itself was 23 and 32 cm out |
| 39 | The engine gives minutes until cars lose passage only for a rise that stands clear of the doubt in the readings | `tests/test_workflow.py::test_no_minutes_are_put_on_a_rise_smaller_than_the_doubt_in_the_readings`, `tests/test_core.py::test_a_rise_is_clear_only_when_the_newest_range_lies_wholly_above_the_oldest` | A design choice, and a rule to say less. Its one trial did not confirm it: where the rise was clear the slope was further out more often than closer. The deployed functions predate it |
| 40 | The designs the model shares with defence and with forecasting offices are listed with what was kept and what was tried and dropped: of four tried on the real flood, one was kept | `file: docs/borrowed-designs.md`, `tests/test_river_forecast.py::test_the_borrowed_designs_page_says_what_was_kept_and_what_was_not` | Naming a design does not make the model closer. Not every source was checked on the day; the page marks which were |
| 41 | Replayed over the rain the live system is fed, the watch rule would not have opened on any of 11 dated reports that name one of the nine places under water | `file: docs/watch-history.md`, `tests/test_watch_history.py::test_the_figures_in_the_report_are_the_ones_the_data_gives` | The reports are what an hour's search found, not every flood. It counts misses and cannot count false watches. Nothing after the watch was tested |
| 42 | On five of six occasions the forecast's rain was a twentieth to a quarter of what a gauge near the place recorded | `tests/test_watch_history.py::test_the_models_rain_is_set_beside_what_gauges_recorded`, `file: data/flood-reports.json` | Gauge figures are as quoted in news reports, one of them 5 km from the place |

## Reworded or removed in this check

| Was | Why | Now |
|---|---|---|
| "Each alert is sent once (twice in one rare crash case, never lost)" | "Never lost" is too strong: an alert that fails every retry waits in a failure queue until a person acts | "a failed send is retried, and one that keeps failing raises an alarm for a person" |
| "Right now it shows nine places, all clear" | Only true while no heavy rain is forecast; the live system opens watches by itself | "Unless heavy rain is forecast in Hyderabad as you look, it shows nine places, all clear" |
| "Guardians nearby are asked for a photo" (video draft) | There are no guardians and no nearby lookup in use: the request goes to a topic nobody reads | "a request for photos is issued" |
| "reviewed, run and tested by me" (README draft) | The assistant cannot know what the author reviewed | "written by Claude Code under my direction" |
| A count of tests in the README and the video | A number that is stale the next day | No count; `DESIGN.md` section 18 is generated from pytest |
