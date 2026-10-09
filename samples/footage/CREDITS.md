# Footage: credits and licences

Three clips of flooding in Hyderabad, used only to exercise the camera change gate
(`scripts/gate_demo.py`, results in [docs/gate-demo.md](../../docs/gate-demo.md)).

**The video files and the frames cut from them are not in this repository.** They are kept out by
`.gitignore`: the frames show people's faces, and this project's own rule is that faces are blurred
before anything is stored. Only counts and times derived from them are published here.

Each video's own YouTube page showed "Creative Commons Attribution license (reuse allowed)" when
checked on 10 October 2026.

| File | Title | Channel | Published | Length | Link | Licence |
|---|---|---|---|---|---|---|
| `030j7lSZ3cY.mp4` | Rain Lashes in Hyderabad, Road turns into river | Siasat Daily | 10 Sep 2015 | 1:33 | https://www.youtube.com/watch?v=030j7lSZ3cY | CC BY |
| `izJR0sCbfPg.mp4` | Rain leaves Hyderabad roads flooded | Sakshi TV | 30 Sep 2019 | 2:20 | https://www.youtube.com/watch?v=izJR0sCbfPg | CC BY |
| `kS2ivWlwSyo.mp4` | Heavy Flood Water in Uppal Area, Heavy Rain in Hyderabad, Cars Sinking | NAYA NEWS | 15 Oct 2020 | 1:04 | https://www.youtube.com/watch?v=kS2ivWlwSyo | CC BY |

## What each is, and how far the licence can be trusted

- **Siasat Daily, 2015.** The channel's own camera work: the video ends with a camera and editing
  credit. Shallow waterlogging on a main road with autos, two-wheelers, cars and people walking
  through it. The most useful of the three, and the one whose licence is clearest.
- **Sakshi TV, 2019.** An edited montage of flooded colonies and roads with captions over it. Some
  shots may have been sent in by viewers, whose rights the channel's licence cannot give away.
- **NAYA NEWS, 2020.** Cars carried along a flooded lane, filmed on a phone from a building. It looks
  like a resident's clip that the channel republished, so the channel may not own it.

Because of the last two points, nothing from the Sakshi TV or NAYA NEWS clips should be shown in the
demo video or republished. The Siasat Daily clip may be shown with this credit:

> "Rain Lashes in Hyderabad, Road turns into river", Siasat Daily, CC BY,
> https://www.youtube.com/watch?v=030j7lSZ3cY

## What this footage is not

- It is not CCTV and not a fixed camera. It is edited news footage with cuts.
- No water depth is known for any frame, so it cannot give an accuracy figure.
- None of it has been read by the photo reader: no model route exists yet.

## To fetch them again

The files were fetched as 720p or 360p video without sound, then cut to two frames a second:

```
ffmpeg -i samples/footage/030j7lSZ3cY.mp4 -vf "fps=2,scale=640:-2" samples/footage/frames/030j7lSZ3cY/%05d.jpg
```
