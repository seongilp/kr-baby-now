"""playground layer: 행정안전부_전국어린이놀이시설정보서비스, pk 15124519,
apis.data.go.kr/1741000/pfc3/getPfctInfo3. JSON.

TRAP: this API family (host 1741000) does NOT use the usual pageNo/numOfRows
params -- it silently ignores them and always returns page 1. The real
pagination params are `pageIndex` / `recordCountPerPage` (verified live).

Cross-referenced against pk 15124527 (exfc5/getExfc5, ~183 rows) to tag
"우수시설" by matching pfctSn.
"""
from __future__ import annotations

from collections import Counter

from lib import http
from lib.keyutil import load_key
from lib.schema import LayerBuilder, meta_entry

PK = "15124519"
TITLE = "행정안전부_전국어린이놀이시설정보서비스"
BASE = "https://apis.data.go.kr/1741000/pfc3/getPfctInfo3"

EXFC_PK = "15124527"
EXFC_BASE = "https://apis.data.go.kr/1741000/exfc5/getExfc5"

PAGE_SIZE = 1000


def _url(key, page):
    return f"{BASE}?serviceKey={key}&pageIndex={page}&recordCountPerPage={PAGE_SIZE}&type=json"


def _fetch_page(key, page):
    parsed = http.fetch_json(_url(key, page))
    body = parsed.get("response", {}).get("body", {})
    total = body.get("totalCnt")
    items = body.get("items") or []
    return items, total


def _exfc_url(key, page):
    return f"{EXFC_BASE}?serviceKey={key}&pageIndex={page}&recordCountPerPage=1000&type=json"


def _fetch_exfc_page(key, page):
    parsed = http.fetch_json(_exfc_url(key, page))
    body = parsed.get("response", {}).get("body", {})
    total = body.get("totalCnt")
    items = body.get("items") or []
    return items, total


def _collect_exfc_pfct_sns(key) -> set:
    first_items, total = _fetch_exfc_page(key, 1)
    total = int(total) if total else len(first_items)
    all_items = list(first_items)
    effective_page_size = len(first_items) if first_items else 1000
    num_pages = max(1, (total + effective_page_size - 1) // effective_page_size)
    if num_pages > 1:
        pages = list(range(2, num_pages + 1))

        def worker(page):
            items, _ = _fetch_exfc_page(key, page)
            return items

        for items in http.map_all(worker, pages):
            if items:
                all_items.extend(items)
    return {str(it.get("pfctSn")) for it in all_items if it.get("pfctSn")}


# 누구나 들어갈 수 있는 곳만 지도에 올린다. 아파트 단지·유치원·어린이집·학교 놀이터는 그 시설 이용자 전용이라 뺀다.
PUBLIC_OUTDOOR = {"도시공원", "하천", "자연휴양림", "야영장", "박물관", "공공도서관", "육아종합지원센터",
                  "유아교육진흥원", "도로휴게시설", "의료기관"}
# 돈 내고 들어가는 실내 놀이 공간(키즈카페·키즈 레스토랑·대형마트 놀이방) — 별도 레이어
INDOOR_PAID = {"놀이제공영업소", "식품접객업소", "대규모점포"}


def route(instl: str | None, oper: str | None) -> str | None:
    """설치장소·운영상태 → 출력 레이어 이름. None 이면 버린다."""
    if oper and oper != "운영":
        return None
    if instl in PUBLIC_OUTDOOR:
        return "playground"
    if instl in INDOOR_PAID:
        return "indoor-play"
    return None


def collect_playground():
    key = load_key()
    excellent_pfct_sns = _collect_exfc_pfct_sns(key)

    builders = {name: LayerBuilder(name) for name in ("playground", "indoor-play")}

    first_items, total = _fetch_page(key, 1)
    total = int(total) if total else len(first_items)
    all_items = list(first_items)

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

    instl_counter = Counter()
    for it in all_items:
        addr = it.get("ronaAddr") or it.get("lotnoAddr")
        daddr = it.get("ronaDaddr") or it.get("lotnoDaddr")
        full_addr = " ".join(x for x in [addr, daddr] if x) or None

        instl = it.get("instlPlaceCdNm")
        if instl:
            instl_counter[instl] += 1

        target = route(instl, it.get("operYnCdNm"))
        if target is None:
            continue
        pfct_sn = str(it.get("pfctSn") or "")
        tags = ["우수시설"] if pfct_sn in excellent_pfct_sns else None

        builders[target].add(
            id=f"{target}-{pfct_sn}",
            name=it.get("pfctNm", ""),
            lat=it.get("latCrtsVl"),
            lng=it.get("lotCrtsVl"),
            addr=full_addr,
            tags=tags,
            info={"설치장소": instl},
        )

    paths = {name: b.write("layers") for name, b in builders.items()}
    metas = {
        name: meta_entry(count=len(b.records), dropped_no_coord=b.dropped_no_coord, source_pk=PK, source_title=TITLE)
        for name, b in builders.items()
    }
    detail = {
        "playground": {
            "paths": paths,
            "total_reported": total,
            "excellent_facility_pfctSn_count": len(excellent_pfct_sns),
            "instlPlaceCdNm_top": instl_counter.most_common(15),
        }
    }
    return metas, detail
