"""scripts/deploy_web.py: which files go up, with what headers, and what never does."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import deploy_web  # noqa: E402


def test_the_real_web_folder_uploads_the_pages_and_not_the_notes():
    files = deploy_web.files_to_upload()
    assert {"index.html", "map.js", "style.json", "tokens.css", "base.css", "rules.js",
            "data/rule-cases.json"} <= set(files)
    assert not [key for key in files if key.endswith(".md")]
    assert "data/hyderabad.json" not in files


def test_every_file_found_exists_and_nothing_is_uploaded_twice():
    files = deploy_web.files_to_upload()
    assert all(path.is_file() for path in files.values())
    assert len(files) == len(set(files))


def test_the_publishers_file_can_never_be_overwritten(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "hyderabad.json").write_text("{}")
    with pytest.raises(ValueError, match="publisher"):
        deploy_web.files_to_upload(tmp_path, extra={})


def test_only_web_files_are_picked_up(tmp_path):
    for name in ("a.html", "b.css", "c.js", "d.json", "notes.md", "secret.env", "script.py", "e.svg"):
        (tmp_path / name).write_text("x")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "f.js").write_text("x")
    assert sorted(deploy_web.files_to_upload(tmp_path, extra={})) == [
        "a.html", "b.css", "c.js", "d.json", "e.svg", "sub/f.js"]


@pytest.mark.parametrize("name, expected", [
    ("index.html", "text/html; charset=utf-8"), ("map.js", "text/javascript; charset=utf-8"),
    ("style.json", "application/json; charset=utf-8"), ("base.css", "text/css; charset=utf-8"),
    ("hyderabad.svg", "image/svg+xml")])
def test_content_types(name, expected):
    assert deploy_web.content_type(name) == expected


def test_upload_sets_type_and_a_short_cache():
    class S3:
        def __init__(self):
            self.puts = []

        def put_object(self, **kwargs):
            self.puts.append(kwargs)

    s3 = S3()
    deploy_web.upload(s3, "bucket", {"index.html": ROOT / "web" / "index.html"})
    [put] = s3.puts
    assert put["Bucket"] == "bucket" and put["Key"] == "index.html"
    assert put["ContentType"].startswith("text/html") and put["CacheControl"] == "public, max-age=300"
    assert put["Body"].startswith(b"<!doctype html>")
