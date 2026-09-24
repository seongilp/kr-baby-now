"""vaccine list: 질병관리청_어린이 국가예방접종지원사업 위탁의료기관 현황,
pk 15084303, apis.data.go.kr/1790387/orglist3/getOrgList3. XML only.

This API requires BOTH brtcCd (2-digit) and sggCd (5-digit) and has no
code-lookup operation, so we loop over the static 256-sigungu table in
lib/sigungu_codes.py with the shared 4-worker pool.

There are NO coordinates in this API at all -- per spec we do not geocode;
this is written to data/lists/vaccine.json (not data/layers/).
"""
from __future__ import annotations

from lib import http
from lib.keyutil import load_key
from lib.schema import meta_entry, truncate, write_flat_list
from lib.sigungu_codes import SIGUNGU

PK = "15084303"
TITLE = "질병관리청_어린이 국가예방접종지원사업 위탁의료기관 현황 정보"
BASE = "https://apis.data.go.kr/1790387/orglist3/getOrgList3"
# TRAP: unlike most data.go.kr APIs, this one HARD-ERRORS (resultCode 99,
# "페이지 당 조회 건수가 100 을 초과할 수 없습니다") instead of silently
# capping when numOfRows > 100 -- verified live. Max is 100.
PAGE_SIZE = 100


def _url(key, brtc, sgg, page):
    return f"{BASE}?serviceKey={key}&brtcCd={brtc}&sggCd={sgg}&pageNo={page}&numOfRows={PAGE_SIZE}"


def _fetch_sigungu(key, brtc, sgg):
    import re

    xml_text = http.fetch_xml(_url(key, brtc, sgg, 1))
    items = http.parse_xml_items(xml_text)
    m = re.search(r"<totalCount>([^<]*)</totalCount>", xml_text)
    total = int(m.group(1)) if m and m.group(1).strip().isdigit() else len(items)

    all_items = list(items)
    effective_page_size = len(items) if items else PAGE_SIZE
    if total > effective_page_size:
        num_pages = (total + effective_page_size - 1) // effective_page_size
        for page in range(2, num_pages + 1):
            xt = http.fetch_xml(_url(key, brtc, sgg, page))
            all_items.extend(http.parse_xml_items(xt))
    return all_items, total


def collect_vaccine():
    import time

    key = load_key()

    def worker(entry):
        brtc, sgg, name = entry
        try:
            items, total = _fetch_sigungu(key, brtc, sgg)
        except Exception as e:  # noqa: BLE001
            return {"entry": entry, "sigungu": name, "error": str(e), "items": []}
        return {"entry": entry, "sigungu": name, "total": total, "items": items}

    results = {r["sigungu"]: r for r in http.map_all(worker, SIGUNGU)}

    # Extra sweeps for any sigungu that failed (this API has been observed to
    # throw sporadic HTTP 429s under sustained load even with pacing) -- retry
    # just the failures a couple more times before giving up on them.
    for _ in range(2):
        failed_entries = [r["entry"] for r in results.values() if r.get("error")]
        if not failed_entries:
            break
        time.sleep(3.0)
        for r in http.map_all(worker, failed_entries):
            results[r["sigungu"]] = r

    out = []
    errors = []
    for r in results.values():
        if r.get("error"):
            errors.append({"sigungu": r["sigungu"], "error": r["error"]})
            continue
        for it in r.get("items", []):
            vcn_list = it.get("vcnList") or []
            vcn_names = ", ".join(v.get("vcnNm", "") for v in vcn_list if v.get("vcnNm"))
            info = {}
            if vcn_names:
                info["접종백신"] = vcn_names  # 전체 보관 — enrich.py 가 약어로 줄인다
            out.append(
                {
                    "id": f"vaccine-{it.get('orgcd', '')}",
                    "name": it.get("orgnm", ""),
                    "addr": it.get("orgAddr", ""),
                    "tel": it.get("orgTlno", ""),
                    "expnYmd": it.get("expnYmd", ""),
                    "info": info,
                }
            )

    path = write_flat_list("vaccine", out)
    meta = meta_entry(count=len(out), dropped_no_coord=0, source_pk=PK, source_title=TITLE)
    detail = {
        "vaccine": {
            "path": path,
            "sigungu_queried": len(SIGUNGU),
            "sigungu_errors": errors,
            "no_coordinates": True,
        }
    }
    return {"vaccine": meta}, detail
