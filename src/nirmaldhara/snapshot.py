"""Write a public JSON file that is rebuilt from the database, safely when runs overlap.

Used by the map publisher and the flood-history writer. A file is rebuilt in full from the
database each time, so the only danger is two runs overlapping and an older picture replacing
a newer one. Each run reads the file's version (ETag) first, then the data, and writes only if
the file is still at that version. The run that loses starts again with fresh data.

A run that finds the rows identical to the file's, and the file young enough, writes nothing.
The fingerprint stored with the file covers the rows only, so a changing `generated_at` does
not count as a change.
"""

import gzip
import hashlib
import json

from botocore.exceptions import ClientError

LOST_RACE = ("PreconditionFailed", "ConditionalRequestConflict")
MISSING = ("404", "NoSuchKey", "NotFound")


def fingerprint(rows):
    return hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode("utf-8")).hexdigest()[:16]


def current(s3, bucket, key):
    """(version, fingerprint of its rows, time written) of the file, or None if absent."""
    try:
        head = s3.head_object(Bucket=bucket, Key=key)
    except ClientError as error:
        if error.response["Error"]["Code"] in MISSING:
            return None
        raise
    return head["ETag"], head.get("Metadata", {}).get("rows"), head["LastModified"].timestamp()


def put(s3, bucket, key, build, now, *, cache, refresh_s=300, attempts=4):
    """Rebuild and write the file. `build()` returns (rows, document); the document is what is
    written and the rows are what is compared. Returns {"rows", "bytes", "written"}."""
    for _ in range(attempts):
        existing = current(s3, bucket, key)           # before the data is read, never after
        etag = existing[0] if existing else None
        rows, document = build()
        rows_fingerprint = fingerprint(rows)
        if existing and existing[1] == rows_fingerprint and now - existing[2] < refresh_s:
            return {"rows": len(rows), "bytes": 0, "written": False}
        # mtime=0 so the same content always compresses to the same bytes.
        body = gzip.compress(
            json.dumps(document, separators=(",", ":"), ensure_ascii=False).encode("utf-8"), mtime=0)
        guard = {"IfMatch": etag} if etag else {"IfNoneMatch": "*"}
        try:
            s3.put_object(Bucket=bucket, Key=key, Body=body, ContentType="application/json; charset=utf-8",
                          ContentEncoding="gzip", CacheControl=cache, Metadata={"rows": rows_fingerprint}, **guard)
        except ClientError as error:
            if error.response["Error"]["Code"] in LOST_RACE:
                continue                              # another run wrote first: read again
            raise
        return {"rows": len(rows), "bytes": len(body), "written": True}
    raise RuntimeError(f"{key} kept changing under this run")
