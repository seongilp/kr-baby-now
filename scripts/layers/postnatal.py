"""postnatal layer: 행정안전부_건강_산후조리업 조회서비스, pk 15154981,
apis.data.go.kr/1741000/postpartum_care/info. JSON. Coordinates are in
EPSG:5174 (Korean TM, Bessel, central belt) and must be converted to WGS84
with pyproj -- explicitly permitted for this one conversion.
"""
from __future__ import annotations

from pyproj import Transformer

from lib import http
from lib.keyutil import load_key
from lib.schema import LayerBuilder, meta_entry

PK = "15154981"
TITLE = "행정안전부_건강_산후조리업 조회서비스"
BASE = "https://apis.data.go.kr/1741000/postpartum_care/info"
PAGE_SIZE = 500

_transformer = Transformer.from_crs("EPSG:5174", "EPSG:4326", always_xy=True)

OPEN_SALS = {"영업/정상"}
OPEN_DTL = {"영업중"}


def _url(key, page):
    return f"{BASE}?serviceKey={key}&pageNo={page}&numOfRows={PAGE_SIZE}&type=json"


def _fetch_page(key, page):
    parsed = http.fetch_json(_url(key, page))
    body = parsed.get("response", {}).get("body", {})
    total = body.get("totalCount")
    items = body.get("items", {})
    if isinstance(items, dict):
        items = items.get("item", [])
    if isinstance(items, dict):
        items = [items]
    return items or [], total


def collect_postnatal():
    key = load_key()
    builder = LayerBuilder("postnatal")

    first_items, total = _fetch_page(key, 1)
    total = int(total) if total else len(first_items)
    all_items = list(first_items)

    # TRAP: this endpoint silently caps numOfRows at 100 regardless of what
    # is requested (verified live: requesting 300/500/1000 all still return
    # exactly 100 rows). Use the actually-returned page size, not PAGE_SIZE,
    # to compute how many pages are needed -- otherwise most of the dataset
    # is silently skipped.
    effective_page_size = len(first_items) if first_items else PAGE_SIZE
    num_pages = max(1, (total + effective_page_size - 1) // effective_page_size)
    if num_pages > 1:
        pages = list(range(2, num_pages + 1))

        def worker(page):
            items, _ = _fetch_page(key, page)
            return items

        for items in http.map_all(worker, pages):
            if items:
                all_items.extend(items)

    excluded_status = 0
    for it in all_items:
        sals = (it.get("SALS_STTS_NM") or "").strip()
        dtl = (it.get("DTL_SALS_STTS_NM") or "").strip()
        if sals not in OPEN_SALS or dtl not in OPEN_DTL:
            excluded_status += 1
            continue

        x = it.get("CRD_INFO_X")
        y = it.get("CRD_INFO_Y")
        lat = lng = None
        try:
            xf, yf = float(x), float(y)
            if xf and yf:
                lng, lat = _transformer.transform(xf, yf)
        except (TypeError, ValueError):
            pass

        addr = it.get("ROAD_NM_ADDR") or it.get("LOTNO_ADDR")

        info = {}
        if it.get("LCPMT_YMD"):
            info["인허가일자"] = it["LCPMT_YMD"]
        try:
            prgnw = int(float(it.get("PRGNW_PSCP_CNT") or 0))
            if prgnw:
                info["임산부정원"] = prgnw
        except (TypeError, ValueError):
            pass
        try:
            infant = int(float(it.get("INFANT_PSCP_CNT") or 0))
            if infant:
                info["영유아정원"] = infant
        except (TypeError, ValueError):
            pass

        mng_no = it.get("MNG_NO", "")
        builder.add(
            id=f"postnatal-{mng_no}",
            name=it.get("BPLC_NM", ""),
            lat=lat,
            lng=lng,
            addr=addr,
            tel=it.get("TELNO"),
            info=info or None,
        )

    path = builder.write("layers")
    meta = meta_entry(
        count=len(builder.records),
        dropped_no_coord=builder.dropped_no_coord,
        source_pk=PK,
        source_title=TITLE,
    )
    return (
        {"postnatal": meta},
        {
            "postnatal": {
                "path": path,
                "total_reported": total,
                "excluded_by_status": excluded_status,
                "coord_conversion": "EPSG:5174 -> EPSG:4326 via pyproj",
            }
        },
    )
