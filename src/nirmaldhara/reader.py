"""Depth from one photo with a multimodal model on Amazon Bedrock.

This is estimator 3 in METHOD.md section 6: the fallback that works on any photo.
"""

import base64
import json
import mimetypes
import os

import anthropic
from anthropic import AnthropicBedrock

# The "in." inference profile keeps inference inside India: requests are routed only
# between the Mumbai and Hyderabad regions (ARCHITECTURE.md section 13.1).
MODEL = os.environ.get("NIRMALDHARA_MODEL", "in.anthropic.claude-opus-5")
REGION = os.environ.get("AWS_REGION", "ap-south-1")

INSTRUCTION = """You are reading floodwater depth from a street photo.

Use only objects of known size that are visibly standing in the water:
- Car wheel, about 62 cm across: sidewall only 0-12 cm; rim wet, under one third of the
  wheel 12-20 cm; one third up to the axle 20-31 cm; axle to top of tyre 31-62 cm.
- Motorcycle wheel, about 61 cm: sidewall 0-9; rim to one third 9-20; to axle 20-31;
  axle to top 31-61.
- Scooter or auto-rickshaw wheel, about 43 cm: sidewall 0-9; rim to one third 9-14;
  to axle 14-22; axle to top 22-43.
- Adult: ankle bone 5-7 cm, middle of kneecap 41-52 cm, hip joint 77-94 cm.

Report a depth range in cm, not a single number. If nothing of known size is in the
water, or the photo is too dark or blurred, set cannot_tell to true. Do not guess."""

SCHEMA = {
    "type": "object",
    "properties": {
        "flood_present": {"type": "boolean"},
        "cannot_tell": {"type": "boolean"},
        "objects": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string"},
                    "level": {"type": "string"},
                    "confidence": {"type": "number"},
                },
                "required": ["type", "level", "confidence"],
                "additionalProperties": False,
            },
        },
        "depth_cm_low": {"type": "number"},
        "depth_cm_high": {"type": "number"},
        "confidence": {"type": "number"},
        "reason": {"type": "string"},
    },
    "required": [
        "flood_present", "cannot_tell", "objects",
        "depth_cm_low", "depth_cm_high", "confidence", "reason",
    ],
    "additionalProperties": False,
}

CANNOT_TELL = {
    "flood_present": False, "cannot_tell": True, "objects": [],
    "depth_cm_low": 0, "depth_cm_high": 0, "confidence": 0,
}


def read_depth(image_path, region=None):
    """Return the reading for one image as a dict matching SCHEMA."""
    media_type = mimetypes.guess_type(image_path)[0] or "image/jpeg"
    with open(image_path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode("utf-8")

    client = AnthropicBedrock(aws_region=region or REGION)
    try:
        response = _ask(client, media_type, data)
    except (anthropic.RateLimitError, anthropic.InternalServerError,
            anthropic.APIConnectionError) as error:
        # The service is busy or unreachable, after the client's own retries. The
        # photo is simply unread; a wrong setting (a 4xx) is left to raise.
        return {**CANNOT_TELL,
                "reason": f"The reading service was unavailable ({type(error).__name__})."}
    if response.stop_reason == "refusal":
        return {**CANNOT_TELL, "reason": "The model declined to read this image."}
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)


def _ask(client, media_type, data):
    return client.messages.create(
        model=MODEL,
        max_tokens=16000,
        system=INSTRUCTION,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image",
                 "source": {"type": "base64", "media_type": media_type, "data": data}},
                {"type": "text", "text": "Read the water depth in this photo."},
            ],
        }],
        output_config={"effort": "medium",
                       "format": {"type": "json_schema", "schema": SCHEMA}},
    )
