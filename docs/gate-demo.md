# Change gate on real footage

The camera change gate (`src/nirmaldhara/change.py`) decides which frames a camera sends. It learns
each camera's own noise and sends a frame only when the scene has changed and then settled. This is
the first time it has run on real video; before this it had only seen synthetic frames.

Run on 10 October 2026 with `python scripts/gate_demo.py --all`, on three licensed news clips of
flooding in Hyderabad cut to two frames a second. Credits and licences:
[samples/footage/CREDITS.md](../samples/footage/CREDITS.md).

| Clip | Frames seen | Frames sent | Never left the camera |
|---|---|---|---|
| Siasat Daily, 2015, 1:33 | 186 | 23 | 88% |
| Sakshi TV, 2019, 2:20 | 280 | 51 | 82% |
| NAYA NEWS, 2020, 1:04 | 129 | 12 | 91% |

## How to read this

- **These figures understate the saving.** The clips are edited news footage, a string of short
  shots. Every cut is a new scene, and the gate is right to send it. A fixed camera has no cuts, so
  it would send fewer.
- **Close traffic may still get through.** In the Siasat Daily clip the gate sent five frames
  between seconds 50 and 56, while an auto and a motorcycle filled the frame in a close shot. The
  design means a passing vehicle to be ignored; whether these sends were cuts or vehicles was not
  separated, so that behaviour is not confirmed here.
- **It is a count, not a judgment of usefulness.** Nothing here checks that the frames sent are the
  ones a flood reading would want.

## What it does not show

- A real fixed camera over hours, at night, in heavy rain or with auto-exposure hunting. The
  thresholds were measured on synthetic frames (ARCHITECTURE.md 13.5) and now on about five minutes of
  daytime news footage, which is still far short of that.
- Anything about depth. No frame was read by the photo reader.

## Run it yourself

The video files are not in the repository. Put any clip's frames in a folder and run:

```
ffmpeg -i clip.mp4 -vf "fps=2,scale=640:-2" samples/footage/frames/mine/%05d.jpg
python scripts/gate_demo.py samples/footage/frames/mine --fps 2
```

It prints the sentence "of N frames, M were sent" and writes a strip of the sent frames to
`docs/gate-demo/`, which is also kept out of the repository.
