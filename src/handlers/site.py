"""Serves the public site from the bucket over HTTPS, through a Lambda function URL.

This stands in for CloudFront while the account is not yet allowed to create distributions
(see DESIGN.md). The pages call only relative addresses, so moving to CloudFront later changes
the address and nothing else.

Read-only: GET and HEAD of one object, nothing else. Every object in the bucket is public by
design (the pages and the map file), so the only care taken is that a request cannot name
anything but an object key.
"""

import base64
import os
from urllib.parse import unquote

import boto3
from botocore.exceptions import ClientError

S3 = boto3.client("s3")
BUCKET = os.environ["PUBLIC_BUCKET"]
ROOT_OBJECT = "index.html"
SECURITY = {
    "Strict-Transport-Security": "max-age=31536000",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "SAMEORIGIN",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}


def key_for(path):
    """The object key a request path names, or None if it names nothing safe."""
    key = unquote(path or "/")
    if not key.startswith("/"):
        return None
    key = key[1:] or ROOT_OBJECT              # one leading slash, never more: one address per file
    parts = key.split("/")
    if any(part in ("", ".", "..") for part in parts) or "\\" in key or "\x00" in key:
        return None
    return key


def respond(status, body=b"", headers=None):
    return {"statusCode": status, "isBase64Encoded": True,
            "headers": {**SECURITY, **(headers or {})},
            "body": base64.b64encode(body).decode("ascii")}


def handler(event, context):
    http = event.get("requestContext", {}).get("http", {})
    method = http.get("method", "GET")
    if method not in ("GET", "HEAD"):
        return respond(405, b"Method not allowed", {"Allow": "GET, HEAD", "Content-Type": "text/plain"})
    key = key_for(event.get("rawPath", "/"))
    if key is None:
        return respond(404, b"Not found", {"Content-Type": "text/plain"})
    try:
        obj = S3.get_object(Bucket=BUCKET, Key=key)
    except ClientError as error:
        if error.response["Error"]["Code"] in ("NoSuchKey", "404", "NotFound"):
            return respond(404, b"Not found", {"Content-Type": "text/plain"})
        raise

    headers = {"Content-Type": obj.get("ContentType", "application/octet-stream"),
               "Cache-Control": obj.get("CacheControl", "public, max-age=300")}
    if obj.get("ContentEncoding"):
        headers["Content-Encoding"] = obj["ContentEncoding"]
    if obj.get("ETag"):
        headers["ETag"] = obj["ETag"]
        if event.get("headers", {}).get("if-none-match") == obj["ETag"]:
            return respond(304, b"", headers)
    return respond(200, b"" if method == "HEAD" else obj["Body"].read(), headers)
