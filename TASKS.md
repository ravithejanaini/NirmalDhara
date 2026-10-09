# NirmalDhara: task plan

Written 9 October 2026. The submission form opens on 11 October at 8:00 AM. Check the closing
time on the event page today; this plan assumes the work must be finished by the evening of
10 October, leaving the morning of the 11th for the video and the form only.

That is about two working days. The plan is ordered so that **stopping at any cut line still
leaves something that can be submitted**.

Sections 0 to 2 give the position, the recommendations and the design direction. Section 3
explains how the tasks are organised, sections 4 to 12 are the tasks, and section 13 is the
priority and order. Times are estimates.

---

## 0. Where things stand

| Area | State |
|---|---|
| Method, architecture, low-level design | Written |
| Core logic: bands, state engine, rain check, workflow, notifier, alerts, intake checks, links, change gate, map file | Built, 117 tests passing |
| Deployment template | Written, parses. Never deployed |
| Photo reader | Built. Never run against the real model |
| Any screen a person can look at | Nothing |
| Model access on Bedrock | Blocked; support case 179152567100607 open |
| Uncommitted work | Flood workflow, notifier, engine fixes, design rewrite |

The gap is plain: the reasoning is strong and nothing is visible. Judges see a three-minute
video. The INF, PUB and WEB workstreams close that gap first.

---

## 1. Recommendations

Each one is carried out by the task named beside it; this section only says why.

1. **Make it visible before making it deeper.** The back end already does more than a
   three-minute video can show. → the `PUB` and `WEB` tasks come before `PIPE` and `ENV`.
2. **Do not wait on the support queue.** → MOD-01 has a deadline and a default.
3. **Drive the demo from a replay, not from the weather.** → DEMO-01, DEMO-02.
4. **Show the drain and waste part as one worked example on real images**, not as a live
   camera network that does not exist. → ENV-03.
5. **State what is unproven.** Depth reading has not been measured against real depth.
   → MOD-04, SUB-04.

---

## 2. Design direction for the interface

You asked for something aesthetically pleasing and closer to art than to a dashboard. One
direction, chosen to fit the subject, described closely enough to build.

### 2.1 The idea: "ink and water"

The city at night in the monsoon, drawn like a print. The map is quiet and dark; water is the
only thing with colour, and it behaves like water. A site does not turn red. It **fills**.

The reference points are woodblock prints of water and old survey maps: flat areas of colour,
fine contour lines, generous empty space, one accent. Not glass panels, not neon, not
gradients on everything.

### 2.2 Palette

| Role | Colour | Use |
|---|---|---|
| Night | `#0E1A2B` | Page and map ground |
| Paper | `#F3EDE1` | Sheets, cards, text on dark |
| Ink | `#16202E` | Text on paper |
| Line | `#2B3F5C` | Roads, contours, hairlines |
| Shallow | `#7FB7BE` | Ankle deep, watch |
| Water | `#2F7F93` | Shin deep, warning |
| Deep | `#134B66` | Knee deep and above |
| Signal | `#E4572E` | Critical only. One colour, used rarely |
| Moss | `#8A9A5B` | Clear, receding, "passable with care" |

Depth is shown by the blues getting darker, as water does. Vermilion appears only for
"do not enter", so it still means something when it appears.

### 2.3 Type

- **Display:** Fraunces (a soft serif), for site names and the one large number on a sheet.
- **Text:** Inter, for everything else.
- **Numbers:** tabular figures, so a changing depth does not make the line jump.
- Telugu and Urdu text will need Noto Sans Telugu and Noto Nastaliq Urdu when translations
  are added.

Scale: 40 / 24 / 17 / 14 px. Nothing smaller than 14 on a phone in the rain.

### 2.4 The signature element: the depth glyph

Each site is drawn as a small circle that is a **cross-section of the road**. It is empty
when dry. As the reading rises it fills from the bottom with a slow wave line on top. The
range is honest: the solid fill reaches the low end, and a lighter band reaches the high end.
An unconfirmed reading has a dashed outline. A critical site has a thin vermilion ring.

This one glyph carries state, depth, uncertainty and trust, and it is the thing people will
remember from the video.

On the site's sheet the same idea is drawn large: a car, a scooter and a person in outline,
with the water band across them at the measured range. The answer "not safe for cars" is then
something the eye sees before it is read.

### 2.5 Motion

- Water rises over 800 ms with an ease-out. It never jumps.
- The wave line drifts slowly, a few pixels, only on sites with water.
- A new alert arrives as a ripple from the site, once.
- Everything stops under `prefers-reduced-motion`.

### 2.6 Layout

- **Phone first.** Full-screen map. A paper sheet slides up from the bottom for a site.
- **One number per sheet.** The depth range, large. Then the plain sentence. Then the
  vehicles. Then when it was seen and by whom.
- **Hairlines, not boxes.** Sections are separated by a 1 px line and space.
- **A faint paper grain** over the sheets (one small repeating image, 3% opacity).
- **Console** (officials): the same language on a wider canvas. Left: the map. Right: a
  column of sites ordered by urgency, each a row with its glyph, name and one line.

### 2.7 Rules that keep it honest

- Colour is never the only signal: every state also has a word and a shape.
- Text contrast at least 4.5 to 1. Vermilion on night passes; check blues on night.
- Every reading shows its age. Old data is drawn faded, and says "seen 40 min ago".
- The screen never says "road closed". It says what was seen and what is not safe.

---

## 3. How the tasks are organised

### 3.1 Workstreams

| Prefix | Workstream | Tasks | Work |
|---|---|---|---|
| `REPO` | Repository | 3 | 0.7 h |
| `INF` | Running on AWS | 8 | 5.5 h |
| `MOD` | The model and its evidence | 5 | 3.9 h |
| `PIPE` | Photo to reading | 6 | 5.2 h |
| `PUB` | Data the screens read | 4 | 2.6 h |
| `WEB` | Resident map | 10 | 9 h |
| `ENV` | Environment views | 4 | 4.5 h |
| `DEMO` | Replay and video | 5 | 3.8 h |
| `SUB` | Submission | 8 | 3.5 h |
| | **All** | **53** | **38.7 h** |

There are about two days. The whole list does not fit and is not meant to: section 13 says
which tasks are done, in what order, and where to stop.

### 3.2 Reading a task heading

`### ID · title · owner · time · priority`

| Owner | Meaning |
|---|---|
| `You` | Only you can do it: accounts, keys, photos, recording. No model is involved |
| `AI: Sonnet` | The assistant does it, running **Sonnet 5.5** (`claude-sonnet-5-5`) |
| `AI: Opus` | The assistant does it, running **Opus 5.5** (`claude-opus-5-5`) |
| `Both: Sonnet`, `Both: Opus` | The assistant writes or diagnoses on the named model; you run commands on your machine or supply the content named in the steps |

