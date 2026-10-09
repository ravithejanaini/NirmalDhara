"""Command line: read a photo, or check a depth range without calling the model.

    python -m nirmaldhara read photo.jpg
    python -m nirmaldhara check --low 20 --high 30 --confidence 0.7
"""

import argparse
import json

from .bands import band_for, passability


def report(low, high, confidence, moving=False):
    return {
        "band": band_for(high),
        "passability": passability(low, high, confidence, moving),
    }


def main():
    parser = argparse.ArgumentParser(prog="nirmaldhara")
    sub = parser.add_subparsers(dest="command", required=True)

    read = sub.add_parser("read", help="read water depth from a photo")
    read.add_argument("image")
    read.add_argument("--region", help="AWS region; defaults to AWS_REGION, then ap-south-1")

    check = sub.add_parser("check", help="passability for a depth range")
    check.add_argument("--low", type=float, required=True)
    check.add_argument("--high", type=float, required=True)
    check.add_argument("--confidence", type=float, required=True)
    check.add_argument("--moving", action="store_true")

    args = parser.parse_args()
    if args.command == "check":
        out = report(args.low, args.high, args.confidence, args.moving)
    else:
        from .reader import read_depth  # needs the anthropic package and AWS credentials

        reading = read_depth(args.image, args.region)
        out = {"reading": reading}
        if not reading["cannot_tell"]:
            out.update(report(reading["depth_cm_low"], reading["depth_cm_high"],
                              reading["confidence"]))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
