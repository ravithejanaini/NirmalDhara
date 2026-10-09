"""The interim site host (handlers/site.py): what it serves, and what it must refuse."""

import base64
import io
import os

import pytest
from botocore.exceptions import ClientError

os.environ.setdefault("AWS_DEFAULT_REGION", "ap-south-1")
os.environ.setdefault("PUBLIC_BUCKET", "public")

from handlers import site  # noqa: E402


class Bucket:
    def __init__(self, objects):
        self.objects, self.asked = objects, []

    def get_object(self, Bucket, Key):
        self.asked.append(Key)
        if Key not in self.objects:
            raise ClientError({"Error": {"Code": "NoSuchKey", "Message": "x"}}, "GetObject")
        obj = dict(self.objects[Key])
        obj["Body"] = io.BytesIO(obj.pop("body"))
        return obj


OBJECTS = {
    "index.html": {"body": b"<!doctype html>hi", "ContentType": "text/html; charset=utf-8",
                   "CacheControl": "public, max-age=300", "ETag": '"a"'},
    "data/hyderabad.json": {"body": b"\x1f\x8bgz", "ContentType": "application/json; charset=utf-8",
                            "ContentEncoding": "gzip", "CacheControl": "public, max-age=15", "ETag": '"b"'},
}


@pytest.fixture
def bucket(monkeypatch):
    fake = Bucket(OBJECTS)
    monkeypatch.setattr(site, "S3", fake)
    return fake


def get(path, method="GET", **headers):
    return site.handler({"rawPath": path, "requestContext": {"http": {"method": method}},
                         "headers": headers}, None)


def body(response):
    return base64.b64decode(response["body"])


def test_the_root_serves_the_index_page(bucket):
    r = get("/")
    assert r["statusCode"] == 200 and body(r) == b"<!doctype html>hi"
    assert r["headers"]["Content-Type"].startswith("text/html")
    assert bucket.asked == ["index.html"]


def test_the_map_file_keeps_its_encoding_and_short_cache(bucket):
    r = get("/data/hyderabad.json")
    assert r["statusCode"] == 200 and body(r) == b"\x1f\x8bgz"
    assert r["headers"]["Content-Encoding"] == "gzip"
    assert r["headers"]["Cache-Control"] == "public, max-age=15"
    assert r["isBase64Encoded"] is True


def test_every_response_carries_the_security_headers(bucket):
    for response in (get("/"), get("/missing"), get("/", method="POST")):
        assert response["headers"]["Strict-Transport-Security"].startswith("max-age=")
        assert response["headers"]["X-Content-Type-Options"] == "nosniff"


def test_a_missing_object_is_a_404(bucket):
    assert get("/nothing.html")["statusCode"] == 404


@pytest.mark.parametrize("path", [
    "/../secret", "/data/../../secret", "/%2e%2e/secret", "/%2E%2E%2Fsecret", "//index.html",
    "/data//hyderabad.json", "/a/./b", "/a\\b", "/%00", "/index.html/", "/./index.html"])
def test_paths_that_do_not_name_one_object_never_reach_the_bucket(bucket, path):
    assert get(path)["statusCode"] == 404
    assert bucket.asked == []


@pytest.mark.parametrize("method", ["POST", "PUT", "DELETE", "PATCH"])
def test_only_reads_are_allowed(bucket, method):
    r = get("/", method=method)
    assert r["statusCode"] == 405 and r["headers"]["Allow"] == "GET, HEAD" and bucket.asked == []


def test_head_returns_the_headers_and_no_body(bucket):
    r = get("/", method="HEAD")
    assert r["statusCode"] == 200 and body(r) == b"" and r["headers"]["ETag"] == '"a"'


def test_an_unchanged_object_is_a_304(bucket):
    r = get("/", **{"if-none-match": '"a"'})
    assert r["statusCode"] == 304 and body(r) == b""
    assert get("/", **{"if-none-match": '"old"'})["statusCode"] == 200


def test_other_storage_errors_are_not_hidden(monkeypatch):
    class Denied:
        def get_object(self, **_):
            raise ClientError({"Error": {"Code": "AccessDenied", "Message": "x"}}, "GetObject")

    monkeypatch.setattr(site, "S3", Denied())
    with pytest.raises(ClientError):
        get("/")
