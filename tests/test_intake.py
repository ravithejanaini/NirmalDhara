import numpy as np
from PIL import Image, ImageFilter

from nirmaldhara import intake, tokens

SITE = (17.4575, 78.3638)


def street(seed=0, size=(640, 480)):
    """A busy, sharp, daylight picture."""
    rng = np.random.default_rng(seed)
    return Image.fromarray(rng.integers(40, 220, (size[1], size[0], 3), dtype=np.uint8))


def check(image, lat=SITE[0], lon=SITE[1], requested_at=0, received_at=60, seen=()):
    return intake.check(image, "h1", lat, lon, *SITE, requested_at, received_at, set(seen))


def test_distance_is_about_right():
    # One thousandth of a degree of latitude is about 111 metres.
    assert 105 < intake.distance_m(17.0, 78.0, 17.001, 78.0) < 117


def test_good_photo_is_accepted():
    assert check(street()) == intake.OK


def test_photo_from_elsewhere_is_refused():
    assert check(street(), lat=SITE[0] + 0.002) == intake.TOO_FAR


def test_late_upload_is_refused():
    assert check(street(), received_at=301) == intake.TOO_OLD


def test_repeat_of_the_same_file_is_refused():
    assert check(street(), seen={"h1"}) == intake.DUPLICATE


def test_dark_photo_is_refused():
    assert check(Image.new("RGB", (640, 480), (5, 5, 5))) == intake.TOO_DARK


def test_blurred_photo_is_refused():
    assert check(street().filter(ImageFilter.GaussianBlur(12))) == intake.TOO_BLURRED


def test_crop_keeps_only_the_shared_region():
    image = Image.new("RGB", (200, 100), (200, 200, 200))
    kept = intake.crop_to_region(image, [(50, 20), (150, 20), (150, 80), (100, 80)])
    assert kept.size == (100, 60)
    assert kept.getpixel((90, 10)) == (200, 200, 200)   # inside the shape
    assert kept.getpixel((5, 55)) == (0, 0, 0)          # in the bounds, outside the shape


def test_blur_changes_the_box_and_nothing_else():
    image = street(seed=1)
    out = intake.blur_boxes(image, [(0.25, 0.25, 0.25, 0.25)])
    before, after = np.asarray(image, dtype=int), np.asarray(out, dtype=int)
    inside = np.abs(before - after)[130:230, 170:310].mean()
    outside = np.abs(before - after)[300:, :].mean()
    assert inside > 20 and outside == 0


def test_capture_link_round_trip():
    key = b"test-key"
    token = tokens.issue(key, "capture", "sub_017", "hyd-001", now=1000,
                         ttl_s=tokens.CAPTURE_TTL_S)
    claims = tokens.verify(key, token, "capture", now=1500)
    assert claims["s"] == "sub_017" and claims["t"] == "hyd-001"


def test_capture_link_fails_when_expired_altered_or_misused():
    key = b"test-key"
    token = tokens.issue(key, "capture", "sub_017", "hyd-001", now=1000, ttl_s=60)
    assert tokens.verify(key, token, "capture", now=1061) is None          # expired
    assert tokens.verify(b"other-key", token, "capture", now=1010) is None  # forged
    assert tokens.verify(key, token, "ack", now=1010) is None               # wrong purpose
    body, signature = token.split(".")
    assert tokens.verify(key, body[:-2] + "AA." + signature, "capture", now=1010) is None
    assert tokens.verify(key, "garbage", "capture", now=1010) is None
