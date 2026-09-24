"""peds / obgyn layers: 국립중앙의료원 병·의원찾기 API
(HsptlAsembySearchService/getHsptlMdcncListInfoInqire), pk 15000736.
QD=D002 -> peds (~15,183), QD=D011 -> obgyn (~4,147). XML only, no
resultType param needed/supported.
"""
from __future__ import annotations

from lib import http
from lib.keyutil import load_key
from lib.schema import LayerBuilder, meta_entry, truncate

PK = "15000736"
TITLE = "국립중앙의료원_전국 병·의원찾기서비스"
BASE = "https://apis.data.go.kr/B552657/HsptlAsembySearchService/getHsptlMdcncListInfoInqire"
PAGE_SIZE = 1000


def _url(key, qd, page):
    return f"{BASE}?serviceKey={key}&QD={qd}&pageNo={page}&numOfRows={PAGE_SIZE}"


def _fetch_page(key, qd, page):
    xml_text = http.fetch_xml(_url(key, qd, page))
    items = http.parse_xml_items(xml_text)
    total_m = None
    import re

    m = re.search(r"<totalCount>([^<]*)</totalCount>", xml_text)
    if m and m.group(1).strip().isdigit():
        total_m = int(m.group(1).strip())
    return items, total_m


def _weekday_late(item) -> bool:
    for i in range(1, 6):
        v = item.get(f"dutyTime{i}c", "")
        if v and v.strip().isdigit() and int(v.strip()) >= 2000:
            return True
    return False


def _collect(layer_name: str, qd: str):
    key = load_key()
    builder = LayerBuilder(layer_name)

    first_items, total = _fetch_page(key, qd, 1)
    if total is None:
        total = len(first_items)
    all_items = list(first_items)

    effective_page_size = len(first_items) if first_items else PAGE_SIZE
    num_pages = max(1, (total + effective_page_size - 1) // effective_page_size)
    if num_pages > 1:
        pages = list(range(2, num_pages + 1))

        def worker(page):
            items, _ = _fetch_page(key, qd, page)
            return items

        results = http.map_all(worker, pages)
        for items in results:
            if items:
                all_items.extend(items)

    for it in all_items:
        info = {}
        div = it.get("dutyDivNam")
        if div:
            info["종류"] = div
        etc = it.get("dutyEtc")
        if etc:
            info["안내"] = truncate(etc, 80)
        inf = it.get("dutyInf")
        if inf:
            info["비고"] = truncate(inf, 80)
        mapimg = it.get("dutyMapimg")
        if mapimg:
            info["찾아가는 길"] = truncate(mapimg, 80)

        hours = {}
        for day in range(1, 9):
            s = it.get(f"dutyTime{day}s")
            c = it.get(f"dutyTime{day}c")
            if s or c:
                hours[str(day)] = [s or "", c or ""]

        tags = []
        if _weekday_late(it):
            tags.append("야간")
        if it.get("dutyTime6s"):
            tags.append("토요일")
        if it.get("dutyTime7s"):
            tags.append("일요일")
        if it.get("dutyTime8s"):
            tags.append("공휴일")

        hpid = it.get("hpid", "")
        builder.add(
            id=f"{layer_name}-{hpid}",
            name=it.get("dutyName", ""),
            lat=it.get("wgs84Lat"),
            lng=it.get("wgs84Lon"),
            addr=it.get("dutyAddr"),
            tel=it.get("dutyTel1"),
            hours=hours or None,
            tags=tags or None,
            info=info or None,
        )

    path = builder.write("layers")
    return builder, path, total


def collect_peds():
    builder, path, total = _collect("peds", "D002")
    meta = meta_entry(
        count=len(builder.records),
        dropped_no_coord=builder.dropped_no_coord,
        source_pk=PK,
        source_title=TITLE + " (QD=D002 소아청소년과)",
    )
    return {"peds": meta}, {"peds": {"path": path, "total_reported": total}}


def collect_obgyn():
    builder, path, total = _collect("obgyn", "D011")
    meta = meta_entry(
        count=len(builder.records),
        dropped_no_coord=builder.dropped_no_coord,
        source_pk=PK,
        source_title=TITLE + " (QD=D011 산부인과)",
    )
    return {"obgyn": meta}, {"obgyn": {"path": path, "total_reported": total}}
