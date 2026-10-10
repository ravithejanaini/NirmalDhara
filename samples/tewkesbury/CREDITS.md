# River camera pictures and water levels: credits and licence

Used by `scripts/river_camera_test.py` and `scripts/learn_river_cameras.py`; results in
[docs/waterline-river.md](../../docs/waterline-river.md) and [docs/gauge-river.md](../../docs/gauge-river.md).

> Vetra-Carvalho, S., Dance, S. L., Mason, D., Garcia-Pintado, J. (2020). *River water level height
> measurements obtained from river cameras near Tewkesbury.* Mendeley Data, version 1.
> https://doi.org/10.17632/769cyvdznp.1

Described in: Vetra-Carvalho, S., Dance, S. L., Mason, D. C., Waller, J. A., Cooper, E. S., Smith, P. J.,
Tabeart, J. M. (2020). Collection and extraction of water level information from a digital river camera
image dataset. *Data in Brief* 33, 106338. https://doi.org/10.1016/j.dib.2020.106338

- **Rights:** Copyright 2020 University of Reading. The camera pictures were provided to the authors by
  Farson Digital Ltd, and carry its watermark.
- **Licence:** the dataset's page says CC BY 4.0, and so does the sentence in its README. The link in that
  same sentence of the README goes to the non-commercial variant, CC BY-NC 4.0. This project treats it as
  the stricter of the two: attribution, and no commercial use.
- **Downloaded:** 10 October 2026, 580 files, 236.9 MB, every file checked against the hash the archive gives.

## What is in this repository, and what is not

- **Not here:** the pictures, the spreadsheets and the survey files. They are in `samples/tewkesbury/data/`
  on the machine that ran the test, kept out of the repository by `.gitignore`.
- **Here:** `data/tewkesbury-levels.json`, the water level and its stated error for each picture, copied
  from the dataset's four spreadsheets without change. And the figures in the report.

## What the dataset is

Four fixed cameras on the Severn and the Avon, one picture an hour in daylight, 21 November to 5 December
2012, through a flood. For each picture the authors read the water level by eye against points in view
that they had surveyed, and gave each reading an error of up to 25 cm. Pictures they could not read to
within that have no level.

It is a river, in England, in 2012. It is not a street and not Hyderabad.
