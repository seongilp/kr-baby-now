#!/usr/bin/env python3
"""수집 후처리: 좌표 없는 예방접종 위탁의료기관 목록(data/lists/vaccine.json)을
소아청소년과·산부인과 레이어에 이름+시군구로 붙여 '예방접종' 태그와 접종 백신 목록을 단다. 여러 번 돌려도 같은 결과.
"""
import json
import re
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / 'data'
TAG = '예방접종'
INFO_KEY = '접종백신'


def norm_name(s: str) -> str:
    s = re.sub(r'\(.*?\)|\[.*?\]', '', s or '')
    return re.sub(r'[\s·.,\-]', '', s)


def region(addr: str) -> str:
    """'서울특별시 종로구 …' → '서울종로구' (시도 앞 두 글자 + 시군구). 시도 표기 차이(서울/서울특별시)를 흡수한다."""
    parts = (addr or '').split()
    if len(parts) < 2:
        return ''
    return parts[0][:2] + parts[1]


def short_vaccines(s: str) -> str:
    """'결핵(BCG, 피내용), B형간염(HepB), …' → 'BCG·HepB·…'. 괄호 속 첫 약어만 모은다."""
    abbrs = []
    for inner in re.findall(r'\(([^()]*)\)', s):
        a = inner.split(',')[0].strip()
        if a and a not in abbrs:
            abbrs.append(a)
    return '·'.join(abbrs) if abbrs else s


def main() -> None:
    vaccine = json.loads((DATA / 'lists/vaccine.json').read_text())
    index = {}
    for v in vaccine:
        index.setdefault((norm_name(v['name']), region(v.get('addr', ''))), v)

    for layer in ('peds', 'obgyn'):
        path = DATA / f'layers/{layer}.json'
        rows = json.loads(path.read_text())
        hit = 0
        for r in rows:
            v = index.get((norm_name(r['name']), region(r.get('addr', ''))))
            tags = [t for t in r.get('tags') or [] if t != TAG]
            info = {k: val for k, val in (r.get('info') or {}).items() if k != INFO_KEY}
            if v:
                hit += 1
                tags.append(TAG)
                vac = (v.get('info') or {}).get(INFO_KEY)
                if vac:
                    info[INFO_KEY] = short_vaccines(vac)
            r['tags'] = tags or None
            r['info'] = info or None
            if r['tags'] is None:
                del r['tags']
            if r['info'] is None:
                del r['info']
        path.write_text(json.dumps(rows, ensure_ascii=False, separators=(',', ':')))
        print(f'{layer}: {hit}/{len(rows)} 예방접종 매칭')


if __name__ == '__main__':
    main()
