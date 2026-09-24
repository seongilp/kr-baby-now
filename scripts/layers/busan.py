"""Busan-specific layers: merge district-level daycare APIs city-wide, plus
nursing rooms, kids cafes, postnatal centers, and a birth-grant list.
"""
from __future__ import annotations

import hashlib
import json
import math
import os

from lib import http
from lib.keyutil import load_key
from lib.schema import LayerBuilder, LAYERS_DIR, meta_entry, write_flat_list

DAYCARE_DISTRICTS = [
    ("15147779", "apis.data.go.kr/6260000/BsChctrJgService", "getBsChctrJg", "중구"),
    ("15147936", "apis.data.go.kr/6260000/BsChctrSgService", "getBsChctrSg", "서구"),
    ("15147943", "apis.data.go.kr/6260000/BsChctrDgService", "getBsChctrDg", "동구"),
    ("15147946", "apis.data.go.kr/6260000/BsChctrYdService", "getBsChctrYd", "영도구"),
    ("15147948", "apis.data.go.kr/6260000/BsChctrBjService", "getBsChctrBj", "부산진구"),
    ("15147966", "apis.data.go.kr/6260000/BsChctrDnService", "getBsChctrDn", "동래구"),
    ("15147990", "apis.data.go.kr/6260000/BsChctrNgService", "getBsChctrNg", "남구"),
    ("15147995", "apis.data.go.kr/6260000/BsChctrBgService", "getBsChctrBg", "북구"),
    ("15148121", "apis.data.go.kr/6260000/BsChctrHgService", "getBsChctrHg", "해운대구"),
    ("15148252", "apis.data.go.kr/6260000/BsChctrShService", "getBsChctrSh", "사하구"),
    ("15148259", "apis.data.go.kr/6260000/BsChctrGjService", "getBsChctrGj", "금정구"),
    ("15148262", "apis.data.go.kr/6260000/BsChctrGsService", "getBsChctrGs", "강서구"),
    ("15148268", "apis.data.go.kr/6260000/BsChctrYjService", "getBsChctrYj", "연제구"),
    ("15148269", "apis.data.go.kr/6260000/BsChctrSyService", "getBsChctrSy", "수영구"),
    ("15148276", "apis.data.go.kr/6260000/BsChctrSsService", "getBsChctrSs", "사상구"),
    ("15148277", "apis.data.go.kr/6260000/BsChctrGiService", "getBsChctrGi", "기장군"),
]

NURSING_PK = "15034033"
NURSING_TITLE = "부산광역시_수유실 보유 시설 현황"
NURSING_BASE = "https://apis.data.go.kr/6260000/BusanNursingroomInfoService/getNursingroomInfo"

KIDSCAFE_PK = "15088938"
KIDSCAFE_TITLE = "부산광역시_키즈카페현황"
KIDSCAFE_BASE = "https://apis.data.go.kr/6260000/BusanKidsCafeInfoService/getKidsCafeInfo"

POSTNATAL_PK = "15088928"
POSTNATAL_TITLE = "부산광역시_산후조리원 현황"
POSTNATAL_BASE = "https://apis.data.go.kr/6260000/BusanBabyCenterInfoService/getBabyCenterInfo"

BIRTH_GRANT_PK = "15114191"
BIRTH_GRANT_TITLE = "부산광역시_출산지원금 현황"
BIRTH_GRANT_BASE = "https://apis.data.go.kr/6260000/BusanChildBirthService/getTblChildBirth"

PAGE_SIZE = 500


def _items_and_total(parsed):
    body = parsed.get("response", {}).get("body", {})
    total = body.get("totalCount")
    try:
        total = int(total) if total is not None else 0
    except (TypeError, ValueError):
        total = 0
    items = body.get("items", {})
    if isinstance(items, dict):
        items = items.get("item", [])
    if isinstance(items, dict):
        items = [items]
    return items or [], total


