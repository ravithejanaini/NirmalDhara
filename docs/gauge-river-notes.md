
## How to read this

**Tewkesbury was used to build the gauge**, so its figures come after choices made while looking at them.
Four things were settled there:

- Only two things are kept about a patch: how like its dry self its pattern is, and its contrast. Brightness
  and colour were used at first and thrown out. The water there is grey under cloud and dark blue under a
  clear sky, and a gauge that had learnt one called the other dry.
- A step is put between whole days, never inside one. Inside a day it found the morning and the afternoon.
- How much a patch's look moves from one day to the next is measured over all patches and added to each.
- A level is given only if it explains the picture, and clearly beats "below everything" and "above
  everything".

**Strensham, Diglis Lock and Evesham were run once, after `gauge.py` had been fixed.** Nothing was chosen for
them: no strip, no dry view, no setting. Strensham's pictures had been read once before, by the detector.

**One thing was changed after that run, and the tables above are from the run after the change.** Past its
last step the gauge can give only a floor or a ceiling. As first run, it gave the far end of that step. At
Strensham, with each day left out, 34 of its 67 floors and ceilings were then on the wrong side of the
measured level, by up to 39 cm. The pictures had not misled it: every level from about 12.56 m up fitted
them equally well, and the wrong end of that range was being reported. It now reports the near end, and 0 of
the 67 are on the wrong side. Every level it gave is the same in both runs. Only the floors and ceilings
moved, and with them "both together", which uses them: at Strensham from 9 cm to 8 cm typically, and at
Tewkesbury its 90% figure from 71 cm to 83 cm.

## What Strensham shows

The only one of the three with much to learn from: 2.6 m of water over 13 days.

- **Where it gave a level, it was closer than the detector.** With each day left out: 8 cm out, typically,
  and nine in ten within 30 cm. The dataset's own error there is 5 cm.
- **It gave a level for 4 pictures in 10.** The detector gave one for more than 9 in 10. For most of the rest
  the gauge said only "above" or "below". A step needs two whole days on each side of it, and on six of the
  thirteen days the water stood within about 70 cm of its peak. For all of those the gauge said only that
  the water was at or above about 12.5 m, which was true and is not a level.
- **Learning from half the days**, the same split the detector was judged on: 8 cm typically against the
  detector's 13 cm, but a worse tail, with one reading in ten more than 87 cm out against 54 cm.
- **Both together**, the gauge's level where it gave one and the detector's otherwise: a level for 110 of 113
  pictures, 8 cm out typically, nine in ten within 52 cm. The detector alone: 107 pictures, 13 cm, 54 cm.
  Learning took the typical error from 13 cm to 8 cm and left the tail where it was.
- **Learning only from earlier days**, which is how it would be used: a level for 33 of 85 pictures, 31 cm
  out typically. Guessing the middle level of the earlier days is 56 cm out.

## What Diglis Lock and Evesham show

- **Diglis Lock: nothing.** Six days and 0.6 m of water. With each day left out it gave 3 levels in 50
  pictures and no answer at all for 30. With half the days it could not learn.
- **Evesham: worse than not looking.** Eight days, four of them with three pictures or fewer, and 1.0 m of
  water. It gave 35 levels, 16 cm out typically. Always guessing the middle level was 1 cm out, typically,
  because most of the pictures there are at one of two levels.

## What Tewkesbury shows

- Where it gave a level it was 14 to 15 cm out, typically, against 29 cm for the detector on the same
  pictures. The dataset's own error there is 15 cm.
- Learning only from earlier days it was no better than guessing: 37 cm against 37 cm. It had learnt on
  rising water and was reading falling water.
- Two days given the same level there, 23 November and 1 December at 11.45 m, show clearly different amounts
  of the bank under water when the pictures are put side by side. That is a judgement by eye, made while
  building the gauge. If it is right, some of what is counted as error at this camera is in the levels.

## What it means

- **Learning from measured pictures helps where there is something to learn from**: a camera that has seen a
  few metres of water over a dozen days. On the one camera that tests this cleanly, the typical error went
  from 13 cm to 8 cm.
- **It does not help where the water moved little or the days were few.** That was two of the three cameras
  it was tried on unseen.
- **Used the way it would be used, it is tens of centimetres out.** A flood rises past everything the gauge
  has seen, and then all it can say is "above".
- **8 cm is still the width of the narrowest depth band in this project**, and it comes with a tail. This is
  not a reading to close a road on.
- **It cannot be used at any of the nine sites.** It learns from measured levels, and no site has a camera,
  let alone a level measured beside one. What it would take: each time a depth at a site is confirmed some
  other way, the camera's picture from that moment is kept with it. Nothing does that yet.

## What this is not

- **Not a street, and not Hyderabad.** Rivers in England, in 2012.
- **Not independent levels.** The levels it learnt from and the levels it was judged against were read by the
  same people from these same pictures. A mistake they made the same way every time would not show here.
- **Not a second flood.** It learnt from days of one flood and was read on other days of that flood. Whether
  a gauge learnt in one flood holds in the next, after the bank and the season have changed, is not tested.
- **Not night.** No picture was taken in the dark.
- **Not connected to anything.** Nothing in the system calls `gauge.py`.
