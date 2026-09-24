"""Shared HTTP fetching with bounded concurrency and retry/backoff for
data.go.kr APIs.

Rules enforced here:
  - at most 4 concurrent in-flight requests (module-level ThreadPoolExecutor)
  - up to 3 attempts per request, exponential backoff on network errors or
    non-success result codes
  - result codes "22" (LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR) and
    "23" (SERVICE_ACCESS_DENIED / throttling) back off harder before retrying
  - the raw API key is never printed/logged (see keyutil.redact)
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from xml.etree import ElementTree as ET

import threading

from . import keyutil

MAX_WORKERS = 4
_EXECUTOR = ThreadPoolExecutor(max_workers=MAX_WORKERS)

SUCCESS_CODES = {"00", "0", "0000", "C00"}
THROTTLE_CODES = {"22", "23"}

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) kr-baby-now-collector/1.0"

# A light global pacer: even with only 4 concurrent workers, hammering a
# single data.go.kr host back-to-back for a few hundred requests (e.g. the
# vaccine layer's 256-sigungu loop) can trip an undocumented per-second rate
# limit and return raw HTTP 429s (verified live). Enforce a minimum spacing
# between request *starts* across all threads.
_PACE_LOCK = threading.Lock()
_LAST_REQUEST_TS = [0.0]
MIN_REQUEST_SPACING = 0.12  # seconds


def _pace():
    with _PACE_LOCK:
        now = time.monotonic()
        wait = _LAST_REQUEST_TS[0] + MIN_REQUEST_SPACING - now
        if wait > 0:
            time.sleep(wait)
            now = time.monotonic()
        _LAST_REQUEST_TS[0] = now


class FetchError(RuntimeError):
    pass


def submit(fn, *args, **kwargs):
    """Submit work to the shared 4-worker pool. Returns a Future."""
    return _EXECUTOR.submit(fn, *args, **kwargs)


def map_all(fn, items):
    """Run fn(item) for each item using the shared pool, preserving order,
    and raise the first exception encountered (after all futures finish)."""
    futures = [submit(fn, item) for item in items]
    results = []
    errs = []
    for fut in futures:
        try:
            results.append(fut.result())
        except Exception as e:  # noqa: BLE001
            errs.append(e)
            results.append(None)
    if errs:
        raise errs[0]
    return results


class TooManyRequests(RuntimeError):
    pass


def _http_get(url: str, timeout: int) -> str:
    _pace()
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        if e.code == 429:
            raise TooManyRequests(str(e)) from None
        raise
    for enc in ("utf-8", "euc-kr"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _extract_json_result_code(body: str):
    try:
        parsed = json.loads(body)
    except Exception:
        return None, None

    def find_code(obj):
        if isinstance(obj, dict):
            for k in ("resultCode", "returnReasonCode"):
                if k in obj:
                    return obj[k]
            for v in obj.values():
                r = find_code(v)
                if r is not None:
                    return r
        return None

    code = find_code(parsed)
    return (str(code) if code is not None else None), parsed


def _extract_xml_result_code(body: str):
    m = re.search(r"<resultCode>([^<]*)</resultCode>", body)
    if m:
        return m.group(1).strip(), body
    m2 = re.search(r"<returnReasonCode>([^<]*)</returnReasonCode>", body)
    if m2:
        return m2.group(1).strip(), body
    # Some error bodies omit resultCode but are clearly OpenAPI_ServiceError XML
    if "<OpenAPI_ServiceResponse>" in body or "SERVICE ERROR" in body.upper():
        return "SERVICE_ERROR", body
    return None, body


def fetch_json(url: str, *, retries: int = 3, timeout: int = 25) -> dict:
    """Fetch a URL expected to return JSON with a data.go.kr resultCode.
    Retries on network errors and throttling codes with exponential backoff."""
    delay = 1.0
    last_code = None
    for attempt in range(1, retries + 1):
        try:
            body = _http_get(url, timeout)
        except TooManyRequests:
            # raw HTTP 429 -- back off harder than a normal network hiccup
            if attempt == retries:
                raise FetchError(f"HTTP 429 after {retries} attempts") from None
            time.sleep(max(3.0, delay * 3))
            delay *= 2
            continue
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            if attempt == retries:
                raise FetchError(f"network error after {retries} attempts: {keyutil.redact(str(e))}") from None
            time.sleep(delay)
            delay *= 2
            continue

        code, parsed = _extract_json_result_code(body)
        last_code = code
        if code in SUCCESS_CODES:
            return parsed
        if code in THROTTLE_CODES:
            # back off harder on throttling
            time.sleep(delay * 3)
            delay *= 2
            continue
        if code is None:
            # Unparseable / unexpected shape -- could be transient; retry.
            if attempt == retries:
                raise FetchError(
                    f"could not parse JSON result code, snippet={keyutil.redact(body[:200])}"
                )
            time.sleep(delay)
            delay *= 2
            continue
        # Some other explicit error code -- retry with normal backoff.
        if attempt == retries:
            raise FetchError(f"API error resultCode={code}")
        time.sleep(delay)
        delay *= 2
    raise FetchError(f"failed after {retries} attempts, last_code={last_code}")


def fetch_xml(url: str, *, retries: int = 3, timeout: int = 25) -> str:
    """Fetch a URL expected to return XML with a <resultCode>. Returns the
    raw XML text on success."""
    delay = 1.0
    last_code = None
    for attempt in range(1, retries + 1):
        try:
            body = _http_get(url, timeout)
        except TooManyRequests:
            if attempt == retries:
                raise FetchError(f"HTTP 429 after {retries} attempts") from None
            time.sleep(max(3.0, delay * 3))
            delay *= 2
            continue
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            if attempt == retries:
                raise FetchError(f"network error after {retries} attempts: {keyutil.redact(str(e))}") from None
            time.sleep(delay)
            delay *= 2
            continue

        code, _ = _extract_xml_result_code(body)
        last_code = code
        if code in SUCCESS_CODES:
            return body
        if code in THROTTLE_CODES:
            time.sleep(delay * 3)
            delay *= 2
            continue
        if code is None:
            if attempt == retries:
                raise FetchError(f"could not find resultCode in XML, snippet={keyutil.redact(body[:200])}")
            time.sleep(delay)
            delay *= 2
            continue
        if attempt == retries:
            raise FetchError(f"API error resultCode={code}")
        time.sleep(delay)
        delay *= 2
    raise FetchError(f"failed after {retries} attempts, last_code={last_code}")


def parse_xml_items(xml_text: str):
    """Parse <response><body><items><item>...</item></items></body></response>
    into a list of dicts (child tag -> text)."""
    root = ET.fromstring(xml_text)
    items_el = root.find(".//items")
    out = []
    if items_el is None:
        return out
    for item_el in items_el.findall("item"):
        d = {}
        for child in item_el:
            if len(list(child)) > 0:
                # nested (e.g. vaccine's vcnList/vcnInfo) -- keep as sub-list of dicts
                sub = []
                for sub_child in child:
                    sd = {gc.tag: (gc.text or "").strip() for gc in sub_child}
                    sub.append(sd)
                d[child.tag] = sub
            else:
                d[child.tag] = (child.text or "").strip()
        out.append(d)
    return out
