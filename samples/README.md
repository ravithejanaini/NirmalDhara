# Photos for the evaluation

## `synthetic/`: drawings, not photographs

22 scenes drawn by `scripts/make_synthetic_photos.py`: a car wheel of a known size standing in
water of a known depth, plus the hard cases (waves, glare, a hidden wheel, no wheel, too dark, too
blurred). They exist so the evaluation and photo scripts could be built and run before a model
route and real photos were available. **They say nothing about how a model reads real floods.** Do
not put them in front of the real reader, and do not quote results on them as accuracy.

## Your photos go here

Put 12 to 15 real flood photos in this folder, and a file `labels.csv` beside them. Use photos you
took, or openly licensed ones with the licence written down; do not copy news photos.

| Column | What to write |
|---|---|
| `file` | The photo's file name, in this folder |
| `band_low`, `band_high` | The depth band you judge from the wheel or knee rule, `B0` to `B5`. Equal if you are sure; the two ends of your doubt if not |
| `object_used` | What you measured against: `car wheel`, `motorcycle wheel`, `knee`, or `none` if nothing of known size is in the water |
| `moving` | `yes` or `no`: is the water flowing |
| `source` | Where it came from (your own, or a link) |
| `licence` | Yours, or the licence it is shared under |
| `readable` | Optional. `no` if the photo is too dark or blurred for anyone to read |

Bands: `B0` dry, `B1` under 12 cm (ankle), `B2` 12 to 20 (shin), `B3` 20 to 30 (below the knee),
`B4` 30 to 50 (about knee deep), `B5` above 50. Label each photo **before** running any model on it.

Also add two or three photos of a partly blocked roadside drain inlet in `inlets/`, with their
source and licence in `inlets/README.md`.

Then:

```bash
python scripts/evaluate.py --reader bedrock
```

That writes `EVALUATION.md` and `data/eval-results.json`. It needs a working model route; see
MOD-01 in `TASKS.md`.
