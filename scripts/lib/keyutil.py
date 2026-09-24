"""Loads the data.go.kr service key WITHOUT ever printing/logging it.

CRITICAL: the key in .env.local is already URL-percent-encoded. It must be
concatenated into query strings verbatim -- never pass it through
urllib.parse.quote() / quote_plus() again, or auth breaks with a 403 that
looks like a "not subscribed" error.
"""
from __future__ import annotations

import os
import re

_ENV_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    ".env.local",
)

_KEY_CACHE: str | None = None


def load_key() -> str:
    global _KEY_CACHE
    if _KEY_CACHE is not None:
        return _KEY_CACHE
    if not os.path.exists(_ENV_PATH):
        raise RuntimeError(".env.local not found -- cannot load DATA_GO_KR_KEY")
    with open(_ENV_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("DATA_GO_KR_KEY="):
                v = line.split("=", 1)[1].strip().strip('"').strip("'")
                if not v:
                    raise RuntimeError("DATA_GO_KR_KEY is empty in .env.local")
                _KEY_CACHE = v
                return v
    raise RuntimeError("DATA_GO_KR_KEY not found in .env.local")


def redact(text: str) -> str:
    """Best-effort redaction of the raw key from any string headed for
    stdout/logs/errors (defense in depth -- callers should avoid embedding
    the key in messages in the first place)."""
    if not text:
        return text
    try:
        key = load_key()
    except Exception:
        return text
    out = text.replace(key, "<redacted-key>")
    # Also strip anything that looks like a serviceKey= query param value,
    # in case a differently-encoded copy of the key ends up in a URL.
    out = re.sub(r"([sS]ervice[kK]ey=)[^&\s]+", r"\1<redacted-key>", out)
    return out
