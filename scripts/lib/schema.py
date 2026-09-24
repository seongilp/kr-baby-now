"""Common output schema helpers: coordinate validation, dedup, and layer
metadata tracking, shared by every layer collector."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

LAT_MIN, LAT_MAX = 33.0, 39.0
LNG_MIN, LNG_MAX = 124.0, 132.0

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
)
LAYERS_DIR = os.path.join(DATA_DIR, "layers")
LISTS_DIR = os.path.join(DATA_DIR, "lists")
META_PATH = os.path.join(DATA_DIR, "meta.json")


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def in_korea_bounds(lat, lng) -> bool:
    try:
        lat = float(lat)
        lng = float(lng)
    except (TypeError, ValueError):
        return False
    return LAT_MIN <= lat <= LAT_MAX and LNG_MIN <= lng <= LNG_MAX


class LayerBuilder:
    """Accumulates records for one output layer, applying the shared rules:
    drop rows with no/invalid coordinates (counted), dedupe by
    (name, round(lat,5), round(lng,5))."""

    def __init__(self, name: str):
        self.name = name
        self.records = []
        self.dropped_no_coord = 0
        self._seen = set()

    def add(self, *, id, name, lat, lng, addr=None, tel=None, hours=None, tags=None, info=None):
        if lat is None or lng is None or lat == "" or lng == "":
            self.dropped_no_coord += 1
            return False
        try:
            latf, lngf = float(lat), float(lng)
        except (TypeError, ValueError):
            self.dropped_no_coord += 1
            return False
        if not in_korea_bounds(latf, lngf):
            self.dropped_no_coord += 1
            return False

        key = (name, round(latf, 5), round(lngf, 5))
        if key in self._seen:
            return False
        self._seen.add(key)

        rec = {"id": id, "name": name, "lat": latf, "lng": lngf}
        if addr:
            rec["addr"] = addr
        if tel:
            rec["tel"] = tel
        if hours:
            rec["hours"] = hours
        if tags:
            rec["tags"] = tags
        if info:
            cleaned = {k: v for k, v in info.items() if v is not None and v != ""}
            if cleaned:
                rec["info"] = cleaned
        self.records.append(rec)
        return True

    def write(self, subdir="layers"):
        target_dir = LAYERS_DIR if subdir == "layers" else LISTS_DIR
        os.makedirs(target_dir, exist_ok=True)
        path = os.path.join(target_dir, f"{self.name}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.records, f, ensure_ascii=False, separators=(",", ":"))
        return path

    def size_bytes(self, subdir="layers") -> int:
        target_dir = LAYERS_DIR if subdir == "layers" else LISTS_DIR
        path = os.path.join(target_dir, f"{self.name}.json")
        return os.path.getsize(path) if os.path.exists(path) else 0


def write_flat_list(name: str, rows: list) -> str:
    """Write a plain list-only output (no schema transform) to data/lists/."""
    os.makedirs(LISTS_DIR, exist_ok=True)
    path = os.path.join(LISTS_DIR, f"{name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, separators=(",", ":"))
    return path


def load_meta() -> dict:
    if os.path.exists(META_PATH):
        with open(META_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_meta(meta: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, separators=(",", ":"), indent=2)


def update_meta(entries: dict) -> None:
    """Merge new layer entries into data/meta.json, keeping other layers'
    prior entries untouched."""
    meta = load_meta()
    meta.update(entries)
    save_meta(meta)


def meta_entry(*, count, dropped_no_coord, source_pk, source_title):
    return {
        "count": count,
        "dropped_no_coord": dropped_no_coord,
        "source_pk": source_pk,
        "source_title": source_title,
        "collected_at": now_iso(),
    }


def truncate(s, n=80):
    if s is None:
        return None
    s = str(s)
    return s[:n]
