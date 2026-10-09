"""Signed links: capture links for photos and acknowledge links for officials.

A link carries who it is for, what it is for and when it expires, signed so it
cannot be altered. Single use is enforced by the caller, which records the nonce.
ARCHITECTURE.md section 8.
"""

import base64
import hashlib
import hmac
import json
import secrets

CAPTURE_TTL_S = 20 * 60
ACK_TTL_S = 2 * 60 * 60


def _b64(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text):
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def issue(key, purpose, subject, target, now, ttl_s):
    """A token for `subject` (a subscriber or officer) to act on `target`."""
    claims = {"p": purpose, "s": subject, "t": target, "e": int(now + ttl_s),
              "n": secrets.token_urlsafe(9)}
    body = _b64(json.dumps(claims, separators=(",", ":")).encode())
    signature = _b64(hmac.new(key, body.encode(), hashlib.sha256).digest())
    return f"{body}.{signature}"


def verify(key, token, purpose, now):
    """The claims if the token is genuine, for this purpose and unexpired; else None."""
    try:
        body, signature = token.split(".")
        expected = _b64(hmac.new(key, body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            return None
        claims = json.loads(_unb64(body))
    except (ValueError, json.JSONDecodeError):
        return None
    if claims.get("p") != purpose or now > claims.get("e", 0):
        return None
    return claims
