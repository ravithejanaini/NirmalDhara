"""The reader against a stand-in client: request shape and response handling only.

This does not test what a real model says about a real photo.
"""

import json
from types import SimpleNamespace

import anthropic
import pytest
from PIL import Image

from nirmaldhara import reader

READING = {
    "flood_present": True, "cannot_tell": False,
    "objects": [{"type": "car", "level": "rim_to_one_third", "confidence": 0.7}],
    "depth_cm_low": 12, "depth_cm_high": 20, "confidence": 0.7,
    "reason": "Water reaches the rim of the front wheel.",
}


def fake_client(response, seen):
    def create(**kwargs):
        seen.update(kwargs)
        return response
    return lambda **_: SimpleNamespace(messages=SimpleNamespace(create=create))


def photo(tmp_path):
    path = tmp_path / "street.jpg"
    Image.new("RGB", (64, 48), "grey").save(path)
    return str(path)


def test_request_carries_image_and_schema(tmp_path, monkeypatch):
    seen = {}
    response = SimpleNamespace(
        stop_reason="end_turn",
        content=[SimpleNamespace(type="text", text=json.dumps(READING))],
    )
    monkeypatch.setattr(reader, "AnthropicBedrock", fake_client(response, seen))

    assert reader.read_depth(photo(tmp_path)) == READING

    image = seen["messages"][0]["content"][0]
    assert image["type"] == "image"
    assert image["source"]["media_type"] == "image/jpeg"
    assert seen["output_config"]["format"]["schema"] == reader.SCHEMA
    assert seen["model"] == reader.MODEL


def test_refusal_becomes_cannot_tell(tmp_path, monkeypatch):
    response = SimpleNamespace(stop_reason="refusal", content=[])
    monkeypatch.setattr(reader, "AnthropicBedrock", fake_client(response, {}))

    reading = reader.read_depth(photo(tmp_path))
    assert reading["cannot_tell"] is True
    assert reading["confidence"] == 0


def failing_client(error):
    def create(**_):
        raise error
    return lambda **_: SimpleNamespace(messages=SimpleNamespace(create=create))


def api_error(kind):
    """An instance of one of the SDK's error classes, without building an HTTP response.

    The reader only looks at the kind of error, so the test does not need a response object,
    and so does not depend on which HTTP library the installed SDK version uses."""
    return kind.__new__(kind)


@pytest.mark.parametrize("error", [
    api_error(anthropic.RateLimitError),
    api_error(anthropic.InternalServerError),
    api_error(anthropic.APIConnectionError),
])
def test_a_busy_or_unreachable_service_becomes_cannot_tell(tmp_path, monkeypatch, error):
    monkeypatch.setattr(reader, "AnthropicBedrock", failing_client(error))
    reading = reader.read_depth(photo(tmp_path))
    assert reading["cannot_tell"] is True and "unavailable" in reading["reason"]


def test_a_wrong_setting_is_not_hidden(tmp_path, monkeypatch):
    error = api_error(anthropic.BadRequestError)
    monkeypatch.setattr(reader, "AnthropicBedrock", failing_client(error))
    with pytest.raises(anthropic.BadRequestError):
        reader.read_depth(photo(tmp_path))
