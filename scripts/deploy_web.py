"""Upload web/ to the public bucket, and clear the CloudFront cache if CloudFront is on.

    python scripts/deploy_web.py            # shows what would be uploaded
    python scripts/deploy_web.py --apply    # uploads it

The bucket and distribution are read from the deployed stack, so nothing is typed in.
Pages are uploaded with a five-minute cache and the whole distribution is invalidated after,
so a change is live within a minute or two.

What goes up: the pages, styles, scripts and map style in web/. What does not: notes (*.md),
and anything that is not a web file. `data/hyderabad.json` is written by the publisher and
this script never touches it. `data/rule-cases.json` goes up because the rules check page
reads it.
"""

import argparse
import mimetypes
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
STACK, REGION = "nirmaldhara", "ap-south-1"
CACHE = "public, max-age=300"
SERVED = {".html", ".css", ".js", ".json", ".svg", ".png", ".jpg", ".webp", ".woff2", ".ico"}
EXTRA = {"data/rule-cases.json": ROOT / "data" / "rule-cases.json"}
RESERVED = {"data/hyderabad.json"}          # written by the publisher, never by this script

TYPES = {".js": "text/javascript; charset=utf-8", ".json": "application/json; charset=utf-8",
         ".css": "text/css; charset=utf-8", ".html": "text/html; charset=utf-8",
         ".svg": "image/svg+xml", ".woff2": "font/woff2"}


def content_type(name):
    suffix = Path(name).suffix.lower()
    return TYPES.get(suffix) or mimetypes.guess_type(name)[0] or "application/octet-stream"


def files_to_upload(web=WEB, extra=None):
    """{key in the bucket: path on disk}, sorted. Never includes a reserved key."""
    out = {}
    for path in sorted(Path(web).rglob("*")):
        if path.is_file() and path.suffix.lower() in SERVED:
            out[path.relative_to(web).as_posix()] = path
    out.update(EXTRA if extra is None else extra)
    clash = RESERVED & set(out)
    if clash:
        raise ValueError(f"would overwrite the publisher's file: {sorted(clash)}")
    return out


def upload(s3, bucket, files):
    for key, path in files.items():
        s3.put_object(Bucket=bucket, Key=key, Body=path.read_bytes(),
                      ContentType=content_type(key), CacheControl=CACHE)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    files = files_to_upload()
    for key in files:
        print(f"  {key}")
    print(f"{len(files)} files")
    if not args.apply:
        print("Run again with --apply to upload them.")
        return 0

    import boto3
    outputs = {o["OutputKey"]: o["OutputValue"] for o in boto3.client(
        "cloudformation", region_name=REGION).describe_stacks(StackName=STACK)["Stacks"][0]["Outputs"]}
    upload(boto3.client("s3", region_name=REGION), outputs["PublicBucket"], files)
    if "SiteDistributionId" in outputs:         # only when CloudFront is switched on
        boto3.client("cloudfront").create_invalidation(
            DistributionId=outputs["SiteDistributionId"],
            InvalidationBatch={"Paths": {"Quantity": 1, "Items": ["/*"]},
                               "CallerReference": f"deploy-web-{int(time.time())}"})
    print(f"Uploaded. {outputs['SiteUrl']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
