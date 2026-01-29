import base64
import hmac
import json
import time
from hashlib import sha256
from typing import Any
from app.core.config import settings


STATE_TTL_SECONDS = 600


def _sign(payload: str) -> str:
    return hmac.new(settings.secret_key.encode("utf-8"), payload.encode("utf-8"), sha256).hexdigest()


def create_state(data: dict[str, Any]) -> str:
    envelope = {
        "data": data,
        "ts": int(time.time()),
    }
    raw = json.dumps(envelope, separators=(",", ":"), sort_keys=True)
    sig = _sign(raw)
    token = base64.urlsafe_b64encode(raw.encode("utf-8")).decode("utf-8")
    return f"{token}.{sig}"


def verify_state(state: str) -> dict[str, Any]:
    try:
        token, sig = state.rsplit(".", 1)
        raw = base64.urlsafe_b64decode(token.encode("utf-8")).decode("utf-8")
    except Exception as exc:
        raise ValueError("Invalid state payload") from exc
    expected = _sign(raw)
    if not hmac.compare_digest(expected, sig):
        raise ValueError("Invalid state signature")
    payload = json.loads(raw)
    timestamp = payload.get("ts")
    if not isinstance(timestamp, int):
        raise ValueError("Invalid state timestamp")
    if int(time.time()) - timestamp > STATE_TTL_SECONDS:
        raise ValueError("State expired")
    return payload.get("data") or {}
