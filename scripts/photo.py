"""Read one photo and send the depth to a site's queue, as a phone upload would eventually do.

    python scripts/photo.py samples/photo.jpg hyd-006                       # reads it, shows the reading
    python scripts/photo.py samples/photo.jpg hyd-006 --go                  # and sends it
    python scripts/photo.py samples/synthetic/normal-16cm.png hyd-006 --reader simulated --go --simulated-ok

The photo goes through the same gates a real upload will meet (too dark, too blurred), then the
reader, and only a reading the reader was willing to give is sent. A photo it declines sends
nothing and says why.

Sending the same photo twice within a few minutes counts once (the queue drops the repeat). Later,
it would count again: stopping that is the upload pipeline's job, by the photo's hash, in
nirmaldhara.intake. This script is not that pipeline.

The simulated reader works only on the drawn scenes in samples/synthetic/ and is not a model. A
simulated reading sent to the real queue puts a made-up depth on the real map, so it needs
--simulated-ok, and it is always sent as an unconfirmed resident reading from device
"simulated-reader", never as a trusted one.
"""

import argparse
import hashlib
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from nirmaldhara import intake  # noqa: E402

SIMULATED_DEVICE = "simulated-reader"
SIMULATED_NOTE = ("SIMULATED: the depth below was measured on a drawn scene by a stand-in, not read from "
                  "a photograph by a model.")


def prepare(image_path, site_id, read, source="resident", device="photo-script", simulated=False, now=None):
    """What would happen to this photo. Returns {"status", "reason", "message"}; message only if "ok".

    `read` is the reader's read_depth. Statuses: ok, refused (a gate), declined (the reader would not
    read it).
    """
    now = int(now if now is not None else time.time())
    image = Image.open(image_path)
    if np.asarray(image.convert("L")).mean() < intake.MIN_BRIGHTNESS:
        return {"status": "refused", "reason": intake.TOO_DARK, "message": None}
    if intake.sharpness(image) < intake.MIN_SHARPNESS:
        return {"status": "refused", "reason": intake.TOO_BLURRED, "message": None}

    reading = read(str(image_path))
    if reading["cannot_tell"]:
        return {"status": "declined", "reason": reading.get("reason", "the reader would not say"), "message": None}

    import send
    message = send.reading_message(
        site_id, reading["depth_cm_high"], reading["depth_cm_low"], reading["confidence"],
        source=source, device=SIMULATED_DEVICE if simulated else device, ts=now)
    return {"status": "ok", "reason": reading.get("reason", ""), "message": message}


def photo_hash(image_path):
    return hashlib.sha256(Path(image_path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("image")
    parser.add_argument("site", help="a registry site id such as hyd-006")
    parser.add_argument("--reader", choices=["bedrock", "simulated"], default="bedrock")
    parser.add_argument("--source", choices=["resident", "guardian", "cctv"], default="resident",
                        help="who took it; guardian and cctv are trusted by the engine (default: resident)")
    parser.add_argument("--device", default="photo-script")
    parser.add_argument("--go", action="store_true", help="send the reading (default: show it)")
    parser.add_argument("--simulated-ok", action="store_true",
                        help="allow a simulated reading to be sent to the real queue")
    args = parser.parse_args()

    simulated = args.reader == "simulated"
    if simulated and args.source != "resident":
        print("A simulated reading is never sent as a trusted source. Leave --source as resident.")
        return 2
    if simulated and args.go and not args.simulated_ok:
        print(SIMULATED_NOTE)
        print("Sending it would put a made-up depth on the real map. Add --simulated-ok if you mean to.")
        return 2

    if simulated:
        import simulated_reader as reader_module
    else:
        from nirmaldhara import reader as reader_module

    result = prepare(args.image, args.site, reader_module.read_depth, args.source, args.device, simulated)
    if simulated:
        print(SIMULATED_NOTE)
    if result["status"] != "ok":
        print(f"Nothing sent. {result['status'].capitalize()}: {result['reason']}")
        return 1
    reading = result["message"]["reading"]
    print(f"Read {reading['low']:g}-{reading['high']:g} cm, confidence {reading['confidence']:g}, "
          f"as {reading['source']} / {reading['device']}.")
    print(f"  {result['reason']}")
    if not args.go:
        print("Run again with --go to send it.")
        return 0

    import send
    import stack
    aws = stack.session()
    resources = stack.resources(aws)
    table = aws.resource("dynamodb").Table(resources["SitesTable"])
    if table.get_item(Key={"city": send.CITY, "site_id": args.site}).get("Item") is None:
        print(f"{args.site} is not in the registry. Nothing sent.")
        return 1
    send.send(aws.client("sqs"), send.queue_url(aws, resources), result["message"],
              dedup=f"photo-{photo_hash(args.image)[:48]}-{result['message']['reading']['ts'] // 60}")
    print(f"Sent to {args.site}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
