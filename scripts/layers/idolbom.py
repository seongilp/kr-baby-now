"""idolbom layer + related list-only outputs: 한국건강가정진흥원 아이돌봄
services. This API family (host 1383000) needs `type=json` (not
resultType=json/_type=json) to get a JSON body.

- pk 15078130 getServiceInstitutionList (~232 rows) -> idolbom layer
- pk 15078132 getAreaBaseInstitutionList (~17 rows, mostly blank coords)
  merged in with tag "광역거점"
- pk 15078134 getUsageFeeList -> data/lists/idolbom-fee.json (raw dump)
- pk 15078149 getQualificationDocumentsList -> data/lists/idolbom-docs.json (raw dump)

NOTE: the coordinate field is `lot` (longitude), not `lng`.
"""
from __future__ import annotations

from lib import http
from lib.keyutil import load_key
from lib.schema import LayerBuilder, meta_entry, write_flat_list

INST_PK = "15078130"
INST_TITLE = "한국건강가정진흥원_아이돌봄서비스제공기관 정보 서비스"
INST_BASE = "https://apis.data.go.kr/1383000/idis/serviceInstitutionService/getServiceInstitutionList"

AREA_PK = "15078132"
AREA_BASE = "https://apis.data.go.kr/1383000/idis/areaBaseInstitutionService/getAreaBaseInstitutionList"

FEE_PK = "15078134"
FEE_TITLE = "한국건강가정진흥원_아이돌봄서비스이용요금표 정보 서비스"
FEE_BASE = "https://apis.data.go.kr/1383000/idis/usageFeeService/getUsageFeeList"

DOCS_PK = "15078149"
DOCS_TITLE = "한국건강가정진흥원_아이돌봄정부지원 자격여부 입증서류 및 확인방법 정보 서비스"
DOCS_BASE = "https://apis.data.go.kr/1383000/idis/qualificationDocumentsService/getQualificationDocumentsList"

PAGE_SIZE = 100


def _items_and_total(parsed):
    body = parsed.get("response", {}).get("body", {})
    total = body.get("totalCount")
    items = body.get("items", {})
    if isinstance(items, dict):
        items = items.get("item", [])
    if isinstance(items, dict):
        items = [items]
    return items or [], (int(total) if total else 0)


def _fetch_all(base_url, key, page_size=PAGE_SIZE):
    def url(page):
        return f"{base_url}?serviceKey={key}&pageNo={page}&numOfRows={page_size}&type=json"

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


def collect_idolbom():
    key = load_key()
    builder = LayerBuilder("idolbom")

    inst_items, inst_total = _fetch_all(INST_BASE, key)
    for it in inst_items:
        builder.add(
            id=f"idolbom-{it.get('childCareInstNo', '')}",
            name=it.get("childCareInstNm", ""),
            lat=it.get("lat"),
            lng=it.get("lot"),
            addr=it.get("addr"),
            tel=it.get("rprsTelno"),
        )

    area_items, area_total = _fetch_all(AREA_BASE, key)
    area_skipped_blank = 0
    for it in area_items:
        lat, lot = it.get("lat"), it.get("lot")
        if lat in (None, "") or lot in (None, ""):
            area_skipped_blank += 1
            continue
        builder.add(
            id=f"idolbom-{it.get('childCareInstNo', '')}",
            name=it.get("childCareInstNm", ""),
            lat=lat,
            lng=lot,
            addr=it.get("addr"),
            tel=it.get("rprsTelno"),
            tags=["광역거점"],
        )

    path = builder.write("layers")
    meta = meta_entry(
        count=len(builder.records),
        dropped_no_coord=builder.dropped_no_coord,
        source_pk=f"{INST_PK}+{AREA_PK}",
        source_title=INST_TITLE + " + 아이돌봄광역거점기관 정보 서비스",
    )
    detail = {
        "idolbom": {
            "path": path,
            "inst_total_reported": inst_total,
            "area_total_reported": area_total,
            "area_skipped_blank_coord": area_skipped_blank,
        }
    }
    return {"idolbom": meta}, detail


def collect_idolbom_fee():
    key = load_key()
    items, total = _fetch_all(FEE_BASE, key)
    path = write_flat_list("idolbom-fee", items)
    meta = meta_entry(count=len(items), dropped_no_coord=0, source_pk=FEE_PK, source_title=FEE_TITLE)
    return {"idolbom-fee": meta}, {"idolbom-fee": {"path": path, "total_reported": total}}


def collect_idolbom_docs():
    key = load_key()
    items, total = _fetch_all(DOCS_BASE, key)
    path = write_flat_list("idolbom-docs", items)
    meta = meta_entry(count=len(items), dropped_no_coord=0, source_pk=DOCS_PK, source_title=DOCS_TITLE)
    return {"idolbom-docs": meta}, {"idolbom-docs": {"path": path, "total_reported": total}}