def _fetch_all(base_url, key, page_size=PAGE_SIZE):
    def url(page):
        return f"{base_url}?serviceKey={key}&pageNo={page}&numOfRows={page_size}&resultType=json"

    first = http.fetch_json(url(1))
    first_items, total = _items_and_total(first)
    all_items = list(first_items)
    # Defend against APIs that silently cap numOfRows lower than requested
    # (seen on the postpartum_care endpoint) by using the actual page size.
    effective_page_size = len(first_items) if first_items else page_size
    num_pages = max(1, (total + effective_page_size - 1) // effective_page_size) if total else 1
    if num_pages > 1:
        pages = list(range(2, num_pages + 1))

        def worker(page):
            items, _ = _items_and_total(http.fetch_json(url(page)))
            return items

        for items in http.map_all(worker, pages):
            if items:
                all_items.extend(items)
    return all_items, total


def _stable_id(prefix, *parts):
    h = hashlib.md5("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{h}"


def collect_busan_daycare():
    key = load_key()
    builder = LayerBuilder("busan-daycare")

    def worker(entry):
        pk, host, op, gu_name = entry
        url = f"https://{host}/{op}?serviceKey={key}&pageNo=1&numOfRows=500&resultType=json"
        items, total = _items_and_total(http.fetch_json(url))
        return gu_name, items, total

    results = http.map_all(worker, DAYCARE_DISTRICTS)

    total_reported = 0
    excluded_not_operating = 0
    for gu_name, items, total in results:
        total_reported += total
        for it in items:
            oper = (it.get("operYn") or "").strip()
            if oper != "Y":
                excluded_not_operating += 1
                continue
            info = {}
            if it.get("chctrTypeNm"):
                info["유형"] = it["chctrTypeNm"]
            if it.get("pscpCnt"):
                info["정원"] = it["pscpCnt"]
            name = it.get("chctrNm", "")
            addr = it.get("dtlAddr", "")
            builder.add(
                id=_stable_id("busan-daycare", gu_name, name, addr),
                name=name,
                lat=it.get("fcltLat"),
                lng=it.get("fcltLot"),
                addr=addr,
                tel=it.get("telno"),
                info=info or None,
            )

    path = builder.write("layers")
    meta = meta_entry(
        count=len(builder.records),
        dropped_no_coord=builder.dropped_no_coord,
        source_pk="+".join(pk for pk, *_ in DAYCARE_DISTRICTS),
        source_title="부산광역시 16개 구·군 어린이집 현황 (구별 API 병합)",
    )
    detail = {
        "busan-daycare": {
            "path": path,
            "total_reported": total_reported,
            "excluded_not_operating": excluded_not_operating,
            "districts": len(DAYCARE_DISTRICTS),
        }
    }
    return {"busan-daycare": meta}, detail


def collect_busan_nursing():
    key = load_key()
    builder = LayerBuilder("busan-nursing")
    items, total = _fetch_all(NURSING_BASE, key)
    for it in items:
        info = {}
        if it.get("place"):
            info["위치"] = it["place"]
        if it.get("target"):
            info["대상"] = it["target"]
        if it.get("father"):
            info["아빠휴게실여부"] = it["father"]
        name = it.get("sj", "")
        builder.add(
            id=_stable_id("busan-nursing", name, it.get("address", "")),
            name=name,
            lat=it.get("lat"),
            lng=it.get("lng"),
            addr=it.get("address"),
            tel=it.get("tel"),
            info=info or None,
        )
    path = builder.write("layers")
    meta = meta_entry(
        count=len(builder.records), dropped_no_coord=builder.dropped_no_coord,
        source_pk=NURSING_PK, source_title=NURSING_TITLE,
    )
    return {"busan-nursing": meta}, {"busan-nursing": {"path": path, "total_reported": total}}


def collect_busan_kidscafe():
    key = load_key()
    builder = LayerBuilder("busan-kidscafe")
    items, total = _fetch_all(KIDSCAFE_BASE, key)
    for it in items:
        name = it.get("cafe_nm", "")
        addr = it.get("road_nm", "")
        builder.add(
            id=_stable_id("busan-kidscafe", name, addr),
            name=name,
            lat=it.get("lat"),
            lng=it.get("lng"),
            addr=addr,
            tel=it.get("tel_no"),
        )
    path = builder.write("layers")
    meta = meta_entry(
        count=len(builder.records), dropped_no_coord=builder.dropped_no_coord,
        source_pk=KIDSCAFE_PK, source_title=KIDSCAFE_TITLE,
    )
    return {"busan-kidscafe": meta}, {"busan-kidscafe": {"path": path, "total_reported": total}}


def _haversine_m(lat1, lng1, lat2, lng2):
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def _load_postnatal_records():
    path = os.path.join(LAYERS_DIR, "postnatal.json")
    if not os.path.exists(path):
        return None, path
    with open(path, encoding="utf-8") as f:
        return json.load(f), path


def collect_busan_postnatal():
    key = load_key()
    items, total = _fetch_all(POSTNATAL_BASE, key)

    candidates = []
    dropped_no_coord = 0
    for it in items:
        name = it.get("center_nm", "")
        addr = it.get("road_nm", "")
        lat, lng = it.get("lat"), it.get("lng")
        try:
            latf, lngf = float(lat), float(lng)
        except (TypeError, ValueError):
            dropped_no_coord += 1
            continue
        candidates.append({"name": name, "addr": addr, "lat": latf, "lng": lngf, "tel": it.get("tel")})

    postnatal_records, postnatal_path = _load_postnatal_records()

    matched = 0
    if postnatal_records is not None:
        changed = False
        for cand in candidates:
            best = None
            best_dist = None
            for rec in postnatal_records:
                dist = _haversine_m(cand["lat"], cand["lng"], rec["lat"], rec["lng"])
                name_match = cand["name"].replace(" ", "") in rec["name"].replace(" ", "") or rec[
                    "name"
                ].replace(" ", "") in cand["name"].replace(" ", "")
                if dist < 300 and name_match:
                    if best_dist is None or dist < best_dist:
                        best, best_dist = rec, dist
            if best is not None:
                matched += 1
                info = best.setdefault("info", {})
                if cand.get("tel") and "부산시전화" not in info:
                    info.setdefault("부산시전화", cand["tel"])
                changed = True

        if changed:
            with open(postnatal_path, "w", encoding="utf-8") as f:
                json.dump(postnatal_records, f, ensure_ascii=False, separators=(",", ":"))

    overlap_ratio = matched / len(candidates) if candidates else 0.0

    if candidates and overlap_ratio >= 0.5:
        # Heavy overlap with the nationwide postnatal layer -- do not write a
        # separate layer file; extra info already merged above.
        meta = meta_entry(
            count=0, dropped_no_coord=dropped_no_coord, source_pk=POSTNATAL_PK,
            source_title=POSTNATAL_TITLE + " (merged into postnatal layer, no separate file)",
        )
        detail = {
            "busan-postnatal": {
                "path": None,
                "total_reported": total,
                "overlap_matched": matched,
                "overlap_ratio": round(overlap_ratio, 3),
                "decision": "merged into postnatal.json, no busan-postnatal.json written",
            }
        }
        return {"busan-postnatal": meta}, detail

    builder = LayerBuilder("busan-postnatal")
    for cand in candidates:
        builder.add(
            id=_stable_id("busan-postnatal", cand["name"], cand["addr"]),
            name=cand["name"],
            lat=cand["lat"],
            lng=cand["lng"],
            addr=cand["addr"],
            tel=cand["tel"],
        )
    builder.dropped_no_coord = dropped_no_coord
    path = builder.write("layers")
    meta = meta_entry(
        count=len(builder.records), dropped_no_coord=builder.dropped_no_coord,
        source_pk=POSTNATAL_PK, source_title=POSTNATAL_TITLE,
    )
    detail = {
        "busan-postnatal": {
            "path": path,
            "total_reported": total,
            "overlap_matched": matched,
            "overlap_ratio": round(overlap_ratio, 3),
            "decision": "written as separate layer (low overlap with nationwide postnatal layer)",
        }
    }
    return {"busan-postnatal": meta}, detail


def collect_busan_birth_grant():
    key = load_key()
    items, total = _fetch_all(BIRTH_GRANT_BASE, key)
    path = write_flat_list("busan-birth-grant", items)
    meta = meta_entry(count=len(items), dropped_no_coord=0, source_pk=BIRTH_GRANT_PK, source_title=BIRTH_GRANT_TITLE)
    return {"busan-birth-grant": meta}, {"busan-birth-grant": {"path": path, "total_reported": total}}