| Priority | Meaning |
|---|---|
| `Must` | Part of the submission |
| `Should` | Done in run-sheet order (13.3) unless a checkpoint (13.4) removes it |
| `Could` | Done only under the last rule in 13.4 |
| `Conditional`, `Fallback` | Done or skipped by the **Condition** line in the task |

### 3.3 Which model, and when to switch

**The owner in the heading is the model. There is no other source.** It was assigned by this
rule, which also covers any task added later:

| Use **Opus 5.5** when the task… | Tasks |
|---|---|
| has to find out why a real AWS service rejected or misbehaved | INF-05, INF-08 |
| handles a signed link, a single-use value, or a raw photo before it is blurred | PIPE-02, PIPE-03 |
| sets how the product looks where this file gives a direction, not a finished layout | WEB-01, WEB-03, WEB-04, WEB-06, WEB-07 |
| writes an instruction for the vision model, or draws a conclusion from data or hydraulics | MOD-05, ENV-02, ENV-03 |
| decides what the project claims in public | DEMO-03, SUB-03, SUB-04 |

**Sonnet 5.5** does every other AI task: those whose files, steps and check are fully written
here.

**Switching up, from Sonnet to Opus, in the middle of a Sonnet task.** Stop and switch if
either is true:

1. The task's **Done when** check has failed twice after two different fixes.
2. The fix would change one of the protected files below, which hold the safety rules and
   the concurrency design in `DESIGN.md` sections 6 to 9.

   | Protected |
   |---|
   | `src/nirmaldhara/state.py`, `src/nirmaldhara/workflow.py`, `src/nirmaldhara/store.py` |
   | `src/nirmaldhara/bands.py`, `src/nirmaldhara/alerts.py` |
   | `src/handlers/engine.py`, `src/handlers/flood.py`, `src/handlers/notifier.py` |
   | `statemachine/flood.asl.json` |
   | The `Policies` block of a function or state machine that already exists in `template.yaml` |

   Two things do not count as changing a protected file: INF-04 moving the files without
   editing them, and a task adding a new resource with its own `Policies` block to
   `template.yaml`.

Opus then finishes that task. The next task starts on the model in its own heading.

**Switching down.** Never in the middle of a task. An Opus task is finished on Opus.

**How to switch.** Use the model picker in the app before sending the message that starts the
task, and start the message with the task id, for example "Do WEB-04". The run sheet in 13.3
groups the work into six blocks; the model is set once at the start of each.

**If the wrong model was used.** A Sonnet task done on Opus stands. An Opus task done on
Sonnet is checked again on Opus against its **Done when** line before the next block starts.

### 3.4 Rules for every AI task

These apply to all of them and are not repeated in the tasks.

1. Work only on the files named in the task. A needed change elsewhere is reported, not made,
   unless it is one line.
2. `python -m pytest` passes before and after.
3. The **Done when** check is run and its actual result is reported, including a failure.
4. One commit per task, message starting with the task id (`WEB-04: depth glyph`), then push.
   `git log --oneline` is the record of what is done; there is no separate tracker.
5. No secret is written to any file or to the chat.
6. Sending a message, submitting a form and deleting anything in AWS wait for your yes.
7. A command that needs the model key or AWS rights the assistant's shell does not have is
   run by you in your own terminal; the assistant gives the exact command and reads the
   result you paste back.
8. The assistant says when the model must change. Its message ending a block's last task
   closes with one line in this form: "Block A is done. Switch to Opus 5.5 before block B,
   which starts with WEB-01." The same line is given when a Sonnet task has to be handed up
   under 3.3. If a task is started on a model other than the one in its heading, the
   assistant says so before doing any work.

### 3.5 Parts of a task

**Goal** what exists afterwards · **Condition** when the task is done or skipped ·
**Files** created or changed · **Steps** in order · **Done when** a check with a visible
result · **Tests** automated checks to add · **Risk** the likely failure and the way round it.
What a task needs first is stated once, in 13.2. Who may do and decide what is in 3.6.

### 3.6 Roles and authority

Three roles. The owner label in a task heading says which role does the task; this section
says what each role may and may not do.

| Role | Who | Does | Decides | May not |
|---|---|---|---|---|
| **Owner** | You | Everything marked `You`; runs commands that need your keys or AWS rights; supplies sites, photos and the recording | Scope, what is claimed in public, every checkpoint answer, every outward action (send, submit, delete in AWS), any change to this file | — |
| **Lead** | Opus 5.5 | Tasks marked `Opus`; takes over a Sonnet task under the two rules in 3.3; reviews each Sonnet block | How a task is built, within its **Files** and **Done when** | Change scope, priorities or this file without the Owner's yes; act outwardly without the Owner's yes |
| **Builder** | Sonnet 5.5 | Tasks marked `Sonnet`, exactly as written | Details the task leaves open, inside the files it names | Edit a protected file (3.3); skip or reorder tasks; change a **Done when** check; mark a task done when its check failed |

**Review.** Each Opus block starts with a review of the Sonnet block before it: the Lead reads
`git diff` across that block's commits, runs `python -m pytest`, and reports anything wrong
before starting its own first task. Faults are fixed by the Lead. Block A is reviewed at the
start of B, C at the start of D, E at the start of F. Opus work is reviewed by the Owner
through each task's **Done when** result.

**When a role is stuck.** The Builder stops and says so under the rules in 3.3. The Lead stops
and asks the Owner when a task cannot meet its **Done when** check as written, or when the
only way forward changes what the project claims.

**Who does what in the `Both` tasks.**

| Task | Owner (You) | AI |
|---|---|---|
| INF-05 | Run `sam validate`, `sam build`, `sam deploy` in your terminal; paste each failure | Opus reads the failure, changes the template, says what to run next |
| INF-06 | Choose the sites and give each one's name, position and source link | Sonnet writes `data/hyderabad_sites.json` and `scripts/seed.py`; you run the script |
| INF-08 | Run each step's command; report what arrived in the inbox | Opus writes `scripts/send.py`, checks tables and executions against the expected column, diagnoses any mismatch, writes `docs/smoke-test.md` |
| DEMO-03 | Read the script aloud with a timer; change wording to your own voice | Opus writes `docs/video-script.md` from what is proven to work |
| SUB-03 | Paste the text into the form; cut to the form's limits | Opus writes the text from the README and the claim check |

---

## 4. REPO: repository hygiene

### REPO-01 · Commit the uncommitted work · AI: Sonnet · 10 min · Must
- **Goal:** Everything built so far is in history inside the event dates.
- **Steps:**
  1. `git status` and read the diff summary.
  2. Commit 1: flood workflow, notifier, state machine, template, their tests.
  3. Commit 2: engine outbox, message keys, repeated-reading guard, ordering fix, tests.
  4. Commit 3: `DESIGN.md`, `ARCHITECTURE.md` 6.3, `TASKS.md`.
  5. Push.
- **Done when:** `git status` is clean and the three commits show on GitHub.

