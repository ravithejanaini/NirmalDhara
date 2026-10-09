"""Run the camera change gate over a clip's frames: how many frames would actually be sent?

    python scripts/gate_demo.py samples/footage/frames/030j7lSZ3cY --fps 2
    python scripts/gate_demo.py --all            # every folder under samples/footage/frames, and the report

A fixed camera sees the same street most of the time. The gate (src/nirmaldhara/change.py) learns
each camera's own noise and sends a frame only when the scene has changed and settled, so most
frames never leave the premises. This script feeds it real frames and counts.

The frames are cut from a video beforehand, for example with ffmpeg:

    ffmpeg -i clip.mp4 -vf fps=2 samples/footage/frames/NAME/%05d.jpg

The clips used are listed with their licences in samples/footage/CREDITS.md. They are edited news
footage, not a fixed camera: every cut in the edit is a new scene, which the gate must send. A
real fixed camera would send fewer.
"""

import argparse
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nirmaldhara.change import ChangeGate  # noqa: E402

FRAMES = ROOT / "samples" / "footage" / "frames"
OUT = ROOT / "docs" / "gate-demo"
THUMB = (160, 90)
STRIP_COLUMNS = 8


def run(folder, fps):
    """[(index, seconds, sent)] for every frame in the folder, in name order."""
    gate, out = ChangeGate(), []
    for index, path in enumerate(sorted(Path(folder).glob("*.jpg"))):
        with Image.open(path) as image:
            out.append((index, index / fps, gate.should_send(image, index / fps), path))
    return out


def summary(results):
    seen, sent = len(results), sum(1 for r in results if r[2])
    return {"seen": seen, "sent": sent, "saved": 0.0 if not seen else 1 - sent / seen}


def strip(results, target):
    """One image of the frames that were sent, in order, so a reader can see what triggered."""
    sent = [r for r in results if r[2]]
    if not sent:
        return None
    rows = -(-len(sent) // STRIP_COLUMNS)
    sheet = Image.new("RGB", (THUMB[0] * min(len(sent), STRIP_COLUMNS), THUMB[1] * rows), (14, 26, 43))
    for n, (_, _, _, path) in enumerate(sent):
        with Image.open(path) as image:
            sheet.paste(image.convert("RGB").resize(THUMB), ((n % STRIP_COLUMNS) * THUMB[0], (n // STRIP_COLUMNS) * THUMB[1]))
    target.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(target, quality=80)
    return target


def sentence(name, counts):
    return f"`{name}`: of {counts['seen']} frames, {counts['sent']} were sent ({counts['saved']:.0%} never left the camera)."


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("folder", nargs="?", help="a folder of frames, in name order")
    parser.add_argument("--fps", type=float, default=2, help="frames per second the folder was cut at")
    parser.add_argument("--all", action="store_true", help="every folder under samples/footage/frames")
    args = parser.parse_args()
    folders = sorted(p for p in FRAMES.iterdir() if p.is_dir()) if args.all else [Path(args.folder)] if args.folder else []
    if not folders:
        parser.error("name a folder of frames, or use --all")
    for folder in folders:
        results = run(folder, args.fps)
        counts = summary(results)
        strip(results, OUT / f"{folder.name}.jpg")
        print(sentence(folder.name, counts))
        print("  sent at seconds:", ", ".join(f"{r[1]:.1f}" for r in results if r[2]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
