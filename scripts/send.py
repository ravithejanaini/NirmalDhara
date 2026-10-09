"""Send one message to the state engine's queue on AWS.

    python scripts/send.py rain hyd-001 25
    python scripts/send.py reading hyd-001 16
    python scripts/send.py reading hyd-001 24 --low 18 --source resident --device phone-7

A reading is sent as a range: --low defaults to 5 cm under the high value. The engine treats
the time in the message as when the reading was received; --ts sets it (default now).
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stack  # noqa: E402

CITY = "hyderabad"


def rain_message(site_id, index_mm, ts):
    return {"type": "rain", "city": CITY, "site_id": site_id, "index_mm": float(index_mm), "ts": int(ts)}


def reading_message(site_id, high, low=None, confidence=0.8, source="guardian", device="send-py", ts=None):
    high = float(high)
    low = max(0.0, high - 5) if low is None else float(low)
    if low > high:
        raise ValueError("low is above high")
    return {"type": "reading", "city": CITY, "site_id": site_id,
            "reading": {"ts": int(ts if ts is not None else time.time()), "low": low, "high": high,
                        "confidence": float(confidence), "source": source, "device": device}}


def send(sqs, queue_url, message, dedup=None):
    """Queue a message for its site. `dedup` must differ for the queue to accept a repeat."""
    sqs.send_message(
        QueueUrl=queue_url, MessageBody=json.dumps(message), MessageGroupId=message["site_id"],
        MessageDeduplicationId=dedup or f"send-{message['type']}-{time.time_ns()}")


def queue_url(aws, resources):
    return aws.client("sqs").get_queue_url(QueueName=resources["EngineQueue"].split("/")[-1])["QueueUrl"]


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    kinds = parser.add_subparsers(dest="kind", required=True)
    rain = kinds.add_parser("rain")
    rain.add_argument("site")
    rain.add_argument("index_mm", type=float)
    reading = kinds.add_parser("reading")
    reading.add_argument("site")
    reading.add_argument("high", type=float)
    reading.add_argument("--low", type=float)
    reading.add_argument("--confidence", type=float, default=0.8)
    reading.add_argument("--source", default="guardian", choices=["cctv", "guardian", "resident"])
    reading.add_argument("--device", default="send-py")
    for sub in (rain, reading):
        sub.add_argument("--ts", type=int)
    args = parser.parse_args()

    ts = args.ts if args.ts is not None else int(time.time())
    message = (rain_message(args.site, args.index_mm, ts) if args.kind == "rain" else
               reading_message(args.site, args.high, args.low, args.confidence, args.source, args.device, ts))
    aws = stack.session()
    send(aws.client("sqs"), queue_url(aws, stack.resources(aws)), message)
    print("queued:", json.dumps(message))
    return 0


if __name__ == "__main__":
    sys.exit(main())