### REPO-02 · Licence, ignore rules, secret check · AI: Sonnet · 15 min · Must
- **Goal:** The public repository is safe and reusable.
- **Files:** `LICENSE` (MIT), `.gitignore` (add `.aws-sam/`, `samconfig.toml`, `*.zip`,
  `web/config.local.js`).
- **Steps:** Add both; search history for secrets:
  `git log -p | grep -inE "aws_secret|AKIA|sk-ant|api[_-]?key"`.
- **Done when:** The search prints nothing that is a real key.
- **Risk:** If a key is found, it must be rotated by you; removing it from history is not
  enough once it has been public.

### REPO-03 · Folder layout for what is coming · AI: Sonnet · 15 min · Must
- **Goal:** Each new part has an obvious home.
- **Files:** `scripts/`, `data/`, `web/`, `samples/`, `docs/`, `layers/vision/` (each with a
  `.gitkeep`).
- **Done when:** The folders exist and the README lists them.

---

## 5. INF: running on AWS

### INF-01 · Tools on your machine · You · 30 min · Must
- **Goal:** Deployment is possible from this PC.
- **Steps:**
  1. Install AWS CLI v2 and SAM CLI (Windows installers).
  2. Open a new terminal: `aws --version`, `sam --version`.
  3. `aws sts get-caller-identity` returns the `nirmaldhara-dev` user.
- **Done when:** All three commands print a result.

### INF-02 · Deployment rights for the IAM user · You · 20 min · Must
- **Goal:** The user can create the stack.
- **Steps:**
  1. In the console, attach `AdministratorAccess` to `nirmaldhara-dev` for the event.
  2. Turn on MFA for the console login of that user and of the root account.
  3. Note a reminder to remove the policy on 12 October.
- **Done when:** `aws cloudformation list-stacks` works.
- **Risk:** Broad rights on a key stored on a laptop. Acceptable for three days; not after.

### INF-03 · Find what spent the credit · You · 15 min · Must
- **Goal:** No surprise bill while deploying.
- **Steps:** Billing → Bills → expand by service. Stop or delete whatever it is (an EC2
  instance is the likeliest). Set a budget alert at 25 USD.
- **Done when:** You know the service, and it is stopped or accepted.

### INF-04 · Move the code under `src/` · AI: Sonnet · 45 min · Must
- **Goal:** The five existing functions build from Windows without Docker, and nothing but
  their code is packaged.
- **Why:** With the code at the repository root, the build copies the whole folder (tests,
  the web app, sample photos, the virtual environment) into every function, and installs
  `numpy`, `pillow` and `anthropic` from `requirements.txt` as Windows binaries that do not
  run on Lambda. The five functions import only `boto3`, which the runtime already has, and
  the standard library.
- **Files:** `src/handlers/`, `src/nirmaldhara/` (moved with `git mv`), `pyproject.toml`,
  `requirements.txt` (deleted), `requirements-dev.txt`, `layers/vision/requirements.txt`,
  `template.yaml`, `README.md`.
- **Steps:**
  1. `git mv handlers src/handlers` and `git mv nirmaldhara src/nirmaldhara`.
  2. `pyproject.toml`: project `nirmaldhara`, setuptools, packages found under `src`.
  3. `layers/vision/requirements.txt`: `anthropic[bedrock]`, `numpy`, `pillow`.
  4. `requirements-dev.txt`: `-e .`, `-r layers/vision/requirements.txt`, `pytest`.
  5. `template.yaml`: `CodeUri: src/` in `Globals`. Handler names do not change.
  6. `README.md`: the install line becomes `python -m pip install -r requirements-dev.txt`;
     the `python -m nirmaldhara …` commands stay as they are.
  7. `python -m pip install -r requirements-dev.txt`, then `python -m pytest`.
- **Done when:** 117 tests pass; `python -m nirmaldhara check --low 15 --high 25
  --confidence 0.8` prints an answer; `src/` holds no `requirements.txt`.
- **Risk:** A test that opens a file by a path relative to the old layout. Fix the path in
  the test; do not move the file back.

### INF-05 · Validate and first deploy · Both: Opus · 1.5 h · Must
- **Goal:** The stack exists in ap-south-1.
- **Steps:**
  1. `sam validate --lint`. Fix every finding.
  2. `sam build`.
  3. `sam deploy --guided`: stack `nirmaldhara`, region `ap-south-1`, allow role creation,
     save the answers.
  4. On failure read the first `CREATE_FAILED` event, fix, delete the stack if it is in
     `ROLLBACK_COMPLETE`, repeat.
  5. Paste the stack outputs into `data/stack-outputs.json` (names only, no secrets).
- **Done when:** Status is `CREATE_COMPLETE`; five functions, three tables, two queues, one
  topic and one state machine are listed.
- **Risk, most likely first:**
  - The state machine's own start-execution permission: narrow or correct the resource.
  - `StepFunctionsExecutionPolicy` wants the state machine *name*: already given via `GetAtt`.
  - A circular reference between the reactor and the state machine: break it by passing the
    ARN through a parameter built with `!Sub`.

### INF-06 · Seed the site registry · Both: Sonnet · 1 h · Must
- **Goal:** Real Hyderabad sites are in the table.
- **Files:** `data/hyderabad_sites.json`, `scripts/seed.py`, `data/SOURCES.md`.
- **Steps:**
  1. You pick 12 to 20 known waterlogging points from published lists (municipal or traffic
     police notices, news reports). For each: id `hyd-001…`, name, latitude, longitude, the
     source link.
  2. The assistant writes `seed.py`: reads the file, writes `city, site_id, name, lat, lon,
     rain_threshold_mm` with a condition that leaves an existing item's engine attributes
     alone.
  3. Run it. Wait for the next rain run or invoke the rain function by hand.
- **Done when:** A table scan shows the sites, and the engine queue received one rain message
  per site (CloudWatch metric or the function's return value).
- **Tests:** `seed.py` run twice changes nothing the second time.
- **Risk:** Invented locations. Every row needs a source, or it is left out.

### INF-07 · Subscribe to the alerts topic · You · 10 min · Must
- **Goal:** Alerts are visible on a real device.
- **Steps:** Console → SNS → the alerts topic → create an email subscription → confirm from
  your inbox.
- **Done when:** A test publish from the console arrives.

### INF-08 · Smoke test on AWS · Both: Opus · 1 h · Must
- **Goal:** The whole chain is proven on real services, including the database conditions the
  tests only imitate.
- **Files:** `scripts/send.py` (rain or reading to the queue, with group and deduplication
  ids), `docs/smoke-test.md` (what was run and what was seen).
- **Steps and expected result:**

  | Step | Expect |
  |---|---|
  | Rain index 25 to `hyd-001` | Site WATCH; a flood item; an execution named `hyd-001-<start>`; one photo request email |
  | Reading 16 cm, guardian | WARNING; four alert emails |
  | Readings 24, 28 cm | CRITICAL; closure recommendation |
  | The same reading sent again | No change in `readings`; no new email |
  | Wait 5 min without acknowledging | A second closure-recommendation email; the `Alerts` table holds an item whose id ends `#1#closure_recommendation` |
  | Readings falling to 8, 6 cm | RECEDING, then CLEAR; `EventClosed`; execution ends |

- **Done when:** Every row matches, and `docs/smoke-test.md` records it with times.
- **Risk:** A condition expression that the fakes accepted and DynamoDB rejects. This is the
  point of the task; fix and add the case to the tests.

---

## 6. MOD: the model and its evidence

### MOD-01 · Decide the model route · You · 10 min · Must
- **Goal:** One route is chosen, so work is not blocked on a support queue.
- **Steps:** Check the support case and the account email. Try
  `python -m nirmaldhara read samples/<any>.jpg`. If it still fails, choose the fallback.
- **Deadline:** 6 PM on 9 October.
- **Done when:** You have said "Bedrock" or "fallback" in the chat. No answer by the deadline
  counts as "fallback".

### MOD-02 · Second client path in the reader · AI: Sonnet · 45 min · Conditional
- **Condition:** Done only if MOD-01 ends in "fallback". If it ends in "Bedrock", skip it.
- **Goal:** The reader works with either route, chosen by one setting.
- **Files:** `src/nirmaldhara/reader.py`, `tests/test_reader.py`, `README.md`.
- **Steps:**
  1. `NIRMALDHARA_PROVIDER` = `bedrock` (default) or `anthropic`.
  2. For `anthropic`: the standard client, key read from `ANTHROPIC_API_KEY` in the
     environment, model from `NIRMALDHARA_MODEL`.
  3. Same request, same schema, same error handling.
  4. README and writeup: say which route the demo used and what that means for the
     in-country claim.
- **Done when:** One real photo returns a range through the chosen route.
- **Tests:** The existing six, run for both providers with the stand-in client.
- **Risk:** The key must never be typed into this chat or committed. You set it in your own
  terminal.

### MOD-03 · Sample photos with labels · You · 1 h · Must
- **Goal:** Evidence that depth reading works at all.
- **Files:** `samples/*.jpg`, `samples/labels.csv` (`file, band_low, band_high, object_used,
  moving, source, licence`), `samples/SOURCES.md`.
- **Steps:**
  1. 12 to 15 photos: your own, or openly licensed with the licence written down.
  2. Cover the range: dry, ankle, shin, knee, above; day and night; one with nothing of known
     size in the water.
  3. Label each by the wheel or knee rule in METHOD 6 **before** running the model.
  4. Add two or three photos of a roadside drain inlet, partly blocked, to
     `samples/inlets/` with their source and licence. MOD-05 and ENV-03 use them.
- **Done when:** The CSV has a row per photo.
- **Risk:** News photos are usually not free to reuse. If in doubt, keep the file out of the
  repository and list only its address.

### MOD-04 · Evaluation script and table · AI: Sonnet · 1 h · Must
- **Status, 9 Oct:** the script and its tests are built and have been run **simulated**, on 22 drawn
  scenes with a stand-in reader (`docs/evaluation-simulated.md`). That proves the tool, not the
  model. The real run, which writes `EVALUATION.md`, still needs MOD-01 and the photos from MOD-03.
- **Goal:** A number, with its limits stated.
- **Files:** `scripts/evaluate.py`, `EVALUATION.md`, `data/eval-results.json`.
- **Steps:**
  1. Run the reader on each photo; store the raw answers.
  2. Report: exact band agreement; within one band; `cannot_tell` count; **dangerous misses**
     (model's top of range below the car limit while the label says at or above it).
  3. Show every photo's row, not only the totals.
- **Done when:** `EVALUATION.md` gives the table, the sample size, and this sentence or its
  equal: "Labels are one person's reading of the photo, not measured depth."

### MOD-05 · Inlet blockage instruction · AI: Opus · 1 h · Should
- **Status, 9 Oct: not done.** Needs a working model route (MOD-01) and inlet photos (MOD-03).
- **Goal:** The same reader can estimate how blocked a drain inlet is.
- **Files:** `src/nirmaldhara/reader.py` (`read_inlet`), schema `{inlet_visible, blocked_share_low,
  blocked_share_high, material: [plastic, leaves, silt, debris], confidence, cannot_tell}`,
  tests with the stand-in.
- **Done when:** Two or three inlet photos return a blocked share, stored for ENV-03.
- **Risk:** Not validated against anything. Present as a worked example only.

---

## 7. PIPE: photo to reading

### PIPE-01 · Buckets and the capture key · AI: Sonnet · 30 min · Should
- **Files:** `template.yaml`: `RawBucket` (1-day expiry, no public access), `FramesBucket`
  (3-day expiry), a secret for the link-signing key.
- **Done when:** Deployed; both buckets are private.

### PIPE-02 · Upload endpoint · AI: Opus · 1 h · Should
- **Goal:** A phone with a valid capture link can upload one photo.
- **Files:** `src/handlers/upload.py`, `template.yaml` (HTTP API route `POST /uploads`).
- **Steps:**
  1. Body: `{token, lat, lon}`. `tokens.verify(key, token, "capture", now)`.
  2. Record the nonce with a conditional put; a second use is refused.
  3. Return a presigned PUT for `raw/{site}/{nonce}.jpg`, valid 5 minutes, with the site,
     subject, position and request time as object metadata.
  4. Allow cross-origin `POST` from the CloudFront address only.
- **Done when:** `curl` with a good token gets a URL; a reused or altered token gets 403.
- **Tests:** Good, expired, wrong purpose, reused, altered.

### PIPE-03 · Intake function · AI: Opus · 1.5 h · Should
- **Goal:** A raw photo is checked, cropped, blurred and replaced.
- **Files:** `src/handlers/intake.py`, `template.yaml` (S3 trigger on `raw/`, layer `VisionDeps`).
- **Steps:** Read object and metadata → `intake.check` → on a reason other than OK, delete and
  publish `ReadingRejected` with the reason → Rekognition `DetectFaces` and `DetectText` →
  `blur_boxes` → write to the frames bucket → delete the raw object.
- **Done when:** A photo with a face lands in the frames bucket with the face blurred, and
  the raw object is gone.
- **Tests:** With a fake Rekognition: boxes are scaled from ratios to pixels correctly; a
  rejected photo is never written.
- **Risk:** The layer `VisionDeps` (from `layers/vision/requirements.txt`) must be built for
  Linux with `sam build --use-container`, which needs Docker on your machine. If the layer is
  not built within 30 minutes, stop PIPE-01 to PIPE-05 and do PIPE-06.

### PIPE-04 · Vision function · AI: Sonnet · 1 h · Should
- **Goal:** A cleaned frame becomes a reading on the engine queue.
- **Files:** `src/handlers/vision.py`, `template.yaml` (queue trigger, layer `VisionDeps`).
- **Steps:** `read_depth` → if `cannot_tell`, count a metric and stop → `Reading(ts=receive
  time, low, high, confidence, source, device)` → send to the queue, group = site,
  deduplication id = the photo's hash.
- **Done when:** Uploading a flood photo moves the site's state within a minute.
- **Tests:** `cannot_tell` sends nothing; source and device come from the token's subject.

### PIPE-05 · Capture page · AI: Sonnet · 45 min · Should
- **Goal:** The page a guardian opens from a photo request.
- **Files:** `web/capture.html`.
- **Steps:** Reads the token from the address; asks for position; opens the camera with
  `<input type="file" accept="image/*" capture="environment">`; uploads; shows "received" or
  the plain reason it was refused. Styled from the same tokens as the map.
- **Done when:** On your phone, a link leads to a photo arriving in the bucket.

### PIPE-06 · Photo to reading by script · AI: Sonnet · 30 min · Fallback
- **Status, 9 Oct:** `scripts/photo.py` is built and tested, and works with the simulated reader on the
  drawn scenes. With a real model route it needs no change. Sending a simulated reading to the real
  queue needs `--simulated-ok`.
- **Condition:** Done unless the upload-pipeline rule in 13.4 releases PIPE-01 to PIPE-05.
- **Goal:** Photos still become readings in the demo, by script.
- **Files:** `scripts/photo.py`: runs the reader locally on a file and sends the reading to
  the queue.
- **Done when:** `python scripts/photo.py samples/x.jpg hyd-003` moves the site on the map.
- **Say in the writeup:** intake, blur and upload are built as tested functions and designed
  as a pipeline, and were not deployed.

---

## 8. PUB: data the screens read

### PUB-01 · Add confidence to the map file · AI: Sonnet · 20 min · Must
- **Why:** The browser cannot give a passability answer without it: the rule needs confidence
  of at least 0.6, and the file has no confidence column today.
- **Files:** `src/nirmaldhara/publish.py` (column `c`), `tests/test_design.py`, `DESIGN.md` 15.3, `data/sample-map.json`.
- **Steps:** Add the column; re-measure the size table in `DESIGN.md` 15.3; write
  `data/sample-map.json` with eight sites covering every state, an unconfirmed reading and a
  stale one. The web tasks are built against this file until PUB-02 is deployed.
- **Done when:** The tests pass with the new column and the sample file loads with
  `json.load`.

### PUB-02 · Publisher function · AI: Sonnet · 45 min · Must
- **Files:** `src/handlers/publisher.py`, `template.yaml` (`PublicBucket`; rule on
  `SiteStateChanged` and `ReadingAccepted`).
- **Steps:** Query the city's sites (name, position, `doc`); build with
  `publish.city_document`; write `data/hyderabad.json` with `Cache-Control: max-age=15` and
  gzip.
- **Done when:** Sending a reading changes the file within seconds.
- **Tests:** Sites without a position are left out; an unchanged city still writes a valid
  file.

### PUB-03 · Flood history file · AI: Sonnet · 45 min · Should
- **Goal:** The repeat offenders view has data.
- **Files:** `src/handlers/history.py`, `template.yaml` (rule on `EventClosed`).
- **Steps:** Query each site's closed floods; write `data/hyderabad-floods.json`: per site,
  count, total minutes blocked for cars and two-wheelers, highest peak, and the list of
  floods with start, end, peak.
- **Done when:** After a replay the file lists the flood that just closed.

### PUB-04 · Hosting · AI: Sonnet · 45 min · Must
- **Files:** template: CloudFront distribution in front of `PublicBucket` with origin access
  control; `scripts/deploy_web.py` (sync `web/`).
- **Done when:** The map opens on your phone from a public HTTPS address. CloudFront was
  refused (account not verified, 9 Oct), so a Lambda function URL serves it until Support
  clears that; see DESIGN.md.
- **Risk:** A new distribution takes several minutes to become reachable. Start it early.

---

## 9. WEB: resident map

No framework and no build step: plain HTML, CSS and JavaScript modules in `web/`.

### WEB-01 · Design tokens and base styles · AI: Opus · 40 min · Must
- **Files:** `web/tokens.css` (palette, type scale, spacing 4/8/16/24/40, radii, durations),
  `web/base.css`, fonts.
- **Steps:** Write the two style sheets; add `.claude/launch.json` with one entry that serves
  `web/` on port 8080 with `python -m http.server`, so every web task is checked in the
  browser pane.
- **Done when:** A page `web/styleguide.html` shows every colour with its name and contrast
  ratio, the type scale, and the hairline and grain.
- **Tests:** Each text and background pair in use meets 4.5 to 1; computed in a small script
  and printed in the style guide.

### WEB-02 · Rules in the browser · AI: Sonnet · 40 min · Must
- **Goal:** One set of answers in Python and JavaScript.
- **Files:** `web/rules.js` (`bandFor`, `answerFor`, `passability`), `data/rule-cases.json`
  generated from `bands.py`, `tests/test_rules_match.py`.
- **Steps:** Generate about 400 cases from Python (every 2 cm, four confidences, each class).
  A small Node-free check loads `rules.js` in the browser test page and compares; the Python
  test checks the file matches `bands.py`.
- **Done when:** `web/rules-check.html` shows "400 of 400".
- **Risk:** Without this the two rule sets drift, and the map says "passable" where the alert
  says "not safe".

### WEB-03 · The map ground · AI: Opus · 1 h · Must
- **Files:** `web/index.html`, `web/map.js`, `web/style.json`.
- **Steps:**
  1. First 10 minutes: open the OpenFreeMap terms page. If it states that no key is needed
     and public use is allowed, use its vector tiles. Otherwise use the SVG route in step 3.
     Record the decision and the page address in `web/CREDITS.md`.
  2. Tile route: MapLibre with a style cut down to ground, lakes, main roads and a few
     labels, all in the Line and Night colours. Bounds locked to Hyderabad.
  3. SVG route: `web/hyderabad.svg` with the city outline, the Musi river, Hussain Sagar and
     the ring roads traced from OpenStreetMap data, with credit; sites placed by a linear
     map from latitude and longitude to the drawing's box.
- **Done when:** The city reads as a quiet night print at 360 px wide, and `web/CREDITS.md`
  names the map data's source and licence.

### WEB-04 · The depth glyph · AI: Opus · 1.5 h · Must
- **Files:** `web/glyph.js`.
- **Spec:**

  | Part | Rule |
  |---|---|
  | Size | 28 px on the map, 44 px touch target |
  | Scale | 0 to 60 cm maps to the circle's height; above 60 is full |
  | Solid fill | to the low end of the range |
  | Light band | from the low end to the high end |
  | Surface | a sine path, amplitude 1.5 px, drifting 6 s per cycle |
  | Colour | Shallow under 12 cm, Water 12 to 30, Deep above 30 |
  | Unconfirmed | dashed outline |
  | Critical | 2.5 px Signal ring (the watch ring is 1 px) |
  | Watch, no water | empty circle with a slow pulse on the outline |
  | Stale (over 30 min) | 50% opacity |
  | Change | fill animates 800 ms ease-out |

- **Done when:** `web/glyph-gallery.html` shows every state side by side, and they can be
  told apart in greyscale.

### WEB-05 · Live data on the map · AI: Sonnet · 45 min · Must
- **Files:** `web/data.js`.
- **Steps:** Fetch `data/hyderabad.json` from the same origin (locally, a copy of
  `data/sample-map.json` at that path) every 20 s; diff by site id; update only glyphs that changed;
  on a fetch failure keep the last data and show "last updated 3 min ago" in Signal.
- **Done when:** Running `scripts/send.py` makes a glyph fill without a reload.

### WEB-06 · The site sheet · AI: Opus · 1.5 h · Must
- **Files:** `web/sheet.js`, `web/sheet.css`.
- **Content, top to bottom:** name (display type) · range as the one large number
  ("14–19 cm") with the band in words · the sentence ("Not safe for bikes, scooters, autos
  and cars") · the cross-section drawing · five rows: bikes and scooters, autos, cars, SUVs,
  people on foot, each with a word and a mark, never colour alone · "seen 6 min ago" and
  "from one unconfirmed photo" when so · a line that never changes: "Do not enter moving
  water at any depth."
- **Done when:** For five ranges the sheet's answers equal
  `python -m nirmaldhara check` for the same input.

### WEB-07 · Cross-section drawing · AI: Opus · 1 h · Should
- **Files:** `web/section.js`, three outline drawings (car, scooter, person) as inline SVG to
  a common scale: car wheel 62 cm, scooter wheel 43 cm, knee 46 cm.
- **Steps:** Water band drawn across all three at the range; the wave line on top; each
  class's limit marked as a fine tick with its number.
- **Done when:** At 20 cm the water visibly reaches a third of the car's wheel.

### WEB-08 · First-open and empty states · AI: Sonnet · 30 min · Should
- **Steps:** A three-line welcome on first open; "No water reported in Hyderabad right now"
  with the rain outlook when all sites are clear; a legend reachable from one button.
- **Done when:** With an empty map file the page is still worth looking at.

### WEB-09 · Accessibility and phone check · AI: Sonnet · 40 min · Must
- **Steps:** Keyboard reach for every site and the sheet; labels read out as "Malakpet
  underpass, warning, 14 to 19 centimetres, seen 6 minutes ago"; reduced motion; 360 px wide;
  one-hand reach for the sheet handle.
- **Done when:** The page can be used with the keyboard alone and at 360 px.

### WEB-10 · Installable and offline last-known · AI: Sonnet · 45 min · Could
- **Files:** `web/manifest.json`, `web/sw.js`.
- **Steps:** Cache the shell and the last map file; when offline show the last data with its
  age in Signal.
- **Done when:** In aeroplane mode the map opens and says how old its data is.

---

## 10. ENV: environment views

### ENV-01 · Repeat offenders page · AI: Sonnet · 1.5 h · Should
- **Files:** `web/offenders.html`, `web/offenders.js`.
- **Design:** One row per site, ordered by minutes blocked. Each row: name, floods in the
  period, hours blocked, highest peak, and a strip of small vertical marks, one per flood,
  height by peak depth, in the blues. No bar chart chrome.
- **Done when:** After two replays the order and numbers match the Floods table.

### ENV-02 · What the record implies · AI: Opus · 45 min · Should
- **Status, 9 Oct: not done, on purpose.** It draws a site's typical time to flood and its drainage
  rate from recorded floods. No real flood has been recorded, and the only records are from a
  scripted replay, so any figure would describe the script, not a place. Do it once real floods exist.
- **Goal:** Turn "it floods often" into a statement an engineer could act on.
- **Steps:** For the top site, from its recorded floods: typical time from watch to 20 cm,
  typical duration, and the drawdown rate from the receding readings (cm per minute), which
  is the site's effective drainage. Shown with the readings it came from.
- **Done when:** The page shows the figure and the count of floods behind it, and says when
  the count is too small to mean much.

### ENV-03 · Blocked inlet worked example · AI: Opus · 1.5 h · Should
- **Status, 9 Oct: not done.** Depends on MOD-05.
- **Files:** `web/inlet.html`, `src/nirmaldhara/inlet.py` (capacity from METHOD 16.10),
  `tests/test_inlet.py`.
- **Steps:** For one inlet photo: the blocked share from MOD-05; clear and current capacity by
  the smaller of weir and orifice flow; the forecast rain's runoff for a stated catchment;
  the action ("clearing this inlet restores about X litres a second") with every input
  listed and its source.
- **Done when:** A reader can redo the sum by hand from the page.
- **Tests:** Capacity is zero when fully blocked, equals the clear value at zero, and never
  rises as the blocked share rises.
- **Risk:** The catchment area is an assumption. Label it as one.

### ENV-04 · Change gate demonstration · AI: Sonnet · 45 min · Could
- **Files:** `scripts/gate_demo.py`, a short clip you record of any street.
- **Steps:** Run `ChangeGate` over the clip's frames; report frames seen, frames sent, and the
  share saved; show the sent frames on a strip.
- **Done when:** One image and one sentence: "of N frames, M were sent".

---

## 11. DEMO: replay and video

### DEMO-01 · Scenario file · AI: Sonnet · 30 min · Must
- **Files:** `data/scenarios/evening.json`: time-stamped rain indexes and readings for four
  sites over 90 minutes: one that reaches CRITICAL and recedes, one WARNING held by an
  unconfirmed resident photo, one dry watch that ends, one that stays clear.
- **Done when:** Fed through the pure functions in a test, the four sites end in the states
  the file says.
- **Tests:** `tests/test_scenario.py` runs the file against `apply_rain`/`apply_reading`.

### DEMO-02 · Replay script · AI: Sonnet · 45 min · Must
- **Files:** `scripts/replay.py` (`--speed 45` plays 90 minutes in 2), `scripts/reset.py`
  (returns the demo sites to CLEAR and closes open floods).
- **Done when:** `reset` then `replay` gives the same map twice in a row.
- **Limit, decided:** Alerts repeat on a 20-minute clock and escalate on a 5-minute clock in
  real time, so a sped-up replay shows neither. No demo-only setting is added to change
  that. The video shows the first alerts from the replay and the escalation email from the
  INF-08 record.

### DEMO-03 · Script and shot list · Both: Opus · 45 min · Must
- **Files:** `docs/video-script.md`.
- **Shots:**

  | Time | Screen | Words |
  |---|---|---|
  | 0:00–0:20 | Map at night, empty | The problem in one sentence; who is hurt |
  | 0:20–0:45 | Replay starts; a glyph pulses | Forecast starts a watch before any water |
  | 0:45–1:15 | A photo; glyph fills; the sheet | Depth as a range; per-vehicle answer |
  | 1:15–1:35 | Inbox | Alerts once each; closure waits for a trusted source |
  | 1:35–2:00 | AWS console: queue, execution, tables | What runs where |
  | 2:00–2:35 | Repeat offenders; inlet example | The environmental case |
  | 2:35–2:55 | Evaluation table; limits | What is proven; what is next |

- **Done when:** Read aloud with a timer, it is under 2:50.

### DEMO-04 · Record · You · 1 h · Must
- **Steps:** One take per shot; 1080p; browser zoom so text is readable on a phone; voice
  recorded separately if the room is noisy.
- **Done when:** Seven clips exist.

### DEMO-05 · Edit and upload · You · 45 min · Must
- **Done when:** Under 3:00; uploaded; the link opens in a private window; visibility is what
  the form requires.

---

## 12. SUB: submission

### SUB-01 · README · AI: Sonnet · 45 min · Must
- **Sections:** what it does (five lines) · the picture · try it (the public address) · run
  the tests · deploy · **built and running / built and tested / designed** table · limits ·
  AI tools used · sources.
- **Done when:** A stranger can run the tests from the README alone.

### SUB-02 · Architecture picture · AI: Sonnet · 30 min · Should
- **Files:** `docs/architecture.svg` in the product's palette.
- **Done when:** It shows only what is deployed, with designed parts drawn dashed.

### SUB-03 · Writeup for the form · Both: Opus · 30 min · Must
- **Content:** problem, approach, AWS services used and for what, AI tools used and for what,
  what is unproven.
- **Done when:** It fits the form's limits and matches the README's claims.

### SUB-04 · Claim check · AI: Opus · 30 min · Must
- **Steps:** Read the README, writeup and video script; for each claim find the test, the
  smoke-test row, or the evaluation row that supports it; reword or remove the rest.
- **Done when:** `docs/claims.md` lists each claim with its support.

### SUB-05 · Submit · You · 20 min · Must
- **Done when:** You hold the confirmation. Before the last hour.

### SUB-06 · After the event · You · 15 min · Must
- **Steps:** Remove `AdministratorAccess`; rotate the access key; delete the stack if you are
  not keeping it; check the bill.
- **Done when:** `aws iam list-attached-user-policies --user-name nirmaldhara-dev` no longer
  lists `AdministratorAccess`, and the old access key shows as deleted.

### SUB-07 · Bring DESIGN.md up to date · AI: Sonnet · 30 min · Should
- **Goal:** The design document describes the code as submitted.
- **Steps:** Section 1 (new modules and their status), 15 (new handlers and functions),
  18 (test counts from `pytest --collect-only`), 17.2 (close what INF-08 proved; add what it
  found). Paths changed by INF-04.
- **Done when:** Every file under `src/` appears in section 1, and the test total equals the
  collected count.

### SUB-08 · Confirm the closing time and the video rules · You · 10 min · Must
- **Goal:** The plan's dates rest on the event's real deadline, not on an assumption.
- **Deadline:** 6 PM on 9 October.
- **Steps:** On the event page or its Discord, find when the submission form closes, the
  video's length limit, and the YouTube visibility it requires. Say all three in the chat.
- **Done when:** The three facts are in the chat. If the form closes before noon on
  11 October, every time in 13.3 and 13.4 moves earlier by the same number of hours.

---

## 13. Priority, order and switching

### 13.1 Priority

| Priority | Count | Work | Tasks |
|---|---|---|---|
| Must | 35 | 23.2 h | REPO-01, REPO-02, REPO-03, INF-01, INF-02, INF-03, INF-04, INF-05, INF-06, INF-07, INF-08, MOD-01, MOD-03, MOD-04, PUB-01, PUB-02, PUB-04, WEB-01, WEB-02, WEB-03, WEB-04, WEB-05, WEB-06, WEB-09, DEMO-01, DEMO-02, DEMO-03, DEMO-04, DEMO-05, SUB-01, SUB-03, SUB-04, SUB-05, SUB-06, SUB-08 |
| Should | 14 | 12.8 h | MOD-05, PIPE-01, PIPE-02, PIPE-03, PIPE-04, PIPE-05, PUB-03, WEB-07, WEB-08, ENV-01, ENV-02, ENV-03, SUB-02, SUB-07 |
| Could | 2 | 1.5 h | WEB-10, ENV-04 |
| Conditional | 1 | 0.8 h | MOD-02 |
| Fallback | 1 | 0.5 h | PIPE-06 |

Of the Must work, 4.9 h is yours alone, 4.8 h is done
together, and 13.5 h is the assistant's. Yours and the assistant's run at the same
time.

### 13.2 What each task needs first

The only place dependencies are stated. A task starts when every task in its row is done.

| Task | Owner | Needs |
|---|---|---|
| REPO-01 | AI: Sonnet | nothing |
| REPO-02 | AI: Sonnet | REPO-01 |
| REPO-03 | AI: Sonnet | REPO-01 |
| INF-01 | You | nothing |
| INF-02 | You | nothing |
| INF-03 | You | nothing |
| INF-04 | AI: Sonnet | REPO-03 |
| INF-05 | Both: Opus | INF-01, INF-02, INF-03, INF-04 |
| INF-06 | Both: Sonnet | INF-05 |
| INF-07 | You | INF-05 |
| INF-08 | Both: Opus | INF-06, INF-07 |
| MOD-01 | You | nothing |
| MOD-02 | AI: Sonnet | MOD-01, INF-04 |
| MOD-03 | You | nothing |
| MOD-04 | AI: Sonnet | MOD-01, MOD-03, and MOD-02 if it applies |
| MOD-05 | AI: Opus | MOD-01, and MOD-02 if it applies |
| PIPE-01 | AI: Sonnet | INF-05 |
| PIPE-02 | AI: Opus | PIPE-01 |
| PIPE-03 | AI: Opus | PIPE-01 |
| PIPE-04 | AI: Sonnet | PIPE-03, MOD-01 |
| PIPE-05 | AI: Sonnet | PIPE-02, WEB-01, PUB-04 |
| PIPE-06 | AI: Sonnet | INF-08, MOD-01, and MOD-02 if it applies |
| PUB-01 | AI: Sonnet | INF-04 |
| PUB-02 | AI: Sonnet | PUB-01, INF-05 |
| PUB-03 | AI: Sonnet | INF-08 |
| PUB-04 | AI: Sonnet | INF-05 |
| WEB-01 | AI: Opus | REPO-03 |
| WEB-02 | AI: Sonnet | INF-04 |
| WEB-03 | AI: Opus | WEB-01 |
| WEB-04 | AI: Opus | WEB-01 |
| WEB-05 | AI: Sonnet | WEB-03, WEB-04, PUB-01 |
| WEB-06 | AI: Opus | WEB-02, WEB-05 |
| WEB-07 | AI: Opus | WEB-06 |
| WEB-08 | AI: Sonnet | WEB-05 |
| WEB-09 | AI: Sonnet | WEB-06 |
| WEB-10 | AI: Sonnet | WEB-05, PUB-04 |
| ENV-01 | AI: Sonnet | PUB-03, WEB-01 |
| ENV-02 | AI: Opus | ENV-01 |
| ENV-03 | AI: Opus | MOD-05, WEB-01 |
| ENV-04 | AI: Sonnet | INF-04, and a street clip from you |
| DEMO-01 | AI: Sonnet | INF-04 |
| DEMO-02 | AI: Sonnet | DEMO-01, INF-08 |
| DEMO-03 | Both: Opus | DEMO-02, WEB-06 |
| DEMO-04 | You | DEMO-03, PUB-02, PUB-04 |
| DEMO-05 | You | DEMO-04 |
| SUB-01 | AI: Sonnet | INF-08 |
| SUB-02 | AI: Sonnet | INF-05, WEB-01 |
| SUB-03 | Both: Opus | SUB-01 |
| SUB-04 | AI: Opus | SUB-01, SUB-03, DEMO-03 |
| SUB-05 | You | DEMO-05, SUB-04, REPO-02 |
| SUB-06 | You | SUB-05 |
| SUB-07 | AI: Sonnet | INF-08 |
| SUB-08 | You | nothing |

### 13.3 Run sheet

The order of work and the model for each stretch. Tasks in a block are done left to right.
**Switch model only at a block boundary**, or under the two "switching up" rules in 3.3.

| Block | Model | Tasks, in order | Work | You, during this block |
|---|---|---|---|---|
| A | **Sonnet 5.5** | REPO-01 → REPO-02 → REPO-03 → INF-04 → PUB-01 → WEB-02 → DEMO-01 → MOD-02 | 3.7 h | INF-01, INF-02, INF-03, MOD-01, SUB-08, MOD-03 |
| B | **Opus 5.5** | WEB-01 → WEB-03 → WEB-04 → INF-05 | 4.7 h | Run the deploy commands in INF-05; pick the sites for INF-06 |
| C | **Sonnet 5.5** | INF-06 → PUB-02 → PUB-04 → WEB-05 | 3.2 h | INF-07; run the seed and deploy commands |
| D | **Opus 5.5** | INF-08 → WEB-06 → MOD-05 → ENV-03 → WEB-07 | 6 h | Run the INF-08 steps and report what arrives; run MOD-05 on the inlet photos |
| E | **Sonnet 5.5** | DEMO-02 → MOD-04 → PIPE-06 → PUB-03 → ENV-01 → WEB-08 → WEB-09 → SUB-01 → SUB-02 → SUB-07 | 7.4 h | Check the map on your phone; run MOD-04 |
| F | **Opus 5.5** | ENV-02 → DEMO-03 → SUB-03 → SUB-04 | 2.5 h | Read DEMO-03 aloud with a timer; then DEMO-04, DEMO-05, SUB-05, SUB-06 |

- Block A: MOD-02 is done only if MOD-01 ended in "fallback"; otherwise skip it. If MOD-01
  has no answer yet when block A reaches MOD-02, MOD-02 moves to the start of block C.
- Block D: checkpoint 2 falls after WEB-06. Its answer decides whether MOD-05, ENV-03 and
  WEB-07 are done.
- The run sheet holds every Must task that an AI does, plus these others: MOD-02, MOD-05, ENV-03, WEB-07, PIPE-06, PUB-03, ENV-01, WEB-08, SUB-02, SUB-07, ENV-02.
  With your own tasks it comes to 32.4 h of work: 14.3 h on Sonnet,
  13.2 h on Opus, the rest yours.
- Not on the run sheet: PIPE-01, PIPE-02, PIPE-03, PIPE-04, PIPE-05, WEB-10, ENV-04. They are done only under 13.4.

Target times: A and B on 9 October. C, then INF-08 and WEB-06, by 1 PM on 10 October. The
rest of D, and E, by 6 PM. F by 9 PM, with DEMO-03 written by 8 PM. SUB-05 on the morning of
11 October.

The estimates add up to more than those hours hold. That is deliberate: the checkpoints
below remove work in a fixed order when the clock says so, so nothing has to be decided
under pressure.

### 13.4 Checkpoints

Each is a decision with one rule. Nothing else changes the plan.

| When | Question | If yes | If no |
|---|---|---|---|
| 1 · 9 Oct, 6 PM | Is INF-05 done? | Carry on with block C | All AI work stops except INF-05 until it is done. MOD-01 defaults to "fallback" |
| 2 · 10 Oct, 1 PM | Are INF-08 and WEB-06 done, with a glyph filling on the public map when `scripts/send.py` sends a reading? | Carry on with the run sheet | Skip every Should that has not started. Do the remaining Must tasks in run-sheet order, each on the model in its heading |
| 3 · 10 Oct, 8 PM | Does DEMO-03 exist? | Record (DEMO-04) | Stop building. Opus writes DEMO-03 from what works now; you record |

**The upload pipeline.** PIPE-01 to PIPE-05 are done only if block E is finished, apart from
PIPE-06, before 3 PM on 10 October. Then: PIPE-01 on Sonnet, PIPE-02 → PIPE-03 on Opus,
PIPE-04 → PIPE-05 on Sonnet, and PIPE-06 is skipped. Otherwise PIPE-06 is done and the five
are not.

**The Could tasks.** WEB-10 and ENV-04 are done on Sonnet only if block F is finished before
8 PM on 10 October.

### 13.5 What can be submitted at each stopping point

| Stopped after | Submission |
|---|---|
| INF-08 | An alerting back end running on AWS, shown through the console and an inbox |
| WEB-06 | The above with a public map. The least worth aiming for |
| ENV-03 | Safety and environment both shown |

---

## 14. After submission

Not part of this plan's two days. Each row is described where the second column points; all
are Opus tasks under rule 3.3, except the two marked Sonnet.

| Task | Described in | Time |
|---|---|---|
| Sweep for stored events on the dead-letter alarm | DESIGN.md 17.2 item 1 | 45 min |
| `AlertFailed` and resend | DESIGN.md 17.2 item 3 | 1 h |
| Failure counter in the timer loop | DESIGN.md 17.2 item 4 | 30 min |
| Engine and workflow tests against DynamoDB Local | DESIGN.md 17.2 item 5 | 1.5 h |
| Acknowledge link for officials | DESIGN.md 16.4 | 1.5 h |
| Telegram channel (Sonnet) | DESIGN.md 16.5 | 1.5 h |
| Telugu and Hindi templates, checked by a native speaker (Sonnet) | DESIGN.md 17.2 item 8 | 1 h plus review |
| Official console | Section 2.6 of this file | 3 h |
| Agent wording with Strands | DESIGN.md 16.6 | 2 h |
